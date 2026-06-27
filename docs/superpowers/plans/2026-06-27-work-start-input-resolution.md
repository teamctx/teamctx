# Work-start Input Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `work_start` (CLI and MCP) resolve repo/branch/docs_root from git and `.teamctx/config.json` so an agent calls it with just `paths`, degrading to honest-UNKNOWN.

**Architecture:** A new transport-agnostic resolution layer (`resolve.py`) applies precedence `explicit > config > git-detect > honest-absent` and returns a `WorkStartInputs`. Git facts come from a thin read-only `git_context.py`; the stable project facts come from a new additive `work_start` section in the existing `project_config` model. Both transports call `resolve_work_start_inputs` before `render_work_start`, exactly as they already share that use case.

**Tech Stack:** Python 3.12, click (CLI), FastMCP (MCP), pydantic (config), pytest. ruff (`E,F,I,N,W,UP,B,SIM`, line 100) + mypy `--strict`.

---

## File structure

- **Create** `src/teamctx/git_context.py` — read-only git detection: `detect_repo`, `detect_branch`, `parse_owner_name`. No network.
- **Create** `src/teamctx/resolve.py` — `WorkStartResolutionError`, `resolve_work_start_inputs(...)`. The one resolution path both transports use.
- **Modify** `src/teamctx/project_config.py` — add `WorkStartConfig` model + `work_start` field on `ProjectConfig` (additive, backward-compatible, still `v0`).
- **Modify** `src/teamctx/cli.py` — `work-start`: `--github-repo` optional; resolve via `resolve_work_start_inputs`; remove now-unused `WorkStartInputs` import.
- **Modify** `src/teamctx/mcp_server.py` — `work_start`: `repo` optional, `paths` first; extract `_run_work_start` + `_resolution_root` (honours `TEAMCTX_PROJECT_ROOT`); resolution error returned as the tool's text.
- **Create** `tests/test_git_context.py`, `tests/test_resolve.py`; **Modify** `tests/test_project_config.py`, `tests/test_work_start_cli.py`, `tests/test_mcp_server.py`.

Dependency order: Task 1 (git_context) and Task 2 (config) are independent; Task 3 (resolve) needs both; Tasks 4–5 (transports) need Task 3; Task 6 verifies the whole.

---

## Task 1: git detection module

**Files:**
- Create: `src/teamctx/git_context.py`
- Test: `tests/test_git_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_git_context.py
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from teamctx.git_context import detect_branch, detect_repo, parse_owner_name


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("git@github.com:acme/widgets.git", "acme/widgets"),
        ("https://github.com/acme/widgets.git", "acme/widgets"),
        ("https://github.com/acme/widgets", "acme/widgets"),
        ("ssh://git@github.com/acme/widgets.git", "acme/widgets"),
        ("https://github.com/acme/widgets/", "acme/widgets"),
        ("not-a-url", None),
        ("", None),
    ],
)
def test_parse_owner_name(url: str, expected: str | None) -> None:
    assert parse_owner_name(url) == expected


def _init_repo(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)


def test_detect_repo_and_branch_in_a_real_repo(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "git@github.com:acme/widgets.git"], check=True,
    )
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "feature"], check=True)
    assert detect_repo(tmp_path) == "acme/widgets"
    assert detect_branch(tmp_path) == "feature"


def test_detect_returns_none_outside_a_repo(tmp_path: Path) -> None:
    assert detect_repo(tmp_path) is None
    assert detect_branch(tmp_path) is None


def test_detect_branch_none_when_detached(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    head = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-q", head], check=True)
    assert detect_branch(tmp_path) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_git_context.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'teamctx.git_context'`.

- [ ] **Step 3: Implement the module**

```python
# src/teamctx/git_context.py
"""Read-only git detection for work-start input resolution.

Resolves the two facts git already knows about a working tree — the repository identity
(owner/name from the ``origin`` remote) and the current branch. Any failure returns ``None``
(honest absence), never a guess, so a non-git or unreachable tree degrades to the broker's
honest-UNKNOWN rather than a fabricated value. No network I/O.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def detect_repo(root: Path) -> str | None:
    """``owner/name`` of the ``origin`` remote at ``root``, or ``None`` if undeterminable."""

    url = _run_git(root, "remote", "get-url", "origin")
    if url is None:
        return None
    return parse_owner_name(url)


def detect_branch(root: Path) -> str | None:
    """Current branch at ``root``, or ``None`` for detached HEAD or non-git."""

    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None or branch == "HEAD":  # "HEAD" means detached
        return None
    return branch


def parse_owner_name(url: str) -> str | None:
    """Extract ``owner/name`` from a git remote URL (scp-style, ssh://, or https)."""

    s = url.strip()
    if s.endswith(".git"):
        s = s[:-4]
    s = s.rstrip("/")
    if "://" in s:
        after_scheme = s.split("://", 1)[1]
        rest = after_scheme.split("/", 1)[1] if "/" in after_scheme else ""
    elif ":" in s:
        rest = s.split(":", 1)[1]
    else:
        rest = s
    segments = [part for part in rest.strip("/").split("/") if part]
    if len(segments) >= 2:
        return "/".join(segments[-2:])
    return None


def _run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    output = result.stdout.strip()
    return output or None
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_git_context.py -v`
Expected: PASS (all parametrize cases + 3 repo tests).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/git_context.py tests/test_git_context.py
git commit -m "feat: read-only git detection for repo + branch (Sprint 1)"
```

---

## Task 2: work_start config section

**Files:**
- Modify: `src/teamctx/project_config.py`
- Test: `tests/test_project_config.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_project_config.py`)

```python
def test_project_config_loads_work_start_section(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "acme/widgets", "docs_root": "docs"},
            }
        ),
        encoding="utf-8",
    )
    config = load_project_config(config_path)
    assert config.work_start is not None
    assert config.work_start.repo == "acme/widgets"
    assert config.work_start.docs_root == "docs"


def test_project_config_without_work_start_is_none(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {"schema_version": "teamctx.project_config.v0", "github": {"repo": "org/app"}}
        ),
        encoding="utf-8",
    )
    config = load_project_config(config_path)
    assert config.work_start is None


def test_work_start_section_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {"repo": "acme/widgets", "surprise": True},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProjectConfigError):
        load_project_config(config_path)
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_project_config.py -k work_start -v`
Expected: FAIL — `AttributeError`/validation: `ProjectConfig` has no `work_start`.

- [ ] **Step 3: Implement the models** — in `src/teamctx/project_config.py`, add `WorkStartConfig` after `GitHubSourceConfig`, and the `work_start` field on `ProjectConfig`.

```python
class WorkStartConfig(StrictConfigModel):
    """Project-stable inputs for the work-start broker, shared across actors (committed).
    Per-actor secrets (the token) live in the environment, never here."""

    repo: str | None = None
    docs_root: str | None = None


class ProjectConfig(StrictConfigModel):
    schema_version: Literal["teamctx.project_config.v0"]
    github: GitHubSourceConfig | None = None
    default_output: str = DEFAULT_OUTPUT_PATH
    work_start: WorkStartConfig | None = None
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_project_config.py -v`
Expected: PASS (new tests + all pre-existing config tests still green — backward compatible).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/project_config.py tests/test_project_config.py
git commit -m "feat: additive work_start config section (repo, docs_root)"
```

---

## Task 3: input resolution layer

**Files:**
- Create: `src/teamctx/resolve.py`
- Test: `tests/test_resolve.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_resolve.py
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import teamctx.resolve as resolve_mod
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs


def _write_config(root: Path, **work_start: str) -> None:
    (root / ".teamctx").mkdir(parents=True, exist_ok=True)
    (root / ".teamctx" / "config.json").write_text(
        json.dumps({"schema_version": "teamctx.project_config.v0", "work_start": work_start}),
        encoding="utf-8",
    )


def test_explicit_repo_wins_over_config_and_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), repo="from/explicit", root=tmp_path)
    assert inputs.repo == "from/explicit"


def test_config_repo_wins_over_git(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/config"


def test_git_used_when_no_explicit_or_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: "from/git")
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "feature")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "from/git"
    assert inputs.branch == "feature"


def test_missing_repo_raises(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: None)
    with pytest.raises(WorkStartResolutionError):
        resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)


def test_branch_from_git_not_config_and_docs_root_from_config(monkeypatch, tmp_path: Path) -> None:
    _write_config(tmp_path, repo="from/config", docs_root="docs")
    monkeypatch.setattr(resolve_mod, "detect_repo", lambda root: None)
    monkeypatch.setattr(resolve_mod, "detect_branch", lambda root: "detected")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.branch == "detected"
    assert inputs.docs_root == "docs"


def test_resolves_from_a_real_repo_and_config(tmp_path: Path) -> None:
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "i"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "checkout", "-qb", "feat"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "remote", "add", "origin",
         "https://github.com/acme/widgets.git"], check=True,
    )
    _write_config(tmp_path, docs_root="docs")
    inputs = resolve_work_start_inputs(paths=("src/x.py",), root=tmp_path)
    assert inputs.repo == "acme/widgets"
    assert inputs.branch == "feat"
    assert inputs.docs_root == "docs"
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_resolve.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'teamctx.resolve'`.

- [ ] **Step 3: Implement the resolver**

```python
# src/teamctx/resolve.py
"""Resolve a work-start request's inputs from the caller, project config, and git.

Both transports (the CLI and the MCP tool) call ``resolve_work_start_inputs`` before running
the broker, so they resolve identically. Precedence per field is
``explicit > .teamctx/config.json > git-detection > honest-absent``. Branch is never read from
config (it is volatile). A repository that cannot be resolved from any source raises
``WorkStartResolutionError`` — there is nothing to check, so that is a setup error, not a
coverage gap.
"""

from __future__ import annotations

from pathlib import Path

from teamctx.git_context import detect_branch, detect_repo
from teamctx.project_config import (
    DEFAULT_CONFIG_PATH,
    WorkStartConfig,
    maybe_load_project_config,
)
from teamctx.runner import WorkStartInputs

_REPO_UNRESOLVED = (
    "could not determine the repository: not in a git repo with a recognizable 'origin' "
    "remote, and no work_start.repo in .teamctx/config.json. Pass the repo explicitly "
    "(--github-repo / repo=)."
)


class WorkStartResolutionError(ValueError):
    """Raised when a required work-start input (the repository) cannot be resolved."""


def resolve_work_start_inputs(
    *,
    paths: tuple[str, ...],
    repo: str | None = None,
    branch: str | None = None,
    docs_root: str | None = None,
    task: str = "Start work.",
    issues: tuple[str, ...] = (),
    since: str | None = None,
    ref: str | None = None,
    include_titles: bool = False,
    token: str | None = None,
    root: Path,
    config_path: Path | None = None,
) -> WorkStartInputs:
    config = _load_work_start_config(root, config_path)

    resolved_repo = repo or _config_repo(config) or detect_repo(root)
    if resolved_repo is None:
        raise WorkStartResolutionError(_REPO_UNRESOLVED)

    return WorkStartInputs(
        repo=resolved_repo,
        paths=tuple(paths),
        branch=branch or detect_branch(root),
        task=task,
        token=token,
        include_titles=include_titles,
        issues=tuple(issues),
        since=since,
        docs_root=docs_root or _config_docs_root(config),
        ref=ref,
    )


def _load_work_start_config(root: Path, config_path: Path | None) -> WorkStartConfig | None:
    path = config_path if config_path is not None else root / DEFAULT_CONFIG_PATH
    project = maybe_load_project_config(path)
    return project.work_start if project is not None else None


def _config_repo(config: WorkStartConfig | None) -> str | None:
    return config.repo if config is not None else None


def _config_docs_root(config: WorkStartConfig | None) -> str | None:
    return config.docs_root if config is not None else None
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_resolve.py -v`
Expected: PASS (all 6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/resolve.py tests/test_resolve.py
git commit -m "feat: work-start input resolution (explicit > config > git > absent)"
```

---

## Task 4: wire the CLI work-start command

**Files:**
- Modify: `src/teamctx/cli.py` (the `work-start` command + imports)
- Test: `tests/test_work_start_cli.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_work_start_cli.py`; add imports `import subprocess` and `from pathlib import Path` at the top)

```python
def _init_repo_with_origin(root: Path, url: str, branch: str) -> None:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    (root / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "init"], check=True)
    subprocess.run(["git", "-C", str(root), "checkout", "-qb", branch], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", url], check=True)


def test_work_start_resolves_repo_from_git_without_flag(monkeypatch, tmp_path: Path) -> None:
    _init_repo_with_origin(tmp_path, "git@github.com:acme/widgets.git", "feature")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        main,
        ["work-start", "--path", "src/widgets/core.py",
         "--token-env", "TEAMCTX_DEFINITELY_UNSET_TOKEN"],
    )
    assert result.exit_code == 0, result.output
    assert "Working context" in result.output
    assert "Conflict check: UNKNOWN" in result.output  # repo resolved, no token => honest


def test_work_start_errors_when_repo_unresolvable(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)  # not a git repo, no config
    result = CliRunner().invoke(main, ["work-start", "--path", "src/x.py"])
    assert result.exit_code != 0
    assert "could not determine the repository" in result.output
```

Also **update** the existing `test_work_start_with_no_token_degrades_honestly` so auto-detection does not fire (it omits `--branch`): change its signature to `(monkeypatch, tmp_path)` and add `monkeypatch.chdir(tmp_path)` as the first line. Keep `--github-repo acme/widgets` and all existing assertions.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_work_start_cli.py -v`
Expected: FAIL — `test_work_start_resolves_repo_from_git_without_flag` errors because `--github-repo` is currently required.

- [ ] **Step 3: Implement** — in `src/teamctx/cli.py`:

(a) Remove the unused import line `from teamctx.runner import WorkStartInputs`.
(b) Add `from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs`.
(c) Change the `--github-repo` option from `required=True` to optional:

```python
@click.option(
    "--github-repo", "repo", default=None,
    help="GitHub repo owner/name. Optional: auto-detected from the git 'origin' remote or "
         ".teamctx/config.json when omitted.",
)
```

(d) Replace the body of `work_start_command` (the `inputs = WorkStartInputs(...)` construction and the `click.echo(...)`) with:

```python
    try:
        inputs = resolve_work_start_inputs(
            paths=paths,
            repo=repo,
            branch=branch,
            docs_root=docs_root,
            task=task,
            issues=issues,
            since=since,
            ref=ref,
            include_titles=include_title,
            token=os.environ.get(token_env),
            root=Path.cwd(),
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(render_work_start(inputs, observed_at=_utc_now_string()), nl=False)
```

(`ProjectConfigError` and `Path` are already imported in `cli.py`.)

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_work_start_cli.py -v`
Expected: PASS (2 new + 2 updated/existing).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_work_start_cli.py
git commit -m "feat: work-start CLI auto-resolves repo/branch/docs_root"
```

---

## Task 5: wire the MCP work_start tool

**Files:**
- Modify: `src/teamctx/mcp_server.py`
- Test: `tests/test_mcp_server.py`

- [ ] **Step 1: Write the failing / updated tests** in `tests/test_mcp_server.py`

Add two new tests:

```python
def test_work_start_resolves_repo_from_root(monkeypatch, tmp_path) -> None:
    import subprocess

    import teamctx.mcp_server as mcp_server

    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "i"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin",
                    "git@github.com:acme/widgets.git"], check=True)
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))

    captured: dict[str, object] = {}

    def fake_render(inputs, *, observed_at):  # type: ignore[no-untyped-def]
        captured["repo"] = inputs.repo
        return "ok"

    monkeypatch.setattr(mcp_server, "render_work_start", fake_render)
    assert work_start(paths=["src/x.py"]) == "ok"
    assert captured["repo"] == "acme/widgets"


def test_work_start_returns_error_text_when_repo_unresolvable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))  # non-git, no config
    out = work_start(paths=["src/x.py"])
    assert "could not determine the repository" in out
```

**Update** the three existing tests that call the tool so detection cannot reach a real repo (the collision test would otherwise hit the network). Add `tmp_path` to each signature and set the root env as the first line:

- `test_work_start_tool_is_directly_callable_and_degrades_without_token(monkeypatch, tmp_path)` → add `monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))`.
- `test_work_start_tool_surfaces_a_collision(monkeypatch, tmp_path)` → add `monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))`.
- `test_call_tool_runs_the_broker_over_mcp(monkeypatch, tmp_path)` → add `monkeypatch.setenv("TEAMCTX_PROJECT_ROOT", str(tmp_path))`.

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_mcp_server.py -v`
Expected: FAIL — new tests fail (`work_start(paths=...)` requires `repo`; no `_resolution_root`).

- [ ] **Step 3: Implement** — in `src/teamctx/mcp_server.py`:

(a) Replace `from teamctx.runner import WorkStartInputs` with:

```python
from teamctx.project_config import ProjectConfigError
from teamctx.resolve import WorkStartResolutionError, resolve_work_start_inputs
```

(b) Append to `_WORK_START_DESCRIPTION` (inside the string): ` Repo, branch, and docs root are auto-detected from the working tree and .teamctx/config.json; pass them only to override.`

(c) Replace the `work_start` tool function and add the helpers:

```python
@mcp.tool(name="work_start", description=_WORK_START_DESCRIPTION)
def work_start(
    paths: list[str],
    repo: str | None = None,
    branch: str | None = None,
    task: str = "Start work.",
    issues: list[str] | None = None,
    since: str | None = None,
    docs_root: str | None = None,
    ref: str | None = None,
) -> str:
    """Run the unified work-start broker and return its answer as text.

    paths: files the work will touch (required). repo/branch/docs_root are auto-detected from
    the server's working tree and ``.teamctx/config.json``; pass them only to override.
    """

    return _run_work_start(
        paths=paths, repo=repo, branch=branch, task=task,
        issues=issues, since=since, docs_root=docs_root, ref=ref,
    )


def _run_work_start(
    *,
    paths: list[str],
    repo: str | None,
    branch: str | None,
    task: str,
    issues: list[str] | None,
    since: str | None,
    docs_root: str | None,
    ref: str | None,
) -> str:
    try:
        inputs = resolve_work_start_inputs(
            paths=tuple(paths),
            repo=repo,
            branch=branch,
            docs_root=docs_root,
            task=task,
            issues=tuple(issues or ()),
            since=since,
            ref=ref,
            token=_resolve_github_token(),
            root=_resolution_root(),
        )
    except (WorkStartResolutionError, ProjectConfigError) as exc:
        return str(exc)
    return render_work_start(inputs, observed_at=_utc_now_string())


def _resolution_root() -> Path:
    override = os.environ.get("TEAMCTX_PROJECT_ROOT")
    return Path(override) if override else Path.cwd()
```

- [ ] **Step 4: Run to verify pass**

Run: `pytest tests/test_mcp_server.py -v`
Expected: PASS (2 new + 3 updated + the unchanged token/list-tools tests).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: MCP work_start auto-resolves repo; root via TEAMCTX_PROJECT_ROOT"
```

---

## Task 6: full verification

**Files:** none (verification only)

- [ ] **Step 1: Full test suite**

Run: `pytest`
Expected: PASS — all pre-existing tests plus the new ones (no regressions).

- [ ] **Step 2: Lint**

Run: `ruff check src tests`
Expected: clean. (If an unused-import `F401` appears for `WorkStartInputs`, confirm it was removed from `cli.py` and `mcp_server.py`.)

- [ ] **Step 3: Types**

Run: `mypy src`
Expected: clean under `--strict`.

- [ ] **Step 4: Commit any fixups**

```bash
git add -A
git commit -m "chore: lint/type fixups for work-start input resolution" || echo "nothing to fix"
```

---

## Self-Review

**1. Spec coverage:**
- Resolution layer (`resolve.py`) → Task 3. Git helper (`git_context.py`) → Task 1. `work_start` config section → Task 2. Precedence per field → Task 3 tests. Honest-UNKNOWN edges: repo-missing error → Tasks 3/4/5; branch/docs absent → covered by no-token CLI test + resolve unit tests (connector not run). Fork safety (config overrides git) → `test_config_repo_wins_over_git` (Task 3). Resolution root / `TEAMCTX_PROJECT_ROOT` → Task 5. Both transports share one path → Tasks 4 & 5 both call `resolve_work_start_inputs`. All spec sections map to a task.
- Non-goals (linked-issue discovery, legacy retirement, breadth) correctly absent.

**2. Placeholder scan:** No TBD/TODO; every code step contains complete code; every command has expected output.

**3. Type/name consistency:** `resolve_work_start_inputs`, `WorkStartResolutionError`, `WorkStartConfig`, `detect_repo`/`detect_branch`/`parse_owner_name`, `_run_work_start`/`_resolution_root`, `TEAMCTX_PROJECT_ROOT` used consistently across tasks. `WorkStartInputs` fields (repo, paths, branch, task, token, include_titles, issues, since, docs_root, ref) match `runner.py`.
