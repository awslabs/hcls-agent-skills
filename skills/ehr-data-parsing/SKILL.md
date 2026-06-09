---
name: ehr-data-parsing
description: Parse and extract clinical data from HL7v2 messages and FHIR R4 resources using Python. Use when the user mentions HL7v2, HL7, FHIR, PID segment, OBX segment, MSH segment, Patient resource, Observation resource, Condition resource, MedicationRequest, EHR data extraction, clinical message parsing, FHIR bundle, HL7 to FHIR conversion, ADT message, ORU message, lab result extraction, or clinical data quality checks. Triggers include "parse HL7", "extract FHIR", "HL7v2 message", "FHIR resource", "PID segment", "OBX segment", "Patient resource", "Observation resource", "EHR parsing", "clinical data extraction", "HL7 to CSV", "FHIR to DataFrame".
usage: Invoke when parsing HL7v2 messages, extracting FHIR R4 resources, converting between clinical data formats, or running data quality checks on EHR data.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {hl7apy: "1.3.4", fhir-resources: "R4"}
tags: [skill, category:pipeline, ehr, hl7, fhir, clinical-data, interoperability, hcls]
---

# EHR Data Parsing

## Overview

This skill encodes Python pipelines for parsing clinical data from two
dominant formats: HL7v2 (pipe-delimited messages) and FHIR R4 (JSON
resources). It covers extraction of patient demographics, lab results,
diagnoses, and medications, plus format conversion and data quality checks.

Scope:
- HL7v2 message parsing (MSH, PID, PV1, OBR, OBX segments)
- FHIR R4 resource extraction (Patient, Observation, Condition, MedicationRequest)
- HL7v2 → tabular (CSV/DataFrame) conversion
- FHIR Bundle iteration and flattening
- Data quality checks (completeness, date validation, code system verification)

Out of scope: HL7v3/CDA parsing, FHIR server deployment, SMART on FHIR
authentication, real-time message routing.

## Usage

Invoke when the user asks to:
- Parse an HL7v2 message or batch file
- Extract patient demographics, labs, diagnoses, or medications from FHIR
- Convert HL7v2 messages to CSV or pandas DataFrames
- Flatten FHIR Bundles into tabular format
- Run quality checks on clinical data extracts

The skill emits Python code using `python-hl7` for HL7v2 and `fhir.resources`
for FHIR R4. Install dependencies:

```bash
pip install python-hl7 fhir.resources pandas
```


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

### Parser Selection Decision Tree

```
What is the input format?
├─ HL7v2 (pipe-delimited, segments start with MSH|PID|OBX...)
│  ├─ Message type?
│  │  ├─ ORU^R01 (lab results) → extract OBR + OBX segments
│  │  ├─ ADT^A01/A08 (admit/update) → extract PID + PV1 segments
│  │  └─ ORM^O01 (orders) → extract ORC + OBR segments
│  └─ Library: python-hl7 (parse → segment → field access)
└─ FHIR R4 (JSON resources)
   ├─ Single resource → fhir.resources model_validate(json)
   └─ Bundle → iterate entry[], check resource_type, follow pagination (link.next)
      ├─ Extract by system URI, not array position
      └─ Check choice types (valueQuantity vs valueCodeableConcept)
```

### HL7v2 Message Structure

HL7v2 messages are pipe-delimited, segment-based. Each segment starts with
a 3-character identifier followed by fields separated by `|`.

#### Key segments

| Segment | Name | Contains |
|---|---|---|
| MSH | Message Header | Sending/receiving app, message type, timestamp, version |
| PID | Patient Identification | MRN, name, DOB, sex, address, phone |
| PV1 | Patient Visit | Visit number, patient class, attending physician |
| OBR | Observation Request | Order number, test ordered, ordering provider |
| OBX | Observation Result | Result value, units, reference range, abnormal flag |
| DG1 | Diagnosis | Diagnosis code, type, description |
| AL1 | Allergy | Allergen, reaction, severity |

#### Common message types

| Type | Trigger | Use |
|---|---|---|
| ADT^A01 | Admit | Patient admission |
| ADT^A08 | Update | Patient information update |
| ORU^R01 | Observation | Lab/radiology results |
| ORM^O01 | Order | New order placed |
| MDM^T02 | Document | Document notification |

### 1. Parse HL7v2 Messages

```python
import hl7

raw = (
    "MSH|^~\\&|LAB|HOSP|EHR|HOSP|20240115120000||ORU^R01|MSG001|P|2.5\r"
    "PID|1||MRN123^^^HOSP^MR||DOE^JOHN^A||19800315|M|||"
    "123 MAIN ST^^ANYTOWN^CA^90210\r"
    "OBR|1|ORD001||CBC^Complete Blood Count^L|||20240115080000\r"
    "OBX|1|NM|WBC^White Blood Cell Count^L||7.5|10*3/uL|4.5-11.0|N|||F\r"
    "OBX|2|NM|HGB^Hemoglobin^L||14.2|g/dL|12.0-17.5|N|||F\r"
    "OBX|3|NM|PLT^Platelet Count^L||250|10*3/uL|150-400|N|||F\r"
)

msg = hl7.parse(raw)
```

#### Extract patient demographics from PID

```python
def extract_pid(msg):
    pid = msg.segment("PID")
    return {
        "mrn": str(pid(3)(0)(0)),          # PID-3.1: patient ID
        "last_name": str(pid(5)(0)(0)),     # PID-5.1: family name
        "first_name": str(pid(5)(0)(1)),    # PID-5.2: given name
        "dob": str(pid(7)),                 # PID-7: date of birth
        "sex": str(pid(8)),                 # PID-8: administrative sex
    }

demographics = extract_pid(msg)
# {'mrn': 'MRN123', 'last_name': 'DOE', 'first_name': 'JOHN',
#  'dob': '19800315', 'sex': 'M'}
```

#### PID field reference

| Field | Position | Format |
|---|---|---|
| Patient ID | PID-3 | CX datatype (ID^^^authority^type) |
| Patient Name | PID-5 | XPN: Family^Given^Middle |
| Date of Birth | PID-7 | YYYYMMDD |
| Sex | PID-8 | M, F, O, U |
| Address | PID-11 | XAD: Street^City^State^Zip |
| Phone | PID-13 | XTN datatype |

#### Extract lab results from OBX segments

```python
def extract_obx_results(msg):
    results = []
    for segment in msg:
        if str(segment(0)) == "OBX":
            results.append({
                "set_id": str(segment(1)),
                "value_type": str(segment(2)),       # NM=numeric, ST=string, CE=coded
                "test_code": str(segment(3)(0)(0)),   # OBX-3.1: identifier
                "test_name": str(segment(3)(0)(1)),   # OBX-3.2: text
                "value": str(segment(5)),             # OBX-5: observation value
                "units": str(segment(6)),             # OBX-6: units
                "ref_range": str(segment(7)),         # OBX-7: reference range
                "abnormal_flag": str(segment(8)),     # OBX-8: N/H/L/A
                "status": str(segment(11)),           # OBX-11: F=final, P=preliminary
            })
    return results

labs = extract_obx_results(msg)
```

#### OBX value types and status codes

| OBX-2 | Meaning | OBX-8 | Meaning | OBX-11 | Meaning |
|---|---|---|---|---|---|
| NM | Numeric | N | Normal | F | Final |
| ST | String | H | High | P | Preliminary |
| CE | Coded entry | L | Low | C | Corrected |

### 2. Batch HL7v2 Processing

```python
import hl7
import pandas as pd

def parse_hl7_file(filepath):
    """Parse a file containing multiple HL7v2 messages separated by blank lines."""
    with open(filepath, "r") as f:
        content = f.read()

    raw_messages = content.strip().split("\nMSH|")
    raw_messages = [raw_messages[0]] + ["MSH|" + m for m in raw_messages[1:]]

    all_results = []
    for raw in raw_messages:
        raw = raw.strip().replace("\n", "\r")
        if not raw:
            continue
        msg = hl7.parse(raw)
        demo = extract_pid(msg)
        for lab in extract_obx_results(msg):
            all_results.append({**demo, **lab})

    return pd.DataFrame(all_results)

df = parse_hl7_file("lab_results.hl7")
```

### 3. FHIR R4 Resource Extraction

#### Parse a Patient resource

```python
from fhir.resources.patient import Patient

patient_json = {
    "resourceType": "Patient",
    "id": "example-001",
    "identifier": [
        {"system": "http://hospital.example.org/mrn", "value": "MRN123"}
    ],
    "name": [{"family": "Doe", "given": ["John", "A"]}],
    "gender": "male",
    "birthDate": "1980-03-15",
    "address": [
        {"line": ["123 Main St"], "city": "Anytown", "state": "CA", "postalCode": "90210"}
    ],
}

patient = Patient.model_validate(patient_json)

demographics = {
    "id": patient.id,
    "mrn": patient.identifier[0].value if patient.identifier else None,
    "last_name": patient.name[0].family if patient.name else None,
    "first_name": patient.name[0].given[0] if patient.name and patient.name[0].given else None,
    "gender": patient.gender,
    "birth_date": str(patient.birthDate) if patient.birthDate else None,
}
```

#### Extract Observation, Condition, MedicationRequest

Pattern: `model_validate(json)` → extract by system URI, not array position.

```python
from fhir.resources.observation import Observation
from fhir.resources.condition import Condition
from fhir.resources.medicationrequest import MedicationRequest

def extract_observation(obs_json):
    obs = Observation.model_validate(obs_json)
    return {
        "id": obs.id, "status": obs.status,
        "loinc_code": next((c.code for c in (obs.code.coding or []) if c.system == "http://loinc.org"), None),
        "display": obs.code.coding[0].display if obs.code.coding else None,
        "value": obs.valueQuantity.value if obs.valueQuantity else None,
        "unit": obs.valueQuantity.unit if obs.valueQuantity else None,
        "effective_date": str(obs.effectiveDateTime) if obs.effectiveDateTime else None,
        "patient_ref": obs.subject.reference if obs.subject else None,
    }

def extract_condition(cond_json):
    cond = Condition.model_validate(cond_json)
    return {
        "id": cond.id,
        "status": cond.clinicalStatus.coding[0].code if cond.clinicalStatus and cond.clinicalStatus.coding else None,
        "snomed_code": next((c.code for c in (cond.code.coding or []) if c.system and "snomed" in c.system), None),
        "icd10_code": next((c.code for c in (cond.code.coding or []) if c.system and "icd-10" in c.system), None),
        "display": cond.code.coding[0].display if cond.code.coding else None,
        "onset": str(cond.onsetDateTime) if cond.onsetDateTime else None,
        "patient_ref": cond.subject.reference if cond.subject else None,
    }

def extract_medication_request(med_json):
    med = MedicationRequest.model_validate(med_json)
    cc = med.medicationCodeableConcept
    return {
        "id": med.id, "status": med.status,
        "rxnorm_code": cc.coding[0].code if cc and cc.coding else None,
        "display": cc.coding[0].display if cc and cc.coding else None,
        "dosage_text": med.dosageInstruction[0].text if med.dosageInstruction else None,
        "authored_on": str(med.authoredOn) if med.authoredOn else None,
        "patient_ref": med.subject.reference if med.subject else None,
    }
```

### 4. FHIR Bundle Flattening

```python
import json
import pandas as pd
from fhir.resources.bundle import Bundle

def flatten_observation_bundle(bundle_json):
    """Extract all Observation resources from a FHIR Bundle into a DataFrame."""
    bundle = Bundle.model_validate(bundle_json)
    rows = [extract_observation(entry.resource.model_dump())
            for entry in (bundle.entry or [])
            if entry.resource.resource_type == "Observation"]
    return pd.DataFrame(rows)

with open("observations_bundle.json") as f:
    df = flatten_observation_bundle(json.load(f))
```

### 5. Data Quality Checks

```python
import pandas as pd
from datetime import datetime

def check_completeness(df, required_columns):
    """Report missing value rates for required columns."""
    report = {}
    for col in required_columns:
        if col not in df.columns:
            report[col] = {"status": "MISSING_COLUMN", "pct_complete": 0.0}
        else:
            pct = (df[col].notna().sum() / len(df)) * 100
            report[col] = {
                "status": "OK" if pct >= 95 else "WARNING" if pct >= 80 else "FAIL",
                "pct_complete": round(pct, 1),
            }
    return report

def validate_dates(series, fmt="%Y-%m-%d", min_date="1900-01-01", max_date=None):
    """Validate date strings. Returns indices of invalid entries."""
    max_dt = datetime.strptime(max_date, fmt) if max_date else datetime.now()
    min_dt = datetime.strptime(min_date, fmt)
    invalid = []
    for idx, val in series.items():
        if pd.isna(val):
            continue
        try:
            dt = datetime.strptime(str(val)[:10], fmt)
            if dt < min_dt or dt > max_dt:
                invalid.append({"index": idx, "value": val, "reason": "out_of_range"})
        except ValueError:
            invalid.append({"index": idx, "value": val, "reason": "parse_error"})
    return invalid

def verify_code_system(df, code_col, valid_codes, system_name="unknown"):
    """Check that coded values belong to an expected set."""
    if code_col not in df.columns:
        return {"status": "MISSING_COLUMN", "invalid_count": 0}
    codes = df[code_col].dropna().unique()
    invalid = [c for c in codes if c not in valid_codes]
    return {
        "system": system_name, "total_unique": len(codes),
        "invalid_codes": invalid, "invalid_count": len(invalid),
        "status": "OK" if len(invalid) == 0 else "FAIL",
    }
```

#### Quality check thresholds

| Check | Pass | Warning | Fail |
|---|---|---|---|
| Completeness (required field) | ≥ 95% | 80–95% | < 80% |
| Date validity | 0 parse errors | — | Any parse error |
| Date range | All within expected range | — | Future dates or pre-1900 |
| Code system membership | All codes valid | — | Any unrecognized code |
| Duplicate patient IDs | 0 exact duplicates | — | Any duplicate MRN with conflicting demographics |

### 6. HL7v2 to FHIR Conceptual Mapping

| HL7v2 Segment | FHIR Resource | Key fields |
|---|---|---|
| PID | Patient | identifier, name, birthDate, gender |
| PV1 | Encounter | class, period, participant |
| OBR + OBX | Observation | code, value, effectiveDateTime, status |
| DG1 | Condition | code, onsetDateTime, clinicalStatus |
| ORC + RXE | MedicationRequest | medicationCodeableConcept, dosageInstruction |
| AL1 | AllergyIntolerance | code, reaction, criticality |

## Common Mistakes

- **Wrong:** Assuming fixed field positions across all HL7v2 versions without checking for empty segments
  **Right:** Always check for empty segments before accessing subfields — field positions are stable but optional fields may be absent
  **Why:** Accessing a subfield of an empty segment raises index errors or returns incorrect data

- **Wrong:** Splitting HL7v2 messages on `\n` instead of `\r`
  **Right:** Normalize segment delimiters to `\r` before parsing — many files use `\r\n` or `\n`
  **Why:** The HL7v2 standard segment delimiter is carriage return (`\r`); incorrect splitting produces malformed segments

- **Wrong:** Parsing OBX-5 without checking the value type in OBX-2
  **Right:** Always check OBX-2 first — numeric (NM) and coded (CE) results require different parsing logic
  **Why:** Misinterpreting a coded entry as numeric (or vice versa) produces corrupt data

- **Wrong:** Treating all OBX segments as lab results
  **Right:** Filter by OBR context or OBX-3 code system to distinguish labs from vitals, imaging impressions, and clinical notes
  **Why:** OBX carries many observation types; assuming all are labs leads to mixed, unusable datasets

- **Wrong:** Hardcoding FHIR resource field paths (e.g., always accessing `effectiveDateTime`)
  **Right:** Check which choice type variant is present (e.g., `effectiveDateTime` vs `effectivePeriod`, `valueQuantity` vs `valueCodeableConcept`)
  **Why:** FHIR allows choice types — hardcoded paths raise AttributeError or miss data when the alternate variant is used

- **Wrong:** Including preliminary Observations (`status: "preliminary"`) in analysis datasets
  **Right:** Filter on `status: "final"` for analysis — preliminary results may be superseded
  **Why:** Preliminary results can be corrected or replaced, leading to duplicate or inaccurate data in analyses

- **Wrong:** Extracting coded values by array position (e.g., `coding[0]`) instead of by system URI
  **Right:** Extract by system URI (e.g., filter for `"http://snomed.info/sct"`) — a Condition may carry both SNOMED and ICD-10 codings
  **Why:** Array order is not guaranteed; position-based access returns the wrong code system unpredictably

- **Wrong:** Processing only the first page of a FHIR Bundle without checking for pagination
  **Right:** Check `bundle.link` for `relation: "next"` and follow all pages until exhausted
  **Why:** FHIR servers return paginated Bundles — stopping at page one misses most of the data

- **Wrong:** Assuming all dates are ISO 8601 format across HL7v2 and FHIR
  **Right:** Parse HL7v2 dates as `YYYYMMDD[HHmmss]` and FHIR dates with variable precision (`2024`, `2024-01`, `2024-01-15`)
  **Why:** Format mismatches cause parse errors or silent data corruption

- **Wrong:** Accepting coded values without validating the code system URI
  **Right:** Verify that the `system` field matches the expected URI (e.g., `http://loinc.org` for LOINC codes)
  **Why:** Codes without system URIs are ambiguous — a "6690-2" without system confirmation may not be LOINC

## References

- python-hl7: https://python-hl7.readthedocs.io/
- fhir.resources (Python): https://pypi.org/project/fhir.resources/
- FHIR R4 Specification: https://hl7.org/fhir/R4/
- LOINC: https://loinc.org/
- SNOMED CT: https://www.snomed.org/
