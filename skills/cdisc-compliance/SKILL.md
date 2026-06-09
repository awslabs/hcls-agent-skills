---
name: cdisc-compliance
description: >
  Reason about CDISC SDTM and ADaM implementation for regulatory submissions. Use when
  the user asks about SDTM domain mapping, ADaM dataset design, controlled terminology
  versioning, define.xml completeness, FDA or PMDA submission requirements, query
  prioritization by clinical impact, SUPPQUAL usage, or CDISC compliance review. Triggers
  include "SDTM mapping", "ADaM dataset", "CDISC compliance", "controlled terminology",
  "define.xml", "FDA submission data", "PMDA submission", "SDTM domain", "ADSL", "ADAE",
  "ADLB", "BDS structure", "SUPPQUAL", "RELREC", "value-level metadata", "CDISC CT",
  "regulatory submission data standards", "eCTD datasets", "SDTM 3.3", "ADaM 1.1",
  "query prioritization", "clinical data review".
usage: Invoke when evaluating CDISC compliance or planning regulatory submission datasets.
version: 1.0.0
tags: [skill, category:reasoning, cdisc, sdtm, adam, regulatory, clinical-data, fda, hcls]
---

# CDISC Compliance — Reasoning Skill

## Overview

You are an expert in CDISC data standards for regulatory submissions. When the user
asks about SDTM/ADaM implementation, controlled terminology, define.xml, or submission
requirements, apply the decision frameworks below.

## Usage

- Invoke when evaluating CDISC SDTM or ADaM compliance for regulatory submissions
- Use when planning define.xml content, SUPPQUAL decisions, or domain mapping
- Activate for FDA/PMDA submission data standards questions or Pinnacle 21 triage

---

## Core Concepts

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## 1. Tricky Domain Mapping Decision Tree

These are the non-obvious mappings where teams make mistakes:

```
Oncology tumor data?
├─ Identifying tumor location/characteristics → TU (one record per identified lesion)
├─ Measuring a lesion (diameter, volume) → TR (one record per measurement per visit)
└─ Evaluating overall response (CR/PR/SD/PD) → RS (one record per assessment per visit)
    Rule: TU identifies it, TR measures it, RS evaluates the patient.

Medication data?
├─ Is it the study drug or protocol-mandated therapy? → EX (Exposure)
├─ Is it a non-study medication taken during the study? → CM
└─ Ambiguous (e.g., rescue medication specified in protocol)?
   ├─ Protocol-required with dosing rules → EX
   └─ Taken at investigator/subject discretion → CM

Pre-existing condition that worsens on study?
├─ Record in MH (with MHENDTC = blank or ongoing)
├─ ALSO record in AE (with AEPRESP = "Y" to flag pre-existing)
└─ Link via RELREC if needed for traceability

Questionnaire / PRO / scale data?
├─ Uses a published validated instrument (e.g., EQ-5D, PHQ-9) → QS
├─ Sponsor-designed assessment with scoring → QS (with sponsor-defined TESTCDs)
└─ Single ad-hoc question not part of a scale → FA (Findings About)
```

## 2. SUPPQUAL Anti-Pattern Checklist

### NEVER put in SUPPQUAL (move to parent domain or use standard variable):
- Timing variables (--STDTC, --ENDTC, --DUR, --VISITNUM)
- Result qualifiers (--LOC, --LAT, --DIR, --METHOD)
- Standard identifiers (--GRPID, --REFID, --SPID)
- Any variable defined in the current SDTM IG for that domain

### ALWAYS appropriate for SUPPQUAL:
- Free-text verbatim fields not fitting standard variables
- Site-specific or country-specific collected fields
- Non-standard data collected on CRF with no IG slot
- Sponsor-defined flags needed for analysis traceability

### Red flags indicating domain redesign needed:
- **>5 SUPPQUAL records per subject per domain** → consider a custom domain or FA
- **SUPPQUAL variable used in derivations** → promote to parent domain
- **Same QNAM across >80% of subjects** → this is a standard variable in disguise

### SUPPQUAL rules:
- QNAM ≤8 characters, unique within parent domain
- QLABEL ≤40 characters
- QORIG: CRF | DERIVED | ASSIGNED | PROTOCOL

## 3. SDTM Version Requirements

| Agency | Minimum SDTM | Minimum IG | Notes |
|---|---|---|---|
| FDA | 3.3 | 3.3 | Required for NDA/BLA since 2017 |
| PMDA | 3.2 | 3.2 | Accepts 3.3; 3.4 encouraged |
| EMA | 3.2 | 3.2 | Not yet mandatory but recommended |
| Health Canada | 3.3 | 3.3 | Aligned with FDA |

## 4. ADaM Rules (Non-Obvious)

1. **Traceability is mandatory.** Every derived variable must trace to SDTM via SRCDOM/SRCVAR/SRCSEQ.
2. **DTYPE flags derived records.** Imputed/derived records (LOCF, WOCF) require DTYPE.
3. **AVAL and BASE must share units.** CHG = AVAL − BASE is meaningless otherwise.
4. **Value-level metadata required for BDS** where variable attributes differ by PARAMCD — define.xml must include where clauses for each parameter.
5. **Computational methods required** for every derived variable in define.xml.

## 5. define.xml Value-Level Metadata

For BDS datasets, define.xml must specify per-PARAMCD:
- **Origin** (CRF vs Derived) — may differ by parameter
- **Data type and length** — AVAL is always numeric, but AVALC length varies
- **Codelist reference** — only for parameters with categorical AVALC
- **Computational method** — derivation algorithm specific to that PARAMCD
- **Where clause** — the condition identifying which records the metadata applies to

Missing value-level metadata is a **P21 Error** for any BDS dataset with >1 PARAMCD.

## 6. Query Prioritization by Clinical Impact

| Priority | Data Category | Examples | Resolution SLA |
|---|---|---|---|
| P1 — Critical | Safety data | SAE dates, AE causality, death records | 24–48 hours |
| P2 — High | Efficacy endpoints | Primary/secondary endpoint values, visit dates | 3–5 business days |
| P3 — Medium | Key demographics | Randomization data, stratification factors | 5–7 business days |
| P4 — Low | Administrative | Informed consent dates, site identifiers | 10 business days |

**Escalation rules:**
- Queries affecting **multiple subjects** → escalate one priority level
- **Systematic errors** (wrong unit for all subjects at a site) → P1 regardless of data type
- Safety queries **block database lock** — resolve before anything else

## 7. FDA vs PMDA Submission Differences

| Aspect | FDA | PMDA |
|---|---|---|
| SDTM required | Yes (NDA/BLA) | Yes (since 2020 for new drugs) |
| ADaM required | Yes | Recommended, not mandatory |
| define.xml | 2.0+ required | 2.0+ required |
| CT version policy | Latest at time of submission | Pin at study start |
| Dataset size limit | 5 GB per dataset (eCTD) | No explicit limit |
| Blanking rules | Permissible null | Prefer explicit "NOT DONE" |
| Reviewer's Guide | Required (cSDRG, aSDRG) | Required |

**Key gotcha:** FDA accepts null for "not done" assessments; PMDA expects --STAT = "NOT DONE" with --REASND populated. Plan for PMDA requirements upfront if dual submission.

## When NOT to Use This Skill
- Pre-clinical or discovery-phase data not destined for regulatory submission — CDISC standards add overhead without value
- Non-regulatory submissions (e.g., internal research databases, publications) — use domain-appropriate formats instead
- eCTD module assembly or submission gateway mechanics — this skill covers data standards, not submission logistics

## When to Escalate to Human Expert
- Ambiguous domain mapping where the variable could legitimately belong to two SDTM domains — requires sponsor standards team decision
- Novel endpoint types not covered by existing CDISC controlled terminology — requires CDISC SHARE consultation or sponsor extension request
- Regulatory agency feedback contradicts CDISC Implementation Guide — requires regulatory affairs interpretation

## 8. Common Compliance Mistakes (Severity-Ranked)

1. **Wrong:** Submitting a dataset without USUBJID
   **Right:** Include USUBJID as a required variable in every SDTM and ADaM dataset
   **Why:** Missing USUBJID breaks all cross-dataset joins — Critical severity

2. **Wrong:** Creating DM domain without populating RFSTDTC
   **Right:** Always populate RFSTDTC (reference start date) in DM from the first dose or randomization date
   **Why:** All study day (--DY) calculations depend on RFSTDTC — Critical severity

3. **Wrong:** Building ADSL without TRT01A/TRT01P variables
   **Right:** Always include TRT01A (actual treatment) and TRT01P (planned treatment) in ADSL
   **Why:** No treatment assignment means no analysis population can be defined — Critical severity

4. **Wrong:** Creating a non-standard (custom) domain without documenting it in define.xml and the Reviewer's Guide
   **Right:** Document all non-standard domains with full metadata in define.xml and explain rationale in cSDRG
   **Why:** Reviewers cannot interpret undocumented domains, causing review delays — High severity

5. **Wrong:** Placing standard SDTM variables (timing, result qualifiers, identifiers) in SUPPQUAL
   **Right:** Use the parent domain's standard variables (--STDTC, --LOC, --METHOD, --GRPID, etc.) as defined in the IG
   **Why:** Triggers P21 Error and signals poor domain mapping knowledge — High severity

6. **Wrong:** Omitting value-level metadata for BDS datasets with multiple PARAMCDs
   **Right:** Include where-clause-based value-level metadata in define.xml for every PARAMCD in BDS datasets
   **Why:** Missing value-level metadata is a P21 Error; define.xml is incomplete without it — High severity

7. **Wrong:** Using codelist values not present in the pinned controlled terminology version
   **Right:** Pin one CT version at study start and use only values from that version (or document sponsor extensions for extensible codelists)
   **Why:** Triggers P21 Warning CT2003 and may delay regulatory review — Medium severity

8. **Wrong:** Recording dates with inconsistent precision across records (mixing full dates with partial dates without clear rules)
   **Right:** Define date precision rules in the SAP and apply consistent imputation logic documented in define.xml
   **Why:** Inconsistent precision complicates imputation and introduces errors in study day calculations — Medium severity

## 9. Date Handling Gotchas

### Study Day Calculation

```
--DY = date − RFSTDTC + 1  (if date ≥ RFSTDTC)
--DY = date − RFSTDTC      (if date < RFSTDTC)
```

**There is no Day 0.** Day −1 is the day before RFSTDTC; Day 1 is RFSTDTC itself. This off-by-one is the #1 date calculation error in submissions.

### Date Imputation Rules for ADaM

| Scenario | Imputation Rule | DTYPE Flag |
|---|---|---|
| Missing day, AE start | Impute to 1st of month | Set ASTDT, document imputation |
| Missing month and day | Impute to January 1st | Document in define.xml |
| Missing end date, ongoing AE | Use data cutoff date | Flag as ongoing (AENDY missing) |
| Partial date comparison | Conservative: earliest for start, latest for end | Document algorithm |

**Rule:** Every imputed date requires a corresponding imputation flag variable (e.g., ASTDTF, AENDTF) with values Y (imputed) or blank (not imputed).

## 10. Pinnacle 21 Triage Decision Tree

```
P21 finding received
├─ Severity = Error
│  └─ MUST fix before submission (no exceptions)
├─ Severity = Warning
│  ├─ Affects safety/efficacy data? → Fix
│  ├─ Cosmetic or structural only? → Document justification in Reviewer's Guide
│  └─ Systematic across all subjects? → Fix (reviewer will notice)
└─ Severity = Notice
   ├─ Easy fix (<1 hour)? → Fix
   └─ Complex or low-impact? → Skip, document if asked
```

### Top P21 Rules by Fix Priority

| Rule ID | Description | Severity | Action |
|---|---|---|---|
| SD0009 | USUBJID not consistent with DM | Error | Fix immediately — breaks traceability |
| SD0083 | Missing required variable | Error | Fix — submission will be rejected |
| SD1001 | Invalid date/time format | Error | Fix — ISO 8601 non-negotiable |
| CT2001 | CT mismatch (value not in codelist) | Warning | Fix if non-extensible codelist; document if sponsor extension |
| CT2003 | CT version inconsistency | Warning | Usually fix — indicates mixed CT versions |
| SD1020 | Value not found in external codelist | Warning | Fix if standard term exists; extend if legitimate |
| AD0252 | ADSL missing required variables | Error | Fix — ADSL completeness is critical |
| AD0322 | BDS record without PARAMCD | Error | Fix — BDS is unusable without PARAMCD |
| SD0070 | Duplicate records | Warning | Investigate — may be valid (e.g., bilateral findings) |
| SD1015 | Inconsistent values across datasets | Warning | Fix if traceability broken; document if by design |

## 11. Controlled Terminology Rules

| Rule | Description |
|---|---|
| Pin CT version at study start | One CT version for entire study |
| Document in define.xml | Specify package version (e.g., 2024-03-29) |
| Never mix versions | Mixing CT within a study → P21 Warning CT2003 |
| Non-extensible codelists | Use ONLY CDISC-defined values (e.g., SEX, AEOUT) |
| Extensible codelists | Sponsor values allowed but must be documented |
| Map legacy terms on upgrade | Create mapping table; never silently change coded values |
