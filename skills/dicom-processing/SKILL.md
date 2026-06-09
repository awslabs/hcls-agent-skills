---
name: dicom-processing
description: DICOM and NIfTI medical image processing pipeline. Triggers on DICOM, NIfTI, dcm2niix, de-identification, pydicom, DICOM header, conversion, anonymization, BIDS, DICOM tags, medical image format conversion, "DICOM to NIfTI", "burned-in PHI", "SeriesInstanceUID", "nibabel", "DICOM anonymization".
usage: Invoke when converting, parsing, or de-identifying DICOM/NIfTI medical images, or organizing data into BIDS format.
version: 1.0.0
validated_against:
  date: 2025-01-15
  packages: {pydicom: "2.4", dcm2niix: "1.0.20240202", nibabel: "5.2"}
tags: [skill, category:pipeline, medical-imaging, dicom, nifti, de-identification, hcls]
---

# DICOM Processing

## Overview

Pipeline skill for converting, reading, and de-identifying medical images in DICOM and NIfTI formats. Encodes deterministic commands and code for:

- DICOM → NIfTI conversion with `dcm2niix` (including BIDS sidecars)
- Reading DICOM headers and pixel data with `pydicom`
- PHI removal (de-identification) with `pydicom` or CTP DicomAnonymizer
- NIfTI inspection with `nibabel`
- Batch processing grouped by `SeriesInstanceUID`
- BIDS-compliant directory organization

Use this skill whenever the user works with `.dcm`, `.nii`, `.nii.gz`, DICOM directories, or anonymization workflows.

## Usage

### 1. Convert a DICOM series to NIfTI (dcm2niix)

```bash
# Standard conversion: gzip output, BIDS sidecar, pattern-named files
dcm2niix -z y -b y -f %p_%s -o output_dir input_dir
```

Flags (memorize):

| Flag | Meaning |
| --- | --- |
| `-z y` | gzip output (`.nii.gz`) |
| `-b y` | emit BIDS JSON sidecar |
| `-f %p_%s` | filename pattern: `%p` = protocol, `%s` = series number |
| `-m n` | do NOT merge 2D slices across series (prevents cross-series mixing) |
| `-o` | output directory |

Common naming tokens: `%p` protocol, `%s` series, `%t` time, `%i` patient ID, `%n` patient name, `%d` description.

### 2. Read a DICOM file with pydicom

```python
import pydicom

ds = pydicom.dcmread('file.dcm')
print(ds.PatientName, ds.StudyDate, ds.Modality)
print(ds.pixel_array.shape)  # numpy array of pixel data
```

### 3. De-identify a DICOM file (pydicom)

```python
import pydicom
from pydicom.uid import generate_uid

ds = pydicom.dcmread('file.dcm')

tags_to_remove = [
    'PatientName', 'PatientID', 'PatientBirthDate',
    'InstitutionName', 'ReferringPhysicianName', 'StudyDate',
]
for tag in tags_to_remove:
    if tag in ds:
        del ds[tag]

ds.PatientID = 'ANON_001'

# Remove private (vendor) tags — they frequently contain PHI
ds.remove_private_tags()

# Replace UIDs so the study/series/instance cannot be linked back
ds.StudyInstanceUID  = generate_uid()
ds.SeriesInstanceUID = generate_uid()
ds.SOPInstanceUID    = generate_uid()

ds.save_as('anon.dcm')
```

### 4. Batch de-identification with CTP DicomAnonymizer

```bash
# RSNA CTP / DicomBrowser DAP (DICOM Anonymizer Program)
java -jar DAP.jar -p profile.script -i input/ -o output/
```

Use this for large cohorts or when a validated DICOM Supplement 142 profile is required.

### 5. Load a NIfTI volume with nibabel

```python
import nibabel as nib

img = nib.load('file.nii.gz')
data   = img.get_fdata()  # numpy ndarray
affine = img.affine       # 4x4 voxel-to-world transform
header = img.header
```

### 6. Batch pattern: group by SeriesInstanceUID, convert per series

```python
from pathlib import Path
from collections import defaultdict
import pydicom, subprocess

def group_by_series(input_dir):
    series = defaultdict(list)
    for p in Path(input_dir).rglob('*.dcm'):
        ds = pydicom.dcmread(p, stop_before_pixels=True)
        series[ds.SeriesInstanceUID].append(p)
    return series

def convert_all(input_dir, output_dir):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    # dcm2niix handles series grouping internally when given a directory
    subprocess.run(
        ['dcm2niix', '-z', 'y', '-b', 'y', '-f', '%p_%s',
         '-o', output_dir, input_dir],
        check=True,
    )
```

### 7. BIDS organization

```
dataset/
├── dataset_description.json
├── participants.tsv
└── sub-01/
    └── ses-01/
        ├── anat/  sub-01_ses-01_T1w.nii.gz
        ├── func/  sub-01_ses-01_task-rest_bold.nii.gz
        └── dwi/   sub-01_ses-01_dwi.nii.gz
```

Rule: `sub-<label>/ses-<label>/<modality>/<sub>_<ses>_<suffix>.nii.gz`, with a matching `.json` sidecar.


## Response Format

- Lead with the command or code the user needs — explain after
- Structure as: confirm inputs → working code → key parameters explained → gotchas
- One complete working example per task; do not show every alternative
- Keep code comments minimal and functional (what, not why-it-exists)
- Target: 50-100 lines of code with brief surrounding explanation

## Core Concepts

### Format and De-identification Decision Tree

```
What is the target format?
├─ NIfTI (analysis) → dcm2niix -z y -b y
│  ├─ Need BIDS layout? → add -f sub-%i_ses-%t_%p, reorganize post-hoc
│  └─ Single series only? → point dcm2niix at series directory directly
└─ DICOM (archive/PACS) → pydicom read/write

De-identification method:
├─ Small cohort (< 100 studies) → pydicom script (remove tags + private + replace UIDs)
├─ Large cohort or regulatory → CTP DicomAnonymizer with Supplement 142 profile
└─ Burned-in pixel PHI risk?
   ├─ US / Secondary Capture / Screenshots → YES: add OCR + pixel masking step
   └─ CT / MR / PT → Usually NO: tag-level de-ID sufficient
```

**DICOM hierarchy.** `Patient → Study → Series → Instance`. A "series" is the atomic unit for conversion — one NIfTI volume typically corresponds to one `SeriesInstanceUID`.

**UIDs are identifiers, not secrets, but they are *linkable*.** Two files sharing a `StudyInstanceUID` came from the same exam. De-identification must replace UIDs (`generate_uid()`) to break linkage across releases.

**Private tags carry PHI.** Vendor-specific tags (odd group numbers) often embed operator notes, patient IDs, or burned-in metadata. Always call `ds.remove_private_tags()`.

**Pixel data can contain PHI too.** Ultrasound frames, secondary captures, and screenshots frequently have burned-in patient name/MRN in the pixels. Tag removal does *not* scrub pixels — run OCR + masking separately when this risk applies.

**Key DICOM tags for geometry and modality:**

| Tag | Name | Purpose |
| --- | --- | --- |
| `(0008,0060)` | Modality | CT / MR / CR / US / PT ... |
| `(0018,0050)` | SliceThickness | mm |
| `(0028,0030)` | PixelSpacing | in-plane spacing `[row, col]` mm |
| `(0020,0032)` | ImagePositionPatient | origin of slice in patient coords |
| `(0020,0037)` | ImageOrientationPatient | row/col direction cosines |

These five tags are sufficient to reconstruct the NIfTI `affine` matrix.

**NIfTI vs DICOM.** NIfTI stores a single 3D/4D volume with one affine; DICOM stores slice-level metadata. Converters (`dcm2niix`) aggregate slices of a series and compute the affine from the tags above.

## Quick Reference

```bash
# Convert
dcm2niix -z y -b y -f %p_%s -o out/ in/

# Skip merging across series (safer)
dcm2niix -z y -b y -m n -f %p_%s -o out/ in/

# Batch anonymization (CTP)
java -jar DAP.jar -p profile.script -i input/ -o output/
```

```python
# Read DICOM
ds = pydicom.dcmread('file.dcm')
ds.PatientName, ds.Modality, ds.pixel_array.shape

# Header-only (fast, no pixels)
ds = pydicom.dcmread('file.dcm', stop_before_pixels=True)

# Anonymize core fields
for t in ['PatientName','PatientID','PatientBirthDate',
          'InstitutionName','ReferringPhysicianName','StudyDate']:
    if t in ds: del ds[t]
ds.remove_private_tags()
ds.StudyInstanceUID  = generate_uid()
ds.SeriesInstanceUID = generate_uid()
ds.SOPInstanceUID    = generate_uid()

# Load NIfTI
img = nib.load('file.nii.gz'); data = img.get_fdata(); aff = img.affine
```

## Common Mistakes

- **Wrong:** Not removing private tags during DICOM de-identification
  **Right:** Always call `ds.remove_private_tags()` as part of the de-identification pipeline
  **Why:** Vendor private tags (odd group numbers) routinely contain PHI that survives standard tag-level scrubbing

- **Wrong:** Keeping original UIDs after anonymization
  **Right:** Replace `StudyInstanceUID`, `SeriesInstanceUID`, and `SOPInstanceUID` with `generate_uid()` for every de-identified file
  **Why:** Original UIDs are linkable back to the source PACS — two files sharing a StudyInstanceUID reveal they came from the same exam

- **Wrong:** Using default dcm2niix merge behavior without verification
  **Right:** Use `-m n` to disable merging, or inspect output file counts against the expected series list
  **Why:** Default merging can combine distinct acquisitions into one NIfTI volume, corrupting the data

- **Wrong:** Ignoring burned-in annotations in pixel data during de-identification
  **Right:** Add an OCR detection and pixel masking step for ultrasound, secondary capture, and screenshot modalities
  **Why:** Tag-level de-identification does not scrub pixels — patient name/MRN burned into the image persists after tag removal

- **Wrong:** Outputting uncompressed `.nii` files from dcm2niix
  **Right:** Always pass `-z y` to dcm2niix for gzipped `.nii.gz` output unless downstream tools explicitly require uncompressed
  **Why:** Uncompressed NIfTI files are 3-5× larger, wasting storage and slowing transfers with no benefit for most pipelines

- **Wrong:** Reading full pixel data when only DICOM headers are needed
  **Right:** Use `pydicom.dcmread(path, stop_before_pixels=True)` for metadata-only scans
  **Why:** Loading pixel arrays for large cohorts wastes memory and time when only tags like Modality, SeriesInstanceUID, or SliceThickness are needed

- **Wrong:** Treating DICOMDIR as a file directory and iterating its entries
  **Right:** Iterate actual `.dcm` files using `Path(input_dir).rglob('*.dcm')` instead
  **Why:** DICOMDIR is an index file with its own structure — it may be incomplete, outdated, or absent; direct file iteration is more reliable

## References

- dcm2niix: Li et al. J Neurosci Methods 2016, https://doi.org/10.1016/j.jneumeth.2016.03.001
- pydicom: https://pydicom.github.io/pydicom/stable/
- BIDS: Gorgolewski et al. Sci Data 2016, https://doi.org/10.1038/sdata.2016.44
- DICOM de-identification: DICOM PS3.15 Annex E, https://dicom.nema.org/medical/dicom/current/output/chtml/part15/chapter_E.html
