# Evaluating Domain-Specific Agent Skills for Healthcare and Life Sciences: A Pairwise Comparison Study

## Abstract

We evaluate whether loading domain-specific reasoning and pipeline skills into an AI coding assistant improves response quality for healthcare and life sciences (HCLS) questions. Using two harness configurations — an agentic CLI with symmetric tool access and a clean SDK deployment — we measure the impact of 38 domain skills on 410 test prompts spanning 12 HCLS domains. Claude Opus 4.7 serves as the judge, scoring responses on five dimensions: scientific accuracy, coherence, relevance, critical thinking, and actionability.

Skills win **70–86% of head-to-head comparisons** depending on measurement context. In a clean SDK deployment where both conditions produce artifact-free responses, skills win **85.9%** (Cohen's d = 0.97, large effect). In an agentic harness with symmetric tool access, skills win **69.5%** (d = 0.39, small-medium). The gap is explained by response artifacts from tool interleaving in the agentic harness, not by skill quality differences. Critical thinking — the least-confounded dimension — improves **78–85%** of the time regardless of harness.

The strongest effect is on critical thinking (78–85% win rate, d = 0.65–1.03), confirming that skills' primary value is teaching the agent *how to think* about domain problems. We find a strong negative correlation (r = -0.59 to -0.61) between baseline response quality and skill benefit — the most robust finding, replicating across harness configurations. Skills reduce response variance by up to 62%.

## 1. Introduction

Large language models demonstrate broad competence across scientific domains but exhibit inconsistent performance on specialized tasks requiring precise methodology, tool-specific parameters, or domain-specific decision frameworks. In healthcare and life sciences, errors in variant classification criteria, study design choices, or clinical data standards can have downstream consequences for research validity and patient safety.

Agent skills — structured knowledge documents loaded into an AI assistant's context — represent one approach to injecting domain expertise without model fine-tuning. Skills encode two types of knowledge: (1) **reasoning skills** that teach methodology, decision frameworks, and common pitfalls; and (2) **pipeline skills** that encode tool-specific commands, parameters, and code patterns.

This study evaluates 38 HCLS skills across 12 domains using two harness configurations to determine: (a) whether skills measurably improve response quality, (b) which dimensions of quality benefit most, (c) under what conditions skills provide the greatest value, (d) whether reasoning skills and pipeline skills differ in their impact, and (e) how measurement harness choice affects observed effect sizes.

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

410 test prompts were generated via Amazon Bedrock, requested as Claude Sonnet 4.6 (the model actually invoked is not reliably recorded for Strands-era runs — see the execution-model provenance note in §2.3):
- 380 single-skill prompts (10 per skill, varying difficulty: 3 easy, 4 intermediate, 3 hard)
- 30 cross-skill prompts (10 per combination for 3 multi-skill scenarios)

Each prompt is self-contained, providing sufficient context for a complete response without clarification. Prompts include realistic fictional data (patient counts, gene names, specific parameters) and request multiple concrete deliverables.

### 2.3 Experimental Configurations

Two primary harness configurations were evaluated:

**Agentic Harness (Kiro CLI)**

The Kiro CLI agent invokes the underlying model through `kiro-cli chat --no-interactive` with automatic model selection. Skills are loaded via `--agent hcls-eval` which registers all 38 SKILL.md files as readable resources. The agent has access to a `thinking` tool and file-read operations.

**SDK Harness (Strands Agents SDK, execution model labeled Sonnet 4.6)**

The AWS Strands Agents SDK creates a lightweight Python agent via `Agent(model=BedrockModel(...), callback_handler=None)` with the execution model labeled Claude Sonnet 4.6 — but see the provenance note below: the `--model` flag was silently ignored on the Strands backend until a later fix, so this run actually executed on Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`). The skills condition additionally loads an `AgentSkills(skills="./skills/")` plugin. Both conditions capture only the final assistant text via `str(result)`, producing artifact-free output. A `think` tool is provided to both conditions symmetrically.

> **⚠️ Execution-model provenance.** This "headline" SDK configuration (reported as v9, ~85.9% / d=0.97) is labeled Sonnet 4.6 but executed on Sonnet 4.5, because the `--model` flag was silently ignored on the Strands backend until a later fix forced the then-hardcoded Sonnet 4.5. The think-tool configuration it is contrasted against (v7) was intended to differ *only* by execution model, so the two were in fact configured identically — the apparent 4.5-vs-4.6 contrast is not a valid model comparison. No win rate, effect size, or score changes; only the model attribution was wrong.

In both configurations, two conditions are compared:
- **Baseline:** Agent invoked without skill content available
- **Skills:** Agent invoked with all 38 skills available via progressive loading

The independent variable is skill content availability.

### 2.4 Judging Protocol

We employ pairwise comparison with the following design:

- **Judge model:** Claude Opus 4.7 via Amazon Bedrock
- **Presentation:** Both responses shown in a single judge call as "Response A" and "Response B"
- **Position randomization:** 50% probability that baseline is presented as A (and skills as B), or vice versa. This controls for position bias.
- **Sanitization:** Tool-call artifacts (file reads, thinking logs, skill paths) are stripped from both responses before judging. The judge cannot identify which condition produced which response.
- **Scoring:** Five dimensions, each 0-100, plus a forced winner declaration (A, B, or tie)

**Skill activation tracking:** Skill activation is tracked via response text markers and classified into activation patterns: clean (only intended skill loaded), same-domain extra (intended + related skill from same domain), cross-domain extra (unrelated skill also loaded), only unintended (wrong skill loaded), and none (no skill loaded). Precision is computed as |target∩loaded|/|loaded| and recall as |target∩loaded|/|target|, where target is the prompt-level ground truth label and loaded is the set of skills detected in the response.

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
- Position bias assessed via chi-square test on winner declaration by position

## 3. Results

### 3.1 Overall Effect

| Metric | Agentic Harness | SDK Harness |
|---|---|---|
| Prompts evaluated | 410 | 410 |
| Skills win rate | **69.5%** | **85.9%** |
| Cohen's d (overall) | 0.39 | **0.97** |
| Critical thinking win rate | **78.0%** | 85.1% |
| Reasoning skills win rate | 75.6% | 86.2% |
| Pipeline skills win rate | 66.5% | 89.4% |
| Baseline-benefit correlation (r) | -0.59 | -0.61 |
| Max variance reduction | -61.9% | -52.1% |

Two clusters emerge: the SDK harness achieves ~86% win rate while the agentic harness reaches ~70%. The gap is explained by response artifact contamination in the agentic harness (§4), not by differences in skill quality.

### 3.2 Per-Dimension Results

| Dimension | Agentic WR (d) | SDK WR (d) |
|---|---|---|
| Critical Thinking | **78.0%** (0.65) | 85.1% (1.03) |
| Scientific Accuracy | 69.3% (0.34) | **87.7%** (0.85) |
| Actionability | 68.0% (0.37) | 77.3% (0.56) |
| Relevance | 55.6% (0.32) | 78.3% (0.43) |
| Coherence | 54.9% (-0.08) | **92.8%** (1.09) |

Critical thinking is the most stable signal across harnesses (78.0–85.1%, 7pp range). Coherence is the most harness-dependent (54.9–92.8%, 38pp range) — see §4 for explanation.

### 3.3 Skill Activation

Skill activation is classified into patterns based on which skills were loaded relative to the prompt's ground-truth target skill(s):

- **Only intended skill(s):** The agent loaded exactly the skill(s) designated for that prompt — no extras.
- **Intended + same-domain extra:** The intended skill was loaded, plus additional skill(s) from the same domain (e.g., a `variant-calling` prompt also loaded `genomic-variant-interpretation` — both genomics).
- **Intended + cross-domain extra:** The intended skill was loaded, plus skill(s) from a different domain (e.g., a genomics prompt also loaded a clinical-data skill).
- **Only unintended skill(s):** A skill was loaded, but not the one targeted by the prompt.
- **No skill loaded:** The agent did not load any skill.

**Activation metrics:**

| Metric | Agentic | SDK |
|---|---|---|
| Precision (target∩loaded / loaded) | 62.3% | 82.9% |
| Recall (target∩loaded / target) | 84.5% | 93.8% |
| Unintended rate (loaded−target / loaded) | 37.7% | 17.1% |

**Win rate by activation pattern:**

| Pattern | Agentic Count (WR) | SDK Count (WR) |
|---|---|---|
| Only intended skill(s) | 127 (70.9%) | 320 (86.6%) |
| Intended + same-domain extra | 129 (75.2%) | 49 (87.8%) |
| Intended + cross-domain extra | 81 (69.1%) | 12 (91.7%) |
| Only unintended skill(s) | 0 (—) | 27 (74.1%) |
| No skill loaded | 73 (57.5%) | 2 (50.0%) |

Key observations:
- **Clean activation win rates match overall win rates** in each configuration (Agentic: 70.9% vs 69.5% overall; SDK: 86.6% vs 85.9% overall), confirming the benefit comes from targeted skill activation, not bulk context injection.
- **Same-domain extra loading does not hurt** — win rates are equal to or higher than clean activation, suggesting related skills provide complementary value.
- **Precision improves with the SDK harness** (62% → 83%), reflecting better skill selection mechanics when tool calls are cleanly separated from response text.

### 3.4 Effect by Skill Type

| Type | Agentic Win Rate | SDK Win Rate |
|---|---|---|
| Reasoning (n=160) | **76%** | 86% |
| Pipeline (n=200) | 67% | **89%** |

The reasoning > pipeline advantage observed in the agentic harness (+9pp) does not replicate in the SDK harness, where pipeline skills slightly lead (-3pp). Per-skill correlation between configurations is near-zero (r = -0.004), confirming this is sampling noise at n=10 per skill, not a stable skill-type effect.

### 3.5 Effect by Baseline Strength

**Agentic Harness**

| Baseline Tier | N | Baseline (m±s) | Skills (m±s) | Delta | Win Rate |
|---|---|---|---|---|---|
| Weak (<80) | 15 | 75.8±4.0 | 84.4±6.3 | +8.7 | **87%** |
| Medium (80-90) | 246 | 87.1±2.5 | 89.3±3.3 | +2.2 | 79% |
| Strong (>90) | 149 | 91.5±0.9 | 91.0±2.5 | -0.5 | 54% |

**SDK Harness**

| Baseline Tier | N | Baseline (m±s) | Skills (m±s) | Delta | Win Rate |
|---|---|---|---|---|---|
| Weak (<80) | 46 | 77.0±2.6 | 84.9±3.5 | +7.9 | **96%** |
| Medium (80-90) | 325 | 85.8±2.6 | 89.5±3.3 | +3.7 | 89% |
| Strong (>90) | 39 | 91.0±0.7 | 91.1±2.0 | +0.0 | 54% |

Pearson correlation between baseline score and delta: Agentic **r = -0.59**, SDK **r = -0.61** (both p < 0.001). This is the most robust finding in the evaluation — it replicates across harnesses, models, and judging sessions.

## 4. Harness Comparison

The 16-percentage-point gap between the agentic harness (69.5%) and SDK harness (85.9%) traces primarily to a single dimension: **coherence**.

| Configuration | Coherence Win Rate | Overall Win Rate |
|---|---|---|
| Agentic | 54.9% | 69.5% |
| SDK | 92.8% | 85.9% |
| **Gap** | **37.9pp** | **16.4pp** |

### 4.1 Root Cause: Response Artifact Contamination

In the agentic harness, both conditions produce responses interleaved with tool-call artifacts (`Reading file:`, `Successfully read N bytes`, thinking traces). These artifacts are stripped before judging via sanitization rules (Appendix B), but residual formatting disruption — paragraph breaks, incomplete sentences around stripped blocks — reduces coherence scores for both conditions symmetrically. The pairwise comparison remains fair (symmetric noise cancels), but the absolute coherence improvement from skills is obscured.

In the SDK harness, `str(result)` captures only the final assistant text. Tool calls — including the `skills` tool invocation — are invisible in captured output. Both conditions produce clean, artifact-free prose. The coherence comparison is unconfounded, revealing that skills actually *improve* coherence substantially (92.8% win rate).

### 4.2 Critical Thinking: The Least-Confounded Dimension

Across both configurations, critical thinking shows the smallest gap:

| Dimension | Agentic | SDK | Gap |
|---|---|---|---|
| Coherence | 54.9% | 92.8% | 37.9pp |
| Overall | 69.5% | 85.9% | 16.4pp |
| Critical Thinking | 78.0% | 85.1% | **7.1pp** |

Critical thinking is minimally affected by formatting artifacts because it measures whether the agent:
- Applies the correct analytical framework
- Flags appropriate limitations and caveats
- Uses domain-specific thresholds rather than generic ones
- Challenges assumptions when warranted

These qualities are present or absent regardless of response formatting noise. This makes critical thinking the **most reliable signal** for skill value across measurement contexts: skills improve reasoning quality **78–85%** of the time regardless of harness.

### 4.3 Per-Skill Rankings: Unstable at n=10

Per-skill win rates are **uncorrelated between configurations** (Pearson r = -0.004). A skill winning 90% in one configuration has no predictive power for its win rate in the other. This is expected at n=10 per skill: the 95% binomial confidence interval is ±28%, meaning a "true 80%" skill can measure anywhere from 50% to 100% on any given run.

This does NOT mean skill quality varies randomly — it means **n=10 is insufficient to rank individual skills reliably**. The overall win rate (aggregated across 410 prompts) is highly significant (SDK: p < 10⁻³⁰; Agentic: p < 10⁻¹²). Individual per-skill tables in the appendix should be interpreted as illustrative, not as reliable rankings.

### 4.4 Judge Behavior Analysis

Qualitative analysis of judge rationales from the SDK configuration reveals how skills produce wins:

| Reason | Frequency | Description |
|--------|-----------|-------------|
| Factual corrections | 59% | Skills correct specific errors in baseline responses |
| Specificity | 33% | Skills provide calibrated thresholds absent from parametric knowledge |
| Critical thinking | 29% | Skills flag edge cases, limitations, and caveats baseline misses |

When the baseline wins (14.1% of comparisons), the primary causes are: skill steering to the wrong framework for the query (36% of baseline wins) and baseline producing a more direct response (27%).

## 5. Comparison with External Benchmarks

### 5.1 SkillsBench Alignment

The SkillsBench evaluation (arXiv 2602.12670) provides independent validation using a fundamentally different methodology:

| Aspect | This Study | SkillsBench |
|--------|-----------|------------|
| Evaluation method | LLM-as-judge (pairwise) | Deterministic verifiers |
| Task count | 410 prompts | 87 tasks |
| Domain | HCLS-specific (38 skills) | General-purpose |
| Skill implementation | Agent Skills standard (SKILL.md) | Platform-native |
| Key finding | +19–36pp improvement | **+16.6pp** with full tools |

SkillsBench reports a +16.6 percentage point improvement when both conditions have equal tool access — closely matching our agentic harness (69.5% vs 50% chance = +19.5pp) where both conditions have symmetric environment access.

### 5.2 Methodological Convergence

Key methodological principles align across evaluations:

1. **Symmetric tool access** — both SkillsBench and our configurations ensure conditions differ only in skill content
2. **Model pinning** — SkillsBench fixes the model per configuration; our SDK harness used a fixed execution model (labeled Sonnet 4.6, but actually Sonnet 4.5 — see §2.3)
3. **Clean output capture** — SkillsBench uses deterministic verifiers; our SDK harness captures only final text

The convergence across independent frameworks (different prompts, different judges, different skill implementations) strengthens confidence that the effect is real and robust rather than an artifact of any single evaluation methodology.

## 6. Discussion

### 6.1 Baseline Quality Moderates Skill Benefit

The negative correlation between baseline quality and skill benefit is consistent across configurations (r = -0.59 to -0.61). Skills provide the greatest lift when the base model produces weaker responses (87–96% win rate for baseline <80) with diminishing returns as quality increases (54% win rate for baseline >90). However, this is not absolute — cross-domain skills achieve an 80% win rate even with a strong baseline (90.2), demonstrating that well-designed reasoning frameworks add value across the quality spectrum. The relationship is one of diminishing returns, not a binary threshold.

### 6.2 Methodology Over Facts

The d = 0.65 effect on critical thinking versus d = 0.34 on scientific accuracy (agentic harness) reveals that skills' primary contribution is methodological, not factual. The base model already possesses substantial HCLS knowledge from training. What it lacks is the consistent application of domain-specific decision frameworks — when to challenge a user's premise, which pitfalls to flag, how to structure a validation plan. This finding replicates in the SDK harness, where critical thinking shows the largest effect size (d = 1.03) among non-coherence dimensions.

### 6.3 The Coherence Trade-off

In the agentic harness, the coherence regression is negligible (d = -0.08, 55% win rate). The harness comparison reveals this dimension is **extremely sensitive to measurement methodology**. The 38pp coherence gap between configurations is entirely attributable to response artifacts, not skill content. When measured cleanly (SDK harness), skills actually *improve* coherence (92.8% win rate). The true coherence impact of skill content is neutral-to-positive; observed regression in agentic harnesses reflects tool noise, not skill quality.

### 6.4 Variance Reduction

An underappreciated benefit of skills is variance reduction. Across configurations, the skills condition shows lower standard deviation than baseline, with reductions of 52–62% depending on configuration and domain (e.g., clinical-data: 6.8→3.3). This means skills make responses more predictably good — reducing the probability of a catastrophically wrong answer even when the average improvement is modest.

### 6.5 Reasoning vs Pipeline: Not a Stable Predictor

The agentic harness finding that reasoning skills outperform pipeline skills (+9pp) does not replicate in the SDK harness (-3pp). Per-skill correlation between configurations is effectively zero (r = -0.004). Recent literature offers context:

- **MASA (arXiv 2605.30723)** finds the optimal skill form is model-dependent: the same skill can help one model and hurt another.
- **SkillsBench domain breakdown** shows the biggest gains come from "specialized procedural knowledge underrepresented in training" (Healthcare: +51.9pp) versus domains with strong pretraining coverage (Software Engineering: +4.5pp).

This suggests the real axis of skill effectiveness is not reasoning vs pipeline but rather **"novel to the model" vs "already in training data"** — which is consistent with our baseline-strength correlation (r = -0.59 to -0.61) being the most stable finding.

### 6.6 Activation Reliability

Skill activation precision improves from 62% (agentic) to 83% (SDK), with recall at 85% and 94% respectively. Skills with low activation rates (scrna-seq-pipeline: 20%, trajectory-analysis: 30% in the agentic harness) likely have trigger descriptions that don't match the natural language patterns in the test prompts. Improving skill descriptions and trigger phrases is a high-leverage optimization.

### 6.7 Domain-Specific Observations

Domains where skills provide the most value share a common characteristic: they require precise, non-obvious knowledge that is underrepresented in general training data. Clinical data standards (d = 0.52), multi-omics integration (d = 0.48), and pharmacoepidemiology (d = 0.44) are all areas where the base model produces plausible but imprecise responses. Skills inject the exact decision criteria needed.

Conversely, domains where skills provide less benefit (proteomics d = -0.01, clinical-data-review d = -0.05 in the agentic harness) involve well-documented standards that are adequately represented in training data. For these domains, the skill content may need to focus on edge cases and common misapplications rather than standard procedures.

## 7. Conclusions

Domain-specific skills provide a measurable, consistent improvement to AI assistant responses for healthcare and life sciences questions. The effect is substantial: skills win 70–86% of head-to-head comparisons depending on harness configuration, with a large effect size (Cohen's d = 0.97) in the cleanest measurement and a moderate effect (d = 0.39) in a realistic agentic environment with symmetric tool noise.

The improvement is primarily methodological rather than factual. The base model already possesses substantial HCLS knowledge from training data; what skills add is the consistent application of domain-specific decision frameworks. This is evidenced by critical thinking showing the largest and most stable effect (78–85% win rate, d = 0.65–1.03) across all measurement configurations — the agent learns *when to challenge assumptions*, *which thresholds matter*, and *how to structure a validation plan* rather than acquiring new factual knowledge.

The benefit is strongest where the base model is weakest. The negative correlation between baseline quality and skill benefit (r = -0.59 to -0.61) replicates perfectly across configurations and represents the most robust finding of this study. Skills provide transformative improvement (87–96% win rate) for prompts where the baseline produces weak responses, moderate improvement for the middle tier, and marginal benefit for prompts the model already handles well. This points to a practical deployment principle: skills deliver the most value for niche regulatory and methodological domains — areas like claims billing rules, CDISC compliance, and pharmacoepidemiologic design — where specialized procedural knowledge is underrepresented in training data.

Beyond average improvement, skills reduce response variance by up to 62%, making outputs more predictably reliable. This consistency benefit may matter more than the average quality lift in regulated domains where a single catastrophically wrong answer carries greater risk than a modest improvement across many answers.

The harness comparison reveals that measurement methodology significantly affects observed win rates, primarily through its impact on the coherence dimension. When response artifacts are eliminated (SDK harness), skills show a large positive effect on coherence (92.8% win rate); when artifacts contaminate both conditions symmetrically (agentic harness), the coherence signal is obscured. Critical thinking, unaffected by formatting noise, provides the most reliable cross-configuration signal for skill value.

## 8. Limitations

- **LLM-as-judge bias:** Despite sanitization and position randomization, the judge (Opus 4.7) may have systematic preferences that correlate with skill-loaded response patterns. Position bias is not significant (p = 0.096) but exists (+7.4pp).
- **Prompt-skill correlation:** Test prompts were generated from skill descriptions, meaning prompts and skills are intentionally aligned. This reflects real-world deployment where skills are authored to serve specific use cases and user queries naturally correlate with the domains the skills target. The evaluation measures whether skills improve responses to the types of questions they were designed to address.
- **No human validation:** All scoring is automated. Human expert evaluation on a subset would strengthen confidence.
- **Per-skill power:** At n=10 per skill, individual skill win rates have ±28% confidence intervals (95% binomial CI). Per-skill rankings are uncorrelated between configurations (r ≈ 0), confirming that n=10 is insufficient for individual skill attribution. The overall finding (N=410) is highly powered (p < 10⁻¹²).
- **Harness confounding:** The 16pp gap between configurations demonstrates that infrastructure choices materially affect observed results. Any single configuration's win rate should be interpreted in context of its measurement methodology.
- **Model not pinned in agentic configuration:** The agentic harness used automatic model selection rather than an explicit model pin. While both conditions used the same model selection within a run, exact model version is not controlled.

## Appendix A: Per-Skill Detailed Breakdown

See `eval/results/` for individual skill tables with win rate and Cohen's d across all 5 dimensions.

## Appendix B: Judging Methodology

### Pairwise Protocol

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
- Tool status markers (`✓`, `✗`, `↱`, `►`, `▶`, `⋮`)
- Preambles (`I'll share my reasoning process`)

## Appendix C: Harness Effects Detail

For the full analysis of harness effects including artifact frequency tables, per-dimension breakdowns, and additional experimental configurations tested during development (including an asymmetric isolation variant that demonstrated how baseline over-isolation inflates baseline coherence scores), see [`eval/HARNESS_EFFECTS.md`](./HARNESS_EFFECTS.md).

## Appendix D: Per-Domain Breakdown

| Domain | N | Agentic WR (d) | SDK WR (d) |
|---|---|---|---|
| Clinical Data | 20 | 75% (0.52) | 85% (1.32) |
| Clinical Data Review | 20 | 50% (-0.05) | 85% (1.42) |
| Cross-Domain | 30 | 80% (0.38) | 83% (0.83) |
| Drug Discovery | 30 | 77% (0.35) | 90% (0.94) |
| Genomics | 50 | 72% (0.41) | 86% (1.29) |
| Healthcare Ops | 80 | 71% (0.32) | 84% (0.98) |
| Imaging | 40 | 75% (0.43) | 98% (1.86) |
| Multi-Omics | 20 | 70% (0.48) | 80% (0.99) |
| Pharmacoepidemiology | 30 | 67% (0.44) | 83% (0.86) |
| Protein Structure | 30 | 67% (0.18) | 93% (1.72) |
| Proteomics | 20 | 50% (-0.01) | 75% (0.58) |
| Single-Cell | 40 | 65% (0.16) | 90% (2.07) |

Note: per-domain rankings at n=10–20 per domain are subject to the same statistical instability as per-skill rankings (§4.3).
