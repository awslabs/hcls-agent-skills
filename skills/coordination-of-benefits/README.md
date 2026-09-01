# Coordination of Benefits — Skill

## What this adds

A reasoning skill for **Coordination of Benefits (COB)** — the rules that determine which insurer pays first when a patient has multiple plans. This is one of the most common sources of claim denials in healthcare billing, appearing as CO-22 denials across Medicare and commercial payers.

The skill covers two frameworks:

- **Medicare Secondary Payer (MSP)** — federal rules that determine when Medicare is *not* the primary payer. The default assumption in billing is "Medicare pays first," but MSP overrides that when an employer plan, workers' comp, or auto insurer should pay first instead. Getting this wrong is a federal compliance violation with potential penalty exposure.
- **NAIC commercial COB** — order-of-benefits rules for patients with two commercial plans: birthday rule, subscriber vs. dependent, active vs. COBRA, duration tiebreaker.

The skill also covers coordination math (standard COB, non-duplication, Medicaid lesser-of) and CO-22/CO-23 denial resolution.

---

## Why COB needs a skill

COB has a well-defined rule set (CMS MSP Manual, NAIC Model 120, 42 CFR §411) but baseline models fail on it in a predictable way: they know the rules exist but misapply thresholds and edge cases that are extremely common in practice.

The specific failure modes our eval confirmed:

| Scenario | Baseline failure | Skill fix |
|---|---|---|
| Disability patient, employer < 100 | Applies 20-employee working-aged threshold | Correctly applies 100-employee disability threshold |
| Both plans active simultaneously (job overlap) | Applies "active beats COBRA" rule | Skips to longer-coverage tiebreaker |
| Patient turns 65 during ESRD coordination period | Resets COB order at age 65 | Correctly continues ESRD rules through the 30-month window |
| Dual entitlement (age 65 + disability) | Invents a "most restrictive threshold" rule | Evaluates each MSP basis independently; working-aged governs |
| Medicaid as secondary, Medicare paid more than Medicaid's fee schedule | Flags $0 Medicaid payment as an error | Correctly applies lesser-of rule, flags balance billing prohibition |

These aren't obscure edge cases — they are the exact scenarios that generate CO-22 denials on a billing team's desk. A wrong answer isn't just unhelpful; it creates MSP violations, conditional payment recovery demands, and ping-pong denials between payers.

---

## Why this is a skill, not a lookup

COB can't be solved with RAG or a knowledge base because the user presents a novel fact pattern each time (different Medicare basis, different employer size, different denying payer). The skill has to apply rules to facts — it's a reasoning problem, not a retrieval problem. 
This is the category of problem where skills outperform baseline most reliably.

---

## Eval results

### Single-skill: 34 prompts, easy through hard

| Metric | Value |
|---|---|
| Win rate | 97.1% (33/34) |
| Cohen's d | +1.28 (large) |
| Delta | +11.8 |
| Skill activation | 34/34 |

| Dimension | Win Rate | Cohen's d |
|---|---|---|
| critical_thinking | 98.5% | +1.66 |
| actionability | 98.5% | +1.32 |
| relevance | 92.6% | +1.10 |
| scientific_accuracy | 80.9% | +0.76 |
| coherence | 89.7% | +0.63 |

### Cross-skill (COB + provider-denial-workup): 3 prompts

| Metric | Value |
|---|---|
| Win rate | 100% |
| Cohen's d | +7.56 (large) |
| critical_thinking d | +5.00 |

The cross-skill prompts test the natural workflow: a CO-22 denial arrives, COB reasoning determines whether the denial is correct or an error, and denial-workup determines posture (OVERTURN and draft appeal, or reroute with corrective billing steps).

---

## Glossary

| Term | Meaning |
|---|---|
| **COB** | Coordination of Benefits — rules governing how multiple insurers split the bill |
| **MSP** | Medicare Secondary Payer — federal law governing when Medicare is not primary |
| **ESRD** | End-Stage Renal Disease — kidney failure requiring dialysis or transplant; a separate Medicare eligibility basis with its own 30-month coordination period |
| **NAIC** | National Association of Insurance Commissioners — sets Model Regulation 120 governing commercial COB order-of-benefits |
| **GHP** | Group Health Plan — employer-sponsored insurance |
| **CARC** | Claim Adjustment Reason Code — standardized denial code; CO-22 = "another payer may be primary" |

---

## Files

- `SKILL.md` — skill definition
- `../../eval/prompts/single/coordination-of-benefits-01..34.yaml` — 34 single-skill eval prompts
- `../../eval/prompts/cross/cob-denial-workup-01..03.yaml` — 3 cross-skill prompts (COB + provider-denial-workup)

