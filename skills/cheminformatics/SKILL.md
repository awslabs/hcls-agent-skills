---
name: cheminformatics
description: Cheminformatics pipeline for small-molecule property calculation, filtering, and similarity analysis using RDKit. Use when the user asks to compute molecular descriptors, filter compounds by Lipinski or Veber rules, detect PAINS, calculate fingerprint similarity, run matched molecular pair analysis, generate ADMET descriptors, or process SMILES. Triggers include "RDKit", "molecular descriptors", "Lipinski", "rule of five", "Veber", "PAINS", "pan-assay interference", "Morgan fingerprint", "Tanimoto", "fingerprint similarity", "matched molecular pair", "MMP", "mmpdb", "ADMET", "druglikeness", "SMILES", "cheminformatics", "compound filtering", "chemical similarity".
usage: Invoke when computing molecular properties, filtering compound libraries, calculating fingerprint similarity, or running matched molecular pair analysis with RDKit.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {rdkit: "2024.03", mmpdb: "3.1"}
tags: [skill, category:pipeline, cheminformatics, drug-discovery, rdkit, hcls]
---

# Cheminformatics (RDKit) — Pipeline Skill (Thin Scaffold)

## Overview

Adds fingerprint selection logic, filter cascade ordering, and version-specific gotchas for RDKit workflows. The agent already knows RDKit syntax — this skill prevents parameter mismatches and deprecated API usage.

## Usage

- Activate when filtering compound libraries (Lipinski/Veber/PAINS)
- Activate for fingerprint similarity search or clustering
- Activate for matched molecular pair (MMP) analysis with mmpdb

## Core Concepts

**Filter cascade order:** Lipinski → Veber → PAINS → similarity (cheapest first, most expensive last).

**Fingerprint API:** Use `rdFingerprintGenerator` module exclusively (since RDKit 2024.03). The `AllChem.GetMorganFingerprintAsBitVect()` path is deprecated and will be removed.

**SMILES validation:** Always parse with `sanitize=False` then explicit `SanitizeMol()` in try/except. Default `MolFromSmiles` silently returns None on partial failures.

## Decision Logic

### Fingerprint Selection

| Goal | Fingerprint | Parameters | Tanimoto threshold |
|------|-------------|------------|-------------------|
| General similarity | Morgan (ECFP4) | radius=2, fpSize=2048 | ≥ 0.7 |
| High-specificity matching | Morgan (ECFP6) | radius=3, fpSize=4096 | ≥ 0.6 |
| Substructure screening | MACCS 166 keys | — | ≥ 0.8 |
| Pharmacophore similarity | FCFP | radius=2, `GetMorganFeatureAtomInvGen()` | ≥ 0.6 |
| Large-scale clustering | Morgan | radius=2, fpSize=1024 | Speed over precision |

### Filter Thresholds

| Filter | Rule | Threshold | Notes |
|--------|------|-----------|-------|
| Lipinski MW | ≤ 500 Da | Allow ≤1 violation total | Not binary pass/fail |
| Lipinski LogP | ≤ 5 | — | — |
| Lipinski HBD | ≤ 5 | — | — |
| Lipinski HBA | ≤ 10 | — | — |
| Veber TPSA | ≤ 140 Å² | Hard cutoff | — |
| Veber RotBonds | ≤ 10 | Hard cutoff | — |
| PAINS | A+B+C catalogs | HTS triage only | Don't apply to advanced compounds |

### MMP Analysis Decision

| Scenario | Tool | Key parameter |
|----------|------|---------------|
| SAR from compound pairs | mmpdb fragment → index → transform | `--min-pairs 3` |
| Property prediction | mmpdb predict | Requires indexed DB with property data |
| Core identification | `rdFMCS.FindMCS()` | `ringMatchesRingOnly=True, completeRingsOnly=True` |
| Large libraries (>10K) | mmpdb CLI | `--max-variable-size 10` to limit fragmentation |

## Critical Parameters

| Parameter | Value | When to change |
|-----------|-------|----------------|
| Morgan radius | 2 (ECFP4) | 3 for higher specificity |
| fpSize | 2048 | 1024 for speed; 4096 for precision |
| includeChirality | False | True for stereo-sensitive applications |
| Lipinski max_violations | 1 | 0 for strict; exempt biologics entirely |
| mmpdb --min-pairs | 3 | Lower for sparse datasets |
| mmpdb --max-variable-size | 10 | Increase for macrocycle transformations |
| PAINS catalogs | A+B+C (all three) | Never use partial sets |

## Common Mistakes

- **Wrong:** `AllChem.GetMorganFingerprintAsBitVect()` → **Right:** `rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048).GetFingerprint(mol)` → **Why:** AllChem FP functions deprecated since RDKit 2024.03, will be removed

- **Wrong:** Default `MolFromSmiles(smi)` without error handling → **Right:** `MolFromSmiles(smi, sanitize=False)` + `SanitizeMol()` in try/except → **Why:** Default silently returns None; explicit sanitize catches partial failures

- **Wrong:** Lipinski as hard binary filter → **Right:** Allow ≤1 violation → **Why:** Many approved drugs violate one rule; binary filtering rejects valid candidates

- **Wrong:** PAINS on clinical candidates → **Right:** PAINS only for HTS library triage → **Why:** Designed for screening artifacts; flags valid advanced compounds

- **Wrong:** Morgan radius=1 → **Right:** radius=2 minimum (ECFP4) → **Why:** Radius 1 loses structural information; too many false-positive similarities

- **Wrong:** Comparing FPs with different radius or nBits → **Right:** Identical parameters for both FPs → **Why:** Tanimoto only meaningful in same parameter space

- **Wrong:** Ignoring stereochemistry for chiral compounds → **Right:** `includeChirality=True` in generator → **Why:** Default treats enantiomers as identical

- **Wrong:** Fixed 0.7 threshold for all FP types → **Right:** Validate threshold per fingerprint type and chemical series → **Why:** 0.7 convention is ECFP4-specific; other types need different cutoffs

- **Wrong:** Raw SMILES into mmpdb → **Right:** Pre-canonicalize with `MolToSmiles(MolFromSmiles(smi))` → **Why:** mmpdb expects canonical SMILES; non-canonical causes fragmentation errors

- **Wrong:** Confusing LogP with LogD → **Right:** Use LogD at pH 7.4 for ionizable compounds; RDKit computes LogP only → **Why:** LogP overestimates lipophilicity for ionizable molecules at physiological pH

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional
- Target: 50-100 lines of code with brief surrounding explanation
