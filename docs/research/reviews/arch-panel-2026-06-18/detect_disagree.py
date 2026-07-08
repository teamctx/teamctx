#!/usr/bin/env python3
"""Deterministic cross-artifact disagreement detector + scorer.
A REASONABLE approximation of teamctx's typed-field extractor (φ) + phantom filter,
written to GENERAL rules (not tuned to the corpus), run once. It is NOT the eventual
production φ; this probes the inherent difficulty / achievable precision.

Per item, output one of: disagree | agree | unknown.
  unknown = "I can't certify a comparison" (would fall to the L hint tier, not a card).
Score precision/recall of the *disagree* claim (the trust-critical, cry-wolf axis),
split by field_type."""

import json
import pathlib
import re
from collections import Counter

WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
# superseded / non-current markers: lines at/after these are dropped
SUPERSEDED = re.compile(
    r"(previous|prior|old\b|older|earlier|rejected|deprecat|"
    r"do not implement|don't implement|history|was\b|formerly|"
    r"context only|left here|outdated|superseded|no longer|"
    r"~~|originally|initial draft|first draft)",
    re.I,
)
CURRENT = re.compile(
    r"(current|now\b|new behavior|updated|post-|final|today|latest|"
    r"as of|in effect|going forward)",
    re.I,
)
PRIORITY = {
    "p0": 0,
    "p1": 1,
    "p2": 2,
    "p3": 3,
    "critical": 1,
    "highest": 1,
    "high": 2,
    "medium": 3,
    "med": 3,
    "low": 4,
    "blocker": 0,
}


def to_canonical_num(tok, unit):
    n = WORDS.get(tok.lower())
    if n is None:
        try:
            n = float(tok)
        except ValueError:
            return None
    u = (unit or "").lower()
    if u in ("ms", "millisecond", "milliseconds"):
        return ("time", n)
    if u in ("s", "sec", "secs", "second", "seconds"):
        return ("time", n * 1000)
    if u in ("m", "min", "mins", "minute", "minutes"):
        return ("time", n * 60000)
    return ("count", n)


def current_text(text):
    """Drop lines that look superseded/historical; keep current ones."""
    keep = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            continue
        # a line with a 'was/now' both -> keep but we'll prefer the now-value later
        if SUPERSEDED.search(s) and not CURRENT.search(s) and "now" not in s.lower():
            continue
        keep.append(s)
    return "\n".join(keep)


def extract_now_was(text):
    """Handle 'now X (was Y)' / 'is now X' / 'X (was Y)' -> return X tokens."""
    vals = []
    for m in re.finditer(r"(?:is\s+)?now\s+([\w.]+)", text, re.I):
        vals.append(m.group(1))
    for m in re.finditer(r"([\w.]+)\s*\(\s*was\s+[\w.]+\)", text, re.I):
        vals.append(m.group(1))
    return vals


def extract_field_value(field, text, field_type):
    """Best-effort deterministic extraction of the field's CURRENT value."""
    text = current_text(text)
    low = text.lower()
    # priority/enum fields
    if field_type == "structured" and re.search(r"priorit|severity|status", field, re.I):
        for k, v in PRIORITY.items():
            if re.search(rf"\b{k}\b", low):
                return ("enum", v)
    if field_type != "structured":
        return None  # free text: detector cannot certify a comparable value
    # prefer now/was-resolved values
    cand_tokens = extract_now_was(text)
    # explicit "max attempts / total = N" style
    m = re.search(
        r"(?:max\s+attempts?|total(?:\s+attempts| shots)?|maxattempts)\D{0,12}?(\d+)", low
    )
    if m:
        cand_tokens.insert(0, m.group(1))
    # generic number+unit near anywhere (fallback)
    nums = re.findall(
        r"(\b[\w.]+\b)\s*(ms|s|sec|secs|seconds|m|min|mins|minutes|"
        r"retries|retry|attempts?|deliveries|times|x)?",
        text,
        re.I,
    )
    for tok, unit in nums:
        if tok.lower() in WORDS or re.fullmatch(r"\d+(\.\d+)?", tok):
            cand_tokens.append(tok + ("|" + unit if unit else ""))
    # resolve first parseable candidate to canonical
    for c in cand_tokens:
        if "|" in c:
            tok, unit = c.split("|", 1)
        else:
            tok, unit = c, None
        v = to_canonical_num(tok, unit)
        if v:
            return v
    return None


def detect(item):
    f = item["field"]
    ft = item.get("field_type", "structured")
    a = extract_field_value(f, item["source_a"], ft)
    b = extract_field_value(f, item["source_b"], ft)
    if a is None or b is None:
        return "unknown"
    if a[0] != b[0]:
        return "unknown"  # type mismatch -> can't compare
    return "agree" if abs(a[1] - b[1]) < 1e-9 else "disagree"


items = [
    json.loads(line)
    for line in pathlib.Path("corpus_merged.jsonl").read_text().splitlines()
    if line.strip()
]
rows = []
for it in items:
    pred = detect(it)
    truth = it["truth"]
    rows.append((it, pred, truth))


def score(subset, name):
    # positive class = "disagree"
    tp = sum(1 for it, p, t in subset if p == "disagree" and t == "disagree")
    fp = sum(1 for it, p, t in subset if p == "disagree" and t != "disagree")
    fn = sum(1 for it, p, t in subset if p != "disagree" and t == "disagree")
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    metrics = (
        f"{name:22} n={len(subset):2d}  disagree: precision={prec:.2f} "
        f"recall={rec:.2f}  (tp={tp} fp={fp} fn={fn})"
    )
    print(metrics)
    return fp


print("=== Disagreement detection (positive class = 'disagree') ===")
score(rows, "ALL")
score([r for r in rows if r[0].get("field_type") == "structured"], "structured only")
score([r for r in rows if r[0].get("field_type") == "freetext"], "freetext only")
print("\n=== False positives (CRIED WOLF, the trust-killers) ===")
for it, p, t in rows:
    if p == "disagree" and t != "disagree":
        message = (
            f"  [{it.get('id')}/{it['_src']}] field={it['field']} "
            f"trap={it.get('trap')} truth={t} -> said DISAGREE"
        )
        print(message)
print("\n=== False negatives (missed real disagreements -> would be Unknown, not wrong) ===")
for it, p, t in rows:
    if p != "disagree" and t == "disagree":
        message = (
            f"  [{it.get('id')}/{it['_src']}] field={it['field']} "
            f"ft={it.get('field_type')} trap={it.get('trap')} -> said {p}"
        )
        print(message)
print(
    "\ntrap-level FP counts:",
    dict(Counter(it.get("trap") for it, p, t in rows if p == "disagree" and t != "disagree")),
)
