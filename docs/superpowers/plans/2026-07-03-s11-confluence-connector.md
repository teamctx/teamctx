# S11: Confluence Docs Connector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Confluence becomes the first remote docs source: any page in the configured space carrying the `teamctx.superseded_by` content property fires a "Verify before relying" card with an openable URL, with every coverage-honesty pin from the review-hardened spec (a typo'd space, a failed property fetch, or a budget hit can never read as a clean scan).

**Architecture:** BINDING design: `docs/superpowers/specs/2026-07-03-source-breadth.md` REVISION 2 section 4 (P1-1 repo threading, P1-2 space-resolution/property-failure/pagination pins, P2-3 openability) and section 1's reflex-profile skip. Plan pins:
- New `src/teamctx/connectors/confluence.py`: `run_confluence_docs_probe(base_url, space_key, auth, request_context, observed_at, opener)`. Endpoints (recon-verified v2): space id via `GET {base}/wiki/api/v2/spaces?keys={key}` (zero results -> `unavailable`, spec copy below); pages via `GET {base}/wiki/api/v2/spaces/{id}/pages?limit=100&status=current` following the v2 cursor from `_links.next` up to the 500-page budget (malformed/absent cursor with more pages indicated -> `stale`); per page `GET {base}/wiki/api/v2/pages/{page_id}/properties?key=teamctx.superseded_by` (ANY property fetch failure -> the whole source `stale`; skip-and-continue is banned). Archived pages excluded by `status=current`.
- A property-carrying page yields `SupersededDoc(repo=request_context.repo, doc=<page title>, superseded_by=<property value>, url=<base + _links.webui>)` (P1-1 threading is the law; a broker-level test proves the card fires). `SupersededDoc` gains `url: str | None = None`; `normalize_superseded_docs` carries it into scope; `render_open_source`'s doc branch prints the URL when present.
- Source id `confluence_pages` (distinct family entry beside local `docs_supersession`); the two docs sources compose under the closure's worst-status rule (test: local fresh + confluence stale -> docs never complete-green; both fresh -> complete).
- **Runner dispatch:** `confluence` config present + `profile == "full"` -> the probe (auth via `resolve_atlassian_auth`; missing/half credential -> `unavailable` with the pinned copy); `profile == "reflex"` -> the `disabled` skip status with the breadth spec's verbatim note (`Confluence docs are skipped in the quick pre-edit check; run teamctx work-start for the full scan.`).
- **Copy (verbatim, CTO-owned):** space-not-found: `the configured Confluence space couldn't be found with current access.` · no-credential: `Confluence is configured but no Atlassian credential was found. Set ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN (or ATLASSIAN_API_TOKEN_FILE).` · half-credential: `Confluence is configured but only half the Atlassian credential is set; both ATLASSIAN_EMAIL and ATLASSIAN_API_TOKEN are needed.` · unreachable: `Confluence is unavailable with current access.` · budget: `Checked the first 500 pages of the space; more exist, so this is not a complete check.` · property-failure: `A page's supersession marker couldn't be read; the docs scan is not complete.`
- Docs check render copy stays shared (the docs family wording is source-neutral); the superseded card copy already names the replacement.

**Branch:** worktree `git worktree add ../teamctx-s11 -b feat/confluence-connector main`. Another builder is active in ../teamctx-p5c; never touch it or the main worktree. Gates as SEPARATE commands with real exit codes; final task adds coverage >= 90. NO live network calls; injected openers only.

### Task order (TDD per task, commit per task)
1. `SupersededDoc.url` + scope + open-source URL line (local docs unaffected: url stays None).
   Commit: `feat(docs): superseded docs carry an openable url`
2. `connectors/confluence.py` fetchers + every fail-closed pin, test-per-pin (space-not-found,
   cursor-malformed, property-failure, budget, malformed payloads, auth variants). Commit:
   `feat(confluence): space-scoped supersession scan, fail closed everywhere`
3. Runner dispatch (full/reflex/credential paths) + the two-docs-sources composition tests.
   Commit: `feat(runner): confluence docs beside local docs in one honest family`
4. e2e (fake opener: property-carrying page fires with page title + webui URL in open-source;
   clean space reads the real green beside local docs; reflex skip note) + CHANGELOG (Added):
   `- Confluence support: pages in a configured space that carry the teamctx.superseded_by property fire the docs check with an openable link, beside local docs in one honest coverage picture.`
   Commit: `test(confluence): end-to-end supersession; changelog`

## Completion
Stop after the last commit. Do NOT merge, push, or remove the worktree. Report: branch,
commits, gate exit codes, files changed, deviations. On plan-vs-code contradiction, stop
and record.
