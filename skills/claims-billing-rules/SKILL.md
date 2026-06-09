---
name: claims-billing-rules
description: >
  Reasoning skill for healthcare claims billing rules and fraud detection logic. Use when the
  user asks about CMS billing rules, place of service codes, global surgery periods, modifier
  usage (25 59 76 77), NCCI edit logic, column 1 column 2 code pairs, mutually exclusive
  procedures, modifier indicators, fraud waste and abuse patterns, E&M upcoding, unbundling,
  phantom billing, impossible day detection, coding error versus fraud distinction, FWA
  investigation methodology, or claims audit logic. Triggers include "CMS billing rules",
  "NCCI edits", "modifier 25", "modifier 59", "global surgery period", "upcoding",
  "unbundling", "phantom billing", "impossible day", "FWA", "fraud waste abuse",
  "coding error vs fraud", "claims audit", "billing compliance", "E&M level selection".
usage: Invoke when reasoning about healthcare billing compliance, NCCI edit logic, or fraud waste and abuse detection patterns.
version: 1.0.0
tags: [skill, category:reasoning, claims, billing, fwa, hcls]
---

# Claims Billing Rules — Reasoning Skill

## Overview

Guide the agent through CMS billing rules, NCCI edit logic, and fraud/waste/abuse (FWA)
detection patterns. This skill encodes regulatory knowledge and decision frameworks for
claims analysis, audit, and compliance review.

## Usage

- Invoke when reasoning about CMS billing compliance or modifier usage
- Use for NCCI edit logic, global surgery period rules, or FWA detection patterns
- Activate for claims audit methodology or coding error vs fraud distinction

---

## Core Concepts

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail

The decision trees, detection methodologies, and audit protocols in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Never show the tree traversal, step-by-step audit walkthrough, or self-corrections. Present only the final determination with supporting evidence.

## 1. CMS Billing Fundamentals

### Place of Service (POS) Codes

| POS Code | Description | Payment Impact |
|---|---|---|
| 11 | Office | Standard physician fee schedule |
| 21 | Inpatient Hospital | Facility rate (lower physician payment) |
| 22 | On Campus — Outpatient Hospital | Facility rate |
| 23 | Emergency Room — Hospital | Facility rate + ED differential |
| 31 | Skilled Nursing Facility | SNF rate |
| 81 | Independent Laboratory | Lab fee schedule |
| 02 | Telehealth (other than patient home) | Telehealth rate |
| 10 | Telehealth — Patient Home | Telehealth rate |

**Rule**: The same CPT code paid at facility POS (21, 22, 23) yields a LOWER physician payment
than at non-facility POS (11) because the facility bears overhead costs. Billing a facility
service under POS 11 is a common upcoding pattern.

### Global Surgery Periods

| Period | Description | Included Services |
|---|---|---|
| 0-day | Minor procedure | Only the procedure day; pre/post visits billable separately |
| 10-day | Minor procedure with follow-up | Procedure day + 10 days post-op visits included |
| 90-day | Major procedure | 1 day pre-op + procedure day + 90 days post-op included |
| XXX | Global concept does not apply | E&M, lab, radiology — no global period |
| YYY | Carrier determines | Unlisted procedures |

**Rules**:
1. Services within the global period are NOT separately billable unless a qualifying modifier is used.
2. Modifier 24 (unrelated E&M during post-op period) allows separate billing for a DIFFERENT diagnosis.
3. Modifier 78 (return to OR for related complication) allows separate billing during global period.
4. Modifier 79 (unrelated procedure during post-op period) allows separate billing.

### Modifier Usage Decision Tree

```
Is the service within a global surgery period?
 ├─ YES
 │   ├─ Unrelated E&M visit? → Modifier 24 (must have different diagnosis)
 │   ├─ Return to OR for complication? → Modifier 78
 │   ├─ Unrelated procedure? → Modifier 79
 │   └─ Staged procedure? → Modifier 58
 └─ NO
     ├─ Significant, separately identifiable E&M on same day as procedure?
     │   └─ → Modifier 25 (documentation must support separate E&M)
     ├─ Distinct procedural service (different site, organ, or incision)?
     │   └─ → Modifier 59 or XE/XS/XP/XU (NCCI-associated)
     ├─ Repeat procedure by same physician, same day?
     │   └─ → Modifier 76
     └─ Repeat procedure by different physician, same day?
         └─ → Modifier 77
```

### Key Modifier Reference

| Modifier | Name | When to Use | Abuse Risk |
|---|---|---|---|
| 25 | Significant, Separately Identifiable E&M | E&M + procedure same day | HIGH — most abused modifier |
| 59 | Distinct Procedural Service | Bypass NCCI edit for truly distinct services | HIGH — used to unbundle |
| 76 | Repeat Procedure, Same Physician | Same procedure repeated same day | MEDIUM |
| 77 | Repeat Procedure, Different Physician | Same procedure by different provider same day | MEDIUM |
| 24 | Unrelated E&M During Post-Op | E&M for different condition in global period | MEDIUM |
| 78 | Unrelated Procedure During Post-Op | Return to OR for complication | LOW |
| 79 | Unrelated Procedure During Post-Op | Different procedure in global period | LOW |
| 22 | Increased Procedural Services | Substantially greater effort | MEDIUM — subjective |

---

## 2. NCCI Edit Logic

### Overview

The National Correct Coding Initiative (NCCI) defines code pair edits that prevent improper
payment for services that should not be billed together.

### Edit Types

| Edit Type | Description | Example |
|---|---|---|
| Column 1 / Column 2 | Column 2 code is a component of Column 1 code; Column 2 is denied | 43239 (upper GI with biopsy) includes 43235 (upper GI diagnostic) |
| Mutually Exclusive | Two procedures that cannot reasonably be performed together | Two different approaches to the same anatomical site |
| Medically Unlikely Edits (MUE) | Maximum units of service per line per day | Most E&M codes: MUE = 1 |

### NCCI Modifier Indicators

| Indicator | Meaning | Action |
|---|---|---|
| 0 | Modifier NOT allowed to bypass edit | Claim MUST be denied if both codes billed |
| 1 | Modifier allowed to bypass edit | Modifier 59/XE/XS/XP/XU may override if clinically appropriate |
| 9 | Not applicable | Edit does not apply |

### NCCI Edit Resolution Decision Tree

```
Are both codes on the same claim, same date of service, same provider?
 ├─ NO → No NCCI edit applies
 └─ YES
     ├─ Is the code pair in the NCCI edit table?
     │   ├─ NO → Both codes payable
     │   └─ YES
     │       ├─ Modifier indicator = 0?
     │       │   └─ Column 2 code DENIED. No override possible.
     │       ├─ Modifier indicator = 1?
     │       │   ├─ Is modifier 59/XE/XS/XP/XU present on Column 2 code?
     │       │   │   ├─ YES → Is the modifier clinically justified?
     │       │   │   │   ├─ YES → Both codes payable
     │       │   │   │   └─ NO → Flag for audit
     │       │   │   └─ NO → Column 2 code DENIED
     │       │   └─ (end)
     │       └─ Check MUE for each code
     │           └─ Units exceed MUE? → Excess units DENIED
     └─ (end)
```

### Common NCCI Edit Scenarios

| Scenario | Column 1 | Column 2 | Rule |
|---|---|---|---|
| Comprehensive + component lab | 80053 (CMP) | 80048 (BMP) | BMP is subset of CMP; deny 80048 |
| Surgical package | 27447 (TKA) | 27331 (arthrotomy knee) | Arthrotomy included in TKA |
| E&M + minor procedure | 99213 | 11102 (skin biopsy) | Modifier 25 required on E&M |
| Bilateral procedure | 27447-RT | 27447-LT | Not an NCCI edit; use modifier 50 or RT/LT |

---

## 3. Fraud, Waste, and Abuse (FWA) Patterns

### Pattern Taxonomy

| Pattern | Category | Description | Detection Signal |
|---|---|---|---|
| E&M Upcoding | Fraud/Abuse | Systematically billing higher E&M levels than documented | Provider's E&M distribution skewed vs specialty peers |
| Unbundling | Fraud/Abuse | Billing component codes separately instead of comprehensive code | Frequent Column 2 codes with modifier 59 |
| Phantom Billing | Fraud | Billing for services not rendered | Claims on dates patient was not present (cross-ref with other data) |
| Impossible Day | Fraud | >24 hours of time-based services in one day | Sum of time-based codes × minutes > 1440 per provider per day |
| Duplicate Billing | Waste/Error | Same service billed twice | Exact match on provider, patient, date, CPT |
| Upcoding POS | Fraud/Abuse | Billing non-facility POS for facility-based services | POS 11 for services rendered at POS 22 |
| Modifier Abuse | Fraud/Abuse | Appending modifiers to bypass edits without clinical justification | High modifier 59 usage rate vs peers |
| Balance Billing | Fraud | Billing patient for amounts beyond allowed amount | Patient complaints, EOB analysis |

### E&M Upcoding Detection

#### Expected E&M Distribution (Office Visits, General Internal Medicine)

| E&M Code | Expected % Range | Red Flag If |
|---|---|---|
| 99211 | 1–5% | >10% (possible downcoding to avoid scrutiny) |
| 99212 | 5–15% | <2% |
| 99213 | 30–50% | <15% |
| 99214 | 25–40% | >55% |
| 99215 | 5–15% | >30% |

**Detection methodology**:
1. Calculate provider's E&M code distribution.
2. Compare to specialty-specific peer benchmarks.
3. Compute chi-squared statistic or z-score per code level.
4. Flag providers with z-score > 2.0 for 99214/99215 combined.
5. Validate with documentation audit (medical necessity for level billed).

### Unbundling Detection

**Signals**:
1. Provider bills Column 2 codes at rate >2× specialty average.
2. Modifier 59 usage rate >15% of procedure claims (specialty-dependent threshold).
3. Specific code pairs appear together repeatedly (e.g., always billing 76000 with 20610).

**Decision tree**:
```
Does the provider bill NCCI Column 2 codes at >2× peer rate?
 ├─ NO → Low risk
 └─ YES
     ├─ Is modifier 59 present on most Column 2 claims?
     │   ├─ YES → Review documentation for distinct service justification
     │   └─ NO → Claims should have been denied by NCCI edits (payer system issue)
     └─ Are the same code pairs repeated across many patients?
         ├─ YES → Systematic unbundling pattern → escalate to SIU
         └─ NO → Possible isolated coding errors → education
```

### Impossible Day Detection

**Rules**:
1. Sum all time-based service minutes per provider per calendar day.
2. Flag if total > 1,440 minutes (24 hours).
3. For non-time-based services, use CMS time estimates per CPT code.
4. Account for legitimate scenarios: provider working across midnight, multiple locations.

### Phantom Billing Detection

**Cross-reference data sources**:
- Patient check-in/check-out logs
- EHR access logs (was the chart opened on the service date?)
- Badge/swipe data (was the provider in the building?)
- Prescription records (was a prescription written on the service date?)
- Other claims (was the patient at a different facility on the same date?)

---

## 4. Coding Error vs Fraud Distinction

### Decision Framework

| Characteristic | Coding Error | Fraud |
|---|---|---|
| Distribution | Random across codes and patients | Systematic pattern by provider or group |
| Directionality | Both upcoding and downcoding present | Consistently in direction of higher payment |
| Response to education | Improves after training | Persists or shifts to different pattern |
| Documentation | Present but miscoded | Missing, cloned, or fabricated |
| Volume | Sporadic | High volume, consistent over time |
| Financial impact | Variable, often small per claim | Large aggregate impact |

### Escalation Decision Tree

```
Is the pattern systematic (same direction, same codes, over time)?
 ├─ NO
 │   ├─ Is the error rate >5% of claims?
 │   │   ├─ YES → Coding education + re-audit in 90 days
 │   │   └─ NO → Normal error rate; no action needed
 │   └─ (end)
 └─ YES
     ├─ Does the pattern consistently increase payment?
     │   ├─ NO → Systematic coding error → education + process review
     │   └─ YES
     │       ├─ Is documentation present and supports the billed code?
     │       │   ├─ YES → Possible abuse (aggressive but documented coding)
     │       │   │         → Medical director review
     │       │   └─ NO → Probable fraud
     │       │           → Refer to Special Investigations Unit (SIU)
     │       └─ (end)
     └─ (end)
```

### Statistical Tests for Pattern Detection

| Test | Purpose | Threshold |
|---|---|---|
| Chi-squared | Compare provider code distribution to peers | p < 0.01 |
| Z-score per code | Identify specific codes that are outliers | \|z\| > 2.0 |
| Benford's Law | Detect fabricated charge amounts | First-digit distribution deviates from expected |
| Time series | Detect sudden shifts in billing patterns | Change point detection (e.g., CUSUM) |
| Clustering | Group providers by billing behavior | Outlier clusters warrant review |

---

## When NOT to Use This Skill
- Clinical coding (assigning ICD-10 diagnosis codes from chart notes) — use clinical-data-standards skill instead
- Patient billing disputes or EOB interpretation — this skill covers payer/provider compliance, not consumer advocacy
- Pharmacy benefit or Part D claims — this skill covers professional (Part B) and facility claims only

## When to Escalate to Human Expert
- Potential fraud referral to OIG or law enforcement — requires legal counsel and SIU protocol, not algorithmic determination
- Provider appeals involving medical necessity peer-to-peer review — requires clinical judgment from a licensed physician
- State-specific Medicaid billing rules that override federal CMS policy — requires jurisdiction-specific compliance expertise

## 5. Common Billing Compliance Mistakes

1. **Wrong:** Billing E&M with a procedure on the same day without modifier 25
   **Right:** Add modifier 25 to the E&M code and ensure documentation supports a significant, separately identifiable service
   **Why:** Without modifier 25, the claim is denied or the E&M is not paid

2. **Wrong:** Using modifier 59 to bypass NCCI edits without supporting documentation
   **Right:** Document the distinct anatomical site, separate encounter, or different organ system justifying the modifier
   **Why:** Undocumented modifier 59 usage creates audit liability and potential fraud allegations

3. **Wrong:** Billing services separately during a global surgery period without qualifying modifiers
   **Right:** Check the procedure's global period before billing; use modifiers 24/78/79 only when clinically appropriate
   **Why:** Services within the global period are included in the surgical package and are not separately payable

4. **Wrong:** Submitting an incorrect Place of Service (POS) code
   **Right:** Verify where the service was actually rendered and use the corresponding POS code
   **Why:** Incorrect POS causes overpayment or underpayment and triggers audit flags

5. **Wrong:** Billing for an assistant surgeon without modifier 80 or 82
   **Right:** Append the appropriate assistant surgeon modifier (80 for physician, 82 for non-physician)
   **Why:** Claims without the required modifier are denied

6. **Wrong:** Submitting claims without checking NCCI edit tables for code pair conflicts
   **Right:** Validate all code pairs against current quarterly NCCI tables before submission
   **Why:** NCCI violations cause preventable denials that delay payment

7. **Wrong:** Cloning documentation across multiple visits with identical notes
   **Right:** Ensure each note reflects the specific encounter with unique clinical details
   **Why:** Identical notes across visits suggest fraud and put all associated claims at risk of recoupment

---

## 6. Audit Methodology

### Pre-Audit Analysis

1. **Identify target**: Provider, facility, or code pattern flagged by analytics.
2. **Pull claims data**: 12-month window minimum; include all CPT, diagnosis, modifier, and payment data.
3. **Benchmark**: Compare to specialty peers (same specialty, same region, same payer mix).
4. **Statistical screening**: Apply tests from Section 4 to confirm pattern.

### Chart Review Protocol

1. **Sample selection**: Random sample of flagged claims (minimum 30 claims for statistical validity).
2. **Review criteria**: Does the documentation support the billed code level?
3. **Scoring**: For each claim, determine the correct code based on documentation.
4. **Error rate calculation**: (incorrect claims / total reviewed) × 100.
5. **Extrapolation**: If error rate >5%, extrapolate overpayment to full claim population.

### Audit Outcome Actions

| Error Rate | Classification | Action |
|---|---|---|
| 0–5% | Acceptable | No action; routine monitoring |
| 5–15% | Elevated | Education, corrective action plan, re-audit in 6 months |
| 15–30% | Significant | Prepayment review, repayment demand, compliance agreement |
| >30% | Critical | SIU referral, potential exclusion, law enforcement referral |

---

## 7. Regulatory Reference

| Regulation | Scope | Key Requirement |
|---|---|---|
| False Claims Act (31 USC §3729) | Federal | Knowingly submitting false claims; treble damages + per-claim penalty |
| Anti-Kickback Statute (42 USC §1320a-7b) | Federal | Prohibits payment for referrals; safe harbors exist |
| Stark Law (42 USC §1395nn) | Federal | Prohibits physician self-referral for designated health services |
| NCCI (CMS) | Federal | Code pair edits; updated quarterly |
| OIG Work Plan | Federal | Annual focus areas for audits and investigations |
| State FWA laws | State-specific | Vary by state; may have lower intent thresholds |

---

## 8. Glossary

| Term | Definition |
|---|---|
| CPT | Current Procedural Terminology — procedure codes maintained by AMA |
| ICD-10-CM | International Classification of Diseases, 10th Revision, Clinical Modification — diagnosis codes |
| HCPCS | Healthcare Common Procedure Coding System — Level II codes for supplies, DME |
| NCCI | National Correct Coding Initiative — CMS code pair edit system |
| MUE | Medically Unlikely Edit — maximum units per line per day |
| E&M | Evaluation and Management — office visit codes (99202–99215) |
| POS | Place of Service — two-digit code indicating where service was rendered |
| SIU | Special Investigations Unit — payer fraud investigation team |
| FWA | Fraud, Waste, and Abuse |
| EOB | Explanation of Benefits — document sent to patient showing claim adjudication |
| RAF | Risk Adjustment Factor — see risk-adjustment-strategy skill |
