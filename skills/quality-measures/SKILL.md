---
name: quality-measures
description: >
  Pipeline skill for computing HEDIS quality measures from claims and clinical data. Use when the
  user asks to calculate HEDIS measure rates, check continuous enrollment, build denominator/numerator
  logic, detect care gaps, compute utilization rates, identify high-cost claimants, or score risk
  stratification indices. Triggers include "calculate HEDIS", "measure rate", "continuous enrollment
  check", "care gap detection", "denominator query", "numerator logic", "utilization rate",
  "high-cost claimant", "Charlson score", "LACE score", "claims analysis", "quality measure SQL".
usage: Use when building or running quality measure calculation pipelines including enrollment checks, measure rates, and care gap detection.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {pandas: "2.2", sqlalchemy: "2.0"}
tags: [skill, category:pipeline, quality-measures, hedis, hcls]
---

# Quality Measures Calculation Pipeline

## Overview

Provide deterministic Python and SQL code snippets for calculating HEDIS quality measures,
detecting care gaps, computing utilization rates, identifying high-cost claimants, and
scoring risk stratification indices from claims and clinical data.

## Usage

- Calculate HEDIS measure rates, check continuous enrollment, detect care gaps, and score risk indices

## Core Concepts

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Approach Selection

| Scenario | Approach | Key consideration |
|----------|----------|-------------------|
| Single measure, ad-hoc | Python `calculate_measure()` | Fast iteration, easy debugging |
| Enterprise batch (all measures) | SQL CTEs per measure | Scales to millions of members |
| Data source: claims only | Use procedure/revenue codes for numerator | No clinical data available |
| Data source: claims + EHR | Supplement with lab values, vitals | Higher capture rate |
| Enrollment check: single payer | `max_gap_days=45` (HEDIS default) | One enrollment table |
| Enrollment check: multi-payer | Merge enrollment spans first, then check | Avoid double-counting gaps |

## 1. Continuous Enrollment Check

### 1.1 Python Implementation

```python
"""Check continuous enrollment with allowable gap."""
import pandas as pd


def check_continuous_enrollment(
    enrollment: pd.DataFrame, member_id: str,
    start_date: str, end_date: str, max_gap_days: int = 45,
) -> dict:
    """Check if a member is continuously enrolled with allowable gap.

    Args:
        enrollment: DataFrame [member_id, enroll_start, enroll_end].
        member_id: Member to check.
        start_date: Measurement period start (e.g., '2025-01-01').
        end_date: Measurement period end / anchor date (e.g., '2025-12-31').
        max_gap_days: Maximum allowable gap in days (HEDIS default: 45).

    Returns:
        Dict with is_enrolled (bool), total_gap_days (int), gap_periods (list).
    """
    start, end = pd.Timestamp(start_date), pd.Timestamp(end_date)
    me = enrollment[enrollment["member_id"] == member_id].copy()
    me["enroll_start"] = pd.to_datetime(me["enroll_start"]).clip(lower=start)
    me["enroll_end"] = pd.to_datetime(me["enroll_end"]).clip(upper=end)
    me = me[me["enroll_start"] <= me["enroll_end"]].sort_values("enroll_start").reset_index(drop=True)
    if me.empty:
        return {"is_enrolled": False, "total_gap_days": (end - start).days, "gap_periods": []}
    if not (me["enroll_end"] >= end).any():
        return {"is_enrolled": False, "total_gap_days": -1, "gap_periods": []}
    gap_periods, total_gap = [], 0
    if me.iloc[0]["enroll_start"] > start:
        g = (me.iloc[0]["enroll_start"] - start).days
        total_gap += g
        gap_periods.append({"from": str(start.date()), "to": str(me.iloc[0]["enroll_start"].date()), "days": g})
    for i in range(1, len(me)):
        if me.iloc[i]["enroll_start"] > me.iloc[i-1]["enroll_end"] + pd.Timedelta(days=1):
            g = (me.iloc[i]["enroll_start"] - me.iloc[i-1]["enroll_end"]).days - 1
            total_gap += g
            gap_periods.append({"from": str(me.iloc[i-1]["enroll_end"].date()), "to": str(me.iloc[i]["enroll_start"].date()), "days": g})
    return {"is_enrolled": total_gap <= max_gap_days, "total_gap_days": total_gap, "gap_periods": gap_periods}
```

### 1.2 SQL Implementation

```sql
-- Continuous enrollment check with allowable gap (≤45 days)
WITH enrollment_segments AS (
    SELECT member_id, enroll_start, enroll_end,
           LEAD(enroll_start) OVER (PARTITION BY member_id ORDER BY enroll_start) AS next_start
    FROM enrollment
    WHERE enroll_end >= '2025-01-01' AND enroll_start <= '2025-12-31'
),
gaps AS (
    SELECT member_id,
           DATEDIFF(day, enroll_end, next_start) - 1 AS gap_days
    FROM enrollment_segments
    WHERE next_start IS NOT NULL
      AND DATEDIFF(day, enroll_end, next_start) > 1
),
total_gaps AS (
    SELECT member_id, SUM(gap_days) AS total_gap_days
    FROM gaps
    GROUP BY member_id
),
anchor_check AS (
    SELECT DISTINCT member_id
    FROM enrollment
    WHERE enroll_end >= '2025-12-31'
)
SELECT a.member_id,
       COALESCE(g.total_gap_days, 0) AS total_gap_days,
       CASE WHEN COALESCE(g.total_gap_days, 0) <= 45 THEN 1 ELSE 0 END AS is_continuously_enrolled
FROM anchor_check a
LEFT JOIN total_gaps g ON a.member_id = g.member_id;
```

## 2. HEDIS Measure Calculation

### 2.1 Generic Measure Calculator (Python)

```python
"""Generic HEDIS measure rate calculator."""
import pandas as pd
from dataclasses import dataclass


@dataclass
class MeasureResult:
    measure_id: str
    denominator_count: int
    exclusion_count: int
    numerator_count: int
    rate: float
    gap_members: list[str]


def calculate_measure(
    eligible: pd.DataFrame,
    exclusions: pd.DataFrame,
    numerator_events: pd.DataFrame,
    measure_id: str,
) -> MeasureResult:
    """Calculate a HEDIS measure rate.

    Args:
        eligible: Denominator members. Columns: [member_id].
        exclusions: Excluded members. Columns: [member_id, exclusion_reason].
        numerator_events: Members meeting numerator. Columns: [member_id, event_date].
        measure_id: Measure identifier (e.g., 'CDC-HbA1c-Testing').

    Returns:
        MeasureResult with rate and gap member list.
    """
    denom_ids = set(eligible["member_id"])
    excl_ids = set(exclusions["member_id"])
    eligible_denom = denom_ids - excl_ids
    numer_ids = set(numerator_events["member_id"]) & eligible_denom
    gap_ids = eligible_denom - numer_ids
    denom_count = len(eligible_denom)
    rate = len(numer_ids) / denom_count if denom_count > 0 else 0.0
    return MeasureResult(
        measure_id=measure_id,
        denominator_count=denom_count,
        exclusion_count=len(excl_ids & denom_ids),
        numerator_count=len(numer_ids),
        rate=round(rate, 4),
        gap_members=sorted(gap_ids),
    )
```

### 2.2 Full Measure Calculation (SQL — CDC HbA1c Testing Example)

```sql
-- CDC: Comprehensive Diabetes Care — HbA1c Testing
WITH denominator AS (
    SELECT DISTINCT m.member_id
    FROM members m
    JOIN claims c ON m.member_id = c.member_id
    JOIN continuously_enrolled ce ON m.member_id = ce.member_id
    WHERE DATEDIFF(year, m.date_of_birth, '2025-12-31') BETWEEN 18 AND 75
      AND c.diagnosis_code LIKE 'E11%'
      AND c.service_date BETWEEN '2024-01-01' AND '2025-12-31'
      AND ce.is_continuously_enrolled = 1
),
exclusions AS (
    SELECT DISTINCT member_id FROM claims
    WHERE diagnosis_code IN ('Z51.5', 'N18.6')
       OR revenue_code IN ('0115','0125','0135','0145','0155','0235')
),
numerator AS (
    SELECT DISTINCT member_id FROM claims
    WHERE procedure_code IN ('83036','83037')
      AND service_date BETWEEN '2025-01-01' AND '2025-12-31'
)
SELECT COUNT(*) AS denom,
       SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END) AS excluded,
       SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) AS numer,
       ROUND(SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END)*1.0
             / NULLIF(COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END), 0), 4) AS rate
FROM denominator d
LEFT JOIN exclusions e ON d.member_id = e.member_id
LEFT JOIN numerator n ON d.member_id = n.member_id;
```

## 3. Care Gap Detection

```python
"""Detect and prioritize open care gaps across members."""
import pandas as pd
from datetime import date


def detect_care_gaps(
    members: pd.DataFrame,
    measures: list[dict],
    claims: pd.DataFrame,
    measurement_year: int = 2025,
) -> pd.DataFrame:
    """Detect open care gaps for a population.

    Args:
        members: DataFrame [member_id, date_of_birth, gender, risk_score].
        measures: List of dicts with keys: measure_id, age_min, age_max,
            gender (str|None), diagnosis_codes (list), numerator_codes (list),
            star_weight (1 or 3).
        claims: DataFrame [member_id, service_date, diagnosis_code, procedure_code].
        measurement_year: Calendar year for measurement.

    Returns:
        DataFrame: [member_id, measure_id, star_weight, risk_score, priority_score].
    """
    anchor = date(measurement_year, 12, 31)
    year_start = date(measurement_year, 1, 1)
    gaps = []
    for measure in measures:
        eligible = members.copy()
        eligible["age"] = eligible["date_of_birth"].apply(lambda d: (anchor - d).days // 365)
        eligible = eligible[eligible["age"].between(measure["age_min"], measure["age_max"])]
        if measure.get("gender"):
            eligible = eligible[eligible["gender"] == measure["gender"]]
        if measure.get("diagnosis_codes"):
            dx_members = claims[
                claims["diagnosis_code"].str.startswith(tuple(measure["diagnosis_codes"]))
            ]["member_id"].unique()
            eligible = eligible[eligible["member_id"].isin(dx_members)]
        year_claims = claims[claims["service_date"].between(str(year_start), str(anchor))]
        closed = year_claims[
            year_claims["procedure_code"].isin(measure["numerator_codes"])
        ]["member_id"].unique()
        for _, row in eligible[~eligible["member_id"].isin(closed)].iterrows():
            sw = measure.get("star_weight", 1)
            gaps.append({
                "member_id": row["member_id"], "measure_id": measure["measure_id"],
                "star_weight": sw, "risk_score": row.get("risk_score", 0),
                "priority_score": round(sw * 30 + min(row.get("risk_score", 0) * 25, 25) + 20, 1),
            })
    return pd.DataFrame(gaps).sort_values("priority_score", ascending=False).reset_index(drop=True)
```

## 4. Utilization Rate Computation

```sql
-- Utilization rates per 1000 members: ED, inpatient, 30-day readmissions
WITH members AS (
    SELECT COUNT(DISTINCT member_id) AS member_count FROM continuously_enrolled WHERE is_continuously_enrolled = 1
),
ed AS (
    SELECT COUNT(*) AS cnt FROM claims WHERE revenue_code IN ('0450','0451','0452','0456','0459') AND service_date BETWEEN '2025-01-01' AND '2025-12-31'
),
ip AS (
    SELECT COUNT(DISTINCT claim_id) AS cnt FROM claims WHERE claim_type = 'inpatient' AND admit_date BETWEEN '2025-01-01' AND '2025-12-31'
),
readmit AS (
    SELECT COUNT(*) AS cnt FROM (
        SELECT member_id, admit_date, LAG(discharge_date) OVER (PARTITION BY member_id ORDER BY admit_date) AS prev_dc
        FROM claims WHERE claim_type = 'inpatient' AND admit_date BETWEEN '2025-01-01' AND '2025-12-31'
    ) s WHERE DATEDIFF(day, prev_dc, admit_date) <= 30 AND prev_dc IS NOT NULL
)
SELECT ROUND(ed.cnt*1000.0/m.member_count,1) AS ed_per_1000,
       ROUND(ip.cnt*1000.0/m.member_count,1) AS ip_per_1000,
       ROUND(readmit.cnt*1000.0/m.member_count,1) AS readmit_per_1000
FROM members m, ed, ip, readmit;
```

## 5. High-Cost Claimant Identification

```python
"""Identify high-cost claimants and analyze cost drivers."""
import pandas as pd
import numpy as np


def identify_high_cost_claimants(
    claims: pd.DataFrame,
    threshold_percentile: float = 95,
    measurement_year: int = 2025,
) -> dict:
    """Identify high-cost claimants above a percentile threshold.

    Args:
        claims: DataFrame [member_id, service_date, paid_amount, claim_type, diagnosis_code].
        threshold_percentile: Percentile cutoff (default 95th).
        measurement_year: Calendar year to analyze.

    Returns:
        Dict with threshold, count, pct of total spend, and member DataFrame.
    """
    year_claims = claims[
        pd.to_datetime(claims["service_date"]).dt.year == measurement_year
    ]
    member_costs = (
        year_claims.groupby("member_id")
        .agg(total_paid=("paid_amount", "sum"), claim_count=("paid_amount", "count"))
        .reset_index()
    )
    threshold = np.percentile(member_costs["total_paid"], threshold_percentile)
    high_cost = member_costs[member_costs["total_paid"] >= threshold].sort_values(
        "total_paid", ascending=False
    )
    return {
        "threshold_amount": round(threshold, 2),
        "high_cost_count": len(high_cost),
        "high_cost_pct_of_total": round(
            high_cost["total_paid"].sum() / member_costs["total_paid"].sum() * 100, 1
        ),
        "high_cost_members": high_cost,
    }
```

## 6. Risk Stratification Scoring

### 6.1 Charlson Comorbidity Index (Python)

```python
"""Calculate Charlson Comorbidity Index from diagnosis codes."""

# ICD-10 prefix → (condition, weight). Subset of key mappings.
CHARLSON_MAP = {
    "I21": ("mi", 1), "I22": ("mi", 1), "I50": ("chf", 1),
    "I70": ("pvd", 1), "I71": ("pvd", 1), "I6": ("cvd", 1),
    "F01": ("dementia", 1), "F03": ("dementia", 1), "G30": ("dementia", 1),
    "J4": ("copd", 1), "M05": ("ctd", 1), "M06": ("ctd", 1),
    "K25": ("pud", 1), "K26": ("pud", 1),
    "K70": ("mild_liver", 1), "K73": ("mild_liver", 1), "K74": ("mild_liver", 1),
    "E109": ("dm_uncomp", 1), "E119": ("dm_uncomp", 1),
    "E102": ("dm_comp", 2), "E112": ("dm_comp", 2),
    "G81": ("hemiplegia", 2), "N18": ("renal", 2),
    "C": ("cancer", 2),
    "C77": ("metastatic", 6), "C78": ("metastatic", 6), "C79": ("metastatic", 6),
    "B20": ("hiv", 6),
}


def charlson_score(diagnosis_codes: list[str]) -> dict:
    """Calculate Charlson Comorbidity Index. Returns {score, conditions}."""
    matched: dict[str, int] = {}
    for code in [c.replace(".", "") for c in diagnosis_codes]:
        for prefix, (cond, wt) in CHARLSON_MAP.items():
            if code.startswith(prefix):
                if cond == "cancer" and "metastatic" in matched:
                    continue
                if cond == "metastatic":
                    matched.pop("cancer", None)
                if cond == "dm_uncomp" and "dm_comp" in matched:
                    continue
                if cond == "dm_comp":
                    matched.pop("dm_uncomp", None)
                if cond not in matched or wt > matched[cond]:
                    matched[cond] = wt
                break
    return {"score": sum(matched.values()), "conditions": matched}
```

### 6.2 LACE Readmission Risk Score

```python
"""Calculate LACE readmission risk score."""


def lace_score(length_of_stay: int, acuity: str, charlson: int, ed_visits_6mo: int) -> dict:
    """Calculate LACE index for 30-day readmission risk.

    Returns dict with total score, component scores, and risk tier.
    """
    l = 7 if length_of_stay >= 14 else (5 if length_of_stay >= 7 else (4 if length_of_stay >= 4 else min(length_of_stay, 3)))
    a = {"emergent": 3, "urgent": 2, "elective": 0}.get(acuity.lower(), 0)
    c = 5 if charlson >= 4 else min(charlson, 3)
    e = min(ed_visits_6mo, 4)
    total = l + a + c + e
    tier = "high" if total >= 10 else ("moderate" if total >= 5 else "low")
    return {"total": total, "components": {"L": l, "A": a, "C": c, "E": e}, "risk_tier": tier}
```

## 7. Measure Stratification by Plan/Provider

```sql
-- Measure rate stratified by health plan and provider
SELECT health_plan, assigned_pcp_npi,
       COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END) AS eligible_denom,
       SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) AS numerator,
       ROUND(SUM(CASE WHEN e.member_id IS NULL AND n.member_id IS NOT NULL THEN 1 ELSE 0 END) * 100.0
             / NULLIF(COUNT(*) - SUM(CASE WHEN e.member_id IS NOT NULL THEN 1 ELSE 0 END), 0), 1) AS rate_pct
FROM denominator_members m
LEFT JOIN exclusion_members e ON m.member_id = e.member_id
LEFT JOIN numerator_members n ON m.member_id = n.member_id
GROUP BY health_plan, assigned_pcp_npi
ORDER BY rate_pct ASC;
```

## 8. Parameter Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `measurement_year` | Current calendar year | HEDIS reporting year |
| `max_gap_days` | 45 | Maximum allowable enrollment gap |
| `anchor_date` | Dec 31 of measurement year | Date member must be enrolled through |
| `dx_lookback_years` | 2 | Years to look back for qualifying diagnoses |
| `threshold_percentile` | 95 | Percentile cutoff for high-cost identification |
| `readmission_window` | 30 | Days after discharge for readmission flag |

## 9. Common Mistakes

- **Wrong:** Including segment end dates when calculating enrollment gap days
  **Right:** Calculate gaps as the calendar days *between* segments (day after end of segment A to day before start of segment B)
  **Why:** Off-by-one errors in gap calculation incorrectly exclude continuously enrolled members or include ineligible ones

- **Wrong:** Using enrollment segments as-is without clipping to the measurement year boundaries
  **Right:** Clip all enrollment segments to the measurement year start and end dates before calculating gaps
  **Why:** Segments extending beyond the year inflate coverage calculations and produce incorrect enrollment determinations

- **Wrong:** Using service date for inpatient utilization metrics
  **Right:** Use admit date and discharge date for inpatient claims — service date is for professional/outpatient claims
  **Why:** Inpatient utilization (admissions, readmissions, length of stay) is defined by admission events, not individual service lines

- **Wrong:** Counting a member multiple times in the numerator when they have multiple qualifying events
  **Right:** Deduplicate numerator events by member ID — each member counts once regardless of how many tests or services they received
  **Why:** Multiple events for the same member inflate the numerator and produce artificially high measure rates

- **Wrong:** Calculating member age as of the run date or an arbitrary date
  **Right:** Calculate age as of the measure-specific anchor date (typically December 31 of the measurement year)
  **Why:** Using the wrong anchor date shifts age-based eligibility and includes or excludes members incorrectly

- **Wrong:** Only looking at the measurement year for qualifying diagnoses
  **Right:** Apply the measure-specified lookback period (typically 2 years) for identifying members with qualifying conditions
  **Why:** Many HEDIS measures require a diagnosis in the measurement year OR the year prior; using only one year misses eligible members
