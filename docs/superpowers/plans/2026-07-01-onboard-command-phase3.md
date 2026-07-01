# Onboard Command (Phase 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single `teamctx onboard` command that scaffolds a repo for teamctx with zero flags and zero false confidence: it detects the GitHub repo, writes a trackable config, installs the reflex hook, writes an honest CLAUDE.md snippet, reports the real credential path, and prints a live reachability check, reporting exactly what it changed.

**Architecture:** A new focused module `src/teamctx/onboard.py` holds a minimal source-onboarder seam (one `GithubOnboarder` today, in a plain list) plus the orchestration flow, built entirely on the Part 1 resolvers (`resolve_project_root`, `detect_repo`/`parse_github_repo`, `resolve_github_token`). Every write is atomic (temp + rename) and idempotent; the flow returns structured per-step results that the thin CLI command renders. It reuses the existing hook-install logic (extracted from `install_hook_command`) and shares the honest CLAUDE.md snippet.

**Tech Stack:** Python 3.12, click, pydantic v2, pytest. Per-task gate: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src`.

**Source of truth:** spec `docs/superpowers/specs/2026-06-29-onboard-runtime-honesty.md`, sections 2.1 to 2.5. Phase 1 (1.1-1.3) and Phase 2 (1.4-1.7) are merged. This is the last phase of the slice.

**House rules:** no em dashes anywhere (hard ship gate; grep for U+2014 via `grep -rnP "\x{2014}"`, never a literal). Tests network-free (inject the `opener` / mock fetchers; `TEAMCTX_DISABLE_GH_AUTH` is set suite-wide). Build complete to the bar; fail closed on ambiguity. Run a codex adversarial review before merge.

---

## Design decisions (pinned)

- **Non-interactive by design.** `onboard` with no flags does the setup and prints a "what changed" summary. Flags: `--repo owner/name` (override detection), `--force` (overwrite an existing config), `--dry-run` (preview, write nothing), `--yes` (accepted and documented as "assume non-interactive"; there is no prompt today, so it is a reserved no-op, not faked behavior). Deferred, on merit: `--with-mcp`, `--global`, docs auto-enable.
- **Structured results, not prints, in the flow.** `run_onboard(...)` returns an `OnboardResult` (a tuple of `StepResult`s + a single next step + an `ok` flag). The CLI renders it. This makes the flow testable without capturing stdout.
- **Transaction model (from 2.2):** additive and idempotent; each file write is atomic (temp + rename); no cross-step rollback. A step that cannot proceed fails only itself with a how-to-fix; later steps still run. A missing token does not abort (config + hook still written; the gap is the reported to-do).
- **`--yes` open question for Edgar:** it has no behavior today (onboard is already non-interactive). Included as a reserved flag per the spec's flag list; flag at review if you would rather drop it.

## Revisions (rev 2, after the codex plan-review)

A codex adversarial review found one P0 and five P1s, all verified against the code and git
semantics. Apply these on top of the tasks below; where they conflict, the revision wins.

**R1 (was P0): the CLAUDE.md upsert must refuse malformed or hand-edited marker blocks, never
overwrite them (Task 8).** Blind `index(START)`/`index(END)` corrupts when an end marker precedes a
start, or when there are multiple markers, and it would silently replace a user's edits sitting
inside the markers. Replace the whole `upsert_claude_md_snippet` with a line-parsed version that (a)
requires exactly one ordered start/end pair, (b) only manages a marked block whose body matches a
KNOWN teamctx-generated body, and (c) migrates an unmarked legacy block only on an exact single
occurrence. Anything else is left untouched with a warning:

```python
_SNIPPET_START = "<!-- teamctx:start -->"
_SNIPPET_END = "<!-- teamctx:end -->"
_SNIPPET_HEADING = "## Team context (teamctx)"
_KNOWN_BODIES = (CLAUDE_MD_SNIPPET, _LEGACY_SNIPPET_BODY)


def _marked_block() -> str:
    return f"{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_END}\n"


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _marker_span(lines: list[str]) -> tuple[int, int] | None:
    starts = [i for i, ln in enumerate(lines) if ln.strip() == _SNIPPET_START]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == _SNIPPET_END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return None
    return starts[0], ends[0]


def upsert_claude_md_snippet(root: Path, *, dry_run: bool) -> StepResult:
    path = root / "CLAUDE.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines(keepends=True)
    block = _marked_block()
    known_norms = {_normalize_ws(b) for b in _KNOWN_BODIES}

    span = _marker_span(lines)
    if span is None and (_SNIPPET_START in existing or _SNIPPET_END in existing):
        return StepResult("claude_md", "skipped", "found teamctx markers in CLAUDE.md that aren't a "
                          "clean single start/end pair; fix or remove them by hand, then re-run.")
    if span is not None:
        start_i, end_i = span
        body = "".join(lines[start_i + 1 : end_i])
        if _normalize_ws(body) == _normalize_ws(CLAUDE_MD_SNIPPET):
            return StepResult("claude_md", "already", "CLAUDE.md snippet already current.")
        if _normalize_ws(body) not in known_norms:
            return StepResult("claude_md", "skipped", "the teamctx block in CLAUDE.md was hand-edited; "
                              "left it untouched. Remove it and re-run to let teamctx manage it.")
        if dry_run:
            return StepResult("claude_md", "skipped", "--dry-run: would refresh the CLAUDE.md snippet.")
        _atomic_write(path, "".join(lines[:start_i]) + block + "".join(lines[end_i + 1 :]))
        return StepResult("claude_md", "wrote", "refreshed the CLAUDE.md snippet in place.")

    if existing.count(_LEGACY_SNIPPET_BODY) == 1:  # exact, single -> confident migration
        if dry_run:
            return StepResult("claude_md", "skipped", "--dry-run: would migrate the old CLAUDE.md snippet.")
        _atomic_write(path, existing.replace(_LEGACY_SNIPPET_BODY, block, 1))
        return StepResult("claude_md", "wrote", "migrated the old CLAUDE.md snippet to the marked block.")

    if _SNIPPET_HEADING in existing:  # a heading we can't confidently match -> never guess
        return StepResult("claude_md", "skipped", "found an edited '## Team context (teamctx)' block "
                          "in CLAUDE.md; left it untouched. Remove it by hand and re-run.")

    if dry_run:
        return StepResult("claude_md", "skipped", "--dry-run: would add the CLAUDE.md snippet.")
    prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
    joiner = "" if prefix == "" else "\n"
    _atomic_write(path, prefix + joiner + block)
    return StepResult("claude_md", "wrote", "added the teamctx snippet to CLAUDE.md.")
```

This **supersedes Task 8's implementation and `_replace_normalized_span` entirely** (drop the fixed
n-line replacer; exact single-occurrence migration is simpler and cannot false-"wrote"/loop). Add
Task 8 tests: end-marker-before-start (skipped, untouched); two start markers (skipped); a marked
block with a hand-edited body (skipped, preserved); the existing fresh/idempotent/migrate/edited
cases still hold.

**R2 (was P1): the gitignore patch must actually override a blanket `.teamctx/` ignore, idempotently
(Task 7, and use the same stanza in Task 1).** Git cannot re-include a file whose parent dir is
ignored, so `.teamctx/*` + `!.teamctx/config.json` alone does NOT fix an existing `.teamctx/` rule.
Append a canonical three-line stanza that un-ignores the dir first, only if not already present, then
verify and fail closed with a diagnostic:

```python
_TRACKABLE_STANZA = (
    "# teamctx (config is tracked; local state is not)\n"
    "!.teamctx/\n"
    ".teamctx/*\n"
    "!.teamctx/config.json\n"
)


def ensure_config_trackable(root: Path, *, dry_run: bool) -> StepResult:
    if _config_is_trackable(root):
        return StepResult("gitignore", "already", ".teamctx/config.json is already trackable.")
    if dry_run:
        return StepResult("gitignore", "skipped", "--dry-run: would patch .gitignore to track .teamctx/config.json.")
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if "!.teamctx/config.json" not in existing:  # idempotent: never append the stanza twice
        prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
        _atomic_write(gitignore, prefix + "\n" + _TRACKABLE_STANZA)
    if _config_is_trackable(root):
        return StepResult("gitignore", "wrote", "patched .gitignore so .teamctx/config.json is trackable.")
    detail = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-v", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    ).stdout.strip()
    return StepResult("gitignore", "failed", "couldn't make .teamctx/config.json trackable; a broader "
                      f"rule still ignores it ({detail or 'see .gitignore'}). Edit .gitignore by hand.")
```

In Task 1 (teamctx's own repo `.gitignore`), replace the `.teamctx/` line with the same stanza
(`!.teamctx/` then `.teamctx/*` then `!.teamctx/config.json`); the Task 1 test (config trackable,
state ignored) still holds.

**R3 (was P1): `run_onboard` must set `ok=False` when any step failed (Tasks 9, 10).** A failed
required step (malformed settings, gitignore not fixable) currently still returns `ok=True`, so the
CLI exits 0 after a `[FAILED]` line. Fix: `ok = not any(s.status == "failed" for s in steps)`. A
missing token stays `noted`/`skipped` (not `failed`), so it does not flip `ok` (spec: a missing token
does not abort).

**R4 (was P1): token resolution is single-sourced (Task 5).** Drop `github_token_source`. Add to
`tokens.py` a `resolve_github_token_with_source(token_env) -> tuple[str | None, str | None]` (source
in "env"/"file"/"gh"/None) and make `resolve_github_token` delegate to `[0]` (behavior unchanged,
test_tokens still holds). `auth_status` and `run_onboard` resolve ONCE via the with-source function
and pass that same token to `verify_health`, so the gh fallback cannot drift across calls. Interpolate
`token_env` in the messages so a custom env name is reported correctly (not a hardcoded GITHUB_TOKEN):

```python
def resolve_github_token_with_source(token_env: str = "GITHUB_TOKEN") -> tuple[str | None, str | None]:
    token = os.environ.get(token_env)
    if token:
        return token, "env"
    token_file = os.environ.get(f"{token_env}_FILE")
    if token_file:
        try:
            value = Path(token_file).expanduser().read_text(encoding="utf-8").strip() or None
        except OSError:
            value = None
        if value:
            return value, "file"
    if token_env == "GITHUB_TOKEN" and not os.environ.get("TEAMCTX_DISABLE_GH_AUTH"):
        gh = _gh_auth_token()
        if gh:
            return gh, "gh"
    return None, None


def resolve_github_token(token_env: str = "GITHUB_TOKEN") -> str | None:
    return resolve_github_token_with_source(token_env)[0]
```

`auth_status(token_env)` uses `token, source = resolve_github_token_with_source(token_env)`; messages:
env -> f"using {token_env} from your environment.", file -> f"using the token file in {token_env}_FILE.",
gh -> "using your gh CLI login." `run_onboard` calls it once, records the auth step, and passes the
SAME `token` into `verify_health`.

**R5 (was P1): CLI smoke tests must be network-free (Task 10).** `test_onboard_happy_path` must NOT
set a real token and invoke the real command (that hits live GitHub in `verify_health`). Instead run
the CLI tests with NO token (set `TEAMCTX_DISABLE_GH_AUTH=1`, unset `GITHUB_TOKEN`): config, gitignore,
hook, and snippet still write; auth and health report "not found"/"no credential" without any network.
Keep found-credential + health coverage in the `run_onboard` unit tests (Task 9) via the injected
`opener`. The happy-path CLI assertions become: exit 0, config exists, "acme/widgets" in output,
"work-start" in the next step.

**R6 (was P2, fold in): honest labels and a clearer error.**
- `run_onboard` uses a `noted` status for the auth and health report steps (they are not writes);
  add `"noted"` to `StepResult.status` and `_STEP_MARK["noted"] = "checked"`, so it renders
  `[checked] health: reached GitHub...` not `[already set] health: ...`.
- `_resolve_repo`: distinguish an invalid `--repo` from an absent one. If `repo_override` is given but
  `parse_github_repo(repo_override)` is None, the failed detect step says
  f"{repo_override!r} is not a github.com owner/name; pass --repo owner/name", not "no --repo was given".
- Add a Task 2 test that `_atomic_write` is failure-atomic: monkeypatch `os.replace` to raise, assert
  the original file content is unchanged and no `*.tmp` file is left in the directory.

---

## File map

- Create `src/teamctx/onboard.py`: the seam (`GithubOnboarder`, `ONBOARDERS`), the flow (`run_onboard`, `OnboardResult`, `StepResult`, `AuthStatus`, `HealthReport`), and the write helpers (`_atomic_write`, `ensure_config_trackable`, `upsert_claude_md_snippet`, `CLAUDE_MD_SNIPPET`, `_LEGACY_SNIPPET_BODY`).
- Modify `src/teamctx/tokens.py`: add `github_token_source` (report which source a credential came from, for honest auth reporting).
- Modify `src/teamctx/cli.py`: extract `install_hook_into_settings` from `install_hook_command` (reusable, non-click); import `CLAUDE_MD_SNIPPET` from onboard (drop the local `_CLAUDE_MD_SNIPPET`); add the `onboard` command.
- Modify `.gitignore`: line 26 `.teamctx/` -> `.teamctx/*` then `!.teamctx/config.json`.
- Tests: create `tests/test_onboard.py`, `tests/test_onboard_cli.py`; update `tests/test_install_hook.py` (honest snippet copy + shared constant).

---

## Task 1: Make `.teamctx/config.json` trackable in teamctx's own repo (spec 2.3, repo part)

**Files:**
- Modify: `.gitignore:26`
- Test: `tests/test_onboard.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_onboard.py
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_repo_gitignore_allows_tracking_teamctx_config() -> None:
    # .teamctx/config.json must be trackable in teamctx's own repo (for the dogfood fixture and
    # so onboard's own pattern matches). git check-ignore exits 1 when a path is NOT ignored.
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", ".teamctx/config.json"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 1, f"config.json is still ignored: {result.stdout!r}"
    # local state IS still ignored:
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", ".teamctx/state.sqlite3"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert ignored.returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_onboard.py -v`
Expected: FAIL (config.json is currently ignored by `.teamctx/`, so check-ignore exits 0).

- [ ] **Step 3: Edit `.gitignore`**

Replace the `.teamctx/` line (line 26) with the un-ignore pattern:

```
# teamctx local state (config.json is tracked; everything else here is local)
.teamctx/*
!.teamctx/config.json
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_onboard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .gitignore tests/test_onboard.py
git commit -m "build: track .teamctx/config.json (un-ignore it; keep local state ignored)"
```

---

## Task 2: Create `onboard.py` with the honest snippet + atomic write (spec 2.4 copy)

The snippet must claim only what auto-fires today (open PRs touching your files, failing checks), not "changed specs" / "superseded docs". It moves to `onboard.py` as the shared source; `install-hook` imports it. The old text is kept as `_LEGACY_SNIPPET_BODY` for Task 8's migration.

**Files:**
- Create: `src/teamctx/onboard.py`
- Modify: `src/teamctx/cli.py` (`install_hook_command` uses the shared constant; drop `_CLAUDE_MD_SNIPPET`)
- Test: `tests/test_onboard.py`, `tests/test_install_hook.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add)
from teamctx.onboard import CLAUDE_MD_SNIPPET, _atomic_write


def test_snippet_is_honest_about_what_auto_fires() -> None:
    assert "open PRs" in CLAUDE_MD_SNIPPET or "open pull requests" in CLAUDE_MD_SNIPPET
    assert "failing checks" in CLAUDE_MD_SNIPPET
    # it must NOT overclaim the checks that do not auto-fire yet:
    assert "changed specs" not in CLAUDE_MD_SNIPPET
    assert "superseded docs" not in CLAUDE_MD_SNIPPET


def test_atomic_write_creates_and_overwrites(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "f.txt"
    _atomic_write(target, "one\n")
    assert target.read_text(encoding="utf-8") == "one\n"
    _atomic_write(target, "two\n")
    assert target.read_text(encoding="utf-8") == "two\n"
    # no leftover temp files in the directory:
    assert [p.name for p in target.parent.iterdir()] == ["f.txt"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k "snippet_is_honest or atomic_write" -v`
Expected: FAIL (module `teamctx.onboard` does not exist).

- [ ] **Step 3: Create `src/teamctx/onboard.py`**

```python
"""The onboard command: scaffold a repo for teamctx honestly, over the Part 1 resolvers.

A minimal source-onboarder seam (one GithubOnboarder today, in a plain list) plus the flow that
writes a trackable config, installs the reflex hook, writes an honest CLAUDE.md snippet, reports
the real credential path, and prints a live reachability check. Every write is atomic and
idempotent; the flow returns structured results the CLI renders. No LLM, no verdicts here."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# The honest snippet: only what the hook auto-fires today (open PRs on your files, failing
# checks). Do NOT claim changed specs / superseded docs until they auto-fire (next slice).
CLAUDE_MD_SNIPPET = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open pull requests touching your files and failing checks on "
    "your branch. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)

# The pre-Phase-3 snippet body, kept verbatim so Task 8 can recognize and migrate an old unmarked
# block that the user has NOT edited. Never used for new writes.
_LEGACY_SNIPPET_BODY = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open PRs touching your files, failing checks, changed specs, and "
    "superseded docs. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically: a temp file in the same directory, then rename. A
    crash mid-write never leaves a half-written file at ``path``."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib_suppress():
            os.unlink(tmp_name)
        raise


class contextlib_suppress:
    """Tiny inline suppressor to avoid an extra import; ignores OSError on temp cleanup."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return exc_type is not None and issubclass(exc_type, OSError)  # type: ignore[arg-type]
```

Note: prefer the stdlib. Replace the inline suppressor with `import contextlib` and
`with contextlib.suppress(OSError): os.unlink(tmp_name)` when you write the file; the class above
is shown only to make the intent explicit. Use `contextlib.suppress`.

- [ ] **Step 4: Point `install-hook` at the shared snippet**

In `src/teamctx/cli.py`: delete the local `_CLAUDE_MD_SNIPPET` constant (lines ~572-578); add `from teamctx.onboard import CLAUDE_MD_SNIPPET` to the imports; replace the two `_CLAUDE_MD_SNIPPET` uses in `install_hook_command` (the `--print` branch and the write branch) with `CLAUDE_MD_SNIPPET`.

- [ ] **Step 5: Update `tests/test_install_hook.py`**

Grep it for the old snippet phrases and update: `grep -n "changed specs\|superseded docs\|surfaces open PRs" tests/test_install_hook.py`. Any assertion on the old copy becomes the honest copy ("open pull requests touching your files and failing checks"); assert `"changed specs" not in output`.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_onboard.py tests/test_install_hook.py -v && python -m mypy src`
Expected: PASS, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add src/teamctx/onboard.py src/teamctx/cli.py tests/test_onboard.py tests/test_install_hook.py
git commit -m "feat(onboard): honest shared CLAUDE.md snippet + atomic write helper"
```

---

## Task 3: Extract a reusable hook installer from `install_hook_command` (spec 2.2 step 6)

`onboard` must install the reflex hook without duplicating logic. Extract the settings-mutation into a plain function that both the command and onboard call.

**Files:**
- Modify: `src/teamctx/cli.py`
- Test: `tests/test_install_hook.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_install_hook.py  (add)
from teamctx.cli import install_hook_into_settings


def test_install_hook_into_settings_is_idempotent(tmp_path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    wrote = install_hook_into_settings(settings_path)
    assert wrote is True and settings_path.exists()
    # second call is a no-op (already present):
    wrote_again = install_hook_into_settings(settings_path)
    assert wrote_again is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_install_hook.py::test_install_hook_into_settings_is_idempotent -v`
Expected: FAIL (`install_hook_into_settings` not defined).

- [ ] **Step 3: Extract the function**

In `src/teamctx/cli.py`, add a plain function that owns the load + validate + append + atomic write, returning whether it changed anything, and re-implement `install_hook_command` on top of it:

```python
from teamctx.onboard import CLAUDE_MD_SNIPPET, _atomic_write


def install_hook_into_settings(settings_path: Path) -> bool:
    """Add the teamctx PreToolUse hook to ``settings_path`` if absent. Returns True if it wrote a
    change, False if the hook was already present. Raises click.ClickException on a malformed
    settings file (the caller decides whether that aborts). Atomic write."""

    settings = _load_settings(settings_path)
    if _has_hook_entry(settings):
        return False
    hooks = settings.get("hooks")
    if "hooks" in settings and not isinstance(hooks, dict):
        raise click.ClickException(
            f"{settings_path}: its 'hooks' value isn't a JSON object. Fix or remove that key "
            "and re-run."
        )
    pre = (hooks or {}).get("PreToolUse")
    if pre is not None and not isinstance(pre, list):
        raise click.ClickException(
            f"{settings_path}: 'hooks.PreToolUse' isn't a list. Fix or remove it and re-run."
        )
    settings.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
        copy.deepcopy(_HOOK_ENTRY)
    )
    _atomic_write(settings_path, json.dumps(settings, indent=2) + "\n")
    return True
```

Then rewrite `install_hook_command` to use it: for `--print`, compute `settings` as before and echo (no write); otherwise call `install_hook_into_settings(settings_path)` and echo "Installed..." or "hook already present", then echo the snippet. Keep the `--print` behavior (show settings + snippet, write nothing) intact; extract only the write path. Verify the `--print` branch still shows the merged settings (it may build the settings dict via `_load_settings` + a dry merge for display).

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_install_hook.py -v`
Expected: PASS (existing install-hook tests + the new one).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_install_hook.py
git commit -m "refactor(cli): extract install_hook_into_settings for reuse by onboard"
```

---

## Task 4: `GithubOnboarder.detect` + `propose_config` (spec 2.1)

**Files:**
- Modify: `src/teamctx/onboard.py`
- Test: `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add)
import subprocess
from teamctx.onboard import GithubOnboarder


def _init_repo(root: Path, origin: str) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", origin], check=True)


def test_detect_returns_owner_name_for_github_origin(tmp_path: Path) -> None:
    _init_repo(tmp_path, "git@github.com:acme/widgets.git")
    assert GithubOnboarder().detect(tmp_path) == "acme/widgets"


def test_detect_returns_none_for_non_github_origin(tmp_path: Path) -> None:
    _init_repo(tmp_path, "git@gitlab.com:acme/widgets.git")
    assert GithubOnboarder().detect(tmp_path) is None


def test_detect_returns_none_outside_a_repo(tmp_path: Path) -> None:
    assert GithubOnboarder().detect(tmp_path) is None


def test_propose_config_is_repo_fragment() -> None:
    assert GithubOnboarder().propose_config("acme/widgets") == {"repo": "acme/widgets"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k "detect or propose_config" -v`
Expected: FAIL (`GithubOnboarder` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/onboard.py`:

```python
from teamctx.git_context import detect_repo


class GithubOnboarder:
    """The one source onboarder today. Host-aware detection reuses Part 1's ``detect_repo``,
    which returns owner/name only for a github.com origin (fail-closed on any other host)."""

    provider = "github"

    def detect(self, root: Path) -> str | None:
        return detect_repo(root)

    def propose_config(self, repo: str) -> dict[str, str]:
        return {"repo": repo}


ONBOARDERS: list[GithubOnboarder] = [GithubOnboarder()]
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_onboard.py -k "detect or propose_config" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/onboard.py tests/test_onboard.py
git commit -m "feat(onboard): GithubOnboarder detect (host-aware) + propose_config"
```

---

## Task 5: Credential source reporting + `auth_status` (spec 2.1, 2.2 step 5)

`auth_status` reports the real credential path the runtime will use, via `resolve_github_token`, plus a how-to-fix when absent. `resolve_github_token` returns only the token, so add `github_token_source` (which source, mirroring the same precedence) for honest labeling.

**Files:**
- Modify: `src/teamctx/tokens.py`, `src/teamctx/onboard.py`
- Test: `tests/test_tokens.py`, `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tokens.py  (add)
from teamctx.tokens import github_token_source


def test_github_token_source_env(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    assert github_token_source() == "env"


def test_github_token_source_file(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    f = tmp_path / "t"
    f.write_text("secret\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(f))
    assert github_token_source() == "file"


def test_github_token_source_none(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")  # no gh fallback in tests
    assert github_token_source() is None
```

```python
# tests/test_onboard.py  (add)
from teamctx.onboard import GithubOnboarder


def test_auth_status_reports_found_source(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    status = GithubOnboarder().auth_status()
    assert status.found is True and status.source == "env"
    assert "GITHUB_TOKEN" in status.message


def test_auth_status_reports_missing_with_fix(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    status = GithubOnboarder().auth_status()
    assert status.found is False and status.source is None
    assert "GITHUB_TOKEN" in status.message  # names the one thing to do
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tokens.py -k github_token_source tests/test_onboard.py -k auth_status -v`
Expected: FAIL (`github_token_source` / `auth_status` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/tokens.py`, add (it mirrors `resolve_github_token`'s precedence; keep them adjacent so the mirror stays honest):

```python
def github_token_source(token_env: str = "GITHUB_TOKEN") -> str | None:
    """Which source ``resolve_github_token`` would use for a present credential ("env", "file",
    or "gh"), or None. For honest onboard reporting; mirrors resolve_github_token's precedence."""

    if os.environ.get(token_env):
        return "env"
    token_file = os.environ.get(f"{token_env}_FILE")
    if token_file:
        try:
            if Path(token_file).expanduser().read_text(encoding="utf-8").strip():
                return "file"
        except OSError:
            pass
    if (
        token_env == "GITHUB_TOKEN"
        and not os.environ.get("TEAMCTX_DISABLE_GH_AUTH")
        and _gh_auth_token()
    ):
        return "gh"
    return None
```

In `src/teamctx/onboard.py`:

```python
from dataclasses import dataclass

from teamctx.tokens import github_token_source, resolve_github_token

_AUTH_MESSAGE = {
    "env": "using GITHUB_TOKEN from your environment.",
    "file": "using the token file in GITHUB_TOKEN_FILE.",
    "gh": "using your gh CLI login.",
}
_AUTH_MISSING = (
    "no GitHub credential found. Set GITHUB_TOKEN in your environment (or GITHUB_TOKEN_FILE with "
    "a path to a token file), or run `gh auth login`. Until then teamctx can't check open PRs or "
    "failing checks and will say so, never a false all-clear."
)


@dataclass(frozen=True)
class AuthStatus:
    found: bool
    source: str | None
    message: str
```

Add the method to `GithubOnboarder`:

```python
    def auth_status(self, token_env: str = "GITHUB_TOKEN") -> AuthStatus:
        token = resolve_github_token(token_env)
        if token:
            source = github_token_source(token_env)
            return AuthStatus(found=True, source=source, message=_AUTH_MESSAGE.get(source or "", "credential found."))
        return AuthStatus(found=False, source=None, message=_AUTH_MISSING)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_tokens.py tests/test_onboard.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/tokens.py src/teamctx/onboard.py tests/test_tokens.py tests/test_onboard.py
git commit -m "feat(onboard): honest credential source reporting (auth_status)"
```

---

## Task 6: Count-honest `verify_health` (spec 2.5)

A live reachability report (never a verdict): its own lightweight open-PR count fetch. A full first page (>= 100) reports a floor ("100+"); otherwise the exact count. It must NOT reuse the work-start probe's `truncated` boolean.

**Files:**
- Modify: `src/teamctx/onboard.py`
- Test: `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add; reuse the _Resp/_opener_returning helper style from test_gate_status.py)
import json
from teamctx.onboard import GithubOnboarder, HealthReport


class _Resp:
    def __init__(self, body: bytes) -> None:
        self._b = body
    def read(self) -> bytes:
        return self._b
    def __enter__(self):  # type: ignore[no-untyped-def]
        return self
    def __exit__(self, *a: object) -> None:
        return None


def _opener_returning(payload: object):  # type: ignore[no-untyped-def]
    return lambda request: _Resp(json.dumps(payload).encode())


def test_verify_health_exact_count() -> None:
    report = GithubOnboarder().verify_health(
        "acme/widgets", token="t", opener=_opener_returning([{"number": 1}, {"number": 2}])
    )
    assert report.reachable is True
    assert report.open_pr_count == 2 and report.count_is_floor is False
    assert "2 open" in report.message


def test_verify_health_full_page_is_a_floor() -> None:
    report = GithubOnboarder().verify_health(
        "acme/widgets", token="t", opener=_opener_returning([{"number": i} for i in range(100)])
    )
    assert report.count_is_floor is True
    assert "100+" in report.message or "at least 100" in report.message


def test_verify_health_unreachable_is_honest_not_a_verdict() -> None:
    report = GithubOnboarder().verify_health("acme/widgets", token=None, opener=_opener_returning([]))
    assert report.reachable is False
    assert "couldn't reach" in report.message.lower() or "no credential" in report.message.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k verify_health -v`
Expected: FAIL (`verify_health` / `HealthReport` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/onboard.py` (reuse the existing GitHub HTTP plumbing so there is one way to call the API):

```python
from urllib.parse import quote

from teamctx.connectors.github import DEFAULT_OPENER, GITHUB_API_ROOT, GitHubProbeError, HttpOpener, get_json, split_repo


@dataclass(frozen=True)
class HealthReport:
    reachable: bool
    open_pr_count: int | None
    count_is_floor: bool
    message: str
```

Add the method to `GithubOnboarder`:

```python
    def verify_health(
        self, repo: str, *, token: str | None, opener: HttpOpener = DEFAULT_OPENER
    ) -> HealthReport:
        """A live reachability check, never a verdict: count open PRs off the first page. A full
        page (>= 100) is reported as a floor, so the number is never a false exact count."""

        if not token:
            return HealthReport(False, None, False, "no credential, so I couldn't reach GitHub to count open PRs.")
        owner, name = split_repo(repo)
        url = f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}/pulls?state=open&per_page=100"
        try:
            payload = get_json(url, token=token, opener=opener)
        except GitHubProbeError:
            return HealthReport(False, None, False, "couldn't reach GitHub just now (transient or access); teamctx will say so, never a false all-clear.")
        if not isinstance(payload, list):
            return HealthReport(False, None, False, "GitHub returned an unexpected shape for open PRs; reporting it as unreachable rather than guessing.")
        count = len(payload)
        floor = count >= 100
        if floor:
            return HealthReport(True, count, True, "reached GitHub: at least 100 open PRs (100+).")
        return HealthReport(True, count, False, f"reached GitHub: {count} open PRs.")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_onboard.py -k verify_health -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/onboard.py tests/test_onboard.py
git commit -m "feat(onboard): count-honest verify_health (floor vs exact open-PR count)"
```

---

## Task 7: `ensure_config_trackable` (spec 2.3, user-repo part)

onboard writes or patches the user repo's root `.gitignore` so `.teamctx/config.json` is trackable, then verifies with `git check-ignore --no-index` (exit 1 = not ignored = trackable). Idempotent.

**Files:**
- Modify: `src/teamctx/onboard.py`
- Test: `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add)
from teamctx.onboard import ensure_config_trackable


def _git_init(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)


def test_ensure_trackable_patches_a_blanket_ignore(tmp_path: Path) -> None:
    _git_init(tmp_path)
    (tmp_path / ".gitignore").write_text(".teamctx/\n", encoding="utf-8")
    step = ensure_config_trackable(tmp_path, dry_run=False)
    assert step.status in {"wrote", "already"}
    check = subprocess.run(
        ["git", "-C", str(tmp_path), "check-ignore", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    )
    assert check.returncode == 1  # not ignored -> trackable


def test_ensure_trackable_is_idempotent(tmp_path: Path) -> None:
    _git_init(tmp_path)
    ensure_config_trackable(tmp_path, dry_run=False)
    second = ensure_config_trackable(tmp_path, dry_run=False)
    assert second.status == "already"


def test_ensure_trackable_dry_run_writes_nothing(tmp_path: Path) -> None:
    _git_init(tmp_path)
    before = (tmp_path / ".gitignore").exists()
    step = ensure_config_trackable(tmp_path, dry_run=True)
    assert step.status == "skipped"
    assert (tmp_path / ".gitignore").exists() == before
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k ensure_trackable -v`
Expected: FAIL (`ensure_config_trackable` / `StepResult` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/onboard.py`:

```python
import subprocess
from typing import Literal

_TRACKABLE_LINES = ("\n# teamctx (config is tracked; local state is not)\n", ".teamctx/*\n", "!.teamctx/config.json\n")


@dataclass(frozen=True)
class StepResult:
    name: str
    status: Literal["wrote", "already", "skipped", "failed"]
    detail: str


def _config_is_trackable(root: Path) -> bool:
    # git check-ignore exits 1 when the path is NOT ignored (i.e. trackable), 0 when ignored.
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    )
    return result.returncode == 1


def ensure_config_trackable(root: Path, *, dry_run: bool) -> StepResult:
    if _config_is_trackable(root):
        return StepResult("gitignore", "already", ".teamctx/config.json is already trackable.")
    if dry_run:
        return StepResult("gitignore", "skipped", "--dry-run: would patch .gitignore to track .teamctx/config.json.")
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    _atomic_write(gitignore, existing + "".join(_TRACKABLE_LINES))
    if not _config_is_trackable(root):
        return StepResult("gitignore", "failed", "patched .gitignore but .teamctx/config.json is still ignored; check for a broader ignore rule.")
    return StepResult("gitignore", "wrote", "patched .gitignore so .teamctx/config.json is trackable.")
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_onboard.py -k ensure_trackable -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/onboard.py tests/test_onboard.py
git commit -m "feat(onboard): ensure_config_trackable patches .gitignore, verified by git check-ignore"
```

---

## Task 8: Migration-safe CLAUDE.md snippet upsert (spec 2.4)

Write the snippet wrapped in paired markers and update in place between them (idempotent). Migrate an old unmarked block only on a confident match of the known legacy body; if the heading is present but the body was edited, leave it and warn.

**Files:**
- Modify: `src/teamctx/onboard.py`
- Test: `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add)
from teamctx.onboard import _LEGACY_SNIPPET_BODY, upsert_claude_md_snippet

_START = "<!-- teamctx:start -->"
_END = "<!-- teamctx:end -->"


def test_snippet_fresh_write_wraps_in_markers(tmp_path: Path) -> None:
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "wrote"
    assert _START in text and _END in text
    assert "failing checks" in text and "changed specs" not in text


def test_snippet_upsert_is_idempotent(tmp_path: Path) -> None:
    upsert_claude_md_snippet(tmp_path, dry_run=False)
    first = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    assert step.status == "already"
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == first
    assert first.count(_START) == 1  # not duplicated


def test_snippet_migrates_unedited_legacy_block(tmp_path: Path) -> None:
    (tmp_path / "CLAUDE.md").write_text("# Project\n\n" + _LEGACY_SNIPPET_BODY + "\n## Other\n", encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "wrote"
    assert "changed specs" not in text  # legacy body replaced
    assert _START in text and text.count("## Team context (teamctx)") == 1
    assert "## Other" in text  # adjacent content preserved


def test_snippet_warns_not_deletes_edited_legacy_block(tmp_path: Path) -> None:
    edited = "## Team context (teamctx)\nMy own custom teamctx note that I edited.\n"
    (tmp_path / "CLAUDE.md").write_text("# Project\n\n" + edited + "\n## Other\n", encoding="utf-8")
    step = upsert_claude_md_snippet(tmp_path, dry_run=False)
    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert step.status == "skipped"  # did not touch an edited block
    assert "My own custom teamctx note" in text  # user content preserved
    assert "remove" in step.detail.lower()  # tells the user what to do
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k snippet -v`
Expected: FAIL (`upsert_claude_md_snippet` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/onboard.py`:

```python
_SNIPPET_START = "<!-- teamctx:start -->"
_SNIPPET_END = "<!-- teamctx:end -->"
_SNIPPET_HEADING = "## Team context (teamctx)"


def _marked_block() -> str:
    return f"{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_END}\n"


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def upsert_claude_md_snippet(root: Path, *, dry_run: bool) -> StepResult:
    path = root / "CLAUDE.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = _marked_block()

    # 1. Marked block already present -> update in place (exact span between the markers).
    if _SNIPPET_START in existing and _SNIPPET_END in existing:
        start = existing.index(_SNIPPET_START)
        end = existing.index(_SNIPPET_END) + len(_SNIPPET_END)
        current = existing[start:end] + "\n"
        if current.strip() == block.strip():
            return StepResult("claude_md", "already", "CLAUDE.md snippet already current.")
        if dry_run:
            return StepResult("claude_md", "skipped", "--dry-run: would refresh the CLAUDE.md snippet.")
        new_text = existing[:start] + block.rstrip("\n") + existing[end:]
        _atomic_write(path, new_text)
        return StepResult("claude_md", "wrote", "refreshed the CLAUDE.md snippet in place.")

    # 2. Unmarked legacy block, unedited -> migrate exactly that span.
    if _normalize_ws(_LEGACY_SNIPPET_BODY) in _normalize_ws(existing):
        if dry_run:
            return StepResult("claude_md", "skipped", "--dry-run: would migrate the old CLAUDE.md snippet.")
        new_text = _replace_normalized_span(existing, _LEGACY_SNIPPET_BODY, block.rstrip("\n"))
        _atomic_write(path, new_text)
        return StepResult("claude_md", "wrote", "migrated the old CLAUDE.md snippet to the marked, honest block.")

    # 3. Heading present but body edited -> never auto-replace; warn.
    if _SNIPPET_HEADING in existing:
        return StepResult(
            "claude_md", "skipped",
            "found an edited '## Team context (teamctx)' block in CLAUDE.md; left it untouched. "
            "Remove that block by hand and re-run so teamctx can manage a marked one.",
        )

    # 4. No teamctx block -> append.
    if dry_run:
        return StepResult("claude_md", "skipped", "--dry-run: would add the CLAUDE.md snippet.")
    prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
    joiner = "" if prefix == "" else "\n"
    _atomic_write(path, prefix + joiner + block)
    return StepResult("claude_md", "wrote", "added the teamctx snippet to CLAUDE.md.")
```

Add the exact-span replacer (matches the legacy body allowing whitespace differences, and replaces exactly that run of lines, never a guessed boundary):

```python
def _replace_normalized_span(text: str, legacy: str, replacement: str) -> str:
    """Replace the first run of lines whose whitespace-normalized form equals the legacy body's,
    with ``replacement``. Line-based so adjacent user content is never touched."""

    lines = text.splitlines(keepends=True)
    target = _normalize_ws(legacy)
    n = len(legacy.splitlines())
    for i in range(len(lines) - n + 1):
        window = "".join(lines[i : i + n])
        if _normalize_ws(window) == target:
            return "".join(lines[:i]) + replacement + ("\n" if not replacement.endswith("\n") else "") + "".join(lines[i + n :])
    return text  # no confident match (should not happen: caller already checked containment)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_onboard.py -k snippet -v`
Expected: PASS. If the migration span test is off by a trailing newline, adjust `_replace_normalized_span`'s join, not the assertion.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/onboard.py tests/test_onboard.py
git commit -m "feat(onboard): marker-based, migration-safe CLAUDE.md snippet upsert"
```

---

## Task 9: The onboard flow (spec 2.2)

Compose the steps into `run_onboard`, returning an `OnboardResult`. Resolve/validate the repo (detect or `--repo`); write config atomically (respecting `--force` and `--dry-run`); ensure trackable; report auth; install the hook; upsert the snippet; verify health. Additive and idempotent; a missing token does not abort.

**Files:**
- Modify: `src/teamctx/onboard.py`
- Test: `tests/test_onboard.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard.py  (add)
from teamctx.onboard import run_onboard


def _repo_with_github_origin(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"], check=True)


def test_run_onboard_happy_path_writes_everything(tmp_path: Path, monkeypatch) -> None:
    _repo_with_github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    result = run_onboard(tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([]))
    assert result.ok is True
    assert (tmp_path / ".teamctx" / "config.json").exists()
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count("<!-- teamctx:start -->") == 1
    names = {s.name for s in result.steps}
    assert {"config", "gitignore", "auth", "hook", "claude_md", "health"} <= names


def test_run_onboard_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    _repo_with_github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    result = run_onboard(tmp_path, repo_override=None, force=False, dry_run=True, opener=_opener_returning([]))
    assert not (tmp_path / ".teamctx" / "config.json").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert all(s.status in {"skipped", "already", "failed"} for s in result.steps if s.name in {"config", "gitignore", "claude_md", "hook"})


def test_run_onboard_no_repo_stops_writing_nothing(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)  # no origin
    result = run_onboard(tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([]))
    assert result.ok is False
    assert not (tmp_path / ".teamctx").exists()
    assert "repo" in result.steps[0].detail.lower()


def test_run_onboard_existing_config_needs_force(tmp_path: Path, monkeypatch) -> None:
    _repo_with_github_origin(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    run_onboard(tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([]))
    again = run_onboard(tmp_path, repo_override=None, force=False, dry_run=False, opener=_opener_returning([]))
    config_step = next(s for s in again.steps if s.name == "config")
    assert config_step.status == "already" and "force" in config_step.detail.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard.py -k run_onboard -v`
Expected: FAIL (`run_onboard` / `OnboardResult` not defined).

- [ ] **Step 3: Implement**

In `src/teamctx/onboard.py`:

```python
import json as _json

from teamctx.git_context import parse_github_repo
from teamctx.project_config import build_work_start_project_config


@dataclass(frozen=True)
class OnboardResult:
    ok: bool
    steps: tuple[StepResult, ...]
    next_step: str


def _resolve_repo(root: Path, repo_override: str | None) -> str | None:
    if repo_override is not None:
        return parse_github_repo(repo_override)  # None if not a github owner/name
    return ONBOARDERS[0].detect(root)


def _write_config_step(root: Path, repo: str, *, force: bool, dry_run: bool) -> StepResult:
    path = root / ".teamctx" / "config.json"
    if path.exists() and not force:
        return StepResult("config", "already", f"{path} exists; pass --force to overwrite.")
    if dry_run:
        return StepResult("config", "skipped", "--dry-run: would write .teamctx/config.json.")
    config = build_work_start_project_config(repo=repo)
    _atomic_write(path, _json.dumps(config.model_dump(mode="json", exclude_defaults=True), indent=2) + "\n")
    return StepResult("config", "wrote", str(path))


def _install_hook_step(root: Path, *, dry_run: bool) -> StepResult:
    from teamctx.cli import install_hook_into_settings  # local import: cli imports onboard

    settings_path = root / ".claude" / "settings.json"
    if dry_run:
        return StepResult("hook", "skipped", "--dry-run: would install the PreToolUse reflex hook.")
    try:
        wrote = install_hook_into_settings(settings_path)
    except Exception as exc:  # a malformed settings file: fail only this step, keep going
        return StepResult("hook", "failed", f"could not update {settings_path}: {exc}")
    return StepResult("hook", "wrote" if wrote else "already", str(settings_path))


def run_onboard(
    root: Path,
    *,
    repo_override: str | None,
    force: bool,
    dry_run: bool,
    token_env: str = "GITHUB_TOKEN",
    opener: HttpOpener = DEFAULT_OPENER,
) -> OnboardResult:
    repo = _resolve_repo(root, repo_override)
    if repo is None:
        detail = (
            "could not determine a GitHub repo: this is not a git repo with a github.com 'origin', "
            "and no --repo was given. Re-run with --repo owner/name."
        )
        return OnboardResult(False, (StepResult("detect", "failed", detail),), "re-run with --repo owner/name")

    onboarder = ONBOARDERS[0]
    steps: list[StepResult] = [_write_config_step(root, repo, force=force, dry_run=dry_run)]
    steps.append(ensure_config_trackable(root, dry_run=dry_run))
    auth = onboarder.auth_status(token_env)
    steps.append(StepResult("auth", "already" if auth.found else "skipped", auth.message))
    steps.append(_install_hook_step(root, dry_run=dry_run))
    steps.append(upsert_claude_md_snippet(root, dry_run=dry_run))
    token = resolve_github_token(token_env)
    health = onboarder.verify_health(repo, token=token, opener=opener)
    steps.append(StepResult("health", "already" if health.reachable else "skipped", health.message))

    next_step = (
        "Run `teamctx work-start --path <a file you're about to edit>` to see it work."
        if auth.found
        else "Set a GitHub credential (see the auth line above), then run `teamctx work-start`."
    )
    return OnboardResult(True, tuple(steps), next_step)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_onboard.py -v && python -m mypy src`
Expected: PASS, mypy clean. If mypy flags the `cli` import cycle, the local (function-scoped) import in `_install_hook_step` breaks it; keep it local.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/onboard.py tests/test_onboard.py
git commit -m "feat(onboard): the onboard flow (detect, config, gitignore, auth, hook, snippet, health)"
```

---

## Task 10: The `onboard` CLI command (spec 2.2)

A thin command: resolve the root, call `run_onboard`, render the "what changed" summary + the single next step. Exit non-zero when the flow could not proceed (`ok is False`).

**Files:**
- Modify: `src/teamctx/cli.py`
- Test: `tests/test_onboard_cli.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_onboard_cli.py
from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main


def _github_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", "git@github.com:acme/widgets.git"], check=True)


def test_onboard_happy_path(tmp_path: Path, monkeypatch) -> None:
    _github_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    result = CliRunner().invoke(main, ["onboard"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert (tmp_path / ".teamctx" / "config.json").exists()
    assert "acme/widgets" in result.output
    assert "work-start" in result.output  # the next step


def test_onboard_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    _github_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["onboard", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert not (tmp_path / ".teamctx").exists()
    assert "dry-run" in result.output.lower() or "would" in result.output.lower()


def test_onboard_non_github_repo_errors_with_fix(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)  # no origin
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["onboard"])
    assert result.exit_code != 0
    assert "--repo" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_onboard_cli.py -v`
Expected: FAIL (no `onboard` command).

- [ ] **Step 3: Implement**

In `src/teamctx/cli.py`, add the command (near `install-hook`):

```python
from teamctx.onboard import run_onboard

_STEP_MARK = {"wrote": "wrote", "already": "already set", "skipped": "skipped", "failed": "FAILED"}


@main.command("onboard")
@click.option("--repo", "repo", default=None, help="GitHub repo owner/name. Overrides git 'origin' detection.")
@click.option("--force", is_flag=True, help="Overwrite an existing .teamctx/config.json.")
@click.option("--dry-run", "dry_run", is_flag=True, help="Preview every step; write nothing.")
@click.option("--yes", is_flag=True, help="Assume non-interactive (accepted; onboard does not prompt today).")
def onboard_command(repo: str | None, force: bool, dry_run: bool, yes: bool) -> None:
    """Set up teamctx in this repo: config, reflex hook, CLAUDE.md snippet, and an honest
    credential + reachability report. Idempotent; re-run any time."""

    root = resolve_project_root()
    result = run_onboard(root, repo_override=repo, force=force, dry_run=dry_run)
    click.echo("teamctx onboard:" + (" (dry run, nothing written)" if dry_run else ""))
    for step in result.steps:
        click.echo(f"  [{_STEP_MARK[step.status]}] {step.name}: {step.detail}")
    click.echo(f"\nNext: {result.next_step}")
    if not result.ok:
        raise SystemExit(1)
```

- [ ] **Step 4: Run tests + live check**

Run: `python -m pytest tests/test_onboard_cli.py -v`
Expected: PASS. Then a live smoke test in a scratch repo:
`cd $(mktemp -d) && git init -q && git remote add origin git@github.com:acme/widgets.git && TEAMCTX_DISABLE_GH_AUTH=1 python -m teamctx.cli onboard --dry-run` and confirm the summary reads honestly.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_onboard_cli.py
git commit -m "feat(cli): onboard command (what-changed summary + honest next step)"
```

---

## Task 11: Full-suite gate + codex diff-review + merge

- [ ] **Step 1: Full gate**

Run: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src`
Expected: all green.

- [ ] **Step 2: Em-dash ship gate**

Run: `grep -rnP "\x{2014}" src tests README.md CHANGELOG.md docs/superpowers/plans/2026-07-01-onboard-command-phase3.md || echo clean`
Expected: clean (the only allowed hits are the pre-existing em-dash-guard assertions in test_why_open_source_cli.py).

- [ ] **Step 3: CHANGELOG**

Add an Added entry under `[Unreleased]`: the `teamctx onboard` command (detect + trackable config + reflex hook + honest CLAUDE.md snippet + credential/reachability report; idempotent, atomic, `--dry-run`/`--force`/`--repo`). No em dashes.

- [ ] **Step 4: codex adversarial diff-review before merge**

Diff `main..HEAD`, hand it plus spec 2.x to codex (`codex exec --dangerously-bypass-approvals-and-sandbox - < brief > out 2>&1`, backgrounded, ANSI-stripped tail). Focus: any write that is not atomic or not idempotent; the snippet migration deleting user content; the gitignore patch failing on an odd existing ignore; verify_health emitting a verdict or a false exact count; `--dry-run` writing anything; the cli/onboard import cycle. Verify each finding against code as CTO-arbiter; fix real ones (re-gate); re-review the fix diff if needed.

- [ ] **Step 5: Merge + push, mark done**

Per the finish-branch rule: `git switch main && git merge --no-ff feat/onboard-command -m "..."`, push, then mark the onboard slice done in `docs/product/plan/CURRENT.md` (the whole onboard + runtime-honesty slice is then complete; next slice is auto-discovery).

---

## Self-review (against spec 2.1 to 2.5)

- **2.1 seam:** `GithubOnboarder` with `detect` (Task 4), `propose_config` (Task 4), `auth_status` (Task 5), `verify_health` (Task 6); `ONBOARDERS` list, no ABC. Covered.
- **2.2 flow:** `run_onboard` does resolve/detect -> config (atomic, --force) -> trackable -> auth report -> hook (reused) -> snippet -> verify_health -> structured summary + next step; flags `--repo/--force/--dry-run/--yes` (Tasks 9, 10). Transaction model (additive, idempotent, per-step failure isolated, missing token does not abort) covered by `_install_hook_step`'s try/except and the step statuses. Covered.
- **2.3 gitignore:** repo `.gitignore` fixed (Task 1); `ensure_config_trackable` patches the user repo + verifies with `git check-ignore --no-index` (Task 7). Covered.
- **2.4 snippet:** honest copy (Task 2); marker wrap + in-place update + legacy migration + warn-not-delete on an edited block (Task 8). Covered.
- **2.5 verify_health:** own open-PR count fetch, floor vs exact, never the work-start `truncated` boolean, never a verdict (Task 6). Covered.
- **Deferred (not built), on merit:** `--with-mcp`, `--global`, docs auto-enable. Named in the command help / plan, not silently dropped.
- **Type consistency:** `StepResult(name,status,detail)`, `OnboardResult(ok,steps,next_step)`, `AuthStatus(found,source,message)`, `HealthReport(reachable,open_pr_count,count_is_floor,message)` used consistently across Tasks 5 to 10.
- **Open question for Edgar:** `--yes` has no behavior today (onboard is non-interactive); included as a reserved flag per the spec. Drop or keep?
