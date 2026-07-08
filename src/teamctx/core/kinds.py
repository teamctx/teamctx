"""The one card-kind registry: every fact about a card kind lives on its ``CardKind`` entry.

A card kind is a whole vertical: which source signal it derives from, the typed proposition it
asserts (an existential) and the universal that proposition refutes, how it renders to a human,
and the cost, dependency, and routing facts the rest of the broker needs. This module OWNS that
registry (``CARD_KINDS``) and DERIVES every lookup the engine, evaluator, severity, and
assessment used to keep as separate hand-written tables: predicate shapes, refutes pairs,
dependency closures, severity bases, verdict-to-check pairs, and reason-prefix routing. Adding a
kind is a single ``CardKind`` entry; no other table needs a new row.

Dependency direction (no cycles, one definition site per fact): this module imports the pure
datatypes and mechanisms (contracts, prop, severity) only. The engine (select), the evaluator
(evaluate), the broker, and assessment import this module; this module imports none of them.

Pure: dataclasses, typing, and internal core imports only (the core purity test guards this).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from teamctx.core.contracts import (
    ContextCard,
    RequestContext,
    SectionName,
    SourceSignal,
)
from teamctx.core.prop import Prop, PropShape, RefutesMatch, SubjectRef, Witness, witnesses_with
from teamctx.core.severity import compute_severity

CheckId = Literal["conflict", "criteria", "docs", "gate"]
CheckProfile = Literal["reflex", "full"]
CheckLane = Literal["important", "fyi"]


@dataclass(frozen=True)
class ClaimDeclaration:
    """The typed claim a check owns: the finding predicate, the clear-query predicate, and
    the structural match rule by which the finding refutes that query."""

    proposition: str
    card_predicate: str
    query_predicate: str
    refutes_match: RefutesMatch


@dataclass(frozen=True)
class ClosureDeclaration:
    """The closure propositions this check answers up front."""

    propositions: tuple[str, ...]


@dataclass(frozen=True)
class CoverageCopy:
    """Coverage phrases for one check across the report and hook surfaces."""

    clear: str
    not_checked: str
    unreachable: str
    pending: str
    not_applicable: str
    gitlab_clear: str | None = None
    gitlab_unreachable: str | None = None


@dataclass(frozen=True)
class HookCopy:
    clear: str
    gap: str | None
    gitlab_clear: str | None = None
    gitlab_gap: str | None = None


@dataclass(frozen=True)
class FindingCopy:
    action: str


@dataclass(frozen=True)
class SourceStatusCopy:
    """A check-owned source-status phrase keyed by the source contract that produced it."""

    source_id: str
    status: str
    text: str


@dataclass(frozen=True)
class ProvenanceCopy:
    item: str
    single: str
    multiple: str


@dataclass(frozen=True)
class DeltaCopy:
    appear: str
    disappear: str
    transition: str = "{source_name} is back: {tail}"
    coverage_shrank: str = "{gap} can no longer be verified ({note})"
    appear_without_replacement: str | None = None


@dataclass(frozen=True)
class CheckCopy:
    """The complete check-owned copy table. Compatibility properties keep older consumers
    readable while the migration moves them onto the structured contract."""

    coverage: CoverageCopy
    finding: FindingCopy
    hook: HookCopy
    delta: DeltaCopy
    source_status: tuple[SourceStatusCopy, ...] = ()
    provenance: ProvenanceCopy | None = None

    @property
    def clear(self) -> str:
        return self.coverage.clear

    @property
    def not_checked(self) -> str:
        return self.coverage.not_checked

    @property
    def unreachable(self) -> str:
        return self.coverage.unreachable

    @property
    def finding_action(self) -> str:
        return self.finding.action

    @property
    def hook_clear(self) -> str:
        return self.hook.clear

    @property
    def hook_gap(self) -> str | None:
        return self.hook.gap

    @property
    def gitlab_clear(self) -> str | None:
        return self.coverage.gitlab_clear

    @property
    def gitlab_unreachable(self) -> str | None:
        return self.coverage.gitlab_unreachable

    @property
    def gitlab_hook_clear(self) -> str | None:
        return self.hook.gitlab_clear

    @property
    def gitlab_hook_gap(self) -> str | None:
        return self.hook.gitlab_gap


@dataclass(frozen=True)
class IdentityDeclaration:
    """Fields that name a finding across runs. ``key_scope_fields`` preserve the stable
    ambient key; ``material_scope_fields`` are extra rendered-card scope fields the delta voice
    needs to speak the finding."""

    key_scope_fields: tuple[str, ...]
    material_scope_fields: tuple[str, ...] = ()

    @property
    def all_scope_fields(self) -> tuple[str, ...]:
        return self.key_scope_fields + self.material_scope_fields


@dataclass(frozen=True)
class ConfigSchema:
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class ForgeReviewAdvisoryCopy:
    own_branch_single: str
    own_branch_multiple: str
    unbounded_page: str
    unbounded_diff: str
    unbounded_files: str
    fresh: str


@dataclass(frozen=True)
class SourceContract:
    id: str
    advisory_copy: ForgeReviewAdvisoryCopy


FORGE_REVIEW_SOURCE_CONTRACT = SourceContract(
    id="source.git_hosting.forge_review",
    advisory_copy=ForgeReviewAdvisoryCopy(
        own_branch_single=(
            "Your own open {short} {numbers} for this branch touches these files; "
            "not flagged as a collision."
        ),
        own_branch_multiple=(
            "Your own open {plural} {numbers} for this branch touch these files; "
            "not flagged as collisions."
        ),
        unbounded_page=(
            "Checked the {count} most recently updated open {plural}; more exist, so this is "
            "not a complete check."
        ),
        unbounded_diff=(
            "Checked the files of the {checked_count} most recently updated open {plural}; "
            "{unchecked_count} more open {plural} were not file-checked."
        ),
        unbounded_files=(
            "Open {short} {prefix}{number} changes more files than teamctx checked; "
            "it may touch yours."
        ),
        fresh="Git-host {short} metadata refreshed.",
    ),
)


@dataclass(frozen=True)
class ClaimCard:
    """A derived typed claim paired with the source signal it was derived from.

    ``claim`` is the proposition the card asserts (and witnesses); ``signal`` carries the
    render inputs. The render card is a pure function of this pair (each kind's renderer).
    """

    claim: Prop
    signal: SourceSignal


# --- the four kinds' query propositions: the universal each kind's card refutes ---


def no_conflict_query(request: RequestContext) -> Prop:
    """The universal a collision card refutes: 'no open PR conflicts with my paths'."""

    return Prop(
        predicate="no_pr_conflicts_with_paths",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def criteria_changed_query(request: RequestContext) -> Prop:
    """The universal a criteria-changed card refutes: 'no acceptance criteria changed for
    my linked issues'."""

    return Prop(
        predicate="no_criteria_changed_for_issues",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.linked_issues)),
    )


def no_superseded_docs_query(request: RequestContext) -> Prop:
    """The universal a doc-superseded card refutes: 'no doc I rely on was superseded'."""

    return Prop(
        predicate="no_superseded_docs",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


def all_gates_pass_query(request: RequestContext) -> Prop:
    """The universal a missed-gate card refutes: 'all gates pass for my change'."""

    return Prop(
        predicate="all_gates_pass",
        subject=SubjectRef(repo=request.repo, paths=tuple(request.paths)),
    )


# --- the four kinds' derive functions: a P-visible signal + request -> a typed claim or None ---


def _derive_collision_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    candidate_files = signal.scope.get("files")
    candidate = candidate_files if isinstance(candidate_files, list) else []
    shared = sorted(set(request.paths) & set(candidate))
    if not shared:
        return None
    claim = Prop(
        predicate="pr_conflicts_with_path",
        subject=SubjectRef(repo=request.repo, paths=tuple(shared)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_criteria_changed_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    issue = signal.scope.get("issue")
    if not isinstance(issue, str) or issue not in request.linked_issues:
        return None
    claim = Prop(
        predicate="issue_criteria_changed",
        subject=SubjectRef(repo=request.repo, paths=(issue,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_doc_superseded_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    doc = signal.scope.get("doc")
    if not isinstance(doc, str):
        return None
    claim = Prop(
        predicate="doc_superseded",
        subject=SubjectRef(repo=request.repo, paths=(doc,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


def _derive_missed_gate_claim(
    request: RequestContext, signal: SourceSignal
) -> ClaimCard | None:
    if signal.scope.get("repo") != request.repo:
        return None
    gate = signal.scope.get("gate")
    if not isinstance(gate, str) or not gate:
        return None
    claim = Prop(
        predicate="gate_failed",
        subject=SubjectRef(repo=request.repo, paths=(gate,)),
        args=(signal.id,),
    )
    return ClaimCard(claim=claim, signal=signal)


# --- rendering: the shared skeleton, then one renderer per kind ---


def _render_claim_card(
    claim_card: ClaimCard,
    *,
    section: SectionName,
    why_this_matters: str,
    reason: str,
    reason_code: str,
) -> ContextCard:
    """The shared render skeleton. Every kind's card differs only in section, why, reason,
    and reason_code; the rest (status-only body, verify-before-relying, severity) is uniform."""

    claim = claim_card.claim
    signal = claim_card.signal
    return ContextCard(
        schema_version="teamctx.context_card.v0",
        id=f"card_{signal.id}",
        section=section,
        text=signal.evidence_summary,
        why_this_matters=why_this_matters,
        source_display=signal.source_display,
        refs=[signal.id],
        reason=reason,
        scope=dict(signal.scope),
        freshness=signal.freshness,
        confidence=signal.confidence,
        source_body="status_only",
        source_open_target_id=None,
        agent_instruction="verify_before_relying",
        reason_code=reason_code,
        severity=compute_severity(severity_base_for(claim.predicate), claim),
    )


def render_collision_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a collision claim into a human-plane ``ContextCard``.

    Pure: the render card is a function of the claim plus its signal. Output matches the
    pre-typed collision derivation byte for byte.
    """

    claim = claim_card.claim
    overlap = ", ".join(claim.subject.paths)
    return _render_claim_card(
        claim_card,
        section="Needs attention",
        why_this_matters=f"you are editing {claim.subject.paths[0]}.",  # most-salient path
        reason=f"same repository and file path as the current task: {overlap}",
        reason_code="collision.same_path",
    )


def render_criteria_changed_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a criteria-changed claim into a human-plane ``ContextCard``."""

    issue = claim_card.claim.subject.paths[0]
    return _render_claim_card(
        claim_card,
        section="Verify before relying",
        why_this_matters=f"acceptance criteria for {issue} changed; re-check before relying.",
        reason=f"linked issue {issue} had its acceptance criteria changed",
        reason_code="criteria.changed",
    )


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
    return _render_claim_card(
        claim_card,
        section="Verify before relying",
        why_this_matters=why,
        reason=reason,
        reason_code="doc.superseded",
    )


def render_missed_gate_claim(claim_card: ClaimCard) -> ContextCard:
    """Render a missed-gate claim into a human-plane ``ContextCard``."""

    gate = claim_card.claim.subject.paths[0]
    return _render_claim_card(
        claim_card,
        section="Needs attention",
        why_this_matters=f"a check is failing on this branch: {gate}.",
        reason=f"a check is failing on this branch: {gate}",
        reason_code="gate.failed",
    )


@dataclass(frozen=True)
class CardKind:
    """One registered check declaration: every fact about a check in one place.

    The legacy properties below keep the existing engine readable while callers migrate to the
    structured contract fields (claim, closure, copy, identity, lane/profile, and schema).
    """

    signal_type: str
    verdict_label: str
    check_id: CheckId
    reason_prefix: str  # "collision" | "criteria" | "doc" | "gate" (assessment routing)
    deps_family: str
    severity_base: float
    contract_version: int
    claim: ClaimDeclaration
    consumes: tuple[str, ...]
    closure: ClosureDeclaration
    copy: CheckCopy
    identity: IdentityDeclaration
    profile: CheckProfile
    lane: CheckLane
    config_schema: ConfigSchema
    derive: Callable[[RequestContext, SourceSignal], ClaimCard | None]
    query: Callable[[RequestContext], Prop]
    render: Callable[[ClaimCard], ContextCard]

    @property
    def id(self) -> CheckId:
        return self.check_id

    @property
    def card_predicate(self) -> str:
        return self.claim.card_predicate

    @property
    def query_predicate(self) -> str:
        return self.claim.query_predicate

    @property
    def refutes_match(self) -> RefutesMatch:
        return self.claim.refutes_match


CARD_KINDS: tuple[CardKind, ...] = (
    CardKind(
        signal_type="collision",
        verdict_label="Conflict check",
        check_id="conflict",
        reason_prefix="collision",
        deps_family="git_hosting",
        severity_base=0.8,
        contract_version=1,
        claim=ClaimDeclaration(
            proposition="an open PR or MR conflicts with the requested paths",
            card_predicate="pr_conflicts_with_path",
            query_predicate="no_pr_conflicts_with_paths",
            refutes_match="subject-overlap",
        ),
        consumes=("forge_review",),
        closure=ClosureDeclaration(propositions=("no_pr_conflicts_with_paths",)),
        copy=CheckCopy(
            coverage=CoverageCopy(
                clear="no other open PRs touch your files",
                not_checked="open PRs (couldn't determine the repository)",
                unreachable="open PRs (couldn't reach GitHub)",
                pending="conflict (still running, not confirmed yet)",
                not_applicable="conflict (not applicable to the files in scope)",
                gitlab_clear="no other open MRs touch your files",
                gitlab_unreachable="open MRs (couldn't reach GitLab)",
            ),
            finding=FindingCopy(
                action="look at it before you edit so you don't undo each other's work"
            ),
            hook=HookCopy(
                clear="no other open pull requests touch these files",
                gap="open pull requests",
                gitlab_clear="no other open merge requests touch these files",
                gitlab_gap="open merge requests",
            ),
            delta=DeltaCopy(
                appear="{source_display} appeared, touching {paths}",
                disappear="{source_display} no longer touches your files",
            ),
        ),
        identity=IdentityDeclaration(
            key_scope_fields=("pr_number",),
            material_scope_fields=("files",),
        ),
        profile="reflex",
        lane="important",
        config_schema=ConfigSchema(),
        derive=_derive_collision_claim,
        query=no_conflict_query,
        render=render_collision_claim,
    ),
    CardKind(
        signal_type="criteria_changed",
        verdict_label="Criteria check",
        check_id="criteria",
        reason_prefix="criteria",
        deps_family="issue_tracker",
        severity_base=0.5,
        contract_version=1,
        claim=ClaimDeclaration(
            proposition="acceptance criteria changed for a linked issue",
            card_predicate="issue_criteria_changed",
            query_predicate="no_criteria_changed_for_issues",
            refutes_match="subject-overlap",
        ),
        consumes=("issue_criteria",),
        closure=ClosureDeclaration(propositions=("no_criteria_changed_for_issues",)),
        copy=CheckCopy(
            coverage=CoverageCopy(
                clear="the linked issue's criteria are unchanged",
                not_checked="spec changes (no issue is linked to this branch; link one to enable)",
                unreachable="spec changes (couldn't reach GitHub)",
                pending="criteria (still running, not confirmed yet)",
                not_applicable="criteria (not applicable to the files in scope)",
            ),
            finding=FindingCopy(action="re-check the criteria before you rely on them"),
            hook=HookCopy(clear="the linked issue's criteria are unchanged", gap=None),
            delta=DeltaCopy(
                appear="{source_display} changed: {detail}",
                disappear="{source_display} is no longer flagged",
            ),
            provenance=ProvenanceCopy(
                item="{issue} from {source}",
                single="(issue {item})",
                multiple="(issues {items})",
            ),
        ),
        identity=IdentityDeclaration(key_scope_fields=("issue",)),
        profile="reflex",
        lane="fyi",
        config_schema=ConfigSchema(),
        derive=_derive_criteria_changed_claim,
        query=criteria_changed_query,
        render=render_criteria_changed_claim,
    ),
    CardKind(
        signal_type="doc_superseded",
        verdict_label="Docs check",
        check_id="docs",
        reason_prefix="doc",
        deps_family="docs",
        severity_base=0.4,
        contract_version=1,
        claim=ClaimDeclaration(
            proposition="a relied-on document was superseded",
            card_predicate="doc_superseded",
            query_predicate="no_superseded_docs",
            refutes_match="repo-wide",
        ),
        consumes=("docs_supersession",),
        closure=ClosureDeclaration(propositions=("no_superseded_docs",)),
        copy=CheckCopy(
            coverage=CoverageCopy(
                clear="the docs you rely on are current",
                not_checked="docs (no docs root is configured; set work_start.docs_root to enable)",
                unreachable="the docs you rely on (couldn't read the docs folder)",
                pending="docs (still running, not confirmed yet)",
                not_applicable="docs (not applicable to the files in scope)",
            ),
            finding=FindingCopy(action="rely on the current one instead"),
            hook=HookCopy(clear="the docs you rely on are current", gap=None),
            delta=DeltaCopy(
                appear="{doc} was superseded by {superseded_by}",
                appear_without_replacement="{doc} was superseded",
                disappear="the note about {doc} cleared",
            ),
            source_status=(
                SourceStatusCopy(
                    source_id="docs_supersession",
                    status="unavailable",
                    text="couldn't read the local docs folder",
                ),
                SourceStatusCopy(
                    source_id="docs_supersession",
                    status="stale",
                    text="couldn't fully check the local docs folder",
                ),
                SourceStatusCopy(
                    source_id="confluence_pages",
                    status="unavailable",
                    text="couldn't reach Confluence",
                ),
                SourceStatusCopy(
                    source_id="confluence_pages",
                    status="stale",
                    text="couldn't fully check Confluence",
                ),
            ),
        ),
        identity=IdentityDeclaration(
            key_scope_fields=("doc",),
            material_scope_fields=("superseded_by",),
        ),
        profile="reflex",
        lane="fyi",
        config_schema=ConfigSchema(),
        derive=_derive_doc_superseded_claim,
        query=no_superseded_docs_query,
        render=render_doc_superseded_claim,
    ),
    CardKind(
        signal_type="missed_gate",
        verdict_label="Gate check",
        check_id="gate",
        reason_prefix="gate",
        deps_family="ci_deploy",
        severity_base=0.7,
        contract_version=1,
        claim=ClaimDeclaration(
            proposition="a required gate is failing on this branch",
            card_predicate="gate_failed",
            query_predicate="all_gates_pass",
            refutes_match="repo-wide",
        ),
        consumes=("gate_status",),
        closure=ClosureDeclaration(propositions=("all_gates_pass",)),
        copy=CheckCopy(
            coverage=CoverageCopy(
                clear="no failing checks found",
                not_checked="failing checks (couldn't determine your branch)",
                unreachable="failing checks (couldn't reach GitHub)",
                pending="failing checks (CI still running, not confirmed green yet)",
                not_applicable="gate (not applicable to the files in scope)",
                gitlab_unreachable="pipeline state (couldn't reach GitLab)",
            ),
            finding=FindingCopy(
                action="fix it or wait for a green build before relying on it"
            ),
            hook=HookCopy(
                clear="no failing checks found",
                gap="failing checks",
                gitlab_gap="pipeline state",
            ),
            delta=DeltaCopy(
                appear="check '{gate}' started failing on this branch",
                disappear="check '{gate}' is green again",
            ),
        ),
        identity=IdentityDeclaration(key_scope_fields=("gate",)),
        profile="reflex",
        lane="important",
        config_schema=ConfigSchema(),
        derive=_derive_missed_gate_claim,
        query=all_gates_pass_query,
        render=render_missed_gate_claim,
    ),
)


# --- derived lookups: one definition site (CARD_KINDS); everything else reads these ---


@dataclass(frozen=True)
class CheckSelection:
    """Resolved team-level check selection in registry order."""

    enabled_checks: tuple[CheckId, ...]
    important_checks: tuple[CheckId, ...]
    disabled_checks: tuple[CheckId, ...]


DEFAULT_CHECK_IDS: tuple[CheckId, ...] = tuple(kind.check_id for kind in CARD_KINDS)
DEFAULT_IMPORTANT_CHECKS: tuple[CheckId, ...] = tuple(
    kind.check_id for kind in CARD_KINDS if kind.lane == "important"
)


def default_check_selection() -> CheckSelection:
    return CheckSelection(
        enabled_checks=DEFAULT_CHECK_IDS,
        important_checks=DEFAULT_IMPORTANT_CHECKS,
        disabled_checks=(),
    )


def resolve_check_selection(
    enabled: Iterable[CheckId] | None = None,
    *,
    lane_overrides: Mapping[CheckId, CheckLane] | None = None,
) -> CheckSelection:
    """Normalize enabled checks and lane overrides to registry order.

    ``enabled is None`` is the backward-compatible default four. A present checks block passes
    the explicit enabled set; any built-in not in that set is not enabled by the team.
    """

    if enabled is None:
        return default_check_selection()
    enabled_set = set(enabled)
    overrides = lane_overrides or {}
    enabled_checks = tuple(kind.check_id for kind in CARD_KINDS if kind.check_id in enabled_set)
    important_checks = tuple(
        kind.check_id
        for kind in CARD_KINDS
        if kind.check_id in enabled_set
        and overrides.get(kind.check_id, kind.lane) == "important"
    )
    disabled_checks = tuple(
        kind.check_id for kind in CARD_KINDS if kind.check_id not in enabled_set
    )
    return CheckSelection(
        enabled_checks=enabled_checks,
        important_checks=important_checks,
        disabled_checks=disabled_checks,
    )


def _build_predicate_registry() -> dict[str, PropShape]:
    """The predicates this build models and their logical shape, derived from the kinds. A
    universal ('no PR conflicts with any of my paths') is refuted by a single counterexample; an
    existential ('a PR conflicts with this path') is witnessed by a single instance."""

    registry: dict[str, PropShape] = {}
    for kind in CARD_KINDS:
        registry[kind.card_predicate] = "existential"
        registry[kind.query_predicate] = "universal"
    return registry


# The predicate shapes (8 entries: one existential + one universal per kind).
PREDICATE_REGISTRY: dict[str, PropShape] = _build_predicate_registry()

# Each pair is (card_predicate, query_predicate) mapped to the structural overlap a refutation
# requires: a card asserting card_predicate REFUTES the universal query_predicate under that
# match rule. Collision and criteria use subject-overlap (shared repo + at least one shared
# item). Docs and gate use repo-wide (shared repo alone): reliance is the whole declared docs
# set, and gate status is branch-scoped rather than file-scoped.
_REFUTES_MATCH: dict[tuple[str, str], RefutesMatch] = {
    (kind.card_predicate, kind.query_predicate): kind.refutes_match for kind in CARD_KINDS
}
REFUTES_PAIRS: frozenset[tuple[str, str]] = frozenset(_REFUTES_MATCH)

# Placeholder bases per card predicate (cost-of-not-knowing). Calibration deferred.
KIND_BASE: dict[str, float] = {kind.card_predicate: kind.severity_base for kind in CARD_KINDS}

# deps_G: the trusted, mandated source families a proposition's truth depends on. An
# unregistered predicate fails loud; we never silently certify a query whose dependencies we
# have not modeled.
DEPS_REGISTRY: dict[str, frozenset[str]] = {
    kind.query_predicate: frozenset({kind.deps_family}) for kind in CARD_KINDS
}

# The (verdict_label, check_id) pairs the assessment consumes to route each verdict to its check.
LABEL_CHECK_PAIRS: tuple[tuple[str, CheckId], ...] = tuple(
    (kind.verdict_label, kind.check_id) for kind in CARD_KINDS
)

# reason_prefix (the head of a card's reason_code, before the dot) -> the check it belongs to.
REASON_PREFIX: dict[str, CheckId] = {kind.reason_prefix: kind.check_id for kind in CARD_KINDS}

# check -> mandated source family, used by assessment to route disabled-source notes.
CHECK_DEPS_FAMILY: dict[CheckId, str] = {
    kind.check_id: kind.deps_family for kind in CARD_KINDS
}

CHECKS_BY_ID: dict[CheckId, CardKind] = {kind.check_id: kind for kind in CARD_KINDS}
CHECK_COPY: dict[CheckId, CheckCopy] = {
    kind.check_id: kind.copy for kind in CARD_KINDS
}
IMPORTANT_CHECKS: frozenset[CheckId] = frozenset(
    kind.check_id for kind in CARD_KINDS if kind.lane == "important"
)
IDENTITY_BY_CHECK: dict[CheckId, IdentityDeclaration] = {
    kind.check_id: kind.identity for kind in CARD_KINDS
}
DOCS_FAILURE_COPY: dict[tuple[str, str], str] = {
    (copy.source_id, copy.status): copy.text
    for copy in CHECKS_BY_ID["docs"].copy.source_status
}


def check_kind(check: CheckId) -> CardKind:
    """Return the frozen declaration for a registered check."""

    return CHECKS_BY_ID[check]


def shape_of(prop: Prop) -> PropShape:
    """The logical shape of a proposition's predicate. Raises on an unregistered predicate."""

    try:
        return PREDICATE_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(f"unregistered predicate: {prop.predicate!r}") from exc


def witnesses(claim: Prop, query: Prop) -> Witness:
    """Does a card's ``claim`` witness ``query`` (supports), its negation (refutes), or
    neither (unrelated)? Deterministic over typed structure only.

    A registered ``(claim.predicate, query.predicate)`` refutes-pair, satisfied under that pair's
    match rule (subject-overlap or repo-wide), refutes the (universal) query. ``supports`` is
    reserved for kinds whose claim establishes a query directly.
    """

    match = _REFUTES_MATCH.get((claim.predicate, query.predicate))
    if match is None:
        return "unrelated"
    return witnesses_with(claim, query, match)


def deps_for(prop: Prop) -> frozenset[str]:
    """The mandated source families whose state can affect ``prop`` (deps_G)."""

    try:
        return DEPS_REGISTRY[prop.predicate]
    except KeyError as exc:
        raise ValueError(
            f"no dependency closure registered for predicate {prop.predicate!r}"
        ) from exc


def severity_base_for(predicate: str) -> float:
    """The cost-of-not-knowing base for a card predicate. Raises on an unregistered predicate."""

    try:
        return KIND_BASE[predicate]
    except KeyError as exc:
        raise ValueError(f"no severity base registered for predicate {predicate!r}") from exc
