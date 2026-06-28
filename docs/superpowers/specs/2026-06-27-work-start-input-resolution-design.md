# Work-start input resolution (Sprint 1: effortless, correct invocation)

**Status:** design, awaiting CPO review · **Date:** 2026-06-27

## Purpose

Make the broker's one call effortless and correct. Today both transports (`work-start` CLI,
`work_start` MCP tool) require the caller to hand over `repo`, and leave `branch` / `docs_root`
to manual flags. The MCP dogfood showed the friction: the agent did git archaeology for repo
and branch, and docs came back UNKNOWN because nothing told it the docs root. This slice
resolves those inputs from the two places that actually know them, **git** (volatile facts:
repo identity, current branch) and a committed **`.teamctx/config.json`** (stable project
facts: repo override, docs_root), while preserving the honest-UNKNOWN promise exactly.

## Non-goals (sequenced elsewhere, not cut)

- **Linked-issue auto-discovery** (parse `#42` from branch/PR/commits; derive `since`) →
  Sprint 4. Criteria stays honest-UNKNOWN by default; the manual `--issue`/`--since` and the
  MCP `issues`/`since` params still work, so nothing regresses.
- **Legacy retirement** (`refresh`/`context`; rebuild `why`/`open-source` on the broker) →
  Sprint 2. This slice leaves the legacy `github`/`default_output` config fields in place,
  deprecated, and does not reuse them.
- **Additional forges/trackers** (GitLab, Jira) → Sprint 4.
- **Warn when git origin ≠ config repo**: not needed for correctness (config wins); a possible
  future nicety, not built now.

## Design

### New: an input-resolution layer

A dedicated module (`teamctx/resolve.py`) with one function both transports call *before*
`render_work_start`, mirroring how they already share the `render_work_start` use case:

```
def resolve_work_start_inputs(
    *,
    paths: tuple[str, ...],          # always supplied by the caller
    repo: str | None,                # explicit override (CLI --github-repo / MCP repo=)
    branch: str | None,              # explicit override
    docs_root: str | None,           # explicit override
    task: str, issues: tuple[str,...], since: str | None,
    ref: str | None, include_titles: bool,   # passthrough, unchanged
    token: str | None,               # resolved by the transport (env/file), unchanged
    root: Path,                       # resolution root (see "resolution root")
    config_path: Path | None = None, # default: root/.teamctx/config.json
) -> WorkStartInputs
```

It loads the project config (reusing `maybe_load_project_config`), runs git detection, applies
precedence per field, and returns a fully-resolved `WorkStartInputs`. If `repo` cannot be
resolved from any source it raises `WorkStartResolutionError` with a precise message.

### Git detection (`teamctx/git_context.py`)

Thin, read-only subprocess wrappers, no network. Any failure returns `None` (honest absence),
never a guess:

- `detect_repo(root) -> str | None`, parse `git -C <root> remote get-url origin` into
  `owner/name`. Handles SSH (`git@host:owner/name.git`) and HTTPS
  (`https://host/owner/name(.git)`) forms; returns `None` for unparseable / no-origin /
  not-a-repo.
- `detect_branch(root) -> str | None`, `git -C <root> rev-parse --abbrev-ref HEAD`; returns
  `None` for detached HEAD (`"HEAD"`) or not-a-repo.

### Config: additive `work_start` section

Extend `ProjectConfig` (still `teamctx.project_config.v0`, additive, backward-compatible;
`extra="forbid"` plus defaults means old config files keep validating, so no version bump is
warranted):

```
class WorkStartConfig(StrictConfigModel):
    repo: str | None = None        # override for forks / non-canonical origins
    docs_root: str | None = None   # docs dir scanned for supersession frontmatter

class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    github: GitHubSourceConfig | None = None   # LEGACY (refresh), frozen, not reused here
    default_output: str = DEFAULT_OUTPUT_PATH  # LEGACY
    work_start: WorkStartConfig | None = None  # NEW
```

**Shared-vs-local seam (load-bearing for Sprint 2):** `.teamctx/config.json` is *committed and
shared*, `work_start.repo`, `work_start.docs_root` are facts about the project, identical for
every actor. The **token/identity is per-actor and never committed** (`GITHUB_TOKEN` /
`GITHUB_TOKEN_FILE`, unchanged). This is what lets multiple terminals each be a distinct actor
against one shared repo.

### Precedence (per field)

| Field      | Resolution order |
|------------|------------------|
| repo       | explicit arg → `work_start.repo` → git origin → **error if still none** |
| branch     | explicit arg → git HEAD → none |
| docs_root  | explicit arg → `work_start.docs_root` → none |
| token      | unchanged (`GITHUB_TOKEN` → `GITHUB_TOKEN_FILE`) |
| issues / since / ref | explicit-only (unchanged; criteria stays UNKNOWN by default) |

Branch is **never** read from config, it is volatile and a static file would be stale.

### Honest-UNKNOWN behavior (the invariant)

- **repo unresolved** → raise `WorkStartResolutionError`: *"could not determine the repository:
  not in a git repo with a recognizable `origin` remote, and no `work_start.repo` in
  `.teamctx/config.json`. Pass the repo explicitly (`--github-repo` / `repo=`)."* Rationale: with
  no repo there is literally nothing to check; a wall of UNKNOWN would hide the real cause. CLI
  surfaces it as a `ClickException`; the MCP tool returns the message as its result so the agent
  learns exactly what to provide.
- **branch none** (detached HEAD / not a repo) → gate connector not run → **gate UNKNOWN**
  (already the runner's behavior; preserved).
- **docs_root none** → docs connector not run → **docs UNKNOWN** (preserved).
- **fork safety** → committed `work_start.repo` overrides the fork's git origin, so a
  fork checkout is checked against the canonical repo. This is the override's whole job.

### Resolution root (MCP correctness)

Git detection and config load run against an explicit `root`, resolved as
`explicit root → TEAMCTX_PROJECT_ROOT env → process cwd`. The CLI uses cwd. The MCP server is a
subprocess whose cwd is set by the client (typically the workspace root); the env override makes
detection robust when cwd ≠ repo, instead of silently depending on launch cwd.

### Transports (thin, unchanged shape)

- **CLI `work-start`:** `--github-repo` becomes optional; on omission, resolve. Build inputs via
  `resolve_work_start_inputs(...)` then `render_work_start(...)`.
- **MCP `work_start`:** `repo` becomes optional; `paths` stays required (the agent always knows
  them). Resolve against the server's root, then `render_work_start(...)`. Tool description
  updated: repo/branch/docs_root are auto-detected; pass them only to override.

## Testing

- **git_context:** URL parsing, SSH, HTTPS, with/without `.git`, non-parseable → None; branch:
  normal, detached HEAD → None, not-a-repo → None. Use a real temp git repo fixture.
- **resolve:** table-driven precedence per field (explicit / config / git / none); the
  repo-unresolved error; passthrough fields untouched.
- **config:** `work_start` section optional; a pre-existing config without it still validates
  (backward compatibility).
- **transports:** CLI `work-start` with no `--github-repo` in a temp git repo resolves and runs;
  the MCP path resolves via the same function; honest-UNKNOWN for absent branch/docs.
- Existing 212 tests stay green; ruff(src+tests) + mypy --strict + purity.

## Open questions for CPO review

1. The repo-unresolved **error** (vs. an all-UNKNOWN answer), I chose the precise error because
   "no repo" is a setup problem, not a coverage gap. Agree?
2. `TEAMCTX_PROJECT_ROOT` as the MCP root override, minimal and removes a silent cwd dependency.
   Acceptable, or do you want root handling deferred until a real cwd≠repo case appears?
