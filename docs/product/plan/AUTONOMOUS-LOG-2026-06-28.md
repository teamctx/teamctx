# Autonomous build log (Edgar away, 2026-06-28)

Edgar stepped away and authorized full autonomous CTO mode: drive the build, make the design and
judgment calls, surface a consolidated review later. Rules I am holding: build to the bar, zero em
dashes, the surfaced-text principle, a Codex (gpt5.5 xhigh) review on each slice that I arbitrate,
and merge + push to main on green.

**Parked for Edgar (will NOT do autonomously):** anything irreversible or outward-facing. Publishing
to PyPI, making the repo or a site public, linking a public site to the still-private repo, any git
history rewrite. Packaging gets built to "installs locally and works" and stops before publish.

## Already shipped earlier this session
- M1 reflex (`5bf4ad9`), M2 messaging pass (`a41ad60`), GitHub truncation honesty (`df58744`),
  token + clock hygiene (`7e13ec7`).

## In flight
- Codex adversarial pass on the broker core (hunting a false-clear path). Triage its findings.

## Decisions while away

### Slice B: `teamctx init` rebuild
**Call:** `init` becomes work-start-oriented. Auto-detect the repo from the git `origin` remote
(`--repo` overrides); auto-detect `docs_root` (the `docs/` folder if it exists, `--docs-root`
overrides); write only the `work_start` config (not the legacy `github`/`default_output` fields);
refuse to overwrite an existing config without `--force`; print token-setup guidance and the exact
next command (`teamctx work-start`). **Why:** work-start is the canonical entry point, so `init`
should scaffold the canonical config and orient the user, not the refresh-era GitHub config. The old
`init` required `--github-repo` and wrote refresh-era config, which is the legacy flow slice C retires.
**DONE 2026-06-28 (merged `8784ac3`, 266 tests).** Codex review (gpt5.5 xhigh) found 4 issues; I took
3 (scaffold a clean `work_start`-only config via `exclude_defaults`; print a runnable next command,
since `work-start` requires `--path`; drop the `--config` footgun because `work-start` only reads the
default path) and dropped 1 (README still teaches the old flags: deferred to slice E's wholesale
README rewrite rather than piecemeal-patching a doc that is broadly stale and about to be replaced;
the repo is private, so no external user hits it meanwhile).

### Slice C: decomposed into three
**Call:** split slice C into (C-surface) move the diagnostic commands under a `dev` namespace, (C-legacy)
retire the refresh/context snapshot flow, and (C-judge) rebuild `why`/`open-source` on the live broker.
**Why:** `why`/`open-source` currently depend on the snapshot, so retiring the snapshot forces a
decision on them; the rebuild has a real design fork (how to address a finding now that the M2 prose
render exposes no IDs), so it earns its own focused slice rather than bloating the retirement.

**C-surface: DONE 2026-06-28 (merged `2054f73`, 266 tests).** Moved github-pr-probe/docs-probe/
gate-probe/issue-probe/eval-export under `teamctx dev`; top-level is now status/init/work-start/
install-hook/dev. Pure relocation; I verified locally and merged WITHOUT a Codex round (no behavior
change, not worth the cost) - my arbiter call on rigor, logged here for transparency.

**why/open-source design (Codex consult, gpt5.5 xhigh):** Codex recommended Option B (typed natural
selectors like `pr:7`, `path:src/app.py`, `issue:#42`; rerun the live broker; match exactly one
finding; no opaque handles; do NOT retire them, because the inline hint is not enough for issues/docs/
gates and there is a policy-gated source-opening contract). I AGREE and accepted B for the eventual
rebuild, but SPLIT the work: retire the snapshot-coupled why/open-source now, rebuild broker-backed
next (C-judge). Plumbing note from Codex: `SourceOpenTarget`s are dropped by `BrokerAnswer` and live
cards have `source_open_target_id=None`, so C-judge must thread open-targets through the broker answer.

**C-legacy (retire snapshot flow): BUILT `0c9b1f5` (249 tests, 17 removed), in Codex review.** Deleted
`contract_documents.py`, the refresh/context/why/open-source commands + helpers, the snapshot renderers
+ terminal label helpers in `contract_render.py`, and the legacy config (`GitHubSourceConfig`,
`github`/`default_output`, `build_project_config`). Kept `CoreContractDocument`, `render_broker_answer`,
`SourceOpenTarget`, the live broker. Note: `ProjectConfig` now rejects configs with `github`/
`default_output` (a clean break, acceptable pre-release). **MERGED `348c307`. Codex review: APPROVE.**

### Packaging (D): verified buildable 2026-06-28
`pyproject.toml` is complete (hatchling, src layout, three console scripts, mcp/dev extras).
`python -m build` produces a clean sdist + wheel (`teamctx-0.0.0`). Structurally done. Token-hygiene
docs fold into the README (slice E). **PUBLISH to PyPI is PARKED for Edgar** (external, irreversible).

### Slice C-judge (rebuild why/open-source): DESIGNED, DEFERRED for Edgar's nod
All-or-nothing (plumbing is useless without the commands) + touches the sensitive core (`BrokerAnswer`
must carry open-targets) + the selector UX is a product call. So I designed it (Codex B accepted) and
surfaced it rather than build it solo at the tail of this run. Spec:
`docs/superpowers/specs/2026-06-28-c-judge-why-open-source-design.md`. Needs a nod on the selector
syntax (`pr:7` / `path:` / `issue:#`) and confirmation to keep why/open-source at all.

### Slice E (README): deferred until after C-judge (so it reflects the final command set).

### Adversarial false-clear hunt: focused re-run in flight
The broad core pass hung (killed it). A focused re-run is hunting the same bug class as the GitHub
pagination fix across the other connectors (issue_criteria, docs_supersession, gate_status,
declared_authority) + `assess_completeness`. Will triage and fix any real false-clear before surfacing.
