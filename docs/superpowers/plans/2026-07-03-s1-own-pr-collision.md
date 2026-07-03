# S1: Own-PR Collision Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The open PR belonging to the branch you are standing on no longer fires a "Needs attention" collision against you; it is set aside with the fact recorded in the observable and one visible FYI line, and the clear-line copy stays literally true.

**Architecture:** Parse `head.ref` + `head.repo.full_name` in the GitHub PR probe; partition own-branch PRs out of collision signals in `normalize_forge_review_prs` and record them on the forge-review SourceStatus; pass the status note + visibility through `CoverageEntry` so the render can print the FYI; update the two static clear phrases. Fail-closed direction throughout: missing or malformed head data means "not own", so the PR still surfaces.

**Tech Stack:** Python 3.12, pydantic v2, pytest. Gate: `python -m pytest -q -p no:cacheprovider && ruff check src tests && python -m mypy src` plus `grep -rP '\x{2014}' src tests` must be empty.

**Branch:** `feat/own-pr-collision` off `main`. Commit per task. Do NOT touch README.md (that is slice S2).

**Spec:** `docs/superpowers/specs/2026-07-03-full-review-findings.md` finding F1 (the locked design is binding).

---

### Task 1: Parse head fields from the GitHub PR payload

**Files:**
- Modify: `src/teamctx/connectors/forge_review.py` (ForgeReviewPullRequest, ~line 37)
- Modify: `src/teamctx/connectors/github.py` (parse_github_pull_requests, ~line 140)
- Test: `tests/test_own_pr_collision.py` (create)

- [ ] **Step 1: Write the failing tests**

```python
"""S1: own-branch PRs are set aside from collisions (spec F1, 2026-07-03)."""

from teamctx.connectors.github import parse_github_pull_requests


def _raw_pr(number: int = 12, head: object = None) -> dict[str, object]:
    pr: dict[str, object] = {
        "number": number,
        "html_url": f"https://github.com/o/r/pull/{number}",
        "state": "open",
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-02T00:00:00Z",
    }
    if head is not None:
        pr["head"] = head
    return pr


def test_parse_extracts_head_ref_and_head_repo() -> None:
    payload = [_raw_pr(head={"ref": "feat/x", "repo": {"full_name": "o/r"}})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref == "feat/x"
    assert prs[0].head_repo == "o/r"


def test_parse_missing_head_yields_none() -> None:
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=[_raw_pr()], files_by_pr={})
    assert prs[0].head_ref is None
    assert prs[0].head_repo is None


def test_parse_deleted_fork_null_repo_yields_none_repo() -> None:
    payload = [_raw_pr(head={"ref": "feat/x", "repo": None})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref == "feat/x"
    assert prs[0].head_repo is None


def test_parse_malformed_head_types_yield_none() -> None:
    payload = [_raw_pr(head={"ref": 7, "repo": {"full_name": 3}})]
    prs = parse_github_pull_requests(repo="o/r", pulls_payload=payload, files_by_pr={})
    assert prs[0].head_ref is None
    assert prs[0].head_repo is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_own_pr_collision.py -q -p no:cacheprovider`
Expected: FAIL (TypeError: unexpected keyword / AttributeError: head_ref).

- [ ] **Step 3: Implement**

In `forge_review.py`, add two fields to `ForgeReviewPullRequest` (after `labels`):

```python
    head_ref: str | None = None
    head_repo: str | None = None
```

In `github.py` `parse_github_pull_requests`, before constructing `ForgeReviewPullRequest`:

```python
        head = raw_pr.get("head")
        head_ref: str | None = None
        head_repo: str | None = None
        if isinstance(head, dict):
            ref = head.get("ref")
            head_ref = ref if isinstance(ref, str) else None
            head_repo_obj = head.get("repo")
            if isinstance(head_repo_obj, dict):
                full_name = head_repo_obj.get("full_name")
                head_repo = full_name if isinstance(full_name, str) else None
```

and pass `head_ref=head_ref, head_repo=head_repo` in the constructor call.

- [ ] **Step 4: Run the new tests and the full gate**

Run: `python -m pytest tests/test_own_pr_collision.py -q -p no:cacheprovider` then the full gate.
Expected: PASS, everything green (fields are additive with defaults).

- [ ] **Step 5: Commit**

```bash
git add src/teamctx/connectors/forge_review.py src/teamctx/connectors/github.py tests/test_own_pr_collision.py
git commit -m "feat(github): parse PR head ref and head repo (own-PR detection input)"
```

---

### Task 2: Partition own-branch PRs in normalize_forge_review_prs

**Files:**
- Modify: `src/teamctx/connectors/forge_review.py` (normalize_forge_review_prs, ~line 52)
- Test: `tests/test_own_pr_collision.py` (extend)

A PR is **own** exactly when: `request_context.branch is not None and pr.head_ref == request_context.branch and pr.head_repo == pr.repo`. Own PRs **with path overlap** emit no signal, no card, no open target; their numbers are recorded. Own PRs without overlap are ignored as today (they never fired). The forge-review SourceStatus then carries the record:

- scope gains `"own_branch_prs": ["12", ...]` (strings; Scope allows `list[str]`) when any own PR overlapped.
- message: when not truncated and own PRs exist, `"Your own open PR #12 for this branch touches these files; not flagged as a collision."` (join multiple as `#12, #14`). When truncated AND own PRs exist, keep the truncation sentence first and append the own-PR sentence. Truncation status precedence is unchanged (`stale` when truncated, else `fresh`).
- visibility: `"warning_when_relevant"` when own PRs were set aside, else `"silent"` as today.

- [ ] **Step 1: Write the failing tests** (extend `tests/test_own_pr_collision.py`)

```python
from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.contracts import RequestContext


def _request(branch: str | None = "feat/x") -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="t",
        repo="o/r",
        branch=branch,
        task="t",
        paths=["src/a.py"],
        linked_issues=[],
        requested_at="2026-07-03T00:00:00Z",
        requesting_principal=None,
    )


def _pr(number: int, head_ref: str | None, head_repo: str | None) -> ForgeReviewPullRequest:
    return ForgeReviewPullRequest(
        provider="github", repo="o/r", number=number, state="open",
        url=f"https://github.com/o/r/pull/{number}", title=None,
        changed_paths=("src/a.py",), created_at="2026-07-01T00:00:00Z",
        updated_at="2026-07-02T00:00:00Z", head_ref=head_ref, head_repo=head_repo,
    )


def test_own_branch_pr_emits_no_collision_and_is_recorded() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(12, "feat/x", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert doc.source_signals == []
    assert doc.context_cards == []
    assert doc.source_open_targets == []
    status = doc.source_statuses[0]
    assert status.status == "fresh"
    assert status.scope["own_branch_prs"] == ["12"]
    assert "#12" in status.safe_user_message
    assert status.normal_context_visibility == "warning_when_relevant"


def test_other_branch_pr_still_fires() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(13, "feat/other", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1
    assert doc.source_statuses[0].normal_context_visibility == "silent"


def test_fork_pr_with_same_branch_name_still_fires() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(14, "feat/x", "someone/fork")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_unknown_branch_never_matches_own() -> None:
    doc = normalize_forge_review_prs(
        _request(branch=None), [_pr(12, "feat/x", "o/r")], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_missing_head_data_never_matches_own() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(12, None, None)], observed_at="2026-07-03T00:00:00Z"
    )
    assert len(doc.source_signals) == 1


def test_truncated_and_own_pr_keeps_truncation_precedence() -> None:
    doc = normalize_forge_review_prs(
        _request(), [_pr(12, "feat/x", "o/r")],
        observed_at="2026-07-03T00:00:00Z", coverage_truncated=True,
    )
    status = doc.source_statuses[0]
    assert status.status == "stale"
    assert "most recent 100" in status.safe_user_message
    assert "#12" in status.safe_user_message
```

- [ ] **Step 2: Run to verify they fail**, then **Step 3: Implement** in `normalize_forge_review_prs`: inside the PR loop, after computing `overlap` and confirming it is non-empty, add

```python
        if (
            request_context.branch is not None
            and pr.head_ref == request_context.branch
            and pr.head_repo == pr.repo
        ):
            own_branch_prs.append(pr.number)
            continue
```

(with `own_branch_prs: list[int] = []` initialized before the loop). Then compute status fields:

```python
    status: SourceStatusValue = "stale" if coverage_truncated else "fresh"
    messages: list[str] = []
    if coverage_truncated:
        messages.append(
            "Checked the most recent 100 open PRs; there are more open PRs not included, "
            "so this is not a complete check."
        )
    if own_branch_prs:
        numbers = ", ".join(f"#{n}" for n in own_branch_prs)
        plural = "PRs" if len(own_branch_prs) > 1 else "PR"
        messages.append(
            f"Your own open {plural} {numbers} for this branch touches these files; "
            "not flagged as a collision."
        )
    if not messages:
        messages.append("Git-host PR metadata refreshed.")
    safe_user_message = " ".join(messages)
    status_scope: Scope = {"provider": "github", "repo": request_context.repo}
    if own_branch_prs:
        status_scope["own_branch_prs"] = [str(n) for n in own_branch_prs]
    visibility: SourceStatusVisibility = (
        "warning_when_relevant" if own_branch_prs else "silent"
    )
```

and pass `visibility=visibility` to `forge_review_source_status`. Note `forge_review_source_status` builds its own scope; extend its signature with `extra_scope: Scope | None = None` merged in, or inline the `source_status` call with the computed scope. Prefer the smallest change that keeps one construction path.

- [ ] **Step 4: Full gate.** Expected: PASS (existing forge tests pass `branch=None` or non-matching heads and are unaffected; if any existing test now trips the own rule, fix the TEST only if its fixture genuinely models your own branch, otherwise stop and flag).

- [ ] **Step 5: Commit** `feat(forge-review): set aside own-branch PRs from collisions, recorded on the source status`

---

### Task 3: CoverageEntry note + visibility pass-through (pure core)

**Files:**
- Modify: `src/teamctx/core/select.py` (CoverageEntry ~line 361, build_coverage ~line 451)
- Test: `tests/test_select.py` (extend)

- [ ] **Step 1: Failing test**

```python
def test_build_coverage_carries_note_and_visibility() -> None:
    status = _status(...)  # use the existing status helper/fixture pattern in this file,
    # with safe_user_message="Your own open PR #12 ..." and
    # normal_context_visibility="warning_when_relevant"
    coverage = build_coverage([status])
    entry = coverage.entries[0]
    assert entry.note == "Your own open PR #12 ..."
    assert entry.visibility == "warning_when_relevant"
```

(Adapt to the existing SourceStatus construction helper already used in `tests/test_select.py`; keep the assertion shape.)

- [ ] **Step 2: Implement.** `CoverageEntry` gains `note: str | None = None` and `visibility: str = "silent"`; `build_coverage` passes `note=status.safe_user_message, visibility=status.normal_context_visibility`. Additive with defaults, so no other construction site changes.

- [ ] **Step 3: Full gate.** The core purity test must stay green (no new imports).

- [ ] **Step 4: Commit** `feat(core): coverage entries carry the source note and visibility`

---

### Task 4: Render FYI line + the two clear phrases

**Files:**
- Modify: `src/teamctx/contract_render.py` (_CLEAR_PHRASE ~line 25, render_broker_answer ~line 84)
- Modify: `src/teamctx/hook_signal.py` (_CLEAR_PHRASE ~line 14)
- Test: `tests/test_render_broker_answer.py`, `tests/test_hook_signal.py` (extend + sweep)

Rules:
- `contract_render._CLEAR_PHRASE["conflict"]` becomes `"no other open PRs touch your files"`.
- `hook_signal._CLEAR_PHRASE["conflict"]` becomes `"no other open pull requests touch these files"`.
- New render block after the coverage line: for every coverage entry with `status == "fresh"`, `visibility == "warning_when_relevant"`, and a non-empty note, print `"  FYI: {note}"`. This fires only for the own-PR case today (unavailable/pending entries are not fresh; truncated is stale, so its message stays on the UNKNOWN path). The hook's one-line signal does NOT carry the FYI.

- [ ] **Step 1: Failing tests**

```python
def test_render_fyi_line_for_fresh_warning_note() -> None:
    # build a BrokerAnswer via broker_answer(...) whose statuses include a fresh
    # warning_when_relevant forge status with the own-PR message (reuse this file's
    # existing answer-building helpers)
    output = render_broker_answer(answer)
    assert "FYI: Your own open PR #12" in output
    assert "no other open PRs touch your files" in output


def test_render_no_fyi_for_stale_status() -> None:
    # same construction but status="stale": the note must NOT render as FYI
    output = render_broker_answer(answer)
    assert "FYI:" not in output
```

- [ ] **Step 2: Implement**, **Step 3: sweep every existing assertion** on the old phrases (`grep -rn "no open PRs touch your files\|no open pull requests touch these files" tests src docs/superpowers` and update tests; leave docs alone, S2 owns them).

- [ ] **Step 4: Full gate.** **Step 5: Commit** `feat(render): own-PR FYI line; clear phrases say "no other open PRs"`

---

### Task 5: End-to-end integration test

**Files:**
- Test: `tests/test_own_pr_collision.py` (extend)

- [ ] **Step 1: Write the test** (this is the acceptance test for the slice)

```python
def test_end_to_end_own_pr_is_clear_with_fyi() -> None:
    """A repo whose only overlapping open PR is the current branch's own PR must read as a
    clear conflict check (verdict true), with the FYI naming the PR, never a heads-up."""
    # run run_github_pr_probe with a fake opener returning one open PR:
    # head ref == the request branch, head repo == the queried repo, files overlap.
    # Follow the fake-opener pattern in tests/test_github_collision_integration.py.
    # Then broker_answer(request, doc.source_signals, doc.source_statuses) and assert:
    #   verdicts: Conflict check value == "true"
    #   render_broker_answer contains "Looks clear to start." and "FYI: Your own open PR #7"
```

Write it fully (no placeholder): copy the fake-opener scaffolding from
`tests/test_github_collision_integration.py`, set the PR JSON `head` object accordingly, and
assert the three facts above.

- [ ] **Step 2: Full gate + em-dash grep.** **Step 3: Update CHANGELOG.md** (repo root) with one entry under the current unreleased section: `- work-start no longer flags the open PR of the branch you are on as a collision; it is set aside with an FYI line and recorded on the forge source status.` **Step 4: Commit** `test(own-pr): end-to-end own-PR clear + FYI acceptance`

---

## Completion

Stop after the last commit. Do NOT merge. Report: branch name, commits, gate output tail, and any place you deviated from this plan and why. The CTO reviews the diff before merge (reviewer separation: the builder never merges its own slice).
