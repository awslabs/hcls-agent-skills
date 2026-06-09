---
name: pa-decision-automation
description: >
  Pipeline skill for automating prior authorization decision workflows. Use when the user asks to
  parse PA request data (X12 278 or FHIR PAS bundles), extract clinical features for adjudication,
  build rules-based PA decision engines, train ML classifiers on historical PA decisions, analyze
  denial patterns, or generate SHAP explanations for PA outcomes. Triggers include "parse 278",
  "FHIR PAS bundle", "PA automation", "adjudication logic", "PA classifier", "denial analysis",
  "prior auth ML", "SHAP explainability", "PA feature extraction", "rules engine PA",
  "PA decision pipeline", "authorization workflow", "clinical criteria extraction",
  "denial pattern mining", "PA turnaround time".
usage: Use when building or running prior authorization automation pipelines including parsing, classification, and denial analysis.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {fhir-resources: "R4", scikit-learn: "1.4"}
tags: [skill, category:pipeline, prior-authorization, automation, hcls]
---

# Prior Authorization Decision Automation Pipeline

## Overview

Provide deterministic code snippets and pipeline recipes for automating prior authorization
(PA) workflows: parsing inbound requests, extracting clinical features, applying rules-based
adjudication, training ML classifiers, and analyzing denial patterns.

## Usage

- Building or debugging X12 278 or FHIR PAS bundle parsers for PA intake
- Training ML classifiers on historical PA decisions or generating SHAP explanations
- Analyzing denial patterns to identify systemic documentation or policy gaps

## Core Concepts

### Automation Approach Selection

| Condition | Approach | Rationale |
|-----------|----------|-----------|
| Clear-cut policy rules (step therapy, age, lab threshold) | Rules engine | Auditable, deterministic, regulatory-safe |
| Ambiguous cases with soft criteria | ML classifier + SHAP | Handles nuance; SHAP provides explainability |
| < 1000 historical decisions available | Rules engine only | Insufficient data for reliable ML training |
| Multi-payer deployment | Separate model per payer | Policies differ; cross-payer models fail |
| Input is X12 278 (EDI) | `parse_278()` → segment iteration | Pipe-delimited, segment-based |
| Input is FHIR PAS Bundle | `parse_pas_bundle()` → resource extraction | JSON, resource-typed entries |

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## 1. PA Request Parsing

### 1.1 Parse X12 278 Transaction

The X12 278 Health Care Services Review transaction carries PA requests and responses.

```python
"""Parse X12 278 prior authorization request into structured dict."""
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PA278Request:
    member_id: str = ""
    provider_npi: str = ""
    diagnosis_codes: list[str] = field(default_factory=list)
    procedure_codes: list[str] = field(default_factory=list)
    service_date: str = ""
    quantity: int = 0
    place_of_service: str = ""


def parse_278(raw: str) -> PA278Request:
    """Parse X12 278 segments into a PA278Request."""
    req = PA278Request()
    segments = raw.replace("\n", "").split("~")
    for seg in segments:
        elements = seg.strip().split("*")
        seg_id = elements[0] if elements else ""
        if seg_id == "NM1" and len(elements) > 9:
            qualifier = elements[1]
            if qualifier == "IL":  # insured/member
                req.member_id = elements[9] if len(elements) > 9 else ""
            elif qualifier == "1P":  # provider
                req.provider_npi = elements[9] if len(elements) > 9 else ""
        elif seg_id == "HI":
            for el in elements[1:]:
                parts = el.split(":")
                if len(parts) >= 2:
                    code_qualifier, code = parts[0], parts[1]
                    if code_qualifier in ("ABK", "ABF"):  # ICD-10
                        req.diagnosis_codes.append(code)
        elif seg_id == "SV1" and len(elements) > 1:
            svc_parts = elements[1].split(":")
            if len(svc_parts) >= 2:
                req.procedure_codes.append(svc_parts[1])
        elif seg_id == "DTP" and len(elements) > 3:
            if elements[1] == "472":  # service date
                req.service_date = elements[3]
    return req
```

### 1.2 Parse FHIR Da Vinci PAS Bundle

```python
"""Extract PA fields from a FHIR Da Vinci PAS Bundle."""
import json
from dataclasses import dataclass, field


@dataclass
class PASRequest:
    member_id: str = ""
    provider_npi: str = ""
    diagnosis_codes: list[str] = field(default_factory=list)
    service_codes: list[str] = field(default_factory=list)
    supporting_info_types: list[str] = field(default_factory=list)


def parse_pas_bundle(bundle: dict) -> PASRequest:
    """Extract PA data from a FHIR PAS transaction Bundle."""
    req = PASRequest()
    resources = {
        entry["resource"]["resourceType"]: entry["resource"]
        for entry in bundle.get("entry", [])
        if "resource" in entry
    }
    # Patient / member
    patient = resources.get("Patient", {})
    for ident in patient.get("identifier", []):
        if ident.get("type", {}).get("coding", [{}])[0].get("code") == "MB":
            req.member_id = ident.get("value", "")
            break
    # Practitioner / provider NPI
    practitioner = resources.get("Practitioner", {})
    for ident in practitioner.get("identifier", []):
        if ident.get("system", "").endswith("/npi"):
            req.provider_npi = ident.get("value", "")
            break
    # Claim resource — core of the PA request
    claim = resources.get("Claim", {})
    for dx in claim.get("diagnosis", []):
        coding = dx.get("diagnosisCodeableConcept", {}).get("coding", [])
        for c in coding:
            req.diagnosis_codes.append(c.get("code", ""))
    for item in claim.get("item", []):
        svc_coding = item.get("productOrService", {}).get("coding", [])
        for c in svc_coding:
            req.service_codes.append(c.get("code", ""))
    for info in claim.get("supportingInfo", []):
        cat_coding = info.get("category", {}).get("coding", [])
        for c in cat_coding:
            req.supporting_info_types.append(c.get("code", ""))
    return req
```

## 2. Clinical Feature Extraction

### 2.1 Feature Set for PA Adjudication

| Feature | Source | Type | Description |
|---------|--------|------|-------------|
| `dx_specificity` | Diagnosis codes | int | ICD-10 code length (3=category, 4-7=specific) |
| `drug_class` | Service code (NDC/HCPCS) | categorical | Therapeutic class (e.g., biologic, opioid) |
| `prior_treatment_count` | Claims history | int | Number of prior drugs tried in same class |
| `step_therapy_complete` | Claims + formulary | bool | All required prior steps documented |
| `days_since_last_treatment` | Claims history | int | Gap since last related treatment |
| `lab_value_in_range` | Lab results | bool | Key lab (e.g., HbA1c) meets threshold |
| `provider_specialty` | Provider data | categorical | Specialty of ordering provider |
| `place_of_service` | Claim | categorical | Office, outpatient, inpatient, home |
| `prior_pa_denials` | PA history | int | Count of prior denials for same service |
| `documentation_score` | Supporting info | float | Completeness score (0-1) based on required docs |

### 2.2 Feature Extraction Code

```python
"""Extract clinical features from parsed PA request + claims history."""
import pandas as pd
from datetime import datetime


def extract_features(
    pa_request: dict,
    claims_history: pd.DataFrame,
    formulary: pd.DataFrame,
    lab_results: pd.DataFrame,
) -> dict:
    """Build feature vector for PA adjudication model.

    Args:
        pa_request: Parsed PA request (from parse_278 or parse_pas_bundle).
        claims_history: Member's prior claims with columns:
            [member_id, service_date, drug_class, ndc, diagnosis_code].
        formulary: Formulary table with columns:
            [ndc, tier, step_therapy_required, prior_drugs_required].
        lab_results: Lab results with columns:
            [member_id, test_code, result_value, result_date].
    """
    member_id = pa_request.get("member_id", "")
    dx_codes = pa_request.get("diagnosis_codes", [])
    svc_codes = pa_request.get("service_codes", [])

    # Diagnosis specificity: max ICD-10 code length
    dx_specificity = max((len(c.replace(".", "")) for c in dx_codes), default=3)

    # Prior treatment count in same drug class
    requested_drug = svc_codes[0] if svc_codes else ""
    drug_info = formulary[formulary["ndc"] == requested_drug]
    drug_class = drug_info["drug_class"].iloc[0] if len(drug_info) > 0 else "unknown"
    member_claims = claims_history[claims_history["member_id"] == member_id]
    prior_treatments = member_claims[member_claims["drug_class"] == drug_class]
    prior_treatment_count = prior_treatments["ndc"].nunique()

    # Step therapy completion
    required_steps = int(drug_info["prior_drugs_required"].iloc[0]) if len(drug_info) > 0 else 0
    step_therapy_complete = prior_treatment_count >= required_steps

    # Days since last treatment in class
    if len(prior_treatments) > 0:
        last_date = pd.to_datetime(prior_treatments["service_date"]).max()
        days_since = (datetime.now() - last_date).days
    else:
        days_since = -1  # no prior treatment

    # Lab value check (example: HbA1c for diabetes drugs)
    member_labs = lab_results[lab_results["member_id"] == member_id]
    recent_lab = member_labs.sort_values("result_date", ascending=False).head(1)
    lab_in_range = bool(recent_lab["result_value"].iloc[0] >= 7.0) if len(recent_lab) > 0 else False

    # Documentation completeness score
    supporting_info = pa_request.get("supporting_info_types", [])
    required_docs = {"clinical-note", "lab-result", "treatment-history", "diagnosis"}
    doc_score = len(set(supporting_info) & required_docs) / len(required_docs)

    return {
        "dx_specificity": dx_specificity,
        "drug_class": drug_class,
        "prior_treatment_count": prior_treatment_count,
        "step_therapy_complete": step_therapy_complete,
        "days_since_last_treatment": days_since,
        "lab_value_in_range": lab_in_range,
        "documentation_score": doc_score,
    }
```

## 3. Rules-Based Adjudication Engine

```python
"""Rules-based PA adjudication engine."""
from dataclasses import dataclass
from enum import Enum


class Decision(Enum):
    APPROVE = "approve"
    DENY = "deny"
    PEND = "pend"


@dataclass
class AdjudicationResult:
    decision: Decision
    reason_code: str
    reason_text: str


def adjudicate(features: dict, policy: dict) -> AdjudicationResult:
    """Apply rules-based adjudication logic.

    Args:
        features: Feature dict from extract_features().
        policy: Policy config with keys:
            - require_step_therapy (bool)
            - min_dx_specificity (int)
            - min_documentation_score (float)
            - require_lab_in_range (bool)
    """
    # Rule 1: Documentation completeness
    if features["documentation_score"] < policy.get("min_documentation_score", 0.75):
        return AdjudicationResult(
            Decision.PEND, "PEND-001", "Insufficient documentation; request additional clinical records"
        )
    # Rule 2: Diagnosis specificity
    if features["dx_specificity"] < policy.get("min_dx_specificity", 4):
        return AdjudicationResult(
            Decision.DENY, "DENY-DX", "Diagnosis code lacks required specificity"
        )
    # Rule 3: Step therapy
    if policy.get("require_step_therapy", True) and not features["step_therapy_complete"]:
        return AdjudicationResult(
            Decision.DENY, "DENY-STEP", "Step therapy requirements not met"
        )
    # Rule 4: Lab value threshold
    if policy.get("require_lab_in_range", False) and not features["lab_value_in_range"]:
        return AdjudicationResult(
            Decision.DENY, "DENY-LAB", "Required lab value not within criteria range"
        )
    # All rules passed
    return AdjudicationResult(Decision.APPROVE, "APPROVE-001", "All clinical criteria met")
```

## 4. ML Classifier for PA Decisions

### 4.1 Training Pipeline

```python
"""Train a gradient-boosted classifier on historical PA decisions."""
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb


def train_pa_classifier(
    data: pd.DataFrame, target_col: str = "decision",
    feature_cols: list[str] | None = None, n_folds: int = 5,
) -> tuple[xgb.XGBClassifier, pd.DataFrame]:
    """Train XGBoost on historical PA decisions (1=approved, 0=denied)."""
    if feature_cols is None:
        feature_cols = [c for c in data.columns if c != target_col]
    X, y = data[feature_cols].copy(), data[target_col].copy()
    cat_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
    X[cat_cols] = X[cat_cols].astype("category")
    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, enable_categorical=True,
        eval_metric="logloss", random_state=42,
    )
    cv_results = []
    for fold, (ti, vi) in enumerate(StratifiedKFold(n_folds, shuffle=True, random_state=42).split(X, y)):
        model.fit(X.iloc[ti], y.iloc[ti], eval_set=[(X.iloc[vi], y.iloc[vi])], verbose=False)
        y_prob = model.predict_proba(X.iloc[vi])[:, 1]
        cv_results.append({"fold": fold, "auc": roc_auc_score(y.iloc[vi], y_prob)})
    model.fit(X, y, verbose=False)
    return model, pd.DataFrame(cv_results)
```

### 4.2 SHAP Explainability

```python
"""Generate SHAP explanations for PA decisions."""
import shap


def explain_pa_decision(model, X, instance_idx: int = 0) -> dict:
    """Generate SHAP values for a single PA decision."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    explanation = dict(sorted(
        zip(X.columns, shap_values[instance_idx]),
        key=lambda x: abs(x[1]), reverse=True,
    ))
    return {
        "base_value": float(explainer.expected_value),
        "prediction": float(model.predict_proba(X.iloc[[instance_idx]])[:, 1][0]),
        "feature_contributions": explanation,
    }
```

## 5. Denial Reason Analysis

### 5.1 Denial Pattern Analysis

```python
"""Analyze PA denial patterns to identify systemic issues."""
import pandas as pd


def analyze_denials(pa_decisions: pd.DataFrame, group_cols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """Analyze denial patterns across dimensions.

    Args:
        pa_decisions: DataFrame [pa_id, member_id, provider_npi, drug_class, denial_reason, decision, decision_date].
        group_cols: Columns to group by. Defaults to [denial_reason, drug_class, provider_npi].
    """
    denied = pa_decisions[pa_decisions["decision"] == "denied"].copy()
    if group_cols is None:
        group_cols = ["denial_reason", "drug_class", "provider_npi"]
    analyses = {}
    for col in group_cols:
        if col not in denied.columns:
            continue
        g = denied.groupby(col).agg(denial_count=("pa_id", "count"), unique_members=("member_id", "nunique")).sort_values("denial_count", ascending=False).reset_index()
        g["pct_of_denials"] = (g["denial_count"] / len(denied) * 100).round(1)
        analyses[col] = g
    if "denial_reason" in denied.columns:
        doc_gaps = denied[denied["denial_reason"].str.contains("documentation|insufficient", case=False, na=False)]
        analyses["documentation_gaps"] = doc_gaps.groupby("drug_class").agg(gap_count=("pa_id", "count")).sort_values("gap_count", ascending=False).reset_index()
    return analyses
```

### 5.2 Denial Reason Code Reference

| Reason Code | Description | Remediation |
|-------------|-------------|-------------|
| DENY-STEP | Step therapy not completed | Document prior treatments with dates |
| DENY-DX | Non-specific diagnosis | Use highest-specificity ICD-10 code |
| DENY-LAB | Lab criteria not met | Resubmit with current lab results |
| DENY-MN | Medical necessity not established | Submit letter of medical necessity |
| DENY-EXP | Experimental/investigational | Cite peer-reviewed evidence |
| PEND-001 | Incomplete documentation | Submit clinical notes, labs, history |

## 6. Parameter Reference

### 6.1 XGBoost Hyperparameters for PA Classification

| Parameter | Default | Range |
|-----------|---------|-------|
| `n_estimators` | 300 | 100–1000 |
| `max_depth` | 6 | 3–10 |
| `learning_rate` | 0.05 | 0.01–0.3 |
| `subsample` | 0.8 | 0.5–1.0 |
| `colsample_bytree` | 0.8 | 0.5–1.0 |
| `scale_pos_weight` | 1.0 | Set to neg/pos ratio for imbalanced data |

### 6.2 Documentation Completeness Scoring

| Document Type | Weight | Required For |
|---------------|--------|-------------|
| Clinical notes | 0.30 | All PA requests |
| Lab results | 0.25 | Drug PAs with lab criteria |
| Treatment history | 0.25 | Step therapy drugs |
| Diagnosis confirmation | 0.10 | All PA requests |
| Specialist referral | 0.10 | Specialty drugs |

## 7. Common Mistakes

- **Wrong:** Training a PA classifier on imbalanced data without correction
  **Right:** Set `scale_pos_weight` to the neg/pos ratio, or apply SMOTE to balance the training set
  **Why:** PA datasets are often 70–80% approvals; without correction, the model learns to approve everything

- **Wrong:** Including features derived from information not available at the time of the PA request
  **Right:** Ensure all features use only data available before or at the moment of submission (claims history, not future outcomes)
  **Why:** Leaking future data inflates model performance in training but fails completely in production

- **Wrong:** Deploying a model trained on one payer's decisions to adjudicate another payer's requests
  **Right:** Train and validate separate models per payer, or include payer identity as a feature with sufficient per-payer training data
  **Why:** Each payer has independent clinical policies; a model trained on Payer A's criteria will make wrong decisions for Payer B

- **Wrong:** Accepting SHAP explanations at face value without clinical validation
  **Right:** Verify that top SHAP features align with known clinical criteria from the payer's published policy
  **Why:** Spurious correlations in training data can produce plausible-looking but clinically meaningless explanations

- **Wrong:** Hardcoding denial reason strings with free-text matching
  **Right:** Use standardized reason codes (CARC/RARC) and map them to structured enums
  **Why:** Free-text matching is brittle — minor wording changes break the logic and cause silent failures

- **Wrong:** Replacing the rules engine entirely with an ML classifier
  **Right:** Use ML to augment deterministic policy rules; route clear-cut cases through rules and ambiguous cases through ML
  **Why:** Auditable, explainable decisions require deterministic rules for regulatory compliance; ML alone is not audit-defensible
