# Runtime Resolution Layer (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the one shared, honest resolution layer (project root, GitHub repo identity, GitHub credential) that every surface (hook, CLI work-start, MCP, init) uses identically, killing the setup/runtime split-brain. This is phase 1 of the approved spec `docs/superpowers/specs/2026-06-29-onboard-runtime-honesty.md` (sections 1.1, 1.2, 1.3).

**Architecture:** Three new pure-ish helpers in import-light modules: `git_context.resolve_project_root` (one root for everyone), `git_context.parse_github_repo` (validate a GitHub slug, fail closed on non-github), and `tokens.resolve_github_token` (env, file, then `gh` only on the default token env). Then rewire the existing call sites to use them, and enforce the repo invariant at the single chokepoint `WorkStartInputs.__post_init__`.

**Tech Stack:** Python 3.11+, pytest, click (CLI), frozen dataclasses, `subprocess` for git/gh. No new dependencies.

**Baseline:** Before Task 1, confirm the suite is green: `pytest -q` (expected: all pass). All work is on branch `feat/runtime-resolution`.

---

### Task 1: `parse_github_repo` and host-aware `detect_repo`

**Files:**
- Modify: `src/teamctx/git_context.py`
- Test: `tests/test_git_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_context.py  (add to existing file)
import pytest
from teamctx.git_context import parse_github_repo


@pytest.mark.parametrize(
    "value,expected",
    [
        ("owner/name", "owner/name"),
        ("owner/name/", "owner/name"),
        ("https://github.com/owner/name", "owner/name"),
        ("https://github.com/owner/name.git", "owner/name"),
        ("git@github.com:owner/name.git", "owner/name"),
    ],
)
def test_parse_github_repo_accepts_github(value, expected):
    assert parse_github_repo(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "https://gitlab.com/owner/name",       # non-github host fails closed
        "git@gitlab.com:owner/name.git",
        "owner",                                # one segment
        "owner/name/extra",                     # three segments
        "",                                     # empty
        "https://github.com/owner",             # github but not a full slug
    ],
)
def test_parse_github_repo_rejects(value):
    assert parse_github_repo(value) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_git_context.py -k parse_github_repo -v`
Expected: FAIL with `ImportError: cannot import name 'parse_github_repo'`.

- [ ] **Step 3: Implement `parse_github_repo`, and make `detect_repo` use it**

Replace the existing `detect_repo` and `parse_owner_name` in `src/teamctx/git_context.py` with:

```python
def detect_repo(root: Path) -> str | None:
    """``owner/name`` of the ``origin`` remote at ``root`` when it is a github.com remote, else
    ``None`` (honest absence). A non-github origin fails closed: it never becomes a GitHub query."""

    url = _run_git(root, "remote", "get-url", "origin")
    if url is None:
        return None
    return parse_github_repo(url)


def parse_github_repo(value: str) -> str | None:
    """Normalize a GitHub repo reference to ``owner/name``. Accepts a bare ``owner/name`` slug
    (github.com by the field's defined meaning) or a github.com URL (https or scp-style ssh).
    Returns ``None`` for a non-github host or anything that is not a clean two-segment slug, so a
    non-GitHub repo never enters a GitHub-bound path."""

    s = value.strip()
    if s.endswith(".git"):
        s = s[:-4]
    s = s.rstrip("/")
    if "://" in s:                       # scheme://host/owner/name
        after = s.split("://", 1)[1]
        host, _, rest = after.partition("/")
    elif "@" in s and ":" in s:          # git@host:owner/name (scp-style)
        host, _, rest = s.split("@", 1)[1].partition(":")
    elif ":" in s:                       # host:owner/name
        host, _, rest = s.partition(":")
    else:                                # bare owner/name slug
        host, rest = None, s
    if host is not None and host != "github.com":
        return None
    segments = [p for p in rest.strip("/").split("/") if p]
    if len(segments) != 2:
        return None
    return "/".join(segments)
```

(`parse_owner_name` is removed; `parse_github_repo` replaces it. `_run_git` is unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_git_context.py -v`
Expected: PASS (including any existing detect_repo/detect_branch tests; update a test that imported `parse_owner_name` to import `parse_github_repo`).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/git_context.py tests/test_git_context.py
git commit -m "feat: host-aware GitHub repo identity (parse_github_repo, fail closed on non-github)"
```

---

### Task 2: `resolve_project_root` shared helper

**Files:**
- Modify: `src/teamctx/git_context.py`
- Test: `tests/test_git_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_context.py  (add)
from pathlib import Path
from teamctx.git_context import resolve_project_root


def test_resolve_project_root_prefers_override(tmp_path):
    override = tmp_path / "explicit"
    override.mkdir()
    assert resolve_project_root(start=tmp_path, override=override) == override


def test_resolve_project_root_falls_back_to_start_when_non_git(tmp_path):
    # tmp_path is not a git repo, so toplevel is None and we get start back.
    assert resolve_project_root(start=tmp_path) == tmp_path


def test_resolve_project_root_uses_git_toplevel(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    sub = tmp_path / "src"
    sub.mkdir()
    # From a subdirectory, the resolved root is the repo toplevel, not the subdir.
    assert resolve_project_root(start=sub).resolve() == tmp_path.resolve()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_git_context.py -k resolve_project_root -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_project_root'`.

- [ ] **Step 3: Implement the helper**

Add to `src/teamctx/git_context.py`:

```python
def resolve_project_root(start: Path | None = None, override: Path | None = None) -> Path:
    """The project root every surface agrees on. ``override`` (for example MCP's
    ``TEAMCTX_PROJECT_ROOT``) wins; else the git toplevel of ``start``; else ``start`` itself
    (cwd fallback, so a non-git tree still works). ``start`` defaults to the current directory,
    resolved here rather than as an import-time default argument."""

    if override is not None:
        return override
    base = start if start is not None else Path.cwd()
    toplevel = _git_toplevel(base)
    return toplevel if toplevel is not None else base


def _git_toplevel(root: Path) -> Path | None:
    out = _run_git(root, "rev-parse", "--show-toplevel")
    return Path(out) if out is not None else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_git_context.py -k resolve_project_root -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/git_context.py tests/test_git_context.py
git commit -m "feat: resolve_project_root shared root helper (override > git toplevel > cwd)"
```

---

### Task 3: Enforce the GitHub repo invariant at the `WorkStartInputs` chokepoint

**Files:**
- Modify: `src/teamctx/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_runner.py  (add)
import pytest
from teamctx.runner import WorkStartInputs


def test_workstartinputs_accepts_valid_github_slug():
    inputs = WorkStartInputs(repo="owner/name", paths=("a.py",))
    assert inputs.repo == "owner/name"


def test_workstartinputs_rejects_non_github_repo():
    with pytest.raises(ValueError, match="GitHub repo"):
        WorkStartInputs(repo="https://gitlab.com/owner/name", paths=("a.py",))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_runner.py -k workstartinputs -v`
Expected: FAIL (no `ValueError` raised for the gitlab URL).

- [ ] **Step 3: Add the `__post_init__` validation**

In `src/teamctx/runner.py`, add the import and the validator on the frozen dataclass:

```python
from teamctx.git_context import parse_github_repo  # add to imports
```

```python
    # inside the WorkStartInputs dataclass, after the fields:
    def __post_init__(self) -> None:
        if parse_github_repo(self.repo) is None:
            raise ValueError(f"not a valid GitHub repo slug: {self.repo!r}")
```

This is the single chokepoint before the runner runs the GitHub connectors, so resolve, the dev probes that build inputs, and any direct construction are all covered.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_runner.py -v`
Expected: PASS (existing runner tests use `repo="owner/name"`-style slugs, which validate fine; fix any fixture that used a URL or invalid slug).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/runner.py tests/test_runner.py
git commit -m "feat: WorkStartInputs validates repo is a GitHub slug on construction (the invariant chokepoint)"
```

---

### Task 4: Validate `--repo` at resolve, init, and the dev probes

**Files:**
- Modify: `src/teamctx/resolve.py`, `src/teamctx/cli.py`
- Test: `tests/test_resolve.py`, `tests/test_init_command.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_resolve.py  (add)
import pytest
from teamctx.resolve import resolve_work_start_inputs, WorkStartResolutionError


def test_resolve_rejects_non_github_explicit_repo(tmp_path):
    with pytest.raises(WorkStartResolutionError):
        resolve_work_start_inputs(
            paths=("a.py",), repo="https://gitlab.com/o/n", root=tmp_path
        )
```

```python
# tests/test_init_command.py  (add)
def test_init_rejects_non_github_repo(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from teamctx.cli import main
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["init", "--repo", "git@gitlab.com:o/n.git"])
    assert result.exit_code != 0
    assert "GitHub" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_resolve.py -k non_github tests/test_init_command.py -k non_github -v`
Expected: FAIL (no error raised today; the gitlab repo is accepted).

- [ ] **Step 3: Validate at each boundary**

In `src/teamctx/resolve.py`, normalize and validate the resolved repo through `parse_github_repo` before building `WorkStartInputs`:

```python
from teamctx.git_context import detect_branch, detect_repo, parse_github_repo  # extend import
```

```python
    # replace the resolved_repo block:
    raw_repo = repo or _config_repo(config) or detect_repo(root)
    if raw_repo is None:
        raise WorkStartResolutionError(_REPO_UNRESOLVED)
    resolved_repo = parse_github_repo(raw_repo)
    if resolved_repo is None:
        raise WorkStartResolutionError(
            f"{raw_repo!r} is not a GitHub repo (owner/name). teamctx only checks GitHub today; "
            "pass a github.com repo with --github-repo or work_start.repo."
        )
```

In `src/teamctx/cli.py` `init_command`, validate `--repo` before writing config (around cli.py:82-91):

```python
    if repo is not None and parse_github_repo(repo) is None:
        raise click.ClickException(
            f"{repo!r} is not a GitHub repo (owner/name). teamctx only checks GitHub today."
        )
    resolved_repo = parse_github_repo(repo) if repo is not None else detect_repo(root)
```

In `src/teamctx/cli.py`, for each dev probe that takes a raw `--repo` and calls a connector directly (cli.py:116, 434, 474), add the same guard at the top of the command body:

```python
    if parse_github_repo(repo) is None:
        raise click.ClickException(f"{repo!r} is not a GitHub repo (owner/name).")
```

Add `parse_github_repo` to the `from teamctx.git_context import ...` line in cli.py.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_resolve.py tests/test_init_command.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/resolve.py src/teamctx/cli.py tests/test_resolve.py tests/test_init_command.py
git commit -m "feat: validate --repo as a GitHub slug at resolve, init, and dev probes (close the invariant)"
```

---

### Task 5: Route every root resolution through `resolve_project_root`

**Files:**
- Modify: `src/teamctx/cli.py`, `src/teamctx/mcp_server.py`, `src/teamctx/hook.py`
- Test: `tests/test_work_start_cli.py`, `tests/test_mcp_server.py`, `tests/test_hook.py`

- [ ] **Step 1: Write the failing test (subdirectory resolution)**

```python
# tests/test_work_start_cli.py  (add)
def test_work_start_finds_config_from_subdirectory(tmp_path, monkeypatch):
    import json, subprocess
    from click.testing import CliRunner
    from teamctx.cli import main
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".teamctx").mkdir()
    (tmp_path / ".teamctx" / "config.json").write_text(
        json.dumps({
            "schema_version": "teamctx.project_config.v0",
            "work_start": {"repo": "owner/name"},
        }),
        encoding="utf-8",
    )
    sub = tmp_path / "src"
    sub.mkdir()
    monkeypatch.chdir(sub)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    result = CliRunner().invoke(main, ["work-start", "--path", "src/x.py"])
    # Repo resolves from the committed config at the root, even though cwd is the subdir.
    assert "could not determine the repository" not in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_work_start_cli.py -k subdirectory -v`
Expected: FAIL (today `root=Path.cwd()` is the subdir, so the config is not found).

- [ ] **Step 3: Rewire the call sites**

In `src/teamctx/cli.py`, replace every `root=Path.cwd()` and `project_root=Path.cwd()` in `work_start` (cli.py:201, 206, 277, 281) and `init` (cli.py:82) with the resolved root:

```python
from teamctx.git_context import resolve_project_root  # extend import
...
    project_root = resolve_project_root()
    # then pass root=project_root and project_root=project_root
```

For the dev `_work_start_view` / authority load (cli.py:661), anchor `.teamctx/authority.json` to the resolved root:

```python
    declarations = load_declared_authority(resolve_project_root() / ".teamctx" / "authority.json")
```

For `install-hook` (cli.py:552-597), anchor the settings file under the resolved root when the
user did not override `--settings`. Change the option default to `None` and resolve it in the body:

```python
    # in install_hook_command, replace the default Path(".claude/settings.json") usage:
    settings_path = settings_path or (resolve_project_root() / ".claude" / "settings.json")
```

For the dev `docs-probe` (cli.py:428), pass the resolved root as the connector `base_dir` instead
of the implicit `Path(".")`:

```python
    document = run_docs_supersession_probe(
        ..., base_dir=resolve_project_root(),
    )
```

In `src/teamctx/mcp_server.py` (mcp_server.py:71-73), keep the `TEAMCTX_PROJECT_ROOT` override but route through the helper:

```python
from teamctx.git_context import resolve_project_root
...
    override = os.environ.get("TEAMCTX_PROJECT_ROOT")
    return resolve_project_root(override=Path(override) if override else None)
```

In `src/teamctx/hook.py`, delete the local `_git_toplevel` (hook.py:101) and import the shared one; resolve the root from the event cwd (hook.py:47):

```python
from teamctx.git_context import resolve_project_root, _git_toplevel  # _git_toplevel now shared
...
    root = resolve_project_root(start=Path(cwd))
    text = _ground(root, file_path)
```

(Path normalization in `_ground` keeps using `_git_toplevel`; it now lives in git_context.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_work_start_cli.py tests/test_mcp_server.py tests/test_hook.py tests/test_install_hook.py -v`
Expected: PASS, including the existing `test_mcp_server.py:125` override test (the override path is preserved) and the existing install-hook tests (anchoring keeps them green; update any that asserted a cwd-relative `.claude/settings.json` path).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py src/teamctx/mcp_server.py src/teamctx/hook.py tests/
git commit -m "feat: route work-start, init, MCP, hook, and authority root through resolve_project_root"
```

---

### Task 6: `resolve_github_token` with gh fallback and test isolation

**Files:**
- Modify: `src/teamctx/tokens.py`
- Create/Modify: `tests/conftest.py`
- Test: `tests/test_tokens.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tokens.py  (add)
from teamctx.tokens import resolve_github_token


def test_github_token_prefers_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    assert resolve_github_token() == "envtok"


def test_github_token_falls_back_to_gh_on_default(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.delenv("TEAMCTX_DISABLE_GH_AUTH", raising=False)
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token() == "ghtok"


def test_github_token_no_gh_for_custom_env(monkeypatch):
    # A custom token-env means the user controls the source: env/file only, never gh.
    monkeypatch.delenv("MY_TOKEN", raising=False)
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token("MY_TOKEN") is None


def test_github_token_gh_skipped_when_disabled(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
    monkeypatch.setattr("teamctx.tokens._gh_auth_token", lambda: "ghtok")
    assert resolve_github_token() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_tokens.py -k github_token -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_github_token'`.

- [ ] **Step 3: Implement the resolver**

Add to `src/teamctx/tokens.py` (it stays import-light: only `os`, `subprocess`, `pathlib`, no broker import):

```python
import subprocess  # add to imports


def resolve_github_token(token_env: str = "GITHUB_TOKEN") -> str | None:
    """``resolve_token`` plus a ``gh auth token`` fallback, but ONLY on the default
    ``GITHUB_TOKEN`` path. A custom ``token_env`` stays env then file only, so the existing
    'force the no-token path with a custom unset env var' behavior is preserved. The ``gh`` step
    is also skipped when ``TEAMCTX_DISABLE_GH_AUTH`` is set (test isolation)."""

    token = resolve_token(token_env)
    if token:
        return token
    if token_env != "GITHUB_TOKEN":
        return None
    if os.environ.get("TEAMCTX_DISABLE_GH_AUTH"):
        return None
    return _gh_auth_token()


def _gh_auth_token() -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None
```

- [ ] **Step 4: Add the global test isolation fixture**

In `tests/conftest.py` (create if absent, else add), disable the `gh` fallback for the whole suite so a developer's `gh` login never leaks in:

```python
import pytest


@pytest.fixture(autouse=True)
def _no_gh_auth(monkeypatch):
    monkeypatch.setenv("TEAMCTX_DISABLE_GH_AUTH", "1")
```

The targeted gh-fallback tests in Task 6 Step 1 override this by deleting the var and mocking `_gh_auth_token`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_tokens.py -v`
Expected: PASS, and existing `resolve_token` tests still pass (it is unchanged).

- [ ] **Step 6: Commit**

```bash
git add src/teamctx/tokens.py tests/test_tokens.py tests/conftest.py
git commit -m "feat: resolve_github_token (env, file, gh on default only) + suite-wide gh isolation"
```

---

### Task 7: Route every GitHub token call site through `resolve_github_token`

**Files:**
- Modify: `src/teamctx/hook.py`, `src/teamctx/mcp_server.py`, `src/teamctx/cli.py`
- Test: `tests/test_work_start_cli.py` (existing no-token + file-token tests must still pass)

- [ ] **Step 1: Confirm the contract tests exist and pass**

Run: `pytest tests/test_work_start_cli.py -k "token" -v`
Expected: PASS today (no-token degrades to unreachable; file-token works). These guard the rewire.

- [ ] **Step 2: Rewire the call sites**

Replace `resolve_token(...)` with `resolve_github_token(...)` at the GitHub runtime sites:
- `src/teamctx/hook.py:139`: `token = resolve_github_token()`
- `src/teamctx/mcp_server.py:63`: `token=resolve_github_token()`
- `src/teamctx/cli.py:200, 276, 467, 510, 653`: `token=resolve_github_token(token_env)`

Update each module's import: `from teamctx.tokens import resolve_token, resolve_github_token` (keep `resolve_token` where the generic env/file resolver is still wanted; here all the GitHub sites switch to `resolve_github_token`). The dev probes that pass a custom `token_env` keep working because a custom env disables the gh fallback (Task 6).

- [ ] **Step 3: Run the contract tests to verify they still pass**

Run: `pytest tests/test_work_start_cli.py -v`
Expected: PASS. The suite-wide `TEAMCTX_DISABLE_GH_AUTH` fixture (Task 6) keeps the no-token test deterministic even though the GitHub path now consults `gh` in production.

- [ ] **Step 4: Full gate**

Run: `pytest -q && ruff check src tests && mypy src`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/hook.py src/teamctx/mcp_server.py src/teamctx/cli.py
git commit -m "feat: GitHub token call sites (hook, MCP, CLI work-start) use resolve_github_token"
```

---

## Phase-1 done definition
`pytest -q`, `ruff check src tests`, and `mypy src` all green. The shared resolution layer is live: one root helper used by every surface, repo identity validated and fail-closed on non-github at every boundary, and the `gh` token fallback working in the hook/CLI/MCP with tests isolated from a developer's `gh` login. Merge `feat/runtime-resolution` to main (done-and-green standing rule), then start phase 2 (the honesty carrier, spec 1.4 to 1.7).
