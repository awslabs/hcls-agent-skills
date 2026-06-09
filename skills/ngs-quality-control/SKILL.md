---
name: ngs-quality-control
description: NGS quality control pipeline for short-read sequencing data. Triggers on FastQC, QC, quality control, adapter trimming, coverage, mosdepth, Picard metrics, fastp, MultiQC, sequencing QC, BAM QC, WGS/WES coverage analysis.
usage: Invoke when running QC on short-read sequencing data, including FastQC, adapter trimming, coverage analysis, or MultiQC reporting.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {fastqc: "0.12.1", fastp: "0.23.4", mosdepth: "0.3.8"}
tags: [skill, category:pipeline, genomics, quality-control, fastqc, ngs, hcls]
---

# NGS Quality Control

## Overview

This skill encodes a reproducible QC workflow for Illumina short-read sequencing data across the full lifecycle: raw reads → trimmed reads → aligned BAMs. It produces deterministic metrics suitable for QC gating in WGS, WES, and targeted panel projects.

Pipeline stages:

1. **Raw-read QC** — FastQC per FASTQ, aggregated with MultiQC.
2. **Adapter/quality trimming** — fastp with paired-end adapter detection.
3. **Post-trim QC** — FastQC + MultiQC on trimmed reads.
4. **Alignment QC** — samtools stats/flagstat, Picard metric suites.
5. **Coverage QC** — mosdepth (genome windows or target BED).
6. **Aggregation** — MultiQC over all tool outputs for a single-HTML summary.

## Usage

Assume `THREADS=8`, `OUT=qc_out`, paired FASTQs `sample_R1.fastq.gz` / `sample_R2.fastq.gz`, coordinate-sorted `sample.bam` with index, reference `ref.fasta`, and (for WES/panel) target intervals.

### 1. Raw FASTQ QC — FastQC

```bash
mkdir -p $OUT/fastqc_raw
fastqc -t $THREADS -o $OUT/fastqc_raw *.fastq.gz
```

Key FastQC modules to inspect:

- **Per base sequence quality** — Q30 drop-off toward 3′ end indicates trimming need.
- **Per sequence quality scores** — bimodal distribution flags a failing tile/lane.
- **Per base sequence content** — first ~12 bp bias is normal (random-hexamer priming); large bias elsewhere flags adapter/contamination.
- **Per sequence GC content** — deviation from expected species GC → contamination or bias.
- **Sequence Duplication Levels** — high duplication in non-amplicon libraries → library complexity issue.
- **Overrepresented sequences** — adapter readthrough, rRNA, PhiX carryover.
- **Adapter Content** — confirms which adapter set to trim.

### 2. Adapter & Quality Trimming — fastp

```bash
mkdir -p $OUT/fastp
fastp \
  -i sample_R1.fastq.gz -I sample_R2.fastq.gz \
  -o $OUT/fastp/sample_R1.trim.fastq.gz -O $OUT/fastp/sample_R2.trim.fastq.gz \
  --detect_adapter_for_pe \
  --thread $THREADS \
  --html $OUT/fastp/sample.fastp.html \
  --json $OUT/fastp/sample.fastp.json
```

Useful additional flags:

- `--qualified_quality_phred 20` — base quality threshold (default 15).
- `--length_required 50` — drop reads shorter than 50 bp post-trim.
- `--cut_tail --cut_tail_window_size 4 --cut_tail_mean_quality 20` — sliding window 3′ quality trim.
- `--dedup` — in-memory PCR duplicate removal (read-pair identity; prefer Picard/MarkDuplicates post-alignment for most workflows).

### 3. Post-trim QC + MultiQC

```bash
mkdir -p $OUT/fastqc_trim
fastqc -t $THREADS -o $OUT/fastqc_trim $OUT/fastp/*.trim.fastq.gz

multiqc $OUT -o $OUT/multiqc
```

MultiQC auto-detects FastQC, fastp, Picard, samtools, and mosdepth outputs in the scanned directory.

### 4. Alignment QC — samtools

```bash
samtools flagstat -@ $THREADS sample.bam > $OUT/samtools/sample.flagstat.txt
samtools stats    -@ $THREADS sample.bam > $OUT/samtools/sample.stats.txt
samtools idxstats sample.bam               > $OUT/samtools/sample.idxstats.txt
```

Pull from `samtools stats`: `raw total sequences`, `reads mapped`, `error rate`, `insert size average`, `insert size standard deviation`.

### 5. Picard Metric Suites

Picard requires a sequence dictionary (`ref.dict`) next to `ref.fasta` (`picard CreateSequenceDictionary R=ref.fasta`) and a Picard-format interval list for hybrid-capture metrics (`.interval_list`, header = BAM `@SQ` lines; **not** a plain BED).

```bash
# Convert BED → interval_list (required for CollectHsMetrics)
picard BedToIntervalList \
  I=targets.bed O=targets.interval_list SD=ref.dict

# General alignment metrics (all library types)
picard CollectAlignmentSummaryMetrics \
  R=ref.fasta I=sample.bam O=$OUT/picard/sample.alignment_metrics.txt

# Insert size distribution (paired-end)
picard CollectInsertSizeMetrics \
  I=sample.bam O=$OUT/picard/sample.insert_size.txt \
  H=$OUT/picard/sample.insert_size.pdf

# WGS coverage metrics
picard CollectWgsMetrics \
  R=ref.fasta I=sample.bam O=$OUT/picard/sample.wgs_metrics.txt

# WES / targeted panel hybrid-selection metrics
picard CollectHsMetrics \
  R=ref.fasta I=sample.bam O=$OUT/picard/sample.hs_metrics.txt \
  BAIT_INTERVALS=baits.interval_list \
  TARGET_INTERVALS=targets.interval_list
```

### 6. Coverage — mosdepth

```bash
# WGS: 500 bp fixed windows
mosdepth --by 500 --threads $THREADS --fast-mode --no-per-base \
  $OUT/mosdepth/sample_wgs sample.bam

# WES / panel: per-target coverage
mosdepth --by targets.bed --threads $THREADS --no-per-base \
  $OUT/mosdepth/sample_wes sample.bam
```

Outputs of interest:

- `*.mosdepth.summary.txt` — mean depth per chromosome and total.
- `*.mosdepth.region.dist.txt` — cumulative fraction of regions at ≥X coverage (use for `% targets ≥20x`).
- `*.regions.bed.gz` — per-window/per-target mean depth.

Add `--quantize 0:1:10:30:` for stratified coverage bins, or `--thresholds 10,20,30,50` to emit per-region pass counts at those depths.


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

### QC Tool Selection by Sequencing Type

| Sequencing type | Coverage tool | Coverage metric | Picard suite | Key threshold |
|----------------|--------------|-----------------|--------------|---------------|
| WGS | mosdepth `--by 500` | CollectWgsMetrics | `PCT_20X ≥ 95%` | Mean ≥ 30× |
| WES | mosdepth `--by targets.bed` | CollectHsMetrics | `PCT_TARGET_BASES_20X ≥ 80%` | On-target ≥ 60% |
| Targeted panel | mosdepth `--by targets.bed` | CollectHsMetrics | `PCT_TARGET_BASES_20X ≥ 95%` | Mean ≥ 500× (somatic) |
| RNA-seq | — (use featureCounts/STAR logs) | CollectRnaSeqMetrics | `PCT_CODING_BASES` | rRNA < 10% |

**All types:** FastQC (raw + trimmed) → fastp (trim) → samtools flagstat → MultiQC (aggregate).

### Quality encoding detection

Modern Illumina (CASAVA ≥1.8, 2011+) emits **Phred+33** (Sanger). Legacy data (Illumina 1.3–1.7, Solexa) used **Phred+64**. Aligners expect Phred+33.

- FastQC reports encoding in `Basic Statistics → Encoding`. Look for `Sanger / Illumina 1.9`.
- Quick CLI check — inspect the quality-line ASCII range:

  ```bash
  zcat sample_R1.fastq.gz | head -4000 \
    | awk 'NR%4==0' \
    | od -An -c | tr -s ' \n' '\n' \
    | awk 'length==1' | sort -u
  ```

  Characters in the `!`–`I` range → Phred+33; characters `@`–`h` → Phred+64.
- Convert legacy data: `seqtk seq -Q64 -V in.fq > out.fq` (shifts +64 → +33).

### Trim parameter intent

- **Adapter trimming** is for read-through into the adapter (insert < read length). `--detect_adapter_for_pe` uses read overlap, which is more reliable than sequence-based detection for paired-end.
- **Quality trimming** is for 3′ quality decay on 2-channel chemistry (NextSeq/NovaSeq emit poly-G at dark cycles; use `--trim_poly_g` for those platforms — fastp auto-enables it by platform detection).
- Do not hard-clip fixed lengths unless you know the library design (UMIs, inline barcodes).

### Duplication: optical vs PCR

- `samtools flagstat` "duplicates" reflects whatever flag is set in the BAM (usually by Picard MarkDuplicates or samtools markdup). Run MarkDuplicates **after** alignment, not on trimmed FASTQs.
- `CollectWgsMetrics` / `CollectHsMetrics` report `PCT_EXC_DUPE` — fraction of bases excluded due to duplication. This is the canonical dup rate for coverage-based QC.

### Coverage: mean vs uniformity

Mean depth alone is insufficient. Report both:

- **Mean target coverage** (`MEAN_TARGET_COVERAGE` from HsMetrics; `MEAN_COVERAGE` from WgsMetrics).
- **Coverage breadth** — `% targets ≥20x` / `% genome ≥20x` (`PCT_TARGET_BASES_20X`, `PCT_20X` in Picard; mosdepth `region.dist.txt`).

A panel with mean 200x but only 70% of targets at 20x has a coverage-uniformity problem (capture efficiency, GC bias).

## Quick Reference

### Quality thresholds (typical gating)

| Metric | WGS | WES | Targeted panel | Source |
| --- | --- | --- | --- | --- |
| Mean coverage | ≥ 30× | ≥ 50× on-target | ≥ 500× (somatic), ≥ 100× (germline) | WgsMetrics / HsMetrics |
| Breadth at 20× | ≥ 95% genome | ≥ 80% of targets | ≥ 95% of targets | Picard `PCT_20X` / mosdepth |
| Breadth at 10× (germline) | ≥ 90% | ≥ 90% of targets | ≥ 98% of targets | Picard `PCT_10X` |
| Duplicate rate | < 30% | < 40% | < 50% (UMI recommended) | MarkDuplicates / Picard `PCT_EXC_DUPE` |
| Mapping rate | > 95% | > 95% | > 95% | samtools flagstat / AlignmentSummaryMetrics |
| Mean base quality | ≥ Q30 across ≥ 80% of bases | same | same | FastQC / fastp |
| Insert size (PE150) | 300–500 bp, SD < 20% of mean | 150–300 bp | library-specific | CollectInsertSizeMetrics |
| On-target (capture) | n/a | ≥ 60% (`PCT_SELECTED_BASES`) | ≥ 70% | CollectHsMetrics |
| Contamination | < 1% | < 1% | < 1% | VerifyBamID (outside this skill) |

### One-liners

```bash
# Full raw → trimmed → FastQC → MultiQC
fastqc -t 8 -o qc/raw *.fastq.gz && \
fastp -i R1.fq.gz -I R2.fq.gz -o R1.trim.fq.gz -O R2.trim.fq.gz \
      --detect_adapter_for_pe --thread 8 --html fastp.html --json fastp.json && \
fastqc -t 8 -o qc/trim *.trim.fq.gz && \
multiqc qc -o qc/multiqc

# BAM QC bundle
samtools flagstat sample.bam > qc/sample.flagstat.txt
picard CollectAlignmentSummaryMetrics R=ref.fasta I=sample.bam O=qc/aln.txt
picard CollectInsertSizeMetrics I=sample.bam O=qc/ins.txt H=qc/ins.pdf
mosdepth --by 500 --threads 8 --fast-mode --no-per-base qc/sample sample.bam
```

### Tool roles at a glance

| Tool | Input | Primary output | Use for |
| --- | --- | --- | --- |
| FastQC | FASTQ | per-file HTML/zip | raw & post-trim read quality |
| fastp | FASTQ pair | trimmed FASTQ + JSON/HTML | adapter + quality trimming |
| samtools stats/flagstat | BAM | text | mapping counts, error rate |
| Picard AlignmentSummary | BAM | text | strand balance, PF reads, Q20/Q30 aligned bases |
| Picard InsertSize | BAM | text + PDF | PE insert distribution |
| Picard WgsMetrics | BAM | text | WGS coverage + breadth |
| Picard HsMetrics | BAM | text | WES/panel on-target & coverage |
| mosdepth | BAM | BED + dist | fast windowed / per-target depth |
| MultiQC | directory | single HTML | cohort aggregation |

## Common Mistakes

- **Wrong:** Running FastQC only after trimming
  **Right:** Run FastQC on *both* raw and trimmed reads
  **Why:** Pre-trim QC diagnoses the library; post-trim QC confirms trimming worked without over-clipping

- **Wrong:** Passing a raw BED file to Picard CollectHsMetrics
  **Right:** Convert to Picard-format `.interval_list` via `picard BedToIntervalList I=x.bed O=x.interval_list SD=ref.dict`
  **Why:** `BAIT_INTERVALS`/`TARGET_INTERVALS` require `.interval_list` with a full `@SQ` header; a raw BED will fail or silently produce wrong metrics

- **Wrong:** Using interval-list files with mismatched contig names or sort order
  **Right:** Ensure contig names (`chr1` vs `1`) and `@SQ` ordering match the BAM header exactly
  **Why:** Mismatches cause silent metric errors or tool failures

- **Wrong:** Running MarkDuplicates on trimmed FASTQs or name-sorted BAMs
  **Right:** Run MarkDuplicates only on coordinate-sorted, aligned BAMs
  **Why:** MarkDuplicates requires coordinate-sorted aligned reads to identify optical and PCR duplicates

- **Wrong:** Reporting only mean coverage as the QC metric
  **Right:** Always pair mean depth with breadth (`% ≥20x`) and duplicate rate
  **Why:** A high mean with poor uniformity hides failing targets

- **Wrong:** Trusting auto-encoding detection on pre-2012 FASTQ data
  **Right:** Verify Phred encoding explicitly before alignment for ancient data
  **Why:** Phred+64 data passed to a modern aligner produces silently wrong base qualities

- **Wrong:** Merging lanes/samples before running per-lane QC
  **Right:** Run FastQC per lane/FASTQ first; merge only after per-lane QC passes
  **Why:** A single bad lane becomes unidentifiable once merged

- **Wrong:** Using `--dedup` in fastp as the primary deduplication step
  **Right:** Use Picard MarkDuplicates or `samtools markdup` post-alignment for deduplication
  **Why:** fastp `--dedup` only catches exact-sequence duplicates pre-alignment, missing alignment-based duplicates

- **Wrong:** Running mosdepth on large genomes without `--no-per-base`
  **Right:** Always use `--no-per-base` for QC on large genomes
  **Why:** Per-base output is enormous and rarely needed; windowed/region output is sufficient for QC

## References

- FastQC: https://www.bioinformatics.babraham.ac.uk/projects/fastqc/
- fastp: Chen et al. Bioinformatics 2018, https://doi.org/10.1093/bioinformatics/bty560
- Picard: https://broadinstitute.github.io/picard/
- mosdepth: Pedersen & Quinlan, Bioinformatics 2018, https://doi.org/10.1093/bioinformatics/btx699
- Coverage recommendations: Sims et al. Nat Rev Genet 2014, https://doi.org/10.1038/nrg3642
