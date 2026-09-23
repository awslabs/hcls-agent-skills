# HCLS Agent Skills — Hands-On Lab Guide

**Workshop:** Agent Skills for Life Sciences R&D
**Duration:** 90 minutes
**Format:** Hands-on, copy-paste driven. You run every prompt yourself.

This guide walks you through *using* skills, *extending* them with your own org knowledge, and *evaluating* whether your changes actually help. Every exercise gives you an exact prompt, step-by-step instructions, and a "what to look for" contrast between the skilled and unskilled response.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [How to Use This Guide](#how-to-use-this-guide)
- [Module 1: Using Skills (30 min)](#module-1-using-skills-30-min)
  - [Exercise 1.1: Classify a BRCA1 Variant (~12 min)](#exercise-11-classify-a-brca1-variant-12-min)
  - [Exercise 1.2: Build a Variant Calling Pipeline (~10 min)](#exercise-12-build-a-variant-calling-pipeline-10-min)
  - [Exercise 1.3: Explore a Drug Target — optional (~8 min)](#exercise-13-explore-a-drug-target--optional-8-min)
  - [Module 1 Debrief (3 min)](#module-1-debrief-3-min)
- [Module 2: Extending & Creating Skills (30 min)](#module-2-extending--creating-skills-30-min)
  - [Design Principles (8 min)](#design-principles-instructor-led-8-min)
  - [Exercise 2.1: Extend genomic-variant-interpretation (~15 min)](#exercise-21-extend-genomic-variant-interpretation-15-min)
  - [Exercise 2.2: Preview — Creating a Skill from Scratch (4 min)](#exercise-22-preview--creating-a-skill-from-scratch-instructor-walkthrough-4-min)
  - [Module 2 Debrief (3 min)](#module-2-debrief-3-min)
- [Module 3: Evaluating Skills — Take-Home (10 min)](#module-3-evaluating-skills--take-home-10-min)

---

## Prerequisites

> ⚠️ **Setup must be complete before you start.** This lab assumes you have finished the workshop setup guide (`workshop/setup-guide.md`). That means: the `hcls-agent-skills` repo cloned, skills installed for your harness (Kiro CLI, Claude Code, or Quick), and an editor open on the repo. This guide contains **no setup steps** — if `/agent hcls` or `/context add` doesn't work, go back to the setup guide first.

You should be able to:

- Start your agent (`kiro-cli chat`, then `/agent hcls`) or your equivalent harness.
- Load a single skill on demand with `/context add <path>`.
- Clear loaded context with `/context clear` (or start a fresh session).
- Open and edit files under `skills/` in your editor.

---

## How to Use This Guide

Each exercise follows the same three-part rhythm:

1. **The prompt** — copy it verbatim into your agent. Do not paraphrase.
2. **The steps** — run with the skill, then clear and run without it.
3. **What to look for** — the specific signals that separate a skilled response from a base-model answer.

> 💡 **Tip:** The whole point is the *contrast*. A skilled response and an unskilled response can both sound confident. You are training your eye to spot which one is actually applying a rigorous, reproducible framework versus generating plausible prose.

---

## MODULE 1: Using Skills (30 min)

Goal: feel the difference a skill makes on real R&D questions, and see how a reasoning skill and a pipeline skill compose on the same genomics thread.

### Exercise 1.1: Classify a BRCA1 Variant (~12 min)

**Skill:** `genomic-variant-interpretation` (reasoning)

You will classify two variants — one clear-cut pathogenic frameshift, one genuinely hard VUS — and compare skilled vs. unskilled answers.

**Prompt A — the frameshift (clear pathogenic):**

```
I have a BRCA1 variant: c.5266dupC (p.Gln1756Profs*74). It's a frameshift in
exon 20. gnomAD v4 shows AF = 0 (absent). ClinVar has this as pathogenic with
3-star review. The patient has a strong family history of breast and ovarian
cancer. Classify this variant using ACMG/AMP criteria.
```

**Prompt B — the missense (hard VUS):**

```
Now classify BRCA2 c.8188G>A (p.Ala2730Thr). This is a missense variant.
gnomAD v4 AF = 0.00003 (3 alleles in 100K). ClinVar: VUS with 1-star.
REVEL score: 0.45. CADD: 22.1. No functional studies. No segregation data.
How would you classify this, and what evidence would change the classification?
```

**Steps:**

1. Start your agent and load the skill:
   ```
   /context add skills/genomic-variant-interpretation/SKILL.md
   ```
2. Run **Prompt A**, then **Prompt B** in the same session. Read both answers.
3. Clear context to remove the skill:
   ```
   /context clear
   ```
4. Run **Prompt A** and **Prompt B** again — this time with **no skill loaded**.
5. Put the two versions of each answer side by side.

**What to look for:**

| Signal | With skill | Without skill |
|--------|-----------|---------------|
| Criterion codes | Names **PVS1**, **PM2_Supporting**, **PP4** explicitly, and calls out **PP5 as deprecated** | "This is clearly pathogenic" with little criterion-level justification |
| PVS1 rigor | Cites the **ClinGen SVI PVS1 decision tree** for the frameshift (exon 20, not last exon, predicted NMD) | Asserts loss-of-function without walking the decision tree |
| REVEL thresholds | Uses calibrated cutoffs: **>0.773 strong**, **>0.644 moderate**, **<0.290 benign** — and correctly notes 0.45 sits in the intermediate/uninformative zone | Treats REVEL 0.45 as "moderately damaging" with no calibrated cutoff |
| VUS honesty | Lands on **VUS** for BRCA2 and lists what would move it (functional studies → PS3/BS3, segregation → PP1/BS4, multi-gene panel case counts → PS4) | May over-call the VUS as "likely pathogenic" on weak in-silico evidence |
| Frequency logic | Applies frequency first; PM2_Supporting for absence with good coverage | Mentions gnomAD but doesn't tie it to a specific criterion strength |

> 💡 **Teaching point:** The skilled answer for Prompt A should reach **Pathogenic** via PVS1 + PM2_Supporting + supporting phenotype/segregation evidence. For Prompt B it should hold the line at **VUS** — REVEL 0.45 and CADD 22.1 are *not* enough. The base model tends to be overconfident on the hard case. That overconfidence is exactly the failure mode a clinical lab cannot afford.

---

### Exercise 1.2: Build a Variant Calling Pipeline (~10 min)

**Skill:** `variant-calling` (pipeline)

Now switch from *what does this variant mean* to *how do I find the variants in the first place.*

**Prompt:**

```
I have 15 WES samples from a familial breast cancer study. FASTQ files are
paired-end 150bp from a NovaSeq 6000. Reference is GRCh38. I need to call
germline variants and filter them. Give me the complete pipeline from FASTQ
to filtered VCF.
```

**Steps:**

1. In a fresh session, load the pipeline skill:
   ```
   /context add skills/variant-calling/SKILL.md
   ```
2. Run the prompt. Read the pipeline end to end.
3. `/context clear`, then run the same prompt with **no skill**.
4. Compare the two pipelines command by command.

**What to look for:**

| Signal | With skill | Without skill |
|--------|-----------|---------------|
| Aligner | **BWA-MEM2** (2x faster, same output) | Often defaults to legacy `bwa mem` |
| Read groups | Proper `@RG` header with `ID`, `SM`, `PL:ILLUMINA`, `LB` at alignment time | Frequently omits `@RG` → GATK fails or silently merges samples |
| Cohort strategy | `HaplotypeCaller -ERC GVCF` → `GenomicsDBImport` → `GenotypeGVCFs` | May emit per-sample VCFs that cannot be joint-genotyped |
| Filtering choice | **Hard filters, not VQSR** — correctly because 15 samples is **<30** | Reaches for VQSR (which needs ≥30 samples to train its Gaussian mixture) |
| Filter thresholds | SNPs `QD<2.0`, `FS>60.0`, `MQ<40.0`; indels `FS>200.0`, `ReadPosRankSum<-20.0` | Reuses SNP thresholds for indels (`FS>60`) → over-filters real indels |
| WES specifics | Restricts calling with `-L capture.bed -ip 100`, but keeps `--known-sites` genome-wide for BQSR | Subsets known-sites to the capture BED (wrong) or ignores intervals |

> ⚠️ **Watch for this trap:** With 15 samples the *only* correct filtering strategy is hard filters. If the unskilled response proposes VQSR, that pipeline will fail or produce garbage — VQSR cannot train on so few variants. This is the single clearest skilled-vs-unskilled tell in this exercise.

> 💡 **Teaching point — how the two skills compose:** In Exercise 1.1 you used the **reasoning** skill to decide *what a variant means*. Here the **pipeline** skill builds *how to find variants*. On a real familial breast cancer project these run back to back: `variant-calling` produces the filtered VCF, then `genomic-variant-interpretation` classifies each BRCA1/BRCA2 hit inside it. You decide **WHAT** to look for, then build **HOW** to find it — one continuous genomics thread.

---

### Exercise 1.3: Explore a Drug Target — optional (~8 min)

**Skill:** `drug-repurposing` (reasoning)

If time permits, tie back to the TREM2 / Alzheimer's demo shown in the presentation.

**Prompt:**

```
We're considering repurposing existing approved drugs that modulate TREM2 or
its signaling pathway for Alzheimer's disease. Query the relevant databases
and rank candidates by evidence strength.
```

**Steps:**

1. Load the skill:
   ```
   /context add skills/drug-repurposing/SKILL.md
   ```
2. Run the prompt. Then `/context clear` and run it again without the skill.

**What to look for:**

| Signal | With skill | Without skill |
|--------|-----------|---------------|
| Evidence hierarchy | Ranks by **genetic > functional > phenotypic** evidence | Lists candidates without a strength ordering |
| Named databases | **DGIdb**, **OpenTargets** (association score **>0.5** threshold), **ChEMBL**, DrugBank | Vague "search the literature / databases" |
| Potency cutoffs | IC50 **<1µM** = serious candidate, **<100nM** = priority | No potency thresholds |
| Translatability | Weighs existing safety data / approved status as a repurposing advantage | Treats it as a generic target-discovery question |

> 💡 **Callback:** This is the same TREM2 target from the `translational-research` demo. Notice how `drug-repurposing` answers *"which existing drug"* while `translational-research` answers *"is this target even ready to advance"* (T-staging, ≥3/4 genetic convergence, BBB as a blocking gate for antibodies). Different skills, same target, complementary decisions.

---

### Module 1 Debrief (3 min)

Reflect on these three questions:

1. Did the skilled response cite specific **ACMG criteria codes** (PVS1, PM2_Supporting) that the unskilled one missed or hand-waved?
2. Did the pipeline skill choose the **right filtering strategy for your cohort size** (hard filters for 15 samples, not VQSR)?
3. How did the **reasoning skill and pipeline skill compose** on the same genomics thread — deciding *what* to look for, then building *how* to find it?

---

## MODULE 2: Extending & Creating Skills (30 min)

Goal: make a skill *yours*. You'll add org-specific interpretation rules to a real skill and watch the agent's answer change.

### Design Principles (instructor-led, 8 min)

> ### 📐 Skill Design Principles — keep this open while you build
>
> - **Add what the agent lacks; omit what it already knows.** If the base model gets it right without help, cut it.
> - **Teach procedures, not facts.** Top-tier skills average **19.4 numbered steps**; bottom-tier average **4.3**.
> - **Use exact, niche thresholds.** `REVEL > 0.644 pathogenic` beats `adj.p < 0.05` (the model already knows the latter).
> - **Include decision trees** for reasoning skills — they correlate with the biggest critical-thinking gains.
> - **Prescribe an output format.** This is the primary defense against coherence regression from added content.
> - **Winners vs. losers:** `genomic-variant-interpretation` wins **90%** of head-to-head comparisons; `proteomics-analysis` wins only **30%** — because the latter recites well-known limma/DEP recipes the model already produces.

---

### Exercise 2.1: Extend genomic-variant-interpretation (~15 min)

This is the core hands-on exercise. You'll add your lab's gene-specific interpretation overrides to the variant skill.

**Steps:**

1. Open `skills/genomic-variant-interpretation/SKILL.md` in your editor.
2. Find the section on **computational predictors / PP3–BP4 thresholds** (it follows the population-frequency / BA1 discussion under "Core Concepts").
3. Add a new subsection titled **`### Lab-Specific Interpretation Overrides`**.
4. Paste in the **exact** text below:

   ```markdown
   ### Lab-Specific Interpretation Overrides

   #### Gene-Specific BA1 Thresholds
   Some genes have higher carrier frequencies for pathogenic variants. Use gene-specific BA1 instead of the default 5%:

   | Gene | Condition | BA1 Override | Rationale |
   |------|-----------|-------------|----------|
   | HFE | Hereditary hemochromatosis | BA1 = 10% | C282Y carrier freq ~10% in Northern Europeans |
   | GJB2 | DFNB1 hearing loss | BA1 = 5% (keep default) | 35delG carrier freq ~2-4% in Europeans |
   | SERPINA1 | Alpha-1 antitrypsin deficiency | BA1 = 10% | PiZ carrier freq ~4% in Northern Europeans |

   #### REVEL Threshold Adjustments for VCEP-Specific Genes
   For genes with ClinGen Variant Curation Expert Panel (VCEP) specifications, use VCEP thresholds instead of the generic SVI recommendations:

   | Gene/VCEP | PP3 (supporting pathogenic) | PP3_Moderate | PP3_Strong | BP4 (supporting benign) |
   |-----------|---------------------------|-------------|-----------|------------------------|
   | RASopathy VCEP | REVEL ≥ 0.644 | ≥ 0.773 | ≥ 0.932 | ≤ 0.290 |
   | CDH1 VCEP | REVEL ≥ 0.7 | ≥ 0.8 | N/A | ≤ 0.15 |
   | *Your gene here* | | | | |
   ```

5. **Save** the file.
6. Test the modification:
   - Load the modified skill in a fresh session:
     ```
     /context add skills/genomic-variant-interpretation/SKILL.md
     ```
   - Ask:
     ```
     I have an HFE C282Y variant with gnomAD AF of 8%. Is this BA1 benign?
     ```
   - The agent should now cite **your** gene-specific BA1 threshold (**10%**) and conclude the variant does **NOT** meet BA1 at 8%.
   - Now `/context clear` and ask the same question **without** the skill. The base model will most likely apply the standard **5%** BA1 and wrongly call it stand-alone benign.
7. Validate the skill structure (no AWS needed):
   ```bash
   python tests/validate_skill.py --skill genomic-variant-interpretation
   ```
   This checks frontmatter, ≤500 lines, required sections, ≥12 trigger keywords, and reasoning-skill decision-tree content.

**What to look for:**

- **With your edit:** the agent says 8% is below your **10%** HFE override → **BA1 does not apply** (the variant needs further workup, not an automatic benign call).
- **Without the skill:** the agent applies the generic **5%** rule → wrongly fires **BA1 stand-alone benign** at 8%.
- The difference is your encoded domain knowledge overriding the model's default. That's the entire value proposition of a customizable skill.

> ⚠️ **Gotcha:** If the agent still uses 5% *with* the skill loaded, check that (a) you saved the file, (b) you re-ran `/context add` after saving, and (c) your table landed in the right section. A stale loaded copy is the most common cause.

---

### Exercise 2.2: Preview — Creating a Skill from Scratch (instructor walkthrough, 4 min)

The instructor walks through the `pharmacovigilance-signal-detection` example in `CUSTOMIZING.md` as a template — but the shape is identical for any life-sciences domain.

**The frontmatter contract (all 5 fields required):**

```yaml
---
name: your-skill-name              # kebab-case, unique, matches directory
description: >                     # 2-3 sentences + ≥12 quoted trigger phrases
  ... "trigger one", "trigger two", ... "trigger twelve" ...
usage: Invoke when ...             # one-line trigger instruction
version: 1.0.0                     # semver
tags: [skill, category:reasoning, <domain>, hcls]   # first tag literally "skill"
---
```

**The body shape:**

`Purpose` → `Response Format` → numbered procedure (with decision branches) → threshold table → `Gotchas`.

> 🎯 **This is your Module 3 take-home stretch goal.** Domains with real gaps worth filling:
> - **Spatial transcriptomics** (Visium / Xenium) — QC and deconvolution decisions the model fumbles.
> - **Long-read structural variant calling** (Sniffles2 / cuteSV parameter selection).
> - **AlphaFold structure prediction** — pLDDT / PAE interpretation thresholds.
>
> **Or improve a weak skill:** `molecular-docking` wins only **50%**. Add target-class-specific grid-box sizing and a scoring-function selection tree — exactly the decision logic it's missing today.

---

### Module 2 Debrief (3 min)

1. Did your modified skill change the agent's answer for **HFE C282Y BA1** (10% override vs. default 5%)?
2. What **org-specific threshold or protocol** would you add next — a VCEP cutoff, a formulary rule, a sequencer-specific QC gate?

---

## MODULE 3: Evaluating Skills — Take-Home (10 min)

> 📋 **This module is instructor-presented, not hands-on.** Use it as a reference card for the take-home assignment. No AWS is needed for the structural check; the full pairwise eval needs Bedrock.

### How the Eval Works (reference)

- **Pairwise design:** the same prompt is answered **with** and **without** the skill. Responses are sanitized (skill fingerprints stripped) and position-randomized, then **Claude Opus** judges across **5 dimensions**.
- **Metrics:** **win rate** + **Cohen's d** (0.2 small / 0.5 medium / 0.8 large effect).
- **North star:** **critical thinking** — it's the least harness-sensitive dimension (78–85% across every harness configuration tested).

### Pre-Computed Results to Explore

The repo ships with a full evaluation you can browse right now:

- `eval/results/review.html` — interactive review dashboard (open in a browser).
- `eval/TECHNICAL_REPORT.md` — the full 410-prompt analysis.
- **Key rows to inspect:**
  - `genomic-variant-interpretation` — **90%** win (the skill you just extended).
  - `translational-research` — **100%** win, Cohen's d **+2.07** (v4).
  - `proteomics-analysis` — **30%** win (the cautionary tale — recites known recipes).

### Take-Home Assignment

```bash
# Structural check — no AWS, run this anytime
python tests/validate_skill.py --skill <your-skill>

# Full pairwise eval — needs Bedrock in us-east-1; ~15-20 min, ~$1-2
python -m eval.run --skill genomic-variant-interpretation \
  --parallel 2 --version workshop --pairwise
python eval/build_review.py
open eval/results/review.html
```

**What "good" looks like:** win rate ≥ **70%**, critical thinking positive, coherence neutral or positive.

### Take-Home Stretch Goals

1. **Run the eval on the skill you modified in Module 2** — did your HFE/VCEP overrides help, hurt, or stay neutral?
2. **Author a new skill from scratch** using the `CUSTOMIZING.md` template (spatial transcriptomics, long-read SV, or AlphaFold).
3. **Read `SKILL_DESIGN_GUIDE.md`** and diagnose *why* `proteomics-analysis` wins only 30% — then propose the fix.
4. **Full capstone:** pick a skill → use it → spot a weakness → improve it → re-eval → observe the delta.

---

> ✅ **You're done.** You've used reasoning and pipeline skills on real R&D questions, extended a skill with your own lab's rules, and seen how to prove whether a change helps. Take the eval loop home and make one skill measurably better.
