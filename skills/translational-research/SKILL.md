---
name: translational-research
description: Reason about translational research problems in HCLS — especially neurology and hypothesis validation. Use when the user asks to design a validation study, evaluate a target, qualify a biomarker, choose endpoints, critique a preclinical-to-clinical plan, pick a trial design (basket/umbrella/platform), plan multimodal data integration, or assess whether a hypothesis is ready to advance. Triggers include phrases like "validate target", "biomarker context of use", "bench to bedside", "T0/T1/T2/T3/T4", "proof of mechanism", "target engagement", "design a trial for", "preclinical model translates", "imaging-genetics", "is this ready for Phase 2", "mouse results to humans", "GWAS/eQTL/MR", "endpoint selection", "drug repurposing rationale", "fail fast".
usage: Invoke when designing validation studies, evaluating targets, qualifying biomarkers, or assessing readiness to advance a hypothesis.
version: 1.0.0
tags: [skill, category:reasoning, translational-research, neurology, hypothesis-validation, hcls]
---

# Translational Research Reasoning

## Overview

You are reasoning about moving a biological hypothesis across the bench-to-bedside continuum. Your job is not to cheerlead — it is to find the weakest link and name the next falsifiable gate. Every recommendation must be anchored to a translation stage, a decision, and an evidence standard. If you cannot identify the decision the next experiment will enable, refuse to propose experiments and ask for the decision first.

## Usage

Invoke this skill whenever the user is evaluating, designing, or critiquing translational work: target validation, biomarker qualification, preclinical plans, first-in-human or Phase 2 design, endpoint selection, multimodal data strategy, or "should we advance" calls. Apply the frameworks in order:

1. Orient: what T-stage is this hypothesis in, and what is the next T-gate?
2. Audit: use the relevant framework (target validation, biomarker COU, trial design) to find the weakest link.
3. Decide: recommend the minimum experiment or evidence that moves the hypothesis past the next gate — or kills it.
4. Flag failure modes explicitly before closing.

Do not skip step 1. Do not propose experiments without naming the decision they enable.

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

- **T-stages (T0–T4)** orient work to decisions, not activities.
- **Target validation** is a convergence problem across human genetics, functional biology, and druggability.
- **Biomarkers are not data** — they are decisions. A biomarker without a Context of Use (COU) is noise.
- **Preclinical models are wrong by default**; ask how they are wrong before trusting them.
- **Phase 2 tests biology, Phase 3 tests clinical benefit.** Conflating these is a top failure mode.
- **Trial designs encode what is shared** (mechanism, disease, or infrastructure). Pick the design that matches the shared entity.
- **Multimodal integration is a confounding problem first, a modeling problem second.**

---

## 1. Translation Stages (T0–T4)

Every hypothesis lives at exactly one T-stage. Identify it before anything else.

| Stage | Question answered | Typical evidence |
| --- | --- | --- |
| T0 | Does the mechanism exist? | In vitro, omics, model organisms |
| T1 | Does it translate to humans? | First-in-human, PoM, PD biomarkers |
| T2 | Does it work in a controlled trial? | Phase 2/3 efficacy, PoC |
| T3 | Does it work in practice? | Effectiveness, RWE, implementation |
| T4 | Does it improve population health? | Policy, outcomes at scale |

**Decision rule.** Before proposing any experiment:
1. Name the current T-stage.
2. Name the next T-gate (the specific claim the next stage requires).
3. Name the falsifiable result that would open that gate — and the result that would kill the program.

If you cannot state the kill criterion, the gate is not falsifiable. Stop and reframe.

---

## 2. Target Validation Framework

Default posture: **human genetics first.** Non-human evidence supports, it does not substitute.

**Convergence checklist (require ≥3 of 4 before enthusiasm):**
- GWAS signal at the locus in the relevant population.
- Rare-variant / burden-test support (loss- or gain-of-function consistent with proposed direction).
- eQTL or sQTL colocalization in the **disease-relevant tissue and cell type**.
- Mendelian randomization (MR) with **cis-pQTL instruments** giving a causal direction consistent with the therapeutic hypothesis.

**Decision rules:**
- **No human genetic signal → demand stronger functional evidence** (human tissue, iPSC-derived disease-relevant cells, patient-derived perturbations). Do not accept rodent-only support.
- **MR direction opposes the therapeutic direction → stop.** Reassess mechanism before spending more.
- **eQTL is in wrong tissue/cell type → treat as hypothesis-generating only.**
- **Druggability check:** modality feasible (small molecule, biologic, ASO, gene therapy)? Pocket? Expression at the right site?
- **CNS targets:** BBB permeability for the chosen modality is a gate, not an afterthought. If the modality cannot reach the compartment, the target is not actionable as proposed.

**When to stop and reframe:** target is "interesting" but not druggable with available modalities, or genetic direction is inconsistent with the intervention direction.

---

## 3. Biomarker Qualification (BEST Framework)

A biomarker is a **decision instrument**. Without a Context of Use, it is unqualified.

**Every biomarker must specify:**
- **Population** (who is it measured in)
- **Decision** (what action changes based on the value)
- **Category** (see below)

**BEST categories — pick exactly one primary:**
- **Diagnostic** — does this patient have the disease/subtype?
- **Monitoring** — is the disease or exposure changing over time?
- **Pharmacodynamic / Response** — did the drug hit the target / is the biology moving?
- **Predictive** — will this patient respond to this intervention?
- **Prognostic** — what is the natural course regardless of intervention?
- **Safety** — is harm occurring or imminent?
- **Susceptibility / Risk** — what is baseline risk of developing disease?

**Evidence hierarchy (do not skip levels):**
1. **Analytical validation** — accuracy, precision, reproducibility of the measurement itself.
2. **Clinical validation** — biomarker associates with the clinical state / outcome in the COU population.
3. **Clinical utility** — using the biomarker changes decisions and improves outcomes versus not using it.

**Decision rules:**
- Biomarker proposed without COU → **reject and ask for population + decision + category.**
- Category conflated (e.g., "prognostic/predictive") → force separation; they require different study designs (prognostic: single-arm natural history; predictive: treatment-by-biomarker interaction).
- Analytical validation skipped → any downstream signal is uninterpretable. Fix first.
- PD biomarker proposed as efficacy endpoint in Phase 3 → challenge. PD confirms engagement, not benefit.

---

## 4. Preclinical-to-Clinical Pitfalls

Assume the preclinical package is misleading until proven otherwise. Audit for:

- **Species BBB differences** — efflux transporters (P-gp, BCRP), tight-junction biology, and receptor expression differ. A compound penetrant in mouse may not be in human, and vice versa.
- **Free vs total brain concentration** — total brain drug levels are nearly useless. Demand **unbound brain concentration** and compare to in vitro potency (Kp,uu, not Kp).
- **Model validity triad:**
  - *Face validity* (does it look like the disease) — weakest.
  - *Construct validity* (does it share mechanism) — required.
  - *Predictive validity* (do interventions that work here work in humans) — what actually matters.
- **Behavioral translation failure** — over 90% of CNS behavioral readouts fail to translate. Treat rodent behavior as hypothesis-generating, not confirmatory.
- **Underpowered studies** — n=6–8 per arm is not evidence. Demand power calculations and pre-registration.
- **Single-lab bias** — independent replication in a second lab, ideally blinded and pre-registered, before committing clinical resources.
- **Sex as a biological variable** — both sexes, analyzed, not pooled by default.
- **Reverse translation gap** — if the human disease biology is not recapitulated, a positive result is a coincidence.

**Decision rule:** if the preclinical package lacks free-compartment PK, construct validity, or independent replication, **do not advance to IND-enabling work** until fixed.

---

## 5. Endpoint Selection

**Rule of thumb:** early phases test biology, late phases test benefit. Do not invert this.

- **Phase 1 / early PoM:** target engagement (receptor occupancy, PD biomarker, imaging), safety, PK including free CNS concentration for CNS drugs.
- **Phase 2 / PoC:** biology-anchored endpoints — fluid biomarkers (e.g., CSF/plasma protein changes), imaging (volumetric, functional, molecular), electrophysiology. Clinical scales here are secondary.
- **Phase 3:** clinical benefit on regulator-accepted endpoints, with pre-specified subgroups.

**Decision rules:**
- Clinical scales as **primary** in Phase 2 of a novel mechanism → challenge. Noise will dominate; you will fail a working drug or pass a broken one.
- **Timescale mismatch** — endpoint must change on the timescale of the mechanism. A neurodegeneration trial with a 12-week cognitive primary is mismatched to a mechanism that acts on months-long neurodegeneration.
- No **target engagement** readout planned before Phase 2 → **block advancement.** You cannot interpret a negative trial without engagement data.
- Composite endpoints hide effects. Pre-specify component analyses.

---

## 6. Study Design Patterns

**Sequence:** Proof of Mechanism (PoM) → Proof of Concept (PoC) → Confirmatory. Do not pay for PoC before PoM is credible.

**Choosing the design — ask "what is shared?":**
- **Shared mechanism, multiple diseases → Basket trial.** One drug/mechanism, patients across diseases with a common molecular feature.
- **Shared disease, multiple mechanisms → Umbrella trial.** One disease, biomarker-defined subgroups routed to different interventions.
- **Shared infrastructure, persistent question → Platform trial.** Primary protocol, arms add and drop over time (e.g., neurodegeneration platforms).

**Adaptive designs** (response-adaptive randomization, sample-size re-estimation, arm dropping) are appropriate when:
- Biomarker-defined subgroups exist and enrichment is plausible.
- Early readouts are reliable enough to adapt on.
- Operational capacity supports interim analyses with statistical rigor (alpha control, pre-specified rules).

**Decision rules:**
- Heterogeneous population, no stratifier → do not randomize yet. Find the stratifier or the trial will fail for the wrong reason.
- Platform-trial pitch without shared endpoint and governance → reject. The cost is governance, not statistics.
- Enrichment strategy without predictive biomarker evidence → it is guessing.

---

## 7. Multimodal Data Integration

Common modalities: genomics, transcriptomics, proteomics, imaging (MRI/PET), EHR, digital/wearable, fluid biomarkers.

**Fusion strategies:**
- **Early fusion** — concatenate raw/low-level features. Use when modalities are aligned and low-dimensional.
- **Intermediate fusion** — learn modality-specific representations, then combine. Default for heterogeneous modalities.
- **Late fusion** — combine predictions. Use when modalities are collected at different times/sites or models must remain separable for regulatory reasons.

**Specific patterns:**
- **Imaging-genetics for endophenotypes** — map genetic variation to intermediate brain phenotypes that are closer to biology than clinical labels. Useful when clinical diagnosis is heterogeneous.
- **Disease-progression models** (e.g., latent-time models, event-based models) — convert cross-sectional multimodal data into a temporal ordering. Essential when follow-up is short relative to disease.
- **Missing modality handling** — do not impute silently. Either model missingness explicitly (indicator + conditional model) or restrict analysis to the complete-case subset and report both.

**Confounding — check before modeling:**
- Site / scanner / batch effects (ComBat-style adjustment or site as random effect).
- Age, sex, population structure (PCs for genetics).
- Ascertainment bias in EHR-derived cohorts.
- Informative missingness (missingness correlates with outcome).

**Decision rule:** if you cannot name the top three confounders for the proposed analysis, stop and enumerate them before proposing a model.

---

## 8. Failure Modes to Flag

Raise these explicitly whenever present. Do not bury them.

- **No falsifiable T-gate** — no result would change the program's direction.
- **No target engagement plan before Phase 2** — you are buying a trial you cannot interpret.
- **Single-lab preclinical evidence** — no independent replication.
- **Biomarker without COU** — population, decision, or category unspecified.
- **Endpoint–mechanism timescale mismatch** — endpoint cannot move in the trial duration.
- **Population heterogeneity ignored** — no stratifier for a disease known to be heterogeneous.
- **Clinical scales as Phase 2 primary for novel mechanism** — noise dominates.
- **MR direction opposes intervention direction** — ignored genetic warning.
- **Construct validity assumed from face validity** — model looks like the disease but does not share mechanism.
- **Repurposing rationale is epidemiological only** — confounded by indication; demand genetic or mechanistic support.

---

## When NOT to Use This Skill

- Making IND-enabling decisions without toxicology data
- When the question is purely clinical (Phase 3 endpoint selection needs clinical trialist)
- Regulatory strategy for specific submissions (needs regulatory affairs specialist)

## When to Escalate to a Human Expert

- Before committing resources to a target based solely on computational evidence
- When preclinical model validity for the specific indication is uncertain
- When translational biomarker requires prospective clinical validation

## Common Mistakes

- **Wrong:** Proposing experiments before identifying the decision they will enable
  **Right:** Always define decision → experiment, never experiment → decision
  **Why:** Experiments without a clear decision gate generate data that cannot advance or kill a program

- **Wrong:** Treating rodent behavioral readouts as confirmatory evidence
  **Right:** Treat rodent behavior as hypothesis-generating only; require human-relevant confirmation
  **Why:** Over 90% of CNS behavioral readouts fail to translate to humans

- **Wrong:** Using total brain drug concentration to assess CNS target engagement
  **Right:** Use unbound (free) brain concentration (Kp,uu) and compare to in vitro potency
  **Why:** Total concentration includes protein-bound drug that is pharmacologically inactive

- **Wrong:** Conflating a moving PD biomarker with evidence of efficacy
  **Right:** Treat PD as confirmation of target engagement only; require separate efficacy evidence
  **Why:** Target engagement is necessary but not sufficient — the target may not drive the disease

- **Wrong:** Collapsing prognostic and predictive biomarkers into a single category
  **Right:** Separate them explicitly — they require different study designs and different evidence
  **Why:** Prognostic needs single-arm natural history; predictive needs treatment-by-biomarker interaction testing

- **Wrong:** Picking basket/umbrella/platform trial design based on trend rather than data structure
  **Right:** Choose by what is shared: shared mechanism → basket; shared disease → umbrella; shared infrastructure → platform
  **Why:** Mismatched design wastes resources and produces uninterpretable results

- **Wrong:** Imputing missing modalities without modeling the missingness mechanism
  **Right:** Model missingness explicitly (indicator + conditional model) or restrict to complete cases and report both
  **Why:** Silent imputation introduces outcome-correlated bias when missingness is informative

- **Wrong:** Claiming "multi-omics integration" when datasets were analyzed separately and results compared
  **Right:** Perform joint statistical analysis across modalities (early, intermediate, or late fusion)
  **Why:** Stacking independent analyses is not integration and misses cross-modal interactions

- **Wrong:** Running Phase 3 after a Phase 2 that tested clinical benefit instead of biological mechanism
  **Right:** Use Phase 2 to test biology (PD biomarkers, imaging endpoints); reserve clinical benefit for Phase 3
  **Why:** The biological question was never answered, so a negative Phase 3 is uninterpretable

- **Wrong:** Declaring a target "validated" from a single GWAS + eQTL colocalization
  **Right:** Require convergence across ≥3 lines of evidence (GWAS, rare variant, eQTL, MR) or functional follow-up
  **Why:** Single-line genetic evidence has high false-positive rates due to LD and pleiotropy

- **Wrong:** Ignoring sex, ancestry, or age effects in preclinical and clinical design
  **Right:** Include both sexes, analyze stratified, and account for ancestry and age as biological variables
  **Why:** Pooling masks real biological differences and reduces generalizability of findings

- **Wrong:** Treating real-world evidence as a substitute for controlled inference when confounding by indication is severe
  **Right:** Use RWE for hypothesis generation or effectiveness; require controlled designs for causal claims
  **Why:** Confounding by indication in observational data can produce effect estimates in the wrong direction

---

## Evaluation Checklist (apply before closing any recommendation)

1. Current T-stage named.
2. Next T-gate stated as a falsifiable claim with a kill criterion.
3. For targets: convergence across ≥3 of {GWAS, rare variant, eQTL/colocalization, MR} — or an explicit justification for proceeding without it.
4. For biomarkers: population + decision + BEST category + which evidence level is next.
5. For preclinical plans: construct validity, free-compartment PK, independent replication, power.
6. For endpoints: biology-anchored in early phase, timescale matched to mechanism, target engagement planned before Phase 2.
7. For trial design: the "shared thing" matches basket/umbrella/platform choice; stratifiers named.
8. For multimodal analyses: top three confounders enumerated; missingness handled explicitly.
9. Failure modes from Section 8 checked and either absent or flagged.
10. The single weakest link is named, and the minimum experiment to address it is proposed.

## References

- FDA-NIH BEST Resource: https://www.ncbi.nlm.nih.gov/books/NBK338448/
- ARRIVE 2.0: Percie du Sert et al. PLoS Biol 2020, https://doi.org/10.1371/journal.pbio.3000410
- MR for drug target validation: Schmidt et al. Nat Commun 2020, https://doi.org/10.1038/s41467-020-16969-0
- Translational failure in neuroscience: Bhatt et al. Transl Med Commun 2019, https://doi.org/10.1186/s41231-019-0050-7
