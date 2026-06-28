# teamctx: Safe-Experiment Harness (spec)

*How teamctx tests its own adversarial-input claims without ever running an unsafe
experiment. Companion to the [protocol paper v1.0](teamctx-protocol-v1.0.md) (T3
feature-mediated selection; the injection-scope honesty in §8) and the
[architecture decision record](../product/vision/architecture-decision.md) (D1
capability ladder; D7 phantom filter). Closes open-item #7 in
[state-and-plan.md](../product/vision/state-and-plan.md).*

> **One-line thesis.** The harness obeys the same invariant the product does:
> **untrusted input only ever reaches a deterministic, read-only broker with no
> egress and no agency**, so the test rig can never become the exploit path. The
> harness eats teamctx's own dogfood.

---

## 1. Why this needs a spec

teamctx makes an adversarial claim that has to be *measured*, not asserted:
**feature-mediated selection** (T3), a poisoned source artifact (a PR body or Jira
comment crafted to read as an instruction) can change *what the agent is told* only
through the same structural features any artifact is selected by; it cannot inject
free-form text into the agent's instructions. The honest scope is equally load-bearing:
teamctx hardens *its pipe*, not the model, end-to-end safety still needs a cooperating
consumer, and **we do not claim "incapable of harm."**

Testing those claims means deliberately handling **malicious input**. Done naively, the
experiment is the vulnerability: a payload meant to probe selection-safety instead
reaches a live model with real tools, real source credentials, or open egress, and now
the *test* is the injection vector, the exfil path, or the source-corruption event. The
harness exists to make that class of mistake **structurally impossible**, not merely
discouraged.

**Non-goal.** This is not the model-referee harness (the arch-panel rig under
`/tmp/teamctx-arch-panel/`, which runs frontier panels over *our own sanitized
design briefs*). That one handles trusted text we wrote; this one handles **untrusted
text an attacker wrote.** Different threat model, different rig.

---

## 2. Threat model

The asset under test is the **selection pipeline** (Route/Stamp/Envelope + the phantom
filter). The adversary controls the *content* of one or more source artifacts but not
teamctx's code or config. Three harms the harness must prevent **by construction**:

| Harm | Naive-experiment failure | What it would cost |
|---|---|---|
| **Injection escalation** | payload reaches a live agent with tools | the test steers a real model into a real action |
| **Exfiltration** | sandbox has egress + real creds | payload phones home with real data |
| **Source corruption** | experiment writes to a real source | poisoned fixtures leak into a real GitHub/Jira |

The harness defeats all three with the same move the product uses: **remove agency and
egress from anything the untrusted bytes can touch.**

---

## 3. The core invariant (the one rule)

> **Untrusted bytes may reach exactly one of two destinations, and nothing else:**
> **(A)** the **deterministic broker in a golden test**: a pure function: no LLM, no
> network, no tools, no real credentials; or
> **(B)** a **sealed disposable sandbox**: no real credentials, egress denied by
> default, ephemeral filesystem, an agent with no act-capable tools.
>
> An untrusted payload reaching a live model **with** real credentials **or** open
> egress is, by definition, an unsafe experiment, and the harness must **fail closed**
> rather than run it.

Everything below is the mechanism that makes that invariant true and *checkable*.

---

## 4. Mode A: Golden tests (the safe default, ~99% of runs)

The poisoned artifacts are **static, inert fixtures** in the corpus (§6). They are fed
to the broker's selection pipeline; assertions are made on the **emitted card surface
and certificate**, deterministically, with no model and no network in the loop.

```
poisoned_fixture(s)  →  broker.select()  →  (cards, κ certificate)  →  assert
        (inert data)     (pure function)        (deterministic)
```

This is where the T3 claim is actually *exercised*: does an injection string in a PR
body change **which** cards are selected, **how loud** they route, or **what tier**
they land in? The answer must be "no, beyond the structural features any artifact is
scored on", and that is a property of a pure function over fixtures, so it is fully
reproducible and bisectable. Golden tests also pin the **phantom filter** (diagnostic
vectors → no false collision) and the **Stamp honesty** invariants (a poisoned artifact
can never be stamped `certified` if its target-confidence is semantic).

Mode A needs no sandbox because there is nothing to sandbox: no agency, no egress, no
credentials. The bytes are data the way the product treats them as data.

---

## 5. Mode B: Sealed disposable sandbox (rare; consumer-cooperation studies only)

Mode A cannot answer one question: does a *cooperating* consumer actually honor the
labeled-evidence boundary at generation time? Studying that needs a real model in the
loop, the one case where untrusted bytes meet an LLM. It runs **only** in a sealed
sandbox:

- **No real credentials**: the connectors are pointed at **fixture sources** via
  synthetic OAuth; the sandbox holds no token that authorizes any real system.
- **Egress denied by default**: the **connector-allowlist rung** of the capability
  ladder (D1) is pointed *only* at the sealed fixtures; all other egress is blocked at
  the network boundary, not in application code.
- **Ephemeral filesystem**: disposable container; destroyed after the run; no mount of
  any real workspace.
- **No act-capable tools**: the agent under study is given read-only context and a
  text channel; it has no shell, no write tools, no real network.

The blast radius of a successful injection in Mode B is **the sandbox and nothing
else**, which is the whole point.

---

## 6. Guardrails

**G1, Pre-flight cage check ("verify real tooling before any agent-under-attack
test").** Before a Mode-B run, the harness *proves the cage is locked*: it actively
attempts an egress to a canary endpoint and asserts it is **denied**; asserts the
credentials in scope are synthetic; asserts every configured source resolves to a
fixture. **Any check failing aborts the run.** You test the deny, you never assume it.

**G2, Corpus provenance & inertness.** The malicious-input corpus lives in one
clearly-marked, version-controlled location (e.g. `tests/corpus/adversarial/`), is
**never executed**, and is **never** fed to any live system outside Mode B. Each entry
carries provenance (what attack class, where it came from) and is treated as opaque
bytes.

**G3, The no-unsafe-experiment gate.** A single guard sits in front of every
experiment entry point and refuses to run if the configuration would route untrusted
input to (a live model) ∧ (real credentials ∨ non-fixture egress). This is the
executable form of §3, the invariant as code, fail-closed.

**G4, Determinism receipts.** Mode-A runs emit the same κ-style certificate the
product does (content-addressed snapshot of inputs → outputs), so a result is replayable
and a regression is attributable to a specific fixture + code rev.

---

## 7. What it measures (deconfounded eval)

The harness is also the evaluation rig for the claims the protocol leans on. Modeled and
adversarial, honest about *direction, not exact percentage* (the house style from the
arch-panel experiments):

- **Selection-safety under attack** (Mode A), does a poisoned artifact change the
  certified surface beyond its structural features? Target: **no**.
- **Phantom-filter precision** (Mode A), diagnostic-vector false-collision rate.
- **Disagreement-detector precision** (Mode A), the measured **0.44** on the 48-item
  corpus is exactly the kind of result this rig produces, and it is *why* undeclared
  value-disagreement stays an **L hint, not a certified card.** The integrity thesis
  eating its own dogfood.
- **Consumer-cooperation rate** (Mode B), given correctly labeled evidence, how often
  does a given model honor the boundary? Reported as *"this model, this config,"* never
  as a universal guarantee.

---

## 8. Honest limits

- **Mode A proves selection-safety (T3), not end-to-end safety.** The cooperating-
  consumer residual is real and shared with Sol and Wei (teamctx hardens its pipe, not
  the model). Mode B studies it but cannot retire it.
- **The corpus is necessarily incomplete.** You cannot enumerate all attacks. The
  corpus is a **regression floor**: "these known attacks stay defeated", not a proof
  of injection-immunity. New attack classes are new fixtures, forever.
- **Mode B findings are existential, not universal.** "Model X in config Y honored the
  boundary" does not generalize to all models or all prompts; it is evidence, weighted
  accordingly.
- **The cage check (G1) tests the egress paths it knows about.** A novel egress channel
  the harness does not probe is an untested path; G1 reduces risk, it does not certify
  the sandbox hermetic.

---

## 9. Build order (when code starts)

1. **Corpus + Mode A first**: the corpus location, the inert-fixture format, and the
   golden-test selection assertions. This delivers the regression floor with **zero**
   live-model risk and needs no sandbox.
2. **G3 gate + G2 provenance**: the fail-closed guard and the corpus discipline, before
   any Mode-B code exists, so the unsafe path is closed by construction from day one.
3. **Mode B + G1/G4 last**: the sealed sandbox and the pre-flight cage check, added only
   when a consumer-cooperation study is actually needed. Most of teamctx's adversarial
   claims are settled in Mode A; Mode B is the exception, not the default.
