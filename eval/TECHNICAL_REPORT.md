# Evaluating Domain-Specific Agent Skills for Healthcare and Life Sciences: A Pairwise Comparison Study

## Abstract

We evaluate whether loading domain-specific reasoning and pipeline skills into an AI coding assistant (Kiro CLI) improves response quality for healthcare and life sciences (HCLS) questions. Using 410 test prompts spanning 12 HCLS domains, we compare responses generated with and without 38 domain skills using a pairwise LLM-as-judge methodology with randomized position assignment. Claude Opus 4.7 serves as the judge, scoring responses on five dimensions: scientific accuracy, coherence, relevance, critical thinking, and actionability. Skills win **69.5%** of head-to-head comparisons (overall Cohen's d = 0.39, small-medium effect). The strongest effect is on critical thinking (78% win rate, d = 0.65, medium-large), confirming that skills' primary value is teaching the agent *how to think* about domain problems. We find a strong negative correlation (r = -0.59) between baseline response quality and skill benefit — the improvement is most pronounced when the base model produces weaker responses and diminishes as baseline quality increases, though well-designed reasoning skills still improve strong baselines (cross-domain: 80% win rate at baseline 90.2). Reasoning skills that encode decision frameworks outperform pipeline skills that encode tool commands (74% vs 65% win rate). Skills also reduce response variance by up to 51%, making outputs more consistently reliable.

## 1. Introduction

Large language models demonstrate broad competence across scientific domains but exhibit inconsistent performance on specialized tasks requiring precise methodology, tool-specific parameters, or domain-specific decision frameworks. In healthcare and life sciences, errors in variant classification criteria, study design choices, or clinical data standards can have downstream consequences for research validity and patient safety.

Agent skills — structured knowledge documents loaded into an AI assistant's context — represent one approach to injecting domain expertise without model fine-tuning. Skills encode two types of knowledge: (1) **reasoning skills** that teach methodology, decision frameworks, and common pitfalls; and (2) **pipeline skills** that encode tool-specific commands, parameters, and code patterns.

This study evaluates 38 HCLS skills across 12 domains to determine: (a) whether skills measurably improve response quality, (b) which dimensions of quality benefit most, (c) under what conditions skills provide the greatest value, and (d) whether reasoning skills and pipeline skills differ in their impact.

## 2. Methodology

### 2.1 Skill Corpus

The evaluation covers 38 skills organized into 12 domains:

| Domain | Skills | Type Split |
|---|---|---|
| Genomics | 4 | 1 reasoning, 3 pipeline |
| Single-Cell Analysis | 4 | 1 reasoning, 3 pipeline |
| Medical Imaging | 4 | 1 reasoning, 3 pipeline |
| Protein Structure | 3 | 1 reasoning, 2 pipeline |
| Cross-Domain | 3 | 3 reasoning |
| Pharmacoepidemiology | 2 | 1 reasoning, 1 pipeline |
| Clinical Data | 2 | 1 reasoning, 1 pipeline |
| Drug Discovery | 2 | 1 reasoning, 1 pipeline |
| Proteomics | 2 | 1 reasoning, 1 pipeline |
| Clinical Data Review | 2 | 1 reasoning, 1 pipeline |
| Multi-Omics | 2 | 1 reasoning, 1 pipeline |
| Healthcare Operations | 8 | 4 reasoning, 4 pipeline |

Total: 17 reasoning skills, 21 pipeline skills.

### 2.2 Test Prompt Generation

410 test prompts were generated using Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-6`) via Amazon Bedrock:
- 380 single-skill prompts (10 per skill, varying difficulty: 3 easy, 4 intermediate, 3 hard)
- 30 cross-skill prompts (10 per combination for 3 multi-skill scenarios)

Each prompt is self-contained, providing sufficient context for a complete response without clarification. Prompts include realistic fictional data (patient counts, gene names, specific parameters) and request multiple concrete deliverables.

### 2.3 Response Generation

Two conditions were evaluated:
- **Baseline:** Kiro CLI invoked from a clean temporary directory with no skills available
- **Skills:** Kiro CLI invoked with an agent configuration loading all 38 skills via `skill://` resource URIs

Both conditions use the same underlying model (auto-selected by Kiro CLI). Responses were cached to ensure identical prompts across conditions. Timeout: 1200 seconds per invocation.

### 2.4 Judging Protocol

We employ pairwise comparison with the following design:

- **Judge model:** Claude Opus 4.7 (`us.anthropic.claude-opus-4-7`) via Amazon Bedrock
- **Presentation:** Both responses shown in a single judge call as "Response A" and "Response B"
- **Position randomization:** 50% probability that baseline is presented as A (and skills as B), or vice versa. This controls for position bias.
- **Sanitization:** Tool-call artifacts (file reads, thinking logs, skill paths) are stripped from both responses before judging. The judge cannot identify which condition produced which response.
- **Scoring:** Five dimensions, each 0-100, plus a forced winner declaration (A, B, or tie)

### 2.5 Scoring Dimensions and Metrics

| Dimension | Definition |
|---|---|
| Scientific Accuracy | Correctness of facts, mechanisms, citations, domain knowledge |
| Coherence | Logical structure, clear reasoning chain, internal consistency |
| Relevance | Addresses all parts of the prompt, appropriate depth, stays on topic |
| Critical Thinking | Challenges assumptions, identifies limitations, considers alternatives |
| Actionability | Provides concrete next steps, specific parameters, runnable commands |

**Note on metrics:** The judge scores each response on a 0-100 scale per dimension. However, LLM judges exhibit score compression — scores cluster in the 78-96 range, making raw deltas (e.g., +1.5) difficult to interpret. We therefore report two primary metrics:

- **Win rate:** Percentage of prompts where the skills condition scored higher than baseline. Intuitive and robust to scale compression.
- **Cohen's d:** Effect size (mean delta / pooled standard deviation). Measures how large the improvement is relative to natural variance. Benchmarks: 0.2 = small, 0.5 = medium, 0.8 = large.

Raw deltas are reported as a secondary reference.

### 2.6 Statistical Analysis

- Per-skill win rates and Cohen's d computed from paired observations (same prompt, both conditions)
- Correlation between baseline strength and skill benefit assessed via Pearson r
- Skill activation detected by parsing response text for explicit skill file reads

## 3. Results

### 3.1 Overall Effect

| Metric | Value |
|---|---|
| Prompts evaluated | 410 |
| Skills win rate | **69.5%** (285/410) |
| Baseline win rate | 29.5% (121/410) |
| Ties | 1.0% (4/410) |
| Cohen's d (overall) | **0.39** (small-medium) |

### 3.2 Per-Dimension Results

| Dimension | Win Rate | Cohen's d | Interpretation | Delta |
|---|---|---|---|---|
| Critical Thinking | **78.0%** | **0.65** | Medium-large | +3.4 |
| Actionability | 68.0% | 0.37 | Small-medium | +1.7 |
| Scientific Accuracy | 69.3% | 0.34 | Small-medium | +1.7 |
| Relevance | 55.6% | 0.32 | Small-medium | +0.9 |
| Coherence | 54.9% | -0.08 | Negligible | -0.4 |

Critical thinking shows the largest effect (d = 0.65, medium-large). Coherence shows negligible regression (d = -0.08).

### 3.3 Skill Activation

Skills were explicitly loaded (detected via file read operations) on 337/410 prompts (82%). When filtering to only activated prompts, the win rate increases to approximately 74%.

### 3.4 Effect by Domain

| Domain | N | Win Rate | Cohen's d | Delta | Insight |
|---|---|---|---|---|---|
| Clinical Data | 20 | **75%** | **0.52** | +2.6 | Niche knowledge (HL7v2, MedDRA hierarchy). Largest variance reduction (6.8→3.3). |
| Multi-Omics | 20 | 70% | 0.48 | +2.3 | Integration strategy decisions the base model gets wrong. |
| Pharmacoepidemiology | 30 | 67% | 0.44 | +2.0 | Causal inference methodology (immortal time bias, target trial emulation). |
| Imaging | 40 | **75%** | 0.43 | +2.0 | Tool-specific flags and DICOM de-ID rules where base model makes silent errors. |
| Genomics | 50 | 72% | 0.41 | +1.9 | ACMG/AMP criteria the base model approximates but doesn't apply precisely. |
| Healthcare Ops | 80 | 71% | 0.32 | +1.6 | Regulatory-specific knowledge. Inconsistent activation across 8 skills. |
| Cross-Domain | 30 | **80%** | 0.38 | +1.6 | Highest win rate. T0-T4 framework improves even strong baselines. |
| Drug Discovery | 30 | 77% | 0.35 | +1.5 | Evidence hierarchy and translatability framework add structure. |
| Protein Structure | 30 | 67% | 0.18 | +0.8 | Negligible effect. Base model already knows these tools well. |
| Single-Cell | 40 | 65% | 0.16 | +0.8 | Low activation rate drags down average. Trigger phrases need work. |
| Proteomics | 20 | 50% | -0.01 | -0.1 | No benefit. Standard methods well-covered in training data. |
| Clinical Data Review | 20 | 50% | -0.05 | -0.4 | No benefit. CDISC standards well-documented. |

### 3.5 Effect by Skill Type

| Type | N | Win Rate | Cohen's d | Crit.Think d |
|---|---|---|---|---|
| Reasoning | 170 | **74%** | 0.38 | **0.69** |
| Pipeline | 210 | 65% | 0.33 | 0.56 |

Reasoning skills win more often and show a larger effect on critical thinking (d = 0.69 vs 0.56).

### 3.6 Effect by Baseline Strength

| Baseline Tier | N | Baseline (m±s) | Skills (m±s) | Delta | Win Rate |
|---|---|---|---|---|---|
| Weak (<80) | 15 | 75.8±4.0 | 84.4±6.3 | +8.7 | **87%** |
| Medium (80-90) | 227 | 86.8±2.5 | 89.1±3.3 | +2.3 | 79% |
| Strong (>90) | 168 | 91.3±1.0 | 91.0±2.5 | -0.3 | 55% |

Pearson correlation between baseline score and delta: **r = -0.59** (p < 0.001).

## 4. Discussion

### 4.1 Baseline Quality Moderates Skill Benefit

The strongest finding is the -0.59 correlation between baseline quality and skill benefit. Skills provide the greatest lift when the base model produces weaker responses (87% win rate for baseline <80) with diminishing returns as quality increases (55% win rate for baseline >90). However, this is not absolute — cross-domain skills achieve an 80% win rate even with a strong baseline (90.2), demonstrating that well-designed reasoning frameworks add value across the quality spectrum. The relationship is one of diminishing returns, not a binary threshold.

### 4.2 Methodology Over Facts

The d = 0.65 effect on critical thinking versus d = 0.34 on scientific accuracy reveals that skills' primary contribution is methodological, not factual. The base model already possesses substantial HCLS knowledge from training. What it lacks is the consistent application of domain-specific decision frameworks — when to challenge a user's premise, which pitfalls to flag, how to structure a validation plan. Reasoning skills that encode these frameworks deliver this value (critical thinking d = 0.69 for reasoning vs d = 0.56 for pipeline skills).

### 4.3 The Coherence Trade-off

The coherence regression is negligible (d = -0.08, 55% win rate — barely above chance). Skill-loaded responses tend to be longer and more structured (following the skill's analytical framework), which can slightly reduce readability. This is a known trade-off in retrieval-augmented generation: injecting context improves accuracy but can fragment the response's natural flow. Mitigation strategies include adding conciseness guidance to skill templates or limiting the number of skills loaded per query.

### 4.4 Variance Reduction

An underappreciated benefit of skills is variance reduction. Across domains, the skills condition shows lower standard deviation than baseline (e.g., clinical-data: 6.8→3.3, a 51% reduction; pharmacoepidemiology: 2.8→1.8, 36%). This means skills make responses more predictably good — reducing the probability of a catastrophically wrong answer even when the average improvement is modest.

### 4.5 Activation Reliability

18% of prompts did not trigger skill activation despite skills being available. This represents unrealized potential — the skill content exists but the model chose not to read it. Skills with low activation rates (scrna-seq-pipeline: 20%, trajectory-analysis: 30%) likely have trigger descriptions that don't match the natural language patterns in the test prompts. Improving skill descriptions and trigger phrases is a high-leverage optimization.

### 4.6 Domain-Specific Observations

Domains where skills provide the most value share a common characteristic: they require precise, non-obvious knowledge that is underrepresented in general training data. Clinical data standards (d = 0.52), multi-omics integration (d = 0.48), and pharmacoepidemiology (d = 0.44) are all areas where the base model produces plausible but imprecise responses. Skills inject the exact decision criteria needed.

Conversely, domains where skills provide no benefit (proteomics d = -0.01, clinical-data-review d = -0.05) involve well-documented standards that are adequately represented in training data. For these domains, the skill content may need to focus on edge cases and common misapplications rather than standard procedures.

### 4.7 Limitations

- **Single model evaluation:** Results are specific to the model auto-selected by Kiro CLI at evaluation time. Different base models may show different skill sensitivity.
- **LLM-as-judge bias:** Despite sanitization and position randomization, the judge (Opus 4.7) may have systematic preferences that correlate with skill-loaded response patterns.
- **Prompt generation bias:** Test prompts were generated by an LLM from skill descriptions, which may favor skill-loaded responses by design.
- **No human validation:** All scoring is automated. Human expert evaluation on a subset would strengthen confidence in the findings.
- **Skill activation detection:** Our heuristic (file read detection) may undercount cases where skills influence behavior through metadata alone without explicit file reads.
- **Score compression:** LLM judges compress scores into a narrow range (78-96), limiting the discriminative power of raw deltas. Win rate and Cohen's d mitigate this but the underlying scores may still miss fine-grained quality differences.

## 5. Conclusion

Domain-specific skills provide a measurable, consistent improvement to AI assistant responses for HCLS questions (69.5% win rate, Cohen's d = 0.39). The improvement is concentrated in critical thinking (78% win rate, d = 0.65) and scientific accuracy (69% win rate, d = 0.34), with negligible coherence cost (d = -0.08). The benefit is most pronounced when the base model would otherwise produce a weaker response (87% win rate for baseline <80), but well-designed reasoning skills still improve responses even at high baselines (cross-domain: 80% win rate at baseline 90.2).

The most effective skills encode decision frameworks and common-mistake checklists (reasoning skills, 74% win rate) rather than tool commands (pipeline skills, 65% win rate). Domains with niche, non-obvious knowledge benefit most (clinical-data d = 0.52, multi-omics d = 0.48). Skills also reduce response variance by up to 51%, making outputs more consistently reliable.

Future work should focus on: (1) selective skill loading based on query difficulty, (2) trigger phrase optimization for low-activation skills, (3) conciseness guidance to mitigate coherence regression, and (4) human expert validation of a representative subset.

## Appendix A: Per-Skill Detailed Breakdown

See `eval/results/report_v3.md` § "Per-Skill Detailed Breakdown" for individual skill tables with win rate and Cohen's d across all 5 dimensions.

## Appendix B: Judging Methodology

### Pairwise Protocol (v3)

Both responses are sent in a single Claude Opus 4.7 call:
- Labeled as "Response A" and "Response B"
- Position randomized (50/50) per prompt to control for position bias
- Tool-call artifacts stripped from both responses (sanitized)
- Judge scores both responses on 5 dimensions (0-100) and declares a winner
- Win rate and Cohen's d derived from the paired 0-100 scores

### Sanitization Rules

The following patterns are removed before judging:
- Tool usage headers (`using tool: thinking`, `Batch fs_read operation`)
- File read operations (`Reading file:`, `Successfully read`)
- Skill file paths (`.kiro/skills/*/SKILL.md`)
- Completion timestamps (`Completed in 0.0s`)
- Summary lines (`operations processed, N successful`)

### Comparison with Alternative Methods

| Method | Win Rate | Cohen's d | Notes |
|---|---|---|---|
| v1: Independent, unsanitized | — | — | Biased — judge sees tool calls |
| v2: Independent, sanitized | — | — | Unbiased but less sensitive |
| v3: Pairwise, sanitized + randomized | 69.5% | 0.39 | Most sensitive, gold standard |

All three methods show a positive skill effect (v1 delta: +1.1, v2: +0.6, v3: +1.5), confirming the benefit is robust to judging methodology.
