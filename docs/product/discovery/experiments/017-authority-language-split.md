# E-017: Authority Language Split

## Purpose

Separate reviewed project guidance from advisory source matches.

E-016 exposed a product risk: a note in an approved folder can be useful without
being authoritative. If the language blurs that line, the product will make
ordinary notes feel like policy.

## Product Question

How should TeamCtx describe source matches that may be relevant but are not
reviewed guidance?

## Hypothesis

The product needs two internal signal types and two external tones:

- `approved_guidance`: reviewed guidance, rendered as `Project guidance`.
- `advisory_match`: relevant source match, rendered as `Good to know`.

Users should not see either internal signal name.

## Test Variants

Test the same source fact in three phrasings:

1. Over-authoritative: `An approved vault note says...`
2. Too weak: `A note might mention...`
3. Preferred: `A note in a selected folder may be relevant...`

## Pass Criteria

The preferred language should:

- Make the source worth checking.
- Avoid implying policy or truth.
- Avoid implying broad vault search.
- Avoid making the user learn `advisory_match`.
- Give the agent a clear next behavior.

## Stop Conditions

Revise if:

- Agents treat note matches as commands.
- Users would reasonably feel their private notes are being searched.
- The phrase sounds so weak that the agent ignores it.
- The card needs explanation text to be understood.

## Output

A recommended language split and revised source-signal fixture for local notes.
