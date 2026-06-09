---
name: imaging-study-design
description: Reasoning skill for medical imaging study design and biomarker selection. Use when the user asks to plan an imaging study, choose a preprocessing strategy, select an imaging biomarker, design a radiomics pipeline, handle DICOM de-identification, plan longitudinal imaging analysis, or pick a registration target. Triggers include "imaging study", "preprocessing strategy", "DICOM de-identification", "imaging biomarker", "radiomics", "longitudinal imaging", "registration target", "MNI vs native space", "scanner harmonization", "ComBat", "IBSI", "multi-site imaging", "burned-in PHI", "test-retest reliability", "volumetric biomarker", "diffusion MRI", "perfusion imaging", "fMRI study design", "spectroscopy biomarker".
usage: Invoke when planning an imaging study, choosing preprocessing strategies, selecting imaging biomarkers, or designing radiomics pipelines.
version: 1.0.0
tags: [skill, category:reasoning, medical-imaging, study-design, biomarker, radiomics, hcls]
---

# Imaging Study Design and Biomarker Selection

## Overview

This skill encodes methodology for designing medical imaging studies and selecting imaging biomarkers. It guides decisions about preprocessing, registration targets, de-identification, biomarker choice, radiomics stability, and multi-site harmonization. It is a reasoning skill — it does not generate pipeline code. For concrete tooling (FreeSurfer, FSL, ANTs, PyRadiomics, nnU-Net, MONAI), pair this skill with a pipeline skill after the study design is settled.

The central principle: **preprocessing and biomarker choice must preserve the signal that answers the clinical question**. A pipeline that is standard for one question (e.g., MNI registration for group comparison) can destroy the signal for another (e.g., individual atrophy in longitudinal studies).

## Usage

Invoke this skill when planning an imaging study or critiquing an existing imaging pipeline. Typical prompts:

- "I want to measure hippocampal atrophy over 2 years in Alzheimer's patients — how should I preprocess?"
- "Design a multi-site radiomics study for NSCLC prognosis."
- "We're collecting brain MRI across three scanners. What harmonization do I need?"
- "Is it safe to share these DICOMs after standard de-identification?"
- "Which imaging biomarker should I use for presurgical mapping in epilepsy?"

Use the Decision Framework at the end of Core Concepts to structure any imaging study question.

## Response Format

- Lead with the direct recommendation or classification (≤3 sentences)
- Structure as: recommendation → justification (citing specific criteria/thresholds) → caveats
- Use tables for comparisons; bullet points for criteria lists
- Omit background the user already knows — they asked the question
- Target: 200-400 words unless the user requests exhaustive detail
The decision trees and frameworks in this skill are for internal reasoning only. Apply them to reach your conclusion, but do not reproduce them in your response. Present only the final recommendation with supporting evidence.


## Core Concepts

### 1. Preprocessing strategy is downstream-goal-dependent

There is no universal "preprocess MRI" recipe. The pipeline must match the analysis target.

| Downstream goal | Preprocessing priorities | What to avoid |
| --- | --- | --- |
| Group comparison (cross-sectional) | Register to common template (MNI/SPM), smooth, modulate if VBM | Native-space-only analysis |
| Longitudinal atrophy / change | Rigid register follow-ups to subject baseline, then (optionally) baseline to template | Registering each timepoint independently to MNI |
| Lesion segmentation | Bias field correction, skull strip, intensity normalization; registration often optional | Aggressive smoothing that blurs lesion edges |
| Radiomics / texture | Standardize acquisition first (voxel size, reconstruction, binning); resample to isotropic; discretize intensity deterministically | Mixing protocols without harmonization; default-bin radiomics on heterogeneous data |
| Functional MRI | Slice-timing (if long TR), motion correction, distortion correction, coregister to anatomical, normalize if group, bandpass filter as appropriate | Normalizing before motion scrubbing; smoothing before ICA denoising |
| Diffusion MRI | Denoise, Gibbs unringing, eddy + motion correction, bias correction, then tensor/ODF fitting | Reordering these steps; skipping distortion correction when reverse-PE is available |

### 2. Registration target decisions

The registration target encodes an assumption about where the signal lives.

- **MNI / population template** — for cross-sectional group statistics, voxelwise analyses (VBM, TBSS), atlas-based ROI extraction. Accepts that individual anatomy is partly warped away.
- **Subject baseline (within-subject template)** — for longitudinal analyses of change (atrophy, tumor growth, lesion evolution). Preserves each subject's anatomy and measures change in a consistent individual frame.
- **Native space** — for lesion analysis, surgical planning, radiomics on tumors, any case where registration would deform the structure of interest or introduce interpolation artifacts in the ROI.
- **Subject anatomical (T1)** — for within-subject cross-modal alignment (fMRI, DWI, PET to T1) before any group normalization.

Heuristic: ask "if I warp this image, do I still measure the thing I care about?" If the answer is no (volume change, lesion shape, tumor texture), keep the measurement in native or within-subject space.

### 3. DICOM de-identification risk surface

Standard tag-based de-identification (DICOM PS 3.15 Basic Application Level Confidentiality Profile) is necessary but not sufficient. Residual PHI risks:

- **Burned-in annotations in pixel data** — ultrasound frames, screen captures, secondary captures, dose reports, 3D reformats. Patient name/MRN/DOB is often rendered into the pixels. Tag-level scrubbing does not remove this. Requires visual QC or OCR-based pixel redaction.
- **Private tags by manufacturer** — Siemens CSA headers (`0029,xx10` / `0029,xx20`) may contain protocol and sometimes patient info; GE private blocks (e.g., `0043,xx`) and Philips MR private tags can hold acquisition metadata that includes identifiers or free-text. Default DICOM profiles may retain or only partially scrub these. Decide per-vendor: strip all private tags unless a specific block is needed, and validate.
- **Structured reports (SR) and encapsulated PDFs** — narrative findings often contain patient name, referring physician, dates, prior history. Must be treated as free-text and redacted or dropped.
- **UIDs encoding dates or MRNs** — some sites generate Study/Series/SOP Instance UIDs from timestamps or record numbers. Rewrite UIDs with a consistent hash (preserving referential integrity within the release) rather than leaving originals.
- **Facial reconstructability from head MRI/CT** — high-resolution T1/CT allow face re-rendering. Apply defacing (e.g., remove or deform voxels around the face) for public release; consider skull-stripping for research-only shares.
- **Acquisition dates and times** — even after name removal, exact dates can re-identify when combined with auxiliary data. Date-shift per subject with a preserved offset if relative timing matters.

A defensible de-identification plan specifies: which profile is applied, how private tags are handled, whether pixel data is inspected, how SR/PDF objects are handled, UID remapping strategy, defacing policy, and a QC sample checked by a human.

### 4. Imaging biomarker selection by indication

Match the biomarker to the biology being probed.

| Indication | Modality / contrast | Biomarker | Rationale |
| --- | --- | --- | --- |
| Alzheimer's disease, MCI | Structural T1 MRI | Hippocampal volume, cortical thickness, ventricular volume | Measures neurodegeneration directly |
| Multiple sclerosis | T2/FLAIR + T1 | Lesion load, lesion count, brain parenchymal fraction, cord area | Disease burden and atrophy |
| White matter disease, DAI, schizophrenia | Diffusion MRI | FA, MD, RD, AD (tract-based or voxelwise) | Microstructural integrity |
| Acute stroke | DWI + PWI | DWI lesion volume, PWI-DWI mismatch, CBF | Core vs penumbra triage |
| Brain tumor (glioma) | DSC/DCE perfusion, MRS, diffusion | rCBV, Ktrans, ADC, NAA/Cho ratio | Grade, treatment response, pseudoprogression vs recurrence |
| Presurgical planning (epilepsy, tumor) | Task and resting-state fMRI, DTI tractography | Language/motor activation maps, tract-to-lesion distance | Functional localization |
| Neuronal integrity (various) | 1H-MRS | NAA/Cr, Cho/Cr, mI/Cr | Metabolic markers of neuronal loss, membrane turnover |
| Oncology outside brain | CT, PET/CT, mpMRI | Volumetry, SUVmax/SUVpeak, radiomic signatures, ADC | Staging, response (RECIST, PERCIST) |
| Cardiac | Cine, LGE, T1/T2 mapping | EF, strain, LGE burden, native T1, ECV | Function, fibrosis, edema |

Selection criteria: (1) biological plausibility — is this biomarker mechanistically linked to the question? (2) measurability — does the available scanner/protocol yield adequate SNR and reliability? (3) validity — has it been validated for this indication and this population? (4) practicality — can it be obtained within the study's scan time and cost?

### 5. Radiomics stability and sample-size discipline

Radiomics features are notoriously unstable. A signature built on unstable features will not generalize.

- **Test-retest reliability** — require ICC ≥ 0.75 (commonly ICC ≥ 0.9 for high confidence) on repeat scans for any feature entering the model. Use a test-retest cohort or a publicly available one (e.g., RIDER Lung CT) aligned to the modality.
- **IBSI compliance** — use an IBSI-compliant extractor (PyRadiomics with IBSI settings, CERR, LIFEx) and report IBSI feature definitions and hash. Non-compliant extractors produce features that cannot be reproduced across sites.
- **Segmentation robustness** — evaluate inter-rater and intra-rater ICC for feature values under realistic contour variability, not just ideal contours.
- **Acquisition standardization first** — fixing voxel size, reconstruction kernel, and intensity discretization (fixed bin width vs fixed bin count — choose one and justify) eliminates more variance than any post-hoc harmonization.
- **Harmonization** — apply ComBat (or its variants: parametric/non-parametric, with or without covariate preservation) to remove scanner/site effects after acquisition standardization, not as a substitute for it.
- **Feature reduction before modeling** — cluster redundant features (|ρ| > 0.8), drop unstable features, then apply a supervised reducer (LASSO, mRMR) inside cross-validation. Cap the final model at roughly **1 feature per 10 events** (EPV ≥ 10) to avoid overfitting. For low-event studies, report this constraint explicitly; it often means choosing 3–5 features, not 20.
- **Report a TRIPOD- or CLEAR-style pipeline description** so the study is reproducible.

### 6. Multi-site study considerations

Multi-site studies trade statistical power for between-site heterogeneity. Plan for the heterogeneity.

- **Protocol standardization** — adopt ADNI-style or equivalent harmonized protocols (sequence parameters, resolution, coverage, reconstruction). Agree on inclusion criteria for scanner models and software versions.
- **Scanner and coil effects** — fixed by protocol where possible, residual effects modeled with ComBat or linear mixed models (site as random effect). A traveling phantom (one subject or a physical phantom scanned at all sites) quantifies residual bias.
- **QC metrics, scored per scan** — SNR, CNR, motion (e.g., FD for fMRI, Euler number for FreeSurfer T1 QC), ghosting, coverage, geometric distortion. Define pre-specified exclusion thresholds before the analysis starts, not after.
- **Central vs local processing** — central processing removes local pipeline variance; local processing with a harmonized Docker/Singularity container is acceptable if the container is version-pinned.
- **Reader variability** — for any human-in-the-loop step (segmentation, lesion counting, BI-RADS), use ≥ 2 readers on a sample, report Cohen's κ or ICC, and adjudicate disagreements with a predefined rule.
- **Analysis plan** — pre-register the statistical model. Decide in advance whether site is a fixed effect (few sites, stable) or random effect (many sites, generalization target), and whether ComBat is applied at feature level or image level.

### 7. Decision framework — apply to every imaging study

Before writing a single line of pipeline code, answer four questions:

1. **What is the clinical question?** — Screening, diagnosis, staging, prognosis, treatment response, mechanism? The question determines the endpoint and the acceptable error profile.
2. **What modality and contrast answers it?** — Match biology to physics (see §4). If multiple modalities answer it, pick the one with the best cost/benefit and existing validation for the indication.
3. **What preprocessing preserves the signal of interest?** — Work backward from the measurement. If the measurement is volume change, preserve individual anatomy. If it is group-level activation, register to a template. If it is texture, standardize acquisition and avoid interpolation across the ROI.
4. **What confounds must be controlled?** — Age, sex, scanner, site, coil, software version, motion, time of day, medication, scan quality. List them explicitly, decide which are in the model, which are excluded by design, and which are acknowledged as limitations.

If any of the four is unclear or contested, resolve it before building the pipeline. Most imaging study failures are failures of step 1 or 3, not failures of the tool.

## When NOT to Use This Skill

- Selecting imaging protocols for individual patient diagnosis (clinical radiology)
- When regulatory submission requires qualified imaging CRO oversight
- Real-time image interpretation or radiological reporting

## When to Escalate to a Human Expert

- Multi-site harmonization decisions affecting primary endpoints
- When imaging biomarker will serve as surrogate endpoint in a trial
- Scanner-specific protocol optimization requiring vendor expertise

## Common Mistakes

- **Wrong:** Registering each longitudinal timepoint independently to MNI
  **Right:** Build a within-subject template or rigidly register follow-ups to baseline first; only then normalize to MNI if needed
  **Why:** Subject-specific atrophy is absorbed into the warp field and the longitudinal change signal is lost

- **Wrong:** Relying solely on tag-based DICOM de-identification
  **Right:** Include pixel inspection, private-tag policy, SR/PDF handling, UID remapping, and defacing in the de-identification plan
  **Why:** Burned-in PHI in pixels, private tags, SR/PDF narratives, and date-encoded UIDs all survive a naive tag-level scrub

- **Wrong:** Building a radiomics model using features with test-retest ICC < 0.75
  **Right:** Filter features by ICC ≥ 0.75 (preferably ≥ 0.9) and by segmentation robustness before any supervised selection
  **Why:** Unstable features poison reproducibility — signatures built on them will not generalize to external cohorts

- **Wrong:** Ignoring scanner/site effects in multi-site imaging studies
  **Right:** Standardize protocols, apply ComBat or mixed-effects modeling, include site as a covariate, and pre-register the analysis plan
  **Why:** Site confounding can fully explain apparent biological effects, producing false-positive findings

- **Wrong:** Fitting dozens of radiomics features to a dataset with few outcome events
  **Right:** Enforce EPV ≥ 10 (events per variable), use nested cross-validation, and report external validation
  **Why:** Over-fitting produces signatures that appear strong internally but fail completely on any external cohort

- **Wrong:** Choosing an imaging biomarker by convenience rather than biological relevance
  **Right:** Run the Decision Framework (question → modality → biomarker) — the biomarker should be mechanistically linked to the clinical question
  **Why:** Using whole-brain volume when the question is hippocampal atrophy, or ADC when the question is perfusion, measures the wrong thing

- **Wrong:** Deciding QC exclusion thresholds after seeing the analysis results
  **Right:** Pre-specify QC metrics and exclusion thresholds before analysis; report inclusion/exclusion counts transparently
  **Why:** Post-hoc threshold selection biases the study toward desired results

- **Wrong:** Smoothing or interpolating through a lesion or tumor ROI
  **Right:** Keep ROI-based measurements in native space, or use lesion-filling / cost-function masking before template normalization
  **Why:** Smoothing across lesion boundaries corrupts texture features and blurs lesion edges, invalidating radiomics and lesion-aware analyses

## References
- IBSI: Zwanenburg et al. Radiology 2020, https://doi.org/10.1148/radiol.2020191145
- ADNI protocol: https://adni.loni.usc.edu/methods/mri-tool/mri-analysis/
- ComBat harmonization: Fortin et al. NeuroImage 2018, https://doi.org/10.1016/j.neuroimage.2017.11.024
