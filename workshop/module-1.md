# Module 1: Using Skills (30 min)

[← Overview](overview.md) | [Module 2 →](module-2.md)

Goal: feel the difference a skill makes on real life science R&D questions, and see how two reasoning skills compose when a single question spans two domains. This module works two prioritized use cases — a medical-imaging trial and a genomics trial. Each use case gives you one prompt that engages a single skill, then one prompt that engages two skills together, so you can watch a skill sharpen an answer *and* watch two skills divide a problem.

Throughout, you build your own evidence: run each prompt **without** the skill first to capture your baseline, then run it **with** explicit skill invocation, then diff the two against the "What to look for" table. The deltas are real but **uneven** — some exercises show a dramatic gap, some are deliberately narrow, and others land in between. The tables say so honestly, because learning to see a *small* delta is as important as seeing a large one.

## Before You Start — Two Sessions, Side by Side

Every exercise in this module is a **two-run comparison** — the same prompt answered once without the skill and once with it. The cleanest way to feel the difference is to open **two terminals with two agent sessions side by side** and keep them open for the whole module: a **baseline session** (no skill available) on the left, and a **skilled session** (started inside the `hcls-agent-skills` repo) on the right. Running them side by side makes the diff **immediate** rather than a scroll-back exercise, and you set this up **once** instead of per exercise. Each exercise's steps just name which skill(s) to invoke in the skilled session.

<details>
<summary><b>Claude Code</b></summary>

- **Baseline session:** start it **outside the repo** (a directory with no `.claude/skills/`) so no skill can fire.
- **Skilled session:** start it **inside the `hcls-agent-skills` repo** and invoke the skill explicitly (e.g. `/imaging-study-design`). Explicit invocation makes the skilled run deterministic even though Claude also auto-activates on a description match.
- The per-exercise steps name which skill(s) to invoke.

</details>

<details>
<summary><b>GitHub Copilot</b></summary>

- **Baseline session:** Copilot auto-discovers skills from their `description`, so an un-prefixed prompt in a skills-installed session is **not** a valid baseline — use a separate session where the skills are **not** installed.
- **Skilled session:** start it **inside the repo** and invoke the skill explicitly (e.g. `/imaging-study-design`). `/skills list` confirms a skill is loaded; `/skills reload` picks up mid-session changes.
- The per-exercise steps name which skill(s) to invoke.

</details>

---

## Use Case 1 — Medical Imaging + Clinical Trial

**Intended skills:** `imaging-study-design` and `translational-research`

A neuroimaging group is moving from study design toward a first efficacy trial. Exercise 1.1 engages `imaging-study-design` alone; Exercise 1.2 adds `translational-research` so the pair has to decide both *is the program ready* and *how should the imaging be built*.

### Exercise 1.1: Set Up a Multisite Longitudinal Atrophy Study (~7 min)

**Skill:** `imaging-study-design` (reasoning)

**Prompt:**

```
We're running a two-year longitudinal study to track hippocampal and cortical
atrophy in about 120 early Alzheimer's patients, scanned on 3T T1 MRI across
four different hospitals. Because this runs across four sites, what do I need
to consider so site differences don't swamp the atrophy signal we care about?
And how should we prepare the cohort's imaging data — preprocessing, QC, and
harmonization — so the measurements stay consistent and analysis-ready?
```

**Steps:**

1. **Baseline first.** In your **baseline session**, run the prompt and keep the answer (see [Before You Start](#before-you-start--two-sessions-side-by-side)).
2. **Then skilled.** In your **skilled session**, run the same prompt with `/imaging-study-design` invoked explicitly.
3. **Diff.** Put the two answers side by side and score them against the table below — most of the multisite playbook will match, so the delta to watch for is **specificity**.

**What to look for:**

| Signal | With the skill | Without the skill |
|--------|----------------|-------------------|
| QC thresholds | Pre-specifies **numeric QC thresholds and named metrics** — **Euler number**, SNR/CNR, motion/FD — before analysis | Qualitative QC only; **no thresholds, no named metrics** |
| Reader reliability | Sets a **κ/ICC reliability target** for reader-in-the-loop segmentation | Suggests only a **second rater** — no reliability metric |
| Reasoning path | Works an explicit **4-question sequence** (clinical question → modality → signal-preserving preprocessing → confounds) | Ad hoc walk-through with **no named framework** |

---

### Exercise 1.2: Is the Trial Ready, and How Should the Imaging Be Built? (~8 min)

**Skills:** `imaging-study-design` + `translational-research` 

**Prompt:**

```
My lab has a novel anti-tau antibody that reduced neurodegeneration in a mouse
model, and we think a volumetric MRI atrophy measure could be the readout in
our first efficacy trial in prodromal Alzheimer's. Is this program ready for
that trial, and if so how should we design the imaging so the measure actually
reflects the drug's effect?
```

**Steps:**

1. **Baseline first.** In your **baseline session**, run the prompt and keep the answer.
2. **Then skilled.** In your **skilled session**, run the same prompt with **both** skills invoked — name `/translational-research` and `/imaging-study-design` so both fire.
3. **Observe the handoff.** Note which skill answered which half: `translational-research` should own *is it ready* (T-staging, gates), `imaging-study-design` should own *how to build the readout*. Flag anything that fell **between** them.
4. **Diff** against the table below.

**What to look for:**

| Signal | With the skills | Without the skills |
|--------|-----------------|--------------------|
| Readiness framework | `translational-research` names the current **T-stage** and the next falsifiable **T-gate** with an explicit **kill criterion** before endorsing a trial | Was appropriately cautious and listed sensible evidence gaps — but named **no formal framework**: no T-stage, no gate, no kill criterion |
| BBB gate | Flags **blood-brain-barrier permeability** as a gate for an antibody reaching the CNS compartment | Did not raise BBB penetration at all |
| Target engagement | Requires a **target-engagement / PD readout before Phase 2**; challenges a volumetric endpoint as proof of **mechanism vs. benefit** | Suggested pairing with tau PET / CSF-plasma tau / NfL and a Phase 1b/2a proof-of-mechanism — reasonable, but not stated as a **requirement before** Phase 2 |
| Biomarker qualification | Assigns a **BEST category** and a **Context of Use (COU)** to the MRI measure; checks **endpoint-mechanism timescale match** for a 2-year neurodegeneration readout | Discussed atrophy as a "supportive" endpoint without BEST/COU vocabulary |
| Imaging design | `imaging-study-design` chooses **within-subject-baseline registration** and addresses **test-retest reliability (ICC ≥ 0.75, preferably ≥ 0.9)** for a measure serving as a trial endpoint | Called for a within-subject pipeline and pre-registered measure, but **no ICC target** for an endpoint |

---

## Use Case 2 — Genomics + Clinical Trial

**Intended skills:** `genomic-variant-interpretation` and `pharmacoepidemiology` 

A cardiovascular-genetics group needs to classify variants and then design a real-world study around one. Exercise 1.3 engages `genomic-variant-interpretation` alone on a KCNQ1 cardiac channelopathy variant; Exercise 1.4 adds `pharmacoepidemiology` on an LDLR / familial-hypercholesterolemia variant, so the pair spans *what is this variant* and *how do we study its effect in genotype-linked claims data*.

### Exercise 1.3: Classify a Canonical Splice Variant (~6 min)

**Skill:** `genomic-variant-interpretation` 

**Prompt:**

```
Help me classify a germline variant: KCNQ1 c.1032G>A, a canonical splice
variant at the +1 position. It's absent from gnomAD v4 at well-covered sites,
SpliceAI gives 0.91, and ClinVar lists it as likely pathogenic with a single
submitter. Which criteria apply and at what strength, and what's the final call?
```

**Steps:**

1. **Baseline first.** In your **baseline session**, run the prompt and keep the answer.
2. **Then skilled.** In your **skilled session**, run the same prompt with `/genomic-variant-interpretation` invoked explicitly.
3. **Diff** against the table — but expect a **narrow** delta: the final call is likely the **same** (**Pathogenic**) with and without the skill, and that is by design.

**What to look for:**

| Signal | With the skill | Without the skill |
|--------|----------------|-------------------|
| PVS1 derivation | **Walks the ClinGen SVI PVS1 decision tree** for the +1 canonical splice variant and states the strength it lands on **and why** | Applied **PVS1 at Very Strong** and noted the right caveats (NMD, exon position) — but **did not walk the SVI decision tree** to justify the strength |
| ClinVar weight | Explicitly **discounts the single-submitter 1-star** ClinVar entry as insufficient on its own | Noted it as "context, not independent evidence" — but didn't frame it as a 1-star discount |
| Gene-disease gate | Checks the **ClinGen Gene-Disease Validity** classification as a gate before classifying | **Did not** check gene-disease validity |
| Combination logic | Combines criteria via the **rules table / Bayesian point system** (PVS=8, PS=4, PM=2, PP=1), each criterion cited | Reached **Pathogenic** by the ACMG combining rules narratively |

---

### Exercise 1.4: Classify a Variant, Then Let It Define the Cohort (~8 min)

**Skills:** `genomic-variant-interpretation` + `pharmacoepidemiology` 

**Prompt:**

```
We have an LDLR variant from a research exome, and we want to build a study
around carriers.

  NM_000527.5(LDLR):c.1646G>A  p.(Gly549Asp), het
  gnomAD v4: global AF 1.2e-5, popmax 4.1e-5 (SAS), no homozygotes
  REVEL 0.82
  LDL-uptake assay: ~58% of wild-type activity
  Segregates in 2 affected relatives; 1 unaffected carrier, age 31
  ClinVar: 1 Likely pathogenic, 2 VUS, no assertion criteria, no expert panel
  Proband untreated LDL-C 232 mg/dL, DLCN score 6

First: classify it, and tell us what the classification turns on.

Second: we have 18,000 genotyped biobank participants with linked claims
(2016-2024, genotype never returned to clinicians). Design a study testing
whether carriers starting high-intensity statin monotherapy have more MACE
than carriers starting statin + ezetimibe — and tell us how your answer
above changes the cohort definition.
```

**Steps:**

1. **Baseline first.** In your **baseline session**, run the prompt and keep the answer.
2. **Then skilled.** In your **skilled session**, run the same prompt with **both** skills invoked — name `/genomic-variant-interpretation` and `/pharmacoepidemiology`.
3. **Observe the handoff.** The second half **depends** on the first: whether the variant is **Likely Pathogenic vs. VUS** decides who is eligible for the carrier cohort. Watch whether the design **propagates the classification into the inclusion rule** rather than echoing a label.
4. **Diff** against the table below — expect a **narrow** delta: a strong baseline reproduces most of the method, so the tells are **last-mile specificity**.

**What to look for:**

| Signal | With the skills | Without the skills |
|--------|-----------------|--------------------|
| Rarity threshold | Judges **PM2** against the **filtering allele frequency** (upper bound of the 95% CI) vs. max credible disease AF | Reached **PM2_Supporting** correctly — but off the **raw popmax AF** against VCEP cutoffs, no FAF |
| PS balance | Specifies **SMD < 0.1** (never p-values) and a matching **caliper of 0.2 × SD(logit-PS)** | Said **"report SMDs for balance"** and named IPTW/matching — but **no SMD threshold, no caliper** |

---

## Module 1 Debrief (1 min)

Reflect on these questions:

1. **Uneven deltas.** You saw a dramatic gap (1.2), a moderate specificity/auditability delta (1.1), and two deliberately narrow deltas where the baseline was already strong (1.3 and 1.4). What do those *narrower* deltas teach about where skills earn their keep in a **regulated** setting?
2. **Auditability vs. answer.** In 1.3 the final call was the same with and without the skill. Why might a **reproducible derivation** matter more than the conclusion itself?
3. **The handoff.** In the two-skill exercises (1.2, 1.4), which skill owned which half of the problem — and did anything fall **between** the two skills that neither handled well?
