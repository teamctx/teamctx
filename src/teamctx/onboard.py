"""The onboard command: scaffold a repo for teamctx honestly, over the Part 1 resolvers.

A minimal source-onboarder seam (one GithubOnboarder today, in a plain list) plus the flow that
writes a trackable config, installs the reflex hook, writes an honest CLAUDE.md snippet, reports the
real credential path, and prints a live reachability check. Every write is atomic and idempotent;
the flow returns structured results the CLI renders. No LLM, no verdicts here.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from teamctx.connectors.github import (
    DEFAULT_OPENER,
    GITHUB_API_ROOT,
    GitHubProbeError,
    HttpOpener,
    get_json,
    split_repo,
)
from teamctx.git_context import detect_repo, parse_github_repo
from teamctx.project_config import (
    ProjectConfig,
    ProjectConfigError,
    build_work_start_project_config,
    load_project_config,
)
from teamctx.resolve import resolve_github_repo
from teamctx.tokens import resolve_github_token_with_source

# The honest snippet: all four checks, with the two conditional ones stating their conditions
# (criteria fires when an issue is derivable or named; docs when a docs folder is configured).
CLAUDE_MD_SNIPPET = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open pull requests touching your files, failing checks on your "
    "branch, acceptance criteria that changed when an issue is linked from your branch or "
    "commits, and superseded docs when a docs folder is configured. Tell your human collaborator "
    "anything relevant in plain terms so they can decide.\n"
)

# The two-check snippet body written between Phase 3 and the auto-discovery slice, kept verbatim
# so the upsert recognizes and refreshes an unedited managed block. Never used for new writes.
_SNIPPET_BODY_2026_07 = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open pull requests touching your files and failing checks on your "
    "branch. Tell your human collaborator anything relevant in plain terms so they can decide.\n"
)

# The pre-Phase-3 snippet body, kept verbatim so the upsert can recognize and migrate an old
# unmarked block the user has NOT edited. Never used for new writes.
_LEGACY_SNIPPET_BODY = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan. It surfaces open PRs touching your files, failing checks, changed specs, and "
    "superseded docs. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)


def _atomic_write(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically: a temp file in the same directory, then rename. A
    crash mid-write never leaves a half-written file at ``path``. The temp file is on the same
    filesystem as the target (``dir=path.parent``), so ``os.replace`` is atomic."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


@dataclass(frozen=True)
class AuthStatus:
    found: bool
    source: str | None
    message: str


@dataclass(frozen=True)
class HealthReport:
    reachable: bool
    open_pr_count: int | None
    count_is_floor: bool
    message: str


StepStatus = Literal["wrote", "already", "skipped", "failed", "noted", "ok"]


@dataclass(frozen=True)
class StepResult:
    name: str
    status: StepStatus
    detail: str


# Un-ignore the .teamctx directory first (git can't re-include a file whose parent dir is ignored),
# then re-ignore its contents, then re-include config.json. Overrides a blanket `.teamctx/` rule.
_TRACKABLE_STANZA = (
    "# teamctx (config is tracked; local state is not)\n"
    "!.teamctx/\n"
    ".teamctx/*\n"
    "!.teamctx/config.json\n"
)


def _is_git_repo(root: Path) -> bool:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        capture_output=True, text=True,
    ).returncode == 0


def _config_is_trackable(root: Path) -> bool:
    # git check-ignore exits 1 when the path is NOT ignored (i.e. trackable), 0 when ignored.
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    )
    return result.returncode == 1


def ensure_config_trackable(root: Path, *, dry_run: bool) -> StepResult:
    """Make .teamctx/config.json trackable in the user repo, idempotently, verified by
    git check-ignore. In a non-git tree there is nothing to track (git check-ignore errors), so it
    is skipped, not failed, matching that work-start still works from config alone."""

    if not _is_git_repo(root):
        return StepResult(
            "gitignore", "skipped", "not a git repo, so there is nothing to make trackable yet."
        )
    if _config_is_trackable(root):
        return StepResult("gitignore", "already", ".teamctx/config.json is already trackable.")
    if dry_run:
        return StepResult(
            "gitignore", "skipped",
            "--dry-run: would patch .gitignore to track .teamctx/config.json.",
        )
    gitignore = root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if "!.teamctx/config.json" not in existing:  # idempotent: never append the stanza twice
        prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
        _atomic_write(gitignore, prefix + "\n" + _TRACKABLE_STANZA)
    if _config_is_trackable(root):
        return StepResult(
            "gitignore", "wrote", "patched .gitignore so .teamctx/config.json is trackable."
        )
    detail = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-v", "--no-index", ".teamctx/config.json"],
        capture_output=True, text=True,
    ).stdout.strip()
    return StepResult(
        "gitignore", "failed",
        "couldn't make .teamctx/config.json trackable; a broader rule still ignores it "
        f"({detail or 'see .gitignore'}). Edit .gitignore by hand.",
    )


def _auth_found_message(token_env: str, source: str | None) -> str:
    if source == "env":
        return f"using {token_env} from your environment."
    if source == "file":
        return f"using the token file in {token_env}_FILE."
    if source == "gh":
        return "using your gh CLI login."
    return "credential found."


def _auth_missing_message(token_env: str) -> str:
    return (
        f"no GitHub credential found. Set {token_env} in your environment (or {token_env}_FILE "
        "with a path to a token file), or run `gh auth login`. Until then teamctx can't check "
        "open PRs or failing checks and will say so, never a false all-clear."
    )


class GithubOnboarder:
    """The one source onboarder today. Host-aware detection reuses Part 1's ``detect_repo``, which
    returns owner/name only for a github.com origin (fail-closed on any other host)."""

    provider = "github"

    def detect(self, root: Path) -> str | None:
        return detect_repo(root)

    def propose_config(self, repo: str) -> dict[str, str]:
        return {"repo": repo}

    def auth_status(self, token_env: str = "GITHUB_TOKEN") -> AuthStatus:
        token, source = resolve_github_token_with_source(token_env)
        if token:
            return AuthStatus(True, source, _auth_found_message(token_env, source))
        return AuthStatus(False, None, _auth_missing_message(token_env))

    def verify_health(
        self, repo: str, *, token: str | None, opener: HttpOpener = DEFAULT_OPENER
    ) -> HealthReport:
        """A live reachability check, never a verdict: count open PRs off the first page. A full
        page (>= 100) is reported as a floor, so the number is never a false exact count."""

        if not token:
            return HealthReport(
                False, None, False,
                "no credential, so I couldn't reach GitHub to count open PRs.",
            )
        try:
            owner, name = split_repo(repo)  # inside the try: a bad repo string must never crash
            url = (
                f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}/pulls?state=open&per_page=100"
            )
            payload = get_json(url, token=token, opener=opener)
        except (GitHubProbeError, OSError, ValueError):
            # any bad-repo, network, HTTP, or decode failure: an honest unreachable report, never a
            # crash and never a false all-clear (this is a reachability check, not a verdict).
            return HealthReport(
                False, None, False,
                "couldn't reach GitHub just now (transient or access); teamctx will say so, "
                "never a false all-clear.",
            )
        if not isinstance(payload, list):
            return HealthReport(
                False, None, False,
                "GitHub returned an unexpected shape for open PRs; reporting it as unreachable "
                "rather than guessing.",
            )
        count = len(payload)
        if count >= 100:
            return HealthReport(True, count, True, "reached GitHub: at least 100 open PRs (100+).")
        return HealthReport(True, count, False, f"reached GitHub: {count} open PRs.")


ONBOARDERS: list[GithubOnboarder] = [GithubOnboarder()]


_SNIPPET_START = "<!-- teamctx:start -->"
_SNIPPET_END = "<!-- teamctx:end -->"
_SNIPPET_HEADING = "## Team context (teamctx)"
_KNOWN_BODIES = (CLAUDE_MD_SNIPPET, _SNIPPET_BODY_2026_07, _LEGACY_SNIPPET_BODY)
SnippetState = Literal[
    "current", "outdated", "edited", "conflicted_markers", "legacy", "edited_heading", "absent"
]


def _marked_block() -> str:
    return f"{_SNIPPET_START}\n{CLAUDE_MD_SNIPPET}{_SNIPPET_END}\n"


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def _marker_span(lines: list[str]) -> tuple[int, int] | None:
    """The single well-formed teamctx marker pair, or None (absent, multiple, or out of order)."""

    starts = [i for i, ln in enumerate(lines) if ln.strip() == _SNIPPET_START]
    ends = [i for i, ln in enumerate(lines) if ln.strip() == _SNIPPET_END]
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return None
    return starts[0], ends[0]


def classify_claude_md(existing: str) -> SnippetState:
    """Classify the teamctx snippet state in a CLAUDE.md text. The one classifier used by
    upsert (to decide the write) and status (to report), so they can never disagree."""

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


def upsert_claude_md_snippet(root: Path, *, dry_run: bool) -> StepResult:
    """Write or refresh the teamctx snippet in CLAUDE.md, never destroying user content: manage
    only a single well-formed marker pair whose body teamctx generated, migrate an exact unedited
    legacy block, and otherwise warn rather than guess a boundary."""

    path = root / "CLAUDE.md"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines(keepends=True)
    block = _marked_block()
    state = classify_claude_md(existing)

    if state == "conflicted_markers":
        return StepResult(
            "claude_md", "skipped",
            "found teamctx markers in CLAUDE.md that aren't a clean single start/end pair; fix or "
            "remove them by hand, then re-run.",
        )
    if state == "current":
        return StepResult("claude_md", "already", "CLAUDE.md snippet already current.")
    if state == "edited":
        return StepResult(
            "claude_md", "skipped",
            "the teamctx block in CLAUDE.md was hand-edited; left it untouched. Remove it and "
            "re-run to let teamctx manage it.",
        )
    if state == "outdated":
        if dry_run:
            return StepResult(
                "claude_md", "skipped", "--dry-run: would refresh the CLAUDE.md snippet."
            )
        span = _marker_span(lines)
        assert span is not None
        start_i, end_i = span
        _atomic_write(path, "".join(lines[:start_i]) + block + "".join(lines[end_i + 1 :]))
        return StepResult("claude_md", "wrote", "refreshed the CLAUDE.md snippet in place.")

    if state == "legacy":
        if dry_run:
            return StepResult(
                "claude_md", "skipped", "--dry-run: would migrate the old CLAUDE.md snippet."
            )
        _atomic_write(path, existing.replace(_LEGACY_SNIPPET_BODY, block, 1))
        return StepResult(
            "claude_md", "wrote", "migrated the old CLAUDE.md snippet to the marked block."
        )

    if state == "edited_heading":
        return StepResult(
            "claude_md", "skipped",
            "found an edited '## Team context (teamctx)' block in CLAUDE.md; left it untouched. "
            "Remove it by hand and re-run.",
        )

    assert state == "absent"
    if dry_run:
        return StepResult("claude_md", "skipped", "--dry-run: would add the CLAUDE.md snippet.")
    prefix = existing if existing == "" or existing.endswith("\n") else existing + "\n"
    joiner = "" if prefix == "" else "\n"
    _atomic_write(path, prefix + joiner + block)
    return StepResult("claude_md", "wrote", "added the teamctx snippet to CLAUDE.md.")


@dataclass(frozen=True)
class OnboardResult:
    ok: bool
    steps: tuple[StepResult, ...]
    next_step: str


@dataclass(frozen=True)
class StatusReport:
    steps: tuple[StepResult, ...]
    next_step: str


def _load_existing_config(path: Path) -> tuple[ProjectConfig | None, str | None]:
    """(config, None) if a valid config exists, (None, error) if it exists but is malformed, or
    (None, None) if absent."""

    if not path.exists():
        return None, None
    try:
        return load_project_config(path), None
    except ProjectConfigError as exc:
        return None, str(exc)


def _config_step_and_effective_repo(
    path: Path,
    *,
    override_repo: str | None,
    detected: str | None,
    existing: ProjectConfig | None,
    error: str | None,
    force: bool,
    dry_run: bool,
    detected_docs_root: str | None = None,
) -> tuple[StepResult, str | None]:
    """The config step plus the github.com owner/name work-start will actually resolve after
    onboard (explicit > config > git-detect, normalized through ``parse_github_repo`` exactly like
    ``resolve.py``), so onboard's report and health can never drift from runtime. The returned
    ``effective_repo`` is None when nothing resolves; a config that names a non-github repo is a
    failure here just as it is at runtime."""

    # A malformed existing config: runtime raises before it resolves any repo, so there is nothing
    # to health-check (effective None) and it is a failure.
    if error is not None and not force:
        return (
            StepResult(
                "config", "failed",
                f"{path} exists but is not valid teamctx config ({error}); fix it or pass --force "
                "to overwrite.",
            ),
            None,
        )
    # Keeping a valid existing config: the repo is whatever runtime resolves from it, via the ONE
    # shared resolver (config.repo normalized, else git-detect), and rejected exactly as runtime
    # rejects it. No drift.
    if existing is not None and not force:
        config_raw = existing.work_start.repo if existing.work_start is not None else None
        effective, repo_error = resolve_github_repo(None, config_raw, detected)
        if repo_error is not None:
            return (
                StepResult(
                    "config", "failed",
                    f"{path} configures a repo work-start can't use: {repo_error} Fix it or pass "
                    "--force to overwrite.",
                ),
                None,
            )
        if config_raw:
            detail = f"{path} already configures {effective}; pass --force to overwrite."
            if override_repo is not None and override_repo != effective:
                detail = (
                    f"{path} already configures {effective}, not {override_repo}; pass --force to "
                    "change it."
                )
        else:
            detail = (
                f"{path} exists with no repo set; work-start will use the git origin {effective}."
            )
        return StepResult("config", "already", detail), effective
    # Writing a new config: the written repo is explicit-or-git-detect, resolved the same way, so
    # the config we write is exactly what runtime will read back.
    write_repo, repo_error = resolve_github_repo(override_repo, None, detected)
    if repo_error is not None or write_repo is None:
        return (
            StepResult(
                "config", "failed",
                "can't determine a repo to write: not a git repo with a github.com 'origin', and "
                "no --repo. Pass --repo owner/name.",
            ),
            None,
        )
    if dry_run:
        return (
            StepResult(
                "config", "skipped",
                f"--dry-run: would write .teamctx/config.json for {write_repo}.",
            ),
            write_repo,
        )
    config = build_work_start_project_config(repo=write_repo, docs_root=detected_docs_root)
    _atomic_write(
        path, json.dumps(config.model_dump(mode="json", exclude_defaults=True), indent=2) + "\n"
    )
    return StepResult("config", "wrote", f"{path} (repo {write_repo})"), write_repo


DocsDirState = Literal["ok", "unsafe", "empty", "absent"]


def _docs_dir_state(root: Path) -> DocsDirState:
    """Whether a conventional top-level ``docs/`` folder is safely configurable, mirroring the
    runtime scan's fail-closed rules (connectors/docs.py): the directory and every markdown file
    in it must resolve inside the project root, else the runtime scan would read unavailable.
    ``empty`` = the folder exists (safely) but holds no markdown; ``absent`` = no folder."""

    docs_dir = root / "docs"
    if not docs_dir.is_dir():
        return "absent"
    try:
        base = root.resolve()
        docs_dir.resolve().relative_to(base)
        markdown = list(docs_dir.rglob("*.md"))
        if not markdown:
            return "empty"
        for path in markdown:
            path.resolve().relative_to(base)
    except (OSError, ValueError):
        return "unsafe"
    return "ok"


def _detect_docs_root(root: Path) -> str | None:
    """``"docs"`` when a conventional docs folder is safely configurable, else None."""

    return "docs" if _docs_dir_state(root) == "ok" else None


_DOCS_FOUND = "found a docs/ folder; superseded docs there will be flagged."
_DOCS_NOT_FOUND = (
    "no docs/ folder found; set work_start.docs_root in .teamctx/config.json to flag "
    "superseded docs."
)
_DOCS_EXISTS_UNCONFIGURED = (
    "a docs/ folder exists but the existing config has no docs_root; add work_start.docs_root "
    "to .teamctx/config.json (or re-run with --force) to flag superseded docs."
)
_DOCS_UNSAFE = (
    "a docs/ folder exists but couldn't be safely configured (it or a file in it resolves "
    "outside the repo); set work_start.docs_root by hand if this is intended."
)
_DOCS_EMPTY = "a docs/ folder exists but has no markdown files in it; nothing to scan yet."


def _docs_step(
    configured_docs_root: str | None, wrote_detected: bool, dir_state: DocsDirState
) -> StepResult:
    """Report the docs configuration honestly in every branch: what IS configured after the
    config step, or the true reason nothing is, with the fix. Never claims a folder is absent
    when it exists, and never blesses a root the runtime scan would fail closed on."""

    if wrote_detected:
        return StepResult("docs", "noted", _DOCS_FOUND)
    if configured_docs_root:
        return StepResult(
            "docs", "noted",
            f"docs_root '{configured_docs_root}' is configured; superseded docs there will be "
            "flagged.",
        )
    if dir_state == "ok":
        return StepResult("docs", "noted", _DOCS_EXISTS_UNCONFIGURED)
    if dir_state == "unsafe":
        return StepResult("docs", "noted", _DOCS_UNSAFE)
    if dir_state == "empty":
        return StepResult("docs", "noted", _DOCS_EMPTY)
    return StepResult("docs", "noted", _DOCS_NOT_FOUND)


def _install_hook_step(root: Path, *, dry_run: bool) -> StepResult:
    from teamctx.cli import (
        install_hook_into_settings,  # local: cli imports onboard, break the cycle
    )

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
    """Scaffold teamctx in ``root``. Additive and idempotent; each write atomic; a failed step
    fails only itself (and flips ``ok``); a missing token is reported, not fatal."""

    # An empty --repo is treated as absent (falls back to config/git), exactly as runtime treats a
    # falsy explicit repo; only a truthy-but-invalid --repo is an error.
    override_repo = parse_github_repo(repo_override) if repo_override else None
    if repo_override and override_repo is None:
        return OnboardResult(
            False,
            (StepResult(
                "detect", "failed",
                f"{repo_override!r} is not a github.com owner/name; pass --repo owner/name.",
            ),),
            "re-run with --repo owner/name",
        )

    config_path = root / ".teamctx" / "config.json"
    existing, config_error = _load_existing_config(config_path)
    detected = detect_repo(root)

    # Case A: genuinely nothing to onboard (no config file at all, no --repo, no git origin) ->
    # stop and write nothing (spec 2.2 step 2). A config that EXISTS but is broken is handled by
    # the config step (it fails, but the hook/snippet steps still run per the transaction model).
    if existing is None and config_error is None and override_repo is None and detected is None:
        return OnboardResult(
            False,
            (StepResult(
                "detect", "failed",
                "could not determine a GitHub repo: not a git repo with a github.com 'origin', no "
                ".teamctx/config.json, and no --repo. Re-run with --repo owner/name.",
            ),),
            "re-run with --repo owner/name",
        )

    detected_docs = _detect_docs_root(root)
    config_step, effective_repo = _config_step_and_effective_repo(
        config_path, override_repo=override_repo, detected=detected,
        existing=existing, error=config_error, force=force, dry_run=dry_run,
        detected_docs_root=detected_docs,
    )
    # The docs step reports what IS configured after the config step (never a wish): a fresh
    # write includes the detection; an existing config keeps its own docs_root; dry-run previews.
    wrote_fresh_config = config_step.status == "wrote"
    would_write_config = config_step.status == "skipped" and dry_run
    existing_docs = (
        existing.work_start.docs_root
        if existing is not None and existing.work_start is not None
        else None
    )
    docs_dir_state = _docs_dir_state(root)
    if detected_docs is not None and would_write_config:
        docs_step = StepResult(
            "docs", "skipped", f"--dry-run: would set docs_root to '{detected_docs}'."
        )
    elif detected_docs is not None and wrote_fresh_config:
        docs_step = _docs_step(detected_docs, wrote_detected=True, dir_state=docs_dir_state)
    else:
        docs_step = _docs_step(existing_docs, wrote_detected=False, dir_state=docs_dir_state)

    # Resolve the credential ONCE, so the reported source and the health check use the same token
    # (the gh fallback is not re-evaluated) and cannot drift.
    token, source = resolve_github_token_with_source(token_env)
    auth_found = token is not None
    auth_message = (
        _auth_found_message(token_env, source) if auth_found else _auth_missing_message(token_env)
    )
    if effective_repo is not None:
        health = ONBOARDERS[0].verify_health(effective_repo, token=token, opener=opener)
        health_message = health.message
    else:
        health_message = "no valid repo resolved, so no reachability check was run."

    steps: list[StepResult] = [
        config_step,
        ensure_config_trackable(root, dry_run=dry_run),
        docs_step,
        StepResult("auth", "noted", auth_message),
        _install_hook_step(root, dry_run=dry_run),
        upsert_claude_md_snippet(root, dry_run=dry_run),
        StepResult("health", "noted", health_message),
    ]

    ok = not any(step.status == "failed" for step in steps)
    next_step = (
        "Run `teamctx work-start --path <a file you're about to edit>` to see it work."
        if auth_found
        else "Set a GitHub credential (see the auth line above), then run `teamctx work-start`."
    )
    return OnboardResult(ok, tuple(steps), next_step)


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


SnippetStatusMark = Literal["ok", "noted"]


_SNIPPET_STATUS_DETAIL: dict[SnippetState, tuple[SnippetStatusMark, str]] = {
    "current": ("ok", "the CLAUDE.md snippet is current."),
    "outdated": ("noted", "the CLAUDE.md snippet is outdated; `teamctx onboard` refreshes it."),
    "edited": (
        "noted", "the teamctx block in CLAUDE.md was hand-edited; teamctx leaves it to you."
    ),
    "conflicted_markers": (
        "noted",
        "CLAUDE.md has teamctx markers that aren't a clean single start/end pair; fix or remove "
        "them by hand.",
    ),
    "legacy": ("noted", "CLAUDE.md has the old unmarked snippet; `teamctx onboard` migrates it."),
    "edited_heading": (
        "noted",
        "CLAUDE.md has an edited '## Team context (teamctx)' block; teamctx leaves it to you.",
    ),
    "absent": ("noted", "no teamctx snippet in CLAUDE.md; `teamctx onboard` adds it."),
}


def _snippet_status_step(state: SnippetState) -> StepResult:
    mark, detail = _SNIPPET_STATUS_DETAIL[state]
    return StepResult("claude_md", mark, detail)


def _status_next_step(steps: list[StepResult], auth_found: bool) -> str:
    if any(s.status == "failed" for s in steps):
        return "Fix the failed line above (or run `teamctx onboard --force`)."
    if any(s.name in {"config", "hook", "claude_md"} and s.status == "noted" for s in steps):
        return "Run `teamctx onboard` to finish setup."
    if not auth_found:
        return "Set a GitHub credential (see the credential line above)."
    return "You're set. Run `teamctx work-start --path <a file you're about to edit>`."


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

    configured_docs = (
        existing.work_start.docs_root
        if existing is not None and existing.work_start is not None
        else None
    )
    if configured_docs:
        steps.append(StepResult(
            "docs", "ok",
            f"docs_root '{configured_docs}' is configured; superseded docs there will be "
            "flagged.",
        ))
    else:
        docs_state = _docs_dir_state(root)
        if docs_state == "ok" and existing is None and config_error is None:
            # genuinely no config: a fresh onboard WILL write the detection, so the promise is
            # true. A malformed config also parses to existing=None but onboard will NOT write
            # over it without --force, so it takes the add-or-force copy below instead.
            steps.append(StepResult(
                "docs", "noted",
                "a docs/ folder exists but no docs_root is configured; `teamctx onboard` sets "
                "it.",
            ))
        elif docs_state == "ok":
            # an existing config is never modified by onboard, so say the real fix
            steps.append(StepResult("docs", "noted", _DOCS_EXISTS_UNCONFIGURED))
        elif docs_state == "unsafe":
            steps.append(StepResult("docs", "noted", _DOCS_UNSAFE))
        elif docs_state == "empty":
            steps.append(StepResult("docs", "noted", _DOCS_EMPTY))
        else:
            steps.append(StepResult("docs", "noted", _DOCS_NOT_FOUND))

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
