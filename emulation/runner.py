"""Row runner for the Phase 5 emulation harness.

Runs one row or the whole scenario matrix and writes per-row evidence (actual output + verdict),
redacted through the program spec's redaction map before anything is written. The BUILDER runs
ONLY ``--offline``: every row is driven against local tmp git repos and the bundled mock servers,
so no live network call is ever made. LIVE execution against the real lab repos is the CTO's step
after review, never the builder's; the runner refuses to run without ``--offline`` so that rail is
enforced in code, not just in prose.

Runnable as ``python emulation/runner.py --offline --all`` (it bootstraps its own import path) or
imported as ``emulation.runner``.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SRC = _REPO_ROOT / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from emulation.evidence import ProgramResult, RowResult  # noqa: E402
from emulation.redact import NULL_REDACTION, RedactionMap  # noqa: E402
from emulation.rows import (  # noqa: E402
    row01_collision_github,
    row02_collision_gitlab,
    row03_gate_github,
    row04_gate_gitlab,
    row05_criteria_github,
    row06_criteria_jira,
    row07_docs_local,
    row08_docs_confluence,
    row09_onboard_status,
    row10_transports_agree,
    row11_replay,
    row12_unbounded,
)

# The scenario matrix in program order. Row 8 is an honest stub until the Confluence connector
# lands.
ROW_MODULES = [
    row01_collision_github,
    row02_collision_gitlab,
    row03_gate_github,
    row04_gate_gitlab,
    row05_criteria_github,
    row06_criteria_jira,
    row07_docs_local,
    row08_docs_confluence,
    row09_onboard_status,
    row10_transports_agree,
    row11_replay,
    row12_unbounded,
]


def run_program(row_ids: list[str] | None = None) -> ProgramResult:
    """Run every selected row offline and collect the results in program order."""

    selected = ROW_MODULES if not row_ids else [m for m in ROW_MODULES if m.ROW_ID in row_ids]
    return ProgramResult(rows=tuple(module.run_offline() for module in selected))


def write_evidence(
    out_dir: Path, program: ProgramResult, *, redaction: RedactionMap = NULL_REDACTION
) -> None:
    """Write one directory per row: the redacted actual output and a verdict file. Redaction is
    applied before anything touches disk (offline GitHub rows have nothing to redact; the map is
    load-bearing for the live Jira/Confluence rows)."""

    out_dir.mkdir(parents=True, exist_ok=True)
    for row in program.rows:
        row_dir = out_dir / f"row{row.row_id}"
        row_dir.mkdir(parents=True, exist_ok=True)
        (row_dir / "actual.txt").write_text(redaction.apply(row.actual), encoding="utf-8")
        (row_dir / "verdict.txt").write_text(_verdict_text(row), encoding="utf-8")


def _verdict_text(row: RowResult) -> str:
    lines = [f"{row.status} row {row.row_id}: {row.title}"]
    if row.note:
        lines.append(f"note: {row.note}")
    for outcome in row.outcomes:
        mark = "ok" if outcome.ok else "MISS"
        lines.append(f"  [{mark}] {outcome.kind}: {outcome.subject}")
    return "\n".join(lines) + "\n"


def summarize(program: ProgramResult) -> str:
    lines = ["Phase 5 emulation harness (offline)", ""]
    for row in program.rows:
        suffix = f"  ({row.note})" if row.status == "SKIP" and row.note else ""
        lines.append(f"  [{row.status:4}] {row.row_id} {row.title}{suffix}")
    passes = sum(1 for row in program.rows if row.status == "PASS")
    skips = sum(1 for row in program.rows if row.status == "SKIP")
    fails = sum(1 for row in program.rows if row.status == "FAIL")
    lines.append("")
    lines.append(f"{len(program.rows)} rows: {passes} PASS, {skips} SKIP, {fails} FAIL")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emulation/runner.py",
        description="Drive the Phase 5 team-validation scenario matrix offline.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="run every row against tmp repos + the bundled mock (the only mode the harness runs; "
        "live execution against the real lab is the CTO's step after review).",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all", action="store_true", help="run the whole scenario matrix.")
    group.add_argument(
        "--row", action="append", metavar="ID", help="run one row by id (e.g. 01); repeatable."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="evidence output directory (default: a fresh temp dir, printed on completion).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.offline:
        parser.error(
            "refusing to run without --offline: live execution against the real lab is the CTO's "
            "step after review, never the builder's. Re-run with --offline."
        )
    if not args.all and not args.row:
        parser.error("choose --all or --row ID.")

    program = run_program(args.row)
    out_dir = args.out or Path(tempfile.mkdtemp(prefix="teamctx-emulation-"))
    write_evidence(out_dir, program)
    print(summarize(program))
    print(f"\nEvidence written to {out_dir}")
    return 1 if program.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
