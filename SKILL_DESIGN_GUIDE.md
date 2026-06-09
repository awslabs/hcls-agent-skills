---
title: Skill Design Guide
inclusion: fileMatch
fileMatchPattern: 'skills/*/SKILL.md'
---

# Skill Design Guide

What makes a skill actually improve agent responses? This guide distills patterns from our [410-prompt pairwise evaluation](./eval/TECHNICAL_REPORT.md) (v3), a structural audit of all 38 skills, and community best practices from the [Agent Skills standard](https://agentskills.io).

**Method:** Every SKILL.md was audited for 10 structural metrics (line count, code blocks, decision trees, tables, gotcha items, numbered steps, numeric thresholds, description length, trigger keywords, output format sections). These were cross-referenced with per-skill win rates, Cohen's d, and per-dimension deltas from the pairwise evaluation.

---

## The Core Principle

**Add what the agent lacks. Omit what it already knows.**

The single strongest predictor of skill impact is whether the content teaches something the base model gets wrong without help. Skills that recite well-known material (standard R/Python recipes, textbook protocols) show zero or negative benefit. Skills that encode niche decision procedures, exact thresholds, and domain-specific gotchas show 80-100% win rates.

Ask yourself: *"Would the agent get this wrong without this instruction?"* If no, cut it.

---

## The Coherence Trade-Off

The most important finding from the full audit: **skills improve critical thinking (+3.4, d=0.65) but regress coherence (-0.4, d=-0.08)**. This isn't a bug — it's a fundamental tension.

- 38 of 41 skills improve critical thinking (even skills that lose overall)
- 22 of 41 skills regress on coherence
- The worst coherence offenders: quality-measure-specification (-7.2), proteomics-analysis (-5.0), cdisc-compliance (-4.5)

**What causes coherence regression:**
- Too many reference tables competing for attention (cdisc-compliance: 20 tables → -4.5 coherence)
- Encyclopedia-mode skills that cover 5+ topics shallowly
- Skills that add bulk without clear response structure

**What preserves coherence while adding value:**
- Output format sections that prescribe response structure (10 skills have these; avg coherence: +0.3)
- Focused scope — one decision domain per skill
- Concise instruction: "respond with X structure" rather than dumping reference material

**Design rule:** For every piece of content you add, ask: "Does this help the agent think better, or does it just make the response longer?"

---

## Patterns of High-Performing Skills

From the full audit of all 17 skills with ≥80% win rate.

### 1. Teach Procedures, Not Facts

All 17 top-tier skills encode **ordered decision procedures** — numbered steps with branch points. The correlation is stark:

| Metric | Top tier (≥80% win) | Bottom tier (≤50% win) |
|--------|---------------------|------------------------|
| Avg numbered steps | 19.4 | 4.3 |
| Has decision trees | 12/17 (71%) | 0/7 (0%) |
| Avg gotcha items | 10.6 | 7.1 |

**Good** (genomic-variant-interpretation, 90% win):
```
1. Check population frequency (gnomAD AF)
2. If AF < 0.0001 → supports pathogenic (PM2)
3. If AF > 0.01 → strong benign (BS1)
4. Apply computational predictors: REVEL > 0.644 pathogenic, < 0.290 benign
5. Check ClinVar: ≥2 stars = reliable, 1 star = supporting only
```

**Bad** (proteomics-analysis, 30% win):
```
Proteomics analysis involves normalization, imputation, and differential expression.
Use limma for DE analysis. Use clusterProfiler for enrichment.
```

### 2. Use Exact Numeric Thresholds

33 of 38 skills contain explicit thresholds. But the *density* matters — top performers average 8+ distinct thresholds; bottom performers have 2-3 generic ones (like "adj.p < 0.05" which the model already knows).

**High-value thresholds** (niche, not in training data):
| Skill | Thresholds |
|-------|-----------|
| genomic-variant-interpretation | REVEL > 0.644, CADD > 25.3, gnomAD FAF < 0.0001 |
| claims-billing-rules | Global surgery 0/10/90-day, >5% error rate flags fraud |
| rwd-cohort-analysis | SMD < 0.1, PDC ≥ 0.80, F-stat > 10 for IV strength |
| risk-adjustment-strategy | 67%/33% V24/V28 blend, HCC 8 coefficient 2.484 |
| pa-clinical-policy | 72h expedited review, ≥90% gold card threshold |

**Low-value thresholds** (model already knows):
- `adj.p < 0.05` (proteomics-analysis)
- `|log2FC| > 1` (proteomics-analysis)
- `FDR < 0.05` (multi-omics-pipeline)

### 3. Include Decision Trees (Reasoning Skills)

Decision trees appear in 18 skills — exclusively reasoning skills. They correlate with higher critical thinking deltas:

- Skills with ≥3 decision trees: avg critical thinking d = 0.95
- Skills with 0 decision trees: avg critical thinking d = 0.48

The most effective format:
```
Is the procedure in the global surgery period?
├─ Yes → Is it a related complication?
│  ├─ Yes → Not separately billable
│  └─ No → Append modifier 79
└─ No → Bill normally
```

**For pipeline skills:** Use parameter selection tables instead of trees:
```
| Sample size | Normalization | Rationale |
|-------------|---------------|-----------|
| n < 10      | Median centering | Robust to outliers |
| n 10-50     | Quantile | Assumes similar distributions |
| n > 50      | VSN | Variance-stabilizing, handles heteroscedasticity |
```

### 4. Document Common Mistakes (Gotchas)

36 of 38 skills have a Common Mistakes section (94.7%) — it's the most universal structural element. But quantity and specificity vary:

| Tier | Avg gotcha items | Example |
|------|-----------------|---------|
| Top (≥80% win) | 10.6 | "Do NOT use gnomAD total AF; use filtering AF (FAF)" |
| Middle (60-70%) | 8.1 | "Do NOT impute before normalization" |
| Bottom (≤50%) | 7.1 | "Ensure proper quality control" (too vague) |

**Effective gotchas are specific and actionable:**
```
- **Wrong:** Treating ClinVar 1-star entries as definitive evidence
  **Right:** 1-star = supporting only; require ≥2 stars for strong evidence
```

**Ineffective gotchas are generic:**
```
- Ensure data quality before analysis
- Check for batch effects
```

### 5. Prescribe Output Format

10 skills include explicit output format or response structure sections. These skills average +0.3 coherence delta vs -1.2 for skills without. This is the **primary defense against coherence regression**.

Examples:
- **translational-research:** 10-point evaluation checklist the agent must apply
- **biomarker-discovery:** 5-step ordered response (clarify intent → audit data → recommend design → name leakage → define "validated")
- **ml-researcher:** 6-step mental model + 11-item readiness checklist
- **multi-omics-integration:** 8-item mandatory reporting list

**Template:**
```
## Response Structure
When answering, follow this order:
1. [Framework selection — which approach applies]
2. [Key decision with thresholds]
3. [Implementation specifics]
4. [Caveats and limitations]
```

**Internal reasoning markers (v1.2):** For reasoning skills with decision trees, add an explicit "do not narrate" instruction to the Response Format section. This prevents scratchpad leakage where the agent walks through decision trees visibly in output, costing coherence wins. Example:

```
The decision trees and detection methodologies in this skill are for internal reasoning only.
Apply them to reach your conclusion, but do not reproduce them in your response. Present only
the final determination with supporting evidence.
```

### 6. Front-Load Framework Selection

Top skills disambiguate *which approach to use* before diving into details. This prevents the agent from applying the wrong framework:

```
## First: Choose Your Framework
- Germline variant → ACMG/AMP 2015 (28 criteria)
- Somatic variant → AMP/ASCO/CAP 2017 (4 tiers)
- Pharmacogenomic → CPIC levels of evidence
```

### 7. Include Worked Examples with Realistic Data

10 skills include worked examples with realistic values (not placeholders). These skills average 75% win rate vs 67% for skills without.

**Good** (ehr-data-parsing, 100% win):
```
MSH|^~\&|LAB|HOSP|EHR|HOSP|20240115||ORU^R01|MSG001|P|2.5.1
PID|||MRN12345^^^HOSP||DOE^JANE||19800315|F
OBX|1|NM|2345-7^Glucose^LN||126|mg/dL|70-100|H|||F
```

**Good** (risk-adjustment, 80% win):
```
HCC 19 (Diabetes w/o Complication): coefficient 0.302
HCC 18 (Diabetes w/ Chronic Complication): coefficient 0.302 + hierarchy supersedes HCC 19
```

### 8. Reference External Databases with Query Patterns

13 skills reference specific databases with actionable thresholds. This is particularly effective for reasoning skills where the agent needs to know *how to interpret* database results:

```
# Good — actionable query pattern
ClinVar: ≥3 stars = strong evidence; check review status date (pre-2016 = stale)
gnomAD: use v4; check coverage depth at position; use FAF not raw AF
OpenTargets: require association score >0.5 for serious consideration
```

```
# Bad — just naming the database
Check ClinVar for variant classification.
```

### 9. Specify Tool Versions

10 skills explicitly specify versions and warn against older ones. This correlates with pipeline skill success because version-specific flags are exactly what the base model gets wrong:

```
# Good — version-specific
GATK4 HaplotypeCaller (not GATK3 UnifiedGenotyper)
BWA-MEM2 (not BWA-MEM — 2x faster, same output)
gnomAD v4 (not ExAC or 1000 Genomes as primary)
```

---

## Patterns of Low-Performing Skills

From the full audit of all 7 skills with ≤50% win rate.

### 1. Reciting Well-Known Code Recipes

The #1 cause of skill failure. `proteomics-analysis` (30% win) is 90% limma/DEP/clusterProfiler code that the base model already generates correctly. `rna-seq-analysis` (60% win, negative delta) is standard STAR/Salmon/DESeq2 commands.

**Test:** Run 3 prompts without the skill. If the base model produces equivalent code, the skill content is redundant.

### 2. Code Without Decision Logic

Pipeline skills that are mostly code blocks with no guidance on *when to use which approach*:

- `proteomics-analysis`: 11 code blocks, 0 decision trees, 6 numbered steps → 30% win
- `edc-data-validation`: 9 code blocks, 0 decision trees, 6 numbered steps → 30% win
- `variant-calling`: 11 code blocks, 0 decision trees, 8 numbered steps → 50% win

Compare with successful pipeline skills:
- `ehr-data-parsing`: 11 code blocks, 0 decision trees, BUT 10 gotcha items + realistic worked examples → 100% win
- `rwd-cohort-analysis`: 16 code blocks, 0 decision trees, BUT 10 gotcha items + 16 numbered steps → 80% win

**The difference:** Successful pipeline skills pair code with decision context and gotchas. Failed ones are just code dumps.

### 3. Encyclopedia Mode (Too Broad, Too Shallow)

`quality-measure-specification` (40% win, coherence d=-1.24) covers HEDIS + LACE + Charlson + Elixhauser + SDOH + NCQA + care gaps in 323 lines with 15 tables. The agent tries to incorporate everything, producing incoherent responses.

**Structural indicators of encyclopedia mode:**
- >12 tables in a single skill
- >3 unrelated topic areas
- No clear "pick one path" decision tree

**Fix:** Split into focused skills or add a framework selection section that tells the agent which subset to use.

### 4. Zero Trigger Keywords

`scrna-seq-pipeline` has **0 trigger keywords** in its description (just a short direct description without "Triggers include" or "Use when"). Result: 20% activation rate, 50% win rate. The skill might be good but never loads.

**Minimum:** 12+ domain-specific trigger terms. Top performers average 15.6 keywords.

### 5. Coherence Killers

Skills with the worst coherence regression share these traits:

| Skill | Coherence d | Tables | Lines | Root Cause |
|-------|-------------|--------|-------|------------|
| quality-measure-specification | -1.24 | 15 | 323 | Too many reference tables |
| proteomics-analysis | -0.54 | 2 | 339 | Verbose code without structure |
| cdisc-compliance | -0.54 | 20 | 374 | Table overload |
| imaging-study-design | -0.53 | 2 | 134 | Short but no output format |
| quantitative-proteomics | -0.50 | 12 | 323 | Dense reference material |

**Pattern:** >10 tables OR >300 lines without an output format section → coherence regression likely.

---

## Structural Metrics That Predict Success

Cross-referencing the audit with performance data:

| Structural Feature | Present in Top Tier | Present in Bottom Tier | Correlation |
|-------------------|--------------------|-----------------------|-------------|
| ≥15 numbered steps | 14/17 (82%) | 1/7 (14%) | Strong positive |
| Decision trees (≥1) | 12/17 (71%) | 0/7 (0%) | Strong positive |
| Output format section | 8/17 (47%) | 0/7 (0%) | Strong positive |
| ≥10 gotcha items | 12/17 (71%) | 2/7 (29%) | Moderate positive |
| Worked examples | 7/17 (41%) | 1/7 (14%) | Moderate positive |
| Version-specific content | 7/17 (41%) | 1/7 (14%) | Moderate positive |
| >10 tables | 5/17 (29%) | 2/7 (29%) | None (but coherence risk) |
| >10 code blocks | 5/17 (29%) | 4/7 (57%) | Negative (code-heavy = worse) |

**Key insight:** High code block count without decision logic is a negative signal. High numbered step count with decision trees is the strongest positive signal.

---

## The Structural Template

Based on the full 39-skill audit, high-performing skills follow this structure:

```markdown
---
name: skill-name
description: >
  [1-2 sentences: what it does]. Use when [specific triggers with domain jargon].
  Triggers include "term1", "term2", "term3", ... [15+ terms]
version: 1.0.0
tags:
  - skill
  - category:reasoning  # or category:pipeline
  - domain-tag
  - hcls
validated_against:  # pipeline skills only
  date: 2025-01-15
  packages: {tool: "version", ...}
---

# Skill Name

## When to Use
[2-3 bullet points: specific scenarios that trigger this skill]

## Framework Selection
[Decision tree or table: which approach for which situation — FIRST]

## Response Structure
[Ordered checklist: how the agent should structure its answer]
[For reasoning skills: include "do not narrate" instruction for decision trees]

## Core Procedure
[15-25 numbered steps with exact thresholds and branch points]

## Reference Tables
[Compact lookup tables — keep under 10 total, each under 10 rows]

## Worked Example
[One realistic example with actual values, not placeholders]

## Common Mistakes
[8-15 items: wrong → right pairs, explicit "Do NOT" prohibitions]
```

### Length Guidelines

| Category | Ideal Range | Absolute Max | Notes |
|----------|-------------|--------------|-------|
| Reasoning | 200-350 lines | 400 | Decision trees + prose, minimal code |
| Pipeline | 250-400 lines | 460 | Code + decision context + gotchas |
| Tables | ≤10 per skill | — | >12 tables → coherence risk |
| Code blocks | ≤8 per skill | 14 | More code needs more decision logic to compensate |

---

## The Litmus Tests

Before shipping a skill, verify:

| Test | Question | If No... | Evidence |
|------|----------|----------|----------|
| **Novelty** | Does this teach something the base model gets wrong? | Cut the content — it's redundant | proteomics-analysis (30%) recites known recipes |
| **Procedure** | Are there ≥15 numbered steps with branch points? | Add them — top tier averages 19.4 steps | Bottom tier averages 4.3 steps |
| **Specificity** | Are there ≥5 niche numeric thresholds? | Replace vague qualifiers with numbers | "adj.p < 0.05" doesn't count — model knows it |
| **Gotchas** | Are there ≥8 specific common mistakes? | Add them — highest-value content | 36/38 skills have them; quality matters |
| **Focus** | One decision domain, ≤10 tables? | Split or cut — encyclopedia mode kills coherence | quality-measure-spec: 15 tables → d=-1.24 |
| **Activation** | ≥12 domain-jargon trigger keywords? | Add them — 0 keywords = 20% activation | scrna-seq-pipeline: 0 keywords, 20% activation |
| **Structure** | Does it prescribe output format? | Add a Response Structure section | Prevents coherence regression |
| **Conciseness** | Would removing 20% of content hurt? | Remove it — shorter is better for coherence | 134-line skill (imaging-study-design) wins at 80% |

---

## Reasoning vs Pipeline Skills

| Aspect | Reasoning (74% avg win, n=18) | Pipeline (65% avg win, n=20) |
|--------|-------------------------------|-------------------------------|
| Value source | Decision frameworks, methodology | Tool-specific flags, parameter interactions |
| Best content | Decision trees, threshold tables, prohibitions | Realistic code with edge cases, parameter tables |
| Failure mode | Too broad/encyclopedic | Reciting well-known recipes |
| Sweet spot | Niche methodology the model hasn't seen | Tool quirks and silent failure modes |
| Avg numbered steps | 21.3 | 4.8 |
| Avg decision trees | 4.7 | 0.1 |
| Avg code blocks | 2.4 | 9.8 |
| Critical thinking d | 0.69 | 0.56 |

**Reasoning skills** should teach *how to think about a problem* — which framework, which thresholds, which pitfalls. Pure prose with decision trees works (5 top skills have zero code blocks).

**Pipeline skills** should encode *what the model gets wrong* — wrong flags, silent failures, version-specific gotchas, parameter interactions. But they MUST pair code with decision logic and gotchas to succeed.

---

## Diminishing Returns

Skills help most when the base model is weakest:

| Baseline Score | Skills Win Rate | Implication |
|---------------|-----------------|-------------|
| < 80 | **87%** | High-value: model struggles, skill helps a lot |
| 80-90 | 65% | Moderate value: skill adds nuance |
| > 90 | 55% | Low value: model already good, skill may hurt coherence |

Correlation between baseline strength and skill benefit: **r = -0.59**

**Implication:** Don't write skills for topics the model already handles well. Focus on:
- Niche regulatory knowledge (claims billing, CDISC, risk adjustment)
- Domain-specific classification criteria (ACMG/AMP, CMS-HCC hierarchies)
- Tool-specific gotchas not in documentation (DICOM private tags, gnomAD FAF vs AF)
- Methodology the model conflates (target trial emulation vs naive cohort comparison)

---

## Domain Performance Map

| Domain | Win Rate | Cohen's d | Best Skill | Worst Skill | Key Differentiator |
|--------|----------|-----------|-----------|------------|-------------------|
| clinical-data | 75% | 0.52 | ehr-data-parsing (100%) | clinical-data-standards (50%) | Worked examples vs abstract ontology |
| imaging | 75% | 0.43 | radiology-preprocessing (90%) | dicom-processing (60%) | Version-specific flags vs generic parsing |
| cross-domain | 80% | 0.38 | translational-research (80%) | — | Strong evaluation checklists |
| drug-discovery | 77% | 0.35 | drug-repurposing (80%) | cheminformatics (70%) | Database query patterns vs known RDKit |
| genomics | 72% | 0.41 | genomic-variant-interpretation (90%) | variant-calling (50%) | Classification criteria vs known GATK |
| healthcare-ops | 71% | 0.32 | claims-billing-rules (90%) | quality-measure-spec (40%) | Focused trees vs encyclopedia |
| pharmacoepi | 67% | 0.44 | rwd-cohort-analysis (80%) | pharmacoepidemiology (60%) | Concrete code+thresholds vs methodology |
| multi-omics | 70% | 0.48 | multi-omics-pipeline (70%) | multi-omics-integration (70%) | Both decent; integration strategy works |
| protein-structure | 67% | 0.18 | protein-structure-analysis (80%) | molecular-docking (50%) | Specific Biopython vs generic Vina |
| single-cell | 65% | 0.16 | biomarker-discovery (80%) | scrna-seq-pipeline (50%) | Methodology vs known Scanpy |
| proteomics | 50% | -0.01 | quantitative-proteomics (70%) | proteomics-analysis (30%) | Strategy vs known limma |
| clinical-data-review | 50% | -0.05 | cdisc-compliance (70%) | edc-data-validation (30%) | Rules vs known validation code |

---

## Fixing Underperforming Skills

Based on the audit, specific recommendations for bottom-tier skills:

| Skill | Win% | Root Cause | Fix |
|-------|------|-----------|-----|
| proteomics-analysis | 30% | 90% known limma/DEP code, no decision logic | Add normalization selection tree, imputation strategy decision, cut redundant code |
| edc-data-validation | 30% | Generic validation code, no CDISC edge cases | Add partial date handling, therapeutic-area ranges, Pinnacle 21 rule mapping |
| quality-measure-specification | 40% | 15 tables, 7 topics, no focus | Split into 2-3 skills OR add framework selection + output format section |
| variant-calling | 50% | Known GATK commands, no decision context | Add "when to use HaplotypeCaller vs Mutect2" tree, version-specific gotchas |
| molecular-docking | 50% | Generic Vina workflow | Add target-class-specific grid box sizing, scoring function selection tree |
| scrna-seq-pipeline | 50% | 0 trigger keywords, known Scanpy | Add 15+ triggers to description, add QC threshold decision tree |
| clinical-data-standards | 50% | Abstract ontology description | Add worked mapping examples with real codes, decision tree for granularity level |

---

## Sources

- [Eval Technical Report (v3)](./eval/TECHNICAL_REPORT.md) — 410-prompt pairwise evaluation, 41 skills scored
- [Full 38-Skill Structural Audit](./.agents/scratchpad/full-38-skill-audit.md) — per-skill metrics
- [Per-Skill Performance Data](./.agents/scratchpad/eval-per-skill-complete.md) — complete scoring table
- [Agent Skills Standard](https://agentskills.io) — open specification
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills) — authoring guidance
- [anthropics/skills](https://github.com/anthropics/skills) — reference implementations
