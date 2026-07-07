# Design: the check catalog spine (issue #10)

## Status
Revision 1, CTO-drafted from the design session with Edgar 2026-07-07. Two CPO laws locked
in that session govern everything below. Under adversarial review (codex, multiple rounds)
before any implementation plan. The build does not start until this is rock solid.

## The two laws (locked, not revisitable in review)
1. **Trust by design.** Secure, private, content-safe by construction: vulnerability
   classes must be structurally absent, not guarded. No code-loading path exists. Check
   logic can never see credentials. Metadata-only is enforced at the one connector boundary.
2. **Team-level everything.** All verification semantics (which checks, their options,
   their lanes) live in the committed `.teamctx/config.json`: one reality per team, 2 or 50
   people, humans and agents alike. Only credentials and the personal choice to install the
   hook remain individual: the surface, never the semantics.

## 1. The check contract
A check is one frozen declaration:
- `id` (stable string), `contract_version` (integer, starts at 1).
- `claim`: proposition text + refutes-match rule (the kinds registry shape today).
- `consumes`: the document types it reads.
- `derive`: a PURE function, documents in, findings out. No network, no credentials, no
  filesystem, no clock reads. Enforced by the purity conformance test (the same pattern
  that guards core/ today), not by convention.
- `closure`: the propositions this check answers, declared up front, so
  checked / not-checked / couldn't-check / not-applicable / profile-skipped is defined at
  declaration time and the honesty closure is derivable without running anything.
- `copy`: the complete string table this check can ever speak, including coverage-note
  strings keyed by (source_id, status) (the render's current keying; migration task zero
  inventories every existing string so nothing is lost in the move).
- `profile`: reflex or full (what the ambient hook may run vs the full work-start).
- `lane`: important or FYI (default; team config may override). The silence law's
  important-set is derived from the enabled important-lane checks.
- `config_schema`: the options the check accepts, schema-validated with plain errors.

Adding a check touches ONE declaration site. A conformance suite (purity, closure
completeness, copy law incl. the em-dash grep, determinism, one mutation test per claim
input) must pass before a check can register. The suite runs in CI over every registered
check, ours or declared.

## 2. Two registries: sources and checks (N:M)
Connectors produce typed documents; they are the ONLY credentialed, I/O-capable layer;
they remain in-core and reviewed. Checks consume documents. The runner resolves the
document set needed by the ENABLED checks for the current profile, fetches each document
once, then derives. The Jira changelog document feeds both criteria and (later)
issue-lifecycle without a second fetch. Profile handling: a document needed only by
full-profile checks is not fetched in reflex; those checks close as profile-skipped (an
honest, distinct closure state, generalizing today's Confluence-skip note).

## 3. Team-level selection (law 2 applied)
`.teamctx/config.json` gains:
```json
"checks": {
  "collision": {"enabled": true},
  "stale_base": {"enabled": true},
  "deprecations": {"enabled": true, "lane": "important", "options": {...}}
}
```
- Absent block = the default set (backward compatible).
- Default-on requires: zero configuration AND field-proven. Today that grandfathers the
  four; new checks earn it. Everything needing declaration is opt-in by nature.
- Onboard detects repo shape (CODEOWNERS, package.json, a flags SDK) and SUGGESTS relevant
  opt-ins in its output; it never enables them itself.
- **Version skew rule**: a config that enables a check this teamctx version does not have
  produces a LOUD not-checked line ("the team config expects check X; this teamctx does
  not provide it; upgrade") in every answer and a status failure. Never silence: silence
  here would mean two teammates on different versions silently live different realities,
  which breaks law 2.

## 4. Declared sources and declared checks (extensibility as data)
No code-loading path exists. Two config-declared, schema-validated objects:

**Declared source** (consumed by ONE generic connector, in-core):
- `kind`: `file` (in-repo path) or `url`.
- `schema_map`: named fields plucked from the record (JSON pointer per field). ONLY mapped
  fields cross the boundary; everything else is dropped unread. Per-field length caps;
  control characters stripped; parse depth and response size capped (structurally bounded
  untrusted input).
- `credential_env`: optional; MUST match `TEAMCTX_SRC_[A-Z0-9_]+`. First-party credential
  names (GITHUB_TOKEN, GITLAB_TOKEN, ATLASSIAN_*, and any non-TEAMCTX_SRC name) are
  structurally refused at config validation. This kills credential redirection: a config
  cannot point an existing token at a new host.
- **Consent-by-credential**: a `url` source fetches ONLY if its named env var exists in
  the person's environment. A committed config alone can never make anyone's machine
  contact a host. No env var, no fetch: the source closes as "not enabled on this
  machine" (visible, honest, with the env name to set). `file` sources (in-repo, no
  network) need no consent gate.
- An unreachable/oversized/malformed declared source closes as couldn't-check with the
  reason. Never a clear.

**Declared check** (data, not code):
- `claim` text, `match`: a bounded rule over declared-source fields (equality, presence,
  prefix, and threshold comparators; total function). **Missing-field semantics pinned:**
  a match rule referencing a field absent from a record closes couldn't-fully-check,
  never clear, never silently skipped.
- `copy`: the strings it speaks. Rendered fields are quoted data with length caps applied
  at the source boundary (content-safety: a hostile record cannot speak in teamctx's
  voice beyond its capped, quoted field slots; this is the prompt-injection surface and
  it is bounded by construction).
- Runs through the same conformance suite at config load; failures are plain-language
  config errors, not runtime surprises.

What data cannot express (import graphs, cross-repo diffing) stays in-core, ours, built
through the review loop. If a real community someday needs code plugins, that is its own
future design under law 1; the pure-derivation contract means even then plugins would be
credential-blind.

## 5. Honesty at scale (the data half; the voice belongs to #11)
The closure covers ENABLED checks, itemized exactly as today. Checks that exist but are
not enabled appear as one summary line (team-declared coverage, spoken as such), never
item-by-item confession, never silence. Disabled-by-team, not-applicable, profile-skipped,
and couldn't-check are four different truths and read differently. The important-set for
the ambient silence law = enabled important-lane checks; a config edit already invalidates
ambient baselines via the config-hash in the key (verified behavior today), so enabling a
check re-grounds every session correctly for free.

## 6. Migration and compatibility
- The four checks re-declare onto the contract with byte-identical output: the 16-row
  emulation matrix and the full test suite run unchanged as the regression oracle. Any
  expectation change in the matrix is a defect in the spine, not a row to update.
- CLI, MCP, hook, render surfaces: unchanged.
- kinds.py evolves into the contract module; the pin-the-registry tests move with it.
- Config without a `checks` block behaves exactly as today (the default set).

## Out of scope (deliberate)
Code plugins (future design, law 1 applies); personal overrides (law 2 forbids);
the coverage-summary VOICE and severity presentation (#11, designed against this spine);
any new check beyond re-declaring the existing four (those are their own roadmap issues).

## Pre-hardening record (attacks the CTO ran before review)
1. Credential redirection via declared source -> TEAMCTX_SRC_ namespace + structural
   refusal of first-party names.
2. Committed config as remote-fetch trigger on fresh clones -> consent-by-credential.
3. Copy-table expressiveness vs today's (source_id, status)-keyed notes -> migration task
   zero inventories all strings; contract supports the keying.
4. Shared-document profile skew -> profile-skipped closure state.
5. Version skew across a team -> loud unknown-check rule (law 2).
6. Declared-match missing fields -> couldn't-fully-check, never clear.
7. Hostile record content (size, depth, control chars, injection into agent context) ->
   caps + stripping + quoted-slot rendering at the boundary.
