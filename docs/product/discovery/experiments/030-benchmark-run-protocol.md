# E-030: Benchmark Run Protocol

## Purpose

Add run-order, manifest, and score-capture files to the generated benchmark
packet.

## Product Question

Is the benchmark packet ready for real model runs without ad hoc manual setup?

## Hypothesis

The benchmark packet should include enough structure to reduce order bias and
make results capture repeatable:

- alternating first prompt order,
- machine-readable manifest,
- score sheet,
- prompt files generated from fixtures.

## Output

Updated benchmark exporter and regenerated E-029 packet.
