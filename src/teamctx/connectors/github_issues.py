"""Narrow GitHub Issues probe: surface criteria changes for linked issues."""

from __future__ import annotations

from urllib.parse import quote

from teamctx.connectors.github import (
    DEFAULT_OPENER,
    GITHUB_API_ROOT,
    GitHubProbeError,
    HttpOpener,
    get_json,
    split_repo,
)
from teamctx.connectors.issue_criteria import (
    IssueCriteriaChange,
    normalize_issue_changes,
    unavailable_issues_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext


def run_github_issues_probe(
    *,
    repo: str,
    issues: list[str],
    since: str,
    token: str | None,
    request_context: RequestContext,
    observed_at: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if not token:
        return unavailable_issues_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="Issue tracker is unavailable because no token is configured.",
        )
    if not issues:
        return normalize_issue_changes(
            request_context, [], observed_at=observed_at,
        )
    try:
        changes = fetch_issue_changes(
            repo=repo, issues=issues, since=since, token=token, opener=opener,
        )
    except GitHubProbeError as exc:
        return unavailable_issues_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message=_issues_error_message(exc),
        )
    return normalize_issue_changes(request_context, changes, observed_at=observed_at)


def fetch_issue_changes(
    *,
    repo: str,
    issues: list[str],
    since: str,
    token: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> list[IssueCriteriaChange]:
    owner, name = split_repo(repo)
    base = f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}"
    changes: list[IssueCriteriaChange] = []
    for issue_ref in issues:
        number = _parse_issue_number(issue_ref)
        if number is None:
            continue
        change = _probe_single_issue(
            base=base, repo=repo, issue_ref=issue_ref, number=number,
            since=since, token=token, opener=opener,
        )
        if change is not None:
            changes.append(change)
    return changes


def _probe_single_issue(
    *,
    base: str,
    repo: str,
    issue_ref: str,
    number: int,
    since: str,
    token: str,
    opener: HttpOpener,
) -> IssueCriteriaChange | None:
    issue_data = get_json(f"{base}/issues/{number}", token=token, opener=opener)
    if not isinstance(issue_data, dict):
        return None
    updated_at = issue_data.get("updated_at")
    if not isinstance(updated_at, str) or updated_at <= since:
        return None

    change_kinds = _classify_changes(base, number, since, token, opener)

    state = issue_data.get("state", "unknown")
    title = issue_data.get("title", "")
    html_url = issue_data.get("html_url", "")
    labels = _extract_labels(issue_data.get("labels"))

    detail = _build_detail(issue_ref, state, labels, change_kinds)
    return IssueCriteriaChange(
        repo=repo,
        issue=issue_ref,
        issue_url=html_url if isinstance(html_url, str) else "",
        title=title if isinstance(title, str) else "",
        state=state if isinstance(state, str) else "unknown",
        labels=labels,
        change_kinds=change_kinds,
        detail=detail,
        updated_at=updated_at,
    )


def _classify_changes(
    base: str, number: int, since: str, token: str, opener: HttpOpener,
) -> tuple[str, ...]:
    try:
        events_data = get_json(
            f"{base}/issues/{number}/events?per_page=100", token=token, opener=opener,
        )
    except GitHubProbeError:
        return ("body_edited",)

    kinds: list[str] = []
    if isinstance(events_data, list):
        for event in events_data:
            if not isinstance(event, dict):
                continue
            created_at = event.get("created_at", "")
            if not isinstance(created_at, str) or created_at <= since:
                continue
            event_type = event.get("event")
            if event_type in ("closed", "reopened") and "state_changed" not in kinds:
                kinds.append("state_changed")
            elif event_type in ("labeled", "unlabeled") and "labels_changed" not in kinds:
                kinds.append("labels_changed")

    if not kinds:
        kinds.append("body_edited")
    return tuple(kinds)


def _extract_labels(labels_payload: object) -> tuple[str, ...]:
    if not isinstance(labels_payload, list):
        return ()
    labels: list[str] = []
    for raw_label in labels_payload:
        if isinstance(raw_label, dict):
            name = raw_label.get("name")
            if isinstance(name, str):
                labels.append(name)
    return tuple(sorted(set(labels)))


def _build_detail(
    issue_ref: str, state: str, labels: tuple[str, ...], change_kinds: tuple[str, ...],
) -> str:
    parts: list[str] = []
    if "state_changed" in change_kinds:
        parts.append(f"state is now {state}")
    if "labels_changed" in change_kinds:
        label_str = ", ".join(labels) if labels else "none"
        parts.append(f"labels now: {label_str}")
    if "body_edited" in change_kinds:
        parts.append("description or comments updated")
    return f"Issue {issue_ref} updated: {'; '.join(parts)}."


def _parse_issue_number(issue_ref: str) -> int | None:
    cleaned = issue_ref.lstrip("#")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _issues_error_message(error: GitHubProbeError) -> str:
    if error.status_code in {401, 404}:
        return "Issue tracker is unavailable with current access."
    if error.status_code == 403:
        return "Issue tracker is unavailable or rate-limited with current access."
    if error.status_code == 429:
        return "Issue tracker is rate-limited."
    return "Issue tracker is unavailable."
