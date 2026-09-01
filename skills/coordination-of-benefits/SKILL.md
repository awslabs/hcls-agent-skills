---
name: coordination-of-benefits
description: "Reasoning skill for Coordination of Benefits (COB) determination in healthcare claims. Use when a claim involves multiple insurers and the user needs to know which plan pays first, how to sequence billing, or why a COB-related denial or underpayment occurred. Covers Medicare Secondary Payer (MSP) rules and NAIC commercial COB order-of-benefits logic. Triggers include \"coordination of benefits\", \"COB\", \"Medicare secondary payer\", \"MSP\", \"which insurance is primary\", \"birthday rule\", \"primary payer\", \"secondary payer\", \"COB denial\", \"working aged\", \"ESRD coordination\", \"disability MSP\", \"workers comp primary\", \"no-fault primary\", \"auto insurance primary\", \"COB order of benefits\", \"dual coverage\", \"double coverage\", \"two insurances\", \"secondary billing\", \"crossover claim\", \"COB adjustment\", \"non-duplication\", \"benefits coordination error\"."
usage: Invoke when a claim has multiple insurers and the user needs to determine primary/secondary order, compute secondary payment, or resolve a COB denial.
version: 1.0.0
tags: [skill, category:reasoning, revenue-cycle, cob, msp, hcls]
---

# Coordination of Benefits (COB) — Reasoning Skill

## When to Use

- A patient has two or more insurance plans and the user needs to know which pays first
- A claim was denied or underpaid with a COB-related reason code (CO-22, OA-22, CO-23, OA-23, CO-25)
- A Medicare claim needs MSP screening before billing Medicare
- A biller is sequencing a crossover claim (Medicare → Medicaid or Medicare → secondary commercial)

---

## Response Format

Structure each response in this order:

1. **Scenario** — identify which COB framework applies (MSP or NAIC commercial) and why
2. **Order of Benefits** — state primary payer and secondary payer with the specific rule that governs it
3. **Coordination Math** — what the secondary owes, using the correct method (coordination vs non-duplication)
4. **Billing Sequence** — exact steps to bill each payer in order
5. **Flags** — any deadlines, documentation requirements, or common mistakes for this scenario

Do not narrate the decision tree traversal. Present only the conclusion with the governing rule cited.
Target: 200–350 words for analysis; include full billing sequence when requested.

---

## Guardrails

- **No fabrication** — if the patient's plan documents or contract terms are unknown, flag as `[verify with plan document]`
- **MSP takes precedence** — when Medicare is involved, always screen for MSP first; commercial COB rules only apply when Medicare is not a payer
- **State variation** — NAIC Model 120 is the baseline; individual states may vary. Flag: `[verify state-specific COB rules if claim is in a non-conforming state]`
- **Medicaid is always last** — Medicaid is payer of last resort by federal law; never bill Medicaid before all other insurers
- **Date of service governs payer, not the most recent plan on file** — when a patient changes coverage mid-treatment, the plan active on the date of service is the correct payer for that claim. Always verify coverage effective and termination dates against each DOS. Billing the current active plan for a DOS that falls under a prior plan is a COB error regardless of what is in the system at billing time

---

## Framework Selection

```
Does the patient have Medicare?
├─ YES → Apply Medicare Secondary Payer (MSP) rules first
│   └─ Is there also a commercial secondary? → Apply coordination math after MSP
└─ NO → Apply NAIC commercial COB order-of-benefits rules
    └─ Is one plan Medicaid? → Medicaid always pays last regardless of other rules
```

---

## Core Procedure

Follow these steps in order for every COB determination:

1. **Identify all payers** — list every insurance plan the patient carries: commercial, Medicare, Medicaid, Medicare Advantage, TRICARE, workers' comp, no-fault auto. A missed payer is the #1 COB error.
2. **Screen for Medicare** — if Medicare is one of the payers, apply MSP rules before any commercial COB rules. MSP always takes precedence.
3. **Obtain MSP questionnaire status** — for Medicare patients, verify whether an MSP questionnaire was completed at registration. If not on file, ask the user before proceeding; do not assume Medicare is primary.
4. **Handle unknown MSP status** — if MSP status cannot be confirmed: flag as `[MSP status unverified — complete CMS MSP questionnaire before billing]` and default to billing the commercial plan first as a precaution.
5. **Apply MSP scenario table** — match the patient's situation to one of the 10 MSP scenarios using employer size, Medicare basis (age/disability/ESRD), and injury type.
6. **Check for retroactive MSP** — if Medicare already paid and a primary payer is later identified, Medicare must recover its conditional payment. Flag this scenario: `[Conditional payment recovery required — notify MSP Recovery Contractor]`.
7. **Apply NAIC commercial COB rules** — if Medicare is not involved, work through the 7 order-of-benefits rules in sequence (subscriber vs dependent → birthday rule → active vs retired → duration tiebreaker).
8. **Determine COB math method** — read the secondary plan's COB provision for "non-duplication" or "maintenance of benefits" language. If found → Method 2. If standard COB language or unclear → Method 1.
9. **Compute secondary payment** — apply the correct method (coordination or non-duplication) per Part 3 below. Show the math explicitly.
10. **Identify required documentation** — for each payer in sequence: primary EOB (required for secondary submission), MSP questionnaire (required for Medicare secondary claims), accident report (required for WC/no-fault), court order (required for divorced-parent dependent child claims).
11. **Sequence the billing** — bill primary first, wait for EOB, then submit to secondary with primary EOB attached. Never submit to secondary before primary responds.
12. **Check Medicaid last** — if Medicaid is one of the payers, bill it last regardless of any other rule. Attach all prior EOBs.
13. **Resolve COB denials** — map the CARC to the COB Denial table in Part 4; follow the specific resolution path for that code.
14. **Flag crossover claim handling** — for Medicare/Medicaid crossovers, confirm whether the state uses automatic crossover forwarding. If yes, do not bill Medicaid separately; if no, submit manually with Medicare EOB.
15. **Document the determination** — record the COB order determination and the rule that governs it in the claim notes for audit trail purposes.

---

### Part 1 — Medicare Secondary Payer (MSP)

MSP rules determine when Medicare is NOT the primary payer. When any of the following scenarios apply, the other payer must be billed first.

#### MSP Scenario Table

| Scenario | Condition | Primary Payer | Medicare Status |
|---|---|---|---|
| Working aged | Patient 65+, employer has **≥20 employees**, active employee or spouse | Employer group health plan (GHP) | Secondary |
| Working aged — small employer | Patient 65+, employer has **<20 employees**, active employee or spouse | Medicare | Primary |
| Disability | Patient <65, disabled, employer has **≥100 employees** | Employer GHP | Secondary |
| Disability — small employer | Patient <65, disabled, employer has **<100 employees** | Medicare | Primary |
| ESRD — coordination period | End-Stage Renal Disease, first **30 months** after Medicare entitlement begins (entitlement starts the **4th month of dialysis** for regular dialysis patients, or month of kidney transplant) | Employer GHP (if active coverage exists) | Secondary |
| ESRD — after coordination period | After 30-month coordination period | Medicare | Primary |
| ESRD — patient turns 65 during/after coordination period | Patient has ESRD Medicare entitlement and reaches age 65 while also covered by a GHP | **During** coordination period: GHP primary (ESRD rules still govern). **After** coordination period: apply working-aged MSP rules — if employer ≥20 employees, GHP is primary again under working-aged rules. Turning 65 does **not** reset the 30-month clock, but once the coordination period ends, working-aged rules take over if the patient is still an active employee. | Depends on employer size and whether coordination period has ended |
| No-fault insurance | Injury covered by auto no-fault policy | No-fault insurer | Secondary |
| Workers' compensation | Work-related injury or illness | Workers' comp carrier | Secondary — **never bill Medicare first for WC claims** |
| Liability insurance | Third-party liability (auto accident, slip-and-fall) | Liability insurer | Secondary |
| Veterans benefits | VA-covered condition | VA | Secondary — only if treatment at non-VA facility for non-VA condition |
| COBRA | Patient on COBRA, also has Medicare due to disability | Medicare | Primary (COBRA is secondary when Medicare is due to disability) |

**Key MSP thresholds:**
- Working aged employer size: **≥20 employees** = GHP primary
- Disability employer size: **≥100 employees** = GHP primary
- ESRD coordination period: **30 months** from first Medicare entitlement date (not ESRD onset). `[Verify exact start date against CMS MSP Manual Publication 100-05 — some CMS guidance places the start at the first month of dialysis rather than the 4th month entitlement date]`
- **ESRD employer size is irrelevant during the coordination period** — unlike working-aged and disability MSP, the ESRD 30-month coordination rule applies regardless of employer size. Do not cite employer size as a factor in ESRD COB order during the coordination period.
- MSP verification source: CMS MSP Manual, Publication 100-05, Chapter 2 — verify current version

**Dual entitlement (age + disability simultaneously):** When a patient is both 65+ and disabled (SSDI), evaluate each MSP provision independently — do NOT apply a "most restrictive" or "higher threshold" rule. Working-aged rules govern when the patient is an active employee. Example: patient age 69, disabled, employer has 95 employees → working-aged threshold (≥20) = GHP primary; disability threshold (≥100) = Medicare primary. Because the patient is working-aged and the employer meets the ≥20 threshold, **working-aged rules control and GHP is primary**. The disability provision is irrelevant once working-aged rules establish GHP primacy. `[Verify with CMS MSP Manual Publication 100-05 for current dual-entitlement guidance]`

#### MSP Decision Tree

```
Is the patient 65 or older with an active employer GHP?
├─ YES
│   ├─ Employer has ≥20 employees? → GHP primary, Medicare secondary
│   └─ Employer <20 employees? → Medicare primary, GHP secondary (Medicare SELECT)
└─ NO
    ├─ Patient disabled (under 65) with employer GHP?
    │   ├─ Employer ≥100 employees? → GHP primary, Medicare secondary
    │   └─ Employer <100 employees? → Medicare primary
    ├─ Patient has ESRD?
    │   ├─ Calculate 30-month period from Medicare entitlement date (4th month of dialysis, not diagnosis date)
    │   ├─ Within 30-month coordination period? → GHP primary (if GHP exists)
    │   └─ After 30 months? → Medicare primary regardless of employer size
    └─ Injury involved?
        ├─ Workers' comp? → WC carrier primary, never bill Medicare first
        ├─ No-fault auto? → No-fault insurer primary
        └─ Liability? → Liability insurer primary (conditional payment rules apply)
```

**Conditional payment warning:** For liability, no-fault, and WC claims, Medicare may make conditional payments while the primary payer case is pending. When the primary payer settles, Medicare must be reimbursed via the Benefits Coordination & Recovery Center (BCRC). **Do not cite specific BCRC phone numbers, form numbers, or MMSEA Section 111 reporting deadlines in responses** — these change and must be verified at cms.gov/medicare/coordination-of-benefits-and-recovery before acting. Flag: `[Verify current BCRC contact and reporting requirements at cms.gov]`.

---

### Part 2 — NAIC Commercial COB (Non-Medicare)

When Medicare is not involved, apply NAIC Model 120 order-of-benefits rules.

#### Order of Benefits Rules (apply in sequence — first rule that applies controls)

| Priority | Rule | Primary Plan |
|---|---|---|
| 1 | Non-COB plan | A plan with no COB provision always pays first |
| 2 | Patient is not a dependent | The plan covering the patient as an **employee/subscriber** pays before the plan covering them as a dependent |
| 3 | Dependent child — parents not separated | Plan of the parent whose **birthday falls earlier in the calendar year** (birthday rule — month and day only, not year) |
| 4 | Dependent child — parents separated/divorced | Plan of the parent with **court-ordered financial responsibility** pays first; if no court order, custodial parent's plan; then stepparent of custodial parent; then non-custodial parent |
| 5 | Active employee vs. retired/COBRA | **Active employee** plan is primary. **Retired/inactive employee** plan is secondary to active but **primary over COBRA/continuation**. COBRA is always last among these three. **This rule only applies when one plan covers the patient as an active employee and the other as an inactive/retired/COBRA enrollee. When both plans cover the patient as an active employee simultaneously, skip to Rule 6.** |
| 6 | Longer continuous coverage | Plan covering the patient **longer** pays first (tiebreaker) |
| 7 | Equal duration | Plans share costs 50/50 if all else equal |

**Retired vs COBRA distinction:** A retiree plan and a COBRA plan are not equivalent. A retiree plan (ongoing coverage from former employer as a benefit) is primary over a COBRA plan (temporary continuation coverage). Order: Active employee → Retiree/inactive → COBRA.

**Dual active-employment overlap:** When a patient is actively employed at two jobs simultaneously and both employer plans are active for the same dates of service, Rule 5 does not apply — neither plan is continuation or inactive coverage. Apply Rule 6 directly: the plan that has covered the patient longer is primary. This scenario arises when a patient changes jobs with overlapping coverage periods (e.g., old plan active through June 30, new plan effective June 1 — during June 1–30 both are active-employment plans and the longer-coverage rule governs).

**Birthday rule detail:** If both parents have the same birthday (month and day), the plan that covered the parent longer pays first. The rule is based on calendar birthday, not age — a younger parent with a January 1 birthday is primary over an older parent with a December 31 birthday.

**Gender rule:** Some older plans used the gender rule (father's plan primary). NAIC Model 120 replaced this with the birthday rule. If a plan still uses the gender rule, it violates NAIC guidelines — flag for the patient to contest.

---

### Part 3 — Coordination Math

#### Method 1: Coordination of Benefits (Standard — most commercial plans)

Secondary pays the lesser of:
- Its own allowed amount minus what the primary paid, OR
- The patient's out-of-pocket cost after primary payment (copay + coinsurance + deductible)

```
Example:
Billed:           $1,000
Primary allowed:  $800  →  Primary pays $640 (80%), patient owes $160
Secondary allowed: $850
Secondary pays:   min($850 − $640, $160) = min($210, $160) = $160
Patient owes:     $0
```

#### Method 2: Non-Duplication (some commercial plans — check plan document)

Secondary pays only if its own benefit exceeds what the primary already paid. It pays the difference up to its own benefit — but only if primary paid less than the secondary would have paid alone.

```
Example:
Primary pays $640 on a $800 allowed claim (80%)
Secondary allows $850, would pay $680 alone (80%)
Secondary pays: $680 − $640 = $40
```

**Non-duplication is less generous to the patient.** If the primary paid more than the secondary would have paid alone, the secondary pays $0.

**How to tell which method applies:** Read the secondary plan's COB provision. "Non-duplication" or "maintenance of benefits" language = Method 2. Standard COB language = Method 1. When in doubt, assume Method 1.

#### Method 3: Medicaid as Secondary — Lesser-of Rule

When Medicaid is secondary (always payer of last resort), most states apply the **lesser-of** methodology:

Medicaid pays the **lesser of**:
- Its own fee schedule amount minus what the primary already paid, OR
- $0 if the primary already paid ≥ Medicaid's fee schedule amount

```
Example:
Medicare (primary) paid:   $148
Medicaid fee schedule:     $90
Medicaid pays:             max($90 − $148, $0) = $0
Patient owes:              $0 (balance billing prohibited for Medicaid patients)
```

**Key rule:** If Medicare (or any primary payer) has already paid more than Medicaid's fee schedule, Medicaid pays $0. This is not an error — it is the correct outcome under the lesser-of rule. Do not bill the patient the difference; balance billing Medicaid patients is prohibited by federal law.

`[Verify state-specific Medicaid lesser-of methodology — some states use cost-sharing or supplemental payment rules that differ]`

#### Medicare as Secondary — Crossover Claims

When Medicare is secondary (MSP applies):
1. Bill primary payer first; obtain remittance
2. Submit crossover claim to Medicare with primary's EOB attached
3. Medicare pays up to its allowed amount minus what primary paid
4. Medicare does **not** pay more than its own allowed amount total
5. For Medicare/Medicaid crossover: Medicare forwards claim automatically to Medicaid in most states — do not bill Medicaid separately

---

### Part 4 — COB Denial Resolution

| CARC | Description | Root Cause | Resolution |
|---|---|---|---|
| CO-22 | This care may be covered by another payer | Payer believes another plan is primary | Provide MSP questionnaire result or primary EOB |
| OA-22 | Same as CO-22 | Same | Same |
| CO-23 | Payment adjusted due to COB | COB applied — payment reduced | Verify coordination math; dispute if secondary calculation is wrong |
| OA-23 | Same as CO-23 | Same | Same |
| CO-25 | Payment denied — payment made by another payer | Duplicate payment concern | Provide remittance showing no duplicate; resubmit |

---

## Common Mistakes

- **Wrong:** Applying the 20-employee threshold for a disability-based Medicare patient.
  **Right:** The 20-employee threshold applies only to working-aged (65+) MSP. For disability-based Medicare, the threshold is **100 employees**. An employer with 80 employees makes Medicare primary for a disabled patient under 65, but secondary for a working-aged patient 65+.

- **Wrong:** Billing Medicare first for a working-aged patient whose employer has 80 employees.
  **Right:** The employer GHP is primary. Bill GHP first, then Medicare. Billing Medicare first creates an MSP violation and Medicare will recover the conditional payment.

- **Wrong:** Applying the birthday rule by age (older parent = primary).
  **Right:** Birthday rule uses calendar date (month and day) — earlier in the year = primary, regardless of which parent is older.

- **Wrong:** Billing Medicaid before a commercial secondary payer.
  **Right:** Medicaid is always payer of last resort by federal law (42 CFR §433.139). Bill all other payers first.

- **Wrong:** Assuming ESRD coordination period starts at diagnosis.
  **Right:** The 30-month period starts at the **first month of Medicare entitlement** due to ESRD — not at diagnosis or dialysis start.

- **Wrong:** Using non-duplication math when the plan uses standard COB.
  **Right:** Check the plan document for "non-duplication" or "maintenance of benefits" language. Default to standard coordination method if unclear.

- **Wrong:** Billing Medicare for a workers' comp claim before WC settles.
  **Right:** WC is always primary. Medicare may make conditional payments but must be reimbursed when WC settles. Document all conditional payments.

- **Wrong:** Applying the gender rule (father's plan primary) for dependent children.
  **Right:** NAIC Model 120 replaced the gender rule with the birthday rule in all conforming states. Flag if a payer is still applying the gender rule.

- **Wrong:** Assuming the longer-coverage tiebreaker applies before checking active vs. retired status.
  **Right:** Active employee plan always beats retired/COBRA plan — apply that rule before the duration tiebreaker.

- **Wrong:** Applying the active-employee-beats-COBRA rule when both plans are active-employment plans.
  **Right:** Rule 5 (active vs. retired/COBRA) only fires when one plan is genuinely continuation or inactive coverage. When a patient is actively employed at two employers simultaneously and both plans are active for the same dates, skip Rule 5 entirely and apply Rule 6: the plan covering the patient longer is primary.

- **Wrong:** Applying a "most restrictive" or "higher threshold" rule when a patient has dual Medicare entitlement (age + disability).
  **Right:** Evaluate each MSP provision independently. Working-aged rules govern for an active employee 65+. If the employer meets the ≥20 working-aged threshold, GHP is primary regardless of disability status or the 100-employee disability threshold.

- **Wrong:** Citing Form CMS-L564 as the MSP questionnaire.
  **Right:** Form CMS-L564 is the Request for Employment Information used for Medicare Part B enrollment, not the MSP questionnaire. The MSP questionnaire is a separate CMS intake form completed at registration to determine MSP status. `[Verify current MSP questionnaire form number at cms.gov]`

---

## Quick Reference: MSP Employer Size Thresholds

| Medicare Basis | GHP Primary Threshold | Medicare Primary When |
|---|---|---|
| Age 65+ (working aged) | ≥20 employees | <20 employees |
| Disability (under 65) | ≥100 employees | <100 employees |
| ESRD | Any size — first 30 months | After 30-month period |

**Sources:**
- CMS MSP Manual, Publication 100-05 — verify current version at cms.gov
- NAIC Coordination of Benefits Model Regulation, Model 120 — verify state adoption at content.naic.org/model-laws
- 42 CFR §433.139 — Medicaid payer of last resort
- 42 CFR §411 — Medicare Secondary Payer statute
