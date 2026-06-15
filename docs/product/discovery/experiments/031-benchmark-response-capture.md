# E-031: Benchmark Response Capture

## Purpose

Make the generated benchmark packet ready to store raw model answers and
scored results without inventing a folder layout during the run.

## Product Question

Can we move from local fixture checks to external model evidence without
turning the run into scattered notes?

## Hypothesis

The packet should include explicit response paths and result instructions so
each model run can be compared scenario by scenario:

- prompt files generated from fixtures,
- alternating run order,
- response path convention,
- score sheet with response-file columns,
- scoring and flag definitions beside the packet.

## Output

Updated benchmark exporter and regenerated E-029 packet with response and
result capture files.
