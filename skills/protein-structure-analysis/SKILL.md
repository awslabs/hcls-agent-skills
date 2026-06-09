---
name: protein-structure-analysis
description: Pipeline skill for protein structure analysis covering PDB/mmCIF parsing, RMSD superposition, Ramachandran/dihedral analysis, binding pocket detection, contact maps, B-factor flexibility, DSSP secondary structure, and format conversion. Triggers on PDB, protein structure, RMSD, Ramachandran, binding pocket, Biopython, PyMOL, pocket detection, fpocket, DSSP, PDBQT, structural alignment, superposition.
usage: Invoke when parsing PDB/mmCIF files, computing RMSD, generating Ramachandran plots, detecting binding pockets, or converting structure formats.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {biopython: "1.83", pymol: "2.5", fpocket: "4.1"}
tags: [skill, category:pipeline, protein-structure, biopython, structural-biology, hcls]
---

# Protein Structure Analysis — Pipeline Skill (Thin Scaffold)

## Overview

Adds tool-selection logic, format-conversion rules, and niche gotchas for protein structure tasks. The agent already knows Biopython/PyMOL syntax — this skill prevents common parameter and workflow mistakes.

## Usage

- Activate when parsing PDB/mmCIF, computing RMSD, detecting pockets, or converting formats
- Activate for Ramachandran plots, contact maps, B-factor analysis, or DSSP assignment
- Activate when preparing structures for downstream docking (PDBQT export)

## Core Concepts

**SMCRA hierarchy:** Structure → Model → Chain → Residue → Atom. Always iterate at the correct level; NMR files have multiple models.

**Altloc:** Alternate conformations flagged with non-blank code ('A','B'). Filter to one before any geometry calculation.

**fpocket output:** Writes `<basename>_out/` in the *current working directory*, not next to the input file. Pockets ranked by druggability score (0–1).

## Decision Logic

### Tool Selection

| Task | Tool | Key consideration |
|------|------|-------------------|
| Parse PDB/mmCIF | Biopython `PDBParser`/`MMCIFParser` | Always pass `QUIET=True` |
| RMSD superposition | `Bio.PDB.Superimposer` | Requires equal-length, 1-to-1 atom lists |
| Binding pocket detection | fpocket CLI | Needs clean PDB (no altloc, no HETATM clutter) |
| Pocket visualization | PyMOL (`-cq` for headless) | `byres all within 5 of organic` for pocket selection |
| Contact analysis | `Bio.PDB.NeighborSearch` | 4.0 Å default cutoff; returns atom pairs |
| Secondary structure | DSSP via Biopython | Binary is `mkdssp` on newer installs |
| Format: PDB→mmCIF | `Bio.PDB.MMCIFIO` | Lossless for coordinates |
| Format: PDB→PDBQT | `obabel -O out.pdbqt -xr` | Add `-xh` for hydrogens first |
| Ramachandran | `PPBuilder` → `get_phi_psi_list()` | Termini return `None` — must check |

### RMSD Type Selection

| Scenario | Atoms to use | Notes |
|----------|-------------|-------|
| Backbone comparison | Cα only | Standard for fold similarity |
| Loop flexibility | All backbone (N, Cα, C, O) | Captures local deviations |
| Binding site comparison | All-atom within 5 Å of ligand | Requires residue selection first |
| Identical sequences | All-atom | Only valid for same-length chains |

## Critical Parameters

| Parameter | Value | When to change |
|-----------|-------|----------------|
| NeighborSearch cutoff | 4.0 Å | 3.5 for H-bonds, 5.0 for hydrophobic |
| Superimposer atoms | Cα | All-atom only for identical sequences |
| fpocket `-m` (min alpha spheres) | 35 (default) | Lower to 15 for small/shallow pockets |
| DSSP binary name | `mkdssp` | Use `dssp` on legacy installs |
| obabel `-xr` flag | receptor mode | Omit for flexible ligand PDBQT |
| PPBuilder vs CaPPBuilder | PPBuilder | CaPPBuilder only for Cα-only traces |

## Common Mistakes

- **Wrong:** Assuming single model in PDB → **Right:** Always `structure[0]` or iterate models → **Why:** NMR ensembles have many models; raw iteration hits unexpected atoms

- **Wrong:** Ignoring altloc in geometry → **Right:** Filter `atom.get_altloc() in ('', 'A')` → **Why:** Duplicate atoms corrupt RMSD and dihedral calculations

- **Wrong:** All-atom RMSD when backbone intended → **Right:** Restrict to Cα for fold comparison → **Why:** Side-chains inflate RMSD and break correspondence across non-identical sequences

- **Wrong:** Unequal-length atom lists in Superimposer → **Right:** Match by residue number, build parallel lists of equal length → **Why:** `set_atoms()` requires strict 1-to-1 correspondence

- **Wrong:** No hydrogens before PDBQT export → **Right:** `obabel -xh` then `-xr -O receptor.pdbqt` → **Why:** Crystal PDBs lack H; docking scoring needs them

- **Wrong:** Including HETATM/water in backbone calculations → **Right:** Filter `residue.id[0] == ' '` → **Why:** Heteroatoms and water corrupt phi/psi and backbone RMSD

- **Wrong:** `math.degrees()` on None phi/psi → **Right:** Check `if phi is not None and psi is not None` → **Why:** Chain termini return None; TypeError crashes

- **Wrong:** Default `dssp` binary name → **Right:** Pass `dssp='mkdssp'` to `DSSP()` → **Why:** Newer installs only provide `mkdssp`

- **Wrong:** Expecting fpocket output next to input → **Right:** Run from target directory or move output after → **Why:** fpocket writes to CWD, not input file location

- **Wrong:** Forgetting `QUIET=True` in parser → **Right:** `PDBParser(QUIET=True)` → **Why:** Non-fatal warnings flood stdout and obscure real errors

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional
- Target: 50-100 lines of code with brief surrounding explanation
