---
name: rna-seq-analysis
description: Bulk RNA-seq analysis pipeline covering alignment (STAR), quantification (Salmon, featureCounts), and differential expression (DESeq2). Triggers on RNA-seq, STAR, Salmon, DESeq2, differential expression, gene expression, tximport, featureCounts, transcriptomics, "bulk RNA-seq", "STAR alignment", "Salmon quantification", "gene counts", "DESeq2 results", "shrinkage estimator", "volcano plot RNA-seq".
usage: Invoke when running bulk RNA-seq alignment, quantification, or differential expression analysis with STAR, Salmon, or DESeq2.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {star: "2.7.11", salmon: "1.10", deseq2: "1.42"}
tags: [skill, category:pipeline, genomics, rna-seq, star, deseq2, differential-expression, hcls]
---

# RNA-seq Analysis — Pipeline Skill (Thin Scaffold)

## Overview

Adds decision logic for choosing quantification paths (STAR vs Salmon), strandedness determination, and DESeq2 modeling pitfalls that LLMs routinely get wrong.

## Usage

- Activate when choosing between alignment-based (STAR+featureCounts) vs alignment-free (Salmon) quantification
- Activate when setting up DESeq2 from either count source
- Activate when debugging unexpected low counts or weak DE signal

## Core Concepts

## Decision Logic

```
Need BAMs? (variant calling, fusions, novel transcripts)
├── YES → STAR two-pass + featureCounts
└── NO → Salmon (faster, lower RAM, bias-corrected)

Salmon output → DESeq2:
└── Use DESeqDataSetFromTximport (preserves length offset)
    └── NEVER round txi$counts and pass to DESeqDataSetFromMatrix

Filtering strategy (VQSR equivalent):
├── ≥30 samples → VQSR-like (default DESeq2 shrinkage works well)
└── <30 samples → still works, but pre-filter aggressively
```

**Strandedness determination (MUST verify before counting):**

| Kit | featureCounts `-s` | Salmon `-l` |
|-----|-------------------|-------------|
| TruSeq Stranded / dUTP | 2 | ISR (PE) / SR (SE) |
| Ligation / forward | 1 | ISF / SF |
| Unstranded | 0 | IU / U |

Verify with: `infer_experiment.py` (RSeQC) or Salmon's `lib_format_counts.json`.

## Critical Parameters

| Parameter | Value | When to change |
|-----------|-------|----------------|
| `--sjdbOverhang` | readLength - 1 (default 100) | Non-100bp reads |
| `--twopassMode Basic` | Always for DE | Skip only for speed in QC runs |
| Salmon `--gcBias --seqBias` | Always on | Never skip for Illumina |
| Salmon `--validateMappings` | Always on | Enables selective alignment |
| featureCounts `-s` | Kit-dependent | ALWAYS verify empirically |
| DESeq2 pre-filter | `rowSums(counts >= 10) >= smallest_group` | Adjust 10 for shallow sequencing |
| `lfcShrink type` | `"apeglm"` | Use `"ashr"` for arbitrary contrasts |
| Design formula | `~ batch + condition` (interest LAST) | Always put interest term last |

## Common Mistakes

- **Wrong:** Guessing strandedness (`-s`) instead of verifying empirically
  **Right:** Check with `infer_experiment.py` or Salmon `lib_format_counts.json` before running featureCounts
  **Why:** Wrong strandedness causes 2–10× lower counts and weak DE signal

- **Wrong:** Passing normalized counts (TPM, FPKM, CPM) to DESeq2
  **Right:** Always start from raw integer counts
  **Why:** Normalized values break the negative-binomial model

- **Wrong:** Rounding `txi$counts` and passing to `DESeqDataSetFromMatrix`
  **Right:** Use `DESeqDataSetFromTximport(txi, ...)` which preserves the length offset
  **Why:** Rounding discards per-gene length correction for transcript-length bias

- **Wrong:** Placing variable of interest first in design (`~ condition + batch`)
  **Right:** Put interest last: `~ batch + condition`
  **Why:** DESeq2 tests the last term by default

- **Wrong:** Assuming DESeq2 reorders samples to match
  **Right:** Assert `stopifnot(all(colnames(cts) == rownames(coldata)))` before creating DESeq object
  **Why:** DESeq2 silently mislabels samples if order doesn't match

- **Wrong:** Skipping pre-filtering of low-count genes
  **Right:** Filter with `rowSums(counts(dds) >= 10) >= smallest_group_size`
  **Why:** Near-zero genes inflate runtime and dilute multiple-testing correction

- **Wrong:** Using STAR `ReadsPerGene.out.tab` column 2 for stranded libraries
  **Right:** Use column 3 (forward) or column 4 (reverse) matching your kit
  **Why:** Column 2 is unstranded; using it for stranded data halves effective counts

- **Wrong:** Including samples with <10M mapped reads or <70% mapping rate
  **Right:** Exclude or flag before fitting
  **Why:** Low-quality samples distort size factors and dispersion estimates

- **Wrong:** Modeling when batch is perfectly confounded with condition
  **Right:** Check `table(coldata$batch, coldata$condition)` first
  **Why:** No statistical model can separate perfectly correlated effects

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation
