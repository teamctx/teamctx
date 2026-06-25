# CP1 — Missed-Gate Vertical (teamctx CI + check-runs connector) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Light up teamctx's **second live source on a repo we actually build** — itself. Add CI (GitHub Actions) so check-runs exist, then a `missed-gate` connector that surfaces "a required gate is failing on the files you're about to change," dogfooded on teamctx.

**Architecture:** Mirror the collision connector's two-module split (`github.py` I/O + `forge_review.py` normalizer). Slice A is config: a GitHub Actions workflow running the existing gates (ruff/mypy/pytest), which produces check-runs. Slice B adds a **pure normalizer** (`gate_status.py`) emitting `missed_gate` signals (scope `{repo, files}`, family `ci_deploy`) and a thin **I/O probe** (`github_checks.py`) that fetches failing check-runs via the *existing* `github.py` `get_json`/auth, plus a `gate-probe` CLI command sharing `_work_start_view`. The engine is **unchanged** — the `gate_failed` kind (derive, render, "Gate check" verdict, deps_G `ci_deploy`) already exists. Slice C is the dogfood.

**Tech Stack:** Python 3.12, click, pydantic, pytest/ruff/mypy; GitHub Actions YAML; stdlib `urllib` (reused from `github.py`). No new deps.

**Spike resolved (the `files` question):** GitHub check-runs don't report per-file coverage, and teamctx's gates are whole-repo. So v1 scopes a failing gate to `request.paths` — "the whole-repo gate is red and you're about to change code under it." The engine derive intersects `scope["files"]` with `request.paths`; setting `files = request.paths` means it fires whenever CI is red and you're touching code. Refinement (scope to branch-changed files via local `git diff`) is **deferred** until the dogfood shows the coarse version is too noisy.

**Prerequisite (Slice C):** real check-runs require the workflow **pushed** to `origin` (teamctx is already a GitHub repo we push `main` to). Slices A–B build + test locally with fixtures; Slice C needs a push to activate Actions — that's Edgar's go.

---

## File structure
- `.github/workflows/ci.yml` (new) — CI: ruff/mypy/pytest on push + PR.
- `src/teamctx/connectors/gate_status.py` (new, pure normalizer) — `FailingGate` + `normalize_failing_gates` + `unavailable_gates_document` + private helpers.
- `src/teamctx/connectors/github_checks.py` (new, I/O edge) — `run_github_checks_probe` + `fetch_failing_check_runs` + `FAILING_CONCLUSIONS`; reuses `github.py` (`get_json`, auth, `split_repo`, `GitHubProbeError`, `github_error_message`, `GITHUB_API_ROOT`, `HttpOpener`, `DEFAULT_OPENER`).
- `src/teamctx/cli.py` (modify) — add `gate-probe` command; reuse `_work_start_view`.
- `tests/test_gate_status.py` (new) — normalizer + probe (injected opener).
- `tests/test_gate_probe_cli.py` (new) — CLI end-to-end with injected opener.

Engine files are **not** touched (the `missed_gate` kind already exists).

---

## Task 0: Branch + plan

- [ ] **Step 1: Branch**
```bash
cd /home/eparenti/agents/repos/teamctx && git checkout -b build/cp1-missed-gate
```
- [ ] **Step 2: Commit this plan**
```bash
git add docs/superpowers/plans/2026-06-21-cp1-missed-gate-vertical.md
git commit -m "docs: CP1 missed-gate vertical plan"
```

---

## Task 1 (Slice A): CI workflow

**Files:** Create `.github/workflows/ci.yml`.

- [ ] **Step 1: Write the workflow**
```yaml
name: CI
on:
  push:
  pull_request:
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: ruff check src
      - run: mypy --strict src
      - run: pytest -q
```
- [ ] **Step 2: Validate locally** (YAML parses; the three gate commands match what we run)
```bash
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('yaml ok')" 2>/dev/null || python -c "print('no pyyaml; visual-check the YAML')"
ruff check src && mypy --strict src && pytest -q
```
Expected: the three commands pass locally (they are the gates CI will run).
- [ ] **Step 3: Commit**
```bash
git add .github/workflows/ci.yml
git commit -m "ci: run ruff + mypy --strict + pytest on push and PR"
```
> Note: CI only *runs* once pushed to `origin` (Slice C). This task just lands the workflow.

---

## Task 2 (Slice B.1): the gate-status normalizer

**Files:** Create `src/teamctx/connectors/gate_status.py`; `tests/test_gate_status.py`.

- [ ] **Step 1: Write the failing test** (`tests/test_gate_status.py`)
```python
from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    unavailable_gates_document,
)
from teamctx.core.contracts import RequestContext


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="teamctx/teamctx",
        branch="build/x",
        task="work",
        paths=["src/teamctx/core/select.py"],
        linked_issues=[],
        requested_at="2026-06-21T00:00:00Z",
        requesting_principal=None,
    )


def test_normalize_emits_missed_gate_signal_with_scope() -> None:
    gate = FailingGate(
        repo="teamctx/teamctx", gate_name="pytest", url="https://gh/run/1",
        files=("src/teamctx/core/select.py",),
    )
    doc = normalize_failing_gates(_request(), [gate], observed_at="2026-06-21T00:00:00Z")
    assert len(doc.source_signals) == 1
    sig = doc.source_signals[0]
    assert sig.signal_type == "missed_gate"
    assert sig.source_family == "ci_deploy"
    assert sig.scope["repo"] == "teamctx/teamctx"
    assert sig.scope["files"] == ["src/teamctx/core/select.py"]
    assert any(s.source_family == "ci_deploy" and s.status == "fresh" for s in doc.source_statuses)


def test_unavailable_gates_document_reports_status_only() -> None:
    doc = unavailable_gates_document(
        _request(), repo="teamctx/teamctx", observed_at="2026-06-21T00:00:00Z",
        safe_user_message="CI status unavailable.",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"
```
- [ ] **Step 2: Run → FAIL** (`ModuleNotFoundError: teamctx.connectors.gate_status`)
```bash
python -m pytest tests/test_gate_status.py -v
```
- [ ] **Step 3: Implement** (`src/teamctx/connectors/gate_status.py`)
```python
"""CI gate-status normalization.

Turns failing-gate facts into Core Contract V0 objects. No file/network I/O and no card
rendering — work-start DERIVES missed-gate cards from the signals emitted here.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    CoreContractDocument,
    PolicyDecision,
    RequestContext,
    Scope,
    SourceSignal,
    SourceStatus,
    SourceStatusValue,
)


@dataclass(frozen=True)
class FailingGate:
    """A required CI gate that is failing. ``files`` are repo-relative POSIX paths the gate
    covers (v1: the request paths, since the gate is whole-repo)."""

    repo: str
    gate_name: str
    url: str
    files: tuple[str, ...]


def normalize_failing_gates(
    request_context: RequestContext,
    gates: Iterable[FailingGate],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "github_check_runs",
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    for gate in gates:
        scope: Scope = {
            "repo": gate.repo,
            "files": list(gate.files),
            "gate": gate.gate_name,
            "url": gate.url,
        }
        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=f"sig_missed_gate_{_slug(gate.gate_name)}",
                signal_type="missed_gate",
                source_family="ci_deploy",
                scope=scope,
                evidence_summary=f"Required gate '{gate.gate_name}' is failing on this branch.",
                source_display=f"CI: {gate.gate_name}",
                freshness="fresh",
                confidence="high",
                visibility="visible",
                created_at=observed_at,
                observed_at=observed_at,
                expires_at=expires_at,
                policy=_policy_metadata_only(),
            )
        )
    source_statuses = [
        _ci_source_status(
            source_id=source_id,
            repo=request_context.repo,
            status="fresh",
            observed_at=observed_at,
            safe_user_message="CI check-run status refreshed.",
            visibility="silent",
        )
    ]
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=source_signals,
        source_statuses=source_statuses,
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def unavailable_gates_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "github_check_runs",
    status: SourceStatusValue = "unavailable",
    safe_user_message: str,
) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            _ci_source_status(
                source_id=source_id,
                repo=repo,
                status=status,
                observed_at=observed_at,
                safe_user_message=safe_user_message,
                visibility="warning_when_relevant",
            )
        ],
        source_open_targets=[],
        guidance_records=[],
        session_context_uses=[],
        context_cards=[],
    )


def _ci_source_status(
    *,
    source_id: str,
    repo: str,
    status: SourceStatusValue,
    observed_at: str,
    safe_user_message: str,
    visibility: Literal["silent", "warning_when_relevant", "always"],
) -> SourceStatus:
    return SourceStatus(
        schema_version="teamctx.source_status.v0",
        source_id=source_id,
        source_family="ci_deploy",
        scope={"repo": repo},
        status=status,
        last_checked_at=observed_at if status != "stale" else None,
        safe_user_message=safe_user_message,
        normal_context_visibility=visibility,
        policy=_policy_metadata_only(),
    )


def _policy_metadata_only() -> PolicyDecision:
    return PolicyDecision(
        schema_version="teamctx.policy_decision.v0",
        can_render_to_user=True,
        can_render_to_agent=True,
        can_include_source_text=False,
        requires_review_for_guidance=False,
        decision_reason="CI gate status is allowed as evidence; source bodies are not included.",
    )


def _slug(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name)
```
- [ ] **Step 4: Run → PASS** (2 passed). Also `ruff check src` + `mypy --strict src` clean. If a contract validator rejects an object, STOP and report the exact error.
- [ ] **Step 5: Commit**
```bash
git add src/teamctx/connectors/gate_status.py tests/test_gate_status.py
git commit -m "feat: normalize failing CI gates into Core Contract signals"
```

---

## Task 3 (Slice B.2): the check-runs probe

**Files:** Create `src/teamctx/connectors/github_checks.py`; append to `tests/test_gate_status.py`.

- [ ] **Step 1: Append the failing test** (`tests/test_gate_status.py`)
```python
from teamctx.connectors.github_checks import parse_failing_check_runs, run_github_checks_probe


def test_parse_failing_check_runs_keeps_only_failing() -> None:
    payload = {"check_runs": [
        {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"},
        {"name": "ruff", "status": "completed", "conclusion": "success", "html_url": "u2"},
        {"name": "mypy", "status": "in_progress", "conclusion": None, "html_url": "u3"},
    ]}
    failing = parse_failing_check_runs(payload)
    assert failing == [("pytest", "u1")]


def test_probe_uses_injected_opener_and_scopes_to_request_paths() -> None:
    import json

    class _Resp:
        def __init__(self, body: bytes) -> None:
            self._b = body
        def read(self) -> bytes:
            return self._b
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self
        def __exit__(self, *a: object) -> None:
            return None

    def opener(request):  # type: ignore[no-untyped-def]
        body = json.dumps({"check_runs": [
            {"name": "pytest", "status": "completed", "conclusion": "failure", "html_url": "u1"}
        ]}).encode()
        return _Resp(body)

    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token="t",
        request_context=_request(), observed_at="2026-06-21T00:00:00Z", opener=opener,
    )
    assert len(doc.source_signals) == 1
    sig = doc.source_signals[0]
    assert sig.signal_type == "missed_gate"
    assert sig.scope["files"] == ["src/teamctx/core/select.py"]  # scoped to request.paths


def test_probe_without_token_is_unavailable() -> None:
    doc = run_github_checks_probe(
        repo="teamctx/teamctx", ref="build/x", token=None,
        request_context=_request(), observed_at="2026-06-21T00:00:00Z",
    )
    assert doc.source_signals == []
    assert doc.source_statuses[0].status == "unavailable"
```
- [ ] **Step 2: Run → FAIL** (`ImportError: cannot import name ... github_checks`)
```bash
python -m pytest tests/test_gate_status.py -v
```
- [ ] **Step 3: Implement** (`src/teamctx/connectors/github_checks.py`) — reuse `github.py`
```python
"""Narrow GitHub check-runs probe: surface failing required gates for a ref."""

from __future__ import annotations

from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    unavailable_gates_document,
)
from teamctx.connectors.github import (
    DEFAULT_OPENER,
    GITHUB_API_ROOT,
    GitHubProbeError,
    HttpOpener,
    get_json,
    github_error_message,
    split_repo,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

# A completed check with one of these conclusions is a failing gate.
FAILING_CONCLUSIONS = frozenset({"failure", "timed_out", "action_required"})


def run_github_checks_probe(
    *,
    repo: str,
    ref: str,
    token: str | None,
    request_context: RequestContext,
    observed_at: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if not token:
        return unavailable_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="CI status is unavailable because no token is configured.",
        )
    try:
        failing = fetch_failing_check_runs(repo=repo, ref=ref, token=token, opener=opener)
    except GitHubProbeError as exc:
        return unavailable_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message=github_error_message(exc),
        )
    gates = [
        FailingGate(repo=repo, gate_name=name, url=url, files=tuple(request_context.paths))
        for name, url in failing
    ]
    return normalize_failing_gates(request_context, gates, observed_at=observed_at)


def fetch_failing_check_runs(
    *, repo: str, ref: str, token: str, opener: HttpOpener = DEFAULT_OPENER
) -> list[tuple[str, str]]:
    from urllib.parse import quote

    owner, name = split_repo(repo)
    url = f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}/commits/{quote(ref)}/check-runs"
    payload = get_json(url, token=token, opener=opener)
    return parse_failing_check_runs(payload)


def parse_failing_check_runs(payload: object) -> list[tuple[str, str]]:
    if not isinstance(payload, dict):
        raise GitHubProbeError("GitHub check-runs response was not an object")
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        return []
    failing: list[tuple[str, str]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        if run.get("status") != "completed":
            continue
        if run.get("conclusion") not in FAILING_CONCLUSIONS:
            continue
        name = run.get("name")
        html_url = run.get("html_url")
        if isinstance(name, str) and isinstance(html_url, str):
            failing.append((name, html_url))
    return failing
```
- [ ] **Step 4: Run → PASS** (all in the file). `ruff check src` + `mypy --strict src` clean.
- [ ] **Step 5: Commit**
```bash
git add src/teamctx/connectors/github_checks.py tests/test_gate_status.py
git commit -m "feat: GitHub check-runs probe (failing gates -> Core Contract)"
```

---

## Task 4 (Slice B.3): `gate-probe` CLI command

**Files:** Modify `src/teamctx/cli.py`; create `tests/test_gate_probe_cli.py`.

- [ ] **Step 1: Write the failing test** (`tests/test_gate_probe_cli.py`)
```python
import json

from click.testing import CliRunner

from teamctx.cli import main


def test_gate_probe_surfaces_missed_gate_card_and_verdict(monkeypatch) -> None:
    # Inject a failing check-run by patching the probe's opener at the github module boundary.
    import teamctx.connectors.github_checks as gc

    class _Resp:
        def __init__(self, body: bytes) -> None:
            self._b = body
        def read(self) -> bytes:
            return self._b
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self
        def __exit__(self, *a: object) -> None:
            return None

    def fake_fetch(*, repo, ref, token, opener=None):  # type: ignore[no-untyped-def]
        return [("pytest", "https://gh/run/1")]

    monkeypatch.setattr(gc, "fetch_failing_check_runs", fake_fetch)
    monkeypatch.setenv("GITHUB_TOKEN", "t")

    result = CliRunner().invoke(
        main,
        ["gate-probe", "--repo", "teamctx/teamctx", "--ref", "build/x",
         "--path", "src/teamctx/core/select.py"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Gate check: NOT CLEAR" in result.output
    assert "pytest" in result.output
```
- [ ] **Step 2: Run → FAIL** (`No such command 'gate-probe'`)
```bash
python -m pytest tests/test_gate_probe_cli.py -v
```
- [ ] **Step 3: Implement** in `src/teamctx/cli.py`
Add the import near the other connector imports:
```python
from teamctx.connectors.github_checks import run_github_checks_probe
```
Add the command (after `docs_probe_command`):
```python
@main.command("gate-probe")
@click.option("--repo", required=True, help="GitHub repository in owner/name form.")
@click.option("--ref", required=True, help="Git ref (branch or SHA) to read check-runs for.")
@click.option("--path", "paths", multiple=True, required=True, help="A path the work is about to touch.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
@click.option("--token-env", default="GITHUB_TOKEN", show_default=True, help="Token env var name.")
def gate_probe_command(
    repo: str,
    ref: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
    token_env: str,
) -> None:
    """Derive missed-gate context from failing GitHub check-runs."""

    observed_at = _utc_now_string()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"github-checks-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_github_checks_probe(
        repo=repo,
        ref=ref,
        token=os.environ.get(token_env),
        request_context=request_context,
        observed_at=observed_at,
    )
    click.echo(_work_start_view(document), nl=False)
```
(`os`, `RequestContext`, `_utc_now_string`, `_work_start_view`, `click` are already imported/defined in `cli.py`.)
- [ ] **Step 4: Run → PASS.** Then full suite `python -m pytest -q`, `ruff check src`, `mypy --strict src`. If "Gate check: NOT CLEAR" or "pytest" is missing, investigate the render output (don't weaken the assertion) and report.
- [ ] **Step 5: Commit**
```bash
git add src/teamctx/cli.py tests/test_gate_probe_cli.py
git commit -m "feat: gate-probe CLI command (failing-gate cards + verdict)"
```

---

## Task 5: Full gate (green-CI handoff)
- [ ] Run `python -m pytest -q && ruff check src && mypy --strict src` — all green. Commit any fixups only if needed.

---

## Task 6 (Slice C): Dogfood on teamctx — the CP1 done-gate
> No teamctx code. This is the verdict; performed by Edgar.

- [ ] **Step 1: Activate CI.** Push the branch (or merge to main and push) so the `ci.yml` workflow runs on GitHub Actions. *(Requires a push to `origin` — Edgar's go.)*
- [ ] **Step 2: Make a gate red.** On a working branch, introduce a failing check (e.g., a failing test or a lint error) and let CI run red.
- [ ] **Step 3: Probe at work-start.** From the repo, with `GITHUB_TOKEN` set:
```bash
teamctx gate-probe --repo teamctx/teamctx --ref <your-branch> --path <a file you're about to change>
```
Expected: a "Needs attention" missed-gate card naming the failing gate, and **Gate check: NOT CLEAR**.
- [ ] **Step 4: Record the verdict** (the finding, not a checkbox) in `.remember/teamctx.md`: did the red-CI card change what you did (fix the gate first vs. build on red)? Was it worth it, or noise? This pulls CP2.

---

## Self-review
- **Spec coverage:** CI (T1) · normalizer (T2) · probe (T3) · CLI (T4) · gate (T5) · dogfood (T6). ✓
- **Engine untouched:** no edits to `core/`; the `missed_gate` kind, deps_G `ci_deploy`, derive (`scope{repo,files}∩paths`), and render already exist. Only connectors + CLI + CI.
- **Type consistency:** `FailingGate` fields match their use in `github_checks.py` and `normalize_failing_gates`; signal `signal_type="missed_gate"` + `source_family="ci_deploy"` match `_KIND_BY_SIGNAL_TYPE` and `DEPS_REGISTRY`; scope keys `repo`/`files` match `_derive_missed_gate_claim`.
- **Pattern match:** `gate_status.py` mirrors `forge_review.py`/`docs_supersession.py`; `github_checks.py` reuses `github.py` (`get_json`, auth, `split_repo`, error mapping); `gate-probe` mirrors `docs-probe` and shares `_work_start_view`.
- **No bare `git checkout <sha>`** (it detached HEAD last time) — only branch operations as written.

## Deferred (dogfood-pulled)
- `scope["files"]` refinement to branch-changed files (v1 = request.paths).
- Distinguishing "required" vs optional checks (v1 treats any failing completed check as a gate).
- Merging gate + collision + docs into one `work-start` (the multi-source aggregation).
