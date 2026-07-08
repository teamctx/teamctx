"""Row 8: Docs, Confluence, through the real connector and renderer.

(a) A Confluence page with ``teamctx.superseded_by`` fires the docs card with the page title and
replacement, and ``open-source`` opens the page's webui URL.
(b) A typo'd space key reports the exact source-status copy and the rendered docs coverage reads
couldn't-reach-Confluence, never clear.
(c) A clean configured Confluence space reads as the real docs green beside honest other checks.
(d) Reflex mode reports the full-work-start skip note, while the hook stays silent on docs because
docs is not a glanceable check (program spec rev 2, row 8).
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path

from emulation.actors import (
    DEFAULT_SLUG,
    SYNTHETIC_TOKEN,
    SubprocessEnv,
    build_lab_repo,
    commit_files,
    pretooluse_event,
    process_env,
    run_cli,
    run_hook,
    write_file,
)
from emulation.evidence import Expectation, RowResult, combine, passed_or_failed
from emulation.mockconfluence import (
    ConfluenceFixtures,
    MockConfluence,
    no_property_payload,
    page_item,
    pages_payload,
    property_payload,
    space_item,
)
from emulation.mockgh import Fixtures, MockGitHub, check_runs_payload, graphql_page
from teamctx.contract_render import render_broker_answer
from teamctx.core.broker import BrokerAnswer
from teamctx.resolve import resolve_work_start_inputs
from teamctx.work_start import work_start_answer

ROW_ID = "08"
TITLE = "Docs, Confluence"

_PATH = "src/app.py"
_SPACE_ID = "space-100"
_SPACE_KEY = "TS"
_TYPO_SPACE_KEY = "TSS"
_PAGE_ID = "4242"
_PAGE_TITLE = "Rounding Policy"
_REPLACEMENT = "Rounding Policy v2"
_WEBUI = f"/spaces/{_SPACE_KEY}/pages/{_PAGE_ID}/Rounding+Policy"
_OBSERVED = "2026-07-03T12:00:00Z"
_ATLASSIAN_EMAIL = "operator@emulation.example"
_ATLASSIAN_TOKEN = "synthetic-atlassian-token"


def _github_clear() -> Fixtures:
    return Fixtures(graphql_pages=[graphql_page([])], check_runs=check_runs_payload([]))


def _space_with_page(*, property_value: str | None) -> ConfluenceFixtures:
    return ConfluenceFixtures(
        spaces={_SPACE_KEY: space_item(_SPACE_ID, _SPACE_KEY)},
        pages={
            _SPACE_ID: pages_payload(page_item(_PAGE_ID, _PAGE_TITLE, webui=_WEBUI))
        },
        properties={
            _PAGE_ID: (
                property_payload(property_value)
                if property_value is not None
                else no_property_payload()
            )
        },
    )


def _write_config(repo_root: Path, *, confluence_base_url: str, space_key: str) -> None:
    write_file(
        repo_root,
        ".teamctx/config.json",
        json.dumps(
            {
                "schema_version": "teamctx.project_config.v0",
                "work_start": {
                    "repo": DEFAULT_SLUG,
                    "confluence": {
                        "base_url": confluence_base_url,
                        "space_key": space_key,
                    },
                },
            }
        ),
    )
    commit_files(repo_root, ".teamctx/config.json")


def _env(*, github_api_root: str, ambient_state: Path | None = None) -> SubprocessEnv:
    return SubprocessEnv(
        api_root=github_api_root,
        ambient_state=ambient_state,
        atlassian_email=_ATLASSIAN_EMAIL,
        atlassian_api_token=_ATLASSIAN_TOKEN,
    )


def _render_answer(
    repo_root: Path,
    *,
    github_api_root: str,
    profile: str = "full",
) -> tuple[str, BrokerAnswer]:
    with process_env(
        TEAMCTX_GITHUB_API_ROOT=github_api_root,
        GITHUB_TOKEN=SYNTHETIC_TOKEN,
        GITHUB_TOKEN_FILE=None,
        TEAMCTX_DISABLE_GH_AUTH="1",
        GITLAB_TOKEN=None,
        GITLAB_TOKEN_FILE=None,
        ATLASSIAN_EMAIL=_ATLASSIAN_EMAIL,
        ATLASSIAN_API_TOKEN=_ATLASSIAN_TOKEN,
        ATLASSIAN_API_TOKEN_FILE=None,
    ):
        inputs = resolve_work_start_inputs(paths=(_PATH,), token=SYNTHETIC_TOKEN, root=repo_root)
        if profile == "reflex":
            inputs = replace(inputs, profile="reflex")
        answer = work_start_answer(inputs, observed_at=_OBSERVED, project_root=repo_root)
    return render_broker_answer(answer), answer


def _source_note(answer: BrokerAnswer, source_id: str) -> str:
    for entry in answer.selection.coverage.entries:
        if entry.source_id == source_id and entry.note is not None:
            return entry.note
    raise AssertionError(f"missing source note for {source_id}")


def _superseded_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "superseded", branch="feature", files={_PATH: "x\n"})
    with MockGitHub(_github_clear()) as gh, MockConfluence(
        _space_with_page(property_value=_REPLACEMENT)
    ) as confluence:
        _write_config(repo.root, confluence_base_url=confluence.base_url, space_key=_SPACE_KEY)
        env = _env(github_api_root=gh.api_root)
        work_start = run_cli(["work-start", "--path", _PATH], cwd=repo.root, env=env)
        open_source = run_cli(
            ["open-source", f"doc:{_PAGE_TITLE}", "--path", _PATH],
            cwd=repo.root,
            env=env,
        )

    actual = f"--- work-start ---\n{work_start.output}\n--- open-source ---\n{open_source.output}"
    expectation = Expectation(
        must_match=(
            "Before you start, here is what to handle first:",
            f"{_PAGE_TITLE} was superseded by {_REPLACEMENT}: rely on the current one instead",
            f"Open the source for {_PAGE_TITLE}:",
            f"open {{url}}/wiki{_WEBUI}",
        ),
        must_absent=("Looks clear to start.", "the docs you rely on are current"),
    )
    return passed_or_failed(
        ROW_ID, TITLE, actual, expectation, note="superseded page + open-source"
    )


def _space_typo_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "space-typo", branch="feature", files={_PATH: "x\n"})
    with MockGitHub(_github_clear()) as gh, MockConfluence(
        _space_with_page(property_value=None)
    ) as confluence:
        _write_config(
            repo.root,
            confluence_base_url=confluence.base_url,
            space_key=_TYPO_SPACE_KEY,
        )
        text, answer = _render_answer(repo.root, github_api_root=gh.api_root)

    actual = f"{text}\n--- source-status ---\n{_source_note(answer, 'confluence_pages')}"
    expectation = Expectation(
        must_match=(
            "Couldn't check: the docs you rely on (couldn't reach Confluence).",
            "the configured Confluence space couldn't be found with current access.",
        ),
        must_absent=("the docs you rely on are current",),
    )
    return passed_or_failed(ROW_ID, TITLE, actual, expectation, note="space-key typo")


def _clean_space_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "clean", branch="feature", files={_PATH: "x\n"})
    with MockGitHub(_github_clear()) as gh, MockConfluence(
        _space_with_page(property_value=None)
    ) as confluence:
        _write_config(repo.root, confluence_base_url=confluence.base_url, space_key=_SPACE_KEY)
        run = run_cli(
            ["work-start", "--path", _PATH],
            cwd=repo.root,
            env=_env(github_api_root=gh.api_root),
        )

    expectation = Expectation(
        must_match=(
            "Looks clear to start.",
            "the docs you rely on are current",
            "no other open PRs touch your files",
            "no failing checks found",
        ),
        must_absent=(
            "couldn't reach Confluence",
            "Before you start, here is what to handle first:",
        ),
    )
    return passed_or_failed(ROW_ID, TITLE, run.output, expectation, note="clean space")


def _reflex_sub_row(tmp: Path) -> RowResult:
    repo = build_lab_repo(tmp / "reflex", branch="feature", files={_PATH: "x\n"})
    with MockGitHub(_github_clear()) as gh, MockConfluence(
        _space_with_page(property_value=_REPLACEMENT)
    ) as confluence:
        _write_config(repo.root, confluence_base_url=confluence.base_url, space_key=_SPACE_KEY)
        profile_text, _answer = _render_answer(
            repo.root, github_api_root=gh.api_root, profile="reflex"
        )
        hook_context = run_hook(
            pretooluse_event(cwd=repo.root, file_path=_PATH),
            cwd=repo.root,
            env=_env(github_api_root=gh.api_root, ambient_state=tmp / "ambient"),
        )

    actual = f"--- profile=reflex work-start ---\n{profile_text}\n--- hook ---\n{hook_context}"
    profile_result = passed_or_failed(
        ROW_ID,
        TITLE,
        profile_text,
        Expectation(
            must_match=(
                "Confluence docs are skipped in the quick pre-edit check; run teamctx "
                "work-start for the full scan.",
            ),
            must_absent=(f"{_PAGE_TITLE} was superseded by {_REPLACEMENT}",),
        ),
        note="profile=reflex work-start",
    )
    hook_result = passed_or_failed(
        ROW_ID,
        TITLE,
        hook_context,
        Expectation(
            must_absent=(
                "Confluence",
                "docs",
                f"{_PAGE_TITLE} was superseded by {_REPLACEMENT}",
            ),
        ),
        note="hook docs silence",
    )
    combined = combine(ROW_ID, TITLE, [profile_result, hook_result], actual=actual)
    # Keep the row-level evidence compact: the two sub-results above carry the precise split.
    return RowResult(
        row_id=combined.row_id,
        title=combined.title,
        status=combined.status,
        outcomes=combined.outcomes,
        actual=actual,
        note="reflex skip + hook silence",
    )


def run_offline() -> RowResult:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        parts = [
            _superseded_sub_row(tmp),
            _space_typo_sub_row(tmp),
            _clean_space_sub_row(tmp),
            _reflex_sub_row(tmp),
        ]
    return combine(ROW_ID, TITLE, parts)


if __name__ == "__main__":  # pragma: no cover
    result = run_offline()
    print(result.status)
    print(result.actual)
    for outcome in result.outcomes:
        print(outcome.ok, outcome.kind, repr(outcome.subject)[:90])
