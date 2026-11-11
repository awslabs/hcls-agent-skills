# Harness Effects on Skill Evaluation Measurements

A supplementary analysis examining how execution harness choice affects measured win rates in the HCLS agent skills evaluation. This document accompanies the main [Technical Report](./TECHNICAL_REPORT.md).

## Summary

The execution harness significantly affects observed win rates — primarily through its impact on the coherence dimension. Two harness families were tested:

- **SDK harness (Strands Agents SDK):** Captures only final assistant text via `str(result)`. Tool calls are invisible in output. Both conditions produce clean, artifact-free prose. Win rate: **85.9%**.
- **Agentic harness (Kiro CLI):** Responses interleaved with tool-call artifacts. Both conditions equally affected when run symmetrically. Win rate: **69.5%**.

The 16-percentage-point gap is explained by response artifact contamination, not by differences in skill quality. Critical thinking — unaffected by formatting noise — shows only a 7pp gap (78% vs 85%), confirming the underlying skill benefit is stable across harnesses.

## Evaluation Design

The evaluation uses pairwise comparison across 410 prompts (380 single-skill, 30 cross-skill) spanning 38 skills and 11 HCLS domains. Each prompt is answered twice — once with skills loaded and once without — under otherwise identical conditions. Claude Opus 4.7 performs blinded pairwise judging on five dimensions. Response position is randomized and both responses are sanitized before judging.

The independent variable is skill content availability. Everything else — model, tools, environment — is held constant within each configuration.

## Configuration Matrix

| Configuration | Backend | Model | Baseline Tools | Win Rate | Cohen's d |
|---|---|---|---|---|---|
| Agentic (symmetric) | Kiro CLI | auto | thinking, file reads | 69.5% | 0.39 |
| SDK (bare baseline) | Strands SDK | Sonnet 4.5 | none | 88.5% | — |
| SDK (think tool) | Strands SDK | Sonnet 4.5 | think tool | 88.0% | — |
| SDK (labeled 4.6) | Strands SDK | Sonnet 4.5 (labeled 4.6) | think tool | 85.9% | 0.97 |

> **⚠️ Execution-model provenance.** The row labeled "Sonnet 4.6" actually executed on **Sonnet 4.5** (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`): the `--model` flag was silently ignored on the Strands backend until a later fix, so every strands run used the then-hardcoded Sonnet 4.5. The two "SDK" rows above (Sonnet 4.5, from hand-entered metadata) and this row were therefore configured identically on the execution model — any difference between them is run-to-run noise, not a model-upgrade effect. Win rates and Cohen's d are unaffected; only the model label was wrong.

Additionally, an asymmetric agentic configuration was tested where the baseline was over-isolated (see §Asymmetric Isolation below). This produced a 64.6% win rate that underestimates skill value.

## The Coherence Gap

The gap between harness families traces primarily to a single dimension: **coherence**.

| Configuration | Coherence Win Rate | Overall Win Rate |
|---|---|---|
| Agentic (symmetric) | 54.9% | 69.5% |
| SDK (labeled 4.6) | 92.8% | 85.9% |
| **Gap** | **37.9pp** | **16.4pp** |

In the agentic harness, both conditions produce responses interleaved with tool-call artifacts (`Reading file:`, `Successfully read N bytes`, thinking traces). Sanitization removes these before judging, but residual formatting disruption — paragraph breaks, incomplete sentences around stripped blocks — reduces perceived coherence for both conditions symmetrically. The pairwise comparison remains fair (symmetric noise cancels), but the absolute coherence improvement from skills is obscured.

In the SDK harness, `str(result)` captures only the final assistant text. The coherence comparison is unconfounded, revealing that skills substantially *improve* coherence (92.8% win rate).

## The Think Tool Has No Measurable Effect

Two SDK configurations form a natural experiment — identical setup except one adds a `think` tool to the baseline:

- Without think tool: 88.5% win rate
- With think tool: 88.0% win rate
- Baseline mean scores identical: 84.7 in both

The think tool is confirmed to be invoked (spot-checked responses show tool calls), but because `callback_handler=None` suppresses streaming output, thinking content never reaches the captured response. The judge sees only final text, which is unaffected.

Despite producing non-identical responses (23% mean text similarity between the two baseline outputs), quality scores are the same. This establishes convergent quality regardless of whether internal deliberation is explicit or implicit.

These configurations also serve as a reproducibility test for the judge: 80% agreement on pairwise verdicts, with symmetric flips (39 reversals in each direction), indicating stable judging without systematic drift.

## SDK AgentSkills: Progressive Loading, Clean Output

The Strands SDK's `AgentSkills` plugin uses a progressive loading mechanism. The system prompt receives only a lightweight XML catalog (~3–4KB) listing available skills with trigger keywords. When the model determines a skill is relevant, it calls the `skills` tool to load the full SKILL.md content into its context.

This is architecturally analogous to the agentic harness's file-read mechanism for skill loading, but with a critical difference: `str(result)` captures only the final assistant message. Tool invocations, skill content, and intermediate reasoning are excluded from captured output. Both conditions produce clean text, enabling fair pairwise comparison on content quality alone.

## Model-Specific Skill Activation Behavior

An important finding: not all models proactively read skills in the agentic harness. The model receives skill summaries in its context window but some models do not invoke the `read` tool to load full SKILL.md content. Models trained with awareness of the Agent Skills specification (Sonnet 4.6+) reliably load skills; earlier models may treat summaries as informational context rather than pointers to loadable resources.

This is relevant for deployment: organizations using agentic harnesses should verify their model actively loads skills, not merely receives summaries.

## Asymmetric Isolation (Methodological Lesson)

One agentic configuration attempted to create a clean baseline by isolating its environment, stripping all MCP servers, steering files, and global context. This produced artifact-free baseline responses. However, the skills condition retained the full environment, introducing tool artifacts visible in captured output.

The result was an unfair coherence advantage for the baseline, producing a 64.6% win rate that underestimates skill value. The symmetric agentic configuration — where both conditions share the same environment and tool access — produces a fairer measurement (69.5%) despite being "messier" in absolute terms. Symmetric noise cancels in pairwise comparison; asymmetric noise does not.

**Lesson:** The only variable between conditions should be skill content availability. Over-isolating the baseline introduces confounds as damaging as under-isolating the treatment.

## Critical Thinking: The Least-Confounded Dimension

Across all configurations, critical thinking shows the smallest gap:

| Dimension | Agentic | SDK | Gap |
|---|---|---|---|
| Coherence | 54.9% | 92.8% | 37.9pp |
| Overall | 69.5% | 85.9% | 16.4pp |
| Critical Thinking | 78.0% | 85.1% | **7.1pp** |

Critical thinking is minimally affected by formatting artifacts because it measures whether the agent applies the correct analytical framework, flags appropriate limitations, uses domain-specific thresholds, and challenges assumptions. These qualities are present or absent regardless of response formatting noise.

This makes critical thinking the **most reliable cross-harness signal**: skills improve reasoning quality 78–85% of the time regardless of measurement infrastructure.

## Judge Behavior Analysis

Qualitative analysis of judge rationales from the SDK configuration:

| Reason | Frequency | Description |
|---|---|---|
| Factual corrections | 59% | Skills correct specific errors in baseline responses |
| Specificity | 33% | Skills provide calibrated thresholds absent from parametric knowledge |
| Critical thinking | 29% | Skills flag edge cases, limitations, and caveats baseline misses |

When the baseline wins (14.1% of comparisons), the primary causes are: skill steering to the wrong framework (36% of baseline wins) and baseline producing a more directly relevant response (27%).

Position bias is +7.4 percentage points (favoring the second-presented response) but not statistically significant (p = 0.096).

## Alignment with External Benchmarks

The SkillsBench evaluation (arXiv 2602.12670) reports +16.6pp improvement with full agentic tools when both conditions have equal tool access. Our symmetric agentic configuration (69.5% vs 50% chance = +19.5pp) aligns closely with this finding.

The convergence across independent frameworks (different prompts, different judges, different skill implementations) strengthens confidence that the effect is real and robust rather than an artifact of any single evaluation methodology.

---

*Analysis based on evaluation runs conducted April–June 2026. Judge model: Claude Opus 4.7. Prompt set: 410 (380 single-skill + 30 cross-skill). Full per-skill results available in `eval/results/`.*
