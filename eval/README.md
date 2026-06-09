# HCLS Skills Evaluation Suite

Automated evaluation measuring whether domain skills improve Kiro CLI responses for healthcare and life sciences questions.

## Quick Start

```bash
conda activate drift-experiments
./install.sh --target kiro --path .
python -m eval.run --parallel 2 --version v1
python eval/build_review.py
open eval/results/review.html
```

## Prerequisites

- **conda environment:** `drift-experiments` (with boto3, scipy, pyyaml, rich)
- **kiro-cli:** installed and authenticated
- **AWS credentials:** with Bedrock access (Claude Opus 4.7 for judging, Sonnet 4 for prompt generation)

## Architecture

```
eval/
├── run.py                  # CLI orchestrator — execute → judge → report
├── execute.py              # Invokes kiro-cli under baseline/skills conditions
├── judge.py                # Independent scoring via Bedrock Opus 4.7
├── judge_pairwise.py       # Pairwise scoring (both responses in one call)
├── report.py               # Generates JSON + markdown reports
├── build_review.py         # Generates interactive HTML review
├── generate_prompts.py     # One-time prompt generation from skill metadata
├── config.yaml             # Eval configuration
├── prompts/                # Version-controlled test prompts (410 total)
│   ├── single/             # 380 prompts (10 per skill × 38 skills)
│   └── cross/              # 30 prompts (10 per combo × 3 combos)
├── results/                # Output (gitignored)
│   ├── responses/          # Cached kiro-cli responses
│   ├── scores_v*.json      # Scored results per version
│   ├── report_v*.md        # Markdown reports per version
│   ├── review.html         # Interactive HTML review (all versions)
│   └── METHODOLOGY.md      # Judging method comparison
├── TECHNICAL_REPORT.md     # Academic-style analysis of v3 results
└── PRESENTATION.md/.html   # Slide deck (Marp)
```

## Cross-Skill Prompts

The eval suite includes 30 cross-skill prompts (10 per category × 3 categories) that test multi-skill activation — questions spanning multiple domains where the agent must draw on several skills simultaneously. These are **not** standalone skills (no `SKILL.md` exists for them) but evaluation-only prompt categories.

| Category | Skills Tested | Example Scenario |
|----------|--------------|------------------|
| `drug-discovery-structural` | drug-repurposing + structure-based-drug-design + molecular-docking | Repurposing a kinase inhibitor requiring docking validation |
| `pharma-rwd-clinical` | pharmacoepidemiology + rwd-cohort-analysis + clinical-data-standards | Target trial emulation with claims data and MedDRA coding |
| `genomics-variant-pipeline` | genomic-variant-interpretation + variant-calling + ngs-quality-control | ACMG classification of a variant discovered via GATK pipeline |

Cross-skill prompts live in `eval/prompts/cross/` (e.g., `drug-discovery-structural-01.yaml`). In eval reports, they appear as 3 additional entries alongside the 38 single-skill entries, bringing the total to 41 rows. They should be interpreted as "cross-skill" category results, not as standalone skill evaluations.

## Running an Evaluation

### Full run (execution + judging + report)

```bash
python -m eval.run --parallel 2 --version v1
```

This will:
1. Execute all 410 prompts under both conditions (baseline from temp dir, skills from project dir)
2. Score all 820 responses via Claude Opus 4.7
3. Generate `report_v1.md` and `scores_v1.json`

### Re-judge only (skip execution, use cached responses)

```bash
python -m eval.run --skip-execution --version v2
```

### Pairwise judging (recommended — most sensitive)

```bash
python -m eval.run --skip-execution --version v3 --pairwise
```

Sends both responses in one judge call with randomized A/B position. Half the API calls, better relative comparison.

### Build interactive HTML review

```bash
python eval/build_review.py
open eval/results/review.html
```

Loads all score versions (v1, v2, v3) with a toggle. Shows per-skill tables, side-by-side responses, judge reasoning, and skill activation flags.

## Regenerating Prompts

Prompts are version-controlled and don't need regeneration. To regenerate:

```bash
python eval/generate_prompts.py --force
```

Uses Claude Sonnet 4 (`us.anthropic.claude-sonnet-4-6`) via Bedrock. Generates 10 prompts per skill with varying difficulty (3 easy, 4 intermediate, 3 hard).

## Configuration

`eval/config.yaml`:

```yaml
judge:
  model: us.anthropic.claude-opus-4-7
  max_tokens: 2048
  retries: 3

execution:
  timeout_seconds: 1200
  parallel: 1
  kiro_cmd: kiro-cli
  skills_agent: hcls-eval
```

## Key Design Decisions

- **Baseline isolation:** Baseline runs from a temp directory with no `.kiro/` to prevent skill auto-discovery
- **Response sanitization:** Tool-call artifacts stripped before judging so the judge can't identify which condition produced the response
- **Position randomization (v3):** 50/50 chance which response is shown as A vs B, canceling position bias
- **Score caching:** Responses and scores cached to disk — re-runs only process missing data
- **Paired t-test:** Per-skill significance via `scipy.stats.ttest_rel` on paired observations

## Judging Versions

| Version | Method | Blind? | Best for |
|---|---|---|---|
| v1 | Independent, raw | ❌ | Historical baseline |
| v2 | Independent, sanitized | ✅ | Absolute quality scores |
| v3 | Pairwise, sanitized + randomized | ✅ | Delta measurement (gold standard) |

## Interpreting Results

- **Overall delta:** Mean score difference (skills - baseline) across all prompts and dimensions
- **Win rate (v3):** Percentage of prompts where the judge declared skills the winner
- **Per-skill N:** Number of valid prompts (excludes timeouts). "activated" count shows how many had the intended skill loaded.
- **Sig? (✓):** Paired t-test p < 0.05 for that dimension
- **Skill flags:** ✓ Intended loaded, ⚠ Unintended loaded, ✗ Intended not loaded, ○ No skill loaded
- **Cross-skill entries (3 of 41):** These rows test multi-skill activation and are labeled with a `cross-skill` category. Unlike single-skill entries, they measure whether the agent can combine knowledge from 2–3 skills in one response. A win here indicates effective skill composition, not the quality of any individual skill.
