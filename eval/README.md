# HCLS Skills Evaluation Suite

Automated evaluation measuring whether domain skills improve agent responses for healthcare and life sciences questions. Uses the [AWS Strands Agents SDK](https://github.com/strands-agents/sdk-python) as the default execution backend, with kiro-cli as a legacy alternative.

## Quick Start

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"

# Recommended: v9 methodology (Strands + think tool)
python -m eval.run --parallel 2 --version v9 --pairwise \
  --model us.anthropic.claude-sonnet-4-6-20250514-v1:0 --tools think

python eval/build_review.py
open eval/results/review.html
```

> ⚠️ **Cost & Time Estimate**
>
> A full eval run (410 prompts × 2 conditions + 410 pairwise judgments) costs **~$126** on-demand:
>
> | Phase | Model | Estimated Cost |
> |-------|-------|---------------|
> | Execution (820 calls) | Claude Sonnet 4.6 — $3/1M input, $15/1M output | ~$60 |
> | Judging (410 calls) | Claude Opus 4.7 — $15/1M input, $75/1M output | ~$66 |
> | **Total** | | **~$126** |
>
> Wall time: ~4 hours at `--parallel 2`. Costs vary with prompt complexity and response length.

## Prerequisites

- **Python 3.12+** managed via [uv](https://docs.astral.sh/uv/)
- **AWS credentials:** configured via `~/.aws/credentials` or environment variables
- **Amazon Bedrock access:** model access enabled for the `global.*` cross-region inference profiles the eval requests by default:
  - `global.anthropic.claude-sonnet-5` (execution, default — override with `EVAL_MODEL_ID` or `--model`)
  - `global.anthropic.claude-opus-5` (LLM judge — override with `EVAL_JUDGE_MODEL_ID`)
- **Region:** set via `AWS_REGION` (falls back to `AWS_DEFAULT_REGION`, then your AWS profile/config). Every step — execution, generation, judging, and preflight — uses this one resolved region; nothing is hardcoded. If no region is resolvable, the preflight check fails with an actionable message.

## Architecture

```
eval/
├── run.py                  # CLI orchestrator — execute → judge → report
├── execute.py              # Dual-backend executor (strands SDK or kiro-cli)
├── judge.py                # Independent scoring via the configured Bedrock judge model
├── judge_pairwise.py       # Pairwise scoring (both responses in one call)
├── report.py               # Generates JSON + markdown reports
├── build_review.py         # Generates interactive HTML review
├── generate_prompts.py     # One-time prompt generation from skill metadata
├── config.yaml             # Eval configuration (judge model, timeouts)
├── prompts/                # Version-controlled test prompts (410 total)
│   ├── single/             # 380 prompts (10 per skill × 38 skills)
│   └── cross/              # 30 prompts (10 per combo × 3 combos)
├── results/                # Output (gitignored)
│   ├── responses/          # Cached agent responses
│   ├── scores_v*.json      # Scored results per version
│   ├── report_v*.md        # Markdown reports per version
│   ├── review.html         # Interactive HTML review (all versions)
│   └── METHODOLOGY.md      # Judging method comparison
├── TECHNICAL_REPORT.md     # Academic-style analysis of v3 results
└── PRESENTATION.md/.html   # Slide deck (Marp)
```

### Execution Backends

`execute.py` supports two backends:

| Backend | Default | How it works | Requirements |
|---------|---------|--------------|--------------|
| `strands` | ✅ | AWS Strands Agents SDK with `AgentSkills` plugin, calls Bedrock directly | AWS credentials + Bedrock access |
| `kiro-cli` | — | Subprocess invocation of `kiro-cli chat` | kiro-cli installed + authenticated |

The **strands** backend builds an `Agent` with a `BedrockModel` for each prompt. For the "skills" condition, it attaches an `AgentSkills` plugin pointed at the skills directory. For "baseline", it runs a bare agent with no skills. No external CLI tools are needed.

## CLI Flags

```
python -m eval.run [OPTIONS]

Execution:
  --backend {strands,kiro-cli}  Execution backend (default: strands)
  --model MODEL_ID              Bedrock model ID for execution (strands only)
                                Default: global.anthropic.claude-sonnet-5 (or $EVAL_MODEL_ID)
  --max-tokens N                Max output tokens for execution (strands only)
                                Precedence: --max-tokens > $EVAL_MAX_TOKENS >
                                config.yaml > fallback (16384). Applied identically
                                to both conditions.
  --skip-model-check            Skip the preflight Converse probe that verifies each
                                model is invocable. The STS check still runs; no
                                Bedrock access is verified.
  --tools TOOL [TOOL ...]       Tools to provide to the agent (e.g., --tools think)
                                Adds specified tools to both conditions symmetrically
  --kiro-model MODEL            Model override for kiro-cli backend
                                (e.g., --kiro-model claude-sonnet-4.6)
  --skills PATH                 Path to skills directory (default: ./skills/)
  --parallel N                  Max concurrent executions (default: 1)
  --version V                   Version label (e.g., v9). Tags output files.

Judging:
  --pairwise                    Use pairwise judge (recommended, most sensitive)
  --judge-model MODEL_ID        Bedrock model ID for the LLM judge
                                Precedence: --judge-model > $EVAL_JUDGE_MODEL_ID >
                                config.yaml > fallback (global.anthropic.claude-opus-5)
  --skip-execution              Skip execution, re-judge cached responses
  --skip-judge                  Skip judging, just generate report

Paths:
  --prompts-dir PATH            Prompts directory (default: eval/prompts)
  --results-dir PATH            Results directory (default: eval/results)
  --config PATH                 Config file (default: eval/config.yaml)
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
python -m eval.run --parallel 2 --version v9 --pairwise \
  --model us.anthropic.claude-sonnet-4-6-20250514-v1:0 --tools think
```

This will:
1. Execute all 410 prompts under both conditions (baseline = bare agent, skills = agent with AgentSkills plugin)
2. Score all 820 responses via the configured Bedrock judge model (pairwise)
3. Generate `report_v9.md` and `scores_v9.json`

### Re-judge only (skip execution, use cached responses)

```bash
python -m eval.run --skip-execution --version v9 --pairwise
```

### Custom model

```bash
python -m eval.run --model us.anthropic.claude-sonnet-4-20250514-v1:0 --version v5 --pairwise --tools think
```

> As above, this pins the **execution** model via `--model`, which is **now honored** (previously inert on the Strands backend). This is a legacy *regional* ID; a `global.*`-only account will get `AccessDeniedException` unless legacy regional model access is enabled. (The command requests a Sonnet 4 ID, but because the flag was ignored at the time, v5 actually ran the then-hardcoded Sonnet 4.5 the table lists.) v5 was judged by Claude Opus 4.7; that exact judge model ID is not recorded here, so to reproduce v5's judging prefix the command with `EVAL_JUDGE_MODEL_ID=<the Opus 4.7 Bedrock model ID that run used>`. Without it the judge defaults to the `global.anthropic.claude-opus-5` profile in `config.yaml`.

### Build interactive HTML review

```bash
python eval/build_review.py
open eval/results/review.html
```

Loads all score versions (v1–v9) with a toggle. Shows per-skill tables, side-by-side responses, judge reasoning, and skill activation flags.

### Using kiro-cli backend (legacy)

```bash
./install.sh --target kiro --path .
python -m eval.run --backend kiro-cli --parallel 2 --version v8 \
  --kiro-model claude-sonnet-4.6
```

Requires kiro-cli installed and authenticated. The agent config is auto-created at `.kiro/agents/hcls-eval.json`. Use `--kiro-model` to pin the model (recommended for reproducibility).

## Running eval for a single skill

Evaluation is **optional** for contributors (see [CONTRIBUTING.md](../CONTRIBUTING.md) step 8) — maintainers may run their own evaluation during review if you skip it. If you'd like to measure your skill's impact before opening a PR, run a scoped evaluation against only that skill's prompts. This is not a replacement for the full 410-prompt suite (which remains the statistical-power standard for repo-wide validation), but it gives an indicative smoke-test signal at minimal cost.

**How it works:** `--prompts-dir` tells the runner where to find prompt YAML files. The loader scans `<dir>/single/*.yaml` and `<dir>/cross/*.yaml`. By creating a temporary directory containing only your target skill's prompt files, you scope execution to just those prompts.

**If your skill is new,** it has no prompts yet — generate 30 first with `generate_prompts.py --skill <name> --count 30` (see [Regenerating Prompts](#regenerating-prompts) below). If you're evaluating an existing skill, its prompts already exist under `eval/prompts/single/`.

**Worked example — evaluating a new skill `my-new-skill`:**

```bash
# 1. Generate 30 prompts for your new skill (requires Bedrock access)
python eval/generate_prompts.py --skill my-new-skill --count 30

# 2. Create a subset prompts directory with the required single/ subdirectory
mkdir -p /tmp/eval-subset/single

# 3. Copy only the target skill's prompt files
cp eval/prompts/single/my-new-skill-*.yaml /tmp/eval-subset/single/

# 4. Run the scoped evaluation
python -m eval.run \
  --prompts-dir /tmp/eval-subset \
  --parallel 2 \
  --version my-skill-test \
  --pairwise

# 5. Review results
python eval/build_review.py
open eval/results/review.html
```

At n=30 prompts, a single-skill run evaluates 30 prompts × 2 conditions = 60 executions + 30 pairwise judgments. This costs roughly **~$9** and takes **~30 minutes** at `--parallel 2`.

> **Note:** n=30 is the recommended minimum for a contributor smoke test with some statistical signal. The full 410-prompt suite (10 prompts/skill × 38 skills + cross-skill combos) remains required for repo-wide, statistically meaningful conclusions.

## Regenerating Prompts

Prompts are version-controlled and don't need regeneration. To regenerate:

```bash
# Regenerate all prompts (38 skills + 3 cross-skill combos) at the standard 10/skill
python eval/generate_prompts.py --force

# Generate 30 prompts for a single (typically new) skill
python eval/generate_prompts.py --skill my-new-skill --count 30

# Regenerate an existing skill's prompts at the standard 10/skill
python eval/generate_prompts.py --skill genomic-variant-interpretation --force
```

The `--skill <name>` flag scopes generation to a single skill's prompt files in `eval/prompts/single/` and any cross-skill combos that include it. Omit `--skill` to regenerate the full suite. Use `--count <n>` to override the default of 10 prompts/skill — e.g. `--count 30` for a contributor evaluation run.

Uses `global.anthropic.claude-sonnet-5` via Bedrock (override with `EVAL_MODEL_ID`). Generates 10 prompts per skill by default, with varying difficulty (3 easy, 4 intermediate, 3 hard); counts above 10 add further prompts at the same difficulty mix.

## Configuration

`eval/config.yaml`:

```yaml
judge:
  model: global.anthropic.claude-opus-5
  max_tokens: 2048
  retries: 3

execution:
  timeout_seconds: 1200
  parallel: 1
  kiro_cmd: kiro-cli
  skills_agent: hcls-eval
```

The `execution.kiro_cmd` and `execution.skills_agent` fields are only used by the `kiro-cli` backend. The strands backend reads model and skills path from CLI flags (or defaults).

**Environment overrides:**

| Variable | Controls | Default |
|---|---|---|
| `AWS_REGION` → `AWS_DEFAULT_REGION` | Region for execution, generation, judging, and preflight. If neither is set, boto3's own resolution (profile / config / instance metadata) applies. | boto3 resolution |

**Model overrides (for restricted accounts):** If your account can invoke only certain Bedrock models, substitute a model you *can* invoke using any lever below. Each model role resolves independently, at call time:

| Model role | CLI flag | Env var | Config file | Built-in fallback |
|---|---|---|---|---|
| Execution + prompt generation | `--model` (`eval.run` and `eval.generate_prompts`) | `EVAL_MODEL_ID` | — | `global.anthropic.claude-sonnet-5` |
| Judge | `--judge-model` (`eval.run`) | `EVAL_JUDGE_MODEL_ID` | `eval/config.yaml` → `judge.model` | `global.anthropic.claude-opus-5` |

**Precedence (highest wins):** **CLI flag > environment variable > `eval/config.yaml` (judge only) > built-in fallback.** The fallbacks live in `eval/aws_config.py` as `FALLBACK_EXECUTION_MODEL_ID` / `FALLBACK_JUDGE_MODEL_ID`, and resolution goes through the call-time functions `execution_model_id()` / `judge_model_id()` — so an env var set in-process (a test, a notebook, a wrapper script) is honored rather than frozen at import.

**Preflight model probe:** Before executing, `eval.run` validates credentials (`sts:GetCallerIdentity`) and — critically — performs a **minimal real invocation** (a 1-token `bedrock-runtime` Converse) against each model it will use. Because `list_foundation_models` does not enumerate `global.*` cross-region inference profiles, this probe is the only check that exercises IAM, model enablement, and region routing together. An `AccessDeniedException` therefore surfaces **at preflight, naming the exact failing model and every override path**, instead of failing mid-run. Transient errors (throttling, service unavailable) warn and continue rather than aborting. Pass `--skip-model-check` to skip the Converse probe entirely — this leaves the STS identity check **alone**, so **no Bedrock access is verified at all**. A restricted workshop role can pass preflight with `--skip-model-check` and still fail at the first real invocation.

## Interpreting Results

- **Overall delta:** Mean score difference (skills - baseline) across all prompts and dimensions
- **Win rate:** Percentage of prompts where the judge declared skills the winner
- **Per-skill N:** Number of valid prompts (excludes timeouts). "activated" count shows how many had the intended skill loaded.
- **Sig? (✓):** Paired t-test p < 0.05 for that dimension
- **Skill flags:** ✓ Intended loaded, ⚠ Unintended loaded, ✗ Intended not loaded, ○ No skill loaded
- **Cross-skill entries (3 of 41):** These rows test multi-skill activation and are labeled with a `cross-skill` category. Unlike single-skill entries, they measure whether the agent can combine knowledge from 2–3 skills in one response. A win here indicates effective skill composition, not the quality of any individual skill.

**Truncated responses.** When an execution response hits the output token ceiling, `execute.py` preserves the partial text behind a `[TRUNCATED]` marker and sets `metadata["truncated"] = True` rather than discarding it. `run.py` guards `[TRUNCATED]` responses out of judging alongside `[TIMEOUT]`/`[ERROR]`: they score zero on every dimension and are never rescored (so a later re-judge pass skips them too). A run with many truncations is scoring fewer valid prompts than it appears to — re-run it with a higher `--max-tokens` rather than trusting the result.

## Running the tests

`eval/tests/` holds 18 unit tests (no AWS or network calls). Run them with:

```bash
python -m pytest eval/tests -p no:cacheprovider -p no:asyncio -q
```

The `-p no:asyncio` / `-p no:cacheprovider` flags sidestep a local `pytest_asyncio` collection error. CI runs the same suite via [`.github/workflows/eval-tests.yml`](../.github/workflows/eval-tests.yml).
