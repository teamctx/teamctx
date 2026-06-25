"""Narrow GitHub check-runs probe: surface failing required gates for a ref."""

from __future__ import annotations

from urllib.parse import quote

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
            safe_user_message=_checks_error_message(exc),
        )
    gates = [
        FailingGate(repo=repo, gate_name=name, url=url, files=tuple(request_context.paths))
        for name, url in failing
    ]
    return normalize_failing_gates(request_context, gates, observed_at=observed_at)


def fetch_failing_check_runs(
    *, repo: str, ref: str, token: str, opener: HttpOpener = DEFAULT_OPENER
) -> list[tuple[str, str]]:
    owner, name = split_repo(repo)
    url = (
        f"{GITHUB_API_ROOT}/repos/{quote(owner)}/{quote(name)}"
        f"/commits/{quote(ref)}/check-runs?per_page=100"
    )
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


def _checks_error_message(error: GitHubProbeError) -> str:
    if error.status_code in {401, 404}:
        return "CI status is unavailable with current access."
    if error.status_code == 403:
        return "CI status is unavailable or rate-limited with current access."
    if error.status_code == 429:
        return "CI status is rate-limited."
    return "CI status is unavailable."
