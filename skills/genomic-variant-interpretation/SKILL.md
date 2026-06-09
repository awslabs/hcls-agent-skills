---
name: genomic-variant-interpretation
description: Reason about germline and somatic variant classification using ACMG/AMP 2015 and AMP/ASCO/CAP frameworks. Use when the user asks to classify a variant, interpret a VCF annotation, resolve a VUS, apply ACMG criteria, weigh ClinVar evidence, evaluate gnomAD allele frequencies, interpret REVEL/CADD/SpliceAI scores, decide whether PVS1 applies, or assess gene-disease validity before reporting. Triggers include "ACMG", "variant classification", "pathogenic", "likely pathogenic", "VUS", "benign", "ClinVar", "gnomAD", "REVEL", "CADD", "SpliceAI", "PVS1", "loss of function", "nonsense variant", "missense interpretation", "splice variant", "filtering allele frequency", "ClinGen", "somatic variant tier".
usage: Invoke when classifying variants, applying ACMG criteria, or interpreting ClinVar/gnomAD evidence.
version: 1.0.0
tags: [skill, category:reasoning, genomics, variant-interpretation, acmg, hcls]
---

# Genomic Variant Interpretation

## Overview

This is a reasoning skill. It encodes the decision frameworks used in clinical variant interpretation so the agent can help a user classify a genomic variant correctly, justify each piece of evidence, and avoid common pitfalls. It does not run tools or generate code. It assumes the user has variant-level annotation (HGVS nomenclature, population frequency, in silico predictors, ClinVar records, literature) and wants help reasoning about what the variant means.

Two standards dominate:

- **ACMG/AMP 2015** (Richards et al., *Genet Med*) for germline variants in Mendelian disease, with later ClinGen Sequence Variant Interpretation (SVI) refinements (e.g., PVS1 decision tree, PP3/BP4 quantitative calibration, PM2_Supporting).
- **AMP/ASCO/CAP 2017** (Li et al., *JMD*) for somatic variants in cancer, organized by clinical actionability tier (I–IV), not pathogenicity.

Confusing these two is the single most common interpretation error. Pick the framework first, then apply it.

## Usage

Invoke this skill when the user asks you to:

- Classify a specific variant (germline or somatic) using ACMG or AMP rules.
- Decide whether a given ACMG criterion (e.g., PVS1, PM2, PP3) applies to the variant in front of them.
- Reconcile conflicting evidence (e.g., ClinVar "likely pathogenic" vs. high gnomAD frequency).
- Resolve a VUS — what evidence would move it up or down.
- Interpret in silico predictor scores (REVEL, CADD, SpliceAI, AlphaMissense) responsibly.
- Sanity-check a draft classification before it goes into a clinical report.

When invoked, walk through the **Decision Framework** section below in order. Do not skip the gene-disease validity check. Cite the specific criterion codes (e.g., "PM2_Supporting because absent from gnomAD v4 with good coverage") rather than vague language ("rare in population").

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

### The five germline tiers (ACMG/AMP 2015)

| Tier | Clinical meaning |
| --- | --- |
| Pathogenic (P) | Sufficient evidence for disease causation. Reportable. |
| Likely pathogenic (LP) | >90% certainty of pathogenicity. Reportable, managed similarly to P. |
| Uncertain significance (VUS) | Insufficient or conflicting evidence. **Not actionable.** Do not use for medical management. |
| Likely benign (LB) | >90% certainty of benign. |
| Benign (B) | Sufficient evidence against disease causation. |

### Evidence criteria (28 total)

Pathogenic evidence is graded by strength: **Very Strong (PVS), Strong (PS), Moderate (PM), Supporting (PP)**. Benign evidence: **Stand-alone (BA), Strong (BS), Supporting (BP)**.

**Pathogenic:**

- **PVS1** — Null variant (nonsense, frameshift, canonical ±1/2 splice, initiation codon, single/multi-exon deletion) in a gene where loss of function is a known disease mechanism. Subject to the ClinGen PVS1 decision tree (see below).
- **PS1** — Same amino acid change as a previously established pathogenic variant (different nucleotide).
- **PS2** — De novo (paternity and maternity confirmed) in a patient with the disease and no family history.
- **PS3** — Well-established functional studies show a damaging effect.
- **PS4** — Prevalence in affected individuals significantly increased vs. controls (e.g., case-control OR >5).
- **PM1** — Located in a mutational hot spot and/or critical, well-established functional domain without benign variation.
- **PM2** — Absent from (or at extremely low frequency in) population databases. **SVI now recommends PM2_Supporting** rather than Moderate.
- **PM3** — For recessive disorders, detected in trans with a pathogenic variant.
- **PM4** — Protein length changes due to in-frame indels in a non-repeat region or stop-loss.
- **PM5** — Novel missense change at an amino acid residue where a different missense change has been seen as pathogenic.
- **PM6** — Assumed de novo without confirmation of paternity/maternity.
- **PP1** — Co-segregation with disease in multiple affected family members (upgrade to PS with stronger segregation).
- **PP2** — Missense in a gene with a low rate of benign missense variation and where missense is a common mechanism.
- **PP3** — Multiple computational lines of evidence support a deleterious effect (SVI: use calibrated thresholds, e.g., REVEL).
- **PP4** — Patient phenotype highly specific for a gene with a single etiology.
- **PP5** — Reputable source reports pathogenic (**deprecated by SVI — do not use**).

**Benign:**

- **BA1** — Allele frequency >5% in a large, outbred population (e.g., gnomAD).
- **BS1** — Allele frequency greater than expected for the disorder.
- **BS2** — Observed in healthy adults at a dose inconsistent with the disorder (homozygous for recessive, hemizygous for X-linked, heterozygous for dominant).
- **BS3** — Well-established functional studies show no damaging effect.
- **BS4** — Lack of segregation in affected family members.
- **BP1** — Missense in a gene where only truncating variants cause disease.
- **BP2** — Observed in trans with a dominant pathogenic variant, or in cis with a pathogenic variant in any inheritance.
- **BP3** — In-frame indel in a repetitive region without known function.
- **BP4** — Multiple computational lines of evidence suggest no impact (SVI: calibrated).
- **BP5** — Variant found in a case with an alternate molecular basis for disease.
- **BP6** — Reputable source reports benign (**deprecated by SVI**).
- **BP7** — Synonymous variant with no predicted splice impact and not highly conserved.

### Combining rules (ACMG/AMP 2015)

| Classification | Required evidence combinations |
| --- | --- |
| **Pathogenic** | (a) 1 PVS1 + ≥1 PS; or (b) 1 PVS1 + ≥2 PM; or (c) 1 PVS1 + 1 PM + 1 PP; or (d) 1 PVS1 + ≥2 PP; or (e) ≥2 PS; or (f) 1 PS + ≥3 PM; or (g) 1 PS + 2 PM + ≥2 PP; or (h) 1 PS + ≥4 PP |
| **Likely pathogenic** | (a) 1 PVS1 + 1 PM; or (b) 1 PS + 1–2 PM; or (c) 1 PS + ≥2 PP; or (d) ≥3 PM; or (e) 2 PM + ≥2 PP; or (f) 1 PM + ≥4 PP |
| **Benign** | 1 BA1; or ≥2 BS |
| **Likely benign** | 1 BS + 1 BP; or ≥2 BP |
| **VUS** | Criteria do not meet any above, or benign and pathogenic evidence conflict |

ClinGen SVI has since introduced a **Bayesian point system** (Tavtigian et al., 2018) where each strength level has a point value (PVS=8, PS=4, PM=2, PP=1; benign symmetric) and tiers correspond to point ranges. Prefer the point system when modifying criterion strength (e.g., PM2_Supporting = 1 point).

### Population frequency — the filtering step

Always apply frequency first. It is the cheapest and most decisive evidence.

- **BA1 (stand-alone benign)**: allele frequency **>5%** in any continental population with adequate coverage and sample size (≥2000 alleles). Gene-specific BA1 thresholds exist for some ClinGen VCEPs (e.g., *MYH7* uses 0.1%).
- **BS1**: frequency **greater than expected** for the disorder given prevalence, penetrance, allelic and genetic heterogeneity. Use the **filtering allele frequency (FAF)** — the upper bound of the 95% confidence interval of the population allele frequency — and compare to the maximum credible population AF for the disease.
- **PM2_Supporting**: variant **absent or at extremely low frequency** in gnomAD, in a population relevant to the disease, with adequate read depth. Do not apply PM2 when coverage is poor or the variant is in a low-complexity / segmental duplication region — absence may be artifactual.

Use the **largest, most current** population reference (gnomAD v4 at time of writing). Exclude founder populations when appropriate. Never rely on 1000 Genomes alone.

### Computational predictors — use responsibly

In silico scores are **supporting evidence at most** unless calibrated by ClinGen for a specific gene.

- **REVEL** (missense ensemble, 0–1): SVI-calibrated thresholds are roughly >0.773 PP3_Moderate, >0.644 PP3_Supporting, <0.290 BP4_Supporting, <0.183 BP4_Moderate (exact values vary by gene family — check the current SVI recommendation).
- **CADD** (all variant types, phred-scaled): >20 ≈ top 1%, >25 ≈ top 0.3%. Popular but **not recommended alone for clinical classification** — poorly calibrated for missense.
- **SpliceAI** (0–1 splice-altering probability): ≥0.2 possible impact, ≥0.5 likely impact, ≥0.8 high confidence. Apply to any variant within ~50 nt of a splice site, including synonymous and deep intronic.
- **AlphaMissense**: emerging; treat as one predictor, do not over-weight.

Rules of thumb:

1. **Never** base PP3 or BP4 on a single predictor. Use at least two concordant (REVEL + SpliceAI for missense near splice; REVEL + conservation for deep missense).
2. Do not apply PP3 if the variant type is already captured by PVS1 (nonsense, canonical splice). That would double-count.
3. Predictors are weaker for in-frame indels and non-coding variants — do not force PP3.

### ClinVar — how to read it

ClinVar is a submission database, not ground truth. Weight each assertion by:

- **Review status (stars)**:
  - ★★★★ practice guideline (e.g., ACMG SF list)
  - ★★★ expert panel (ClinGen VCEP)
  - ★★ multiple submitters, no conflicts
  - ★ single submitter, or conflicting interpretations
  - (no star) no assertion criteria provided

  **One-star and no-star entries are unreliable** on their own. A single commercial lab calling a variant pathogenic without supporting evidence is not sufficient to apply PS1 or influence classification.

- **Date**: classifications before ~2016 predate ACMG/AMP and may be outdated. Prefer the most recent submission.
- **Conflicting interpretations**: read each submitter's evidence, do not average the calls. Resolve the conflict by going back to the primary evidence.
- **Submitter identity**: expert panels > large reference labs > smaller labs > case reports.

ClinVar is appropriate for PS1 (same amino acid change), PM5 (different change at same residue), and as a pointer to primary literature. It is **not** a substitute for performing your own classification.

### PVS1 decision tree (ClinGen SVI 2018)

Not every loss-of-function (LoF) variant deserves full PVS1 strength. Walk this tree:

1. **Is LoF a known disease mechanism for this gene?** If the only reported pathogenic variants are missense with gain-of-function or dominant-negative effects, LoF may not cause disease. If unclear, **do not apply PVS1** — use lower strength or none.
2. **Variant class:**
   - **Nonsense or frameshift**: go to step 3.
   - **Canonical ±1,2 splice**: go to step 4.
   - **Initiation codon loss**: PVS1_Moderate (downstream ATG rescue possible).
   - **Single or multi-exon deletion**: consider reading frame.
3. **Does the variant predict nonsense-mediated decay (NMD)?**
   - Premature termination codon (PTC) in any exon except the last, and more than ~50 nt upstream of the final exon-exon junction → NMD predicted → PVS1 applies.
   - PTC in the last exon or last 50 nt of the penultimate exon → NMD escape → **downgrade to PVS1_Strong**; also check whether the truncated region is critical to protein function. If the removed region is not functionally critical, downgrade further to Moderate or drop.
4. **Splice variant:**
   - Does the variant likely cause exon skipping or intron retention? Predict the reading-frame consequence.
   - In-frame skipping of a non-critical exon → PVS1_Moderate or lower.
   - Out-of-frame skipping with NMD → PVS1.
5. **Rescue transcripts / alternative isoforms:** if the affected exon is only included in a minor isoform not expressed in the disease-relevant tissue, downgrade.
6. **Recurrent vs. unique:** if multiple unrelated pathogenic LoF variants are already reported in the same exon, confidence increases.

Document which step you applied and at what strength.

### Variant type — practical notes

- **Nonsense and frameshift**: usually PVS1 (after decision tree). Also consider PM2, PS4, PM3 for recessive.
- **Canonical splice (±1, ±2)**: PVS1 after decision tree. Support with SpliceAI.
- **Extended splice region (±3 to ±8, exonic near junction, deep intronic)**: PVS1 does not apply. Use PP3/BP4 with SpliceAI; PS3 if an RNA study confirms aberrant splicing.
- **Missense — the hardest class:** cannot use PVS1. Evidence usually comes from PM1 (hotspot/domain), PM2 (rarity), PM5 (another change at residue pathogenic), PP2 (missense-intolerant gene), PP3 (calibrated predictor), PS1 (same amino acid change), PS3 (functional assay). Most variants end up VUS because no single line is strong.
- **In-frame indels**: PM4 if not in a repeat; BP3 if in a repeat without known function. Predictors are weak — avoid PP3.
- **Synonymous**: usually BP7 unless SpliceAI or conservation flags a splice effect.
- **UTR, deep intronic, regulatory**: default to VUS unless functional or splicing evidence exists.

### Gene-disease validity — check before you classify

Applying ACMG criteria to a variant in a gene that does not cause the disease in question produces a confidently wrong answer. Before classifying:

1. Confirm the gene is associated with the patient's phenotype via **ClinGen Gene-Disease Validity** (Definitive, Strong, Moderate, Limited, Disputed, Refuted, No Known Disease Relationship).
2. **Limited or Disputed** → do not report pathogenic calls clinically; the gene itself is not validated.
3. Confirm the **mechanism of disease** (LoF, GoF, dominant-negative) — this gates PVS1, PP2, BP1.
4. Confirm the **inheritance pattern** — this gates BS2, PM3, and interpretation of heterozygous vs. homozygous observations.

### Somatic variants — different framework

For tumor-derived variants, use **AMP/ASCO/CAP 2017 tiers**, which grade **clinical actionability in cancer**, not germline pathogenicity. Do not apply ACMG tiers to somatic calls.

| Tier | Meaning |
| --- | --- |
| **I — Strong clinical significance** | FDA-approved therapy, included in professional guidelines, or well-powered study with consensus. Levels A (FDA/guideline) and B (well-powered study). |
| **II — Potential clinical significance** | FDA-approved in a different tumor type, investigational therapy with some evidence, or multiple small studies. Levels C and D. |
| **III — Unknown clinical significance** | Not observed at a significant allele frequency in population databases or cancer hotspots; no convincing published evidence of cancer association. |
| **IV — Benign or likely benign** | Observed at significant frequency in population databases; no existing evidence of cancer association. |

Use resources like OncoKB, CIViC, COSMIC (hotspots), and JAX CKB. Distinguish **driver vs. passenger**, and flag variants that may be **germline incidentally found on tumor sequencing** (high VAF ~50%, in a cancer predisposition gene) — those need germline confirmation and ACMG classification.

## Decision Framework — per variant

Apply these steps in order. Stop when a classification is reached.

1. **Framework selection.** Germline → ACMG/AMP. Somatic → AMP/ASCO/CAP. Tumor-normal with a germline incidental finding → both.
2. **Gene-disease validity.** Check ClinGen. If Disputed/Refuted, classify as benign for that condition or decline to classify.
3. **Variant nomenclature & transcript.** Use a MANE Select or ClinGen-approved transcript. Confirm HGVS is correct.
4. **Population frequency.**
   - AF >5% → **BA1, classify Benign. Stop.**
   - AF > max credible for disease (BS1) → strong benign evidence.
   - Absent / extremely rare with good coverage → PM2_Supporting.
5. **Variant class & PVS1.** If predicted LoF, walk the PVS1 decision tree and record the applied strength.
6. **ClinVar & literature.** Check stars, date, conflicts. Extract PS1, PM5 candidates. Use as pointer to primary data — do not use PP5/BP6.
7. **Functional data (PS3/BS3).** Only well-established assays relevant to the mechanism. Weight by assay quality per ClinGen VCEP rubrics when available.
8. **Computational (PP3/BP4).** Calibrated REVEL / SpliceAI. Do not double-count with PVS1.
9. **Segregation, de novo, case-control (PP1, PS2/PM6, PS4).** Require paternity/maternity confirmation for PS2.
10. **Trans / cis observations (PM3, BP2).** For recessive, phase with a known pathogenic variant.
11. **Phenotype specificity (PP4).** Only when phenotype is highly specific (e.g., biochemical pattern pathognomonic for the gene).
12. **Combine.** Apply the combining rules table or the Bayesian point system. Be explicit about every criterion applied and its strength.
13. **Sanity check.** Does the final call match the evidence narrative? If a single piece of evidence (e.g., one ClinVar star-1 submission) is driving a pathogenic call, downgrade to VUS.
14. **Document.** Record every criterion, its strength, its source, and the reviewer.

## When NOT to Use This Skill

- Issuing clinical reports to patients (requires CLIA-certified lab director sign-off)
- Reclassifying variants without access to functional data or segregation studies
- Pharmacogenomic dosing decisions for individual patients

## When to Escalate to a Human Expert

- VUS in actionable genes where treatment decisions depend on classification
- Discordant classifications between ClinVar submitters (needs expert panel)
- When novel variant requires functional studies before classification

## Common Mistakes

- **Wrong:** Classifying a variant as pathogenic in a gene with Disputed disease validity
  **Right:** Check ClinGen gene-disease validity before applying ACMG criteria — skip classification if validity is Disputed or below
  **Why:** If the gene does not cause the disease, no variant in it can be pathogenic for that condition

- **Wrong:** Applying full PVS1 strength to all loss-of-function variants regardless of NMD prediction
  **Right:** Walk the PVS1 decision tree — a nonsense variant in the last exon that escapes NMD requires downgrade to PVS1_Strong or lower
  **Why:** Not all LoF variants trigger NMD; those that escape may produce a truncated protein with residual function

- **Wrong:** Applying both PVS1 and PP3 to a canonical splice variant
  **Right:** Do not add PP3 from SpliceAI when PVS1 already captures the splice effect — this is the same evidence counted twice
  **Why:** Double-counting inflates the evidence score and can push a variant to an incorrect pathogenic classification

- **Wrong:** Applying PM2 at Moderate strength for absent-from-gnomAD variants
  **Right:** Use PM2_Supporting per current SVI guidance in nearly all cases
  **Why:** PM2 at Moderate strength inflates classifications — absence from databases is weak evidence on its own

- **Wrong:** Treating a single ClinVar 1-star submission as sufficient evidence for pathogenicity
  **Right:** Read the underlying evidence from each submitter — a single lab's call without supporting data is not reliable
  **Why:** One-star entries lack review criteria or independent confirmation; the label does not equal the evidence

- **Wrong:** Using PP5 or BP6 criteria (reputable source reports pathogenic/benign)
  **Right:** Evaluate the primary evidence directly — PP5 and BP6 are deprecated by ClinGen SVI
  **Why:** These criteria outsource classification to another lab without verifying their reasoning

- **Wrong:** Basing PP3 on a single in silico predictor (e.g., CADD > 20 alone)
  **Right:** Use ≥2 concordant, calibrated predictors (e.g., REVEL + SpliceAI) for PP3
  **Why:** Individual predictors have high false-positive rates; concordance across calibrated tools increases reliability

- **Wrong:** Applying PM2 when the variant falls in a poorly covered region of gnomAD
  **Right:** Check coverage depth at the variant position — absence in low-coverage regions (segmental duplications, pseudogene overlap) may be artifactual
  **Why:** The variant may simply be uncalled rather than truly absent from the population

- **Wrong:** Using 1000 Genomes or ExAC as the primary population frequency source
  **Right:** Use the largest current reference (gnomAD v4 or later) for population frequency assessment
  **Why:** Older databases have smaller sample sizes, fewer populations, and outdated variant calling

- **Wrong:** Averaging conflicting ClinVar classifications (e.g., "3 labs say P, 1 says LB → P")
  **Right:** Read each submitter's evidence independently and resolve the conflict based on primary data
  **Why:** Averaging labels ignores the quality and basis of each submission — one well-evidenced dissent may be correct

- **Wrong:** Applying ACMG pathogenicity tiers (P/LP/VUS/LB/B) to somatic variants
  **Right:** Use AMP/ASCO/CAP Tier I–IV for somatic variants, which grades clinical actionability, not germline pathogenicity
  **Why:** Mixing frameworks produces confusing reports — somatic variants are assessed for treatment relevance, not disease causation

- **Wrong:** Not flagging a high-VAF variant (~50%) in a cancer predisposition gene found on tumor sequencing as potentially germline
  **Right:** Flag for germline confirmation and separate ACMG classification — this has implications for the patient and relatives
  **Why:** A germline finding requires genetic counseling and family cascade testing, which tumor-only reporting misses

- **Wrong:** Reporting a VUS as clinically actionable or using it to guide medical management
  **Right:** Clearly state that VUS means insufficient evidence and should not change clinical management
  **Why:** Acting on a VUS exposes patients to unnecessary interventions or false reassurance

- **Wrong:** Calling a heterozygous variant pathogenic for an autosomal recessive disease without identifying a second hit
  **Right:** Confirm inheritance pattern and require a second pathogenic variant in trans for recessive disease attribution
  **Why:** A single heterozygous variant in a recessive gene does not explain the patient's disease

- **Wrong:** Applying PP2 or BP1 by default without gene-level evidence of the disease mechanism
  **Right:** Confirm that missense (for PP2) or only truncating variants (for BP1) are the established disease mechanism for the specific gene
  **Why:** These criteria require gene-level evidence; applying them generically inflates or deflates classifications incorrectly

- **Wrong:** Treating a variant at 0.01% allele frequency as "absent" and applying PM2
  **Right:** Use filtering allele frequency (FAF) and compare to the maximum credible population AF for the disease
  **Why:** A variant at 0.01% may still be too common for an ultra-rare dominant disease — "rare" is not the same as "absent"

- **Wrong:** Maintaining old variant classifications without periodic re-review as new data emerges
  **Right:** Re-curate classifications periodically as new population data, functional studies, and ClinVar submissions become available
  **Why:** Classifications drift as evidence accumulates — a former VUS may now be classifiable, or a former LP may be downgraded

## References

- ACMG/AMP 2015: Richards et al. Genet Med 2015, https://doi.org/10.1038/gim.2015.30
- ClinGen SVI: https://clinicalgenome.org/working-groups/sequence-variant-interpretation/
- PVS1 decision tree: Abou Tayoun et al. Hum Mutat 2018, https://doi.org/10.1002/humu.23626
- Bayesian ACMG: Tavtigian et al. Hum Mutat 2018, https://doi.org/10.1002/humu.23388
- gnomAD: Karczewski et al. Nature 2020, https://doi.org/10.1038/s41586-020-2308-7
- ClinVar: Landrum et al. Nucleic Acids Res 2018, https://doi.org/10.1093/nar/gkx1153
