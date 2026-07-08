from __future__ import annotations

from dataclasses import dataclass

import teamctx.contract_render as report_copy
import teamctx.hook_signal as hook_copy
import teamctx.runner as runner_copy
from teamctx.ambient import Delta, FindingMaterial
from teamctx.connectors.forge_review import ForgeReviewPullRequest, normalize_forge_review_prs
from teamctx.core.contracts import RequestContext


@dataclass(frozen=True)
class InventorySlot:
    slot: str
    value: str


OBSERVED_AT = "2026-07-08T00:00:00Z"


def _request(*, branch: str | None = "feature") -> RequestContext:
    return RequestContext(
        schema_version="teamctx.request_context.v0",
        request_id="inventory",
        repo="acme/widgets",
        forge="github",
        branch=branch,
        task="work",
        paths=["src/app.py"],
        linked_issues=[],
        requested_at=OBSERVED_AT,
        requesting_principal=None,
    )


def _review(
    *,
    provider: str,
    number: int,
    head_ref: str | None = "feature",
) -> ForgeReviewPullRequest:
    return ForgeReviewPullRequest(
        provider=provider,  # type: ignore[arg-type]
        repo="acme/widgets",
        number=number,
        state="open",
        url=f"https://example.invalid/{number}",
        title=None,
        changed_paths=("src/app.py",),
        created_at=OBSERVED_AT,
        updated_at=OBSERVED_AT,
        head_ref=head_ref,
        head_repo="acme/widgets",
        source_project_id=1,
        target_project_id=1,
    )


def _forge_status_message(
    *,
    provider: str = "github",
    own_numbers: tuple[int, ...] = (),
    coverage_unbounded_list: bool = False,
    unbounded_files_prs: tuple[int, ...] = (),
    diff_checked_count: int | None = None,
    diff_unchecked_count: int = 0,
) -> str:
    reviews = [
        _review(provider=provider, number=number)
        for number in own_numbers
    ]
    if unbounded_files_prs:
        reviews.extend(
            _review(provider=provider, number=number, head_ref="someone-else")
            for number in unbounded_files_prs
        )
    doc = normalize_forge_review_prs(
        _request(),
        reviews,
        observed_at=OBSERVED_AT,
        provider=provider,  # type: ignore[arg-type]
        source_id=f"{provider}_review_metadata",
        coverage_unbounded_list=coverage_unbounded_list,
        unbounded_files_prs=unbounded_files_prs,
        diff_checked_count=diff_checked_count,
        diff_unchecked_count=diff_unchecked_count,
    )
    return doc.source_statuses[0].safe_user_message


def _delta_line(delta: Delta, *, forge: str = "github") -> str:
    return report_copy.delta_lines((delta,), (), forge)[0]


def _check_copy_inventory() -> list[InventorySlot]:
    slots: list[InventorySlot] = []
    for check, copy in report_copy.RENDER_COPY.items():
        slots.extend(
            [
                InventorySlot(f"check.{check}.copy.coverage.clear.github", copy.clear),
                InventorySlot(
                    f"check.{check}.copy.coverage.not_configured.default",
                    copy.not_checked,
                ),
                InventorySlot(
                    f"check.{check}.copy.coverage.unreachable.github",
                    copy.unreachable,
                ),
                InventorySlot(
                    f"check.{check}.copy.finding.action.default",
                    copy.finding_action,
                ),
                InventorySlot(f"check.{check}.copy.hook.clear.github", copy.hook_clear),
            ]
        )
        if copy.hook_gap is not None:
            slots.append(InventorySlot(f"check.{check}.copy.hook.gap.github", copy.hook_gap))
        if copy.gitlab_clear is not None:
            slots.append(
                InventorySlot(f"check.{check}.copy.coverage.clear.gitlab", copy.gitlab_clear)
            )
        if copy.gitlab_unreachable is not None:
            slots.append(
                InventorySlot(
                    f"check.{check}.copy.coverage.unreachable.gitlab",
                    copy.gitlab_unreachable,
                )
            )
        if copy.gitlab_hook_clear is not None:
            slots.append(
                InventorySlot(f"check.{check}.copy.hook.clear.gitlab", copy.gitlab_hook_clear)
            )
        if copy.gitlab_hook_gap is not None:
            slots.append(
                InventorySlot(f"check.{check}.copy.hook.gap.gitlab", copy.gitlab_hook_gap)
            )
    return slots


def _closure_copy_inventory() -> list[InventorySlot]:
    return [
        InventorySlot(
            f"check.{check}.copy.coverage.pending",
            report_copy._pending_phrase(check),  # noqa: SLF001
        )
        for check in ("conflict", "criteria", "docs", "gate")
    ] + [
        InventorySlot(
            f"check.{check}.copy.coverage.not_applicable",
            report_copy._not_applicable_phrase(check),  # noqa: SLF001
        )
        for check in ("conflict", "criteria", "docs", "gate")
    ]


def _source_copy_inventory() -> list[InventorySlot]:
    return [
        InventorySlot(
            f"source.docs.status.{source_id}.{status}.copy",
            value,
        )
        for (source_id, status), value in sorted(report_copy._DOCS_FAILURE_COPY.items())  # noqa: SLF001
    ] + [
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.advisory.own_branch.single",
            _forge_status_message(own_numbers=(12,)),
        ),
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.advisory.own_branch.multiple",
            _forge_status_message(own_numbers=(12, 14)),
        ),
        InventorySlot(
            "source.git_hosting.status.gitlab_mr_metadata.advisory.own_branch.single",
            _forge_status_message(provider="gitlab", own_numbers=(12,)),
        ),
        InventorySlot(
            "source.git_hosting.status.gitlab_mr_metadata.advisory.own_branch.multiple",
            _forge_status_message(provider="gitlab", own_numbers=(12, 14)),
        ),
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.unbounded.page_limit",
            _forge_status_message(coverage_unbounded_list=True),
        ),
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.unbounded.diff_limit",
            _forge_status_message(diff_checked_count=20, diff_unchecked_count=3),
        ),
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.unbounded.unchecked_files",
            _forge_status_message(unbounded_files_prs=(12,)),
        ),
        InventorySlot(
            "source.git_hosting.status.github_pr_metadata.fresh.default",
            _forge_status_message(),
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.no_issue",
            runner_copy._CRITERIA_NO_ISSUE,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.no_since.template",
            runner_copy._CRITERIA_NO_SINCE,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.no_since.cap_note",
            runner_copy._CAP_NOTE,  # noqa: SLF001
        ),
        InventorySlot(
            "source.docs.status.disabled.no_docs_root",
            runner_copy._DOCS_DISABLED,  # noqa: SLF001
        ),
        InventorySlot(
            "source.ci_deploy.status.disabled.github.no_branch",
            runner_copy._GATE_DISABLED,  # noqa: SLF001
        ),
        InventorySlot(
            "source.ci_deploy.status.disabled.gitlab.no_branch",
            runner_copy._GITLAB_GATE_DISABLED,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.gitlab_unwired",
            runner_copy._GITLAB_ISSUES_DISABLED,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.gitlab_unwired.policy_reason",
            runner_copy._GITLAB_ISSUES_MESSAGE,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.disabled.jira_unconfigured.template",
            runner_copy._JIRA_UNCONFIGURED,  # noqa: SLF001
        ),
        InventorySlot(
            "source.issue_tracker.status.unavailable.jira_half_credential",
            runner_copy._JIRA_HALF_CREDENTIAL,  # noqa: SLF001
        ),
        InventorySlot(
            "source.docs.status.disabled.confluence_reflex_skip",
            runner_copy._CONFLUENCE_REFLEX_SKIP,  # noqa: SLF001
        ),
        InventorySlot(
            "source.docs.status.unavailable.confluence_half_credential",
            runner_copy._CONFLUENCE_HALF_CREDENTIAL,  # noqa: SLF001
        ),
        InventorySlot(
            "source.git_hosting.status.not_applicable.empty_paths",
            runner_copy._EMPTY_PATH_CONFLICT_NOTE,  # noqa: SLF001
        ),
    ]


def _delta_copy_inventory() -> list[InventorySlot]:
    return [
        InventorySlot(
            "check.conflict.copy.delta.appear",
            _delta_line(
                Delta(
                    "appear",
                    "conflict",
                    FindingMaterial(
                        key="conflict:7",
                        source_display="GitHub PR #7",
                        paths=("src/auth/token.py",),
                    ),
                )
            ),
        ),
        InventorySlot(
            "check.gate.copy.delta.appear",
            _delta_line(
                Delta(
                    "appear",
                    "gate",
                    FindingMaterial(key="gate:build", source_display="CI: build", gate="build"),
                )
            ),
        ),
        InventorySlot(
            "check.criteria.copy.delta.appear",
            _delta_line(
                Delta(
                    "appear",
                    "criteria",
                    FindingMaterial(
                        key="criteria:#12",
                        source_display="GitHub issue #12",
                        detail="acceptance criteria edited",
                    ),
                )
            ),
        ),
        InventorySlot(
            "check.docs.copy.delta.appear.with_replacement",
            _delta_line(
                Delta(
                    "appear",
                    "docs",
                    FindingMaterial(
                        key="docs:spec.md",
                        doc="spec.md",
                        superseded_by="spec-v2.md",
                    ),
                )
            ),
        ),
        InventorySlot(
            "check.docs.copy.delta.appear.without_replacement",
            _delta_line(
                Delta("appear", "docs", FindingMaterial(key="docs:spec.md", doc="spec.md"))
            ),
        ),
        InventorySlot(
            "check.conflict.copy.delta.disappear",
            _delta_line(
                Delta(
                    "disappear",
                    "conflict",
                    FindingMaterial(key="conflict:7", source_display="GitHub PR #7"),
                )
            ),
        ),
        InventorySlot(
            "check.gate.copy.delta.disappear",
            _delta_line(
                Delta(
                    "disappear",
                    "gate",
                    FindingMaterial(key="gate:build", source_display="CI: build", gate="build"),
                )
            ),
        ),
        InventorySlot(
            "check.criteria.copy.delta.disappear",
            _delta_line(
                Delta(
                    "disappear",
                    "criteria",
                    FindingMaterial(key="criteria:#12", source_display="GitHub issue #12"),
                )
            ),
        ),
        InventorySlot(
            "check.docs.copy.delta.disappear",
            _delta_line(
                Delta("disappear", "docs", FindingMaterial(key="docs:spec.md", doc="spec.md"))
            ),
        ),
        InventorySlot(
            "check.conflict.copy.delta.coverage_shrank.github",
            _delta_line(
                Delta(
                    "coverage_shrank",
                    "conflict",
                    FindingMaterial(key="conflict:__source__"),
                    note="couldn't reach GitHub",
                )
            ),
        ),
        InventorySlot(
            "check.conflict.copy.delta.coverage_shrank.gitlab",
            _delta_line(
                Delta(
                    "coverage_shrank",
                    "conflict",
                    FindingMaterial(key="conflict:__source__"),
                    note="couldn't reach GitLab",
                ),
                forge="gitlab",
            ),
        ),
        InventorySlot(
            "check.gate.copy.delta.coverage_shrank.github",
            _delta_line(Delta("coverage_shrank", "gate", FindingMaterial(key="gate:__source__"))),
        ),
        InventorySlot(
            "check.criteria.copy.delta.coverage_shrank.fallback",
            _delta_line(
                Delta("coverage_shrank", "criteria", FindingMaterial(key="criteria:__source__"))
            ),
        ),
        InventorySlot(
            "check.docs.copy.delta.coverage_shrank.fallback",
            _delta_line(Delta("coverage_shrank", "docs", FindingMaterial(key="docs:__source__"))),
        ),
    ]


def _provenance_inventory() -> list[InventorySlot]:
    return [
        InventorySlot(
            "check.criteria.copy.provenance.single.branch",
            report_copy._criteria_provenance_suffix(  # noqa: SLF001
                type(
                    "Answer",
                    (),
                    {
                        "request": type(
                            "Request",
                            (),
                            {
                                "linked_issues": ["#42"],
                                "input_provenance": {"issue:#42": "your branch name"},
                            },
                        )()
                    },
                )()
            ),
        ),
        InventorySlot(
            "check.criteria.copy.provenance.multi.commit_trailer",
            report_copy._criteria_provenance_suffix(  # noqa: SLF001
                type(
                    "Answer",
                    (),
                    {
                        "request": type(
                            "Request",
                            (),
                            {
                                "linked_issues": ["#12", "#34"],
                                "input_provenance": {
                                    "issue:#12": "your branch name",
                                    "issue:#34": "a commit message trailer",
                                },
                            },
                        )()
                    },
                )()
            ),
        ),
    ]


def _surface_inventory() -> list[InventorySlot]:
    return [
        *(
            InventorySlot(f"surface.report.headline.{key}", value)
            for key, value in report_copy._HEADLINE.items()  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.headline.none_checked",
            "Nothing checked yet; here's why:",
        ),
        InventorySlot("surface.report.coverage.clear_label.ready", "Checked: "),
        InventorySlot("surface.report.coverage.clear_label.non_ready", "Also checked: "),
        InventorySlot("surface.report.fyi.prefix", "FYI: "),
        InventorySlot("surface.report.gap.unreachable.prefix", "Couldn't check: "),
        InventorySlot("surface.report.gap.unbounded.prefix", "Partially checked: "),
        InventorySlot("surface.report.gap.not_configured.prefix", "Not checked: "),
        InventorySlot("surface.report.gap.pending.prefix", "Still running: "),
        InventorySlot("surface.report.gap.not_applicable.prefix", "Not applicable: "),
        InventorySlot(
            "surface.report.gap.pending.gate_bullet",
            report_copy._pending_bullet("gate"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.gap.fix.github",
            report_copy._fix_text("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.gap.fix.gitlab",
            report_copy._fix_text("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.source_name.github",
            report_copy._source_name("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.source_name.gitlab",
            report_copy._source_name("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.conflict_label.github",
            report_copy._conflict_label("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.conflict_label.gitlab",
            report_copy._conflict_label("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.gate_label.github",
            report_copy._gate_label("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.gate_label.gitlab",
            report_copy._gate_label("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.colliding_review_phrase.github",
            report_copy._colliding_review_phrase("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.colliding_review_phrase.gitlab",
            report_copy._colliding_review_phrase("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.red_gate_phrase.github",
            report_copy._red_gate_phrase("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.red_gate_phrase.gitlab",
            report_copy._red_gate_phrase("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.missing_both_phrase.github",
            report_copy._missing_both_phrase("github"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.report.missing_both_phrase.gitlab",
            report_copy._missing_both_phrase("gitlab"),  # noqa: SLF001
        ),
        InventorySlot(
            "surface.why.body.status_only",
            "teamctx shows metadata only here; it does not read the source body.",
        ),
        InventorySlot("surface.why.body.blocked", "Source body access is blocked by policy."),
        InventorySlot("surface.why.body.unavailable", "Source body is unavailable."),
        InventorySlot(
            "surface.open_source.body.status_only",
            "teamctx shows metadata only; the source body is not included "
            "(status-only by policy).",
        ),
        InventorySlot(
            "surface.open_source.body.blocked",
            "Source body access is blocked by policy.",
        ),
        InventorySlot("surface.open_source.body.unavailable", "Source body is unavailable."),
        InventorySlot(
            "surface.hook.heads_up.lead.with_file",
            "teamctx: before you edit src/app.py, from the team's current work:",
        ),
        InventorySlot(
            "surface.hook.heads_up.lead.without_file",
            "teamctx: before you start, from the team's current work:",
        ),
        InventorySlot(
            "surface.hook.heads_up.tail",
            "Factor these into your plan, and surface anything relevant to your human "
            "collaborator so they can decide.",
        ),
        InventorySlot(
            "surface.hook.gap.pending_gate",
            "CI checks are still running, so the gate isn't confirmed green yet.",
        ),
        InventorySlot(
            "surface.hook.cant_verify.no_token.github",
            hook_copy._cant_verify(  # noqa: SLF001
                type(
                    "Assessment",
                    (),
                    {
                        "deltas": (),
                        "checks": (
                            type(
                                "CheckState",
                                (),
                                {
                                    "check": "conflict",
                                    "status": "unreachable",
                                    "failing_sources": (),
                                    "note": None,
                                },
                            )(),
                        ),
                    },
                )(),
                False,
                "github",
            ),
        ),
        InventorySlot(
            "surface.hook.cant_verify.with_token.github",
            hook_copy._cant_verify(  # noqa: SLF001
                type(
                    "Assessment",
                    (),
                    {
                        "deltas": (),
                        "checks": (
                            type(
                                "CheckState",
                                (),
                                {
                                    "check": "conflict",
                                    "status": "unreachable",
                                    "failing_sources": (),
                                    "note": None,
                                },
                            )(),
                        ),
                    },
                )(),
                True,
                "github",
            ),
        ),
        InventorySlot(
            "surface.hook.ready.with_file",
            hook_copy._ready(  # noqa: SLF001
                (
                    type("CheckState", (), {"check": "conflict", "status": "clear"})(),
                ),
                "src/app.py",
                "github",
            ),
        ),
        InventorySlot(
            "surface.hook.ready.without_file",
            hook_copy._ready(  # noqa: SLF001
                (
                    type("CheckState", (), {"check": "conflict", "status": "clear"})(),
                ),
                None,
                "github",
            ),
        ),
        InventorySlot("surface.hook.source_name.github", hook_copy._source_name("github")),  # noqa: SLF001
        InventorySlot("surface.hook.source_name.gitlab", hook_copy._source_name("gitlab")),  # noqa: SLF001
        InventorySlot("surface.hook.token_env.github", hook_copy._token_env("github")),  # noqa: SLF001
        InventorySlot("surface.hook.token_env.gitlab", hook_copy._token_env("gitlab")),  # noqa: SLF001
    ]


def _inventory() -> list[InventorySlot]:
    return [
        *_check_copy_inventory(),
        *_closure_copy_inventory(),
        *_source_copy_inventory(),
        *_delta_copy_inventory(),
        *_provenance_inventory(),
        *_surface_inventory(),
    ]


def test_migration_task_zero_inventory_has_a_future_slot_for_every_string() -> None:
    slots = _inventory()

    assert len(slots) == 122
    assert len({slot.slot for slot in slots}) == len(slots)
    assert all(slot.value for slot in slots)


def test_migration_task_zero_inventory_pins_current_render_strings() -> None:
    by_slot = {slot.slot: slot.value for slot in _inventory()}

    assert by_slot["check.conflict.copy.coverage.clear.github"] == (
        "no other open PRs touch your files"
    )
    assert by_slot["source.docs.status.confluence_pages.stale.copy"] == (
        "couldn't fully check Confluence"
    )
    assert by_slot["source.git_hosting.status.github_pr_metadata.advisory.own_branch.single"] == (
        "Your own open PR #12 for this branch touches these files; not flagged as a collision."
    )
    assert by_slot["source.git_hosting.status.gitlab_mr_metadata.advisory.own_branch.single"] == (
        "Your own open MR !12 for this branch touches these files; not flagged as a collision."
    )
    assert by_slot["check.criteria.copy.provenance.single.branch"] == (
        "(issue #42 from your branch name)"
    )
    assert by_slot["check.conflict.copy.delta.appear"] == (
        "since you started: GitHub PR #7 appeared, touching src/auth/token.py"
    )
