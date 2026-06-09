---
name: molecular-docking
description: Molecular docking pipeline using AutoDock Vina for structure-based drug discovery. Triggers on docking, AutoDock Vina, receptor preparation, ligand preparation, PDBQT, grid box, virtual screening, binding affinity, pose prediction, structure-based virtual screening, "redocking RMSD", "Vina score", "docking pose", "prepare receptor", "ligand library screening".
usage: Invoke when performing molecular docking with AutoDock Vina, preparing receptors/ligands, or running virtual screening.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {autodock-vina: "1.2.5", meeko: "0.5", openbabel: "3.1.1"}
tags: [skill, category:pipeline, molecular-docking, autodock-vina, drug-discovery, hcls]
---

# Molecular Docking — Pipeline Skill (Thin Scaffold)

## Overview

Adds decision logic for receptor/ligand preparation tool selection, grid box sizing, exhaustiveness tuning, and validation protocol. Focuses on gotchas that produce silently wrong poses.

## Usage

- Activate when choosing preparation tools (obabel vs ADFR/meeko) for a docking campaign
- Activate when defining grid box dimensions or placement
- Activate when validating docking setup via redocking

## Core Concepts

## Decision Logic

```
Receptor preparation tool:
├── Quick exploration / single ligand → obabel (-d, reduce, -xr)
└── Production virtual screen → prepare_receptor (ADFR) or meeko
    └── Handles altlocs, metals, non-standard residues correctly

Ligand preparation:
├── Single ligand from SMILES/SDF → obabel --gen3d -h
├── Large library (>100 ligands) → meeko (mk_prepare_ligand.py)
└── Stereocenters undefined? → Enumerate explicitly BEFORE docking

Grid box placement:
├── Co-crystal ligand available → Center on ligand centroid
└── No co-crystal → Use pocket predictor (fpocket, P2Rank, SiteMap)

Grid box sizing:
└── Ligand longest diameter + 10–15 Å padding per axis
    └── Typical: 20–30 Å per side for drug-like molecules

Exhaustiveness:
├── Quick exploration → 8 (Vina default)
├── Production / ranking → 32
└── Large/flexible ligands (>8 rotatable bonds) → 64+
```

**Validation gate (MUST pass before trusting screen results):**
Redock co-crystal ligand → RMSD < 2 Å against crystallographic pose. If fails, fix preparation or grid before screening.

## Critical Parameters

| Parameter | Recommended | When to change |
|-----------|-------------|----------------|
| `exhaustiveness` | 32 | 64+ for >8 rotatable bonds |
| `num_modes` | 10 | Increase for ensemble analysis |
| `energy_range` | 3 kcal/mol | Widen to capture diverse poses |
| Box padding | +10–15 Å | Larger for allosteric sites |
| Protonation pH | 7.0 (reduce default) | Use PROPKA/H++ for acidic pockets (e.g., aspartyl proteases pH 4.5) |

**Score interpretation:**
- Vina scores are only comparable within the SAME receptor + grid setup
- Typical drug-like hits: -7 to -12 kcal/mol
- Scores are NOT transferable across different targets or grid configurations

## Common Mistakes

- **Wrong:** Leaving crystallographic waters in the receptor
  **Right:** Strip HOH/WAT residues before PDBQT conversion (unless explicit-water docking)
  **Why:** Waters block the binding site and produce unphysical poses

- **Wrong:** Using default pH 7 protonation for all binding sites
  **Right:** Use PROPKA or H++ for acidic/basic pockets
  **Why:** Wrong protonation alters H-bond networks and produces incorrect poses

- **Wrong:** Grid box barely enclosing the binding site
  **Right:** Ligand diameter + 10–15 Å padding per axis
  **Why:** Under-padding clips the site and biases poses toward box center

- **Wrong:** Default `exhaustiveness = 8` for large/flexible ligands
  **Right:** Use 32+ for production; 64+ for >8 rotatable bonds
  **Why:** Low exhaustiveness misses global minima, unreliable rankings

- **Wrong:** Skipping redocking validation before screening
  **Right:** Redock co-crystal ligand, verify RMSD < 2 Å
  **Why:** RMSD ≥ 2 Å means preparation or grid is wrong; screen results untrustworthy

- **Wrong:** Using `obabel -xr` PDBQT for production virtual screens
  **Right:** Use `prepare_receptor` (ADFR) or meeko for production
  **Why:** obabel may miss altlocs, metals, or non-standard residues

- **Wrong:** Running `obabel --gen3d` on SMILES with undefined stereocenters
  **Right:** Provide isomeric SMILES or enumerate stereoisomers explicitly
  **Why:** Undefined stereocenters resolved arbitrarily — may dock wrong enantiomer

- **Wrong:** Comparing Vina affinities across different receptors or grid configs
  **Right:** Only compare within same receptor + grid; re-rank when changing either
  **Why:** Scores are context-dependent, not transferable

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation
