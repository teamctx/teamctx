# Team-emulation validation: live run summary (2026-07-04)

Program: `docs/superpowers/specs/2026-07-03-phase5-emulation-program.md` (revision 2).
Operator: the CTO, per the program's safety rail (builders never touch live systems).
Goal sentence being certified: *"test it like a team of people + agents that works with
Jira, Confluence, GitHub, and GitLab, and make sure it all works as expected."*

## Verdict: PASS, with two named residuals (below), zero silent ones.

Two layers of evidence back this:
1. **The offline matrix: 12 of 12 rows PASS** through the real CLI, hook, and MCP against
   bundled mock transports (`emulation/`, runnable by anyone:
   `python emulation/runner.py --offline --all`). Expected blocks quote the real renderer,
   per-span byte-exact or templated.
2. **The live pass in this directory**: real multi-actor scenarios on real infrastructure:
   a private GitHub lab repo, a private GitLab lab project, and the operator-authorized Jira
   project and Confluence space on a staging Atlassian instance (redacted here per the
   program's map: instance -> ATLASSIAN.example, project -> PROJ, space -> SPACE, ids ->
   {id}; the disposable lab repo slugs are committed as-is).

## What the live pass proved, row by row
- **01 GitHub collision**: actor B warned about actor A's real open PR with the exact
  `gh pr view` hint; actor A saw the own-PR FYI instead of a self-alarm; the deliberately
  slow CI job was mid-run, so the live PENDING gate state was captured too.
- **02 GitLab collision**: the same pair through a real MR, MR-worded; the own-MR FYI live.
- **03 GitHub gate**: a real failing Actions check named; ZERO check-runs reads clear (the
  documented GitHub half of the gate asymmetry); no-token reads can't-verify with the fix.
- **04 GitLab gate**: running -> pending; canceled -> its unfinished jobs surfaced as
  not-passing, never clear; failed -> the job named; TRUE zero-pipelines -> "no pipeline
  ran for this branch, so the gate is unverified" (the GitLab half of the asymmetry);
  SKIPPED pipeline -> the connector's honest "could not be confirmed green" (this exact
  scenario found a real copy bug during the run; it was fixed, adversarially reviewed, and
  re-captured before this summary: see "Findings the run produced").
- **05 GitHub criteria**: an issue edited after work started fired; the unchanged control
  read clear WITH the derivation provenance ("issue #3 from your branch name").
- **06 Jira criteria**: a real PROJ issue created, edited after the work anchor, fired with
  field-level detail ("description updated") off the real changelog; artifact closed after.
- **07 Local docs**: a superseded doc fired on an edit to an UNRELATED file (relied-on
  semantics), naming its replacement.
- **08 Confluence docs**: a real page pair in SPACE; the `teamctx.superseded_by` property
  fired beside the local doc and the Jira change (three sources in one honest report), and
  `open-source` printed the real, openable page URL. Artifacts deleted after.
- **09 Onboard/status truth**: a fresh actor onboarded with one command; every onboard step
  and every `status` line was true against reality, including the exact open-PR count.
- **10 Transports agree**: CLI and MCP byte-identical on a live collision; the hook said
  less by design and nothing it said disagreed.
- **11 Replay**: two live runs with the same `observed_at` seconds apart produced identical
  digests and identical verdicts.
- **12 Unbounded at scale**: test-verified (fabricated 301-PR payload through the REAL
  pipeline via the API-root seam): "Checked the 300 most recently updated open PRs; more
  exist", never a clear; the hook carried its own reflex-budget figure honestly.

## Findings the run produced (the run was itself a test of the honesty bar)
- **A real copy bug found live and fixed** (merged `1f1652e` after a two-round adversarial
  review that also caught the same class in the hook): GitLab's `ci.skip` creates a SKIPPED
  pipeline rather than none, and a skipped (reached, not-green) pipeline rendered as
  "couldn't reach GitLab". Reached-but-unconfirmable sources now carry the connector's
  message on every surface. The live re-capture is in row04.
- **Cosmetic, on the polish list**: the new stale-note bullet join can drop a period
  ("...confirmed green If a green build matters..."); an unpushed branch's gate reads
  "couldn't reach GitHub" where "this branch isn't on GitHub yet" would be kinder.

## Named residuals (never silent)
- **Live-unbounded**: no real 300+-open-PR repo in the lab; the at-scale behavior is
  test-verified through the real pipeline (row 12), not live-verified.
- **Real rate limiting**: unit-verified only (no seam can stage it live safely).

## Lab lifecycle
Lab repos (`tempo-64/teamctx-emulation-lab`, `tempo64/teamctx-emulation-lab`) remain for
re-runs and are disposable; Atlassian artifacts were closed (PROJ) or deleted (SPACE pages)
during the run.
