# Module 2: Extending & Creating Skills (30 min)

[← Module 1](module-1.md) | [Overview](overview.md) | [Module 3 →](module-3.md)

Goal: make a skill *yours*. You'll add org-specific interpretation rules to a real skill and watch the agent's answer change.

### Design Principles (instructor-led, 8 min)

> ### 📐 Skill Design Principles — keep this open while you build
>
> - **Add what the agent lacks; omit what it already knows.** If the base model gets it right without help, cut it.
> - **Teach procedures, not facts.** Top-tier skills average **19.4 numbered steps**; bottom-tier average **4.3** from our evaluation.
> - **Use exact, niche thresholds.** `REVEL > 0.644 pathogenic` beats `adj.p < 0.05` (the model already knows the latter).
> - **Include decision trees** for reasoning skills — they correlate with the biggest critical-thinking gains.
> - **Prescribe an output format.** This is the primary defense against coherence regression from added content.
> - **Winners vs. losers:** `genomic-variant-interpretation` wins **90%** of head-to-head comparisons; `quantitative-proteomics` wins only **30%** — because the latter recites well-known limma/DEP recipes the model already produces.

---

### Exercise 2.1: Extend imaging-study-design (~15 min)

This is the core hands-on exercise. You'll make `imaging-study-design` more useful for **cohort construction for clinical trials using endoscopic imaging studies** — adding the endoscopic trial-eligibility scoring and endoscopy-specific de-identification rules the skill doesn't yet carry.

> 📎 **Which file do I edit?** Edit the installed copy your agent actually reads: `.claude/skills/imaging-study-design/SKILL.md` (Claude Code) or `.agents/skills/imaging-study-design/SKILL.md` (GitHub Copilot). Do **not** edit the repo's `skills/imaging-study-design/SKILL.md` — `npx skills add` copied the skill, so that source file is not what the agent loads.

**Steps:**

1. Open the installed copy of `imaging-study-design/SKILL.md` for your harness (see the 📎 note above) in your editor.
2. Find the section **`### 4. Imaging biomarker selection by indication`** under "Core Concepts" — its biomarker table covers only MRI/CT/PET and has no endoscopy, no participant-eligibility scoring, and no endoscopy-specific de-identification.
3. Immediately after that section, add a new subsection titled **`### Lab-Specific Endoscopic Trial-Eligibility and De-identification`**.
4. Paste in the **exact** text below:

   ```markdown
   ### Lab-Specific Endoscopic Trial-Eligibility and De-identification

   #### Endoscopic trial-eligibility scoring
   Endoscopic disease-activity instruments gate enrollment and define endpoints in IBD trials. Encode the instrument, its score range, and the cutoff — but only hard-code cutoffs that are standardized; flag the rest as protocol-specific.

   | Instrument | Disease / use | Score range | Encoded cutoff | Note |
   |------------|---------------|-------------|----------------|------|
   | Mayo endoscopic subscore (MES) | UC trial entry | 0–3 | baseline **MES ≥ 2** (moderate-to-severe); improvement = **0 or 1** | graded on the worst-affected mucosa |
   | SES-CD | Crohn's endoscopic activity | 0–56 | **remission 0–2** | trial-entry "active" cutoff is protocol-specific — do not hard-code a single number |
   | UCEIS | UC severity | **3–11** (original 1-based) or **0–8** (modern 0-based) | encode the numbering your CRF uses | same instrument, two conventions; severity bands are not a single fixed standard |
   | BBPS | colonoscopy prep adequacy | 0–9 | **adequate ≥ 6** with each segment **≥ 2** (stricter **≥ 7** variant exists) | gate for an evaluable baseline endoscopy |
   | *Your instrument here* | | | | |

   **Decision rule:** encode the eligibility cutoff for the *exact* instrument and numbering convention on your CRF; never emit a single universal number for cutoffs the field treats as protocol-specific (SES-CD trial-entry activity, UCEIS severity bands). For an endoscopic primary endpoint, require **central blinded reading** — the regulatory expectation for IBD registrational endpoints.

   #### Endoscopy-specific de-identification
   The §3 DICOM de-identification surface assumes MRI/CT/US; endoscopy adds a pixel-overlay problem that header scrubbing cannot touch.

   | Residual-PHI risk | Required handling |
   |-------------------|-------------------|
   | Burned-in identifiers overlaid into endoscopy pixels (name / MRN / DOB / exam date / institution) | Header scrubbing alone is insufficient — crop/black-box or OCR-driven pixel redaction |
   | `BurnedInAnnotation` tag (0028,0301), values YES/NO | Do **not** trust the flag to decide whether to scrub — it is frequently absent, empty, or wrong; inspect or OCR the pixels regardless |
   | De-identification profile | Apply **DICOM PS3.15 Annex E** Basic Application Level Confidentiality Profile **+ the Clean Pixel Data Option** |
   | Longitudinal linkage across a subject's exams | Use the PS3.15 **"Retain Longitudinal Temporal Information with Modified Dates Option"** (consistent date-shift) plus a secured pseudonym crosswalk (HIPAA §164.514(c) re-id code) |
   | *Your rule here* | |
   ```

5. **Save** the file.
6. Test the modification. With your **edited** skill active, ask:
   ```
   I'm writing endoscopic entry criteria for a moderate-to-severe ulcerative colitis trial using the Mayo endoscopic subscore (MES), with UCEIS as a secondary measure. What MES cutoff should patients meet at baseline, and what UCEIS score range should I put on the CRF?
   ```
   The agent should now cite your encoded **baseline MES ≥ 2** entry cutoff (range 0–3; improvement = 0 or 1) **and** flag that UCEIS has two numbering conventions — **3–11** (original) vs **0–8** (modern) — so the CRF must state which, and that UCEIS severity bands are not universally fixed. Then ask the same question with **no skill active** — the base model will most likely give **MES ≥ 2** correctly but report a **single** UCEIS range (usually 0–8) without surfacing the dual-numbering ambiguity.
7. Validate the skill structure (no AWS needed). First set up the validator — a one-time Python 3.12 virtual environment with the repo's dev dependencies — then run it against the skill you just edited:
   ```bash
   uv venv --python 3.12 && source .venv/bin/activate
   uv pip install -e ".[dev]"
   python tests/validate_skill.py --skill imaging-study-design
   ```
   This checks frontmatter, ≤500 lines, required sections, ≥12 trigger keywords, and reasoning-skill decision-tree content. (Skip the first two lines on later runs — the venv persists for the rest of the workshop.)

How you pick up your edit and toggle the skill off for the baseline depends on your harness:

<details>
<summary><b>Claude Code</b></summary>

Claude Code re-reads `SKILL.md` from `.claude/skills/` automatically, so just save and ask again in the same session (no reload, no restart). **Verify:** re-run the prompt from step 6 and confirm the agent now surfaces your encoded **MES ≥ 2** cutoff and the UCEIS **3–11 vs 0–8** dual-numbering caveat. For the no-skill baseline, ask in a **separate** session started **outside the repo**.

</details>

<details>
<summary><b>GitHub Copilot</b></summary>

After saving, run `/skills reload` to re-read the edited file in the current session (no restart needed), then invoke `/imaging-study-design` again. **Verify:** re-run the prompt from step 6 and confirm the agent now surfaces your encoded **MES ≥ 2** cutoff and the UCEIS **3–11 vs 0–8** dual-numbering caveat. For the no-skill baseline, ask the same question in a **separate** session where the skills are **not** installed (or a prompt that doesn't name the skill) — Copilot auto-discovers from the description, so the baseline must avoid triggering the skill.

</details>

**What to look for:**

- **With your edit:** the agent cites **MES ≥ 2** for entry and **explicitly flags the UCEIS 3–11 vs 0–8 numbering split**, and declines to hard-code UCEIS severity bands as if universal.
- **Without the skill:** the base model will **likely still get MES ≥ 2 right** — that cutoff is well documented — but it tends to report a **single** UCEIS range and may present severity bands as a fixed standard, missing the dual-numbering gotcha your CRF depends on.
- The difference is your encoded domain discipline — the exact numbering convention and which cutoffs are protocol-specific — not a wrong-vs-right flip on the headline number. That last-mile specificity is the value proposition of a customizable skill.

> ⚠️ **Gotcha:** If the agent still reports a single UCEIS range (or asserts fixed severity bands) *with* your edit in place, check that (a) you saved the file, (b) the agent actually re-read it (Claude Code re-reads automatically; GitHub Copilot picks it up after `/skills reload`), and (c) your tables landed in the right section. A stale copy of the skill is the most common cause.

---

### Exercise 2.2: Preview — Creating a Skill from Scratch (instructor walkthrough, 4 min)

The instructor walks through the `pharmacovigilance-signal-detection` example in `CUSTOMIZING.md` as a template — but the shape is identical for any life-sciences domain.

**The frontmatter contract (all 5 fields required):**

```yaml
---
name: your-skill-name              # kebab-case, unique, matches directory
description: >                     # 2-3 sentences + ≥12 quoted trigger phrases
  ... "trigger one", "trigger two", ... "trigger twelve" ...
usage: Invoke when ...             # one-line trigger instruction
version: 1.0.0                     # semver
tags: [skill, category:reasoning, <domain>, hcls]   # first tag literally "skill"
---
```

> These five fields are the base contract every skill in this repo uses. Harnesses tend to require even less — GitHub Copilot, for example, only needs `name` and `description` in the frontmatter, and no separate config file — but keeping all five keeps a skill portable across every harness this repo targets.

**The body shape:**

`Purpose` → `Response Format` → numbered procedure (with decision branches) → threshold table → `Gotchas`.

> 🎯 **This is your Module 3 take-home stretch goal.** Two skills worth building for **cohort construction in endoscopic-imaging trials**, both adjacent to the (reasoning-only) skill you just extended:
> - **`endoscopy-pixel-deid`** (pipeline) — encode the endoscopy burned-in-PHI workflow: OCR/inspect every frame because the `BurnedInAnnotation` (0028,0301) flag is unreliable, apply the PS3.15 Clean Pixel Data Option, and preserve longitudinal linkage with the date-shift option plus a pseudonym crosswalk — operational steps a general model under-specifies.
> - **`ibd-endoscopic-endpoint-scoring`** (reasoning) — encode per-instrument eligibility and endpoint logic (MES, the UCEIS 3–11 vs 0–8 numbering split, SES-CD remission, BBPS adequacy) plus the central-blinded-reading expectation, flagging which cutoffs are protocol-specific rather than universal — judgment a general model flattens into one confident number.

### Troubleshooting

- **`validate_skill.py` fails** → ensure you are on Python 3.12+ and that `uv pip install -e ".[dev]"` completed without errors. Confirm your venv is activated. 

---

### Module 2 Debrief (3 min)

1. Did your edit change the agent's answer — did it surface the **UCEIS 3–11 vs 0–8 numbering split** (and hold **MES ≥ 2** for entry), where the unedited agent gave a single range?
2. What **study-specific threshold or protocol** would you add next — a **BBPS ≥ 6** adequacy gate for an evaluable baseline endoscopy, a central-blinded-reading SOP, or an endoscopy pixel-redaction rule?
