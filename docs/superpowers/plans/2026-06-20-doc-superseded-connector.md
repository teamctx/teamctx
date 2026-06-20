# Doc-Superseded Connector (declared-frontmatter docs probe) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the first live `doc-superseded` connector — a declared-frontmatter docs probe — so that when an agent relies on a doc that has been marked superseded, work-start surfaces a card naming the **current** doc and a refuted "Docs check" verdict. Then dogfood it on the real model-citizens repo.

**Architecture:** Mirror the live collision connector's two-module split. A pure **normalizer** (`connectors/docs_supersession.py`, the docs analog of `connectors/forge_review.py`) turns declared supersession facts into Core Contract V0 `SourceSignal`s (`signal_type="doc_superseded"`, `source_family="docs"`, scope `{repo, doc, superseded_by}`) plus a `docs` source status. A thin **I/O connector** (`connectors/docs.py`, the analog of `connectors/github.py`) discovers `*.md` under a root, parses minimal frontmatter, and returns a `CoreContractDocument`. The engine **already** models `doc_superseded` end-to-end (predicate in `core/prop.py`, deps `no_superseded_docs → {"docs"}`, `_derive_doc_superseded_claim`, `render_doc_superseded_claim`, the "Docs check" `CardKind`) — so no engine *semantics* change. One evidence-backed render fix lands here: `render_doc_superseded_claim` currently says *that* a doc was superseded but never names *what* replaces it ("THAT not WHAT" legibility gap); it learns to name the superseding doc from `signal.scope["superseded_by"]`, with a fallback that preserves byte-for-byte output when that key is absent (so existing tests are unaffected). A new `docs-probe` CLI command shares work-start's selection+verdict render via an extracted `_work_start_view` helper.

**Tech Stack:** Python 3.12, pydantic v2, click, pytest, ruff, mypy --strict. I/O uses stdlib `pathlib` only; frontmatter is parsed by a small hand-rolled reader (no PyYAML — matching `connectors/github.py`'s stdlib-only ethos and keeping parsing deterministic).

**Path contract (correctness-critical):** All paths are **repo-root-relative POSIX strings**. `_derive_doc_superseded_claim` fires only when `signal.scope["doc"]` is exactly a string in `request.paths` and `signal.scope["repo"] == request.repo`. The probe must therefore run from the repo root so that discovered paths (e.g. `docs/superpowers/specs/x.md`) match the `--path` the caller passes, and frontmatter `superseded_by:` must also be a repo-root-relative POSIX path so the card can name something openable.

---

## File structure

- `src/teamctx/connectors/docs_supersession.py` (new, pure normalizer) — `SupersededDoc` dataclass; `normalize_superseded_docs(...) -> CoreContractDocument`; `unavailable_docs_document(...)`; private `_docs_source_status`, `_policy_metadata_only`, `_slug`.
- `src/teamctx/connectors/docs.py` (new, I/O edge) — `run_docs_supersession_probe(...)`; `parse_superseded_docs(...)`; `parse_frontmatter(text)`; `default_doc_reader(root)`; `DocReader` type; `DocsProbeError`.
- `src/teamctx/core/select.py` (modify) — `render_doc_superseded_claim` names the superseding doc.
- `src/teamctx/cli.py` (modify) — extract `_work_start_view(document)`; add `docs-probe` command; import the probe.
- `tests/test_docs_supersession.py` (new) — normalizer + frontmatter parse + probe with an in-memory reader.
- `tests/test_select.py` (modify) — render names the superseding doc; fallback preserved.
- `tests/test_docs_probe_cli.py` (new) — `docs-probe` end-to-end via `CliRunner` over a temp docs tree.

Each task is self-contained: a focused failing test, a minimal implementation, green, commit.

---

## Task 0: Branch + plan

- [ ] **Step 1: Branch**

```bash
cd /home/eparenti/agents/repos/teamctx && git checkout -b build/doc-superseded-connector
```

- [ ] **Step 2: Commit this plan**

```bash
git add docs/superpowers/plans/2026-06-20-doc-superseded-connector.md docs/engineering/connector-status.md
git commit -m "docs: doc-superseded connector plan + connector status"
```

---

## Task 1: Minimal frontmatter parser

**Files:**
- Create: `src/teamctx/connectors/docs.py` (parser only this task)
- Test: `tests/test_docs_supersession.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_supersession.py
from teamctx.connectors.docs import parse_frontmatter


def test_parse_frontmatter_reads_superseded_by() -> None:
    text = "---\nsuperseded_by: docs/new.md\ntitle: Old design\n---\n\n# Body\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md", "title": "Old design"}


def test_parse_frontmatter_absent_block_is_empty() -> None:
    assert parse_frontmatter("# No frontmatter here\n") == {}


def test_parse_frontmatter_ignores_non_kv_and_stops_at_close() -> None:
    text = "---\nsuperseded_by: docs/new.md\n---\nsuperseded_by: docs/IGNORED.md\n"
    assert parse_frontmatter(text) == {"superseded_by": "docs/new.md"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'teamctx.connectors.docs'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/teamctx/connectors/docs.py
"""Narrow docs-supersession probe: read declared supersession from markdown frontmatter."""

from __future__ import annotations


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a leading ``---`` fenced ``key: value`` block. No YAML dependency: only
    top-level string scalars are read, the block ends at the first closing ``---``, and a
    file without a leading ``---`` has no frontmatter."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/docs.py tests/test_docs_supersession.py
git commit -m "feat: minimal markdown frontmatter parser for the docs probe"
```

---

## Task 2: `SupersededDoc` + normalizer → Core Contract document

**Files:**
- Create: `src/teamctx/connectors/docs_supersession.py`
- Test: `tests/test_docs_supersession.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_supersession.py  (append these imports + tests)
from teamctx.connectors.docs_supersession import (
    SupersededDoc,
    normalize_superseded_docs,
    unavailable_docs_document,
)
from teamctx.core.contracts import RequestContext


def _request() -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="tempo-64/model-citizens",
        branch=None,
        task="work",
        paths=["docs/superpowers/specs/old.md"],
        linked_issues=[],
        requested_at="2026-06-20T00:00:00Z",
        requesting_principal=None,
    )


def test_normalize_emits_doc_superseded_signal_with_scope() -> None:
    doc = SupersededDoc(
        repo="tempo-64/model-citizens",
        doc="docs/superpowers/specs/old.md",
        superseded_by="docs/superpowers/research/new.md",
    )
    document = normalize_superseded_docs(_request(), [doc], observed_at="2026-06-20T00:00:00Z")
    assert len(document.source_signals) == 1
    signal = document.source_signals[0]
    assert signal.signal_type == "doc_superseded"
    assert signal.source_family == "docs"
    assert signal.scope["repo"] == "tempo-64/model-citizens"
    assert signal.scope["doc"] == "docs/superpowers/specs/old.md"
    assert signal.scope["superseded_by"] == "docs/superpowers/research/new.md"
    assert any(s.source_family == "docs" and s.status == "fresh" for s in document.source_statuses)


def test_unavailable_docs_document_reports_status_only() -> None:
    document = unavailable_docs_document(
        _request(),
        repo="tempo-64/model-citizens",
        observed_at="2026-06-20T00:00:00Z",
        safe_user_message="Docs are unavailable at the configured root.",
    )
    assert document.source_signals == []
    assert document.source_statuses[0].status == "unavailable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'teamctx.connectors.docs_supersession'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/teamctx/connectors/docs_supersession.py
"""Docs supersession normalization.

The docs connector reads markdown frontmatter; this module turns declared supersession
facts into Core Contract V0 objects. It does no file I/O and renders no cards directly —
work-start DERIVES doc-superseded cards from the signals emitted here.
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
class SupersededDoc:
    """A doc that declares it has been superseded, with the doc that replaces it.

    All paths are repo-root-relative POSIX strings."""

    repo: str
    doc: str
    superseded_by: str


def normalize_superseded_docs(
    request_context: RequestContext,
    docs: Iterable[SupersededDoc],
    *,
    observed_at: str,
    expires_at: str = "next_refresh",
    source_id: str = "docs_supersession",
) -> CoreContractDocument:
    source_signals: list[SourceSignal] = []
    for entry in docs:
        scope: Scope = {
            "repo": entry.repo,
            "doc": entry.doc,
            "superseded_by": entry.superseded_by,
        }
        source_signals.append(
            SourceSignal(
                schema_version="teamctx.source_signal.v0",
                id=f"sig_doc_superseded_{_slug(entry.doc)}",
                signal_type="doc_superseded",
                source_family="docs",
                scope=scope,
                evidence_summary=f"{entry.doc} was superseded by {entry.superseded_by}.",
                source_display=entry.doc,
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
        _docs_source_status(
            source_id=source_id,
            repo=request_context.repo,
            status="fresh",
            observed_at=observed_at,
            safe_user_message="Docs supersession metadata refreshed.",
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


def unavailable_docs_document(
    request_context: RequestContext,
    *,
    repo: str,
    observed_at: str,
    source_id: str = "docs_supersession",
    status: SourceStatusValue = "unavailable",
    safe_user_message: str,
) -> CoreContractDocument:
    return CoreContractDocument(
        schema_version="teamctx.core_contract_document.v0",
        request_context=request_context,
        source_signals=[],
        source_statuses=[
            _docs_source_status(
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


def _docs_source_status(
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
        source_family="docs",
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
        decision_reason="Docs supersession metadata is allowed as evidence; bodies are not included.",
    )


def _slug(path: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/docs_supersession.py tests/test_docs_supersession.py
git commit -m "feat: normalize declared doc supersession into Core Contract signals"
```

---

## Task 3: The I/O probe (discover docs, parse frontmatter, build the document)

**Files:**
- Modify: `src/teamctx/connectors/docs.py` (add discovery + probe)
- Test: `tests/test_docs_supersession.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_supersession.py  (append)
from teamctx.connectors.docs import parse_superseded_docs, run_docs_supersession_probe


def test_parse_superseded_docs_keeps_only_declared() -> None:
    files = [
        ("docs/superpowers/specs/old.md", "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n# Old\n"),
        ("docs/superpowers/specs/current.md", "# No frontmatter\n"),
    ]
    docs = parse_superseded_docs(repo="tempo-64/model-citizens", files=files)
    assert len(docs) == 1
    assert docs[0].doc == "docs/superpowers/specs/old.md"
    assert docs[0].superseded_by == "docs/superpowers/research/new.md"


def test_probe_uses_injected_reader_and_emits_signal() -> None:
    def reader(root: str) -> list[tuple[str, str]]:
        assert root == "docs/superpowers"
        return [("docs/superpowers/specs/old.md", "---\nsuperseded_by: docs/superpowers/research/new.md\n---\n")]

    document = run_docs_supersession_probe(
        repo="tempo-64/model-citizens",
        root="docs/superpowers",
        request_context=_request(),
        observed_at="2026-06-20T00:00:00Z",
        reader=reader,
    )
    assert len(document.source_signals) == 1
    assert document.source_signals[0].scope["doc"] == "docs/superpowers/specs/old.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: FAIL with `ImportError: cannot import name 'parse_superseded_docs'`

- [ ] **Step 3: Write minimal implementation** (append to `src/teamctx/connectors/docs.py`)

```python
# add to the top imports of src/teamctx/connectors/docs.py
from collections.abc import Callable, Iterable
from pathlib import Path, PurePosixPath

from teamctx.connectors.docs_supersession import (
    SupersededDoc,
    normalize_superseded_docs,
    unavailable_docs_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

# (repo-relative-posix-path, file-text) pairs under the docs root.
DocReader = Callable[[str], Iterable[tuple[str, str]]]


class DocsProbeError(RuntimeError):
    pass


def run_docs_supersession_probe(
    *,
    repo: str,
    root: str,
    request_context: RequestContext,
    observed_at: str,
    reader: DocReader | None = None,
) -> CoreContractDocument:
    read = reader if reader is not None else default_doc_reader
    try:
        files = list(read(root))
    except OSError:
        return unavailable_docs_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="Docs are unavailable at the configured root.",
        )
    superseded = parse_superseded_docs(repo=repo, files=files)
    return normalize_superseded_docs(request_context, superseded, observed_at=observed_at)


def parse_superseded_docs(
    *, repo: str, files: Iterable[tuple[str, str]]
) -> list[SupersededDoc]:
    docs: list[SupersededDoc] = []
    for rel_path, text in files:
        target = parse_frontmatter(text).get("superseded_by")
        if not target:
            continue
        docs.append(
            SupersededDoc(
                repo=repo,
                doc=PurePosixPath(rel_path).as_posix(),
                superseded_by=target,
            )
        )
    return docs


def default_doc_reader(root: str) -> list[tuple[str, str]]:
    """Yield (repo-relative-posix-path, text) for every ``*.md`` under ``root``. Run from the
    repo root so that paths match the ``--path`` a caller passes."""

    base = Path(root)
    return [(p.as_posix(), p.read_text(encoding="utf-8")) for p in sorted(base.rglob("*.md"))]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_docs_supersession.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/docs.py tests/test_docs_supersession.py
git commit -m "feat: docs supersession probe (discover + parse + normalize)"
```

---

## Task 4: Render fix — name the superseding doc ("THAT not WHAT")

**Files:**
- Modify: `src/teamctx/core/select.py` (`render_doc_superseded_claim`, lines ~226-249)
- Test: `tests/test_select.py` (append)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_select.py  (append; reuse the file's existing _typed_signal helper + render import)
from teamctx.core.select import render_doc_superseded_claim, _derive_doc_superseded_claim


def test_doc_superseded_card_names_the_superseding_doc() -> None:
    request = _request_with_paths(repo="r", paths=["docs/old.md"])  # see helper note below
    signal = _typed_signal(
        "doc_superseded",
        "docs",
        {"repo": "r", "doc": "docs/old.md", "superseded_by": "docs/new.md"},
        "sig_doc_x",
    )
    claim_card = _derive_doc_superseded_claim(request, signal)
    assert claim_card is not None
    card = render_doc_superseded_claim(claim_card)
    assert "docs/new.md" in card.why_this_matters
    assert "docs/new.md" in card.reason


def test_doc_superseded_card_falls_back_without_superseding_doc() -> None:
    request = _request_with_paths(repo="r", paths=["docs/old.md"])
    signal = _typed_signal("doc_superseded", "docs", {"repo": "r", "doc": "docs/old.md"}, "sig_doc_y")
    card = render_doc_superseded_claim(_derive_doc_superseded_claim(request, signal))
    assert card.why_this_matters == "the doc docs/old.md was superseded; verify it is current before relying."
```

> Helper note: if `tests/test_select.py` has no `_request_with_paths`, add a tiny local builder that returns a `RequestContext` with the given `repo`/`paths` (mirror the existing `RequestContext(...)` construction already used in that file). Keep the existing `test_doc_superseded_derives_for_a_relied_on_doc` untouched — it has no `superseded_by` and must still pass via the fallback.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_select.py -k doc_superseded -v`
Expected: the `names_the_superseding_doc` test FAILS (`'docs/new.md' not in ...`); the fallback test PASSES.

- [ ] **Step 3: Write minimal implementation** (replace the body of `render_doc_superseded_claim`)

```python
def render_doc_superseded_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a doc-superseded claim into a human-plane ``ContextCard``.

    Names the superseding doc when the signal carries ``scope["superseded_by"]`` (so the card
    says WHAT to open, not only THAT the doc is stale); falls back byte-for-byte otherwise."""

    claim = claim_card.claim
    signal = claim_card.signal
    doc = claim.subject.paths[0]
    superseded_by = signal.scope.get("superseded_by")
    current = superseded_by if isinstance(superseded_by, str) and superseded_by else None
    if current is not None:
        why = f"{doc} was superseded; rely on {current} instead, not {doc}."
        reason = f"the doc {doc} was superseded by {current}"
    else:
        why = f"the doc {doc} was superseded; verify it is current before relying."
        reason = f"a doc you rely on ({doc}) was superseded"
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section="Verify before relying",
        text=signal.evidence_summary,
        why_this_matters=why,
        source_display=signal.source_display,
        refs=[signal.id],
        reason=reason,
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
        reason_code="doc.superseded",
        severity=compute_severity(claim.predicate, claim),
    )
```

- [ ] **Step 4: Run tests to verify they pass (and nothing regressed)**

Run: `python -m pytest tests/test_select.py -v`
Expected: PASS (all, including the untouched derive test)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/core/select.py tests/test_select.py
git commit -m "feat: doc-superseded card names the superseding doc (close THAT-not-WHAT)"
```

---

## Task 5: `docs-probe` CLI command (shares work-start's verdict render)

**Files:**
- Modify: `src/teamctx/cli.py` (import probe; extract `_work_start_view`; add `docs-probe`)
- Test: `tests/test_docs_probe_cli.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docs_probe_cli.py
from pathlib import Path

from click.testing import CliRunner

from teamctx.cli import main


def test_docs_probe_surfaces_superseded_card_and_verdict(tmp_path: Path) -> None:
    root = tmp_path / "docs" / "superpowers" / "specs"
    root.mkdir(parents=True)
    spec = root / "old.md"
    spec.write_text("---\nsuperseded_by: docs/superpowers/research/new.md\n---\n# Old\n", encoding="utf-8")
    rel = "docs/superpowers/specs/old.md"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "docs-probe",
            "--repo", "tempo-64/model-citizens",
            "--root", "docs/superpowers",
            "--path", rel,
        ],
        catch_exceptions=False,
        # run from tmp_path so discovered paths are repo-root-relative and match --path
        **{"env": None},
    )
    # invoke runs in the current process CWD; chdir for the path contract
    assert result.exit_code == 0, result.output
    assert "docs/superpowers/research/new.md" in result.output  # names the current doc
    assert "Docs check" in result.output  # the verdict label rendered


def test_docs_probe_with_no_supersession_is_clean(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir(parents=True)
    (root / "fine.md").write_text("# nothing declared\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["docs-probe", "--repo", "r", "--root", "docs", "--path", "docs/fine.md"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
```

> Test note: `docs-probe` resolves `--root` relative to CWD. In the test, wrap the invoke in `runner.isolated_filesystem(temp_dir=tmp_path)` **or** `monkeypatch.chdir(tmp_path)` so that `Path("docs/superpowers").rglob` finds the file and the discovered path equals `--path`. Use whichever the repo's other CLI tests already use (check `tests/test_work_start_cli.py`); prefer `monkeypatch.chdir(tmp_path)` and drop the `env`/comment scaffolding above.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_docs_probe_cli.py -v`
Expected: FAIL — `No such command 'docs-probe'`.

- [ ] **Step 3: Write minimal implementation**

Add the import near the other connector imports in `cli.py`:

```python
from teamctx.connectors.docs import run_docs_supersession_probe
```

Extract the shared render helper (place near `_github_contract_document`):

```python
def _work_start_view(document: CoreContractDocument) -> str:
    declarations = load_declared_authority(Path(".teamctx/authority.json"))
    selection = select_context(
        document.request_context,
        document.source_signals,
        document.source_statuses,
        declarations,
    )
    verdicts = tuple(
        (
            kind.verdict_label,
            evaluate(
                kind.query(document.request_context), selection.claim_cards, selection.closure
            ),
        )
        for kind in CARD_KINDS
    )
    return render_selection(selection, verdicts)
```

Replace the body of `work_start_command` (the `declarations`/`selection`/`verdicts`/`echo` block, cli.py ~183-199) with:

```python
    click.echo(_work_start_view(document), nl=False)
```

Add the command (place after `work_start_command`):

```python
@main.command("docs-probe")
@click.option("--repo", required=True, help="Repository in owner/name form (scope only; no fetch).")
@click.option("--root", required=True, help="Docs root to scan for supersession frontmatter.")
@click.option("--path", "paths", multiple=True, required=True, help="A doc the work relies on.")
@click.option("--branch", default=None, help="Current branch name.")
@click.option("--task", default="Start work.", show_default=True, help="Task text.")
def docs_probe_command(
    repo: str,
    root: str,
    paths: tuple[str, ...],
    branch: str | None,
    task: str,
) -> None:
    """Derive doc-superseded context (declared-frontmatter) for the relied-on docs."""

    observed_at = _utc_now_string()
    request_context = RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id=f"docs-supersession-probe:{repo}:{observed_at}",
        repo=repo,
        branch=branch,
        task=task,
        paths=list(paths),
        linked_issues=[],
        requested_at=observed_at,
        requesting_principal=None,
    )
    document = run_docs_supersession_probe(
        repo=repo, root=root, request_context=request_context, observed_at=observed_at
    )
    click.echo(_work_start_view(document), nl=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_docs_probe_cli.py tests/test_work_start_cli.py -v`
Expected: PASS (new docs-probe tests + the unchanged work-start test, proving the extraction is behavior-preserving)

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/cli.py tests/test_docs_probe_cli.py
git commit -m "feat: docs-probe CLI command (shared work-start verdict render)"
```

---

## Task 6: Full gate (the green-CI handoff)

- [ ] **Step 1: Run the whole suite + linters + types**

```bash
python -m pytest -q && ruff check src && mypy --strict src
```
Expected: all tests pass; `ruff check src` clean; mypy `Success`.

- [ ] **Step 2: Commit only if any fixups were needed** (otherwise skip)

```bash
git commit -am "chore: doc-superseded connector lint/type fixups"
```

---

## Task 7: Dogfood on model-citizens (no teamctx code — this is the verdict)

> This is the point of the whole vertical: a card must change a real decision, or we learn the declaration cost outweighs the catch. Performed in `/home/eparenti/agents/repos/model-citizens`, not in teamctx.

- [ ] **Step 1: Pick the real supersession and mark it.** Edgar chooses the current doc that replaces `docs/superpowers/specs/2026-06-17-comedy-engine-design.md` (candidate: the critic-rebuild / `docs/superpowers/research/2026-06-19-generation-bottleneck.md`). Add frontmatter to the **superseded** spec:

```text
---
superseded_by: docs/superpowers/research/2026-06-19-generation-bottleneck.md
---
```

- [ ] **Step 2: Run the probe from the model-citizens repo root**

```bash
cd /home/eparenti/agents/repos/model-citizens
teamctx docs-probe \
  --repo tempo-64/model-citizens \
  --root docs/superpowers \
  --path docs/superpowers/specs/2026-06-17-comedy-engine-design.md
```
Expected: a "Verify before relying" card naming the current doc, and a refuted **Docs check** verdict.

- [ ] **Step 3: Record the verdict (the finding, not a checkbox).** In `.remember/teamctx.md`, write down: (a) did the card change what you/the agent read or did? (b) was declaring `superseded_by` worth the friction, or too costly? (c) any "THAT not WHAT" residue (does the card make the *next action* obvious, or just name the file?). These findings pull the next connector decision — they are not a formality.

---

## Self-review (run after the plan is written, before execution)

- **Spec coverage:** connector (Tasks 1-3) ✓; legibility fix (Task 4) ✓; live entry point + verdict (Task 5) ✓; green-CI handoff (Task 6) ✓; real dogfood (Task 7) ✓. The status-doc + branch are Task 0 ✓.
- **Engine untouched (by design):** no change to `prop.py`, `evaluate.py`, deps/predicate registries — the only `core/` edit is the `render_doc_superseded_claim` text, guarded by the core purity test (no I/O/time/randomness added) and a fallback that preserves existing output.
- **Type consistency:** signal scope keys `repo`/`doc`/`superseded_by` match `_derive_doc_superseded_claim` (`select.py:195-205`); `SupersededDoc` fields match their use in `parse_superseded_docs` and `normalize_superseded_docs`; `DocReader` returns `(str, str)` pairs consumed identically by `parse_superseded_docs` and produced by `default_doc_reader`.
- **Path contract:** discovered paths and `--path` are both repo-root-relative POSIX; the probe must run from the repo root (documented in Task 3 / Task 7).

## Deferred (dogfood-pulled, explicitly out of this slice)

- Merging the docs document into `work-start` alongside the GitHub fetch (a multi-connector merge layer) — not needed; `docs-probe` runs the full verdict pipeline on its own.
- `DocsSourceConfig` in `project_config.py` + a `refresh`-style docs source — `--root` on the probe is enough to dogfood.
- Path-overlap *filtering refinements* / openable doc bodies (`source_open_target_id` plumbing for docs) — only if the dogfood shows the text-only legibility is insufficient.
- The `criteria-changed` and `missed-gate` live connectors — pulled when a real session needs them (see `docs/engineering/connector-status.md`).
