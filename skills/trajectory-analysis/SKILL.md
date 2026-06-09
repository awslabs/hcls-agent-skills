---
name: trajectory-analysis
description: Single-cell trajectory inference pipeline covering diffusion pseudotime (DPT), PAGA, RNA velocity with scVelo, and fate mapping with CellRank. Use when the user mentions pseudotime, trajectory, lineage, differentiation, RNA velocity, scVelo, CellRank, PAGA, diffusion map, fate probabilities, terminal states, spliced/unspliced, velocyto, order cells by development, cell differentiation path, cell fate, branching analysis, monocle, developmental trajectory, stem cell differentiation, progenitor to mature, how do cells differentiate, cell lineage tree, velocity arrows, fate mapping, transition probabilities, root cells, terminal states, absorption probabilities, or latent time.
usage: Invoke when inferring cell trajectories, computing pseudotime, running RNA velocity, or mapping cell fate probabilities.
version: 2.0.0
validated_against:
  date: 2025-01-15
  packages: {scvelo: "0.3.2", cellrank: "2.0", scanpy: "1.10"}
tags: [skill, category:pipeline, single-cell, trajectory, pseudotime, rna-velocity, hcls]
---

# Trajectory Analysis

## Overview

Reconstructs continuous cell-state transitions from single-cell RNA-seq. Four layers:

1. **Diffusion pseudotime** (`scanpy.tl.dpt`) — orders cells along a diffusion manifold from a user-specified root.
2. **PAGA** — coarse-grained cluster connectivity; initializes force-directed layouts.
3. **RNA velocity** (`scVelo`) — directional flow from unspliced/spliced mRNA ratios. Note: scVelo is in maintenance mode (no new features); APIs remain stable.
4. **CellRank v2** — unified kernel API combining velocity, pseudotime, real-time, or CytoTRACE signals into a Markov chain for macrostates, terminal states, and fate probabilities. CytoTRACEKernel enables velocity-free trajectory inference.

Inputs assume a preprocessed `AnnData` (normalized, log-transformed, HVGs, neighbors computed). Velocity additionally requires `spliced`/`unspliced` layers from velocyto or STARsolo.

## Usage

Describe the analysis in natural language:

- "Compute diffusion pseudotime rooted in the HSC cluster."
- "Run PAGA on leiden clusters and re-embed with force-directed layout."
- "Run dynamical scVelo and plot the velocity stream."
- "Use CellRank with CytoTRACEKernel to find terminal states without velocity data."
- "Combine VelocityKernel and ConnectivityKernel to compute fate probabilities."

The skill produces a runnable Python script or notebook cell.

## Response Format

1. **Method selection** — state which approach fits the user's data (use decision tree below)
2. **Prerequisites check** — confirm required layers/annotations exist
3. **Working code** — complete, copy-paste-ready script
4. **Key parameters** — explain non-obvious choices
5. **Gotchas** — warn about common failure modes specific to the chosen method

## Decision Tree — Choosing a Trajectory Method

```
Have spliced/unspliced layers?
├─ YES → RNA velocity (scVelo dynamical) → CellRank VelocityKernel
│         Best for: steady-state or dynamical kinetics inference
│
└─ NO
    ├─ Have experimental time points?
    │   └─ YES → CellRank RealTimeKernel
    │             Best for: time-course experiments (reprogramming, perturbation)
    │
    └─ NO time points
        ├─ Want directionality (root → terminal)?
        │   ├─ CytoTRACEKernel (uses gene-count gradient as differentiation proxy)
        │   │   Best for: differentiation without velocity; no extra input needed
        │   └─ PseudotimeKernel (uses precomputed DPT as direction)
        │       Best for: when you trust your DPT root choice
        │
        └─ Just want cluster connectivity?
            └─ PAGA (no directionality, shows which clusters connect)
```

## Core Concepts

### 1. Prerequisites — spliced/unspliced counts

Velocity needs `spliced` and `unspliced` layers. Generate with velocyto or STARsolo:

```bash
# Option A: velocyto run10x
velocyto run10x \
    --samtools-threads 8 \
    /path/to/cellranger_outs/sample_id \
    /path/to/genes.gtf

# Option B: STARsolo (Velocyto-compatible matrices)
STAR --runThreadN 16 \
     --genomeDir /path/to/star_index \
     --readFilesIn R2.fq.gz R1.fq.gz \
     --readFilesCommand zcat \
     --soloType CB_UMI_Simple \
     --soloCBallowlist 3M-february-2018.txt \
     --soloFeatures Gene Velocyto \
     --soloCBstart 1 --soloCBlen 16 --soloUMIstart 17 --soloUMIlen 12 \
     --outSAMtype BAM SortedByCoordinate
```

Merge the loom with an existing `AnnData`:

```python
import scvelo as scv

adata = sc.read_h5ad("processed.h5ad")
ldata = scv.read("sample_id.loom", cache=True)
# scv.utils.merge inner-joins on barcodes — ensure obs_names match between objects
adata = scv.utils.merge(adata, ldata)
assert "spliced" in adata.layers and "unspliced" in adata.layers
```

### 2. Diffusion pseudotime (DPT)

```python
import numpy as np
import scanpy as sc

sc.tl.diffmap(adata)

# Root cell: pick one cell in the known starting population
root_cluster = "HSC"
adata.uns["iroot"] = np.flatnonzero(adata.obs["celltype"] == root_cluster)[0]

sc.tl.dpt(adata)  # writes adata.obs['dpt_pseudotime']
sc.pl.umap(adata, color=["celltype", "dpt_pseudotime"])
```

### 3. PAGA

```python
sc.tl.paga(adata, groups="leiden")

# threshold controls edge pruning: higher = fewer edges shown
# Default 0.01 shows almost everything; 0.03-0.1 is typical for clean plots
sc.pl.paga(adata, threshold=0.03, show=False)

# PAGA-initialized layout for cleaner trajectory visualization
sc.tl.draw_graph(adata, init_pos="paga")
sc.pl.draw_graph(adata, color=["leiden", "dpt_pseudotime"], legend_loc="on data")

# Gene trends along a chosen path
sc.pl.paga_path(
    adata,
    nodes=["HSC", "MPP", "GMP", "Mono"],
    keys=["Elane", "Mpo", "Gata1"],
)
```

**PAGA threshold note:** `sc.pl.paga(threshold=...)` only affects visualization (which edges to draw), not the underlying graph. The connectivity weights live in `adata.uns['paga']['connectivities']`. Set `threshold=0` to see all edges, increase to declutter.

### 4. RNA velocity (scVelo)

> **Status:** scVelo is in maintenance mode. APIs are stable but no new features are planned. For new projects without velocity data, consider CellRank's CytoTRACEKernel as a velocity-free alternative.

```python
import scvelo as scv

scv.settings.n_jobs = 8

# Preprocessing — operates on spliced/unspliced layers
scv.pp.filter_and_normalize(adata, min_shared_counts=20, n_top_genes=2000)
scv.pp.moments(adata, n_pcs=30, n_neighbors=30)

# Dynamical mode (recommended): fits full kinetic model per gene
scv.tl.recover_dynamics(adata, n_jobs=8)
scv.tl.velocity(adata, mode="dynamical")
scv.tl.velocity_graph(adata)

scv.pl.velocity_embedding_stream(adata, basis="umap", color="celltype")

# Latent time (dynamical mode only)
scv.tl.latent_time(adata)
scv.pl.scatter(adata, color="latent_time", color_map="gnuplot")
```

### 5. CellRank v2 — unified kernel API

CellRank v2 provides a unified kernel interface. All kernels:
- Accept an `AnnData` and call `.compute_transition_matrix()`
- Can be combined with `+` and `*` (weighted sum)
- Feed into `cr.estimators.GPCCA` for macrostate decomposition

#### 5a. VelocityKernel (requires scVelo velocity)

```python
import cellrank as cr
from cellrank.kernels import VelocityKernel, ConnectivityKernel

vk = VelocityKernel(adata).compute_transition_matrix()
ck = ConnectivityKernel(adata).compute_transition_matrix()
kernel = 0.8 * vk + 0.2 * ck  # weighted combination

g = cr.estimators.GPCCA(kernel)
g.compute_schur(n_components=20)
g.compute_macrostates(n_states=5, cluster_key="celltype")
g.predict_terminal_states()
g.compute_fate_probabilities()
g.plot_fate_probabilities(same_plot=False)

# Lineage driver genes
drivers = g.compute_lineage_drivers(lineages=["Mono"], use_raw=False)
```

#### 5b. CytoTRACEKernel (velocity-free, new in v2)

Uses gene-count gradient as a proxy for differentiation potential. No velocity data needed.

```python
from cellrank.kernels import CytoTRACEKernel, ConnectivityKernel

ctk = CytoTRACEKernel(adata).compute_transition_matrix()
ck = ConnectivityKernel(adata).compute_transition_matrix()
kernel = 0.8 * ctk + 0.2 * ck

g = cr.estimators.GPCCA(kernel)
g.compute_schur(n_components=15)
g.compute_macrostates(n_states=4, cluster_key="celltype")
g.predict_terminal_states()
g.compute_fate_probabilities()
```

#### 5c. RealTimeKernel (experimental time points)

For time-course experiments where cells are collected at discrete time points.

```python
from cellrank.kernels import RealTimeKernel

# adata.obs["day"] must contain numeric time labels (e.g., 0, 2, 4, 7)
rtk = RealTimeKernel(adata, time_key="day").compute_transition_matrix()

g = cr.estimators.GPCCA(rtk)
g.compute_macrostates(n_states=6, cluster_key="celltype")
g.predict_terminal_states()
g.compute_fate_probabilities()
```

#### 5d. PseudotimeKernel (DPT-directed)

Uses precomputed pseudotime to define directionality.

```python
from cellrank.kernels import PseudotimeKernel, ConnectivityKernel

# Requires adata.obs["dpt_pseudotime"] from sc.tl.dpt
pk = PseudotimeKernel(adata, time_key="dpt_pseudotime").compute_transition_matrix()
ck = ConnectivityKernel(adata).compute_transition_matrix()
kernel = 0.8 * pk + 0.2 * ck

g = cr.estimators.GPCCA(kernel)
g.compute_macrostates(n_states=4, cluster_key="celltype")
g.predict_terminal_states()
g.compute_fate_probabilities()
```

#### 5e. Kernel combination rules

```python
# All kernels support arithmetic combination after .compute_transition_matrix()
combined = 0.6 * vk + 0.2 * ck + 0.2 * pk  # weights must sum to 1

# Inspect kernel quality
combined.plot_projection(basis="umap")  # visualize transition arrows
```

### 6. Spatial neighbors (squidpy)

For spatial transcriptomics, replace kNN with a spatial graph:

```python
import squidpy as sq

sq.gr.spatial_neighbors(adata, coord_type="generic", n_neighs=6)
# Feed spatial connectivities into CellRank ConnectivityKernel
```

## Quick Reference

| Task | Call | Output |
| --- | --- | --- |
| Diffusion map | `sc.tl.diffmap(adata)` | `.obsm['X_diffmap']` |
| Set root | `adata.uns['iroot'] = idx` | — |
| Pseudotime | `sc.tl.dpt(adata)` | `.obs['dpt_pseudotime']` |
| PAGA | `sc.tl.paga(adata, groups='leiden')` | `.uns['paga']` |
| PAGA plot | `sc.pl.paga(adata, threshold=0.03)` | figure (threshold=visual only) |
| PAGA-init layout | `sc.tl.draw_graph(adata, init_pos='paga')` | `.obsm['X_draw_graph_fa']` |
| Merge loom | `scv.utils.merge(adata, ldata)` | combined AnnData (inner-join on barcodes) |
| Velocity preproc | `scv.pp.filter_and_normalize`; `scv.pp.moments` | moment layers |
| Dynamics fit | `scv.tl.recover_dynamics(adata)` | fit params |
| Velocity | `scv.tl.velocity(adata, mode='dynamical')` | `.layers['velocity']` |
| Velocity graph | `scv.tl.velocity_graph(adata)` | `.uns['velocity_graph']` |
| Stream plot | `scv.pl.velocity_embedding_stream(adata, basis='umap')` | figure |
| Latent time | `scv.tl.latent_time(adata)` | `.obs['latent_time']` |
| VelocityKernel | `VelocityKernel(adata).compute_transition_matrix()` | kernel |
| CytoTRACEKernel | `CytoTRACEKernel(adata).compute_transition_matrix()` | kernel (no velocity needed) |
| RealTimeKernel | `RealTimeKernel(adata, time_key="day").compute_transition_matrix()` | kernel |
| PseudotimeKernel | `PseudotimeKernel(adata, time_key="dpt_pseudotime").compute_transition_matrix()` | kernel |
| Combine kernels | `0.8 * vk + 0.2 * ck` | combined kernel |
| Estimator | `cr.estimators.GPCCA(kernel)` | estimator |
| Macrostates | `g.compute_macrostates(n_states=5, cluster_key="celltype")` | `.macrostates` |
| Terminal states | `g.predict_terminal_states()` | `.terminal_states` |
| Fate probs | `g.compute_fate_probabilities()` | `.fate_probabilities` |
| Lineage drivers | `g.compute_lineage_drivers(lineages=["Mono"], use_raw=False)` | DataFrame |
| Spatial graph | `sq.gr.spatial_neighbors(adata)` | `.obsp['spatial_*']` |

## Common Mistakes

- **Wrong:** Calling `sc.tl.dpt` without setting `adata.uns['iroot']`
  **Right:** Set the root cell index before computing DPT: `adata.uns['iroot'] = np.flatnonzero(adata.obs['celltype'] == root_cluster)[0]`
  **Why:** Without a root, pseudotime has no direction and results are meaningless

- **Wrong:** Running scVelo velocity without `spliced`/`unspliced` layers in the AnnData
  **Right:** Check `adata.layers.keys()` after `scv.utils.merge`; ensure both layers exist with matching barcodes
  **Why:** Velocity computation requires both layers; missing layers cause errors or silent failures

- **Wrong:** Using `mode='dynamical'` in `scv.tl.velocity` without first running `scv.tl.recover_dynamics`
  **Right:** Always run `scv.tl.recover_dynamics(adata)` before `scv.tl.velocity(adata, mode='dynamical')`
  **Why:** The dynamical model needs per-gene rate parameters that are only computed by `recover_dynamics`

- **Wrong:** Computing `scv.tl.latent_time` after running velocity in `stochastic` mode
  **Right:** Use `mode='dynamical'` for velocity if you need latent time
  **Why:** Latent time is only defined for the dynamical model; stochastic mode does not produce the required parameters

- **Wrong:** Calling `scv.tl.velocity` without running `scv.pp.moments` first
  **Right:** Run `scv.pp.moments(adata, n_pcs=30, n_neighbors=30)` before velocity computation
  **Why:** Moments (`Ms`, `Mu` layers) are required inputs for velocity estimation

- **Wrong:** Running `sc.tl.paga` before computing cluster labels
  **Right:** Run `sc.tl.leiden` (or equivalent clustering) first; pass the cluster key via `groups=`
  **Why:** PAGA computes connectivity between existing groups; without clusters it has nothing to connect

- **Wrong:** Thinking the `threshold` parameter in `sc.pl.paga()` affects the underlying graph
  **Right:** Understand that `threshold` is purely visual — it controls which edges are drawn, not computed
  **Why:** Misinterpreting this leads to incorrect claims about cluster connectivity

- **Wrong:** Re-running `sc.pp.neighbors` after computing velocity graph or CellRank transition matrices
  **Right:** If neighbors must change, recompute `velocity_graph` and CellRank kernels afterward
  **Why:** Velocity graph and transition matrices depend on the neighbor graph; changing it silently invalidates them

- **Wrong:** Using `n_cells` parameter in CellRank v2's `compute_macrostates()`
  **Right:** Use `n_states` — the v2 API renamed this parameter
  **Why:** `n_cells` was v1 syntax and will raise an error or be silently ignored in v2

- **Wrong:** Calling `predict_terminal_states()` without first inspecting macrostates
  **Right:** Always run `g.plot_macrostates()` and review coarse-grained transitions before predicting terminals
  **Why:** Terminal state prediction depends on macrostate quality; garbage macrostates produce garbage fate maps

- **Wrong:** Forcing velocity-based analysis when velocity arrows look random or incoherent
  **Right:** Switch to CytoTRACEKernel or PseudotimeKernel when velocity signal is absent
  **Why:** Random velocity arrows indicate the data lacks kinetic signal; forcing velocity produces meaningless trajectories

## References

- CellRank 2: Weiler et al. Nat Methods 2024, https://doi.org/10.1038/s41592-023-02088-9
- scVelo: Bergen et al. Nat Biotechnol 2020, https://doi.org/10.1038/s41587-020-0591-3
- CellRank: Lange et al. Nat Methods 2022, https://doi.org/10.1038/s41592-021-01346-6
- PAGA: Wolf et al. Genome Biol 2019, https://doi.org/10.1186/s13059-019-1663-x
- velocyto: La Manno et al. Nature 2018, https://doi.org/10.1038/s41586-018-0414-6
