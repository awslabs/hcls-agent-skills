# Customizing Skills

These skills are designed to be modified. Your organization has specific payer rules, formularies, and protocols — encode them here so the agent applies your knowledge consistently. This guide covers three workflows: modifying, extending, and creating skills from scratch.

## Quick Start: Modify an Existing Skill

**Scenario:** Your MAC jurisdiction uses LCD L35936 for lumbar fusion, requiring 6 months of conservative therapy (not the generic 3 months). You want `claims-billing-rules` to reflect this.

**File to edit:** `skills/claims-billing-rules/SKILL.md`

Find the Global Surgery Periods table (or the relevant section) and add your LCD rule. Here's a before/after:

```diff
 ### Global Surgery Periods
 
 | Period | Description | Included Services |
 |---|---|---|
 | 0-day | Minor procedure | Only the procedure day |
 | 10-day | Minor procedure with follow-up | Procedure day + 10 days post-op |
 | 90-day | Major procedure | Procedure day + 90 days post-op |
+
+### Organization-Specific LCD Rules
+
+| LCD | Procedure | Key Requirement | MAC Jurisdiction |
+|---|---|---|---|
+| L35936 | Lumbar fusion (22612) | 6 months conservative therapy documented | JN (Novitas) |
+| L35936 | Lumbar fusion (22612) | MRI within 6 months showing instability | JN (Novitas) |
```

That's it. The agent will now cite your LCD rule when answering lumbar fusion billing questions.

## Extending a Skill

**Scenario:** Your health plan has a custom formulary with step therapy requirements for GLP-1 agonists. You want `pa-clinical-policy` to know your specific rules.

Open `skills/pa-clinical-policy/SKILL.md` and add a new subsection under the clinical criteria section. Follow the existing format — tables for structured data, numbered steps for procedures:

```markdown
### 2.3 Organization Formulary: GLP-1 Agonists

**Step therapy requirement (effective 2025-01):**

1. Patient must have failed metformin ≥ 1500mg/day for ≥ 90 days
2. If HbA1c remains > 7.5% after step 1, approve semaglutide (Ozempic) Tier 3
3. Tirzepatide (Mounjaro) requires prior semaglutide failure or documented GI intolerance
4. Duration: initial auth 6 months, renewal requires HbA1c reduction ≥ 0.5%

**Documentation required:** Lab results (HbA1c within 30 days), medication history, prescriber attestation of prior therapy failure.

⚠️ **Gotcha:** "GI intolerance" requires specific documentation — nausea alone is insufficient. Must document dose titration attempt and impact on daily function.
```

**Where to insert:** After existing numbered sections, before any "Gotchas" or "Common Pitfalls" section at the end. Keep the heading level consistent with siblings.

## Creating a New Skill from Scratch

Here's a complete skill for pharmacovigilance signal detection (~60 lines):

```markdown
---
name: pharmacovigilance-signal-detection                    # kebab-case, unique
description: >                                              # 2-3 sentences, include trigger phrases
  Reasoning skill for pharmacovigilance signal detection and evaluation. Use when the user
  asks about disproportionality analysis, PRR, ROR, EBGM, FAERS signal detection, safety
  signal prioritization, or MedDRA-based case series review. Triggers include "safety signal",
  "PRR", "ROR", "EBGM", "disproportionality", "FAERS", "pharmacovigilance", "signal detection".
usage: Invoke when reasoning about drug safety signal detection, evaluation, or prioritization.
version: 1.0.0                                             # semver
tags: [skill, category:reasoning, pharmacovigilance, hcls] # always include "skill" and category
---

# Pharmacovigilance Signal Detection

## Purpose

Guide the agent through safety signal detection from spontaneous reporting databases,
disproportionality analysis method selection, and signal prioritization for further evaluation.

## Response Format

- Lead with the signal classification or method recommendation (≤3 sentences)
- Structure as: recommendation → method justification → limitations
- Use tables for method comparisons; numbered steps for workflows

## 1. Signal Detection Methods

| Method | Formula | Threshold | Best For |
|--------|---------|-----------|----------|
| PRR | (a/a+b) / (c/c+d) | PRR ≥ 2, chi² ≥ 4, N ≥ 3 | Simple screening, small datasets |
| ROR | (a/b) / (c/d) | Lower 95% CI > 1 | Case-control framing |
| EBGM | Empirical Bayes geometric mean | EB05 ≥ 2 | Large databases (FAERS), handles sparse data |
| IC | Information component (Bayesian) | IC025 > 0 | WHO VigiBase |

## 2. Signal Evaluation Workflow

1. **Detect**: Run disproportionality on drug-event pair
2. **Validate**: Confirm case quality (completeness, duplicates removed)
3. **Assess causality**: Apply Bradford Hill criteria (temporality, dose-response, biological plausibility)
4. **Prioritize**: Rank by seriousness (death > hospitalization > disability), unexpectedness, and public health impact
5. **Act**: Recommend label update, REMS, or further study

## 3. Gotchas

- ⚠️ Notoriety bias: Publicized safety concerns inflate reporting → spurious signals
- ⚠️ Weber effect: Reporting peaks 2 years post-launch then declines regardless of true risk
- ⚠️ Masking/competition: A strong signal for Drug A + Event X can suppress detection of Drug B + Event X
- ⚠️ PRR is unreliable when N < 3 cases — always apply minimum case threshold
- ⚠️ EBGM shrinks toward the prior with sparse data — low EB05 ≠ no signal, just insufficient evidence
```

## Skill Anatomy

### YAML Frontmatter (required)

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | ✅ | Unique kebab-case identifier |
| `description` | ✅ | What it does + trigger phrases for activation |
| `usage` | ✅ | One-line instruction for when to invoke |
| `version` | ✅ | Semver for tracking changes |
| `tags` | ✅ | Must include `skill` and `category:reasoning` or `category:pipeline` |

### Body Sections (conventions)

| Section | Purpose |
|---------|---------|
| Purpose | 2-3 sentences on what the skill teaches |
| Response Format | How the agent should structure its output |
| Numbered sections | Decision procedures, reference tables, workflows |
| Gotchas / Common Pitfalls | Domain traps the agent would otherwise miss |

## Testing Your Changes

Load a single skill in Kiro CLI and test it against representative prompts:

```bash
# Load your modified skill
/context add ~/kiro-skills-hcls/skills/claims-billing-rules/SKILL.md

# Test with a prompt that should trigger the new content
> "Does lumbar fusion 22612 require prior conservative therapy under LCD L35936?"
```

**Compare with and without:** Remove the skill (`/context clear`), ask the same question, then reload and ask again. The skill-loaded response should cite your specific rules and thresholds.

**What to check:**
- Does the agent use your added content (not just generic knowledge)?
- Is the response well-structured (not a wall of text)?
- Does it cite specific thresholds/rules you added?

## Skill Checklist

Before committing your skill, verify:

- [ ] **Frontmatter complete** — all 5 required fields present and valid
- [ ] **Triggers specific** — description includes 5+ trigger phrases users would actually say
- [ ] **Teaches something new** — content the agent would get wrong without help
- [ ] **Has decision procedures** — numbered steps with branch points, not just facts
- [ ] **Includes thresholds** — specific numbers, not vague guidance ("≥ 6 months" not "adequate duration")
- [ ] **Gotchas present** — at least 3 domain-specific traps or common mistakes
- [ ] **Response format defined** — tells the agent how to structure output
- [ ] **Tested with prompts** — loaded locally and verified against 3+ representative questions

## Common Patterns

**Decision tree** — numbered steps with conditional branches:
```markdown
1. Check X
2. If X > threshold → do A
3. If X ≤ threshold → check Y, then do B
```

**Gotcha list** — domain traps marked with warnings:
```markdown
- ⚠️ Common mistake: doing X when you should do Y because of Z
```

**Threshold table** — exact numbers for classification:
```markdown
| Metric | Threshold | Interpretation |
|--------|-----------|----------------|
| PRR | ≥ 2 | Signal detected |
```

**Code recipe** — runnable snippet with parameters:
```markdown
## Variant Filtering
​```bash
bcftools filter -i 'QUAL>30 && DP>10 && AF>0.05' input.vcf.gz -o filtered.vcf.gz
​```
```

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Skill not activating | Trigger phrases in `description` don't match user's wording | Add more trigger synonyms; use the exact phrases your team uses |
| Response too verbose | No `Response Format` section | Add format constraints: word target, structure prescription |
| Content ignored | Skill is too long (>500 lines) or has too many competing tables | Split into focused sub-skills or cut low-value reference material |
| Agent contradicts skill | Skill states something the model "knows" differently | Add explicit "⚠️ Override" markers; be more assertive in wording |
| Wrong skill activates | Trigger phrases overlap with another skill | Make triggers more specific; add "NOT for X" to description |

## Further Reading

See [SKILL_DESIGN_GUIDE.md](./SKILL_DESIGN_GUIDE.md) for deeper structural guidance on skill architecture, content density patterns, and advanced design decisions.
