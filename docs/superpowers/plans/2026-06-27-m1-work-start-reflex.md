# M1: work_start as a reflex (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A deterministic Claude Code `PreToolUse` hook (plus a portable instruction) that fires `work_start` once per session at the first edit and injects a glanceable signal, *ready* / *heads up* / *can't verify what matters*: never blocking the edit.

**Architecture:** A lightweight `teamctx-hook` script (own module, cheap no-op hot path) reads the PreToolUse JSON, no-ops if the session was already grounded, else resolves inputs, gets the structured `BrokerAnswer` via a new `work_start_answer`, maps it to one signal via a pure `hook_signal`, and emits `additionalContext`. A `teamctx install-hook` CLI command opt-in-installs the hook and prints the portable snippet.

**Tech Stack:** Python 3.12, click (CLI), pytest. ruff (`E,F,I,N,W,UP,B,SIM`, line 100) + mypy `--strict`. Hook I/O verified against the Claude Code hooks docs (2026-06-27).

Spec: `docs/superpowers/specs/2026-06-27-m1-work-start-reflex-design.md`.

---

## File structure

- **Create** `src/teamctx/tokens.py`, `resolve_github_token()` (env `GITHUB_TOKEN` → `GITHUB_TOKEN_FILE`), lightweight, no heavy imports. (DRY: `mcp_server` reuses it.)
- **Modify** `src/teamctx/work_start.py`, add `work_start_answer(...) -> BrokerAnswer`; `render_work_start` delegates to it.
- **Create** `src/teamctx/hook_signal.py`, pure `hook_signal(answer, *, file_path, token_present) -> str`: the ready/heads-up/can't-verify mapper.
- **Create** `src/teamctx/hook.py`, `teamctx-hook` entry: stdin→signal→stdout orchestration, once-per-session cache, fail-safe.
- **Modify** `pyproject.toml`, add `teamctx-hook` console script.
- **Modify** `src/teamctx/cli.py`, add `install-hook` command.
- **Create** `tests/test_tokens.py`, `tests/test_hook_signal.py`, `tests/test_hook.py`, `tests/test_install_hook.py`.

Order: Task 1 (tokens) and Task 2 (work_start_answer) are independent; Task 3 (hook_signal) needs Task 2's `BrokerAnswer` access pattern; Task 4 (hook) needs 1–3; Task 5 (install-hook) is independent; Task 6 verifies.

---

## Task 1: Extract `resolve_github_token`

**Files:** Create `src/teamctx/tokens.py`; Modify `src/teamctx/mcp_server.py`; Test `tests/test_tokens.py`.

- [ ] **Step 1: Write the failing test**: `tests/test_tokens.py`:

```python
from __future__ import annotations

from pathlib import Path

from teamctx.tokens import resolve_github_token


def test_env_value_wins(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_github_token() == "from-env"


def test_falls_back_to_file_then_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    token_file = tmp_path / "tok"
    token_file.write_text("from-file\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(token_file))
    assert resolve_github_token() == "from-file"

    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    assert resolve_github_token() is None

    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(tmp_path / "missing"))
    assert resolve_github_token() is None
```

- [ ] **Step 2: Run to verify failure**: `pytest tests/test_tokens.py -v` → FAIL (no module `teamctx.tokens`).

- [ ] **Step 3: Implement**: `src/teamctx/tokens.py`:

```python
"""Resolve the GitHub token from the environment (value, then file). Lightweight by design:
no project imports, so the hot hook path can use it without pulling the broker."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_github_token() -> str | None:
    """``GITHUB_TOKEN`` (the value) wins; else ``GITHUB_TOKEN_FILE`` (a path) is read. A missing
    or unreadable file yields ``None``, honest absence, never a crash."""

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    token_file = os.environ.get("GITHUB_TOKEN_FILE")
    if token_file:
        try:
            return Path(token_file).expanduser().read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    return None
```

- [ ] **Step 4: Reuse in `mcp_server.py`**: replace the body of `_resolve_github_token` with a call to the shared function (keep the wrapper name so existing tests pass). In `src/teamctx/mcp_server.py`, add import `from teamctx.tokens import resolve_github_token` and change `_resolve_github_token` to:

```python
def _resolve_github_token() -> str | None:
    """The token, resolved server-side (see teamctx.tokens). No token → honest UNKNOWN."""

    return resolve_github_token()
```

Remove the now-unused `import os` / `from pathlib import Path` from `mcp_server.py` ONLY if nothing else there uses them (check: `grep -nE "os\.|Path\(" src/teamctx/mcp_server.py`, `_resolution_root` uses both, so keep them).

- [ ] **Step 5: Run**: `pytest tests/test_tokens.py tests/test_mcp_server.py -v` → all pass. `ruff check src/teamctx/tokens.py src/teamctx/mcp_server.py tests/test_tokens.py` and `mypy src/teamctx/tokens.py src/teamctx/mcp_server.py` clean.

- [ ] **Step 6: Commit**

```bash
git add src/teamctx/tokens.py src/teamctx/mcp_server.py tests/test_tokens.py
git commit -m "refactor: extract resolve_github_token to teamctx.tokens (shared, lightweight)"
```

---

## Task 2: Expose `work_start_answer` (structured BrokerAnswer)

**Files:** Modify `src/teamctx/work_start.py`; Test `tests/test_work_start_answer.py`.

- [ ] **Step 1: Write the failing test**: `tests/test_work_start_answer.py`:

```python
from __future__ import annotations

from teamctx.core.broker import BrokerAnswer
from teamctx.runner import WorkStartInputs
from teamctx.work_start import render_work_start, work_start_answer

OBS = "2026-06-27T00:00:00Z"


def test_work_start_answer_returns_broker_answer(monkeypatch) -> None:
    import teamctx.connectors.github as gh
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: [])
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = WorkStartInputs(repo="acme/widgets", paths=("src/x.py",), token="t")
    answer = work_start_answer(inputs, observed_at=OBS)
    assert isinstance(answer, BrokerAnswer)
    # verdict labels are present and ordered per CARD_KINDS
    labels = [label for label, _ in answer.verdicts]
    assert labels == ["Conflict check", "Criteria check", "Docs check", "Gate check"]


def test_render_work_start_still_renders(monkeypatch) -> None:
    import teamctx.connectors.github as gh
    monkeypatch.setattr(gh, "fetch_github_pull_requests", lambda **kw: [])
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    inputs = WorkStartInputs(repo="acme/widgets", paths=("src/x.py",), token="t")
    text = render_work_start(inputs, observed_at=OBS)
    assert "Working context" in text
    assert "Conflict check:" in text
```

- [ ] **Step 2: Run to verify failure**: `pytest tests/test_work_start_answer.py -v` → FAIL (no `work_start_answer`).

- [ ] **Step 3: Implement**: in `src/teamctx/work_start.py`, add `work_start_answer` and make `render_work_start` delegate. Replace the existing `render_work_start` body and add the new function (keep imports; add `from teamctx.core.broker import BrokerAnswer`):

```python
def work_start_answer(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path = DEFAULT_AUTHORITY_PATH,
    project_root: Path = Path("."),
) -> BrokerAnswer:
    """Run every applicable connector, compose, and evaluate, returning the structured
    broker answer (cards + honest coverage + one verdict per check). Transports render it;
    the hook maps it to a signal."""

    request_context, documents = run_work_start_connectors(
        inputs, observed_at=observed_at, project_root=project_root
    )
    declarations = load_declared_authority(authority_path)
    return broker_answer_from_documents(request_context, documents, declarations)


def render_work_start(
    inputs: WorkStartInputs,
    *,
    observed_at: str,
    authority_path: Path = DEFAULT_AUTHORITY_PATH,
    project_root: Path = Path("."),
) -> str:
    """Render the work-start answer (cards + honest coverage + one verdict per check) as text."""

    answer = work_start_answer(
        inputs, observed_at=observed_at, authority_path=authority_path, project_root=project_root
    )
    return render_broker_answer(answer)
```

(`run_work_start_connectors` already accepts `project_root` from the Sprint-1 docs fix; `render_broker_answer` and `broker_answer_from_documents` are already imported.)

- [ ] **Step 4: Run**: `pytest tests/test_work_start_answer.py tests/test_work_start_cli.py tests/test_mcp_server.py -v` → all pass (render path unchanged). ruff + mypy clean on `work_start.py`.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/work_start.py tests/test_work_start_answer.py
git commit -m "feat: expose work_start_answer (structured BrokerAnswer); render delegates"
```

---

## Task 3: The signal mapper (`hook_signal`)

**Files:** Create `src/teamctx/hook_signal.py`; Test `tests/test_hook_signal.py`.

The mapper is a pure function over `BrokerAnswer`. Tests construct answers via the real engine
(`broker_answer`) so we exercise true verdict/coverage shapes, not hand-rolled internals.

- [ ] **Step 1: Write the failing tests**: `tests/test_hook_signal.py`:

```python
from __future__ import annotations

from teamctx.connectors._contract import metadata_only_policy, source_status
from teamctx.core.broker import broker_answer
from teamctx.core.contracts import RequestContext, SourceSignal
from teamctx.hook_signal import hook_signal


def _request(paths=("src/app.py",)) -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="acme/widgets",
        branch="feature",
        task="work",
        paths=list(paths),
        linked_issues=[],
        requested_at="2026-06-27T00:00:00Z",
        requesting_principal=None,
    )


def _collision_signal() -> SourceSignal:
    return SourceSignal(
        schema_version="teamctx.source_signal.v0",
        id="sig_pr_7",
        signal_type="collision",
        source_family="git_hosting",
        scope={"repo": "acme/widgets", "files": ["src/app.py"]},
        evidence_summary="PR #7 changes src/app.py",
        source_display="github acme/widgets#7",
        freshness="fresh",
        confidence="high",
        visibility="visible",
        created_at="2026-06-27T00:00:00Z",
        observed_at="2026-06-27T00:00:00Z",
        expires_at="next_refresh",
        policy=metadata_only_policy("pr metadata is evidence"),
    )


def _fresh_status(family: str) -> object:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="fresh",
        observed_at="2026-06-27T00:00:00Z",
        safe_user_message="checked",
        visibility="silent",
        policy_reason="status only",
    )


def _unavailable_status(family: str) -> object:
    return source_status(
        source_id=f"{family}-probe",
        source_family=family,
        scope={"repo": "acme/widgets"},
        status="unavailable",
        observed_at="2026-06-27T00:00:00Z",
        safe_user_message="no access",
        visibility="silent",
        policy_reason="status only",
    )


def test_heads_up_when_a_collision_is_found() -> None:
    answer = broker_answer(_request(), [_collision_signal()], [_fresh_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "src/app.py" in text
    assert "PR #7" in text
    assert "ground" not in text.lower() and "broker" not in text.lower()


def test_cant_verify_when_github_unreachable_no_token() -> None:
    # git_hosting present but unavailable => Conflict check unknown[stale-dep] => can't verify
    answer = broker_answer(_request(), [], [_unavailable_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=False)
    assert "GitHub" in text
    assert "install-hook" in text
    assert "keep working" in text


def test_ready_names_the_clear_checks_no_lowstakes_hedge() -> None:
    # git_hosting fresh, no collision => Conflict check clear; criteria/docs not configured =>
    # policy-gap unknown, must NOT be headlined.
    answer = broker_answer(_request(), [], [_fresh_status("git_hosting")])
    text = hook_signal(answer, file_path="src/app.py", token_present=True)
    assert "looks clear" in text.lower()
    assert "src/app.py" in text
    assert "pull request" in text.lower()
    assert "couldn't" not in text.lower()  # no "...but" hedge for low-stakes gaps
```

- [ ] **Step 2: Run to verify failure**: `pytest tests/test_hook_signal.py -v` → FAIL (no module `teamctx.hook_signal`).

- [ ] **Step 3: Implement**: `src/teamctx/hook_signal.py`:

```python
"""Map the broker's answer to one glanceable hook signal: ready / heads up / can't verify.

The hook injects a short signal before an edit, not the full CLI report. Per the surfaced-text
principle, it speaks to a human about to decide: a clean *ready* that names what it checked, a
*heads up* with the specific item, or *can't verify* when a source that matters was unreachable.
Low-stakes coverage gaps (a check not configured) are never headlined.
"""

from __future__ import annotations

from teamctx.core.broker import BrokerAnswer
from teamctx.core.contracts import ContextCard
from teamctx.core.evaluate import Valuation

_IMPORTANT = ("Conflict check", "Gate check")
_CLEAR_PHRASE = {
    "Conflict check": "no open pull requests touch these files",
    "Gate check": "CI is green",
    "Docs check": "the docs you rely on are current",
    "Criteria check": "the linked issue's criteria are unchanged",
}


def hook_signal(answer: BrokerAnswer, *, file_path: str, token_present: bool) -> str:
    """One glanceable signal for the PreToolUse injection. Empty string = nothing worth saying."""

    verdicts: dict[str, Valuation] = {label: val for label, val in answer.verdicts}
    findings = [
        card
        for card in answer.selection.cards
        if card.section in ("Needs attention", "Verify before relying")
    ]
    if findings:
        return _heads_up(findings, file_path)

    blocked = [
        label
        for label in _IMPORTANT
        if label in verdicts
        and verdicts[label].value == "unknown"
        and verdicts[label].reason.startswith("incomplete[stale-dep]")
    ]
    if blocked:
        return _cant_verify(token_present)

    return _ready(verdicts, file_path)


def _heads_up(findings: list[ContextCard], file_path: str) -> str:
    lines = [f"teamctx, before you edit {file_path}, from the team's current work:"]
    lines.extend(f"  • {card.text}, {card.why_this_matters}" for card in findings)
    lines.append("Pass along anything relevant to whoever you're working with so they can decide.")
    return "\n".join(lines)


def _cant_verify(token_present: bool) -> str:
    if not token_present:
        return (
            "teamctx couldn't check what else is happening around this file, it doesn't have "
            "access to GitHub yet. To switch that on, run `teamctx install-hook` and it'll walk you "
            "through giving it a token. If you'd rather not connect it right now, that's fine, "
            "keep working; you just won't get a heads-up about open pull requests on the same files "
            "or checks that are failing."
        )
    return (
        "teamctx couldn't reach GitHub just now, so it couldn't check for open pull requests or "
        "failing checks on these files, usually a passing connection issue, worth a retry. "
        "Until it's back you won't get those warnings, so glance at GitHub yourself if this file is "
        "sensitive."
    )


def _ready(verdicts: dict[str, Valuation], file_path: str) -> str:
    clear = [
        _CLEAR_PHRASE[label]
        for label in ("Conflict check", "Gate check", "Docs check", "Criteria check")
        if label in verdicts and verdicts[label].value == "true"
    ]
    if not clear:
        return ""
    return f"teamctx, looks clear to start on {file_path}: {_join(clear)}."


def _join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]
```

- [ ] **Step 4: Run**: `pytest tests/test_hook_signal.py -v` → PASS. `ruff check src/teamctx/hook_signal.py tests/test_hook_signal.py` and `mypy src/teamctx/hook_signal.py` clean.

> If `source_status` / `metadata_only_policy` are not importable from `teamctx.connectors._contract`, `grep -n "def source_status\|def metadata_only_policy" src/teamctx/connectors/_contract.py` to confirm the names and adjust the test imports. (Do not change `hook_signal.py` for this, only the test's construction helpers.)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/hook_signal.py tests/test_hook_signal.py
git commit -m "feat: hook_signal, map broker answer to ready/heads-up/can't-verify"
```

---

## Task 4: The hook (`teamctx-hook`)

**Files:** Create `src/teamctx/hook.py`; Modify `pyproject.toml`; Test `tests/test_hook.py`.

- [ ] **Step 1: Write the failing tests**: `tests/test_hook.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import teamctx.hook as hook


def _init_repo(root: Path, url: str = "git@github.com:acme/widgets.git") -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", "feature"], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


def _payload(root: Path, file_path: str = "src/app.py") -> str:
    return json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": file_path},
            "cwd": str(root),
            "session_id": "sess-1",
        }
    )


def _run(payload: str, monkeypatch, capsys) -> str:
    monkeypatch.setattr("sys.stdin.read", lambda: payload)
    hook.main()
    return capsys.readouterr().out


def test_first_edit_emits_can_verify_without_token(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    out = _run(_payload(tmp_path), monkeypatch, capsys)
    data = json.loads(out)
    ctx = data["hookSpecificOutput"]["additionalContext"]
    assert "GitHub" in ctx and "install-hook" in ctx
    assert "permissionDecision" not in data["hookSpecificOutput"]  # never blocks


def test_once_per_session(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    _run(_payload(tmp_path), monkeypatch, capsys)  # first: grounds
    out2 = _run(_payload(tmp_path), monkeypatch, capsys)  # second: no-op
    assert out2.strip() == ""


def test_heads_up_surfaces_a_collision(monkeypatch, capsys, tmp_path) -> None:
    _init_repo(tmp_path)
    import teamctx.connectors.github as gh
    from teamctx.connectors.forge_review import ForgeReviewPullRequest
    monkeypatch.setattr(
        gh, "fetch_github_pull_requests",
        lambda **kw: [ForgeReviewPullRequest(
            provider="github", repo="acme/widgets", number=7, state="open",
            url="https://github.com/acme/widgets/pull/7", title=None,
            changed_paths=("src/app.py",), created_at="2026-06-27T10:00:00Z",
            updated_at="2026-06-27T11:00:00Z")],
    )
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    out = _run(_payload(tmp_path), monkeypatch, capsys)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "PR #7" in ctx


def test_non_git_dir_fails_safe(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    payload = json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Edit",
        "tool_input": {"file_path": "src/app.py"}, "cwd": str(tmp_path), "session_id": "s2",
    })
    out = _run(payload, monkeypatch, capsys)
    # never blocks, never crashes; may emit a plain message or nothing
    if out.strip():
        data = json.loads(out)
        assert "permissionDecision" not in data["hookSpecificOutput"]


def test_non_edit_tool_is_noop(monkeypatch, capsys, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_HOOK_CACHE", str(tmp_path / "cache"))
    payload = json.dumps({
        "hook_event_name": "PreToolUse", "tool_name": "Bash",
        "tool_input": {"command": "ls"}, "cwd": str(tmp_path), "session_id": "s3",
    })
    out = _run(payload, monkeypatch, capsys)
    assert out.strip() == ""
```

- [ ] **Step 2: Run to verify failure**: `pytest tests/test_hook.py -v` → FAIL (no module `teamctx.hook`).

- [ ] **Step 3: Implement**: `src/teamctx/hook.py`. The hot no-op path (read stdin, check cache) runs before importing the broker:

```python
"""``teamctx-hook``: the Claude Code PreToolUse reflex.

On the first Edit/Write/MultiEdit of a session it grounds the agent, runs work_start for the
in-flight change and injects a short signal (ready / heads up / can't verify) as
``additionalContext``. It NEVER blocks an edit and never crashes the session: any error exits 0
with a plain message or nothing. Kept import-light so the per-edit no-op path stays cheap.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

_EDIT_TOOLS = {"Edit", "Write", "MultiEdit"}


def main() -> None:
    try:
        _run()
    except Exception:  # noqa: BLE001, a hook must never crash the session
        # Fail-safe: stay silent, allow the edit.
        pass
    sys.exit(0)


def _run() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        return
    event = json.loads(raw)
    if event.get("hook_event_name") != "PreToolUse" or event.get("tool_name") not in _EDIT_TOOLS:
        return
    file_path = event.get("tool_input", {}).get("file_path")
    cwd = event.get("cwd")
    session_id = event.get("session_id")
    if not file_path or not cwd or not session_id:
        return
    if _already_grounded(session_id):  # once per session, cheap no-op path ends here
        return
    _mark_grounded(session_id)

    text = _ground(Path(cwd), file_path)  # imports the broker lazily
    if text:
        _emit(text)


def _emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}
    }))


def _cache_dir() -> Path:
    import os
    import tempfile
    override = os.environ.get("TEAMCTX_HOOK_CACHE")
    base = Path(override) if override else Path(tempfile.gettempdir()) / "teamctx-hook"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _marker(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return _cache_dir() / f"{safe}.grounded"


def _already_grounded(session_id: str) -> bool:
    return _marker(session_id).exists()


def _mark_grounded(session_id: str) -> None:
    _marker(session_id).write_text("", encoding="utf-8")


def _changed_paths(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        name = line[3:].strip()
        if " -> " in name:  # rename
            name = name.split(" -> ", 1)[1]
        if name:
            paths.append(name)
    return paths


def _ground(root: Path, file_path: str) -> str:
    from teamctx.hook_signal import hook_signal
    from teamctx.resolve import resolve_work_start_inputs
    from teamctx.tokens import resolve_github_token
    from teamctx.work_start import work_start_answer

    token = resolve_github_token()
    paths = tuple(dict.fromkeys([file_path, *_changed_paths(root)]))  # dedup, order-preserving
    inputs = resolve_work_start_inputs(paths=paths, token=token, root=root)
    answer = work_start_answer(inputs, observed_at=_utc_now(), project_root=root)
    return hook_signal(answer, file_path=file_path, token_present=token is not None)


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add the console script**: in `pyproject.toml` under `[project.scripts]`, add:

```toml
teamctx-hook = "teamctx.hook:main"
```

- [ ] **Step 5: Run**: `pytest tests/test_hook.py -v` → PASS. `ruff check src/teamctx/hook.py tests/test_hook.py` and `mypy src/teamctx/hook.py` clean.

- [ ] **Step 6: Commit**

```bash
git add src/teamctx/hook.py tests/test_hook.py pyproject.toml
git commit -m "feat: teamctx-hook, PreToolUse reflex, once per session, never blocks"
```

---

## Task 5: The opt-in installer (`teamctx install-hook`)

**Files:** Modify `src/teamctx/cli.py`; Test `tests/test_install_hook.py`.

- [ ] **Step 1: Write the failing tests**: `tests/test_install_hook.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main


def test_install_hook_writes_idempotent_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r1 = CliRunner().invoke(main, ["install-hook"])
    assert r1.exit_code == 0, r1.output
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    pre = settings["hooks"]["PreToolUse"]
    assert any(
        h.get("matcher") == "Edit|Write|MultiEdit"
        and any(c.get("command") == "teamctx-hook" for c in h.get("hooks", []))
        for h in pre
    )
    # idempotent: second run does not duplicate
    CliRunner().invoke(main, ["install-hook"])
    settings2 = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings2["hooks"]["PreToolUse"]) == len(pre)
    # prints the portable instruction
    assert "work-start" in r1.output


def test_print_writes_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(main, ["install-hook", "--print"])
    assert r.exit_code == 0
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert "teamctx-hook" in r.output


def test_install_hook_merges_existing_settings(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": []}]}}), encoding="utf-8"
    )
    CliRunner().invoke(main, ["install-hook"])
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["model"] == "opus"  # preserved
    assert "Stop" in settings["hooks"]  # preserved
    assert "PreToolUse" in settings["hooks"]  # added
```

- [ ] **Step 2: Run to verify failure**: `pytest tests/test_install_hook.py -v` → FAIL (no `install-hook` command).

- [ ] **Step 3: Implement**: in `src/teamctx/cli.py`, add the command and helpers (uses `json`, `Path`, `click`, all already imported):

```python
_HOOK_MATCHER = "Edit|Write|MultiEdit"
_HOOK_ENTRY = {"matcher": _HOOK_MATCHER, "hooks": [{"type": "command", "command": "teamctx-hook"}]}
_CLAUDE_MD_SNIPPET = (
    "## Team context (teamctx)\n"
    "Before you start editing files in this repo, run `teamctx work-start` and factor the result "
    "into your plan, it surfaces open PRs touching your files, failing checks, changed specs, and "
    "superseded docs. Tell your human collaborator anything relevant in plain terms so they can "
    "decide.\n"
)


@main.command("install-hook")
@click.option("--print", "print_only", is_flag=True, help="Show what would change; write nothing.")
@click.option(
    "--settings",
    "settings_path",
    default=Path(".claude/settings.json"),
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Project-local Claude Code settings file.",
)
def install_hook_command(print_only: bool, settings_path: Path) -> None:
    """Opt in to the teamctx reflex: add the PreToolUse hook and print the portable snippet."""

    settings = _load_settings(settings_path)
    if not _has_hook_entry(settings):
        settings.setdefault("hooks", {}).setdefault("PreToolUse", []).append(_HOOK_ENTRY)

    if print_only:
        click.echo(json.dumps(settings, indent=2))
        click.echo("\nAdd this to your CLAUDE.md:\n")
        click.echo(_CLAUDE_MD_SNIPPET)
        return

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    click.echo(f"Installed the teamctx reflex hook in {settings_path}.")
    click.echo("\nAdd this to your CLAUDE.md:\n")
    click.echo(_CLAUDE_MD_SNIPPET)


def _load_settings(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"Could not read {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise click.ClickException(f"{path} is not a JSON object.")
    return loaded


def _has_hook_entry(settings: dict[str, Any]) -> bool:
    for entry in settings.get("hooks", {}).get("PreToolUse", []):
        if entry.get("matcher") == _HOOK_MATCHER and any(
            hook.get("command") == "teamctx-hook" for hook in entry.get("hooks", [])
        ):
            return True
    return False
```

Add `from typing import Any` to `cli.py` imports if not already present (`grep -n "from typing import" src/teamctx/cli.py`).

- [ ] **Step 4: Run**: `pytest tests/test_install_hook.py -v` → PASS. `ruff check src/teamctx/cli.py tests/test_install_hook.py` and `mypy src/teamctx/cli.py` clean. (Note: `hook` is used as a loop variable in `_has_hook_entry`; ensure it doesn't shadow a module import, it doesn't in `cli.py`.)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_install_hook.py
git commit -m "feat: teamctx install-hook, opt-in PreToolUse install + portable snippet"
```

---

## Task 6: Full verification

- [ ] **Step 1:** `pytest -q` → all pass (no regressions).
- [ ] **Step 2:** `ruff check src tests` → clean.
- [ ] **Step 3:** `mypy src` → clean under `--strict`.
- [ ] **Step 4:** Commit any fixups: `git add -A && git commit -m "chore: lint/type fixups for M1" || echo "nothing to fix"`.

---

## Self-Review

**Spec coverage:** Component 1 (the hook) → Tasks 2,3,4. Component 2 (portable instruction) → the snippet in Task 5 (`_CLAUDE_MD_SNIPPET`). Component 3 (opt-in install) → Task 5. Messaging / signal model (ready/heads-up/can't-verify, low-stakes gaps not headlined, the no-token exemplar) → Task 3 `hook_signal` + its tests. Fail-safe-never-block → Task 4 (`main` swallows all exceptions, exits 0, never sets `permissionDecision`). Once-per-session cache → Task 4 (`_already_grounded`). In-flight-change paths → Task 4 (`_changed_paths`). Performance/lazy no-op path → Task 4 (broker imported inside `_ground`, after the cache check). Dedicated `teamctx-hook` script → Task 4. To-verify items (settings schema, real-session delivery) are flagged for the dogfood; the schema is exercised by Task 5's tests.

**Placeholder scan:** none, every step has complete code and exact commands.

**Type/name consistency:** `work_start_answer`, `hook_signal(answer, *, file_path, token_present)`, `resolve_github_token`, `_HOOK_ENTRY`/`_HOOK_MATCHER`, `teamctx-hook` used consistently. Verdict labels ("Conflict check"/"Gate check"/"Docs check"/"Criteria check") match `CARD_KINDS` in `core/select.py`. `Valuation.value`/`.reason` and `ContextCard.section`/`.text`/`.why_this_matters` match `core/evaluate.py` and `core/select.py`.
