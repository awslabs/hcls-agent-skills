---
name: rwd-cohort-analysis
description: Real-world data cohort analysis pipeline for claims and EHR data — cohort identification with ICD-10, NDC, and CPT codes, medication adherence metrics (PDC/MPR), propensity score estimation and balance diagnostics, Kaplan-Meier survival curves, and Cox proportional hazards models. Use when the user mentions claims data, cohort identification, ICD-10 codes, NDC codes, CPT codes, medication adherence, PDC, MPR, propensity score, SMD balance, Kaplan-Meier, Cox model, Schoenfeld residuals, survival analysis on claims, or real-world evidence pipeline.
usage: Invoke when building cohort analysis pipelines from claims or EHR data with adherence metrics, propensity scores, and survival analysis.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {lifelines: "0.28", statsmodels: "0.14", pandas: "2.2"}
tags: [skill, category:pipeline, real-world-data, claims, survival-analysis, propensity-score, cohort, hcls]
---

# Real-World Data Cohort Analysis Pipeline

## Overview

This skill encodes a reproducible pipeline for analyzing administrative claims
or EHR data to estimate comparative treatment effects. It covers the full
workflow from raw claims tables to adjusted survival estimates:

1. Cohort identification using diagnosis (ICD-10-CM), procedure (CPT/HCPCS),
   and drug (NDC) code lists
2. Medication adherence measurement (PDC and MPR)
3. Propensity score estimation and balance diagnostics
4. Kaplan-Meier curves and Cox proportional hazards regression

Code snippets use Python (pandas, scikit-learn, lifelines) and R
(MatchIt, cobalt, survival, survminer). The user is responsible for data
access, IRB/privacy compliance, and clinical code-list validation.

Out of scope: data extraction from source systems, natural language processing
of clinical notes, interrupted time series, instrumental variable analyses.

## Usage

Invoke when the user asks to:
- Build a cohort from claims or EHR data using diagnosis/procedure/drug codes
- Calculate PDC or MPR for medication adherence
- Estimate propensity scores and check covariate balance
- Run Kaplan-Meier or Cox regression on a claims-derived cohort
- Assess the proportional hazards assumption

The skill emits exact code. The user supplies the data and code lists.


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

### Data model assumptions

The pipeline expects these tables (column names are illustrative):

| Table | Key columns |
|---|---|
| `enrollment` | `patient_id`, `enroll_start`, `enroll_end` |
| `diagnoses` | `patient_id`, `dx_date`, `icd10_code`, `dx_position` |
| `procedures` | `patient_id`, `proc_date`, `cpt_code` |
| `pharmacy` | `patient_id`, `fill_date`, `ndc_code`, `days_supply`, `quantity` |
| `demographics` | `patient_id`, `birth_date`, `sex`, `race` |

### 1. Cohort Identification

#### Define code lists

```python
# ICD-10-CM codes for type 2 diabetes (example)
T2D_ICD10 = ["E11.0", "E11.1", "E11.2", "E11.3", "E11.4",
             "E11.5", "E11.6", "E11.8", "E11.9"]

# NDC codes for Drug A (user supplies actual NDCs)
DRUG_A_NDC = ["12345678901", "12345678902"]
DRUG_B_NDC = ["98765432101", "98765432102"]

# CPT codes for outcome procedure (e.g., amputation)
OUTCOME_CPT = ["27590", "27591", "27592"]
```

#### Identify new users with washout

```python
import pandas as pd

def identify_new_users(pharmacy, ndc_list, washout_days=180):
    """Identify incident users: first fill after washout with no prior fills."""
    drug_fills = pharmacy[pharmacy["ndc_code"].isin(ndc_list)].copy()
    drug_fills = drug_fills.sort_values(["patient_id", "fill_date"])

    # First-ever fill
    first_fill = drug_fills.groupby("patient_id")["fill_date"].min().reset_index()
    first_fill.columns = ["patient_id", "index_date"]

    # Require continuous enrollment for washout_days before index
    cohort = first_fill.merge(enrollment, on="patient_id")
    cohort["washout_start"] = cohort["index_date"] - pd.Timedelta(days=washout_days)
    cohort = cohort[cohort["enroll_start"] <= cohort["washout_start"]]

    # Exclude patients with any fill of the drug during washout
    cohort = cohort.merge(drug_fills, on="patient_id", suffixes=("", "_rx"))
    prior_fills = cohort[
        (cohort["fill_date"] >= cohort["washout_start"]) &
        (cohort["fill_date"] < cohort["index_date"])
    ]
    prevalent_users = prior_fills["patient_id"].unique()
    cohort = first_fill[~first_fill["patient_id"].isin(prevalent_users)]
    return cohort  # columns: patient_id, index_date
```

#### Apply inclusion/exclusion criteria

```python
def apply_criteria(cohort, diagnoses, enrollment, min_age=18,
                   required_dx_codes=None, excluded_dx_codes=None,
                   pre_index_window=365, min_followup=30):
    """Filter cohort by age, required/excluded diagnoses, enrollment."""
    # Age at index
    cohort = cohort.merge(demographics, on="patient_id")
    cohort["age"] = (cohort["index_date"] - cohort["birth_date"]).dt.days / 365.25
    cohort = cohort[cohort["age"] >= min_age]

    # Required diagnosis in pre-index window
    if required_dx_codes:
        pre_dx = diagnoses[diagnoses["icd10_code"].isin(required_dx_codes)]
        pre_dx = pre_dx.merge(cohort[["patient_id", "index_date"]], on="patient_id")
        pre_dx = pre_dx[
            (pre_dx["dx_date"] >= pre_dx["index_date"] - pd.Timedelta(days=pre_index_window)) &
            (pre_dx["dx_date"] < pre_dx["index_date"])
        ]
        cohort = cohort[cohort["patient_id"].isin(pre_dx["patient_id"].unique())]

    # Exclude patients with certain diagnoses
    if excluded_dx_codes:
        excl = diagnoses[diagnoses["icd10_code"].isin(excluded_dx_codes)]
        excl = excl.merge(cohort[["patient_id", "index_date"]], on="patient_id")
        excl = excl[excl["dx_date"] < excl["index_date"]]
        cohort = cohort[~cohort["patient_id"].isin(excl["patient_id"].unique())]

    # Minimum follow-up enrollment
    cohort = cohort.merge(enrollment, on="patient_id")
    cohort["followup_end"] = cohort[["enroll_end", cohort.columns[-1]]].min(axis=1)
    cohort = cohort[
        (cohort["enroll_end"] - cohort["index_date"]).dt.days >= min_followup
    ]
    return cohort
```

### 2. Medication Adherence

#### PDC (Proportion of Days Covered)

PDC is the preferred measure (endorsed by PQA). It counts the number of days
in the measurement period covered by at least one fill, capped at 1.0.

```python
def calculate_pdc(pharmacy, cohort, ndc_list, period_days=365):
    """Calculate PDC for each patient over a fixed measurement period."""
    fills = pharmacy[pharmacy["ndc_code"].isin(ndc_list)].copy()
    fills = fills.merge(cohort[["patient_id", "index_date"]], on="patient_id")
    fills["period_end"] = fills["index_date"] + pd.Timedelta(days=period_days)

    # Keep fills within measurement period
    fills = fills[fills["fill_date"] < fills["period_end"]]
    fills["cover_start"] = fills["fill_date"]
    fills["cover_end"] = fills["fill_date"] + pd.to_timedelta(fills["days_supply"], unit="D")
    fills["cover_end"] = fills[["cover_end", "period_end"]].min(axis=1)
    fills["cover_start"] = fills[["cover_start", "index_date"]].max(axis=1)

    # Build day-level coverage (vectorized per patient)
    results = []
    for pid, grp in fills.groupby("patient_id"):
        days_covered = set()
        for _, row in grp.iterrows():
            days_covered.update(pd.date_range(row["cover_start"], row["cover_end"] - pd.Timedelta(days=1)))
        results.append({"patient_id": pid, "pdc": min(len(days_covered) / period_days, 1.0)})
    return pd.DataFrame(results)
```

#### MPR (Medication Possession Ratio)

```python
def calculate_mpr(pharmacy, cohort, ndc_list, period_days=365):
    """MPR = total days supply dispensed / days in period. Can exceed 1.0."""
    fills = pharmacy[pharmacy["ndc_code"].isin(ndc_list)].copy()
    fills = fills.merge(cohort[["patient_id", "index_date"]], on="patient_id")
    fills["period_end"] = fills["index_date"] + pd.Timedelta(days=period_days)
    fills = fills[(fills["fill_date"] >= fills["index_date"]) &
                  (fills["fill_date"] < fills["period_end"])]
    mpr = fills.groupby("patient_id")["days_supply"].sum().reset_index()
    mpr.columns = ["patient_id", "total_supply"]
    mpr["mpr"] = mpr["total_supply"] / period_days
    return mpr
```

| Metric | Formula | Range | Notes |
|---|---|---|---|
| **PDC** | Days covered / days in period | 0–1.0 | Preferred; no double-counting overlapping fills |
| **MPR** | Total days supply / days in period | 0–∞ | Can exceed 1.0 with early refills; less preferred |

Adherence threshold: PDC ≥ 0.80 is the standard cutoff for "adherent."

### 3. Propensity Score Estimation

#### Python (scikit-learn)

```python
from sklearn.linear_model import LogisticRegression
import numpy as np

def estimate_ps(cohort, covariate_cols, treatment_col="treatment"):
    """Fit logistic regression PS model. Returns cohort with ps column."""
    X = cohort[covariate_cols].fillna(0)
    y = cohort[treatment_col]
    model = LogisticRegression(max_iter=1000, solver="lbfgs", C=1e6)
    model.fit(X, y)
    cohort = cohort.copy()
    cohort["ps"] = model.predict_proba(X)[:, 1]
    return cohort, model
```

#### R (MatchIt + cobalt)

```r
library(MatchIt)
library(cobalt)

# Estimate PS and perform 1:1 nearest-neighbor matching
m <- matchit(treatment ~ age + sex + charlson + prior_hosp + prior_rx_count,
             data = cohort, method = "nearest", distance = "glm",
             caliper = 0.2, ratio = 1)
matched_data <- match.data(m)

# Balance diagnostics
bal.tab(m, thresholds = c(m = 0.1))  # SMD threshold
love.plot(m, threshold = 0.1)
```

### 4. Balance Diagnostics

#### SMD calculation (Python)

```python
def compute_smd(cohort, covariate_cols, treatment_col="treatment"):
    """Compute standardized mean differences for all covariates."""
    treated = cohort[cohort[treatment_col] == 1]
    comparator = cohort[cohort[treatment_col] == 0]
    results = []
    for col in covariate_cols:
        mean_t = treated[col].mean()
        mean_c = comparator[col].mean()
        var_t = treated[col].var()
        var_c = comparator[col].var()
        pooled_sd = np.sqrt((var_t + var_c) / 2)
        smd = abs(mean_t - mean_c) / pooled_sd if pooled_sd > 0 else 0
        results.append({"covariate": col, "smd": round(smd, 4),
                        "balanced": smd < 0.1})
    return pd.DataFrame(results)
```

| Diagnostic | Target | Action if failed |
|---|---|---|
| SMD | < 0.1 for all covariates | Add interactions/non-linear terms to PS model |
| Variance ratio | 0.5–2.0 | Re-specify PS model or trim extremes |
| PS overlap | Substantial overlap in both groups | Trim non-overlapping regions; report trimmed N |
| Weight distribution (IPTW) | Mean ≈ 1.0; max < 10 | Truncate at 1st/99th percentile |

### 5. IPTW (Inverse Probability of Treatment Weighting)

```python
def compute_iptw(cohort, treatment_col="treatment", ps_col="ps",
                 stabilized=True, truncate_pct=(1, 99)):
    """Compute stabilized IPTW weights with truncation."""
    cohort = cohort.copy()
    t = cohort[treatment_col]
    ps = cohort[ps_col]

    if stabilized:
        p_treat = t.mean()
        cohort["iptw"] = np.where(t == 1, p_treat / ps, (1 - p_treat) / (1 - ps))
    else:
        cohort["iptw"] = np.where(t == 1, 1 / ps, 1 / (1 - ps))

    # Truncate extreme weights
    lo, hi = np.percentile(cohort["iptw"], truncate_pct)
    cohort["iptw"] = cohort["iptw"].clip(lo, hi)
    return cohort
```

### 6. Kaplan-Meier Survival Analysis

#### Python (lifelines)

```python
from lifelines import KaplanMeierFitter
import matplotlib.pyplot as plt

def plot_km(cohort, duration_col="followup_days", event_col="event",
            group_col="treatment", labels=("Drug B", "Drug A")):
    """Plot Kaplan-Meier curves by treatment group."""
    fig, ax = plt.subplots(figsize=(8, 6))
    kmf = KaplanMeierFitter()
    for grp, label in zip([0, 1], labels):
        mask = cohort[group_col] == grp
        kmf.fit(cohort.loc[mask, duration_col], cohort.loc[mask, event_col],
                label=label)
        kmf.plot_survival_function(ax=ax, ci_show=True)
    ax.set_xlabel("Days from index date")
    ax.set_ylabel("Survival probability")
    ax.set_title("Kaplan-Meier Survival Curves")
    plt.tight_layout()
    return fig
```

#### R (survival + survminer)

```r
library(survival)
library(survminer)

fit <- survfit(Surv(followup_days, event) ~ treatment, data = cohort)
ggsurvplot(fit, data = cohort, pval = TRUE, risk.table = TRUE,
           xlab = "Days from index date", ylab = "Survival probability",
           legend.labs = c("Drug B", "Drug A"))
```

### 7. Cox Proportional Hazards Model

#### Python (lifelines)

```python
from lifelines import CoxPHFitter

def fit_cox(cohort, duration_col="followup_days", event_col="event",
            covariates=None, weight_col=None):
    """Fit Cox PH model, optionally weighted (IPTW)."""
    cols = [duration_col, event_col] + (covariates or [])
    if weight_col:
        cols.append(weight_col)
    df = cohort[cols].dropna()
    cph = CoxPHFitter()
    cph.fit(df, duration_col=duration_col, event_col=event_col,
            weights_col=weight_col, robust=True if weight_col else False)
    cph.print_summary()
    return cph
```

#### R (survival)

```r
# Unweighted (matched cohort)
cox_fit <- coxph(Surv(followup_days, event) ~ treatment + age + sex + charlson,
                 data = matched_data)
summary(cox_fit)

# IPTW-weighted
cox_iptw <- coxph(Surv(followup_days, event) ~ treatment,
                  data = cohort, weights = iptw, robust = TRUE)
summary(cox_iptw)
```

### 8. Proportional Hazards Assumption Check

#### Schoenfeld residuals (Python)

```python
def check_ph_assumption(cph):
    """Test and plot Schoenfeld residuals for PH assumption."""
    cph.check_assumptions(cohort, p_value_threshold=0.05, show_plots=True)
```

#### R

```r
ph_test <- cox.zph(cox_fit)
print(ph_test)       # p < 0.05 → PH assumption violated for that covariate
plot(ph_test)         # visual: residuals should show no trend over time
```

| PH test result | Action |
|---|---|
| All p > 0.05 | PH assumption holds; proceed |
| Covariate p < 0.05 | Stratify on that covariate or add time-interaction term |
| Global p < 0.05 | Consider restricted mean survival time (RMST) or parametric AFT model |

### Pipeline summary

```
1. Define code lists (ICD-10, NDC, CPT)
2. Identify new users with washout          → cohort table
3. Apply inclusion/exclusion criteria       → filtered cohort
4. Build baseline covariate matrix          → pre-index features
5. Estimate propensity scores               → ps column
6. Match or weight (IPTW)                   → balanced cohort
7. Check balance (SMD < 0.1)               → Love plot / SMD table
8. Calculate adherence (PDC/MPR)            → adherence metrics
9. Define outcome + follow-up               → duration + event columns
10. Kaplan-Meier curves                     → survival plot
11. Cox PH model (adjusted or weighted)     → hazard ratios + CIs
12. Check PH assumption (Schoenfeld)        → assumption diagnostics
```

## Common Mistakes

- **Wrong:** Using MPR instead of PDC for medication adherence
  **Right:** Use PDC (Proportion of Days Covered) as the adherence metric
  **Why:** MPR double-counts overlapping fills, can exceed 1.0, and is not endorsed by PQA

- **Wrong:** Not requiring continuous enrollment during the study period
  **Right:** Verify continuous enrollment for both washout and follow-up windows
  **Why:** Gaps in enrollment create unobservable periods where events and fills are missed

- **Wrong:** Omitting a washout period before the index date
  **Right:** Require a clean washout (typically 180 days) with no prior fills of the study drug
  **Why:** Without washout, prevalent users contaminate the new-user cohort and bias results

- **Wrong:** Including post-index covariates in the propensity score model
  **Right:** Only use pre-index (baseline) variables in the PS model
  **Why:** Post-index variables may be affected by treatment, introducing collider bias

- **Wrong:** Using p-values to assess covariate balance after matching/weighting
  **Right:** Use standardized mean differences (SMD < 0.1) for all covariates
  **Why:** P-values conflate balance with sample size and are uninformative for this purpose

- **Wrong:** Not checking propensity score overlap between treatment groups
  **Right:** Plot PS distributions for both groups and trim non-overlapping regions
  **Why:** Estimates in non-overlapping regions are extrapolated and unreliable

- **Wrong:** Reporting Cox model results without testing the proportional hazards assumption
  **Right:** Always run Schoenfeld residual tests and inspect plots for time trends
  **Why:** Violated PH produces misleading hazard ratios; consider RMST or stratification instead

- **Wrong:** Using naive standard errors with IPTW-weighted analyses
  **Right:** Use robust (sandwich) variance estimators when fitting weighted models
  **Why:** Naive SEs underestimate uncertainty because they ignore the weight estimation step

- **Wrong:** Truncating IPTW weights too aggressively (e.g., at 5th/95th percentile)
  **Right:** Truncate conservatively (1st/99th) and report sensitivity across thresholds
  **Why:** Over-truncation reintroduces confounding by effectively unweighting key observations

- **Wrong:** Defining follow-up end as a fixed calendar date for all patients
  **Right:** End follow-up at the earliest of: event, disenrollment, end of study, or death
  **Why:** Incorrect censoring biases survival estimates and violates non-informative censoring assumptions

## References

- Hernán MA, Robins JM. Causal Inference: What If. Chapman & Hall/CRC 2020, https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/
- Austin PC. An introduction to propensity score methods. Multivariate Behav Res 2011, https://doi.org/10.1080/00273171.2011.568786
- Pharmacy Quality Alliance. PDC measure specifications, https://www.pqaalliance.org/
- Davidson-Pilon C. lifelines documentation, https://lifelines.readthedocs.io/
- Ho DE et al. MatchIt: nonparametric preprocessing for parametric causal inference. J Stat Softw 2011, https://doi.org/10.18637/jss.v042.i08
- Therneau TM, Grambsch PM. Modeling Survival Data. Springer 2000
