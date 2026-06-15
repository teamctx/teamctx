# E-026: Section Grouping Compactness

## Purpose

Make the terminal context goldens match the product rule that cards are grouped
by section.

## Product Question

How do we keep working context compact without hiding important signals?

## Finding That Triggered This

The golden contract said to group cards by section, but the first default golden
repeated the `Needs attention` heading. That made a three-card context block feel
larger than it is.

## Hypothesis

Grouping section headings once preserves clarity and reduces terminal noise.

## Output

Revised golden outputs with grouped section headings.
