---
name: claims-analytics
description: >
  Pipeline skill for healthcare claims data parsing, analysis, and fraud detection. Use when
  the user asks to parse X12 837 or 835 claim files, manipulate ICD-10 CPT or HCPCS codes,
  detect billing pattern anomalies, profile providers against specialty peers, identify
  outlier billing behavior, validate NCCI edits programmatically, detect duplicate claims,
  run Benford's law analysis on charges, build claims data pipelines, or analyze E&M code
  distributions. Triggers include "parse X12 837", "parse 835", "claims SQL", "ICD-10
  manipulation", "CPT code analysis", "provider profiling", "billing outlier", "NCCI
  validation code", "duplicate claim detection", "Benford's law charges", "claims ETL",
  "E&M distribution analysis", "claims analytics pipeline".
usage: Invoke to generate executable Python and SQL code for claims data parsing, billing pattern detection, provider profiling, and NCCI edit validation.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {pandas: "2.2", pyx12: "2.3"}
tags: [skill, category:pipeline, claims, analytics, hcls]
---

# Claims Analytics — Pipeline Skill

## Overview

Provide deterministic, copy-paste-ready Python and SQL code for healthcare claims data
processing: X12 parsing, code manipulation, provider profiling, outlier detection, NCCI
edit validation, and duplicate claim identification.

## Usage

- Parse X12 837/835 claim files into structured DataFrames
- Profile provider billing patterns and detect outliers (E&M upcoding, impossible days)
- Validate claims against NCCI edits and detect duplicate submissions

## Core Concepts

---


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## 1. X12 837 Professional Claim Parsing

```python
import pandas as pd
from typing import Generator


def parse_x12_837(filepath: str) -> Generator[dict, None, None]:
    """Parse X12 837P file into claim records.

    Yields:
        dict with claim_id, charge_amount, place_of_service, dx_codes, proc_codes,
        provider_npi, member_id, service_date.
    """
    with open(filepath, "r") as f:
        content = f.read()

    seg_term = content[105] if len(content) > 105 else "~"
    elem_sep = content[3] if len(content) > 3 else "*"
    segments = content.split(seg_term)

    claim = {}
    for seg in segments:
        el = seg.strip().split(elem_sep)
        sid = el[0] if el else ""

        if sid == "CLM":
            if claim:
                yield claim
            claim = {
                "claim_id": el[1] if len(el) > 1 else None,
                "charge_amount": float(el[2]) if len(el) > 2 else 0.0,
                "place_of_service": el[5].split(":")[0] if len(el) > 5 else None,
                "dx_codes": [], "proc_codes": [],
            }
        elif sid == "HI" and claim:
            for e in el[1:]:
                parts = e.split(":")
                if len(parts) >= 2:
                    claim["dx_codes"].append(parts[1])
        elif sid == "SV1" and claim:
            pp = el[1].split(":") if len(el) > 1 else []
            claim["proc_codes"].append({
                "cpt": pp[1] if len(pp) > 1 else None,
                "modifiers": [m for m in pp[2:6] if m] if len(pp) > 2 else [],
                "charge": float(el[2]) if len(el) > 2 else 0.0,
                "units": int(el[4]) if len(el) > 4 else 1,
            })
        elif sid == "NM1" and claim:
            q = el[1] if len(el) > 1 else ""
            if q == "82":
                claim["provider_npi"] = el[9] if len(el) > 9 else None
            elif q == "IL":
                claim["member_id"] = el[9] if len(el) > 9 else None
        elif sid == "DTP" and claim:
            if len(el) > 1 and el[1] == "472":
                claim["service_date"] = el[3] if len(el) > 3 else None
    if claim:
        yield claim

# Usage
claims = pd.json_normalize(list(parse_x12_837("claims_837p.txt")))
```

---

## 2. E&M Provider Profiling

### Python

```python
import pandas as pd
import numpy as np

EM_CODES = ["99202","99203","99204","99205","99211","99212","99213","99214","99215"]


def profile_em_distribution(claims_df: pd.DataFrame) -> pd.DataFrame:
    """Compare each provider's E&M distribution to specialty peers via z-scores."""
    em = claims_df[claims_df["proc_code"].isin(EM_CODES)].copy()

    prov_dist = em.groupby(["provider_id", "specialty", "proc_code"]).size().unstack(fill_value=0)
    prov_pct = prov_dist.div(prov_dist.sum(axis=1), axis=0)

    spec_mean = prov_pct.groupby("specialty").mean()
    spec_std = prov_pct.groupby("specialty").std()

    results = []
    for (prov, spec), row in prov_pct.iterrows():
        if spec not in spec_mean.index:
            continue
        z = (row - spec_mean.loc[spec]) / spec_std.loc[spec].replace(0, np.nan)
        results.append({
            "provider_id": prov, "specialty": spec,
            "total_em": int(prov_dist.loc[(prov, spec)].sum()),
            "pct_99214_99215": row.get("99214", 0) + row.get("99215", 0),
            "z_99214": z.get("99214", np.nan), "z_99215": z.get("99215", np.nan),
            "flag_upcoding": z.get("99214", 0) > 2.0 or z.get("99215", 0) > 2.0,
        })
    return pd.DataFrame(results).sort_values("z_99215", ascending=False)
```

### SQL

```sql
WITH provider_em AS (
    SELECT provider_id, specialty, proc_code, COUNT(*) AS cnt
    FROM claims
    WHERE proc_code IN ('99202','99203','99204','99205','99211','99212','99213','99214','99215')
    GROUP BY provider_id, specialty, proc_code
),
provider_total AS (
    SELECT provider_id, specialty, SUM(cnt) AS total FROM provider_em GROUP BY provider_id, specialty
),
provider_pct AS (
    SELECT e.provider_id, e.specialty, e.proc_code, t.total,
           ROUND(e.cnt * 100.0 / t.total, 2) AS pct
    FROM provider_em e JOIN provider_total t ON e.provider_id = t.provider_id
),
benchmark AS (
    SELECT specialty, proc_code, AVG(pct) AS avg_pct, STDDEV(pct) AS std_pct
    FROM provider_pct GROUP BY specialty, proc_code
)
SELECT p.provider_id, p.specialty, p.proc_code, p.pct, b.avg_pct,
       ROUND((p.pct - b.avg_pct) / NULLIF(b.std_pct, 0), 2) AS z_score
FROM provider_pct p
JOIN benchmark b ON p.specialty = b.specialty AND p.proc_code = b.proc_code
WHERE ABS((p.pct - b.avg_pct) / NULLIF(b.std_pct, 0)) > 2.0
ORDER BY z_score DESC;
```

---

## 3. NCCI Edit Validation

```python
import pandas as pd


def validate_ncci(claims_df: pd.DataFrame, ncci_edits: pd.DataFrame) -> pd.DataFrame:
    """Validate claims against NCCI edits. Returns violations.

    Args:
        claims_df: [claim_id, provider_id, member_id, service_date, proc_code, modifier_1].
        ncci_edits: [column1_cpt, column2_cpt, modifier_indicator, effective_date, deletion_date].
    """
    violations = []
    for (prov, mem, dt), grp in claims_df.groupby(["provider_id", "member_id", "service_date"]):
        codes = grp["proc_code"].tolist()
        mods = grp["modifier_1"].fillna("").tolist()

        for i, c1 in enumerate(codes):
            for j, c2 in enumerate(codes):
                if i >= j:
                    continue
                for col1, col2, mi in [(c1, c2, j), (c2, c1, i)]:
                    match = ncci_edits[
                        (ncci_edits["column1_cpt"] == col1) & (ncci_edits["column2_cpt"] == col2) &
                        (ncci_edits["effective_date"] <= dt) &
                        (ncci_edits["deletion_date"].isna() | (ncci_edits["deletion_date"] > dt))
                    ]
                    if match.empty:
                        continue
                    ind = match.iloc[0]["modifier_indicator"]
                    has_mod = mods[mi] in ("59", "XE", "XS", "XP", "XU")
                    if ind == "0" or (ind == "1" and not has_mod):
                        violations.append({
                            "provider_id": prov, "member_id": mem, "service_date": dt,
                            "column1_cpt": col1, "column2_cpt": col2,
                            "modifier_indicator": ind,
                            "status": "DENIED" if ind == "0" else "DENIED — modifier required",
                        })
    return pd.DataFrame(violations)
```

---

## 4. Duplicate Claim Detection

### Python

```python
import pandas as pd


def detect_duplicates(claims_df: pd.DataFrame, fuzzy_window_days: int = 3) -> pd.DataFrame:
    """Detect exact and near-duplicate claims."""
    key_cols = ["member_id", "provider_id", "proc_code", "service_date"]
    exact = claims_df[claims_df.duplicated(subset=key_cols, keep=False)].copy()
    exact["dup_type"] = "exact"

    s = claims_df.sort_values(key_cols)
    s["prev_date"] = s.groupby(key_cols[:3])["service_date"].shift(1)
    s["gap"] = (s["service_date"] - s["prev_date"]).dt.days
    near = s[(s["gap"] > 0) & (s["gap"] <= fuzzy_window_days)].copy()
    near["dup_type"] = "near"

    cols = ["claim_id", "member_id", "provider_id", "proc_code", "service_date", "dup_type"]
    return pd.concat([exact[cols], near[cols]])
```

### SQL

```sql
-- Exact duplicates
SELECT a.claim_id AS id_1, b.claim_id AS id_2, a.member_id, a.proc_code, a.service_date
FROM claims a JOIN claims b
  ON a.member_id = b.member_id AND a.provider_id = b.provider_id
  AND a.proc_code = b.proc_code AND a.service_date = b.service_date
  AND a.claim_id < b.claim_id;

-- Near-duplicates (within 3 days)
SELECT a.claim_id AS id_1, b.claim_id AS id_2, a.member_id, a.proc_code,
       a.service_date AS date_1, b.service_date AS date_2
FROM claims a JOIN claims b
  ON a.member_id = b.member_id AND a.provider_id = b.provider_id
  AND a.proc_code = b.proc_code AND a.claim_id < b.claim_id
  AND ABS(DATEDIFF(a.service_date, b.service_date)) BETWEEN 1 AND 3;
```

---

## 5. Benford's Law Analysis

```python
import pandas as pd
import numpy as np
from scipy.stats import chisquare

BENFORD = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
           5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}


def benfords_test(charges: pd.Series, provider_id: str = "") -> dict:
    """Test charge first-digit distribution against Benford's Law."""
    first = charges[charges > 0].apply(lambda x: int(str(x).lstrip("0").lstrip(".")[0]))
    first = first[first.between(1, 9)]
    counts = first.value_counts().sort_index()
    n = counts.sum()
    obs = np.array([counts.get(d, 0) for d in range(1, 10)])
    exp = np.array([BENFORD[d] * n for d in range(1, 10)])
    chi2, p = chisquare(obs, exp)
    return {"provider_id": provider_id, "chi2": round(chi2, 2),
            "p_value": round(p, 4), "flag": p < 0.01}
```

---

## 6. Impossible Day Detection

```python
import pandas as pd

CPT_MINUTES = {
    "99213": 15, "99214": 25, "99215": 40, "99203": 30, "99204": 45, "99205": 60,
    "90837": 53, "90834": 38, "97110": 15, "97140": 15, "99291": 74, "99292": 30,
}


def detect_impossible_days(claims_df: pd.DataFrame, max_min: int = 1440) -> pd.DataFrame:
    """Flag providers billing >24 hours of services in a single day."""
    df = claims_df.copy()
    df["est_min"] = df["proc_code"].map(CPT_MINUTES).fillna(0) * df["units"].fillna(1)
    daily = df.groupby(["provider_id", "service_date"]).agg(
        total_min=("est_min", "sum"), claims=("claim_id", "nunique")
    ).reset_index()
    return daily[daily["total_min"] > max_min].sort_values("total_min", ascending=False)
```

---

## 7. Parameter Reference

| Function | Key Parameter | Default | Guidance |
|---|---|---|---|
| `profile_em_distribution` | z-score threshold | 2.0 | Lower to 1.5 for sensitive screening |
| `validate_ncci` | NCCI edit file | CMS quarterly | Update quarterly from CMS |
| `detect_duplicates` | `fuzzy_window_days` | 3 | Increase to 7 for post-acute care |
| `benfords_test` | p-value threshold | 0.01 | Use 0.05 for initial screening |
| `detect_impossible_days` | `max_min` | 1440 | Reduce to 960 for stricter threshold |

---

## Common Mistakes

- **Wrong:** Parsing X12 837 files using the newline character as segment terminator
  **Right:** Read the segment terminator from position 105 of the ISA segment (the character after the last ISA element)
  **Why:** X12 segment terminators are defined in the interchange header — they can be `~`, `\n`, or any character; assuming `~` breaks on files using other terminators

- **Wrong:** Comparing provider E&M distributions to a single national benchmark
  **Right:** Benchmark against same-specialty, same-region, same-payer-mix peers
  **Why:** Specialty and geography drive legitimate variation — a cardiologist's 99214 rate is naturally higher than a pediatrician's

- **Wrong:** Flagging all exact duplicate claims as fraud
  **Right:** Distinguish true duplicates (same claim resubmitted) from legitimate corrections (different claim IDs, adjustment codes)
  **Why:** Payers routinely reprocess claims with new claim IDs after corrections — only same-claim-ID resubmissions without adjustment reason codes are suspect

- **Wrong:** Running Benford's Law analysis on charge amounts below $10
  **Right:** Filter to charges ≥ $10 before first-digit analysis; small charges cluster around fee-schedule amounts and naturally violate Benford's
  **Why:** Benford's Law applies to data spanning multiple orders of magnitude — low-value charges are constrained by fee schedules and produce false positives

- **Wrong:** Using NCCI edit tables without checking effective and deletion dates
  **Right:** Filter NCCI edits to those active on the claim's date of service using `effective_date <= service_date` and `(deletion_date IS NULL OR deletion_date > service_date)`
  **Why:** NCCI edits are versioned quarterly — applying current edits to historical claims produces false violations for pairs that were valid at the time of service

- **Wrong:** Detecting impossible days using only CPT time estimates without accounting for concurrent services
  **Right:** Distinguish sequential time-based services from concurrent ones (e.g., infusion supervision during E&M); only sum non-overlapping service minutes
  **Why:** Some services legitimately overlap (monitoring during infusion, teaching physician attestation) — naive summation inflates minutes and produces false flags
