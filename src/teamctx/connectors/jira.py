"""Narrow Jira issue probe: surface criteria changes for linked Jira issues."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request

from teamctx.clock import parse_since
from teamctx.connectors.github import DEFAULT_OPENER, HttpOpener
from teamctx.connectors.issue_criteria import (
    IssueCriteriaChange,
    normalize_issue_changes,
    unavailable_issues_document,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

_SOURCE_ID = "jira_issues"
_NO_CREDENTIAL = (
    "Jira is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL and "
    "ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE)."
)
_STALE_HISTORY = (
    "Checked the most recent 100 changes on {key}; more history exists, so this is not a "
    "complete check."
)
_MALFORMED_UPDATED = (
    "Jira returned an unreadable update time for {key}; its criteria state can't be confirmed."
)


class JiraProbeError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class _JiraIssueChangeFetch:
    changes: tuple[IssueCriteriaChange, ...]
    coverage_truncated: bool = False
    truncated_user_message: str = "Issue tracker history was truncated, so this is not complete."


@dataclass(frozen=True)
class _JiraIssue:
    key: str
    summary: str
    state: str
    labels: tuple[str, ...]
    updated_at: str
    updated_time: datetime


def run_jira_issues_probe(
    *,
    base_url: str,
    issues: list[str],
    since: str,
    auth: tuple[str, str] | None,
    request_context: RequestContext,
    observed_at: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> CoreContractDocument:
    if auth is None:
        return unavailable_issues_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id=_SOURCE_ID,
            safe_user_message=_NO_CREDENTIAL,
        )
    if not issues:
        return normalize_issue_changes(
            request_context,
            [],
            observed_at=observed_at,
            source_id=_SOURCE_ID,
        )

    normalized_base_url = base_url.rstrip("/")
    try:
        fetch = fetch_jira_issue_changes(
            base_url=normalized_base_url,
            issues=issues,
            since=since,
            auth=auth,
            repo=request_context.repo,
            opener=opener,
        )
    except JiraProbeError as exc:
        return unavailable_issues_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id=_SOURCE_ID,
            status="unavailable",
            safe_user_message=_jira_error_message(exc),
        )
    except ValueError as exc:
        return unavailable_issues_document(
            request_context,
            repo=request_context.repo,
            observed_at=observed_at,
            source_id=_SOURCE_ID,
            status="stale",
            safe_user_message=str(exc),
        )

    return normalize_issue_changes(
        request_context,
        fetch.changes,
        observed_at=observed_at,
        source_id=_SOURCE_ID,
        coverage_truncated=fetch.coverage_truncated,
        truncated_user_message=fetch.truncated_user_message,
    )


def fetch_jira_issue_changes(
    *,
    base_url: str,
    issues: list[str],
    since: str,
    auth: tuple[str, str],
    repo: str,
    opener: HttpOpener = DEFAULT_OPENER,
) -> _JiraIssueChangeFetch:
    since_time = parse_since(since)
    changes: list[IssueCriteriaChange] = []
    coverage_truncated = False
    truncated_user_message: str | None = None
    for issue_key in issues:
        key = issue_key.upper()
        issue = _fetch_issue(base_url, key, auth, opener)
        if issue.updated_time <= since_time:
            continue

        changelog_truncated = False
        try:
            change_kinds, changelog_truncated = _fetch_change_kinds(
                base_url=base_url,
                key=key,
                since_time=since_time,
                auth=auth,
                opener=opener,
            )
            detail = _build_detail(key, issue.state, issue.labels, change_kinds)
        except JiraProbeError:
            change_kinds = ("body_edited",)
            detail = (
                f"Jira {key} updated: criteria changed since you started; "
                "changelog details unavailable."
            )

        if changelog_truncated:
            coverage_truncated = True
            truncated_user_message = _STALE_HISTORY.format(key=key)

        changes.append(
            IssueCriteriaChange(
                repo=repo,
                issue=key,
                issue_url=f"{base_url}/browse/{quote(key)}",
                title=issue.summary,
                state=issue.state,
                labels=issue.labels,
                change_kinds=change_kinds,
                detail=detail,
                source_display=f"Jira {key}: {issue.summary}",
                updated_at=issue.updated_at,
            )
        )

    return _JiraIssueChangeFetch(
        changes=tuple(changes),
        coverage_truncated=coverage_truncated,
        truncated_user_message=truncated_user_message
        or "Issue tracker history was truncated, so this is not complete.",
    )


def _fetch_issue(
    base_url: str, key: str, auth: tuple[str, str], opener: HttpOpener,
) -> _JiraIssue:
    payload = _get_json(
        f"{base_url}/rest/api/3/issue/{quote(key)}?fields=summary,status,labels,updated",
        auth=auth,
        opener=opener,
    )
    if not isinstance(payload, dict):
        raise JiraProbeError("Jira issue payload was malformed")
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        raise JiraProbeError("Jira issue fields were malformed")
    updated_at = fields.get("updated")
    if not isinstance(updated_at, str):
        raise ValueError(_MALFORMED_UPDATED.format(key=key))
    try:
        updated_time = parse_since(updated_at)
    except ValueError as exc:
        raise ValueError(_MALFORMED_UPDATED.format(key=key)) from exc

    summary = fields.get("summary")
    status = fields.get("status")
    status_name = status.get("name") if isinstance(status, dict) else None
    return _JiraIssue(
        key=key,
        summary=summary if isinstance(summary, str) else "",
        state=status_name if isinstance(status_name, str) else "unknown",
        labels=_extract_labels(fields.get("labels")),
        updated_at=updated_at,
        updated_time=updated_time,
    )


def _fetch_change_kinds(
    *,
    base_url: str,
    key: str,
    since_time: datetime,
    auth: tuple[str, str],
    opener: HttpOpener,
) -> tuple[tuple[str, ...], bool]:
    payload = _get_json(
        f"{base_url}/rest/api/3/issue/{quote(key)}/changelog?maxResults=100",
        auth=auth,
        opener=opener,
    )
    if not isinstance(payload, dict):
        return ("body_edited",), True
    is_last = payload.get("isLast")
    truncated = is_last is not True
    values = payload.get("values")
    kinds: list[str] = []
    if isinstance(values, list):
        for history in values:
            if not isinstance(history, dict):
                continue
            created = history.get("created")
            if not _jira_time_after(created, since_time):
                continue
            items = history.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                _append_kind(kinds, item.get("field"))

    if not kinds:
        kinds.append("body_edited")
    return tuple(kinds), truncated


def _append_kind(kinds: list[str], field: object) -> None:
    if field == "description" and "body_edited" not in kinds:
        kinds.append("body_edited")
    elif field == "status" and "state_changed" not in kinds:
        kinds.append("state_changed")
    elif field == "labels" and "labels_changed" not in kinds:
        kinds.append("labels_changed")


def _jira_time_after(value: object, since_time: datetime) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return parse_since(value) > since_time
    except ValueError:
        return True


def _extract_labels(labels_payload: object) -> tuple[str, ...]:
    if not isinstance(labels_payload, list):
        return ()
    return tuple(sorted({label for label in labels_payload if isinstance(label, str)}))


def _build_detail(
    key: str, state: str, labels: tuple[str, ...], change_kinds: tuple[str, ...],
) -> str:
    parts: list[str] = []
    if "state_changed" in change_kinds:
        parts.append(f"status is now {state}")
    if "labels_changed" in change_kinds:
        label_str = ", ".join(labels) if labels else "none"
        parts.append(f"labels now: {label_str}")
    if "body_edited" in change_kinds:
        parts.append("description updated")
    return f"Jira {key} updated: {'; '.join(parts)}."


def _get_json(url: str, *, auth: tuple[str, str], opener: HttpOpener) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": _basic_auth_header(auth),
            "User-Agent": "teamctx-jira-issues-probe",
        },
    )
    try:
        with opener(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise JiraProbeError("Jira API request failed", status_code=exc.code) from exc
    except URLError as exc:
        raise JiraProbeError(f"Jira API request failed: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise JiraProbeError("Jira API response was not valid JSON") from exc


def _basic_auth_header(auth: tuple[str, str]) -> str:
    raw = f"{auth[0]}:{auth[1]}".encode("utf-8")
    return f"Basic {base64.b64encode(raw).decode('ascii')}"


def _jira_error_message(error: JiraProbeError) -> str:
    if error.status_code in {401, 403, 404}:
        return "Jira is unavailable with current access."
    if error.status_code == 429:
        return "Jira is rate-limited."
    return "Jira is unavailable."
