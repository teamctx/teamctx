# Spec: Phase 5 team-emulation validation program

## Status
Revision 1, proposed by the CTO 2026-07-03; adversarial review before execution. Goal source:
Edgar, 2026-07-03: "test it like a team of people + agents that works with Jira, Confluence,
GitHub, and GitLab, and make sure it all works as expected." Runs after Phase 4 merges.

## What is being proven
Not that the code passes tests (CI proves that), but that a REAL multi-actor team flow
produces the surfacing the product promises, live, on all four sources: the right findings
fire across actors, the honest-UNKNOWN degradations say the true thing, and nothing reads
clear that was not checked. Every scenario records expected vs actual as durable evidence;
this corpus then seeds the Phase 3 conformance numbers.

## Actors (emulated; no recruiting)
- **Actor A "author"**: a human-like dev in a terminal; own clone, own branches; opens
  PRs/MRs; edits files directly.
- **Actor B "agent dev"**: an agentic dev; own clone with the hook installed and the CLAUDE.md
  snippet; for scenarios where an agent's USE of the signal matters, a live Opus subagent
  works in the clone; for deterministic hook checks, `teamctx-hook` is driven with synthetic
  PreToolUse events (faithful: that is exactly what Claude Code sends).
- **Actor C "reviewer/PM"**: changes the record: edits issues (GitHub + Jira), supersedes
  docs (local frontmatter + Confluence property), merges/closes PRs.
Actors share credentials (one operator) but are distinguished by clone, branch, and author
identity, which is what the product actually keys on.

## Lab assets
- **GitHub**: a NEW private repo (clearly named, e.g. `teamctx-emulation-lab`), created for
  the program and deleted or archived after; a trivial Actions workflow whose pass/fail is
  controlled by a file in the repo (gate scenarios).
- **GitLab**: a NEW private project under the operator account, same shape, with a controllable
  pipeline.
- **Jira + Confluence**: a project key + space key ON THE OPERATOR-PROVIDED instance where
  test artifacts are explicitly permitted (**the standing Edgar ask; blocks only the
  Jira/Confluence WRITE scenarios**). All artifacts clearly titled as teamctx test items.
- Committed evidence is SANITIZED: no instance hostnames, no real project/space keys, no
  captured payloads; raw logs stay local.

## Scenario matrix (each row: setup -> action -> expected surfacing -> capture)
Per check, per provider, plus the degradations:

1. **Collision, GitHub**: A opens PR touching `src/x.py`; B work-starts on `src/x.py` ->
   heads-up names the PR with the gh hint. B's OWN PR on B's branch -> FYI line, clear
   verdict, "no other open PRs" phrasing.
2. **Collision, GitLab**: same pair through MRs; display says `GitLab MR !N`; open-source
   shows the web URL, no `gh` hint.
3. **Gate, GitHub**: failing check on B's branch -> firing with the check named; pending run
   -> "still running, not confirmed green"; token removed -> can't-verify with the fix line.
4. **Gate, GitLab (the P0 scenarios)**: failed pipeline WITH a failed job -> named gate;
   **canceled pipeline with zero failed jobs -> synthetic `pipeline canceled` gate, never
   clear**; running -> pending; no pipeline on the ref -> the disabled "no pipeline ran"
   note, never clear.
5. **Criteria, GitHub**: B branches `42-fix-auth` off main; C edits issue #42's body ->
   criteria fires with detail; clear line carries "(issue #42 from your branch name)";
   trailer-derived issue via commit message; explicit `--issue` suppresses derivation.
6. **Criteria, Jira**: B branches `PROJ-123-fix`; C edits the Jira issue description ->
   fires with field-level detail; `PROJ-123` with Jira UNCONFIGURED -> the honest disabled
   note and NO clear off the GitHub side (the mixed-family scenario); `#N` + `KEY-N` both
   derived and both checked.
7. **Docs, local**: C adds `superseded_by` frontmatter to a doc under docs_root; B
   work-starts on an UNRELATED source file -> the doc fires (relied-on semantics); clean
   docs tree -> the real green.
8. **Docs, Confluence**: C sets the `teamctx.superseded_by` property on a page in the
   configured space -> fires with the page URL openable; space-key typo -> unavailable,
   never a clean scan; hook (reflex profile) -> the "skipped in the quick pre-edit check"
   note.
9. **Onboard/status truth**: a fresh actor onboards from the README alone (the Sprint 2
   bar); after every scenario stage, `teamctx status` is captured and every line checked
   true.
10. **Transports agree**: one scenario consumed via CLI, MCP tool, and hook signal in the
    same state; the hook says less but nothing it says disagrees.
11. **Replay**: for one composed scenario, the same inputs replayed give the same digest and
    identical output.

Degradations impractical to stage live (rate limiting, 100+ open-PR truncation) are covered
by the unit suites and RECORDED in the evidence as test-verified, stated plainly, never
claimed as live-verified.

## Orchestration and evidence
A driver script per scenario family under a NEW top-level `emulation/` directory in the lab
repo world (NOT in the teamctx package; it is test harness, not product): sets up the state
through the real provider APIs, invokes the real CLI/hook/MCP, captures output, and diffs
against the expected block. Expected blocks state exact strings for stable copy and
structured expectations (verdict, check statuses) elsewhere. Results land in
`docs/validation/team-emulation-<date>/` in teamctx: one markdown per scenario with
setup, expected, actual, PASS/FAIL, and notes; plus a summary table. A FAIL stops the
program until fixed and re-run (fix-loop discipline; findings become slices like everything
else).

## Exit bar (the goal's "make sure it all works as expected")
Every scenario row PASS on live GitHub + GitLab; Jira + Confluence rows PASS live once the
write-scope keys exist (until then their READ paths are validated against the live instance
and write flows against synthetic state, recorded as exactly that); the evidence summary is
committed; CURRENT.md updated. Residuals (if any) are listed with reasons, never silently
dropped.
