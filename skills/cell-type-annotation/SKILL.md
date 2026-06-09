---
name: cell-type-annotation
description: Generate code to assign cell type labels to single-cell RNA-seq clusters using CellTypist, SingleR, marker-based annotation, or reference label transfer (scANVI/ingest). Triggers on requests to "annotate cell types", "label clusters", "run CellTypist", "SingleR annotation", "marker gene dotplot", "transfer labels from reference atlas", "cell identity", "automated annotation", "reference mapping", "scANVI label transfer", "canonical markers", "immune cell types", "hierarchical annotation", "majority voting CellTypist", "over-clustering annotation".
usage: Invoke when annotating cell types in scRNA-seq data using CellTypist, SingleR, marker genes, or reference label transfer.
version: 1.1.0
validated_against:
  date: 2025-01-15
  packages: {celltypist: "1.6", scanpy: "1.10"}
tags: [skill, category:pipeline, single-cell, cell-type, celltypist, annotation, hcls]
---

# Cell Type Annotation

## Overview

This pipeline skill generates code for annotating cell types in single-cell RNA-seq data. It covers four complementary approaches:

1. **Automated** — CellTypist (logistic-regression classifiers trained on curated atlases).
2. **Reference-based** — SingleR (R) or scANVI/`sc.tl.ingest` (Python) label transfer.
3. **Marker-based** — Manual assignment from canonical marker gene panels.
4. **Hierarchical** — Coarse compartment assignment followed by specialized fine-grained annotation.

Use it when the user has a clustered `AnnData` (or `SingleCellExperiment`) and needs cell-type labels in `adata.obs`.

## Usage

### Decision Tree: Choosing an Annotation Approach

Follow this decision tree to select the right method:

1. **Is there a CellTypist model matching your tissue and species?**
   - YES → Use CellTypist (Steps 1–6 below)
   - NO → Go to step 2
2. **Do you have a labeled reference AnnData from the same tissue?**
   - YES, same batch/technology → Use `sc.tl.ingest` (Step 12)
   - YES, different batches → Use scANVI label transfer (Step 13)
   - NO → Go to step 3
3. **Are you working in R with bulk or sorted-cell references?**
   - YES → Use SingleR (Steps 7–9)
   - NO → Go to step 4
4. **Do you have canonical marker gene panels for expected cell types?**
   - YES → Use marker-based annotation (Steps 10–11)
   - NO → Start with CellTypist's broadest model (`Immune_All_Low.pkl` or `Developing_Human_Brain.pkl`), then refine with markers

### Annotation Workflow (15 Steps)

**Step 1 — Confirm normalization.** CellTypist requires `log1p(CP10k)`. Check `adata.uns['log1p']` exists or run normalization. If data is in `adata.raw` or a layer, subset appropriately.

**Step 2 — Verify gene symbols.** Confirm `adata.var_names` are HGNC (human) or MGI (mouse) symbols, not Ensembl IDs. Convert if needed with `sc.queries.biomart_annotations`.

**Step 3 — Select CellTypist model.** Match species + tissue. Use `celltypist.models.models_description()` to list options. If unsure, start with the broadest model for the compartment.

**Step 4 — Run CellTypist annotation.** Use `celltypist.annotate()` with `majority_voting=True` and appropriate `p_thres` (default 0.5; raise to 0.7 for stringent calls).

**Step 5 — Extract results via `to_adata()`.** Call `predictions.to_adata()` to get annotations in `.obs`. Access confidence via `adata_result.obs['conf_score']`.

**Step 6 — Filter low-confidence cells.** Mask cells with `conf_score < 0.5` (or user-specified threshold) as `'Unknown'`.

**Step 7 — (SingleR) Install references.** Use `BiocManager::install("celldex")` and load the appropriate reference dataset.

**Step 8 — (SingleR) Run prediction.** Call `SingleR(test, ref, labels)` with `assay.type.test = "logcounts"`.

**Step 9 — (SingleR) Prune low-quality calls.** Use `pruneScores(pred)` to identify unreliable assignments; set those to `"Unknown"`.

**Step 10 — (Marker-based) Define panels.** Provide ≥3 markers per cell type from literature. Include negative markers where informative.

**Step 11 — (Marker-based) Score and assign.** Use `sc.pl.dotplot` to visualize, then map clusters to types. Leave ambiguous clusters as `'Unknown'`.

**Step 12 — (Ingest) Project query onto reference.** Requires shared PCA space; run `sc.tl.ingest(adata_query, adata_ref, obs='cell_type')`. Only works well when query and reference share the same technology and minimal batch effects.

**Step 13 — (scANVI) Semi-supervised transfer.** Train SCVI on reference, extend to SCANVI with labels, then `load_query_data` for the query. Handles batch effects natively.

**Step 14 — Validate annotations.** Confirm with dotplot of canonical markers grouped by assigned cell type. Check per-sample proportions for biological plausibility.

**Step 15 — Hierarchical refinement.** If fine labels are unstable, annotate coarse compartments first (immune/stromal/epithelial via PTPRC/EPCAM/COL1A1), subset, then re-annotate each with a specialized model or markers.

### Branch Points

- At Step 4: if `>30%` of cells get `conf_score < 0.5`, the model is a poor fit → switch to marker-based or try a different model.
- At Step 6: if a single label dominates `>80%` of cells unexpectedly, suspect wrong model or un-normalized data.
- At Step 12: if query UMAP doesn't align with reference after ingest, batch effects are too strong → switch to scANVI (Step 13).
- At Step 14: if proportions are biologically implausible (e.g., 60% fibroblasts in PBMC), re-examine normalization and model choice.

## Response Format

- Lead with the command or code the user needs — explain after.
- Structure as: confirm inputs → working code → key parameters explained → gotchas.
- One complete working example per task; do not show every alternative.
- Keep code comments minimal and functional.
- Target: 50–100 lines of code with brief surrounding explanation.
- Always include confidence score extraction and a filtering step.

## Core Concepts

### 1. CellTypist (automated, Python)

```python
import scanpy as sc
import celltypist
from celltypist import models

# Input: log1p-normalized to 10,000 counts/cell
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# Download models (first run only)
models.download_models()
print(models.models_description())  # list available models

# Load tissue-matched model
model = models.Model.load(model='Immune_All_Low.pkl')

# Annotate with majority voting
predictions = celltypist.annotate(
    adata,
    model=model,
    majority_voting=True,       # smooth labels over neighborhood graph
    over_clustering='leiden',   # obs key for majority voting resolution
    p_thres=0.5,               # minimum probability threshold (raise for stringency)
)

# Extract results — modern API (CellTypist >=1.3)
adata_result = predictions.to_adata()
# Annotations now in adata_result.obs:
#   'predicted_labels'        — per-cell raw predictions
#   'majority_voting'         — smoothed labels
#   'conf_score'              — max probability per cell

# Transfer to original adata
adata.obs['cell_type'] = adata_result.obs['majority_voting']
adata.obs['cell_type_conf'] = adata_result.obs['conf_score']

# Filter low-confidence assignments
adata.obs.loc[adata.obs['cell_type_conf'] < 0.5, 'cell_type'] = 'Unknown'
```

**Key parameters for `celltypist.annotate()`:**

| Parameter | Default | Effect |
|-----------|---------|--------|
| `majority_voting` | `False` | Smooth labels over kNN graph; always enable |
| `over_clustering` | `None` | obs key (e.g., `'leiden'`) for voting resolution; finer clusters → better resolution |
| `p_thres` | `0.5` | Min probability to assign a label; raise to 0.7 for high-confidence only |
| `mode` | `'best match'` | Use `'prob match'` for multi-label scenarios |

Common models: `Immune_All_Low`, `Immune_All_High`, `Healthy_COVID19_PBMC`, `Human_Lung_Atlas`, `Cells_Intestinal_Tract`, `Developing_Human_Brain`, `Adult_Mouse_Gut`. Match species and tissue.

### 2. SingleR (reference-based, R)

```r
if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
BiocManager::install(c("SingleR", "celldex", "SingleCellExperiment"))

library(SingleR)
library(celldex)
library(SingleCellExperiment)

# Choose reference matching species/tissue
ref <- celldex::HumanPrimaryCellAtlasData()
# ref <- celldex::MonacoImmuneData()       # sorted human immune
# ref <- celldex::ImmGenData()             # mouse immune
# ref <- celldex::BlueprintEncodeData()    # human stromal + immune

pred <- SingleR(
    test = sce,
    ref = ref,
    labels = ref$label.main,
    assay.type.test = "logcounts"
)

sce$cell_type <- pred$labels
table(pred$labels)

# Prune low-confidence calls (delta < median - 3*MAD)
sce$cell_type[is.na(pred$pruned.labels)] <- "Unknown"
```

### 3. Marker-based (manual, Python)

```python
import scanpy as sc

marker_genes = {
    'T cells':      ['CD3D', 'CD3E', 'CD2'],
    'CD4 T':        ['CD4', 'IL7R'],
    'CD8 T':        ['CD8A', 'CD8B'],
    'B cells':      ['CD79A', 'MS4A1', 'CD19'],
    'NK cells':     ['NKG7', 'GNLY', 'KLRD1'],
    'Monocytes':    ['CD14', 'LYZ', 'S100A8'],
    'Dendritic':    ['FCER1A', 'CST3', 'CLEC10A'],
    'Fibroblasts':  ['COL1A1', 'DCN', 'COL3A1'],
    'Endothelial':  ['PECAM1', 'VWF', 'CDH5'],
    'Epithelial':   ['EPCAM', 'KRT18', 'KRT19'],
}

sc.pl.dotplot(adata, marker_genes, groupby='leiden', standard_scale='var')

# Assign after reviewing the dotplot
cluster_to_celltype = {
    '0': 'T cells', '1': 'Monocytes', '2': 'B cells',
    '3': 'NK cells', '4': 'Unknown',
}
adata.obs['cell_type'] = adata.obs['leiden'].map(cluster_to_celltype).astype('category')
```

### 4. Label transfer from a reference atlas

```python
# Quick path: sc.tl.ingest (PCA/UMAP projection, kNN labels)
# Only use when batch effects are minimal
import scanpy as sc
sc.pp.pca(adata_ref)
sc.pp.neighbors(adata_ref)
sc.tl.umap(adata_ref)
sc.tl.ingest(adata_query, adata_ref, obs='cell_type')

# Robust path: scANVI (semi-supervised, handles batch)
import scvi
scvi.model.SCVI.setup_anndata(adata_ref, batch_key='batch')
scvi_model = scvi.model.SCVI(adata_ref)
scvi_model.train()

scvi.model.SCANVI.setup_anndata(
    adata_ref, labels_key='cell_type', unlabeled_category='Unknown', batch_key='batch'
)
scanvi_model = scvi.model.SCANVI.from_scvi_model(scvi_model, unlabeled_category='Unknown')
scanvi_model.train(max_epochs=20)

scanvi_model = scvi.model.SCANVI.load_query_data(adata_query, scanvi_model)
scanvi_model.train(max_epochs=100, plan_kwargs={'weight_decay': 0.0})
adata_query.obs['cell_type_pred'] = scanvi_model.predict(adata_query)
```

### 5. Validation

```python
# Confirm assigned labels express their markers
sc.pl.dotplot(adata, marker_genes, groupby='cell_type', standard_scale='var')
sc.pl.violin(adata, ['CD3D', 'MS4A1', 'CD14'], groupby='cell_type', rotation=90)

# Sanity-check proportions per sample
adata.obs.groupby(['sample', 'cell_type']).size().unstack(fill_value=0)
```

Mark any cluster without clear marker support as `'Unknown'` rather than forcing a label.

### 6. Hierarchical annotation

```python
# Step 1: coarse compartments
compartment_markers = {
    'Immune':     ['PTPRC'],           # CD45
    'Epithelial': ['EPCAM', 'KRT8'],
    'Stromal':    ['COL1A1', 'PECAM1'],
}
# Step 2: subset and re-annotate each compartment
adata_immune = adata[adata.obs['compartment'] == 'Immune'].copy()
model = models.Model.load('Immune_All_Low.pkl')
preds = celltypist.annotate(adata_immune, model=model, majority_voting=True)
adata_immune_result = preds.to_adata()
adata_immune.obs['cell_type_fine'] = adata_immune_result.obs['majority_voting']
```

## Quick Reference

| Task | Tool | Key call |
| --- | --- | --- |
| PBMC / immune automated | CellTypist | `models.Model.load('Immune_All_Low.pkl')` |
| Lung atlas mapping | CellTypist | `'Human_Lung_Atlas.pkl'` |
| Gut / intestine | CellTypist | `'Cells_Intestinal_Tract.pkl'` |
| Broad human ref (R) | SingleR | `celldex::HumanPrimaryCellAtlasData()` |
| Sorted immune ref (R) | SingleR | `celldex::MonacoImmuneData()` |
| Mouse immune (R) | SingleR | `celldex::ImmGenData()` |
| Query→reference transfer | scanpy | `sc.tl.ingest(adata_q, adata_ref, obs='cell_type')` |
| Batch-aware transfer | scvi-tools | `SCANVI.load_query_data(...)` |
| Marker review | scanpy | `sc.pl.dotplot(adata, markers, groupby='leiden')` |
| Confidence (CellTypist) | CellTypist | `predictions.to_adata().obs['conf_score']` |
| Confidence (SingleR) | SingleR | `is.na(pred$pruned.labels)` flags low-quality |

Required inputs:
- CellTypist: `adata.X` = log1p(CP10k) normalized, genes as HGNC symbols in `adata.var_names`.
- SingleR: `SingleCellExperiment` with a `logcounts` assay.
- scANVI: raw counts in `adata.layers['counts']`, `batch_key`, `labels_key` on reference.

### Numeric Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| CellTypist `conf_score` | < 0.5 | Label as `'Unknown'` |
| CellTypist `conf_score` | < 0.7 | Flag for manual review |
| CellTypist `p_thres` | 0.5 (default) | Raise to 0.7 for stringent annotation |
| SingleR delta score | < median - 3×MAD | Pruned (set to `NA`) |
| Cluster size | < 20 cells | Do not assign rare subtypes; use parent label |
| Marker dotplot fraction | < 0.3 | Marker not reliably expressed; do not use for assignment |
| Expected proportion deviation | > 3× literature range | Suspect wrong model or normalization error |

## Common Mistakes

1. **Wrong:** Feeding raw counts to CellTypist
   **Right:** Always run `sc.pp.normalize_total(adata, target_sum=1e4)` + `sc.pp.log1p(adata)` before annotation
   **Why:** CellTypist expects log1p of counts normalized to 10,000/cell — raw or SCTransform'd data produces nonsense labels

2. **Wrong:** Using a reference model that doesn't match the tissue or species
   **Right:** Match species (`Human_*` vs `Mouse_*`) and tissue type when selecting CellTypist models or SingleR references
   **Why:** Using `Immune_All_Low` on epithelial tumor cells or `HumanPrimaryCellAtlasData` on mouse data produces confident but wrong labels

3. **Wrong:** Passing Ensembl IDs or mixed-case gene symbols to CellTypist/SingleR
   **Right:** Convert `adata.var_names` to HGNC (human) or MGI (mouse) symbols before annotation
   **Why:** Ensembl IDs or wrong case (`Cd3d` vs `CD3D`) silently drop features, degrading model performance without warning

4. **Wrong:** Using `predictions.probability_matrix.max(axis=1)` to get confidence scores
   **Right:** Use `predictions.to_adata().obs['conf_score']` which is the stable API since CellTypist ≥1.3
   **Why:** The probability matrix approach is fragile and version-dependent — it may break or return incorrect values across updates

5. **Wrong:** Assigning a rare subtype label to a cluster of fewer than 20 cells
   **Right:** Collapse to the parent cell type or label as `'Unknown'` when cluster size is below 20 cells
   **Why:** Rare subtype assignments on tiny clusters lack statistical power and are unreliable without strong distinguishing markers

6. **Wrong:** Forcing a label on clusters that lack clear markers after dotplot review
   **Right:** Keep ambiguous clusters as `'Unknown'` rather than picking the next-best guess
   **Why:** Forced labels propagate errors into downstream analyses (DE, trajectory) and create false biological narratives

7. **Wrong:** Running CellTypist with `majority_voting=False` and using per-cell labels directly
   **Right:** Always enable `majority_voting=True` to smooth labels over the local neighborhood graph
   **Why:** Per-cell predictions are noisy; majority voting leverages cluster structure to produce coherent, stable annotations

8. **Wrong:** Running `sc.tl.ingest` for label transfer without batch correction
   **Right:** Integrate query and reference first, or use scANVI's `load_query_data` path which handles batch natively
   **Why:** `ingest` assumes query and reference share the same embedding — batch effects cause misalignment and wrong label transfers

9. **Wrong:** Not validating cell-type proportions against biological expectations
   **Right:** Always cross-check per-sample cell-type proportions against known tissue composition
   **Why:** A PBMC sample with 80% fibroblasts is a red flag indicating wrong model, normalization error, or data quality issues

10. **Wrong:** Annotating at one resolution only without hierarchical refinement
    **Right:** Annotate coarse compartments first (immune/stromal/epithelial), then refine each with specialized models or markers
    **Why:** Fine labels on poorly separated clusters are unstable — hierarchical annotation produces more reliable results

## References

- CellTypist: Dominguez Conde et al. Science 2022, https://doi.org/10.1126/science.abl5197
- SingleR: Aran et al. Nat Immunol 2019, https://doi.org/10.1038/s41590-018-0276-y
- scANVI: Xu et al. Mol Syst Biol 2021, https://doi.org/10.15252/msb.20209620
- celldex: Aran et al. 2019, https://bioconductor.org/packages/celldex
