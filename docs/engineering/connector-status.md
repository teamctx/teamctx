# Connector status

The card *kinds* are a closed, engine-complete family of four (frozen in
`core/prop.py` / `core/select.py`). Which kinds go **live**: i.e. have a real
connector feeding real source data, is pulled by the dogfood, one at a time. A kind
is not "done" until it is green **and** a card changed a real decision, before the next
connector is wired. (Rationale: four kinds proven only against fixtures is still zero
proof of usefulness.)

| Kind | Engine | Live connector |
|------|--------|----------------|
| collision (`pr_conflicts_with_path`) | ✅ | ✅ GitHub PRs, `connectors/github.py` |
| doc-superseded (`doc_superseded`) | ✅ | ✅ declared-frontmatter docs probe (merged 2026-06-20), *dogfood not yet run* |
| criteria-changed (`issue_criteria_changed`) | ✅ | ✅ GitHub Issues, `connectors/github_issues.py` + `connectors/issue_criteria.py` |
| missed-gate (`gate_failed`) | ✅ | ✅ GitHub check-runs, `connectors/github_checks.py` + `connectors/gate_status.py` |

> **The 4 kinds are the certified (S) tier, not the whole product.** The broader source
> breadth (Jira/Confluence/GitLab/Slack), the ambient **L (hint) tier**, and MCP transport
> are tracked in the [Product Completion plan](../product/sprints/2026-06-21-product-completion-plan.md).
> All four certified kinds now have live connectors. Next breadth: the **L (hint) tier**
> (ambient awareness, ~43% of high-value events), Jira as a second issue-tracker provider,
> and Confluence/GitLab connectors.
