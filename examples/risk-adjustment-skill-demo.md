# Risk Adjustment Skill Demo: Skilled vs Unskilled Comparison

## Purpose

Demonstrates how the `risk-adjustment` skill produces consistent, production-ready pipeline code versus a base model's prose-only explanation. Modern LLMs don't refuse healthcare operations questions — the skill's value is **precision, consistency, and actionable code**.

## Why This Skill Matters: Domain Context

### The Problem: Risk Adjustment Is a $400B+ Revenue Mechanism With Zero Tolerance for Error

CMS-HCC risk adjustment determines how much Medicare Advantage plans get paid per member. A single missed HCC can mean $3,000–$15,000 in lost annual revenue per member. A single incorrect hierarchy resolution can trigger OIG audit findings and repayment demands. This isn't academic — it's the financial engine of managed care.

### Why a Generic LLM Gets This Wrong

1. **Hierarchy resolution is non-obvious.** The V24 model has 86 HCCs organized into ~30 disease hierarchies. When a member has both HCC 85 (systolic heart failure) and HCC 86 (diastolic heart failure), only 85 pays. A generic model may not know which supersedes which, or may double-count — a compliance violation that triggers audit.

2. **The ICD-10-to-HCC crosswalk changes annually.** CMS publishes updated mappings each payment year. E11.65 (Type 2 DM with hyperglycemia) maps to CC 18 in V24 but the base model may reference older mappings or confuse CC vs HCC numbering. Wrong mapping = wrong payment = audit risk.

3. **Provider type filtering is a regulatory requirement.** Only diagnoses from qualifying provider types (MD, DO, NP, PA, CNS) count for risk adjustment. A lab-only diagnosis or a diagnosis from a non-qualifying provider is invalid for RAF calculation. Most LLMs don't know this rule exists.

4. **Rx-proxy gap detection requires drug-to-condition-to-HCC reasoning chains.** Identifying that donepezil → probable dementia → HCC 51/52 → missing diagnosis requires linking pharmacy claims to clinical conditions to payment categories. This three-hop inference is where generic models hallucinate or miss gaps entirely.

5. **Disease interactions add non-linear RAF components.** Diabetes + CHF together pay more than the sum of their individual HCCs. Missing an interaction term means underestimating member acuity and leaving revenue on the table.

### What the Skill Encodes

The skill encodes the **exact V24 hierarchy map**, the **qualifying provider filter**, the **crosswalk logic**, and the **Rx-proxy reasoning chains** — all as deterministic, auditable Python code. This matters because:

- **Auditability**: CMS and RADV audits require that every RAF calculation be reproducible and traceable. Code that follows a consistent pattern is auditable; ad-hoc prose explanations are not.
- **Consistency**: A health plan running risk adjustment across 500K members needs the same logic applied identically every time. The skill ensures the agent always produces the same pipeline structure.
- **Compliance**: Incorrect hierarchy resolution or invalid provider types can trigger False Claims Act liability. The skill's encoded rules prevent these errors by design.

---

## Prompt

```
Given these member diagnoses, calculate the CMS-HCC V24 RAF score with hierarchy resolution:

member_id,icd10,service_date,provider_type
M001,E1165,2025-03-01,MD
M001,I5023,2025-04-15,DO
M001,I5033,2025-04-15,DO
M001,N1830,2025-05-01,NP
M001,C5011,2025-02-10,MD

Show me the full pipeline: crosswalk mapping, hierarchy resolution, and final RAF score. Also identify any Rx-proxy coding gaps for this member.
```

## How to Identify the Skilled Response

| Signal | With Skill | Without Skill |
|--------|-----------|---------------|
| **Function names** | `map_diagnoses_to_ccs()`, `resolve_hierarchies()`, `calculate_raf()`, `identify_rx_gaps()` | Generic descriptions or ad-hoc code |
| **Response format** | Code-first, then explanation. Ends with "Gotchas" section | Explanation-first, tables only, no executable code |
| **Hierarchy dict** | `V24_HIERARCHIES = {85: [86, 87], 17: [18, 19], ...}` | Prose description of hierarchy rules |
| **Provider filter** | `{"MD", "DO", "NP", "PA", "CNS"}` qualifying set | May omit or use different filter |
| **Rx-proxy gaps** | `identify_rx_gaps()` with specific drug→condition→HCC mapping | Creative clinical reasoning but no structured function |
| **Crosswalk mapping** | E1165 → CC 18 (diabetes w/ chronic complications) | May map differently (e.g., E1165 → HCC 19) |
| **Output structure** | `inputs → working code → parameters → gotchas` | Varies per run |

## Skilled Response (with `risk-adjustment` skill)

The skilled agent produces executable Python calling the skill's prescribed functions:

```python
# Step 1: Crosswalk
mapped = map_diagnoses_to_ccs(dx_df, xwalk)

# Step 2: Hierarchy resolution
hccs = resolve_hierarchies(mapped[["member_id", "cc"]])

# Step 3: RAF calculation
scores = calculate_raf(demo_df, hccs)

# Step 4: Rx-proxy gap detection
gaps = identify_rx_gaps(rx_df, dx_df, year=2025)
```

Key outputs:
- CC 85 (HF systolic) supersedes CC 86 (HF diastolic) → only 85 survives
- Surviving HCCs: {12, 18, 85, 138}
- RAF score: ~2.465 (with interactions: diabetes+CHF, CHF+renal)
- Coding gap: donepezil on Rx without dementia diagnosis → HCC 51/52 opportunity

Ends with **Gotchas** section covering:
- I50.23 vs I50.33 hierarchy resolution
- CKD staging (N18.30 vs N18.4/N18.5 for higher CC)
- Donepezil off-label use caveat

## Unskilled Response (without skill)

The base model produces a prose/table explanation:
- No executable code — only formatted tables
- Different coefficient values (uses different V24 reference)
- Invents Rx gaps not in the skill's framework (AFib, depression, anticoagulants)
- No function names matching the skill's API
- May map E1165 → HCC 19 instead of CC 18
- Clinically reasonable but not production-pipeline code

## Key Takeaway

> Skills don't unlock forbidden knowledge — they give the agent expert-level precision and production-ready output instead of generic answers. The skilled response is copy-paste-ready; the unskilled response requires refactoring into a pipeline.

## Evaluation Results (v4)

The `risk-adjustment` skill achieved:
- **100% win rate** (10/10 prompts)
- **Cohen's d: +1.10** (large effect)
- **+8.0 critical thinking delta** (highest single-dimension score in the eval)
- **+40% improvement** from v3 → v4
