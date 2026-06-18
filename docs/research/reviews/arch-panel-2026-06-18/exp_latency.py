#!/usr/bin/env python3
"""Experiment C-1: the 'Performance Tax of Honesty'.
Tests Gemini's claim that an honest coverage certificate forces an N+1 I/O storm
that adds seconds to every request.

This is a SIMULATION with MODELED per-call latency distributions (lognormal,
fit to rough public p50/p95 for these cloud APIs) — not a benchmark against live
APIs (no creds, no network egress in sandbox). The exact ms are only as good as
the inputs; the QUALITATIVE comparison across architectures is the robust result.

Architectures compared, per get_context request over K sources:
  A  serial, no cache     -> latency = sum of one fresh call per source
  B  parallel, no cache    -> latency = max of one fresh call per source
  C  warm daemon + cache   -> latency = local cache read; freshness stamped,
                              refreshed by a background loop (this is what the
                              broker actually is)
"""
import math, random, statistics

random.seed(7)
N = 20000

def lognorm(median_ms, p95_ms):
    mu = math.log(median_ms)
    sigma = (math.log(p95_ms) - mu) / 1.645
    return lambda: random.lognormvariate(mu, sigma)

# Modeled per-call latencies (ms): (median, p95)
SOURCES = {
    "github":     lognorm(250, 900),
    "jira":       lognorm(400, 1500),
    "confluence": lognorm(500, 2000),
    "gitlab":     lognorm(300, 1200),
}
CACHE_READ = lognorm(2, 8)        # local in-memory/SQLite read
TIMEOUT_MS = 5000                  # a hung source caps here (then -> Unknown)

def draw(fn):
    return min(fn(), TIMEOUT_MS)

def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]

def run():
    fns = list(SOURCES.values())
    A, B, C = [], [], []
    for _ in range(N):
        calls = [draw(f) for f in fns]
        A.append(sum(calls))                 # serial, no cache
        B.append(max(calls))                 # parallel, no cache
        C.append(draw(CACHE_READ))           # warm cache read only
    rows = [("A serial, no cache", A), ("B parallel, no cache", B),
            ("C warm daemon + cache", C)]
    print(f"{'architecture':24} {'p50':>8} {'p95':>9} {'p99':>9}   (ms, modeled)")
    for name, xs in rows:
        print(f"{name:24} {pct(xs,50):8.0f} {pct(xs,95):9.0f} {pct(xs,99):9.0f}")

    # Staleness cost of C: with a background refresh every R seconds, the
    # coverage certificate reports an age uniformly in [0, R]. Show the trade.
    print("\nC's honesty trade — staleness reported vs. refresh interval:")
    print(f"{'refresh interval':>18} {'typical age shown':>20} {'worst age':>12}")
    for R in (15, 30, 60, 300):
        print(f"{R:>15}s {R/2:>18.0f}s {R:>11}s")

if __name__ == "__main__":
    run()
