---
name: quantitative-proteomics
description: >
  Reason about quantitative proteomics experiment design and data analysis strategy.
  Use when the user asks to choose between LFQ, TMT, and DIA quantification; select an
  imputation method for missing values; pick a normalization strategy; interpret
  differential expression results from proteomics data; evaluate ratio compression;
  or design a proteomics study for biomarker discovery or validation. Triggers include
  "LFQ vs TMT", "DIA quantification", "proteomics normalization", "missing value
  imputation", "MNAR", "MinProb", "QRILC", "kNN imputation", "VSN normalization",
  "median centering", "quantile normalization", "limma proteomics", "ratio compression",
  "proteomics study design", "label-free quantification", "tandem mass tag",
  "data-independent acquisition", "DIA-NN", "Spectronaut", "MaxQuant LFQ",
  "proteomics differential expression", "empirical Bayes proteomics",
  "proteinGroups.txt", "MSFragger output", "TMT normalization code",
  "LFQ analysis", "proteomics pipeline R", "MaxQuant output".
usage: Invoke when designing a quantitative proteomics experiment or choosing analysis parameters.
version: 1.0.0
tags: [skill, category:reasoning, proteomics, mass-spectrometry, quantification, biomarker, hcls]
---

# Quantitative Proteomics — Reasoning Skill

## Overview

You are an expert in quantitative proteomics experimental design and statistical analysis.
When the user asks about quantification strategy, imputation, normalization, or
differential expression for proteomics data, apply the decision frameworks below.

## Usage

- Choose between LFQ, TMT, and DIA quantification strategies for a given study design
- Select imputation and normalization methods based on missingness patterns and data properties

## Core Concepts

---

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## 1. Quantification Strategy Selection

### 1.1 Decision Tree

```
Is the goal discovery or targeted validation?
├─ Discovery (maximize coverage)
│  ├─ Sample count ≤ 20 → LFQ (label-free quantification)
│  ├─ Sample count 20–100 → TMT (multiplexed, up to 18-plex)
│  └─ Sample count any, need comprehensive coverage → DIA
├─ Targeted validation
│  └─ Use PRM (parallel reaction monitoring) or SRM/MRM
└─ Large clinical cohort (>100 samples)
   ├─ Budget allows multiplexing → TMT with fractionation
   └─ Budget constrained → DIA (single-shot)
```

### 1.2 Key Rules

1. **Never mix quantification strategies** within a single study unless you have a rigorous batch-correction plan.
2. **LFQ requires match-between-runs (MBR)** to reduce missingness — but MBR can introduce false transfers (~5% false positive rate at default settings).
3. **DIA library-free mode** (DIA-NN ≥1.8) is simpler; library-based gives ~10% more IDs.
4. **Biological replicates matter more than technical replicates.** Minimum 3 per condition; 5+ for clinical studies.
5. **TMT ratio compression:** Expect 30–50% underestimation at MS2 level. True FC ≈ observed FC × 1.5–2.0. SPS-MS3 reduces compression to <10% but costs ~30% fewer IDs. Do not apply arbitrary correction without spike-in ground truth.

---

## 2. Missing Value Assessment and Imputation

### 2.1 Imputation Decision Tree

```
Assess missingness pattern:
├─ >50% missing across ALL groups → Exclude protein (unreliable)
├─ Missing predominantly in one condition
│  └─ Likely MNAR → Use left-censored methods (MinProb, QRILC)
├─ Missing scattered across conditions
│  └─ Likely MAR → Use kNN, MLE, or BPCA
└─ Mixed pattern
   └─ Hybrid: classify each protein's missingness, apply appropriate method
```

### 2.2 Imputation Methods and Pitfalls

| Method | Mechanism | When to Use | Pitfall |
|---|---|---|---|
| MinProb | MNAR | Low-abundance below LOD | Underestimates variance |
| QRILC | MNAR | Left-censored distributions | Assumes normality |
| kNN (k=10) | MAR | Scattered missingness | Fails if too many missing |
| MLE (EM) | MAR | Well-behaved MAR data | Assumes multivariate normality |
| BPCA | MAR | High-dimensional data | Computationally expensive |

### 2.3 Imputation Rules

1. **Always visualize missingness first.** Plot heatmap and density plots before choosing method.
2. **Filter before imputing.** Remove proteins with >50% missing and contaminants.
3. **MNAR parameters:** downshift = 1.8 SD, width = 0.3 SD from the observed distribution.
4. **Never impute then filter.** Filtering after imputation biases the dataset.
5. **Sensitivity analysis:** Run DE with and without imputation to confirm key hits are robust.

---

## 3. Normalization Strategy

### 3.1 Decision Tree

```
What is the expected biological variation?
├─ Most proteins unchanged between conditions (typical)
│  ├─ Default → Median centering (simple, robust)
│  ├─ Strong batch effects → Quantile normalization
│  └─ Variance depends on intensity → VSN
├─ Global shift expected (e.g., drug treatment affecting many proteins)
│  └─ Use spike-in standards, NOT data-driven methods
└─ TMT data
   └─ Sample loading normalization → then median centering within plex
└─ DIA data
   └─ Median centering on precursor quantities BEFORE protein roll-up
```

### 3.2 Rules

1. **Log2-transform intensities before normalization** (except VSN, which includes transformation).
2. **Do NOT quantile-normalize if >30% of proteome is affected.** It will mask real biology.
3. **TMT requires two-step normalization:** sample loading normalization, then internal reference scaling.
4. **Batch correction (ComBat) is separate from normalization.** Normalize first, then correct.
5. **Check with box plots and MA plots.** Post-normalization medians should align.

---

## 4. Differential Expression Interpretation

### 4.1 FC Thresholds and Rules

1. **FC thresholds depend on biology.** Secreted biomarkers: |log2FC| > 0.5. Intracellular: |log2FC| > 1.0.
2. **DEqMS is preferred over limma** because it models variance as a function of peptide count.
3. **Always use adjusted p-values.** Unadjusted p < 0.05 yields hundreds of false positives.
4. **Check for confounders.** Include batch, sex, age as covariates in the linear model.

### 4.2 Common Mistakes

- **Wrong:** Using a standard t-test for differential expression in proteomics
  **Right:** Use limma (empirical Bayes moderated t-test) or DEqMS (variance modeled by peptide count)
  **Why:** Standard t-tests have insufficient power with small sample sizes; moderated statistics borrow strength across proteins

- **Wrong:** Filtering differentially expressed proteins on p-value alone without a fold-change threshold
  **Right:** Require both adjusted p-value < 0.05 and a minimum |log2FC| threshold (≥0.5 for secreted, ≥1.0 for intracellular)
  **Why:** Statistically significant but biologically trivial changes (tiny FC) are not actionable and clutter results

- **Wrong:** Interpreting TMT fold changes at face value without accounting for ratio compression
  **Right:** Use SPS-MS3 quantification or apply a compression correction factor (true FC ≈ observed × 1.5–2.0)
  **Why:** MS2-level TMT systematically underestimates fold changes by 30–50% due to co-isolation interference

- **Wrong:** Including contaminant and reverse-hit proteins in the analysis
  **Right:** Filter out all entries with CON__ and REV__ prefixes before normalization and statistical testing
  **Why:** Contaminants distort normalization and inflate protein counts; reverse hits are decoy sequences

- **Wrong:** Imputing missing values after normalization
  **Right:** Log2-transform first, then impute, then normalize
  **Why:** Imputing on normalized data uses shifted distributions as reference, introducing systematic bias in imputed values

- **Wrong:** Including proteins identified by only a single peptide in quantitative analysis
  **Right:** Require ≥2 unique peptides per protein for confident identification and quantification
  **Why:** Single-peptide IDs have high false-discovery rates and unreliable quantification

---

## 5. Study Design and QC

### 5.1 Sample Size Guidelines

| Study Type | Minimum | Recommended |
|---|---|---|
| Discovery | 3 per group | 5–6 per group |
| Biomarker validation | 10 per group | 20+ per group |
| Clinical proteomics | 20 per group | 50+ per group |

### 5.2 Batch Design Rules

1. **Randomize samples across batches.** Never all cases in one batch, all controls in another.
2. **Include a bridge sample in every TMT plex** for cross-plex normalization.
3. **Block confounders:** Balance age and sex across batches.

### 5.3 QC Checkpoints

| Checkpoint | Acceptable Range |
|---|---|
| Protein IDs per run | >4,000 (LFQ), >6,000 (DIA), >8,000 (TMT) |
| CV of intensities | <20% for technical replicates |
| Missingness rate | <30% (LFQ), <10% (TMT), <15% (DIA) |
| Replicate correlation | Pearson r >0.95 (technical), >0.85 (biological) |
| PCA clustering | Replicates cluster together |

---

## 6. Critical Thresholds Quick Reference

- **CV > 20% across replicates** → flag run for investigation
- **Proteins >50% missing in ALL groups** → exclude before imputation
- **TMT ratio compression correction:** true FC ≈ observed FC × 1.5–2.0 (MS2 level)
- **Quantile normalization forbidden** if >30% of proteome differentially expressed
- **Phosphoproteomics:** require site localization probability >0.75; normalize phospho to total protein
- **Proteomics-transcriptomics correlation** is typically r = 0.4–0.6 — discordance is biologically informative (post-translational regulation)

---

## 7. Quick-Reference Decision Summary

```
Quantification:  Small discovery → LFQ
                 Large cohort → TMT (with SPS-MS3)
                 Comprehensive → DIA

Imputation:      Low-abundance missing → MinProb / QRILC (MNAR)
                 Random missing → kNN / MLE (MAR)
                 Mixed → Hybrid approach

Normalization:   Default → Median centering
                 Batch effects → Quantile
                 Heteroscedastic → VSN
                 Global shift → Spike-in standards

DE Testing:      Default → limma (empirical Bayes)
                 Proteomics-aware → DEqMS
                 Threshold → adj.p < 0.05, |log2FC| > 1.0
```

---

## Pipeline Reference

### Input Formats

| Source | File | Key Columns |
|---|---|---|
| MaxQuant | proteinGroups.txt | Protein IDs, Gene names, LFQ intensity *, iBAQ, Reverse, Potential contaminant |
| MSFragger | combined_protein.tsv | Protein, Gene, *Intensity*, *Spectral Count* |
| Proteome Discoverer | Proteins.txt | Accession, Description, Abundance * |
| DIA-NN | report.pg_matrix.tsv | Protein.Group, sample columns with quantities |

### TMT Sample Loading Normalization + Internal Reference Scaling

```r
# TMT: Sample Loading Normalization + Internal Reference Scaling
col_sums <- colSums(mat, na.rm = TRUE)
scaling_factors <- median(col_sums) / col_sums
mat_sln <- sweep(mat, 2, scaling_factors, "*")

# IRS using bridge channel (e.g., pooled reference in 131C)
bridge <- mat_sln[, grep("131C", colnames(mat_sln))]
irs_factors <- apply(bridge, 1, median, na.rm = TRUE)
mat_irs <- mat_sln / irs_factors  # row-wise scaling across plexes
```

### When limma Fails

| Scenario | Problem | Use Instead |
|---|---|---|
| <3 replicates per group | Variance estimation unreliable | `RankProd` (rank-based, no variance estimate needed) |
| Unbalanced design (e.g., 3 vs 8) | Pooled variance biased toward larger group | Mixed models: `lme4` + `lmerTest` |
| Repeated measures / longitudinal | Correlated samples violate independence | `limma::duplicateCorrelation()` or `dream()` from variancePartition |
| >2 groups | Pairwise t-tests inflate FDR | `limma::contrasts.fit()` with proper contrast matrix |
| Paired samples (e.g., tumor vs adjacent normal) | Must account for patient effect | Include patient as blocking factor in design matrix |

### Parameter Reference

| Parameter | Default | Range | Notes |
|---|---|---|---|
| MinProb quantile (q) | 0.01 | 0.001–0.05 | Lower = more conservative imputation |
| MinProb downshift (σ) | 1.8 | 1.4–2.0 | Standard deviations below mean |
| MinProb width | 0.3 | 0.2–0.5 | Fraction of observed σ for imputed spread |
| kNN k | 10 | 5–15 | Higher k = smoother but slower |
| kNN rowmax | 0.5 | 0.3–0.7 | Max fraction missing per row allowed |
| Missingness filter | 70% in ≥1 group | 50–100% | Stricter = fewer proteins, less noise |
| log2FC threshold | 1.0 | 0.5–2.0 | Adjust to biological context |
| adj.p threshold | 0.05 | 0.01–0.1 | 0.01 for stringent discovery |
| Unique peptides min | 2 | 1–3 | ≥2 required for confident ID |

---

## When NOT to Use This Skill

- Validating biomarker candidates for clinical assay development (needs assay chemist)
- When sample prep issues dominate variance (pre-analytical problem, not analytical)
- Absolute quantification requiring isotope-labeled standards

## When to Escalate to a Human Expert

- When missing data exceeds 50% and imputation assumptions are untestable
- Before publishing quantitative claims from single-batch experiments
- When results require mass spectrometry method development expertise

## 8. Troubleshooting Common Issues

| Symptom | Likely Cause | Solution |
|---|---|---|
| Very few protein IDs (<2,000) | Poor sample prep or instrument issue | Check TIC, re-run QC standard |
| All samples cluster by batch in PCA | Batch effect dominates biology | Apply ComBat or limma removeBatchEffect |
| No significant DE proteins | Underpowered study or wrong test | Check sample size, use DEqMS, relax FC threshold |
| Too many significant hits (>50%) | Normalization failure or global shift | Check box plots, consider spike-in normalization |
| Imputation creates artificial clusters | MNAR imputation too aggressive | Reduce downshift, try kNN, or filter more stringently |
| TMT fold changes smaller than expected | Ratio compression | Use SPS-MS3 or apply compression correction |
| High CV between replicates (>30%) | Sample prep variability | Review digestion protocol, add QC samples |
