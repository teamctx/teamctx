# S3: Real `teamctx status` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the lying `status` stub (cli.py:64 prints fixed fiction) with the read-only twin of onboard's report: config, trackability, hook, snippet, credential, reachability, all through the SAME functions onboard uses, so status can never disagree with onboard or with runtime.

**Architecture:** A `run_status(root, ...)` flow in `src/teamctx/onboard.py` (status is onboard's read-only twin; they share private helpers, so they live together) returning the existing `StepResult` shape with a new `"ok"` status mark. The CLAUDE.md snippet classification is extracted from `upsert_claude_md_snippet` into one shared read-only classifier used by BOTH upsert and status (no second classifier, ever). `status` writes nothing and always exits 0: it is a report, never a judge.

**Tech Stack:** Python 3.12, pytest, click. Gate: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` plus `grep -rP '\x{2014}' src tests` empty.

**Branch:** work in a separate worktree: `git worktree add ../teamctx-s3 -b feat/status-real main` and do everything inside `../teamctx-s3`. Do NOT touch README.md, contract_render.py, or anything outside onboard.py, cli.py, CHANGELOG.md, and tests.

**Spec:** `docs/superpowers/specs/2026-07-03-full-review-findings.md` finding F2 (binding).

---

### Task 1: Extract the shared CLAUDE.md snippet classifier

**Files:**
- Modify: `src/teamctx/onboard.py` (upsert_claude_md_snippet, ~line 260)
- Test: `tests/test_status.py` (create)

`upsert_claude_md_snippet` currently interleaves classification and writing. Extract the classification into one pure function both callers share:

```python
SnippetState = Literal["current", "outdated", "edited", "conflicted_markers", "legacy", "edited_heading", "absent"]


def classify_claude_md(existing: str) -> SnippetState:
    """Classify the teamctx snippet state in a CLAUDE.md text. The ONE classifier used by
    upsert (to decide the write) and status (to report), so they can never disagree.
    current = marked block, body is the current snippet. outdated = marked block, body is a
    known generated body that is not current. edited = marked block, hand-edited body.
    conflicted_markers = markers present but not a single clean pair. legacy = exactly one
    unmarked legacy body. edited_heading = the heading exists but nothing above matched.
    absent = no trace."""
    lines = existing.splitlines(keepends=True)
    span = _marker_span(lines)
    if span is None and (_SNIPPET_START in existing or _SNIPPET_END in existing):
        return "conflicted_markers"
    if span is not None:
        start_i, end_i = span
        body = "".join(lines[start_i + 1 : end_i])
        if _normalize_ws(body) == _normalize_ws(CLAUDE_MD_SNIPPET):
            return "current"
        if _normalize_ws(body) in {_normalize_ws(b) for b in _KNOWN_BODIES}:
            return "outdated"
        return "edited"
    if existing.count(_LEGACY_SNIPPET_BODY) == 1:
        return "legacy"
    if _SNIPPET_HEADING in existing:
        return "edited_heading"
    return "absent"
```

- [ ] **Step 1: Write failing tests** in `tests/test_status.py` covering all seven states (build each `existing` string from the module constants `_SNIPPET_START`/`_SNIPPET_END`/`CLAUDE_MD_SNIPPET`/`_LEGACY_SNIPPET_BODY`/`_SNIPPET_HEADING`, plus an edited-body variant and a double-start-marker variant).
- [ ] **Step 2: Verify they fail** (ImportError). **Step 3: Implement** `classify_claude_md`, then rewrite `upsert_claude_md_snippet` to branch on it (behavior identical; every existing upsert test in `tests/test_onboard.py` must pass unchanged; if one fails, the refactor is wrong, not the test).
- [ ] **Step 4: Full gate.** **Step 5: Commit** `refactor(onboard): one shared CLAUDE.md snippet classifier (upsert + status)`

---

### Task 2: run_status

**Files:**
- Modify: `src/teamctx/onboard.py` (add at the end)
- Test: `tests/test_status.py` (extend)

```python
@dataclass(frozen=True)
class StatusReport:
    steps: tuple[StepResult, ...]
    next_step: str


def run_status(
    root: Path,
    *,
    token_env: str = "GITHUB_TOKEN",
    opener: HttpOpener = DEFAULT_OPENER,
) -> StatusReport:
    """The read-only twin of run_onboard: report exactly what onboard would find, through the
    same resolvers, writing nothing. Never a verdict; reachability is a live check, not a health
    judgment."""

    config_path = root / ".teamctx" / "config.json"
    existing, config_error = _load_existing_config(config_path)
    detected = detect_repo(root)

    steps: list[StepResult] = []
    effective_repo: str | None = None
    if config_error is not None:
        steps.append(StepResult(
            "config", "failed",
            f"{config_path} exists but is not valid teamctx config ({config_error}).",
        ))
    elif existing is not None:
        config_raw = existing.work_start.repo if existing.work_start is not None else None
        effective_repo, repo_error = resolve_github_repo(None, config_raw, detected)
        if repo_error is not None:
            steps.append(StepResult(
                "config", "failed",
                f"{config_path} configures a repo work-start can't use: {repo_error}",
            ))
        elif config_raw:
            steps.append(StepResult(
                "config", "ok", f"{config_path} configures {effective_repo}."
            ))
        else:
            steps.append(StepResult(
                "config", "ok",
                f"{config_path} exists with no repo set; work-start will use the git origin "
                f"{effective_repo}.",
            ))
    else:
        effective_repo, repo_error = resolve_github_repo(None, None, detected)
        if effective_repo is not None:
            steps.append(StepResult(
                "config", "noted",
                f"no {config_path}; work-start will use the git origin {effective_repo}. "
                "Run `teamctx onboard` to make it explicit and shareable.",
            ))
        else:
            steps.append(StepResult(
                "config", "noted",
                f"no {config_path} and no git origin to detect a repo from. "
                "Run `teamctx onboard --repo owner/name`.",
            ))

    if not _is_git_repo(root):
        steps.append(StepResult("tracking", "noted", "not a git repo; nothing to track."))
    elif _config_is_trackable(root):
        steps.append(StepResult("tracking", "ok", ".teamctx/config.json is trackable in git."))
    else:
        steps.append(StepResult(
            "tracking", "noted",
            ".teamctx/config.json is ignored by .gitignore; `teamctx onboard` can fix that.",
        ))

    settings_path = root / ".claude" / "settings.json"
    steps.append(_hook_status_step(settings_path))

    claude_md = root / "CLAUDE.md"
    existing_text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    steps.append(_snippet_status_step(classify_claude_md(existing_text)))

    token, source = resolve_github_token_with_source(token_env)
    auth_found = token is not None
    steps.append(StepResult(
        "credential", "ok" if auth_found else "noted",
        _auth_found_message(token_env, source) if auth_found else _auth_missing_message(token_env),
    ))

    if effective_repo is not None:
        health = ONBOARDERS[0].verify_health(effective_repo, token=token, opener=opener)
        steps.append(StepResult("reachability", "noted", health.message))
    else:
        steps.append(StepResult(
            "reachability", "noted", "no valid repo resolved, so no reachability check was run."
        ))

    return StatusReport(tuple(steps), _status_next_step(steps, auth_found))
```

Helpers (same file):

```python
def _hook_status_step(settings_path: Path) -> StepResult:
    from teamctx.cli import _has_hook_entry, _load_settings  # local: break the cli<->onboard cycle

    try:
        settings = _load_settings(settings_path)
    except Exception:
        return StepResult(
            "hook", "noted", f"couldn't read {settings_path}; can't tell if the hook is installed."
        )
    if _has_hook_entry(settings):
        return StepResult("hook", "ok", f"the reflex hook is installed in {settings_path}.")
    return StepResult(
        "hook", "noted",
        f"the reflex hook is not installed in {settings_path}; `teamctx onboard` installs it.",
    )


_SNIPPET_STATUS_DETAIL: dict[SnippetState, tuple[str, str]] = {
    "current": ("ok", "the CLAUDE.md snippet is current."),
    "outdated": ("noted", "the CLAUDE.md snippet is outdated; `teamctx onboard` refreshes it."),
    "edited": ("noted", "the teamctx block in CLAUDE.md was hand-edited; teamctx leaves it to you."),
    "conflicted_markers": (
        "noted",
        "CLAUDE.md has teamctx markers that aren't a clean single start/end pair; fix or remove "
        "them by hand.",
    ),
    "legacy": ("noted", "CLAUDE.md has the old unmarked snippet; `teamctx onboard` migrates it."),
    "edited_heading": (
        "noted", "CLAUDE.md has an edited '## Team context (teamctx)' block; teamctx leaves it to you."
    ),
    "absent": ("noted", "no teamctx snippet in CLAUDE.md; `teamctx onboard` adds it."),
}


def _snippet_status_step(state: SnippetState) -> StepResult:
    mark, detail = _SNIPPET_STATUS_DETAIL[state]
    return StepResult("claude_md", mark, detail)  # type: ignore[arg-type]


def _status_next_step(steps: list[StepResult], auth_found: bool) -> str:
    if any(s.status == "failed" for s in steps):
        return "Fix the failed line above (or run `teamctx onboard --force`)."
    if any(s.name in {"config", "hook", "claude_md"} and s.status == "noted" for s in steps):
        return "Run `teamctx onboard` to finish setup."
    if not auth_found:
        return "Set a GitHub credential (see the credential line above)."
    return "You're set. Run `teamctx work-start --path <a file you're about to edit>`."
```

Note: `StepResult.status` gains the literal `"ok"`: extend its `Literal[...]` in place (`"wrote", "already", "skipped", "failed", "noted", "ok"`), and if mypy then flags the `type: ignore` above as unused, drop the ignore.

- [ ] **Step 1: Failing tests** (extend `tests/test_status.py`): fresh tmp dir with no git (config noted + "onboard", tracking "not a git repo", reachability skipped); a dir where you first run `run_onboard` with a fake opener then `run_status` with the same opener (every step "ok" except credential per env, and reachability message matches onboard's); an invalid config json (config failed + next_step names the fix); conftest already clears tokens, so the credential line is the missing-credential message unless a test sets `GITHUB_TOKEN`. Use the fake-opener pattern from `tests/test_onboard.py`.
- [ ] **Step 2: fail** → **Step 3: implement** → **Step 4: full gate** → **Step 5: Commit** `feat(onboard): run_status, the read-only twin of onboard`

---

### Task 3: Wire the CLI

**Files:**
- Modify: `src/teamctx/cli.py` (replace the stub at ~line 64)
- Test: `tests/test_status.py` (extend with CliRunner tests)

```python
@main.command()
@click.option(
    "--token-env", default="GITHUB_TOKEN", show_default=True,
    help="Name of the env var holding the GitHub token.",
)
def status(token_env: str) -> None:
    """Report teamctx setup in this repo, read-only: config, hook, snippet, credential, and
    a live reachability check. Writes nothing; never a verdict."""

    from teamctx.onboard import run_status

    root = resolve_project_root()
    report = run_status(root, token_env=token_env)
    click.echo(f"teamctx status for {root}:")
    for step in report.steps:
        click.echo(f"  [{_STEP_MARK[step.status]}] {step.name}: {step.detail}")
    click.echo(f"\nNext: {report.next_step}")
```

`_STEP_MARK` gains `"ok": "ok"`. Exit code is always 0 (a report, never a judge). The old stub text ("teamctx is initialized. No sources are configured yet.") must not survive anywhere.

- [ ] **Step 1: Failing CliRunner tests**: `teamctx status` in a scaffolded tmp repo shows the config repo and exits 0; in an empty dir it recommends onboard and exits 0; the stub sentence is asserted absent.
- [ ] **Step 2: fail** → **Step 3: implement** → **Step 4: full gate** → **Step 5: Commit** `feat(cli): real status command (read-only onboard twin)`

---

### Task 4: CHANGELOG + final sweep

- [ ] Add to CHANGELOG.md under the unreleased section: `- teamctx status now reports real setup state (config, hook, snippet, credential, live reachability) through the same resolvers onboard uses; the old placeholder text is gone.`
- [ ] Run the full gate + `grep -rP '\x{2014}' src tests` (must be empty). `grep -rn "No sources are configured" src tests` must be empty.
- [ ] Commit `docs(changelog): real status command`

---

## Completion

Stop after the last commit. Do NOT merge, do NOT push, do NOT remove the worktree. Report: branch, commits (oneline), gate tail, files changed, deviations with reasons. The CTO reviews and merges.
