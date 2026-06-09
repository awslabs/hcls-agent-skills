---
name: multi-omics-pipeline
description: >
  Pipeline skill for multi-omics data processing and integration. Use when the user asks to
  map gene IDs between HGNC Ensembl and UniProt, convert between omic data formats, run
  batch correction with ComBat or ComBat-seq, perform GSEA or over-representation analysis
  on multi-omic results, run consensus clustering on integrated data, execute MOFA2 in R
  or mofapy2 in Python, build a multi-omics ETL pipeline, harmonize feature identifiers
  across omics layers, or run clusterProfiler enrichment. Triggers include "map Ensembl to
  HGNC", "ID mapping omics", "ComBat code", "run MOFA2", "mofapy2", "GSEA Python",
  "fgsea R", "consensus clustering", "multi-omics pipeline", "gseapy", "biomaRt",
  "clusterProfiler", "mixOmics DIABLO".
usage: Invoke to generate executable code for multi-omics ID mapping, batch correction, factor analysis, enrichment, and consensus clustering.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {mofa2: "1.12", combat: "0.3.4", gseapy: "1.1"}
tags: [skill, category:pipeline, multi-omics, etl, hcls]
---

# Multi-Omics Pipeline — Pipeline Skill

## Overview

Provide deterministic, copy-paste-ready code for multi-omics data processing tasks: ID mapping,
batch correction, integration via MOFA2/mofapy2, enrichment analysis, and consensus clustering.

## Usage

- Map gene identifiers across HGNC, Ensembl, and UniProt systems
- Run batch correction (ComBat/ComBat-seq) and multi-omic factor analysis (MOFA2/mofapy2)
- Perform GSEA enrichment and consensus clustering on integrated data

## Core Concepts

---


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## 1. ID Mapping

### 1a. Python — HGNC Symbol ↔ Ensembl ↔ UniProt

```python
import pandas as pd
import mygene

mg = mygene.MyGeneInfo()

# Input: list of HGNC symbols
genes = ["TP53", "BRCA1", "EGFR", "KRAS"]

# Query multiple ID types at once
result = mg.querymany(
    genes,
    scopes="symbol",
    fields="ensembl.gene,uniprot.Swiss-Prot",
    species="human",
    returnall=True,
)

df = pd.DataFrame(result["out"])
# Handle many-to-many: explode nested Ensembl IDs
df_ensembl = df.explode("ensembl")
df_ensembl["ensembl_id"] = df_ensembl["ensembl"].apply(
    lambda x: x["gene"] if isinstance(x, dict) else None
)
print(df_ensembl[["query", "ensembl_id"]].dropna())
```

### 1b. R — biomaRt

```r
library(biomaRt)

ensembl <- useEnsembl(biomart = "genes", dataset = "hsapiens_gene_ensembl")

# Map HGNC symbols to Ensembl gene IDs and UniProt accessions
mapping <- getBM(
  attributes = c("hgnc_symbol", "ensembl_gene_id", "uniprotswissprot"),
  filters = "hgnc_symbol",
  values = c("TP53", "BRCA1", "EGFR", "KRAS"),
  mart = ensembl
)

# Remove rows with empty UniProt
mapping <- mapping[mapping$uniprotswissprot != "", ]
print(mapping)
```

### ID Mapping Parameter Table

| Parameter | Python (mygene) | R (biomaRt) |
|---|---|---|
| Input ID type | `scopes="symbol"` | `filters = "hgnc_symbol"` |
| Output ID types | `fields="ensembl.gene,uniprot.Swiss-Prot"` | `attributes = c("ensembl_gene_id", "uniprotswissprot")` |
| Species filter | `species="human"` | `dataset = "hsapiens_gene_ensembl"` |
| Many-to-many handling | Explode nested lists | Multiple rows returned automatically |

---

## 2. Batch Correction

### 2a. Python — ComBat (pycombat)

```python
from combat.pycombat import pycombat
import pandas as pd
import numpy as np

# expression_df: genes (rows) x samples (columns), log-transformed
# batch: list of batch labels, same order as columns
# covariates: DataFrame with biological covariates to protect

expression_df = pd.read_csv("expression_matrix.csv", index_col=0)
batch = [1, 1, 1, 2, 2, 2, 3, 3, 3]  # batch labels per sample

# Protect biological covariate (e.g., disease status)
covar_df = pd.DataFrame({"disease": [0, 0, 1, 0, 1, 1, 0, 1, 1]})

corrected = pycombat(
    expression_df,
    batch,
    mod=covar_df,       # biological covariates to protect
    par_prior=True,     # parametric adjustment (default)
)
```

### 2b. R — ComBat / ComBat-seq

```r
library(sva)

# For continuous data (log-transformed expression, protein intensity)
# expr_mat: genes x samples matrix
# batch: vector of batch labels
# mod: model matrix with biological covariates to protect

mod <- model.matrix(~ disease_status, data = sample_info)

corrected <- ComBat(
  dat = expr_mat,
  batch = sample_info$batch,
  mod = mod,
  par.prior = TRUE  # parametric
)

# For count data (RNA-seq raw counts) — use ComBat-seq
corrected_counts <- ComBat_seq(
  counts = count_mat,
  batch = sample_info$batch,
  group = sample_info$disease_status  # biological variable to protect
)
```

### Batch Correction Parameter Table

| Parameter | ComBat (continuous) | ComBat-seq (counts) |
|---|---|---|
| Input | Log-transformed matrix | Raw count matrix (integers) |
| Parametric prior | `par.prior = TRUE` (default) | Not applicable |
| Biological covariate | `mod` (model matrix) | `group` (vector) |
| Output | Corrected continuous matrix | Corrected count matrix |
| When to use | Proteomics, methylation M-values, log-expression | RNA-seq raw counts |

---

## 3. MOFA2 / mofapy2 Integration

### 3a. R — MOFA2

```r
library(MOFA2)

# Prepare data: list of matrices, one per omic layer
# Each matrix: features x samples
data_list <- list(
  transcriptomics = expr_mat,   # genes x samples
  proteomics = prot_mat,        # proteins x samples
  methylation = meth_mat        # CpG sites x samples
)

# Create MOFA object
mofa <- create_mofa(data_list)

# Set data options
data_opts <- get_default_data_options(mofa)

# Set model options
model_opts <- get_default_model_options(mofa)
model_opts$num_factors <- 20  # start with 20; inactive factors pruned automatically

# Set training options
train_opts <- get_default_training_options(mofa)
train_opts$convergence_mode <- "slow"  # more iterations for better convergence
train_opts$seed <- 42

# Prepare and run
mofa <- prepare_mofa(
  mofa,
  data_options = data_opts,
  model_options = model_opts,
  training_options = train_opts
)

mofa <- run_mofa(mofa, outfile = "mofa_model.hdf5")

# Inspect variance explained per factor per view
plot_variance_explained(mofa)

# Extract top features for factor 1
weights <- get_weights(mofa, views = "transcriptomics", factors = 1, as.data.frame = TRUE)
top_genes <- weights[order(abs(weights$value), decreasing = TRUE), ][1:50, ]
```

### 3b. Python — mofapy2

```python
from mofapy2.run.entry_point import entry_point
import numpy as np

# Prepare data: list of numpy arrays [views][groups]
# Each array: samples x features
data = [
    [expr_array],   # view 0: transcriptomics, group 0
    [prot_array],   # view 1: proteomics, group 0
    [meth_array],   # view 2: methylation, group 0
]

ent = entry_point()
ent.set_data_options(scale_groups=False, scale_views=True)
ent.set_data_matrix(data, views_names=["transcriptomics", "proteomics", "methylation"])

ent.set_model_options(factors=20, spikeslab_weights=True, ard_factors=True)
ent.set_train_options(iter=1000, convergence_mode="slow", seed=42)

ent.build()
ent.run()
ent.save("mofa_model.hdf5")
```

### MOFA Parameter Table

| Parameter | Default | Guidance |
|---|---|---|
| `num_factors` / `factors` | 10 | Set 15–25 for exploratory analysis; inactive factors auto-pruned |
| `convergence_mode` | `"fast"` | Use `"slow"` for final analysis; `"fast"` for exploration |
| `scale_views` | `TRUE` / `True` | MUST be True to equalize variance across views |
| `spikeslab_weights` | `TRUE` / `True` | Enables sparse feature selection per factor |
| `ard_factors` | `TRUE` / `True` | Automatic relevance determination; prunes inactive factors |
| `seed` | None | ALWAYS set for reproducibility |

---

## 4. GSEA Enrichment

### 4a. Python — gseapy

```python
import gseapy as gp
import pandas as pd

# ranked_genes: DataFrame with columns ["gene", "rank_metric"]
# rank_metric can be: log2FC, -log10(p) * sign(FC), or MOFA weight
ranked_genes = pd.read_csv("ranked_genes.csv")

# Pre-ranked GSEA against MSigDB Hallmark gene sets
result = gp.prerank(
    rnk=ranked_genes,
    gene_sets="MSigDB_Hallmark_2020",
    min_size=15,
    max_size=500,
    permutation_num=1000,
    seed=42,
    outdir="gsea_results",
)

# Filter significant results
sig = result.res2d[result.res2d["FDR q-val"] < 0.05]
print(sig[["Term", "NES", "FDR q-val"]].sort_values("NES", ascending=False))
```

### 4b. R — fgsea with clusterProfiler

```r
library(fgsea)
library(msigdbr)

# Get Hallmark gene sets for human
hallmark <- msigdbr(species = "Homo sapiens", category = "H")
pathways <- split(hallmark$gene_symbol, hallmark$gs_name)

# ranked_genes: named numeric vector (names = gene symbols, values = rank metric)
ranked_genes <- setNames(de_results$log2FoldChange, de_results$gene_symbol)
ranked_genes <- sort(ranked_genes, decreasing = TRUE)

# Run fgsea
fgsea_res <- fgsea(
  pathways = pathways,
  stats = ranked_genes,
  minSize = 15,
  maxSize = 500,
  nPermSimple = 10000
)

# Filter and sort
sig_pathways <- fgsea_res[fgsea_res$padj < 0.05, ]
sig_pathways <- sig_pathways[order(sig_pathways$NES, decreasing = TRUE), ]
print(sig_pathways[, c("pathway", "NES", "padj")])
```

### Enrichment Parameter Table

| Parameter | gseapy (Python) | fgsea (R) |
|---|---|---|
| Gene set source | `"MSigDB_Hallmark_2020"` or GMT file | `msigdbr()` + `split()` |
| Min gene set size | `min_size=15` | `minSize = 15` |
| Max gene set size | `max_size=500` | `maxSize = 500` |
| Permutations | `permutation_num=1000` | `nPermSimple = 10000` |
| Significance threshold | `FDR q-val < 0.05` | `padj < 0.05` |
| Rank metric | log2FC, signed -log10(p), or MOFA weight | Same |

---

## 5. Consensus Clustering

### Python — scikit-learn based consensus

```python
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

def consensus_clustering(data, k_range=range(2, 9), n_iterations=100, seed=42):
    """Run consensus clustering over a range of k values.
    data: samples x features array. Returns dict mapping k to results.
    """
    rng = np.random.default_rng(seed)
    n_samples = data.shape[0]
    results = {}

    for k in k_range:
        co_occurrence = np.zeros((n_samples, n_samples))
        co_sampled = np.zeros((n_samples, n_samples))

        for _ in range(n_iterations):
            # Subsample 80% of samples
            idx = rng.choice(n_samples, size=int(0.8 * n_samples), replace=False)
            km = KMeans(n_clusters=k, n_init=10, random_state=rng.integers(1e6))
            labels = km.fit_predict(data[idx])

            for i in range(len(idx)):
                for j in range(i + 1, len(idx)):
                    co_sampled[idx[i], idx[j]] += 1
                    co_sampled[idx[j], idx[i]] += 1
                    if labels[i] == labels[j]:
                        co_occurrence[idx[i], idx[j]] += 1
                        co_occurrence[idx[j], idx[i]] += 1

        # Consensus matrix
        with np.errstate(divide="ignore", invalid="ignore"):
            consensus = np.where(co_sampled > 0, co_occurrence / co_sampled, 0)

        # Final clustering on consensus matrix
        km_final = KMeans(n_clusters=k, n_init=10, random_state=seed)
        final_labels = km_final.fit_predict(1 - consensus)  # distance = 1 - consensus
        sil = silhouette_score(1 - consensus, final_labels, metric="precomputed")

        results[k] = {"consensus_matrix": consensus, "silhouette": sil, "labels": final_labels}
        print(f"k={k}: silhouette={sil:.3f}")

    return results

# Usage with MOFA factors
# factors: samples x factors array from MOFA
results = consensus_clustering(factors, k_range=range(2, 9))

# Select optimal k by maximum silhouette score
optimal_k = max(results, key=lambda k: results[k]["silhouette"])
print(f"Optimal k: {optimal_k}")
```

### R — ConsensusClusterPlus

```r
library(ConsensusClusterPlus)
# input_mat: features x samples
results <- ConsensusClusterPlus(
  d = input_mat,
  maxK = 8,
  reps = 1000,
  pItem = 0.8,        # proportion of samples to subsample
  pFeature = 1,       # use all features
  clusterAlg = "km",  # k-means
  distance = "euclidean",
  seed = 42,
  plot = "pdf",
  title = "consensus_clustering"
)

# Inspect consensus CDF and delta area plots in output PDF
# Select k where CDF curve is flattest (highest consensus)
```

### Consensus Clustering Parameter Table

| Parameter | Python (custom) | R (ConsensusClusterPlus) |
|---|---|---|
| k range | `k_range=range(2, 9)` | `maxK = 8` |
| Iterations | `n_iterations=100` | `reps = 1000` |
| Subsample fraction | 0.8 (hardcoded) | `pItem = 0.8` |
| Algorithm | KMeans | `clusterAlg = "km"` |
| Selection criterion | Silhouette score | CDF delta area plot |


---

## Common Mistakes

- **Wrong:** Mapping gene IDs using symbol-based joins without handling duplicates or deprecated symbols
  **Right:** Use HGNC ID or Ensembl stable ID as the primary key; resolve ambiguous symbols via the HGNC multi-symbol checker
  **Why:** Gene symbols are not unique (e.g., "MARCH1" was renamed to "MARCHF1") — symbol joins silently drop or duplicate rows

- **Wrong:** Running ComBat without including biological covariates in the model matrix
  **Right:** Always pass `mod = model.matrix(~ disease_status + sex, data=meta)` to protect biological signal
  **Why:** Without protected covariates, ComBat removes biological variation that correlates with batch

- **Wrong:** Using `mofapy2` with raw counts instead of normalized, variance-stabilized data
  **Right:** Apply log2(CPM+1) or VST to RNA-seq counts before passing to MOFA; use log2 intensity for proteomics
  **Why:** MOFA assumes Gaussian-distributed continuous data — raw counts violate this and produce meaningless factors

- **Wrong:** Running gseapy/fgsea with a gene list ranked by fold change alone (no significance weighting)
  **Right:** Rank by `-log10(p) × sign(log2FC)` or use the Wald statistic from DESeq2/limma
  **Why:** Fold-change-only ranking treats noisy large-FC genes the same as significant ones, inflating false enrichments

- **Wrong:** Using default `min_size=1` in fgsea, allowing tiny gene sets to appear significant
  **Right:** Set `minSize=15, maxSize=500` to filter gene sets to biologically interpretable sizes
  **Why:** Very small gene sets produce unstable enrichment scores; very large sets are too generic to be informative
