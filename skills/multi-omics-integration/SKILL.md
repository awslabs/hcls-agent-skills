---
name: multi-omics-integration
description: >
  Reasoning skill for multi-omics data integration strategy selection. Use when the user asks to
  integrate transcriptomics with proteomics, combine multi-omic layers, choose between early
  intermediate or late integration, apply batch correction across omics, handle partial sample
  overlap, run MOFA+ or iCluster, interpret multi-omic factors, select enrichment methods for
  multi-omic signatures, or decide how to merge genomics epigenomics transcriptomics proteomics
  and metabolomics data. Triggers include "multi-omics integration", "combine omics layers",
  "early vs late fusion", "MOFA+", "iCluster", "batch correction across omics", "partial overlap",
  "multi-omic enrichment", "kernel integration", "concatenation vs stacking", "SNF",
  "similarity network fusion", "intermediate integration", "multi-omic factor analysis".
usage: Invoke when designing a multi-omics integration strategy to select the right fusion approach, batch correction method, and downstream enrichment.
version: 1.0.0
tags: [skill, category:reasoning, multi-omics, integration, hcls]
---

# Multi-Omics Integration — Reasoning Skill

## Overview

Guide the agent through principled selection of multi-omics integration strategies, batch
correction approaches, and enrichment methods. This skill encodes decision frameworks — not
code — so the agent reasons correctly before generating any pipeline.

## Usage

- Invoke when choosing between early, intermediate, or late integration strategies
- Use for batch correction decisions across omics layers or partial sample overlap
- Activate for MOFA+/iCluster/SNF method selection or multi-omic enrichment planning

---

## Core Concepts

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail

The decision trees and parameter selection tables in this skill are for internal reasoning only. Apply them to select the correct integration strategy, but do not reproduce the full trees in your response. Never narrate the tree traversal or show deliberation between options. Present only the recommended approach with justification.

## 1. Integration Strategy Decision Tree

Follow this tree top-down. The first matching leaf is the recommended strategy.

```
START
 ├─ Sample size per omic layer?
 │   ├─ n ≥ 200 AND full overlap across layers
 │   │   └─ → EARLY integration (Section 2)
 │   ├─ 50 ≤ n < 200 OR moderate overlap (≥70%)
 │   │   └─ → INTERMEDIATE integration (Section 3)
 │   └─ n < 50 OR low overlap (<70%) OR layers collected on different cohorts
 │       └─ → LATE integration (Section 4)
 └─ Special cases
     ├─ Only 2 layers, one is sparse (e.g., somatic mutations)
     │   └─ → INTERMEDIATE with kernel methods
     └─ Layers have very different dimensionality (e.g., 20k genes vs 500 metabolites)
         └─ → INTERMEDIATE with MOFA+ (handles heterogeneous dimensionality)
```

### Quick-Reference Table

| Criterion | Early | Intermediate | Late |
|---|---|---|---|
| Minimum sample size | ≥200 | ≥50 | Any |
| Sample overlap required | Full (100%) | ≥70% | None required |
| Handles missing layers | No | Yes (MOFA+) | Yes |
| Interpretability | Low (combined feature space) | Medium (latent factors) | High (per-omic models) |
| Risk of overfitting | High | Medium | Low |
| Best for discovery | Yes (finds cross-omic interactions) | Yes | No |
| Best for prediction | Moderate | Good | Best for small n |

---

## 2. Early Integration

### Definition
Concatenate feature matrices from all omic layers into a single matrix, then apply a single
model (clustering, classification, regression).

### When to Use
- Large cohort (n ≥ 200) with complete overlap across all layers.
- Goal is to discover cross-omic feature interactions.
- All layers have been individually QC'd and normalized.

### Critical Steps

1. **Scale normalization**: Each omic layer MUST be independently scaled before concatenation.
   Failure to do this lets high-variance layers dominate.
   - Transcriptomics: log2(CPM + 1) or variance-stabilizing transform (VST).
   - Proteomics: log2 intensity, median-centered.
   - Methylation: M-values (logit of beta), NOT raw beta values.
   - Metabolomics: log-transform, pareto scaling, or auto-scaling.

2. **Feature selection per layer**: Reduce each layer to top variable features BEFORE
   concatenation to avoid curse of dimensionality.
   - Transcriptomics: top 2,000–5,000 highly variable genes.
   - Proteomics: all detected proteins (typically <5,000).
   - Metabolomics: all detected metabolites after QC filtering.

3. **Block weighting**: After concatenation, optionally weight blocks so each layer contributes
   equally regardless of feature count. Methods: block-PCA, DIABLO block weights.

### Common Mistakes

- **Wrong:** Concatenating raw counts with normalized intensities across layers
  **Right:** Independently normalize each omic layer (log2-CPM for RNA, log2 intensity for proteomics, M-values for methylation) before concatenation
  **Why:** Mixing scales lets the unnormalized layer dominate variance and distort all downstream analyses

- **Wrong:** Not removing batch effects before concatenation
  **Right:** Apply batch correction (ComBat or equivalent) to each layer independently before merging
  **Why:** Batch effects in any single layer propagate into the combined matrix and confound integration

- **Wrong:** Using PCA on the concatenated matrix without block weighting
  **Right:** Apply block-PCA or DIABLO block weights so each layer contributes equally regardless of feature count
  **Why:** The layer with the most features dominates the first principal components, masking signal from smaller layers

---

## 3. Intermediate Integration

### Definition
Learn shared latent factors or kernels that capture cross-omic variation, then use those
factors for downstream analysis.

### Methods

#### 3a. MOFA+ (Multi-Omics Factor Analysis)

| Parameter | Guidance |
|---|---|
| Number of factors | Start with 15–25; MOFA+ prunes inactive factors automatically |
| Likelihoods | Gaussian for continuous data; Poisson for counts; Bernoulli for binary |
| Convergence | Default tolerance (0.01% ELBO change) is usually sufficient |
| Missing data | MOFA+ handles partial overlap natively — no imputation needed |
| Groups | Use for multi-site or multi-batch data; each group learns group-specific weights |

**Interpretation workflow**:
1. Rank factors by variance explained per view (omic layer).
2. Factors explaining variance in multiple views capture shared biology.
3. Factors explaining variance in one view capture omic-specific biology.
4. Extract top-weight features per factor for pathway enrichment.

#### 3b. iCluster / iCluster+

| Parameter | Guidance |
|---|---|
| Number of clusters (k) | Use BIC or gap statistic; test k = 2 to 8 |
| Penalty (lambda) | Tune via cross-validation; higher lambda = sparser solution |
| Data types | iCluster+ supports Gaussian, Binomial, Poisson per layer |
| Convergence | EM algorithm; may need 100+ iterations for large datasets |

**When to prefer iCluster over MOFA+**:
- Primary goal is patient subtyping (clustering), not factor discovery.
- Need sparse feature selection within the model.

#### 3c. Kernel Methods (SNF, MKL)

- **Similarity Network Fusion (SNF)**: Build per-omic patient similarity networks, fuse them.
  Good for heterogeneous data types. Sensitive to hyperparameters (K neighbors, iterations).
- **Multiple Kernel Learning (MKL)**: Combine per-omic kernels with learned weights.
  Good for classification tasks.

### Decision Sub-Tree for Intermediate Methods

```
Goal?
 ├─ Unsupervised factor discovery → MOFA+
 ├─ Patient subtyping with sparse features → iCluster+
 ├─ Patient subtyping, heterogeneous data → SNF
 └─ Supervised classification → MKL or DIABLO (mixOmics)
```

---

## 4. Late Integration

### Definition
Build separate models per omic layer, then combine predictions via ensemble methods.

### When to Use
- Small sample size (n < 50).
- Layers collected on different cohorts with minimal overlap.
- Need interpretable per-omic contributions.

### Combination Strategies

| Strategy | Description | When to Use |
|---|---|---|
| Simple averaging | Average predicted probabilities | Baseline; all layers equally trusted |
| Weighted averaging | Weight by per-omic cross-validated AUC | Layers have different predictive power |
| Stacking | Train meta-learner on per-omic predictions | Enough samples for a held-out meta-training set |
| Rank aggregation | Combine ranked feature lists (RRA, Stuart method) | Feature selection, not prediction |

### Common Mistakes

- **Wrong:** Using the same samples for per-omic model training and meta-learner training
  **Right:** Hold out a separate set of samples for the meta-learner, or use nested cross-validation
  **Why:** Training the meta-learner on the same data used for per-omic models causes data leakage and inflated performance estimates

- **Wrong:** Not calibrating per-omic probabilities before averaging
  **Right:** Apply Platt scaling or isotonic regression to each per-omic model's outputs before combining
  **Why:** Uncalibrated probabilities from different models are not on the same scale, making averages meaningless

- **Wrong:** Ignoring that late integration cannot discover cross-omic interactions
  **Right:** Acknowledge this limitation and use intermediate integration (MOFA+, DIABLO) when cross-omic interactions are the scientific question
  **Why:** Late integration treats each layer independently, so synergistic effects between layers are invisible

---

## 5. Batch Correction Across Omics

### Decision Framework

```
Is the batch variable confounded with biology (e.g., all cases from site A, all controls from site B)?
 ├─ YES → Batch correction WILL remove biology. Do NOT correct. Instead:
 │         - Include batch as covariate in downstream models.
 │         - Use mixed-effects models.
 │         - Report results stratified by batch.
 └─ NO → Proceed with correction.
         ├─ Continuous data (expression, methylation M-values, protein intensity)?
         │   ├─ Known batch variable → ComBat (parametric) or ComBat-seq (counts)
         │   └─ Unknown batch variable → SVA (surrogate variable analysis)
         └─ Count data (RNA-seq raw counts)?
             └─ ComBat-seq (preserves count distribution)
```

### ComBat Parameters

| Parameter | Guidance |
|---|---|
| Parametric vs non-parametric | Parametric is default and works well for most cases. Use non-parametric if batch effects are non-Gaussian (check with QQ plots). |
| Covariates to protect | ALWAYS include biological variables of interest (e.g., disease status, sex) as covariates. Omitting them risks removing real biology. |
| Reference batch | Optional. Set one batch as reference if it is the "gold standard" (e.g., largest site). |

### Validation After Batch Correction
1. PCA/UMAP colored by batch — batches should intermix.
2. PCA/UMAP colored by biology — biological groups should still separate.
3. Silhouette score by batch should decrease; by biology should remain stable or increase.
4. Differential expression results should be qualitatively similar before and after correction.

### Common Mistakes

- **Wrong:** Applying ComBat to data that has already been batch-corrected by another method
  **Right:** Apply only one batch correction method per dataset; if switching methods, start from the uncorrected data
  **Why:** Double correction introduces artificial variance structure and can remove real biological signal

- **Wrong:** Correcting each omic layer with different batch definitions
  **Right:** Use consistent batch labels across all omic layers (same batch variable for all)
  **Why:** Inconsistent batch definitions create misaligned corrections that introduce spurious cross-omic correlations

- **Wrong:** Running ComBat on the full dataset including test samples
  **Right:** Fit ComBat parameters on training samples only, then apply the learned correction to test samples
  **Why:** Including test samples in batch correction leaks information and inflates ML performance estimates

---

## 6. Handling Partial Sample Overlap

When not all samples are measured across all omic layers:

### Decision Framework

| Overlap Level | Strategy |
|---|---|
| ≥90% | Drop non-overlapping samples; proceed with complete cases |
| 70–90% | Use MOFA+ (handles missing views natively) or impute with KNN/MICE |
| 50–70% | Late integration preferred; or MOFA+ with careful validation |
| <50% | Late integration only; do NOT attempt joint factorization |

### Imputation Considerations
- KNN imputation across samples within a layer is acceptable for <10% missingness.
- Cross-omic imputation (predicting one layer from another) is experimental — validate heavily.
- NEVER impute more than 30% of a layer's values; use late integration instead.

---

## 7. Enrichment Methods for Multi-Omic Signatures

After identifying multi-omic factors or feature sets, interpret them biologically:

### Method Selection

| Method | Input | Best For |
|---|---|---|
| Over-representation analysis (ORA) | Gene list (thresholded) | Quick look; requires arbitrary cutoff |
| Gene Set Enrichment Analysis (GSEA) | Ranked gene list (all genes) | No threshold needed; captures subtle shifts |
| Multi-omic enrichment (ActivePathways) | P-values from multiple omics | Integrates evidence across layers |
| Network-based (STRING, PCNA) | Gene/protein list | Finding physical/functional interactions |

### Gene Set Databases

| Database | Content | Use Case |
|---|---|---|
| MSigDB Hallmark (H) | 50 curated gene sets | First pass; broad biological themes |
| MSigDB C2:CP (canonical pathways) | KEGG, Reactome, BioCarta | Pathway-level interpretation |
| MSigDB C5 (GO) | Gene Ontology terms | Biological process, molecular function |
| MSigDB C6 (oncogenic) | Oncogenic signatures | Cancer studies |
| Custom gene sets | Disease-specific or tissue-specific | When public sets are insufficient |

### Common Mistakes

- **Wrong:** Running ORA on a gene list from one omic layer and claiming "multi-omic" enrichment
  **Right:** Use multi-omic enrichment methods (ActivePathways) that integrate p-values across layers, or run enrichment on integrated factor loadings
  **Why:** Single-layer ORA does not leverage multi-omic evidence and misrepresents the analysis as integrated

- **Wrong:** Not correcting for multiple testing in gene set enrichment (or using Bonferroni)
  **Right:** Apply Benjamini-Hochberg FDR correction for gene set tests
  **Why:** Bonferroni is overly conservative for correlated gene sets; no correction produces massive false positives

- **Wrong:** Using KEGG pathways for non-model organisms without verifying pathway coverage
  **Right:** Check pathway annotation coverage for your species; use Reactome or custom gene sets if KEGG coverage is <50%
  **Why:** Sparse pathway annotations produce misleading enrichment results — absence of annotation is not absence of biology

- **Wrong:** Using the entire genome as the background set for over-representation analysis
  **Right:** Set the ORA background (universe) to all genes/proteins actually measured in the experiment
  **Why:** Using the full genome inflates significance by including thousands of genes that were never detectable in the assay

---

## 8. Reporting Checklist

Every multi-omics integration analysis MUST report:

1. **Data description**: Number of samples per layer, overlap matrix, feature counts.
2. **Normalization**: Method per layer, with justification.
3. **Batch correction**: Method, covariates protected, validation plots.
4. **Integration strategy**: Early/intermediate/late, with justification referencing sample size
   and overlap.
5. **Method parameters**: All non-default parameters for MOFA+, iCluster, SNF, etc.
6. **Validation**: Stability analysis (bootstrap or cross-validation), comparison to single-omic
   baselines.
7. **Enrichment**: Method, gene set database, FDR threshold, number of significant terms.
8. **Reproducibility**: Software versions, random seeds, data availability.

---

## When NOT to Use This Skill

- When only one omics layer is available (use single-omic analysis skills instead)
- Interpreting integrated results without domain context for the disease
- When sample sizes differ >10x between layers with no overlap strategy

## When to Escalate to a Human Expert

- When integrated signatures will inform clinical trial stratification
- When batch effects cannot be distinguished from biological signal
- When results contradict established biology for the disease area

## 9. Anti-Patterns to Flag

1. **Wrong:** Concatenating omic layers without independent scaling
   **Right:** Scale each layer independently (e.g., z-score or variance-stabilize) before concatenation
   **Why:** The high-variance layer dominates all downstream analyses, masking signal from other layers

2. **Wrong:** Running ComBat without including biological covariates in the model
   **Right:** Always include biological variables of interest (disease status, sex) as covariates to protect
   **Why:** Without protected covariates, ComBat removes real biological signal along with batch effects

3. **Wrong:** Imputing more than 30% of missing values in an omic layer
   **Right:** Use late integration instead of imputation when missingness exceeds 30%
   **Why:** Heavy imputation introduces artificial structure that does not reflect biology and distorts factor analysis

4. **Wrong:** Running MOFA+ with fewer than 20 samples
   **Right:** Use late integration or simple correlation analysis for very small sample sizes
   **Why:** MOFA+ requires sufficient samples for stable factor estimation; with <20 samples, factors are unreliable

5. **Wrong:** Reporting only the top factor from a multi-factor analysis
   **Right:** Report all factors explaining >5% variance in at least one view
   **Why:** Reporting only the top factor is cherry-picking; biologically important signals may appear in lower-ranked factors

6. **Wrong:** Not comparing multi-omic integration results to single-omic baselines
   **Right:** Always run single-omic analyses as baselines and demonstrate that integration adds value
   **Why:** Without a baseline comparison, you cannot assess whether integration actually improves over the best single-omic result

7. **Wrong:** Using gene symbols directly across species without ortholog mapping
   **Right:** Use proper ortholog databases (HGNC Comparison of Orthology Predictions, Ensembl Compara) for cross-species mapping
   **Why:** Ortholog mapping is non-trivial — many genes have no 1:1 ortholog, and symbol overlap does not guarantee functional equivalence

---

## 10. Glossary

| Term | Definition |
|---|---|
| View | A single omic layer (e.g., transcriptomics, proteomics) in MOFA+ terminology |
| Factor | A latent variable capturing shared or omic-specific variation |
| Block | A feature matrix from one omic layer in mixOmics/DIABLO terminology |
| Kernel | A similarity matrix computed from one omic layer |
| RAF | Risk Adjustment Factor (unrelated — see risk-adjustment skill) |
| ELBO | Evidence Lower Bound; MOFA+ convergence metric |
| BIC | Bayesian Information Criterion; used for selecting k in iCluster |
