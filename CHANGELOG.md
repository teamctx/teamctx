# Changelog

All notable changes to `teamctx` will be documented in this file.

This project follows Semantic Versioning. During the `0.x` series, public APIs
may change while the product is hardened.

## [Unreleased]

### Added

- `teamctx onboard` detects a conventional docs/ folder and configures it, and the CLAUDE.md
  snippet now claims all four checks with their conditions stated; `teamctx status` reports the
  docs configuration.

- work-start now derives the linked issue and the start time from your branch name, local commit trailers, and the merge-base, with the derivation named in the output; explicit --issue/--since override it.
- `teamctx onboard`: a single command to set up a repo with zero flags and zero false confidence.
  It detects the GitHub repo, writes a trackable `.teamctx/config.json`, installs the reflex hook,
  writes an honest CLAUDE.md snippet (managed between markers, migration-safe, never overwriting
  hand-edited content), reports the real credential path, and prints a live open-PR reachability
  check that is never a verdict. Additive and idempotent, every write atomic; `--dry-run`,
  `--force`, and `--repo` supported. A missing credential is reported, never fatal.
- Initial product, architecture, security/privacy, and build-plan documents.
- Python package skeleton with CLI entrypoint.
- Initial project metadata and executable metadata tests.
- Two core coverage states, additive within the `v0` contracts (no existing value is changed or
  removed, so existing documents stay valid): `pending` and `not_applicable` on
  `SourceStatusValue`, and `incomplete[pending]` and `not_applicable[out-of-scope]` on the
  completeness closure. A gate whose CI checks are still running now reads as "still running",
  not a false green. (The `not_applicable` states remain in the contract for future kinds; the
  docs check no longer uses them, see Changed.)

### Changed

- The docs check now covers the whole declared docs folder: any doc there that names a newer replacement is flagged at work-start, whether or not you are editing it. A clean scan is a real green.
- Internal: card kinds are now a single registry (core/kinds.py); adding a kind is a one-entry change. No behavior change.
- teamctx status now reports real setup state (config, hook, snippet, credential, live reachability) through the same resolvers onboard uses; the old placeholder text is gone.
- The GitHub PR connector no longer builds display cards; collision cards derive in the core, so their copy has exactly one home.
- Gate copy no longer claims checks are "required" (real branch-protection requiredness is not
  yet verified); a clear gate reads "no failing checks found" instead of "CI is green".
- `teamctx init` no longer auto-enables `docs_root`; docs fire only when set explicitly with
  `--docs-root`, so init never promises to watch docs you did not ask it to.
- Work-start request paths are normalized to repo-relative POSIX, so a `./path` still matches the
  broker's repo-relative signal paths (previously an in-scope doc, PR, or gate could be missed).

### Fixed

- A skipped check now says exactly which input is missing and how to provide it, and issue-change time comparisons are chronological, never lexical.
- A malformed .teamctx/authority.json now fails closed with a plain message naming the file and the fix, instead of a traceback (CLI and MCP).
- teamctx-mcp without the optional mcp dependency now prints an install hint instead of a raw ImportError.
- work-start no longer flags the open PR of the branch you are on as a collision; it is set aside with an FYI line and recorded on the forge source status.
- The `gh pr view N` hint on a conflict finding now carries `--repo owner/name`, so it works from
  any directory and matches the `open-source` command.
- A malformed GitHub check-runs response now fails closed to an honest "unavailable" instead of a
  false all-clear (non-object runs, a failing run missing its name or url, or a non-integer
  total_count).
- In-progress CI runs are no longer silently skipped: a branch whose checks are still running no
  longer reads as green.
- A completed check whose conclusion is not success-like (cancelled, stale, or any value other
  than success/neutral/skipped) is now surfaced as not-clear instead of reading as green.
