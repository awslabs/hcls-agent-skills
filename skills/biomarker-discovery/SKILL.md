---
name: biomarker-discovery
description: Reason about biomarker discovery and validation in HCLS — classifying biomarker intent, choosing feature-selection and cross-validation strategies, avoiding leakage, and planning external replication. Use when the user asks to discover, develop, or validate a biomarker; select features from high-dimensional omics or clinical data; design a validation study; choose evaluation metrics; justify sample size; combine multi-omics signals; or assess clinical utility. Triggers include "discover a biomarker", "validate biomarker", "prognostic vs predictive", "feature selection", "LASSO vs elastic net", "nested cross-validation", "data leakage", "C-index", "time-dependent AUC", "decision curve analysis", "external validation cohort", "events per variable", "optimism-corrected", "multi-omics integration", "clinical utility of a biomarker", "is this biomarker ready".
usage: Invoke when discovering, validating, or designing studies for biomarkers, or choosing feature-selection and cross-validation strategies.
version: 1.0.0
tags: [skill, category:reasoning, biomarker, feature-selection, validation, hcls]
---

# Biomarker Discovery and Validation

## Overview

This skill teaches the agent how to *think* about biomarker discovery and validation, not how to run a specific pipeline. A biomarker is only useful if three things line up: (1) the **intent** is clearly defined (prognostic, predictive, or diagnostic), (2) the **discovery statistics** are honest (no leakage, appropriate penalization, nested resampling), and (3) the **validation plan** reaches external replication and demonstrates a clinical decision change.

Use this skill to interrogate proposals, spot methodological weaknesses, and guide the user toward the right design *before* code is written.

## Usage

Invoke this skill when the user:

- Describes a candidate marker (gene, protein, imaging feature, EHR variable, composite score) and asks how to develop or validate it.
- Has a high-dimensional dataset (transcriptomics, proteomics, radiomics, methylation) and wants to select features.
- Asks which cross-validation scheme, metric, or sample size is appropriate.
- Claims a biomarker "works" based on a single AUC on a single cohort.
- Wants to combine multiple omics layers or modalities.
- Asks whether a biomarker is ready for clinical use or regulatory submission.

The agent should respond by:

1. **Clarifying intent** — force a prognostic/predictive/diagnostic classification before anything else.
2. **Auditing the data** — sample size, event counts, site structure, missingness, time origin.
3. **Recommending a design** — feature selection, resampling, metrics, validation tier.
4. **Naming the leakage risks** specific to the user's setup.
5. **Stating what "validated" would mean** for this biomarker in this context.

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

### 1. Biomarker Intent Determines Everything

The first question is always: *what decision is this biomarker supposed to inform?*

| Intent | Question answered | Minimal design | Key estimand |
|---|---|---|---|
| **Prognostic** | What is this patient's outcome regardless of treatment? | Single-arm / observational cohort with outcome follow-up | Hazard ratio, C-index, calibration |
| **Predictive** | Who benefits more from treatment A vs B? | RCT or well-emulated target trial with both arms | Treatment × biomarker interaction |
| **Diagnostic** | Does this patient have the disease now? | Case–control with full disease spectrum | Sensitivity, specificity, PPV/NPV |

Consequences of the classification:

- A **prognostic** claim cannot be made from a predictive design without a single-arm reference, and a **predictive** claim cannot be made from a single-arm cohort — there is no counterfactual arm.
- A **diagnostic** biomarker evaluated only in clear cases vs healthy controls will overstate performance; it must be tested across the clinical *spectrum* it will be used in (mild, early, comorbid, mimics).
- Confusing prognostic with predictive is the single most common error in oncology biomarker papers. If the user claims "patients with high X did better on drug Y," ask whether the same is true on the control arm — if yes, it is prognostic, not predictive.

### 2. Feature Selection Strategy

Pick based on the *shape* of the problem, not familiarity.

| Method | Strength | When it fails |
|---|---|---|
| **LASSO (L1)** | Sparse solutions, interpretable, fast | Picks one arbitrary feature from correlated groups |
| **Elastic net (L1 + L2)** | Handles correlated features, groups them | Two hyperparameters to tune |
| **Random (survival) forest importance** | Captures non-linearities and interactions | Biased toward high-cardinality features; importance ≠ causation |
| **Stability selection** | Reports features selected in >60% of subsamples; controls false discoveries | Computationally heavier; needs a base selector (usually LASSO) |
| **Univariate filtering** | Simple | Ignores multivariate structure; almost always wrong as a sole method in high-d |

#### Decision tree: which feature selection method?

```
Start
│
├── Is n < p (more features than samples)?
│     ├── Yes → Use penalization (LASSO / elastic net) OR stability selection.
│     │         Never rely on univariate filtering alone.
│     └── No  → Continue.
│
├── Are features strongly correlated (e.g., gene modules, radiomic clusters)?
│     ├── Yes → Elastic net (groups correlated features) or
│     │         group LASSO if groupings are known a priori.
│     └── No  → LASSO is fine.
│
├── Do you suspect non-linear effects or interactions?
│     ├── Yes → Random forest / gradient-boosted trees for importance,
│     │         confirm with permutation importance (not impurity-based).
│     └── No  → Stay with linear penalized models.
│
└── Need reproducibility / publication-grade selection?
      └── Wrap whatever base method above in stability selection
          (subsample → refit → keep features chosen in ≥60% of runs).
```

### 3. Nested Cross-Validation is Non-Negotiable

Biomarker discovery must use **nested CV**:

- **Outer loop** — estimates generalization performance on held-out folds.
- **Inner loop** — performs feature selection *and* hyperparameter tuning on training folds only.

Rules:

- **Patient-level splits.** Never split rows when a patient contributes multiple samples (longitudinal labs, multiple lesions, bilateral imaging). Leakage across folds via shared patients is the most common silent inflator of performance.
- **Stratify by outcome** (and by site/batch when feasible).
- **Everything learned from data goes inside the inner loop:** feature selection, imputation parameters, normalization statistics, scaler means/SDs, batch-correction fits, PCA loadings.
- Report the **distribution across outer folds**, not just the mean — high variance across folds is a warning sign.

### 4. Data Leakage — The Usual Suspects

Leakage invalidates everything downstream. Check for:

1. **Feature selection on the full dataset before CV.** The selected features already "know" the test labels. Always select inside the CV loop.
2. **Temporal leakage.** A lab is ordered *because* clinicians already suspect the outcome. The feature's presence/absence itself encodes the label. Define a clean **time origin** (e.g., admission, diagnosis, randomization) and only use data available before it.
3. **Outcome-in-features.** Variables that are definitionally downstream of the outcome (e.g., "received hospice" predicting death; "tumor stage IV" predicting metastasis) are circular.
4. **Preprocessing leakage.** Computing normalization means, imputation medians, scaler statistics, or PCA on the full dataset leaks test distribution into training. Fit on training folds only, apply to test.
5. **Batch/site leakage.** If all cases come from Site A and all controls from Site B, the model learns site, not biology.
6. **Target leakage via proxies.** Encounter ID, physician ID, or order timestamps can proxy outcome.

### 5. Evaluation Metrics by Intent

Choosing the wrong metric hides or inflates effects.

- **Prognostic (time-to-event):**
  - C-index (Harrell's or Uno's for censoring).
  - Time-dependent AUC at clinically relevant horizons (e.g., 1, 3, 5 years).
  - Calibration (calibration-in-the-large, calibration slope, calibration plots). Discrimination without calibration is insufficient.
- **Predictive:**
  - Treatment × biomarker **interaction** term (p-value and effect size).
  - Subgroup-specific hazard ratios or risk differences — both point estimates and CIs.
  - Qualitative interaction (benefit flips direction) is stronger evidence than quantitative interaction (benefit magnitude differs).
- **Diagnostic:**
  - Sensitivity and specificity at the *pre-specified* clinical threshold, not the one that maximizes Youden's J on the test set.
  - AUROC as a summary; AUPRC when prevalence is low and positive class is the focus.
  - PPV and NPV — **these are prevalence-dependent**. Report the prevalence assumed and re-estimate PPV/NPV at the deployment prevalence.

Always report **confidence intervals** (bootstrap or analytic) alongside point estimates.

### 6. Validation Hierarchy

A biomarker graduates through tiers. Do not skip.

1. **Internal validation** — nested CV or bootstrap on the discovery cohort. Optimism-corrected.
2. **Internal-external** — leave-one-site-out or leave-one-batch-out within the discovery dataset. Probes site/batch robustness.
3. **External validation** — independent cohort, ideally collected by a different group, with pre-specified model and threshold (locked).
4. **Prospective validation** — biomarker used in real time with outcomes assessed after. Required for most regulatory submissions.

A biomarker is **not validated** until step 3 at minimum, and the model + threshold were locked before seeing the external data. Re-tuning on external data = discovery, not validation.

#### Decision tree: which validation tier applies?

```
Start
│
├── Only one cohort available?
│     └── Internal validation only (nested CV + bootstrap optimism correction).
│         Label result as "discovery", not "validated".
│
├── Multi-site data within a single study?
│     └── Add internal-external (leave-one-site-out).
│         Report performance per site, not just pooled.
│
├── Truly independent cohort available?
│     └── Lock model + threshold → evaluate once → report with CIs.
│         Pre-register the analysis plan if possible.
│
└── Intended for clinical deployment / regulatory submission?
      └── Prospective validation on the target population,
          under intended-use conditions, with the locked model.
```

### 7. Sample Size and Events-Per-Variable

For Cox and logistic models: aim for **10–20 events per candidate variable** considered during modeling (not just the final set). Counting only the selected variables after LASSO is a mistake — the selection itself used the full candidate pool.

In high-dimensional settings (omics, radiomics) events-per-variable is unattainable. Compensate with:

- Penalization (LASSO/elastic net) or Bayesian shrinkage priors.
- **Stability selection** to control false-discovery rate of selected features.
- **Optimism-corrected performance** via bootstrap (.632+ or Harrell's bootstrap optimism correction).
- Pre-specification of the number of features carried forward.

Event counts, not sample size, are the binding constraint for time-to-event outcomes. 1000 patients with 30 events ≈ a 30-event study.

### 8. Multi-Omics Integration

When combining transcriptomics + proteomics + imaging + clinical:

- **Early integration** (concatenate all features, fit one model): high-dimensional, sensitive to scale differences and missing modalities. Works only with very large n.
- **Intermediate integration** (MOFA, canonical correlation, kernel methods, shared latent factors): good when you want to find *shared* biology across layers. Moderate n.
- **Late integration** (fit one model per omic, combine predictions via stacking or simple averaging): most robust when n is small, tolerates missing modalities per patient, and is easiest to validate modality-by-modality.

Default with small-to-moderate sample sizes: **late integration**. Escalate to intermediate or early only if n supports it and shared-factor interpretation is a goal.

Missing modalities are the norm, not the exception — design for it from the start.

### 9. Clinical Utility — The Decision Test

A biomarker with excellent AUC that does not change any decision is not useful. For every candidate, the agent should force the user to answer:

- **What decision does this biomarker change?** (treat vs not, escalate vs de-escalate, biopsy vs observe, enroll vs exclude.)
- **At what threshold?** Thresholds must be pre-specified and tied to the decision's costs and benefits.
- **What is the net benefit** over treat-all and treat-none, across the plausible threshold range? Use **decision curve analysis**.
- **Who is harmed** by a false positive or false negative, and at what rate is that acceptable?

If the user cannot answer these, clinical utility is undefined — regardless of AUC.

## When NOT to Use This Skill
- Established validated biomarkers already in clinical guidelines (e.g., HER2, BRCA1/2) — use guideline-concordant testing protocols instead
- Clinical deployment or CLIA/CAP lab validation decisions — those require regulatory and laboratory expertise, not discovery methodology
- Companion diagnostic development — that is a regulatory/manufacturing problem, not a biomarker discovery problem

## When to Escalate to Human Expert
- The biomarker will be used for treatment selection in a clinical trial — requires biostatistician sign-off on the adaptive design
- Analytical validation (sensitivity, specificity, reproducibility across platforms) is needed — requires wet-lab expertise
- Ethical review is needed for biomarker-driven patient stratification that could deny treatment to a subgroup

## Common Mistakes

- **Wrong:** Claiming a biomarker is "predictive" from a single-arm study
  **Right:** Require a comparator arm (RCT or emulated target trial) to estimate a treatment-by-biomarker interaction
  **Why:** Without a counterfactual arm, you cannot distinguish prognostic from predictive — the biomarker may simply mark prognosis regardless of treatment

- **Wrong:** Performing feature selection on the full dataset, then running CV on the reduced feature set
  **Right:** Always perform feature selection inside the CV inner loop so each fold selects features independently
  **Why:** Selected features already "know" the test labels, inflating performance estimates and producing unreproducible models

- **Wrong:** Splitting by row when a patient contributes multiple samples
  **Right:** Split at the patient level so all samples from one patient stay in the same fold
  **Why:** Repeated measures, bilateral lesions, and longitudinal labs leak patient identity across folds, inflating apparent performance

- **Wrong:** Tuning the decision threshold on the test set
  **Right:** Lock thresholds on training data or pre-specify them based on clinical cost-benefit reasoning
  **Why:** Optimizing the threshold on test data overfits to the evaluation set and produces unreliable operating characteristics

- **Wrong:** Reporting PPV/NPV from a 50/50 case-control sample and implying it generalizes
  **Right:** Re-estimate PPV and NPV at the deployment prevalence using Bayes' theorem
  **Why:** PPV and NPV are prevalence-dependent — values from enriched samples are misleading at real-world disease rates

- **Wrong:** Ignoring calibration when reporting model performance
  **Right:** Always report calibration (calibration-in-the-large, calibration slope, calibration plots) alongside discrimination
  **Why:** Good discrimination with poor calibration produces clinically dangerous probability estimates that misinform decisions

- **Wrong:** Counting events-per-variable only after feature selection
  **Right:** Count EPV against all candidate variables considered during modeling, not just the final selected set
  **Why:** The selection process itself used the full candidate pool — the effective degrees of freedom reflect the original dimensionality

- **Wrong:** Declaring a biomarker "validated" based on cross-validation on the discovery cohort
  **Right:** Require external replication on an independent cohort with a locked model and pre-specified threshold
  **Why:** Cross-validation is internal validation only — it estimates optimism but does not prove generalizability

- **Wrong:** Confounding the biomarker signal with site, batch, platform, or scanner effects
  **Right:** Always check whether site/batch predicts outcome as well as the biomarker does; include site as a covariate or use leave-one-site-out validation
  **Why:** If all cases come from one site and controls from another, the model learns site identity, not biology

- **Wrong:** Using future information as a feature (e.g., a lab ordered because of clinical suspicion)
  **Right:** Define a clean time origin and only use data available before it
  **Why:** A lab ordered because of suspicion encodes the suspicion itself — this is temporal leakage, not predictive signal

- **Wrong:** Early integration of multi-omics with small sample sizes
  **Right:** Use late integration (fit one model per omic, combine predictions via stacking) when n is small to moderate
  **Why:** Concatenating thousands of features across layers with a few hundred patients overfits to batch effects, not biology

- **Wrong:** Reporting only point estimates without confidence intervals
  **Right:** Always include bootstrap or analytic confidence intervals for all performance metrics
  **Why:** Single numbers hide instability — a C-index of 0.78 with a 95% CI of [0.55, 0.92] tells a very different story

- **Wrong:** Optimizing AUC while ignoring clinical utility
  **Right:** Perform decision curve analysis to demonstrate net benefit over treat-all and treat-none strategies
  **Why:** A 0.85 AUC that changes no clinical decision is worse than a 0.70 AUC that reliably changes one

- **Wrong:** Retraining or tuning the model on external validation data "just a little"
  **Right:** Lock the model completely before seeing external data — any tuning collapses validation back into discovery
  **Why:** Even minor adjustments on external data eliminate its independence, making the "validation" circular

- **Wrong:** Skipping decision curve analysis when reporting biomarker performance
  **Right:** Always include net-benefit curves across the plausible threshold range
  **Why:** Without net-benefit reasoning, there is no evidence the biomarker helps patients — only that it correlates with outcome

## References

- Steyerberg EW. Clinical Prediction Models. Springer 2019
- Vickers AJ et al. Decision curve analysis. Med Decis Making 2006, https://doi.org/10.1177/0272989X06295361
- Meinshausen & Bühlmann. Stability selection. JRSS-B 2010, https://doi.org/10.1111/j.1467-9868.2010.00740.x
- Harrell FE. Regression Modeling Strategies. Springer 2015
- Simon RM et al. J Natl Cancer Inst 2009, https://doi.org/10.1093/jnci/djp335
