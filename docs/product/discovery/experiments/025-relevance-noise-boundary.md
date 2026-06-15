# E-025: Relevance Noise Boundary

## Purpose

Fix the first prototype golden outputs so source-health caveats appear only when
they matter to the current task.

## Product Question

When is missing or stale source context helpful, and when is it noise?

## Finding That Triggered This

The first auth-token golden output included a stale release checklist warning.
That is useful for a release-task scenario, but noisy for a token retry edit that
is not release-scoped.

## Hypothesis

Source health should render in working context only when the source is configured
and relevant to the current task scope.

A stale release checklist is context for:

- preparing release checklist updates,
- deploying a release branch,
- release-process changes,
- or tasks that explicitly depend on the release checklist.

It is not default context for every auth-service edit.

## Output

Revised golden outputs and fixture relevance metadata.
