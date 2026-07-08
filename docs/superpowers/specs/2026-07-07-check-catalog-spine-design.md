# Design: the check catalog spine (issue #10)

## Status
**Revision 5: ROCK-SOLID (CTO verdict, 2026-07-08).** Four adversarial rounds (codex 1, 2,
4; Opus fresh-eyes 3), every finding accepted and pinned, dispositions below. Round 4 found
no P0 and no architectural challenge: one classification gap (authority.json, folded) and
wording. The architecture has been unchallenged since round 2. Awaiting Edgar's sign-off,
then writing-plans. Two CPO laws locked 2026-07-07.

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
  `profile_skipped` becomes FIRST-CLASS contract vocabulary (today's Confluence reflex skip
  is encoded as disabled; it recodes to profile_skipped while PRESERVING today's rendered
  strings: vocabulary changes, bytes do not).
- `copy`: the complete string table this check can ever speak. Round 1 proved check copy
  alone cannot express today's output, so the table has four parts (migration task zero
  inventories every existing string into them): finding copy (incl. coverage-note strings
  keyed by (source_id, status)), ADVISORY copy (FYI-lane strings born from source statuses,
  e.g. the own-PR note), PROVENANCE hooks (strings interpolating request derivation, e.g.
  "issue #42 from your branch name"), and DELTA templates per direction (the since-you-
  started voice, today hardcoded in ambient/render, becomes per-check declaration).
- `identity`: the fields that name a finding across runs (PR number + paths, gate name,
  issue ref, doc name): the delta engine's material extraction, declared per check.
  **Conformance proves the wiring (round-2 P1-7):** every check runs through
  compute_baseline_material and a delta round-trip; declared identity fields must exist in
  rendered card scope and produce stable keys, so a declaration/name mismatch cannot break
  delta silence while CLI output looks fine.
- `profile`: reflex or full (what the ambient hook may run vs the full work-start).
- `lane`: important or FYI (default; team config may override). The silence law's
  important-set is derived from the enabled important-lane checks.
- `config_schema`: the options the check accepts, schema-validated with plain errors.

**The declared check carries the SAME contract (round-3 P1-2):** a declared check states
`consumes` (a declared-source id), `identity` (which mapped fields name a finding),
`lane`, and `profile` explicitly; there are no invented defaults. A data-only declaration
satisfies the identity round-trip because its identity fields are mapped record fields,
which appear in rendered card scope by construction; conformance proves it like any check.

Adding a check touches ONE declaration site. A conformance suite (purity, closure
completeness, copy law incl. the em-dash grep, determinism, one mutation test per claim
input) must pass before a check can register. The suite runs in CI over every registered
check, ours or declared.

## 2. Two registries: sources and checks (N:M)
Connectors produce typed documents; they are the ONLY credentialed, I/O-capable layer;
they remain in-core and reviewed. Checks consume documents. The runner resolves the
document set needed by the ENABLED checks for the current profile, fetches each document
once, then derives. Profile handling: a document needed only by full-profile checks is not
fetched in reflex; those checks close as profile_skipped.

**Ownership, pinned (round-1 P1-6, sharpened round-2 P1-6):** fetch status belongs to the
SOURCE/document; verifiedness belongs to each CHECK. Documents gain STABLE ids (uniqueness
validated, consumed ids sorted); closure entries become (check_id, proposition,
consumed_document_ids, closure_status, reason). One failed Jira fetch closes BOTH criteria
and issue-lifecycle as couldn't-check, each with its own copy, off one status. Digest
impact, corrected (round-3 P1-4; an earlier revision left a contradictory sentence here and
a builder rightly stopped on it): closure does NOT feed the replay/snapshot digest (it
hashes request, signals, statuses, declarations) and slice 2 leaves that digest untouched,
with a test proving it. The digest closure feeds is the AMBIENT content digest, which takes
closure (proposition, status) ONLY: reasons and consumed_document_ids stay out (landed in
slice 1 with the ambient state schema bump). Rendered bytes for unchanged worlds stay
identical: the oracle checks bytes, not digests. This is the largest single piece of the
build (build risk #1).

**Advisory ownership (round-2 P2-9, better factoring):** advisory/FYI notes are born from
source statuses, so the SOURCE/document contract owns advisory note keys and payloads;
checks declare only whether and where those advisories surface. The check copy table
correspondingly holds finding copy, provenance hooks, and delta templates; advisory strings
live with the source contract.

## 3. Team-level selection (law 2 applied)
`.teamctx/config.json` gains:
```json
"checks": {
  "conflict": {"enabled": true},
  "docs": {"enabled": false},
  "x_deprecations": {"enabled": true, "lane": "important", "consumes": "x_registry"}
}
```
- Absent block = the default set (backward compatible). (The example uses v1-real ids:
  a spec example must not be a config its own skew rule rejects; round-3 P2-3.)
- Default-on requires: zero configuration AND field-proven. Today that grandfathers the
  four; new checks earn it. Everything needing declaration is opt-in by nature.
- Onboard detects repo shape (CODEOWNERS, package.json, a flags SDK) and SUGGESTS relevant
  opt-ins in its output; it never enables them itself.
- **Version skew rules (round-1 P1-4, generalized; hook mechanism pinned by round-3
  P0-1):** unknown ANYTHING in the checks block (check id, option, lane value,
  declared-source field) is a LOUD, plain-language config failure; older clients never run
  with partial or defaulted semantics. Config may declare `requires_teamctx` (minimum
  version, same loud failure). On the HOOK this cannot rely on exceptions: today the whole
  run sits inside a fail-safe that eats everything, so a config error would silence the
  flagship surface exactly when the team's config outgrew the local binary. Pin: the hook
  catches config-validation failure EXPLICITLY, inside the fail-safe, and emits the loud
  line as context ("your teamctx is behind this repo's team config; upgrade to run the
  team's checks"); an emulation row proves the hook SPEAKS on unknown-check rather than
  going silent. The fail-safe continues to eat only UNEXPECTED errors.
- **Request context vs team semantics, classified (round-1 P1-5):** paths, branch, linked
  issue, and since are REQUEST CONTEXT (vary per invocation by nature). Repo, docs roots,
  declared sources, enabled checks, lanes, and options are TEAM SEMANTICS: committed config
  only on all normal surfaces. The CLI's --github-repo/--docs-root style flags are
  reclassified as diagnostic overrides. **The migration, named exactly (round-2 P1-5):**
  the MCP tool schema DROPS repo/docs_root parameters (breaking change, pre-1.0,
  CHANGELOG'd); normal work-start keeps the flags but documents them as diagnostic; probe
  commands keep them as-is; the emulation rows and tests that pass overrides migrate to
  committed-config fixtures so the oracle exercises the real path. TEAMCTX_AMBIENT_INTERVAL_SECONDS and
  TEAMCTX_AMBIENT_STATE are DELIVERY-SURFACE knobs (when to speak, where state lives): they
  can never change what is verified or how it is judged.

## 4. Declared sources and declared checks (extensibility as data)
No code-loading path exists. Two config-declared, schema-validated objects:

**Declared source** (consumed by ONE generic connector, in-core):
- `kind`: `file` (in-repo path) or `url`.
- `schema_map`: named fields plucked from the record (JSON pointer per field). ONLY mapped
  fields cross the boundary; everything else is dropped unread. Per-field length caps;
  control characters stripped; parse depth and response size capped; duplicate object keys
  REJECTED in both config and fetched records (one canonical strict parser; round-1 P2-10).
- `consent_env`: REQUIRED for every `url` source, no exceptions, public URLs included
  (round-1 P0-1). MUST match `TEAMCTX_SRC_[A-Z0-9_]+`; serves as the credential when the
  endpoint needs one and as pure consent when it does not. First-party credential names and
  any non-TEAMCTX_SRC name are structurally refused at config validation (kills credential
  redirection). No env var on this machine, no socket, ever: the source closes as "not
  enabled on this machine" with the env name to set.
- **URL sources are DEFERRED to v1.1 (round-2 scope decision):** v1 ships file sources
  only; the extensibility contract gets proven with the smaller security surface, and org
  registries reach v1 by committing an exported record file to the repo. The SSRF policy
  below is the pinned v1.1 design, not v1 build scope.
- **SSRF policy, pinned (round-1 P0-2 + round-2 P0-1):** `https` scheme only; no userinfo;
  port 443 only; every resolved A/AAAA address must be outside loopback, private,
  link-local, and cloud-metadata ranges, and the connection is made TO THE CHECKED IP
  (hostname preserved for SNI, Host, and certificate verification), closing the DNS
  rebinding window between check and connect; redirects are NOT followed (a redirect closes
  couldn't-check with the reason). `file://` and every other scheme are refused at
  validation.
- **consent_env semantics, exact (round-2 P1-3):** key PRESENCE is consent; when the
  endpoint needs a credential, a NON-EMPTY value is required and an empty value closes as
  not-enabled with the reason; the value is never rendered, stored, or digested: only the
  env var NAME ever appears in output or state.
- **File-source safety, pinned (round-1 P0-3):** `file` paths must be relative, resolve
  inside the project root with symlink escapes rejected (the docs connector's existing
  hardening pattern), not under `.git`, regular files, size-capped, and TRACKED BY GIT
  (tracked means the content went through the team's review: law 2 applied to data).
- **The config itself obeys law 2, via COMMITTED-BLOB READS (round-2 P1-4, mechanism
  replaced by round-3 P0-2):** on normal surfaces (hook, MCP, work-start), ALL team
  semantics (work_start block, checks block, declared objects) are read from the COMMITTED
  version of `.teamctx/config.json` (the HEAD blob), not the working tree. A dirty working
  tree changes nothing until committed, and the output says so once ("config changes in
  your working tree take effect when committed"). This yields exactly one reality (the
  reviewed one), preserves team disables (nothing falls back to defaults), and closes the
  whole-file-cleanliness gap (round-3 P2-1) with one rule. Never-committed config: the
  file as written is the ONLY version, and since no team semantics were ever reviewed,
  the default four run with a loud line ("commit .teamctx/config.json to activate the
  team's configuration"). NO-GIT trees (exports, build contexts, sandboxes): tracking is
  unverifiable, so same as never-committed: default four plus the loud reason (round-3
  P0-2). Iteration surface (round-3 P1-3): `work-start --allow-dirty`, which runs the FULL
  selection over the working-tree config behind an explicit banner; the connector probes
  are not the iteration surface.
- An unreachable/oversized/malformed/redirecting declared source closes as couldn't-check
  with the reason. Never a clear.
- **Id namespace (round-1 P2-11 + round-2 P1-8):** declared check and source ids MUST match
  `x_[a-z0-9_]+` after casefold normalization; built-in ids are reserved; collisions after
  normalization are validation failures. Shadowing is also closed: built-in display names,
  proposition texts, and canonical clear/finding phrases are reserved (a declared check may
  not present as a built-in), and a disabled built-in remains VISIBLY disabled in the
  coverage summary even when an x_ check resembles it.

**Declared check** (data, not code):
- `claim` text, `match`: a bounded rule over declared-source fields (equality, presence,
  prefix, and threshold comparators; total function). **Missing-field semantics pinned:**
  a match rule referencing a field absent from a record closes couldn't-fully-check,
  never clear, never silently skipped.
- **Time semantics (round-1 P1-9):** match operands may reference mapped fields plus
  EXACTLY two explicit time inputs: `request.requested_at` and the document's
  `observed_at` (both already flow in at the impure edge, so derive stays pure). ISO-8601
  parsing with UTC normalization; a malformed time in a record closes couldn't-fully-check.
  Times reach the replay digest through the documents they ride in, as today. This is
  sufficient for freeze windows (window bounds are record fields; now is requested_at).
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
- The four checks re-declare onto the contract with byte-identical output on every
  surface: the 16-row emulation matrix and the full test suite run unchanged as the
  regression oracle. The closure reshape lands via a PROJECTION SEAM (round-3): the richer
  ClosureEntry ships with a (proposition, status) projection so evaluate, content_digest,
  and render stay byte-identical while consumers migrate one slice at a time; the oracle
  stays green after every slice.
- **The oracle grows WITH the feature (round-3 buildability):** new rows are part of v1
  scope, not an afterthought: a committed-checks-block-honored row; a disabled-check row
  (the disable visible in the coverage summary); an untracked-config row (default four
  plus the loud line); the hook-speaks-on-unknown-check row (round-3 P0-1); and the
  extensibility proof row: ONE declared file source consumed by TWO declared checks, which
  makes the N:M closure machinery (build risk #1) tested rather than speculative, and
  exercises the declared-check contract, the tracked-file rule, and the not-enabled
  summary line in one place. Any expectation change in the matrix is a defect in the spine, not a
  row to update. (Round-1 P1-8 made this claim honest: the contract's advisory copy,
  provenance hooks, identity fields, and delta templates exist precisely so the FYI own-PR
  note, the criteria derivation note, and the since-you-started voice are expressible;
  internal recodings like profile_skipped preserve today's strings.)
- Existing rendered bytes: unchanged except the named new loud lines. MCP/CLI surface
  changes are exactly the ones named in section 3's migration (round-4 P2 wording fix).
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

## Round-1 disposition (codex, 2026-07-07)
All twelve findings accepted and pinned above: P0-1 consent_env required for every url
(no undefined no-credential case); P0-2 full SSRF policy; P0-3 file-source path safety
incl. git-tracked requirement; P1-4 schema evolution rules + requires_teamctx; P1-5
request-context vs team-semantics classification incl. diagnostic-override reclass and
delivery-surface knobs; P1-6 document identity + check-owned closure entries (named the
largest build piece); P1-7 profile_skipped first-class with strings preserved; P1-8 the
four-part copy table + identity fields making byte-identical honest; P1-9 time operands;
P2-10 duplicate-key rejection; P2-11 id namespacing; P2-12 conformance cache keyed by
version+config-hash, fail-closed.

## Round-2 disposition (codex, 2026-07-07)
All accepted: P0-1 connect-to-checked-IP (DNS rebinding closed); P0-2 config/conformance
failures become loud couldn't-check signals, never fail-safe-eaten exceptions; P1-3
consent_env presence/value semantics exact; P1-4 tracked-and-clean config required for
team-semantic blocks (our own dogfood violated this); P1-5 override migration named
exactly incl. MCP schema change and row migration; P1-6 stable document ids + explicit
versioned digest change, bytes-identical oracle; P1-7 identity/ambient round-trip in
conformance; P1-8 shadowing closed via reserved names/phrases; P2-9 advisory ownership
moved to source contracts. Scope decisions: conformance cache CUT; URL sources DEFERRED to
v1.1 (designed, pinned, not v1 build scope); repo-shape onboard suggestions DEFERRED.
Build risks, in order (drive the plan): 1. N:M closure migration without false clears;
2. ambient identity/content-digest drift (unlawful silence or re-speak); 3. declared-file
security + loud config failure across all surfaces.

## Round-3 disposition (Opus fresh eyes, 2026-07-07)
All accepted. P0-1: the hook now catches config-validation failure explicitly and SPEAKS
(row added); the fail-safe eats only unexpected errors. P0-2 + P2-1: tracked-and-clean
REPLACED by committed-blob reads (one reality, disables preserved, whole-file gap closed);
never-committed and no-git trees pinned (default four + loud reason). P1-1: the ambient key
hashes the effective semantics source, so commit-to-activate re-grounds. P1-2: declared
checks carry consumes/identity/lane/profile explicitly. P1-3: work-start --allow-dirty is
the iteration surface. P1-4: content identity takes closure (proposition, status) only;
ambient schema bump named; replay digest correction recorded. Buildability: projection seam
for the closure reshape; five new oracle rows in v1 scope incl. one declared source feeding
TWO declared checks (N:M tested, not speculative). P2-2 folded into the declared-check row;
P2-3 example fixed. Next: one short codex verification round on the committed-blob
mechanism's corners, then the verdict.

## Round-4 disposition (codex, targeted, 2026-07-08)
Verdict REVISE with no P0: the convergence tail. P1: authority.json classified as team
semantics and given the committed-blob rule (accepted; the alternative exemption was
weaker: authority changes what agents see). P2: shared config-failure formatter pinned;
the "surfaces unchanged" contradiction reworded. Mechanism pins folded: git show HEAD:
form; the five key states; the exact dirty-note wording; budget confirmed within the
reflex pins. The committed-blob mechanism verified sound across detached HEAD, linked
worktrees, rebase/bisect, zero-commit, and deleted-working-tree cases.

## CTO verdict
ROCK-SOLID. Four rounds, two independent reviewers, twenty-nine accepted findings, zero
open. The design is as good as review can make it; what remains is what only building
proves. Next: Edgar's spec sign-off, then the implementation plan (slice one: the
projection seam; the oracle green after every slice).
