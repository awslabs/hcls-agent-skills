---
name: hedis-measure-specification
description: >
  Reasoning skill for HEDIS measure specification, enrollment logic, exclusion evaluation,
  NCQA audit requirements, and care gap prioritization. Use when the user asks about HEDIS
  measure definitions, denominator/numerator/exclusion logic, continuous enrollment rules,
  Star Rating impact, or care gap closure strategies.
usage: Use when interpreting HEDIS specifications, evaluating enrollment/exclusion logic, or prioritizing care gaps.
version: 1.0.0
tags: [skill, category:reasoning, hedis, quality-measures, hcls]
triggers:
  - HEDIS measure
  - quality measure
  - denominator
  - numerator
  - exclusion
  - NCQA audit
  - continuous enrollment
  - care gap
  - Star Rating
  - measure specification
  - CDC measure
  - BCS measure
  - CBP measure
---

# HEDIS Measure Specification Reasoning

## Overview

Structured interpretation of HEDIS quality measures: denominator/numerator logic, continuous enrollment evaluation, exclusion application, NCQA audit readiness, and Star Rating-weighted care gap prioritization. Based on NCQA HEDIS Technical Specifications (MY 2024).

## Usage

- Activate when interpreting HEDIS measure denominator/numerator/exclusion logic
- Activate when evaluating continuous enrollment rules or allowable gaps
- Activate when prioritizing care gaps by Star Rating weight or SDOH barriers

## Core Concepts

## Response Format

Apply measure logic internally. Present the final specification, rate interpretation, or gap prioritization with justification. Do not narrate enrollment evaluation steps or exclusion logic walkthrough.

## 1. HEDIS Measure Structure

Every HEDIS measure follows:

```
Eligible Population (Denominator)
  → minus Exclusions
  → equals Eligible Denominator
  → Numerator (members who met the quality criteria)
  → Rate = Numerator / Eligible Denominator
```

| Component | Definition | Example (CDC — Diabetes HbA1c) |
|-----------|-----------|-------------------------------|
| **Denominator** | Members eligible based on age, diagnosis, enrollment | Age 18–75, diabetes (E11.x), continuously enrolled |
| **Exclusions** | Members removed due to clinical exceptions | Hospice, ESRD, organ transplant |
| **Numerator** | Members who met the quality criteria | HbA1c test performed during measurement year |
| **Rate** | Numerator ÷ (Denominator − Exclusions) | Percentage with HbA1c testing |

Five measure types: **Process** (service delivered), **Outcome** (clinical result), **Structural** (system capability), **Patient experience** (CAHPS), **Utilization** (resource consumption).

## 2. Continuous Enrollment Rules

| Rule | Definition |
|------|-----------|
| Measurement year | January 1 – December 31 of reporting year |
| Anchor date | Date member must be enrolled through (usually Dec 31) |
| Allowable gap | ≤45 days total gap permitted |
| Gap counting | Calendar days without coverage; multiple gaps summed |
| Enrollment source | Medical and/or pharmacy benefit, measure-dependent |

### Enrollment Evaluation Decision Tree

```
Is the member enrolled on the anchor date?
├── NO → Exclude from denominator
└── YES
    ├── Total gap days during measurement year?
    │   ├── ≤45 days → Continuously enrolled
    │   └── >45 days → Exclude from denominator
    └── Measure requires pharmacy benefit?
        ├── YES → Verify pharmacy enrollment separately
        └── NO → Medical enrollment sufficient
```

## 3. Exclusion Logic

| Category | Applies To | Condition |
|----------|-----------|-----------|
| Hospice | All measures | Hospice benefit or encounter |
| Deceased | All measures | Death during measurement year |
| ESRD | Diabetes, kidney | N18.6, dialysis codes |
| Organ transplant | Diabetes, kidney | Z94.x |
| Pregnancy | BP, diabetes | O00-O9A |
| Frailty + advanced illness | Age 66+, multiple | BOTH conditions required |

**Evaluation rules:**
1. Apply exclusions AFTER building the full denominator
2. Check the full measurement year for exclusion events
3. Frailty + advanced illness is compound — both must be present
4. Hospice overrides all other logic
5. Document which optional exclusions are applied

## 4. NCQA Audit Requirements

| Source | Priority | Use For |
|--------|----------|---------|
| Administrative claims | Primary | Denominator, exclusions, process numerators |
| Electronic clinical data (ECDS) | Primary (ECDS measures) | Lab results, vitals |
| Supplemental data | Secondary | Fills claims gaps (HIE lab results) |
| Medical record review | Tertiary | Validation, hybrid measures |

### Common Audit Findings

| Finding | Severity | Remediation |
|---------|----------|-------------|
| Supplemental data without source verification | High | Implement source validation |
| Enrollment gap calculation error | High | Revalidate against NCQA specs |
| Incorrect age calculation | Medium | Use age as of anchor date |
| Duplicate member counting | High | Deduplicate on member ID |
| Stale value sets | Medium | Update code sets annually |

## 5. Care Gap Prioritization

### Prioritization Decision Tree

```
Is the measure triple-weighted for Star Ratings?
├── YES → High priority baseline
│   ├── Member high-risk (Charlson ≥3 or LACE ≥10)?
│   │   ├── YES → Critical priority — immediate outreach
│   │   └── NO → High priority — standard outreach
│   └── SDOH barriers (Z-codes, high ADI)?
│       ├── YES → Assign care coordinator
│       └── NO → Automated reminder sufficient
└── NO → Standard priority
    ├── >6 months remaining in measurement year?
    │   ├── YES → Schedule in next outreach batch
    │   └── NO → Escalate if feasible
    └── Process measure (screening/test)?
        ├── YES → High closure probability — include
        └── NO → Outcome measure — coordinate with PCP
```

### Rate Interpretation

| Rate Range | Star Level | Action |
|------------|-----------|--------|
| ≥90th percentile | 5-star | Maintain current programs |
| 75th–89th | 4-star | Targeted improvement |
| 50th–74th | 3-star | Systematic outreach needed |
| 25th–49th | 2-star | Intensive intervention, root cause analysis |
| <25th | 1-star | Urgent remediation, leadership escalation |

## Common Mistakes

- **Wrong:** Calculating age as of data extraction date → **Right:** Use measure-specific anchor date (typically Dec 31)
- **Wrong:** Applying exclusions before building the full denominator → **Right:** Build complete eligible population first, then subtract
- **Wrong:** Excluding members with ≤45-day enrollment gaps → **Right:** HEDIS permits ≤45-day allowable gap
- **Wrong:** Mixing process and outcome sub-measures (e.g., HbA1c testing vs HbA1c <8%) → **Right:** Treat as separate rates
- **Wrong:** Using prior-year value sets without updating → **Right:** Update ICD-10/CPT/HCPCS annually
- **Wrong:** Counting members multiple times across enrollment segments → **Right:** Deduplicate on member ID
- **Wrong:** Submitting supplemental data without source documentation → **Right:** Validate with date, value, provider before submission
- **Wrong:** Treating all measures with equal priority → **Right:** Prioritize triple-weighted Star Rating measures (3× impact)

## When to Escalate

- Exclusion logic produces unexpected denominator drops (>10%)
- Before submitting quality data affecting reimbursement or accreditation
- Supplemental data sources change rates by >5 percentage points
