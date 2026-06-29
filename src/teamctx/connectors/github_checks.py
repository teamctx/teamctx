"""Narrow GitHub check-runs probe: surface failing checks for a ref."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from teamctx.connectors.gate_status import (
    FailingGate,
    normalize_failing_gates,
    pending_gates_document,
    unavailable_gates_document,
)
from teamctx.connectors.github import (
    DEFAULT_OPENER,
    GITHUB_API_ROOT,
    GitHubProbeError,
    HttpOpener,
    get_json,
    split_repo,
)
from teamctx.core.contracts import CoreContractDocument, RequestContext

# A completed check with one of these conclusions is a failing gate.
FAILING_CONCLUSIONS = frozenset({"failure", "timed_out", "action_required"})


@dataclass(frozen=True)
class CheckRunsFetch:
    """Result of fetching check-runs from the GitHub API.

    ``failing`` is the list of (name, url) pairs for completed failing check-runs.
    ``truncated`` is True when the response indicates more check-runs exist than we fetched,
    meaning we cannot assert all gates pass from an empty failing list alone.
    ``pending`` is True when any run is still queued or in progress, so even with no failing run
    the gate cannot be asserted green yet.
    """

    failing: list[tuple[str, str]]
    truncated: bool
    pending: bool


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
        fetch = fetch_failing_check_runs(repo=repo, ref=ref, token=token, opener=opener)
    except GitHubProbeError as exc:
        return unavailable_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message=_checks_error_message(exc),
        )
    gates = [
        FailingGate(repo=repo, gate_name=name, url=url, files=tuple(request_context.paths))
        for name, url in fetch.failing
    ]
    if not gates and not fetch.truncated and fetch.pending:
        # Precedence: found (failing gates) > truncated (stale) > pending. Only emit pending when
        # there is genuinely nothing worse to report.
        return pending_gates_document(
            request_context,
            repo=repo,
            observed_at=observed_at,
            safe_user_message="CI checks are still running; the gate is not confirmed green yet.",
        )
    return normalize_failing_gates(
        request_context,
        gates,
        observed_at=observed_at,
        coverage_truncated=fetch.truncated,
    )


def fetch_failing_check_runs(
    *, repo: str, ref: str, token: str, opener: HttpOpener = DEFAULT_OPENER
) -> CheckRunsFetch:
    owner, name = split_repo(repo)
    url = (
        f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}"
        f"/commits/{quote(ref)}/check-runs?per_page=100"
    )
    payload = get_json(url, token=token, opener=opener)
    if not isinstance(payload, dict) or not isinstance(payload.get("check_runs"), list):
        # A malformed shape must never read as "no failing checks" (a false clear). Routed to
        # unavailable by the caller's GitHubProbeError handler.
        raise GitHubProbeError("GitHub check-runs response was malformed")
    failing = parse_failing_check_runs(payload)
    truncated = _detect_truncation(payload)
    pending = parse_incomplete_check_runs(payload)
    return CheckRunsFetch(failing=failing, truncated=truncated, pending=pending)


def parse_incomplete_check_runs(payload: object) -> bool:
    """True when any check-run is still queued or in progress (status != 'completed').

    These runs are not failing (no conclusion yet) but mean the gate cannot be asserted green.
    """

    if not isinstance(payload, dict):
        return False
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        return False
    return any(isinstance(run, dict) and run.get("status") != "completed" for run in runs)


def _detect_truncation(payload: object) -> bool:
    """True when the response indicates more check-runs exist than we received.

    Uses total_count vs len(check_runs) when total_count is an int (exact detection).
    Falls back to len(check_runs) >= 100 when total_count is absent (conservative).
    """
    if not isinstance(payload, dict):
        return False
    runs = payload.get("check_runs")
    page_size = len(runs) if isinstance(runs, list) else 0
    total_count = payload.get("total_count")
    if isinstance(total_count, int):
        return total_count > page_size
    return page_size >= 100


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


def _checks_error_message(error: GitHubProbeError) -> str:
    if error.status_code in {401, 404}:
        return "CI status is unavailable with current access."
    if error.status_code == 403:
        return "CI status is unavailable or rate-limited with current access."
    if error.status_code == 429:
        return "CI status is rate-limited."
    return "CI status is unavailable."
