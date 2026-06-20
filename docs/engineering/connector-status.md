# Connector status

The card *kinds* are a closed, engine-complete family of four (frozen in
`core/prop.py` / `core/select.py`). Which kinds go **live** — i.e. have a real
connector feeding real source data — is pulled by the dogfood, one at a time. A kind
is not "done" until it is green **and** a card changed a real decision, before the next
connector is wired. (Rationale: four kinds proven only against fixtures is still zero
proof of usefulness.)

| Kind | Engine | Live connector |
|------|--------|----------------|
| collision (`pr_conflicts_with_path`) | ✅ | ✅ GitHub PRs — `connectors/github.py` |
| doc-superseded (`doc_superseded`) | ✅ | 🔨 in progress — declared-frontmatter docs probe (`docs/superpowers/plans/2026-06-20-doc-superseded-connector.md`) |
| criteria-changed (`issue_criteria_changed`) | ✅ | ⏳ deferred — pulled when a dogfood needs it |
| missed-gate (`gate_failed`) | ✅ | ⏳ deferred — pulled when a dogfood needs it |
