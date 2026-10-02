# Instructor Guide — HCLS Agent Skills Workshop

A facilitator guide for running the 90-minute **Agent Skills for Life Sciences R&D** workshop.

## Overview

- **Duration:** 90 minutes, hands-on, copy-paste driven (attendees run every prompt themselves).
- **Structure:** 3 modules — [Module 1: Using Skills](module-1.md), [Module 2: Extending & Creating Skills](module-2.md), [Module 3: Evaluating Skills](module-3.md). Start attendees on the [Overview](overview.md).
- **Audience:** life sciences researchers, bioinformaticians, and clinical data scientists.
- **Goal:** demonstrate that agent skills encode **reproducible methodology** — not just facts — and that this measurably improves an AI agent's responses on real R&D questions.

The through-line to reinforce all session: a skilled and an unskilled answer can both *sound* confident. The workshop trains attendees to spot which one is actually applying a rigorous, reproducible framework.

---

## Timing Table

| Time | Segment | Format | Notes |
|------|---------|--------|-------|
| 0:00–0:05 | Welcome, introductions, confirm setup | Instructor-led | Confirm everyone finished [setup.md](setup.md); skills are active in the chosen harness (Claude Code or GitHub Copilot) |
| 0:05–0:15 | Opening demo — TREM2 / `translational-research` | Live demo | Run the target-readiness prompt with the skill on the projector |
| 0:15–0:45 | **Module 1: Using Skills** | Hands-on (30 min) | Two use cases, two exercises each (single-skill, then both-skills) |
| &nbsp;&nbsp;0:15–0:22 | Ex 1.1: Multisite longitudinal atrophy study setup (`imaging-study-design`) | Hands-on (~7 min) | **Moderate delta** — baseline nails the multisite playbook; numeric QC thresholds, κ/ICC + 4-question sequence are the tells |
| &nbsp;&nbsp;0:22–0:30 | Ex 1.2: Trial readiness + imaging design (`imaging-study-design` + `translational-research`) | Hands-on (~8 min) | Largest delta; watch the readiness/design handoff |
| &nbsp;&nbsp;0:30–0:36 | Ex 1.3: Classify a canonical splice variant (`genomic-variant-interpretation`) | Hands-on (~6 min) | **Narrowest delta by design** — see facilitator note |
| &nbsp;&nbsp;0:36–0:44 | Ex 1.4: Classify a variant, then define the cohort (`genomic-variant-interpretation` + `pharmacoepidemiology`) | Hands-on (~8 min) | **Narrow delta** — baseline reaches LP via the FH VCEP and designs a sound target-trial emulation; FAF vs. raw popmax and the SMD/caliper specifics are the tells; watch the classification→cohort dependency |
| &nbsp;&nbsp;0:44–0:45 | Module 1 debrief | Discussion (1 min) | Fold into the tail of the block |
| 0:45–1:15 | **Module 2: Extending & Creating Skills** | (30 min) | |
| &nbsp;&nbsp;0:45–0:53 | Design principles | Instructor-led (8 min) | Present the 📐 design-principles box on the projector |
| &nbsp;&nbsp;0:53–1:08 | Ex 2.1: Extend `imaging-study-design` | Hands-on (~15 min) | Core exercise — endoscopic trial-eligibility + endoscopy de-id extension |
| &nbsp;&nbsp;1:08–1:12 | Ex 2.2: Skill-from-scratch preview | Instructor walkthrough (4 min) | Frontmatter contract + body shape |
| &nbsp;&nbsp;1:12–1:15 | Module 2 debrief | Discussion (3 min) | |
| 1:15–1:25 | **Module 3: Evaluating Skills** | Instructor-presented (10 min) | Walk `eval/results/review.html` and key win-rate rows |
| 1:25–1:30 | Wrap-up, Q&A, take-home assignment | Instructor-led (5 min) | Point to Module 3 take-home + stretch goals |

---

## Facilitator Answer Key

Make the contrast explicit at every exercise: run **with** the skill active, then run the same prompt **without** it (each module's steps show the per-harness mechanics). The exact codes, thresholds, and model IDs below are what a skilled agent should produce.

### Opening Demo — TREM2 / `translational-research`

- **Point of the demo:** show target-readiness reasoning before hands-on begins. The skilled agent applies T-staging (T0–T4), looks for **≥3/4 genetic convergence**, and flags **blood-brain barrier (BBB) penetration as a blocking gate** for antibody modalities.
- **Talking point:** `translational-research` is the readiness-reasoning skill attendees revisit in **Ex 1.2**, where it pairs with `imaging-study-design` to decide whether an anti-tau program is trial-ready. The demo answers *"is this target ready to advance?"* in isolation; Ex 1.2 shows it working alongside a second skill.

### Exercise 1.1 — Set Up a Multisite Longitudinal Atrophy Study (`imaging-study-design`)

Prompt: 120 early-AD patients, 3T T1 MRI, four sites, two-year hippocampal/cortical atrophy.

- **Skilled (expected):** rigid-registers follow-ups to a **within-subject / subject-baseline template** and reserves standard-space (**MNI**) for group-level analysis only; names **hippocampal volume + cortical thickness** as the AD-matched biomarker; harmonizes acquisition **first**, then **ComBat** (or site as random effect) **after** standardization; pre-specifies QC metrics and exclusion thresholds (**Euler number** for FreeSurfer T1 QC, **SNR/CNR**); works the 4-question sequence (clinical question → modality → signal-preserving preprocessing → confounds).
- **Unskilled (actual baseline):** genuinely strong, and it **got the registration target right** — used FreeSurfer's longitudinal within-subject template for the atrophy measure and explicitly reserved **MNI** for group-level analysis only (exactly what the skill endorses). Named FreeSurfer/FSL/SPM longitudinal streams, ADNI-style MPRAGE, phantom scans, ComBat, and stated harmonizing acquisition up front beats post-hoc correction; handled site as a **random or fixed effect in a mixed model**. What it lacked: **pre-specified** QC metrics/thresholds (asked only for "visual QC") and the explicit 4-question framework.
- **Key tell:** **pre-specified QC thresholds + a κ/ICC reliability target + the inspectable 4-question sequence** — not registration space, which both arms get right. This is a **moderate delta**: specificity and auditability across several dimensions. Unlike 1.3, where even the final call was identical, the skill here adds real measurement rigor rather than only a reproducible derivation.
- **⚠️ Facilitator note:** 1.3 and 1.4 are both **narrow** deltas (the baseline is already strong on both halves); 1.1 is a **moderate** delta where the skill sharpens a strong answer with measurement rigor, and 1.2 is where the **clearest** contrast appears — set expectations accordingly.
- **Teaching point (say this out loud):** The unaided answer was genuinely strong and got the hard calls **right** — it even covered central processing on a **frozen software version**, **same-scanner-per-subject**, **scanner-upgrade breakpoints**, and **differential dropout**. The skill does **not** overturn those calls; it **sharpens a strong answer rather than correcting a wrong one**, adding measurement rigor across several dimensions.

### Exercise 1.2 — Trial Readiness + Imaging Design (`imaging-study-design` + `translational-research`)

Prompt: anti-tau antibody, mouse neurodegeneration data, volumetric MRI atrophy as the readout for a first prodromal-AD efficacy trial.

- **Skilled (expected):** `translational-research` names the current **T-stage** and the next falsifiable **T-gate** with an explicit **kill criterion**; flags **BBB permeability** as a gate for a CNS antibody; requires a **target-engagement / PD readout before Phase 2** and challenges the volumetric endpoint as proof of **mechanism vs. benefit**; assigns a **BEST category** and **Context of Use (COU)**; checks **endpoint-mechanism timescale match**. `imaging-study-design` chooses **within-subject-baseline registration** and sets **test-retest reliability (ICC ≥ 0.75, preferably ≥ 0.9)** for an endpoint measure.
- **Unskilled (actual baseline):** thoughtful and appropriately cautious — discussed tau PET, CSF/plasma tau and NfL, Phase 1b/2a proof-of-mechanism, hippocampal/cortical readouts, enrichment for progressors. But named **no formal framework**: no T-stage, no COU/BEST category, no BBB gate, no target-engagement-before-Phase-2 requirement, no kill criterion, no ICC target.
- **Key tell:** **largest delta of the four.** The win is converting good instincts into a gated, qualifiable plan.
- **Handoff to watch:** readiness is `translational-research`'s half, imaging design is `imaging-study-design`'s half. Ask attendees whether anything fell between them.

### Exercise 1.3 — Classify a Canonical Splice Variant (`genomic-variant-interpretation`)

Prompt: KCNQ1 c.1032G>A, canonical +1 splice, absent gnomAD v4 (well-covered), SpliceAI 0.91, ClinVar LP single submitter.

- **Skilled (expected):** explicitly selects **ACMG/AMP 2015 germline** (not somatic AMP/ASCO/CAP); **walks the ClinGen SVI PVS1 decision tree** and states the strength it lands on and why; **PM2_Supporting** (not PM2 Moderate); treats SpliceAI 0.91 as above the **≥0.8** cutoff but does **not** double-count PP3 with PVS1 on a canonical splice variant; **discounts the single-submitter 1-star** ClinVar entry; checks **ClinGen Gene-Disease Validity** as a gate; combines via the **rules table / Bayesian points** (PVS=8, PS=4, PM=2, PP=1). Final call: **Pathogenic**.
- **Unskilled (actual baseline):** already strong — cited ACMG/AMP, **PVS1 at Very Strong**, **PM2_Supporting**, the **PP3 double-counting caveat**, SpliceAI 0.91, gnomAD v4, and reached **Pathogenic** — the **same final call**. What it did **not** do: walk the SVI PVS1 decision tree, check gene-disease validity, or explicitly discount the 1-star submission.
- **⚠️ Facilitator note — the delta is NARROW by design.** This is intentional. If an attendee says *"the answers look the same,"* that is the expected observation, not a setup failure — **confirm it and reframe**: the final call *is* the same; the win is a **reproducible, auditable derivation** (SVI tree + gene-disease gate + points table), which is what matters in a regulated/clinical setting where two reviewers must reach the same call *the same way*. Do **not** manufacture a bigger gap. Before concluding the skill "didn't fire," verify explicit invocation and a clean baseline — but if both arms genuinely land on Pathogenic, that is correct and on-message.

### Exercise 1.4 — Classify a Variant, Then Let It Define the Cohort (`genomic-variant-interpretation` + `pharmacoepidemiology`)

Prompt: borderline LDLR c.1646G>A p.(Gly549Asp) annotation — classify and say what it turns on, then design a high-intensity statin monotherapy vs. statin + ezetimibe MACE study on 18,000 genotyped biobank participants with linked claims, and state how the call changes the cohort definition.

- **Skilled (expected):** `genomic-variant-interpretation` reaches **Likely Pathogenic (borderline)** under the **ClinGen FH VCEP** spec — **PM2_Supporting** judged against the **filtering allele frequency**, calibrated **REVEL ≥ 0.773 → PP3_Moderate**, **PS3 downgraded to Supporting** for 58% partial function, **PP1_Supporting**, **PP4**, **BS4 not fired** on the 31-y-old unaffected carrier, **criteria-free ClinVar discounted**, combined on the **Bayesian point system** (PVS=8, PS=4, PM=2, PP=1). `pharmacoepidemiology` builds a **target-trial emulation**, **new-user active-comparator**, **180–365 day washout**, **time zero at initiation** (immortal time), **SMD < 0.1** and **caliper 0.2 × SD(logit-PS)**, **E-value + 3–5 negative controls**, **ITT vs. per-protocol IPW** — and makes the cohort **depend on the call**: LP → carriers are eligible; VUS → they cannot define the FH cohort.
- **Unskilled (actual baseline):** remarkably strong — independently reached **Likely Pathogenic**, named the **ClinGen FH VCEP**, used the **calibrated REVEL threshold**, **downgraded PS3 to Supporting** for partial function, **did not fire BS4**, **discounted the criteria-free ClinVar** split, and tallied on the **point system**; on design it produced **target-trial emulation**, **new-user active-comparator**, a **12-month washout**, **grace-period / clone-censor-weight** for immortal time, **ITT + per-protocol IPW**, **propensity weighting for confounding by indication**, **E-value + negative controls**, caught the **power problem** (~60–75 carriers → make LDL-C the primary endpoint), and nailed the **classification→cohort dependency** (LP includes, VUS excludes). What it did **not** do: judge PM2 off a **filtering allele frequency** (used raw popmax), or specify an **SMD < 0.1 threshold or matching caliper** (said only "report SMDs").
- **Key tell:** **narrow delta** — the baseline matched the skilled answer on nearly every load-bearing move; the residue is **FAF vs. raw popmax** and the **SMD/caliper** specifics.
- **Handoff to watch:** the two halves are **genuinely dependent** — the classification sets the cohort inclusion rule, so watch whether the design propagates **LP vs. VUS** into eligibility rather than echoing a label.
- **Teaching point (say this out loud):** a strong model can reproduce most of the methodology unaided; here the skill's residual value is **last-mile specificity** (filtering allele frequency, SMD/caliper) and a **guaranteed, auditable** derivation — not a different conclusion. Honest narrow deltas are the point of the module.

### Exercise 2.1 — Extend `imaging-study-design` (endoscopic trial-eligibility + de-id)

Attendees add a **Lab-Specific Endoscopic Trial-Eligibility and De-identification** subsection (an eligibility-scoring table + an endoscopy de-identification table) immediately after `### 4. Imaging biomarker selection by indication` under "Core Concepts", then test with: *"I'm writing endoscopic entry criteria for a moderate-to-severe UC trial using the Mayo endoscopic subscore (MES), with UCEIS as a secondary measure. What MES cutoff should patients meet at baseline, and what UCEIS score range should I put on the CRF?"*

- **Skilled (with the edit):** cites the encoded **baseline MES ≥ 2** entry cutoff (range 0–3; improvement = 0 or 1) **and** flags that UCEIS has two numbering conventions — **3–11** (original 1-based) vs **0–8** (modern 0-based) — so the CRF must specify which, and that UCEIS severity bands are **not** a single fixed standard.
- **Unskilled / unedited:** will **likely still get MES ≥ 2 right** (well documented), but tends to report a **single** UCEIS range (usually 0–8) without surfacing the dual-numbering ambiguity, and may present severity bands as if universal.
- **Talking points:** this is an **honest, moderate delta** — not a wrong-vs-right flip on the headline number. The win is last-mile discipline: the exact numbering convention the CRF depends on, and the refusal to hard-code cutoffs the field treats as protocol-specific (SES-CD trial-entry activity, UCEIS bands). That encoded local knowledge is the value proposition of a customizable skill.
- **Troubleshooting (if the skill edit didn't take):** the agent still giving a single UCEIS range *with* the edit in place almost always means (a) the file wasn't **saved**, (b) the agent didn't re-read the edited file (Claude Code re-reads automatically; GitHub Copilot: run `/skills reload` — a stale copy is the most common cause), or (c) the tables landed in the wrong section. Also run `python tests/validate_skill.py --skill imaging-study-design` to confirm structure (frontmatter, ≤500 lines, required sections, ≥12 trigger keywords, decision-tree content).

### Exercise 2.2 — Skill-from-Scratch Preview (instructor walkthrough)

Walk the `pharmacovigilance-signal-detection` example in `CUSTOMIZING.md`. Emphasize:

- **Frontmatter contract (all 5 fields required):** `name` (kebab-case, matches directory), `description` (2–3 sentences + **≥12 quoted trigger phrases**), `usage`, `version` (semver), `tags` (first tag literally `skill`).
- **Body shape:** `Purpose` → `Response Format` → numbered procedure with decision branches → threshold table → `Gotchas`.
- Tie to the take-home stretch goals: two endoscopy-cohort skills adjacent to the one just extended — `endoscopy-pixel-deid` (pipeline: OCR-driven burned-in-PHI redaction, the unreliable `BurnedInAnnotation` flag, PS3.15 Clean Pixel Data Option, date-shift + crosswalk for longitudinal linkage) and `ibd-endoscopic-endpoint-scoring` (reasoning: MES / UCEIS numbering / SES-CD / BBPS eligibility logic + central blinded reading, flagging protocol-specific vs universal cutoffs).

### Module 3 — Evaluation (instructor-presented)

- **Pairwise design:** same prompt answered **with** and **without** the skill; responses sanitized (fingerprints stripped) and position-randomized; **Claude Opus** judges across **5 dimensions**.
- **Metrics:** **win rate** + **Cohen's d** (0.2 small / 0.5 medium / 0.8 large).
- **North star:** **critical thinking** (least harness-sensitive, 78–85% across configs).
- **Key rows to show in `eval/results/review.html`:** `genomic-variant-interpretation` **90%** win; `translational-research` **100%** win, Cohen's d **+2.07** (v4); `quantitative-proteomics` **30%** win (cautionary tale — recites known recipes).
- **What "good" looks like:** win rate ≥ **70%**, critical thinking positive, coherence neutral or positive.

---

## Talking Points (transitions)

- **Module 1 intro:** "Skills encode methodology, not just facts. Watch what the skill adds that the base model can't reproduce on its own."
- **Module 1 → 2 transition:** "Now you've seen the difference — let's make it yours."
- **Module 2 intro:** "The best skills add what the model lacks: your lab's thresholds, your org's protocols."
- **Module 2 → 3 transition:** "Intuition says it helps. Eval proves it."
- **Closing:** "Take the eval loop home. Make one skill measurably better."

---

## Room Setup & Logistics

- **Attendee environments:** setup must be complete before the session — repo cloned, skills installed, editor open on the repo, and the chosen harness (Claude Code or GitHub Copilot) working. Attendees run in a pre-provisioned Linux compute environment (AWS Workshop Studio) with the coding agent already installed and signed in. See [setup.md](setup.md). This guide contains no setup steps; redirect any setup issues there during the 0:00–0:05 block.
- **Harnesses in the room:** attendees pick one of two — **Claude Code** or **GitHub Copilot**. Both are pre-installed and signed in on the compute environment, both install skills with a single `npx skills add awslabs/hcls-agent-skills -a <harness>` command, and **both invoke skills the same way — `/skill-name`**. The two arms of every exercise now differ only in setup, not in how a skill is invoked, so you can support a mixed room without maintaining two invocation stories, and there's no friction-based reason to steer the room toward one harness. The one difference that matters for the exercises: Claude Code won't fire a skill from a directory with no `.claude/skills/`, while **Copilot auto-discovers skills from their `description`** — so the *unskilled baseline* on Copilot must be a session where the skills aren't installed (or a prompt that avoids naming the skill), **not** merely an un-prefixed prompt. Call this out when Copilot users produce their baseline.
- **Projector:** for the opening TREM2 demo, the Module 2 design-principles presentation, and the Module 3 eval dashboard.
- **Slack/chat channel:** stand one up for attendees to share prompts, paste outputs, and get troubleshooting help without interrupting the room.
- **Pre-open `eval/results/review.html`** in a browser before Module 3 so the dashboard is ready to walk live.

---

## Common Failure Modes

| Symptom | Fix |
|---------|-----|
| **Skill not loading** | Claude Code: re-run `npx skills add awslabs/hcls-agent-skills -a claude-code` and run inside the repo; verify the file exists (e.g. `skills/genomic-variant-interpretation/SKILL.md`). GitHub Copilot: re-run `npx skills add awslabs/hcls-agent-skills -a github-copilot`, confirm `/skills list` shows the skill, and `/skills reload` if it was added mid-session. |
| **Agent gives the same answer with and without the skill** | The unskilled pass still had the skill active — separate the conditions (Claude Code: outside the repo; GitHub Copilot: a session where the skills are **not** installed, or a prompt that doesn't name the skill — Copilot auto-discovers from the `description`). |
| **Ex 1.3 answers look the same with and without the skill** | **Expected — the delta is narrow by design.** Confirm explicit `/genomic-variant-interpretation` invocation and a clean baseline, but if both arms land on **Pathogenic** that is correct. Reframe the win as the reproducible, auditable derivation (SVI PVS1 tree, gene-disease gate, points table), not a different call. |
| **Ex 2.1 still reports a single UCEIS range with the skill active** | Check (a) file saved, (b) agent re-read it (Claude Code auto; GitHub Copilot: `/skills reload`), (c) tables in the right section (after §4). Expect MES ≥ 2 right either way — the tell is the UCEIS 3–11 vs 0–8 flag. |
| **`validate_skill.py` fails** | Check Python version, confirm the venv is activated, and install missing dev dependencies. |

---

*Do not modify the module files during the session. All exercises, prompts, tables, and thresholds live in [Module 1](module-1.md), [Module 2](module-2.md), and [Module 3](module-3.md).*
