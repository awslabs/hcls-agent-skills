---
name: scrna-seq-pipeline
description: Scanpy-based single-cell RNA-seq analysis pipeline covering loading (10X, h5ad), QC, normalization, HVG selection, PCA/UMAP, Leiden clustering, differential expression, and batch correction (Harmony, scVI). Use when the user mentions single-cell, scRNA-seq, Scanpy, AnnData, UMAP, clustering, 10X, h5ad, leiden, highly variable genes, Harmony, scVI, cluster cells, find marker genes, filter low-quality cells, gene expression matrix, doublet removal, normalize counts, dimensionality reduction, cell clustering, QC single-cell, filtered_feature_bc_matrix, cellranger output, 10X h5, scrublet, cell ranger, count matrix, find cell types, batch effect, integration, neighborhood graph, or differential expression genes.
usage: Invoke when processing scRNA-seq data with Scanpy, including QC, normalization, clustering, DE, or batch correction.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {scanpy: "1.10", anndata: "0.10", scvi-tools: "1.1"}
tags: [skill, category:pipeline, single-cell, scanpy, scrna-seq, hcls]
---

# scRNA-seq Pipeline (Scanpy)

## Overview

This skill produces a reproducible scRNA-seq analysis in Python using Scanpy and AnnData. It covers the standard workflow: load counts → QC filter → normalize/log → HVG → scale/PCA → neighbors/UMAP → Leiden → differential expression, plus batch correction with Harmony or scVI. Default parameters follow the Scanpy PBMC3k tutorial conventions and are safe starting points for most 10X Genomics datasets.

Output is a single `.h5ad` file with all intermediate embeddings, cluster labels, and DE results stored on the `AnnData` object.

## Usage

Install dependencies:

```bash
pip install "scanpy>=1.10" anndata leidenalg python-igraph harmonypy scvi-tools
```

Run the pipeline end-to-end:

```python
import scanpy as sc
import scanpy.external as sce

sc.settings.verbosity = 2
sc.settings.set_figure_params(dpi=100, facecolor="white")

# 1. Load
adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")
# Alternatives:
# adata = sc.read_10x_mtx("filtered_feature_bc_matrix/", var_names="gene_symbols", cache=True)
# adata = sc.read_h5ad("input.h5ad")
adata.var_names_make_unique()

# 2. QC
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], percent_top=None, log1p=False, inplace=True)
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs.n_genes_by_counts < 5000, :]
adata = adata[adata.obs.pct_counts_mt < 20, :].copy()

# 3. Normalize + HVG
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
adata.raw = adata  # freeze log-normalized full gene set BEFORE HVG subset
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat")
adata = adata[:, adata.var.highly_variable].copy()

# 4. Scale + PCA + neighbors + UMAP + Leiden
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, n_comps=50, svd_solver="arpack")
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)

# 5. Differential expression per cluster
sc.tl.rank_genes_groups(adata, groupby="leiden", method="wilcoxon")

# 6. Save
adata.write("result.h5ad", compression="gzip")
```

### Batch correction — Harmony

```python
# Assumes adata.obs["batch"] exists and PCA is already computed.
sce.pp.harmony_integrate(adata, key="batch")  # writes adata.obsm["X_pca_harmony"]
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30, use_rep="X_pca_harmony")
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)
```

### Batch correction — scVI

scVI requires **raw counts**. Run it before normalization, or keep a raw-count layer.

```python
import scvi

# adata_raw holds unnormalized integer counts; adata.obs["batch"] is the batch key.
scvi.model.SCVI.setup_anndata(adata_raw, batch_key="batch")
model = scvi.model.SCVI(adata_raw, n_latent=30)
model.train(max_epochs=400, early_stopping=True)
adata.obsm["X_scVI"] = model.get_latent_representation()

sc.pp.neighbors(adata, n_neighbors=15, use_rep="X_scVI")
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)
```


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

- **AnnData layout.** `adata.X` is the current expression matrix (cells × genes). `adata.obs` holds per-cell metadata (QC metrics, cluster labels, batch). `adata.var` holds per-gene metadata (HVG flags, `mt`). Embeddings live in `adata.obsm` (`X_pca`, `X_umap`, `X_scVI`). Neighbor graph and DE results live in `adata.uns`.
- **`.raw` snapshot.** `adata.raw = adata` stores the full log-normalized matrix before HVG subsetting. Downstream plotting functions (`sc.pl.umap(..., color="GENE")`, `sc.pl.rank_genes_groups`) read from `.raw` so you can visualize any gene even after restricting `adata` to HVGs.
- **QC thresholds are dataset-dependent.** `n_genes ∈ [200, 5000]` and `pct_mt < 20` are reasonable defaults for human 10X PBMC-like data. Inspect distributions (`sc.pl.violin`) before committing. Use `MT-` for human and `mt-` for mouse.
- **HVG flavor matters.** Use `flavor="seurat"` on **log-normalized** data (default). Use `flavor="seurat_v3"` on **raw counts** — it expects integer counts and will error or mislead on log data.
- **Neighbors parameters.** `n_neighbors` controls local/global structure (10–50; larger = smoother UMAP). `n_pcs` should capture the elbow in `sc.pl.pca_variance_ratio` (typically 20–50). Leiden `resolution` controls cluster granularity (0.2–1.5; higher = more clusters).
- **Batch correction choice.** Harmony is fast, operates on PCA, and works well for mild-to-moderate batch effects. scVI is a deep generative model, needs raw counts and GPU for speed, and handles stronger technical variation and multi-modal designs.

## Quick Reference

### Loading

| Input | Call |
| --- | --- |
| 10X HDF5 | `sc.read_10x_h5("filtered_feature_bc_matrix.h5")` |
| 10X MTX dir | `sc.read_10x_mtx("path/", var_names="gene_symbols", cache=True)` |
| Existing AnnData | `sc.read_h5ad("input.h5ad")` |
| Always after load | `adata.var_names_make_unique()` |

### Key parameter ranges

| Parameter | Default | Typical range | Notes |
| --- | --- | --- | --- |
| `filter_cells(min_genes=)` | 200 | 100–500 | Drop empty/low-quality droplets |
| `filter_genes(min_cells=)` | 3 | 3–10 | Drop rarely-expressed genes |
| `n_genes_by_counts <` | 5000 | 2500–8000 | Upper bound flags doublets |
| `pct_counts_mt <` | 20 | 5–25 | Human tissue dependent |
| `normalize_total(target_sum=)` | `1e4` | `1e4` | CP10k; standard |
| `n_top_genes` (HVG) | 2000 | 1000–5000 | More HVGs → more signal + noise |
| `scale(max_value=)` | 10 | 10 | Clip extreme z-scores |
| `pca(n_comps=)` | 50 | 30–100 | Pick elbow for downstream `n_pcs` |
| `neighbors(n_neighbors=)` | 15 | 10–50 | Larger → smoother manifold |
| `neighbors(n_pcs=)` | 30 | 20–50 | ≤ `n_comps` |
| `leiden(resolution=)` | 0.5 | 0.2–1.5 | Higher → more clusters |

### DE & inspection

```python
sc.tl.rank_genes_groups(adata, groupby="leiden", method="wilcoxon")
sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False)

# Top-N markers per cluster as a DataFrame
import pandas as pd
result = adata.uns["rank_genes_groups"]
groups = result["names"].dtype.names
markers = pd.DataFrame({g: result["names"][g][:20] for g in groups})
```

### Saving / loading

```python
adata.write("result.h5ad", compression="gzip")
adata = sc.read_h5ad("result.h5ad")
```

## Common Mistakes

- **Wrong:** Subsetting to HVGs before saving `adata.raw = adata`
  **Right:** Always set `.raw` on the log-normalized full matrix before `adata = adata[:, adata.var.highly_variable].copy()`
  **Why:** Without `.raw`, you lose the ability to plot or score non-HVG genes in downstream analysis

- **Wrong:** Using `flavor="seurat_v3"` on log-normalized data
  **Right:** Match HVG flavor to data state: `seurat_v3` requires raw integer counts; `seurat` (default) requires log-normalized data
  **Why:** Wrong flavor produces nonsense HVG rankings or errors, corrupting all downstream steps

- **Wrong:** Skipping `adata.var_names_make_unique()` after loading 10X data
  **Right:** Call `adata.var_names_make_unique()` immediately after loading
  **Why:** Duplicated gene symbols cause silent misbehavior in indexing, HVG selection, and DE analysis

- **Wrong:** Running scVI on normalized/log-transformed data
  **Right:** Feed scVI the raw-count AnnData and set `batch_key` via `setup_anndata`
  **Why:** scVI models counts directly; normalized input violates its distributional assumptions and produces incorrect latent spaces

- **Wrong:** Using `MT-` prefix for mouse mitochondrial genes (or `mt-` for human)
  **Right:** Use `MT-` for human genes and `mt-` for mouse genes
  **Why:** Wrong prefix makes `pct_counts_mt` always zero, rendering the QC filter a no-op

- **Wrong:** Boolean-slicing AnnData without calling `.copy()`
  **Right:** Always use `.copy()` after filtering: `adata = adata[mask, :].copy()`
  **Why:** Without `.copy()`, the result is a view; subsequent in-place operations will warn or fail

## References

- Scanpy: Wolf et al. Genome Biol 2018, https://doi.org/10.1186/s13059-017-1382-0
- Scanpy tutorials: https://scanpy.readthedocs.io/en/stable/tutorials.html
- scVI: Gayoso et al. Nat Biotechnol 2022, https://doi.org/10.1038/s41587-021-01206-w
- Harmony: Korsunsky et al. Nat Methods 2019, https://doi.org/10.1038/s41592-019-0619-0
