# Launch readiness — teamctx.dev

*Dated 2026-06-21. What it takes to get the public page (and, later, teamctx itself) live.*

## Marketing site (teamctx.dev)
- **Source:** `site/index.html` — self-contained static landing page; copy from
  [`positioning.md`](vision/positioning.md) (ambient-context marquee, credibility as the *because*).
- **Host:** Vercel · team `eddiespaghettinis-projects` · project `site`.
- **Deployed:** live + render-verified at the project URL `https://site-jade-tau-43.vercel.app`.
- **Domain:** `teamctx.dev` added to the project (status: awaiting DNS).

### GO-LIVE — the one DNS record (registrar action; needs Edgar)
Set at the DNS provider (current nameservers `ns1/ns2.dyna-ns.net`):

```
A    teamctx.dev    76.76.21.21
```

Optional `www`: `CNAME  www.teamctx.dev  →  cname.vercel-dns.com`

Once the `A` record is in: Vercel auto-verifies, provisions HTTPS, and **teamctx.dev serves the
current deployment** — no redeploy needed. Propagation is usually minutes.

### Redeploy when the page changes
From `site/`, with the token in `.secrets/vercel`:

```
vercel deploy --prod --yes --scope eddiespaghettinis-projects
```

## Broader OSS launch gates (not blocking the page — tracked so they aren't lost)
- **Repo is private** → make `teamctx/teamctx` public before the site links to it.
- **pip / PyPI** packaging + a user-facing README.
- **CURPLAN1 (missed-gate) PR** is blocked on the GitHub token `workflow` scope —
  `gh auth refresh -h github.com -s workflow`, then push `build/cp1-missed-gate`.
- **Real-world dogfood** remains the only proof of *usefulness* (see
  [CURRENT.md](plan/CURRENT.md)).
