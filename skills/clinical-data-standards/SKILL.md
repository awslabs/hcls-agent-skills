---
name: clinical-data-standards
description: Reason about clinical data terminology standards — MedDRA hierarchy (LLT→PT→HLT→HLGT→SOC), ICD-10 code structure and grouping, SNOMED CT concept model, LOINC panel relationships, and mapping decisions between systems. Use when the user asks to code adverse events, map diagnoses to ICD-10, choose a coding granularity level, group AEs by SOC or PT, interpret SNOMED CT relationships, select LOINC codes for lab panels, convert between terminology systems, or decide when to aggregate at HLT vs PT level. Triggers include "MedDRA coding", "ICD-10 grouping", "SNOMED CT", "LOINC panel", "adverse event coding", "terminology mapping", "SOC table", "preferred term", "code hierarchy", "clinical coding", "AE frequency table", "diagnosis grouping", "lab code selection", "cross-walk between terminologies".
usage: Invoke when coding clinical events, choosing terminology granularity, mapping between MedDRA/ICD-10/SNOMED CT/LOINC, or building frequency tables from coded data.
version: 1.0.0
tags: [skill, category:reasoning, clinical-data, meddra, icd-10, snomed-ct, loinc, terminology, hcls]
---

# Clinical Data Terminology Standards

## Overview

This skill teaches the agent how to reason about clinical terminology systems — MedDRA, ICD-10, SNOMED CT, and LOINC — and the decisions involved in coding, grouping, and mapping clinical data. It does not generate pipeline code; it provides the domain knowledge needed to make correct coding and aggregation choices before any analysis begins.

Getting terminology wrong has direct consequences: miscoded adverse events hide safety signals, wrong ICD-10 granularity inflates or deflates prevalence estimates, and incorrect LOINC assignments break lab result interoperability. This skill encodes the rules, hierarchies, and decision frameworks that prevent those errors.

## Usage

Invoke this skill when the user:

- Needs to code verbatim adverse event text to MedDRA terms.
- Asks which level of MedDRA to use for frequency tables or signal detection.
- Wants to group diagnoses by ICD-10 codes and must choose 3-character vs 4-character granularity.
- Needs to understand SNOMED CT concept relationships for clinical findings or procedures.
- Must select LOINC codes for lab tests or understand panel composition.
- Is mapping between terminology systems (MedDRA ↔ ICD-10, SNOMED CT → ICD-10).
- Asks about regulatory expectations for AE coding in clinical trials.

The agent should respond by:

1. **Identifying the terminology system** appropriate for the data type and use case.
2. **Clarifying the granularity** — which hierarchy level to code at and which to report at.
3. **Applying the mapping rules** specific to the source and target systems.
4. **Flagging common pitfalls** — overcoding, undercoding, inappropriate aggregation.
5. **Stating regulatory context** when relevant (ICH E2B, FDA, EMA expectations).

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

### 1. MedDRA: The 5-Level Hierarchy

MedDRA (Medical Dictionary for Regulatory Activities) is the standard for coding adverse events, medical history, and indications in clinical trials and pharmacovigilance.

| Level | Abbreviation | Count (~v26) | Purpose |
|---|---|---|---|
| System Organ Class | SOC | ~27 | Broadest grouping (e.g., "Cardiac disorders") |
| High Level Group Term | HLGT | ~337 | Groups related HLTs within a SOC |
| High Level Term | HLT | ~1,740 | Groups related PTs by anatomy/mechanism |
| Preferred Term | PT | ~24,000 | Standard reportable term — the workhorse |
| Lowest Level Term | LLT | ~83,000 | Verbatim-level synonyms mapping to one PT |

#### The coding path

```
Verbatim AE text (from CRF)
  │
  ▼
LLT (closest match to verbatim)
  │
  ▼
PT (standard reportable term — one LLT maps to exactly one PT)
  │
  ▼
HLT → HLGT → SOC (for grouping and display)
```

Rules:

1. **Always code to LLT first**, then let the hierarchy derive the PT. Never skip to PT directly from verbatim text — the LLT layer captures synonyms and spelling variants.
2. **PT is the primary analysis level.** Frequency tables in clinical study reports (CSRs) list AEs at the PT level, grouped by SOC.
3. **One LLT → exactly one PT.** But one PT can belong to multiple SOCs (primary SOC assignment determines the default grouping).
4. **Primary SOC assignment** follows the ICH convention: etiology SOC takes precedence over manifestation SOC. "Drug-induced hepatitis" goes under "Hepatobiliary disorders" (manifestation) but its primary SOC is determined by MedDRA's primary path rules.
5. **Multi-axiality:** A PT can appear under multiple SOCs. Always use the **primary SOC** for frequency tables unless the protocol specifies otherwise.

#### When to aggregate above PT

| Scenario | Recommended level | Rationale |
|---|---|---|
| Standard AE frequency table (CSR) | PT within SOC | Regulatory expectation (ICH E3) |
| Signal detection across rare events | HLT or HLGT | Individual PTs too sparse; grouping reveals patterns |
| Standardized MedDRA Queries (SMQs) | SMQ (pre-defined) | Curated term groups for known safety topics (e.g., "Hepatic disorders") |
| High-level safety overview | SOC | Executive summary, not for detailed analysis |

#### Decision tree: MedDRA coding level

```
Start
│
├── Is this a standard CSR AE table?
│     └── Code at LLT → report at PT within primary SOC.
│
├── Are you looking for a safety signal across related terms?
│     ├── Does an SMQ exist for the topic?
│     │     └── Yes → Use the SMQ (narrow or broad scope as appropriate).
│     └── No SMQ → Aggregate at HLT. Document the grouping rationale.
│
├── Are individual PTs too rare to detect a signal?
│     └── Consider HLT or HLGT grouping, but report both grouped
│         and individual PT counts for transparency.
│
└── Executive safety summary only?
      └── SOC-level counts are acceptable, with PT detail available on request.
```

### 2. ICD-10: Code Structure and Grouping

ICD-10 (International Classification of Diseases, 10th Revision) is the standard for diagnosis coding in claims, EHR, and epidemiological studies.

#### Structure

```
Chapter (I–XXII)
  └── Block (e.g., E10–E14: Diabetes mellitus)
        └── Category — 3 characters (e.g., E11: Type 2 diabetes)
              └── Subcategory — 4–7 characters (e.g., E11.6: With complications)
                    └── Extension (e.g., E11.65: With hyperglycemia)
```

| Level | Example | Granularity |
|---|---|---|
| Chapter | Chapter IV: Endocrine diseases | Too broad for most analyses |
| Block | E10–E14 | Disease family grouping |
| 3-character category | E11 | Disease entity (Type 2 DM) |
| 4-character subcategory | E11.6 | Complication type |
| Full code | E11.65 | Specific manifestation |

#### Grouping decisions

The choice of granularity depends on the analysis goal:

| Analysis type | Recommended level | Example |
|---|---|---|
| Population prevalence study | 3-character category | E11 (all Type 2 DM) |
| Comorbidity index (Charlson, Elixhauser) | 3-character or block | Pre-defined code lists per condition |
| Specific outcome study | Full code (4–7 char) | E11.65 (hyperglycemia specifically) |
| Claims-based cohort definition | 3-character + exclusions | E11.* excluding E11.0 (with coma) |
| Cross-country comparison | Block level | ICD-10 blocks are more stable across national modifications |

#### Decision tree: ICD-10 grouping level

```
Start
│
├── Are you estimating disease prevalence or incidence?
│     └── 3-character category. Captures all subtypes.
│         Add block-level grouping if comparing across disease families.
│
├── Are you defining a specific clinical outcome?
│     └── Full code (4+ characters). Be explicit about which
│         manifestations qualify. Document inclusion/exclusion codes.
│
├── Are you building a comorbidity score?
│     └── Use the published code lists (Charlson/Elixhauser).
│         Do not invent your own groupings.
│
├── Are you comparing across countries or ICD-10 modifications?
│     └── Block level. National modifications (ICD-10-CM, ICD-10-GM)
│         diverge at the subcategory level.
│
└── Are you mapping from another system (MedDRA, SNOMED CT)?
      └── Map to 3-character first, then refine to subcategory
          only if the source system provides sufficient specificity.
```

#### ICD-10-CM vs ICD-10-WHO

- **ICD-10-CM** (US Clinical Modification): extends codes to 7 characters, adds laterality, encounter type (initial/subsequent/sequela). Used in US claims and EHR.
- **ICD-10-WHO**: the international base. Shorter codes, no laterality extensions.
- **Always specify which modification** you are using. A code valid in ICD-10-CM may not exist in ICD-10-WHO.

### 3. SNOMED CT: Concept Model

SNOMED CT (Systematized Nomenclature of Medicine — Clinical Terms) is the most comprehensive clinical terminology, used for clinical findings, procedures, substances, body structures, and organisms.

#### Core structure

- **Concepts**: unique identifiers (SCTIDs) representing clinical meanings.
- **Descriptions**: human-readable terms (Fully Specified Name, Preferred Term, Synonyms).
- **Relationships**: typed links between concepts.

#### Key relationship types

| Relationship | Meaning | Example |
|---|---|---|
| IS-A | Subsumption hierarchy | "Acute myocardial infarction" IS-A "Myocardial infarction" |
| Finding site | Where the finding is located | "Pneumonia" → finding site → "Lung structure" |
| Causative agent | What causes the condition | "Aspirin-induced asthma" → causative agent → "Aspirin" |
| Associated morphology | Structural change | "Adenocarcinoma of lung" → morphology → "Adenocarcinoma" |
| Method | How a procedure is performed | "Laparoscopic cholecystectomy" → method → "Laparoscopic approach" |

#### When to use SNOMED CT vs other systems

| Use case | Preferred system | Rationale |
|---|---|---|
| Clinical documentation in EHR | SNOMED CT | Rich concept model, supports clinical detail |
| Billing and claims | ICD-10 | Required by payers |
| Adverse event reporting | MedDRA | Regulatory requirement |
| Lab test ordering/results | LOINC | Standard for lab interoperability |
| Drug coding | RxNorm (US) / SNOMED CT | RxNorm for prescribing; SNOMED CT for substances |

#### SNOMED CT hierarchy navigation rules

1. **Use the IS-A hierarchy for subsumption queries.** To find "all types of diabetes," query descendants of concept 73211009 (Diabetes mellitus).
2. **Post-coordination** (combining concepts) is powerful but complex. Prefer pre-coordinated concepts when they exist.
3. **Reference sets** (refsets) define subsets for specific use cases (e.g., a national drug extension). Always check which refset applies to your jurisdiction.
4. **SNOMED CT → ICD-10 mapping** is maintained by SNOMED International. Use the official map; do not create ad hoc crosswalks.

### 4. LOINC: Lab Test Coding

LOINC (Logical Observation Identifiers Names and Codes) is the standard for identifying laboratory tests and clinical observations.

#### The 6-part naming convention

Every LOINC code is defined by six axes:

| Axis | Description | Example (Glucose, fasting, serum) |
|---|---|---|
| Component | What is measured | Glucose |
| Property | Type of measurement | MCnc (mass concentration) |
| Timing | Point vs over time | Pt (point in time) |
| System | Specimen type | Ser/Plas (serum or plasma) |
| Scale | Quantitative, ordinal, etc. | Qn (quantitative) |
| Method | How measured (optional) | — |

#### Panels

LOINC panels group related tests ordered together:

| Panel | LOINC code | Contains |
|---|---|---|
| CBC with differential | 57021-8 | WBC, RBC, Hgb, Hct, MCV, MCH, MCHC, Plt, differential |
| Basic Metabolic Panel | 51990-0 | Glucose, BUN, Creatinine, Na, K, Cl, CO2, Ca |
| Comprehensive Metabolic Panel | 24323-8 | BMP + albumin, bilirubin, ALP, ALT, AST, total protein |
| Lipid Panel | 24331-1 | Total cholesterol, HDL, LDL (calc), triglycerides |
| Hepatic Function Panel | 24325-3 | Albumin, bilirubin (total/direct), ALP, ALT, AST, total protein |

#### LOINC selection rules

1. **Match all six axes.** A glucose test on serum (quantitative, mass concentration) is a different LOINC code than glucose on urine (quantitative, mass concentration) or glucose on serum (ordinal).
2. **Prefer codes without a method axis** unless the method materially affects interpretation (e.g., calculated vs direct LDL).
3. **Use panel codes** when the full panel was ordered, and individual member codes for the component results within it.
4. **Check the LOINC status.** Codes can be ACTIVE, DEPRECATED, or DISCOURAGED. Only use ACTIVE codes.
5. **LOINC answers** (LA codes) provide standardized answer lists for ordinal observations (e.g., positive/negative/indeterminate).

### 5. Cross-System Mapping Decisions

Mapping between terminology systems is necessary but error-prone. Follow these rules:

#### MedDRA → ICD-10

| Scenario | Approach |
|---|---|
| AE term to diagnosis code | Map PT → ICD-10 3-character category. Refine to subcategory only if the PT provides sufficient specificity. |
| Medical history coding | Map at PT level; ICD-10 subcategory when the verbatim text supports it. |
| Concomitant conditions | Use the official MedDRA-to-ICD crosswalk where available. |

Rules:
1. **One MedDRA PT may map to multiple ICD-10 codes** (and vice versa). Document the mapping table and version.
2. **Never map LLT directly to ICD-10.** Always go through PT first — LLTs are synonyms, not distinct concepts.
3. **Granularity mismatch is expected.** MedDRA PTs are often broader than ICD-10 subcategories. Accept the loss of specificity or require additional clinical context.

#### SNOMED CT → ICD-10

- Use the **SNOMED International maintained map** (released with each SNOMED CT edition).
- The map provides target ICD-10 codes with map rules and priorities.
- **One SNOMED CT concept may map to multiple ICD-10 codes** (combination coding). Follow the map rules to select the correct target(s).
- **Do not reverse the map** (ICD-10 → SNOMED CT) without a dedicated reverse crosswalk — the forward map is many-to-one and loses information when inverted.

#### LOINC → local lab codes

- Most institutions maintain a local-to-LOINC mapping table (often called a "LOINC mapping" or "result code crosswalk").
- **Validate mappings by checking all six LOINC axes** against the local test definition. A common error is mapping a serum test to a urine LOINC code because the component name matches.
- **Panels vs components:** Map the panel order to the panel LOINC code, and each result line to its individual component LOINC code.

#### Decision tree: which mapping approach?

```
Start
│
├── Source is verbatim AE text?
│     └── Code to MedDRA (LLT → PT). Map to ICD-10 only if
│         the downstream system requires it.
│
├── Source is EHR diagnosis (free text or local code)?
│     ├── US system → Map to ICD-10-CM (billing) and SNOMED CT (clinical).
│     └── Non-US → Map to ICD-10-WHO or national modification.
│
├── Source is lab result?
│     └── Map to LOINC. Match all six axes. Use panel codes for orders.
│
├── Need to cross-walk between MedDRA and SNOMED CT?
│     └── Go through ICD-10 as an intermediary (MedDRA → ICD-10 → SNOMED CT)
│         or use UMLS concept mappings. Direct MedDRA ↔ SNOMED CT maps
│         are not officially maintained.
│
└── Building a research dataset combining claims + EHR + trial data?
      └── Define a canonical code system for each data element.
          Map all sources to the canonical. Document every mapping
          decision and version. Accept that some mappings are lossy.
```

### 6. Regulatory Context

| Standard | Required system | Context |
|---|---|---|
| ICH E2B(R3) | MedDRA | Individual Case Safety Reports (ICSRs) |
| ICH E3 | MedDRA | Clinical Study Reports — AE tables at PT within SOC |
| US claims (CMS) | ICD-10-CM, CPT, HCPCS | Billing and reimbursement |
| US EHR (ONC) | SNOMED CT, LOINC, RxNorm | Meaningful Use / Promoting Interoperability |
| CDISC SDTM | MedDRA (AE domain), dictionaries per domain | Clinical trial data submission to FDA |
| OMOP CDM | SNOMED CT (conditions), LOINC (measurements), RxNorm (drugs) | Observational research |

## When NOT to Use This Skill

- Assigning MedDRA codes for regulatory safety reports (needs trained medical coder)
- When coding requires clinical judgment about causality assessment
- ICD-10 coding for billing/reimbursement where legal liability applies

## When to Escalate to a Human Expert

- When a term maps to multiple PT candidates with different SOCs
- Cross-walk decisions that affect regulatory submission acceptance
- When local coding conventions override international standards

## Common Mistakes

- **Wrong:** Coding adverse events directly to PT, skipping the LLT layer
  **Right:** Always code verbatim text to LLT first, then let the hierarchy derive the PT
  **Why:** The LLT layer captures synonyms and spelling variants — skipping it risks inconsistent coding when different verbatim texts describe the same concept

- **Wrong:** Using secondary SOC for AE frequency tables
  **Right:** Always use the primary SOC for frequency tables unless the protocol explicitly specifies otherwise
  **Why:** Multi-axial PTs appear under multiple SOCs — mixing primary and secondary inflates apparent AE counts and confuses signal detection

- **Wrong:** Aggregating at HLT level without documenting justification
  **Right:** Only aggregate above PT when individual terms are too sparse for signal detection; always show both grouped and ungrouped PT counts
  **Why:** HLT grouping hides individual PT signals that may represent distinct safety concerns

- **Wrong:** Applying ICD-10-CM codes in a non-US context
  **Right:** Specify which ICD-10 modification you are using; use ICD-10-WHO or the appropriate national modification for non-US data
  **Why:** ICD-10-CM extensions (laterality, encounter type) do not exist in ICD-10-WHO — codes may be invalid or misinterpreted

- **Wrong:** Grouping ICD-10 at 3-character level for specific outcome studies
  **Right:** Use full codes (4+ characters) when the outcome is a specific manifestation; document inclusion/exclusion codes explicitly
  **Why:** E11 includes all Type 2 DM complications — if the outcome is "Type 2 DM with hyperglycemia," only E11.65 is correct

- **Wrong:** Reversing the SNOMED CT → ICD-10 map to create an ICD-10 → SNOMED CT crosswalk
  **Right:** Use a dedicated reverse crosswalk or UMLS CUI-based mappings; never invert the forward map
  **Why:** The forward map is many-to-one — reversing it creates ambiguous one-to-many mappings without the map rules to resolve them

- **Wrong:** Matching LOINC codes by component name alone
  **Right:** Verify all six LOINC axes (component, property, timing, system, scale, method) match the local test definition
  **Why:** Two LOINC codes can share the same component but differ in system (serum vs urine), property, or scale — partial matching produces wrong assignments

- **Wrong:** Using deprecated LOINC codes without checking status
  **Right:** Always check the LOINC STATUS field and replace deprecated codes with their active successors
  **Why:** Deprecated codes break interoperability and may not be recognized by receiving systems

- **Wrong:** Creating ad hoc terminology crosswalks instead of using official maps
  **Right:** Use curated maps from SNOMED International, NLM, or MSSO; document the map version used
  **Why:** Ad hoc mappings introduce inconsistencies, are not reproducible, and diverge from regulatory expectations

- **Wrong:** Ignoring MedDRA version differences when combining data across studies
  **Right:** Document the MedDRA version used for each study; reconcile terms that were added, merged, or deprecated across versions
  **Why:** PTs are added, merged, and deprecated across versions — a term valid in v25 may be deprecated in v26, causing data loss or miscounting

- **Wrong:** Confusing LOINC panel codes with component codes when storing results
  **Right:** Use the panel code for the order and individual component LOINC codes for each result within the panel
  **Why:** Storing a glucose result under the CBC panel code is semantically wrong and breaks downstream aggregation and interoperability

- **Wrong:** Mapping MedDRA directly to SNOMED CT without an intermediary
  **Right:** Use ICD-10 as an intermediary (MedDRA → ICD-10 → SNOMED CT) or use UMLS CUI-based mappings; document the mapping path
  **Why:** No official direct MedDRA ↔ SNOMED CT crosswalk exists — direct mapping produces unvalidated, irreproducible results

## References

- MedDRA Introductory Guide: https://www.meddra.org/how-to-use/support-documentation
- ICH E2B(R3) guideline: https://database.ich.org/sites/default/files/E2B_R3__Guideline.pdf
- ICD-10-WHO: https://icd.who.int/browse10/2019/en
- ICD-10-CM: https://www.cms.gov/medicare/coding-billing/icd-10-codes
- SNOMED CT Starter Guide: https://confluence.ihtsdotools.org/display/DOCSTART
- SNOMED CT to ICD-10 Map: https://www.snomed.org/snomed-ct/Use-SNOMED-CT/maps
- LOINC Users' Guide: https://loinc.org/kb/users-guide/
- CDISC SDTM Implementation Guide: https://www.cdisc.org/standards/foundational/sdtm
- OMOP CDM Vocabulary: https://ohdsi.github.io/CommonDataModel/
