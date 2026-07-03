# S4: Hardening Small Batch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close findings F6, F8, F10: a malformed `.teamctx/authority.json` gets a plain fail-closed message instead of a traceback; CI tests 3.12 and 3.13 and enforces the coverage gate the config already claims (current coverage 93.16%, so the 90% gate passes as-is); `teamctx-mcp` without the optional dependency prints an install hint instead of a raw ImportError.

**Architecture:** A typed `DeclaredAuthorityError` at the authority I/O edge, caught by the CLI (converted to ClickException) and the MCP tool (returned as the answer text); a thin `mcp_entry` wrapper module for the script entry point; a CI matrix + coverage step. No core changes.

**Tech Stack:** Python 3.12, pytest, click. Gate: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` plus `grep -rP '\x{2014}' src tests` empty.

**Branch:** separate worktree: `git worktree add ../teamctx-s4 -b feat/hardening-small-batch main`, all work inside `../teamctx-s4`.

**Spec:** `docs/superpowers/specs/2026-07-03-full-review-findings.md` findings F6, F8, F10 (binding).

---

### Task 1: DeclaredAuthorityError (F6)

**Files:**
- Modify: `src/teamctx/connectors/declared_authority.py`
- Modify: `src/teamctx/cli.py` (work_start_command ~line 219, `_resolve_work_start` ~line 296)
- Modify: `src/teamctx/mcp_server.py` (work_start ~line 67)
- Test: `tests/test_declared_authority.py` (extend), `tests/test_work_start_cli.py` (extend), `tests/test_mcp_server.py` (extend)

- [ ] **Step 1: Failing loader tests** (in `tests/test_declared_authority.py`, follow its existing tmp_path style):

```python
import pytest

from teamctx.connectors.declared_authority import (
    DeclaredAuthorityError,
    load_declared_authority,
)


def test_invalid_json_raises_plain_error(tmp_path) -> None:
    path = tmp_path / "authority.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError) as excinfo:
        load_declared_authority(path)
    assert "authority.json" in str(excinfo.value)
    assert "not valid" in str(excinfo.value)
    assert "Fix or remove" in str(excinfo.value)


def test_non_list_top_level_raises(tmp_path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('{"subject": "x"}', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_missing_key_raises(tmp_path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('[{"subject": "x"}]', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_non_dict_item_raises(tmp_path) -> None:
    path = tmp_path / "authority.json"
    path.write_text('["x"]', encoding="utf-8")
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)


def test_unreadable_file_raises(tmp_path) -> None:
    path = tmp_path / "authority.json"
    path.mkdir()  # a directory: read_text raises OSError
    with pytest.raises(DeclaredAuthorityError):
        load_declared_authority(path)
```

- [ ] **Step 2: verify fail.** **Step 3: Implement** in `declared_authority.py`:

```python
class DeclaredAuthorityError(ValueError):
    """The declared-authority file exists but cannot be read as authority declarations."""


def load_declared_authority(path: Path) -> list[AuthorityDecl]:
    """Read declared authority from ``path``. Returns ``[]`` if the file does not exist.
    A file that exists but is malformed raises ``DeclaredAuthorityError`` (fail closed with a
    plain, fixable message), never a raw traceback."""

    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DeclaredAuthorityError(
            f"{path} is not valid teamctx authority JSON ({exc}). Fix or remove the file."
        ) from exc
    if not isinstance(data, list):
        raise DeclaredAuthorityError(
            f"{path} is not valid teamctx authority JSON (expected a list of declarations). "
            "Fix or remove the file."
        )
    try:
        return [
            AuthorityDecl(
                subject=str(item["subject"]),
                source=str(item["source"]),
                priority=int(item["priority"]),
                value=str(item["value"]),
                fresh=bool(item["fresh"]),
            )
            for item in data
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise DeclaredAuthorityError(
            f"{path} is not valid teamctx authority JSON (a declaration is missing a field or "
            "has the wrong type). Fix or remove the file."
        ) from exc
```

Drop the now-unused `cast`/`Any` imports if nothing else uses them.

- [ ] **Step 4: CLI + MCP surfacing.** In `cli.py` `work_start_command`, the render call sits outside the existing try; wrap it:

```python
    try:
        output = render_work_start(inputs, observed_at=utc_now_iso(), project_root=project_root)
    except DeclaredAuthorityError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(output, nl=False)
```

In `_resolve_work_start`, add `DeclaredAuthorityError` to the wrap around `work_start_answer` (move the `work_start_answer` call inside the existing try, or a second try; either way the user gets a ClickException, not a traceback). In `mcp_server.work_start`, add `DeclaredAuthorityError` to the caught tuple so the tool returns the message as text. Import it from `teamctx.connectors.declared_authority` in both files.

Failing tests first: a CliRunner `work-start` test in `tests/test_work_start_cli.py` with a malformed `.teamctx/authority.json` in the project root asserting exit code 1 and "Fix or remove the file." in output (no traceback); an MCP test in `tests/test_mcp_server.py` asserting the returned string contains "Fix or remove the file.". Follow each file's existing scaffolding (tmp project root fixtures, fake opener/no-token patterns).

- [ ] **Step 5: full gate.** **Step 6: Commit** `fix(authority): malformed authority.json fails closed with a plain message (F6)`

---

### Task 2: teamctx-mcp import guard (F10)

**Files:**
- Create: `src/teamctx/mcp_entry.py`
- Modify: `pyproject.toml` ([project.scripts])
- Test: `tests/test_mcp_entry.py` (create)

- [ ] **Step 1: Failing tests:**

```python
import sys

import pytest


def test_missing_mcp_dependency_gets_plain_message(monkeypatch, capsys) -> None:
    # simulate the optional dep being absent: None in sys.modules makes `import mcp...` fail
    for name in [m for m in sys.modules if m == "mcp" or m.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.delitem(sys.modules, "teamctx.mcp_server", raising=False)
    monkeypatch.setitem(sys.modules, "mcp", None)

    from teamctx.mcp_entry import main

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    err = capsys.readouterr().err
    assert "pip install 'teamctx[mcp]'" in err


def test_present_dependency_delegates_to_server(monkeypatch) -> None:
    import teamctx.mcp_entry as entry
    import teamctx.mcp_server as server

    called: list[bool] = []
    monkeypatch.setattr(server, "main", lambda: called.append(True))
    entry.main()
    assert called == [True]
```

- [ ] **Step 2: verify fail.** **Step 3: Implement** `src/teamctx/mcp_entry.py`:

```python
"""Entry point for ``teamctx-mcp`` that fails with a plain message when the optional MCP
dependency is missing, instead of a raw ImportError traceback."""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from teamctx.mcp_server import main as server_main
    except ImportError as exc:
        name = getattr(exc, "name", None) or ""
        if name.split(".")[0] == "mcp":
            print(
                "teamctx-mcp needs the optional MCP dependency, which is not installed. "
                "Install it with: pip install 'teamctx[mcp]'",
                file=sys.stderr,
            )
            raise SystemExit(1) from exc
        raise
    server_main()
```

Note: `sys.modules["mcp"] = None` raises `ImportError` (not always `ModuleNotFoundError`) with `name` set on 3.12; catching `ImportError` and reading `.name` covers both. In `pyproject.toml` change the script to `teamctx-mcp = "teamctx.mcp_entry:main"`.

- [ ] **Step 4: full gate.** **Step 5: Commit** `fix(mcp): friendly install hint when the optional mcp dependency is missing (F10)`

---

### Task 3: CI matrix + coverage gate (F8)

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Rewrite the job:**

```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: ruff check src tests
      - run: mypy --strict src
      - run: pytest -q --cov
```

The coverage gate comes from pyproject's `[tool.coverage.report] fail_under = 90` (current coverage 93.16%). Local runs stay fast (`--cov` is CI-only, not in addopts).

- [ ] **Step 2: Sanity-run locally**: `python -m pytest -q -p no:cacheprovider --cov 2>&1 | tail -3` must end with the coverage requirement reached and all tests passing (CI itself cannot be run locally; this proves the coverage gate passes).
- [ ] **Step 3: Commit** `ci: test 3.12 and 3.13; enforce the coverage gate the config claims (F8)`

---

### Task 4: CHANGELOG

- [ ] Under `### Fixed` add:
  - `- A malformed .teamctx/authority.json now fails closed with a plain message naming the file and the fix, instead of a traceback (CLI and MCP).`
  - `- teamctx-mcp without the optional mcp dependency now prints an install hint instead of a raw ImportError.`
- [ ] Full gate + `grep -rP '\x{2014}' src tests` empty. Commit `docs(changelog): S4 hardening batch`

---

## Completion

Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch, commits (oneline), gate tail, files changed, deviations with reasons. The CTO reviews and merges.
