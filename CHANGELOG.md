# Changelog

All notable changes to `teamctx` will be documented in this file.

This project follows Semantic Versioning. During the `0.x` series, public APIs
may change while the product is hardened.

## [Unreleased]

### Added

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
  not a false green; a docs root scanned with nothing relied-on in scope reads "not applicable",
  not a false "current".

### Changed

- Gate copy no longer claims checks are "required" (real branch-protection requiredness is not
  yet verified); a clear gate reads "no failing checks found" instead of "CI is green".
- `teamctx init` no longer auto-enables `docs_root`; docs fire only when set explicitly with
  `--docs-root`, so init never promises to watch docs you did not ask it to.
- Work-start request paths are normalized to repo-relative POSIX, so a `./path` still matches the
  broker's repo-relative signal paths (previously an in-scope doc, PR, or gate could be missed).

### Fixed

- A malformed GitHub check-runs response now fails closed to an honest "unavailable" instead of a
  false all-clear (non-object runs, a failing run missing its name or url, or a non-integer
  total_count).
- In-progress CI runs are no longer silently skipped: a branch whose checks are still running no
  longer reads as green.
- A completed check whose conclusion is not success-like (cancelled, stale, or any value other
  than success/neutral/skipped) is now surfaced as not-clear instead of reading as green.

