---
name: edc-data-validation
description: >
  Generate code for EDC export validation, clinical data range checks, cross-form
  consistency checks, SDTM structure validation, controlled terminology verification,
  and define.xml generation. Use when the user asks to validate clinical trial data
  exports, check vital sign or lab value ranges, verify AE date consistency, validate
  SDTM datasets against CDISC rules, generate define.xml, or build an automated data
  review pipeline. Triggers include "EDC validation", "range check clinical data",
  "cross-form consistency", "SDTM validation", "controlled terminology check",
  "define.xml generation", "Medidata Rave export", "Oracle InForm", "Veeva Vault CDMS",
  "clinical data cleaning", "edit check", "data query", "SDTM structure check",
  "lab range check", "vital signs validation", "AE date check", "protocol deviation
  detection", "OpenCDISC", "Pinnacles 21", "P21 validation".
usage: Invoke to generate Python or R code for clinical data validation and SDTM compliance checks.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {pinnacle21: "4.0", define-xml: "2.1"}
tags: [skill, category:pipeline, clinical-data, edc, sdtm, cdisc, validation, define-xml, hcls]
---

# EDC Data Validation — Pipeline Skill

## Overview

You generate deterministic Python code for clinical data validation pipelines.
When the user provides EDC exports or SDTM datasets, produce validation code following
the recipes below. Always confirm the input format and therapeutic area before generating.

## Usage

- Validate EDC exports with range checks, cross-form consistency, and partial date imputation
- Check SDTM datasets against CDISC controlled terminology and structure rules
- Generate define.xml and prioritized validation reports

## Core Concepts

---

## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

---

## 1. Validation Priority Decision Tree

Use this to triage findings and assign query priority:

```
Issue Detected
├── Missing/invalid RFSTDTC or DSSTDTC? → CRITICAL (blocks submission)
├── AE date outside study period (before consent or after completion)? → CRITICAL
├── CT violation on required codelist (SEX, AEOUT, AESER)? → CRITICAL
├── Out-of-range vital sign WITHOUT data comment? → HIGH
├── Missing AESER when AEOUT='FATAL' or SAE reported? → HIGH
├── Lab value triggers Hy's Law flag (ALT/AST >3×ULN + BILI >2×ULN)? → HIGH
├── Minor CT mismatch (case difference, trailing space)? → MEDIUM
├── Missing optional variable (AEENDTC, AESEV)? → MEDIUM
├── Formatting issue (date separators, decimal precision)? → LOW
└── Case sensitivity only (e.g., "Male" vs "M")? → LOW
```

**Severity → Action mapping:**
- CRITICAL → Auto-query, blocks dataset lock
- HIGH → Query within 48h, reviewer will flag
- MEDIUM → Batch query at next data cut
- LOW → Note for final clean-up, no query needed

---

## 2. Therapeutic-Area Decision Tree

Select range tables based on study type:

```
What is the therapeutic area?
├── Oncology
│   ├── Use RECIST response values: CR, PR, SD, PD, NE
│   ├── Tumor measurement: 0–300 mm (flag >200 as HIGH)
│   └── ECOG valid values: 0, 1, 2, 3, 4, 5
├── Cardiology
│   ├── QTcF: normal <450ms, borderline 450–480ms, prolonged >480ms, critical >500ms
│   ├── SYSBP: 70–200 mmHg (tighter than general)
│   └── HR: 40–150 beats/min (tighter than general)
├── Pediatric (age <18)
│   ├── SYSBP: multiply adult low by 0.7, high by 0.8
│   ├── HR: multiply adult high by 1.3 (higher resting HR)
│   ├── WEIGHT: 2–120 kg
│   └── HEIGHT: 30–200 cm
└── General / Geriatric (age ≥65)
    ├── Use standard ranges (§3 below)
    └── Flag HR >180 as CRITICAL (not just HIGH)
```

---

## 3. Range Checks — Vital Signs and Labs

```python
import pandas as pd

VS_RANGES = {
    "SYSBP":  {"low": 60, "high": 250, "unit": "mmHg"},
    "DIABP":  {"low": 30, "high": 150, "unit": "mmHg"},
    "HR":     {"low": 30, "high": 220, "unit": "beats/min"},
    "TEMP":   {"low": 34.0, "high": 42.0, "unit": "C"},
    "WEIGHT": {"low": 20, "high": 300, "unit": "kg"},
    "HEIGHT": {"low": 50, "high": 250, "unit": "cm"},
    "RESP":   {"low": 6, "high": 60, "unit": "breaths/min"},
}

LB_RANGES = {
    "ALT":   {"low": 0, "high": 500, "unit": "U/L"},
    "AST":   {"low": 0, "high": 500, "unit": "U/L"},
    "BILI":  {"low": 0, "high": 30, "unit": "mg/dL"},
    "CREAT": {"low": 0, "high": 20, "unit": "mg/dL"},
    "HGB":   {"low": 3, "high": 25, "unit": "g/dL"},
    "WBC":   {"low": 0, "high": 100, "unit": "10^9/L"},
    "PLAT":  {"low": 0, "high": 1500, "unit": "10^9/L"},
    "GLUC":  {"low": 10, "high": 1000, "unit": "mg/dL"},
}

# Pediatric multipliers (apply to VS_RANGES when age < 18)
PEDIATRIC_MULT = {"SYSBP_low": 0.7, "SYSBP_high": 0.8, "HR_high": 1.3}

# Hy's Law: ALT or AST >3×ULN AND BILI >2×ULN (ULN: ALT=40, AST=37, BILI=1.2)
HYS_LAW = {"ALT_ULN": 40, "AST_ULN": 37, "BILI_ULN": 1.2, "ALT_MULT": 3, "BILI_MULT": 2}

def check_ranges(df: pd.DataFrame, testcd_col: str, value_col: str,
                 ranges: dict, domain: str) -> pd.DataFrame:
    issues = []
    for testcd, limits in ranges.items():
        subset = df[df[testcd_col] == testcd]
        oob = subset[(subset[value_col] < limits["low"]) | (subset[value_col] > limits["high"])]
        for _, row in oob.iterrows():
            severity = "HIGH" if testcd in ("SYSBP", "HR", "ALT", "AST", "BILI") else "MEDIUM"
            issues.append({"USUBJID": row.get("USUBJID"), "DOMAIN": domain,
                           "TESTCD": testcd, "VALUE": row[value_col],
                           "EXPECTED": f"{limits['low']}–{limits['high']} {limits['unit']}",
                           "SEVERITY": severity})
    return pd.DataFrame(issues)
```

---

## 4. Cross-Form Consistency Checks (8 checks)

```python
def cross_form_checks(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    ae, ds, dm = datasets.get("AE", pd.DataFrame()), datasets.get("DS", pd.DataFrame()), datasets.get("DM", pd.DataFrame())
    sv, cm, ex = datasets.get("SV", pd.DataFrame()), datasets.get("CM", pd.DataFrame()), datasets.get("EX", pd.DataFrame())
    issues = []
    to_dt = lambda s: pd.to_datetime(s, errors="coerce")

    # 1. AE start < informed consent → CRITICAL
    if not ae.empty and "RFICDTC" in dm.columns:
        ic = dm.set_index("USUBJID")["RFICDTC"].apply(to_dt)
        for _, r in ae.assign(AESTDTC=to_dt(ae["AESTDTC"])).iterrows():
            ic_dt = ic.get(r["USUBJID"])
            if pd.notna(ic_dt) and pd.notna(r["AESTDTC"]) and r["AESTDTC"] < ic_dt:
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "AE_BEFORE_CONSENT", "SEVERITY": "CRITICAL"})

    # 2. Fatal AE without DS death record → CRITICAL
    if not ae.empty and not ds.empty and "DSDECOD" in ds.columns:
        death_subj = set(ds[ds["DSDECOD"] == "DEATH"]["USUBJID"])
        for _, r in ae[ae["AEOUT"] == "FATAL"].iterrows():
            if r["USUBJID"] not in death_subj:
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "FATAL_AE_NO_DEATH", "SEVERITY": "CRITICAL"})

    # 3. Disposition date > last visit + 7 days → HIGH
    if not ds.empty and not sv.empty:
        last_sv = sv.groupby("USUBJID")["SVSTDTC"].max().apply(to_dt)
        for _, r in ds.assign(DSSTDTC=to_dt(ds["DSSTDTC"])).iterrows():
            lv = last_sv.get(r["USUBJID"])
            if pd.notna(lv) and pd.notna(r["DSSTDTC"]) and r["DSSTDTC"] > lv + pd.Timedelta(days=7):
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "DS_AFTER_LAST_VISIT", "SEVERITY": "HIGH"})

    # 4. Lab collection on non-visit day → MEDIUM
    if not datasets.get("LB", pd.DataFrame()).empty and not sv.empty:
        sv_set = set(zip(sv["USUBJID"], to_dt(sv["SVSTDTC"]).dt.date))
        lb = datasets["LB"].assign(LBDTC=to_dt(datasets["LB"].get("LBDTC")))
        for _, r in lb.dropna(subset=["LBDTC"]).iterrows():
            if (r["USUBJID"], r["LBDTC"].date()) not in sv_set:
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "LB_NO_VISIT", "SEVERITY": "MEDIUM"})

    # 5. Conmed start after study completion → MEDIUM
    if not cm.empty and "RFPENDTC" in dm.columns:
        end = dm.set_index("USUBJID")["RFPENDTC"].apply(to_dt)
        for _, r in cm.assign(CMSTDTC=to_dt(cm.get("CMSTDTC"))).dropna(subset=["CMSTDTC"]).iterrows():
            e = end.get(r["USUBJID"])
            if pd.notna(e) and r["CMSTDTC"] > e:
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "CM_AFTER_COMPLETION", "SEVERITY": "MEDIUM"})

    # 6. Randomization without signed consent → CRITICAL
    if not dm.empty and "RFICDTC" in dm.columns and "ARMCD" in dm.columns:
        for _, r in dm.iterrows():
            if pd.notna(r.get("ARMCD")) and r["ARMCD"] != "SCRNFAIL" and pd.isna(r.get("RFICDTC")):
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "RAND_NO_CONSENT", "SEVERITY": "CRITICAL"})

    # 7. Unscheduled visit without comment → MEDIUM
    if not sv.empty and "SVUPDES" in sv.columns:
        unsched = sv[sv["VISITNUM"].astype(str).str.contains(r"\.", na=False)]
        no_comment = unsched[unsched["SVUPDES"].isna() | (unsched["SVUPDES"].str.strip() == "")]
        for _, r in no_comment.iterrows():
            issues.append({"USUBJID": r["USUBJID"], "CHECK": "UNSCHED_NO_COMMENT", "SEVERITY": "MEDIUM"})

    # 8. Dose modification without corresponding AE → HIGH
    if not ex.empty and not ae.empty and "EXADJ" in ex.columns:
        ae_subj = set(zip(ae["USUBJID"], to_dt(ae.get("AESTDTC")).dt.date))
        dose_mod = ex[ex["EXADJ"].notna() & (ex["EXADJ"] != "")].assign(EXSTDTC=to_dt(ex["EXSTDTC"]))
        for _, r in dose_mod.dropna(subset=["EXSTDTC"]).iterrows():
            if (r["USUBJID"], r["EXSTDTC"].date()) not in ae_subj:
                issues.append({"USUBJID": r["USUBJID"], "CHECK": "DOSE_MOD_NO_AE", "SEVERITY": "HIGH"})

    return pd.DataFrame(issues)
```

---

## 5. Partial Date Imputation

```python
import calendar

def impute_partial_date(dtc: str, position: str = "start") -> tuple[str, str]:
    """Impute partial ISO 8601 dates. Returns (imputed_date, DTYPE).
    position: 'start' imputes early, 'end' imputes late."""
    if pd.isna(dtc) or dtc.strip() == "":
        return (None, None)
    parts = dtc.split("-")
    if len(parts) == 3 and len(parts[2]) >= 2:
        return (dtc, None)  # Complete date, no imputation
    year = int(parts[0])
    if len(parts) == 1:  # YYYY only
        if position == "start":
            return (f"{year}-01-01", "FIRST")
        return (f"{year}-12-31", "LAST")
    month = int(parts[1])
    if len(parts) == 2:  # YYYY-MM only
        if position == "start":
            return (f"{year}-{month:02d}-01", "FIRST")
        last_day = calendar.monthrange(year, month)[1]
        return (f"{year}-{month:02d}-{last_day}", "LAST")
    return (dtc, None)
```

---

## 6. Aggregate Report and define.xml

```python
from lxml import etree

def generate_validation_report(*issue_dfs, output_path="validation_report.csv"):
    """Combine all issues into a single prioritized report."""
    all_issues = pd.concat([df for df in issue_dfs if not df.empty], ignore_index=True)
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_issues = all_issues.sort_values(by="SEVERITY", key=lambda s: s.map(sev_order).fillna(4))
    all_issues.to_csv(output_path, index=False)
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        print(f"  {sev}: {(all_issues['SEVERITY'] == sev).sum()}")
    return all_issues

def generate_define_xml(datasets: dict[str, pd.DataFrame], study_oid: str,
                        output_path: str = "define.xml") -> None:
    """Generate minimal define.xml 2.0 skeleton from SDTM datasets."""
    NS = "http://www.cdisc.org/ns/odm/v1.3"
    DEF = "http://www.cdisc.org/ns/def/v2.0"
    nsmap = {None: NS, "def": DEF, "xlink": "http://www.w3.org/1999/xlink"}
    root = etree.Element("ODM", nsmap=nsmap, FileOID=f"define_{study_oid}",
                          FileType="Snapshot", ODMVersion="1.3.2")
    study = etree.SubElement(root, "Study", OID=study_oid)
    gd = etree.SubElement(study, "GlobalVariables")
    etree.SubElement(gd, "StudyName").text = study_oid
    etree.SubElement(gd, "ProtocolName").text = study_oid
    mdv = etree.SubElement(study, "MetaDataVersion", OID="MDV.1", Name="SDTM Metadata")
    for domain_name, df in sorted(datasets.items()):
        igd = etree.SubElement(mdv, "ItemGroupDef", OID=f"IG.{domain_name}",
                               Name=domain_name, Repeating="Yes" if domain_name != "DM" else "No")
        for col in df.columns:
            dtype = "integer" if df[col].dtype in ("int64", "float64") else "text"
            etree.SubElement(mdv, "ItemDef", OID=f"IT.{domain_name}.{col}",
                             Name=col, DataType=dtype)
            etree.SubElement(igd, "ItemRef", ItemOID=f"IT.{domain_name}.{col}",
                             Mandatory="Yes" if col in ("STUDYID", "USUBJID") else "No")
    etree.ElementTree(root).write(output_path, xml_declaration=True,
                                   encoding="UTF-8", pretty_print=True)
```

---

## 7. Parameter Reference

| Parameter | Default | Notes |
|---|---|---|
| VS SYSBP range | 60–250 mmHg | Pediatric: ×0.7 low, ×0.8 high |
| VS HR range | 30–220 beats/min | Pediatric: ×1.3 high; Geriatric: flag >180 as CRITICAL |
| LB ALT/AST | 0–500 U/L | Flag >3×ULN (ALT ULN=40, AST ULN=37) for Hy's Law |
| LB BILI | 0–30 mg/dL | Hy's Law: >2×ULN (ULN=1.2) with elevated ALT/AST |
| QTcF (cardiology) | <450 normal | 450–480 borderline, >480 prolonged, >500 CRITICAL |
| RECIST (oncology) | CR/PR/SD/PD/NE | Flag any other value as CT violation |
| Partial date imputation | Start→earliest, End→latest | Always set DTYPE column |
| Severity levels | CRITICAL/HIGH/MEDIUM/LOW | Map to query priority P1–P4 |

---

## Common Mistakes

- **Wrong:** Applying adult vital sign ranges to pediatric subjects without age adjustment
  **Right:** Scale ranges by age group (e.g., pediatric SBP upper = adult × 0.8, HR upper = adult × 1.3)
  **Why:** Normal pediatric values differ substantially from adults — flagging a child's HR of 130 as abnormal wastes data management time

- **Wrong:** Flagging partial dates as errors instead of applying imputation rules
  **Right:** Impute start dates to earliest possible (01-JAN-YYYY) and end dates to latest possible, then set DTYPE = "DERIVED"
  **Why:** Partial dates are expected in clinical data; rejecting them loses valid records and violates SDTM imputation conventions

- **Wrong:** Validating SDTM controlled terminology against a hardcoded list instead of the study's CT version
  **Right:** Always validate against the specific CDISC CT version declared in the study's define.xml
  **Why:** CT evolves across versions — a valid term in CT 2023-12-15 may not exist in CT 2022-09-30 and vice versa

- **Wrong:** Running cross-form date checks without accounting for time zones or visit windows
  **Right:** Allow ±1 day tolerance for cross-form date comparisons and document the tolerance in the validation plan
  **Why:** Subjects crossing time zones or overnight visits produce legitimate 1-day discrepancies that are not data errors

- **Wrong:** Generating queries for every out-of-range lab value without checking units
  **Right:** Normalize units before range checking (e.g., convert mg/dL ↔ µmol/L for creatinine) using LBORRESU/LBSTRESU
  **Why:** A creatinine of 88 µmol/L is normal but flags as critical if the range check assumes mg/dL (normal: 0.6–1.2)

- **Wrong:** Treating all validation findings as equal priority
  **Right:** Classify by clinical impact: CRITICAL (patient safety), HIGH (primary endpoint), MEDIUM (secondary), LOW (cosmetic)
  **Why:** Flooding sites with low-priority queries delays resolution of safety-critical issues
