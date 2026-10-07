# Module 3: Evaluating Skills — Take-Home (10 min)

[← Module 2](module-2.md) | [Overview](overview.md)

> 📋 **This module is instructor-presented, not hands-on.** Use it as a reference card for the take-home assignment. No AWS is needed for the structural check; the full pairwise eval needs Bedrock.

### How the Eval Works (reference)

- **Pairwise design:** the same prompt is answered **with** and **without** the skill. Responses are sanitized (skill fingerprints stripped) and position-randomized, then **Claude Opus** judges across **5 dimensions**.
- **Metrics:** **win rate** + **Cohen's d** (0.2 small / 0.5 medium / 0.8 large effect).
- **North star:** **critical thinking** — it's the least harness-sensitive dimension (78–85% across every harness configuration tested).

### Pre-Computed Results to Explore

The repo ships with a full evaluation you can browse right now:

- `eval/results/review.html` — interactive review dashboard (open in a browser).
- `eval/TECHNICAL_REPORT.md` — the full 410-prompt analysis.
- **Key rows to inspect:**
  - `genomic-variant-interpretation` — **90%** win.
  - `translational-research` — **100%** win, Cohen's d **+2.07** (v4).
  - `quantitative-proteomics` — **30%** win (the cautionary tale — recites known recipes).

### Take-Home Assignment

> ⚠️ **Prerequisites — everything except step 0.** The structural check runs offline; the rest needs valid **AWS credentials** + **Amazon Bedrock model access**, with both a **Sonnet** (execution) and an **Opus** (judge) model reachable.
> - **One region, set via `AWS_REGION`:** every step (execution, generation, judging, preflight) now targets a single region resolved from `AWS_REGION` (falling back to `AWS_DEFAULT_REGION`, then your AWS profile/config). Set `AWS_REGION` and enable model access there.
> - **Model IDs use the `global.` profile:** `eval/` now requests the `global.` cross-region inference profile IDs (`global.anthropic.claude-sonnet-5` for execution, `global.anthropic.claude-opus-5` for the judge) — matching `setup.md`. Enable access to those profiles (overridable via `EVAL_MODEL_ID` / `EVAL_JUDGE_MODEL_ID`).
> - **Cost:** a 30-prompt pairwise run makes **60 execution calls** (30 prompts × 2 arms) + **30 judge calls**.

```bash
# 0. Set up environment (Skip if you've done this in Module 2.)
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"

# 1. Structural check first
python tests/validate_skill.py --skill my-new-skill

# 2. Generate 30 prompts for your new skill (requires Bedrock access)
python eval/generate_prompts.py --skill my-new-skill --count 30

# Verify generation actually succeeded — should print 30
ls eval/prompts/single/my-new-skill-*.yaml | wc -l

# 3. Create a subset prompts directory with the required single/ subdirectory
mkdir -p /tmp/eval-subset/single

# 4. Copy only the target skill's prompt files
cp eval/prompts/single/my-new-skill-*.yaml /tmp/eval-subset/single/

# 5. Run the scoped evaluation
python -m eval.run \
  --prompts-dir /tmp/eval-subset \
  --parallel 2 \
  --version my-skill-test \
  --pairwise

# 6. Review results
python eval/build_review.py
open eval/results/review.html # or download the html to your local device to view
```

The verify step matters because `generate_prompts.py` catches per-prompt exceptions and prints a `WARN` line instead of failing — a credentials or model-access problem leaves a partial or empty prompt set that still looks like success.

**What "good" looks like:** win rate ≥ **70%**, critical thinking positive, coherence neutral or positive.

> ⚠️ **Sample size matters.** Those thresholds only mean something at **n ≥ 30 prompts** for a single skill — that's the minimum for the win rate and **Cohen's d** to carry real statistical weight. Run a handful of prompts and the win rate swings on noise. See the eval README's [Running eval for a single skill](https://github.com/awslabs/hcls-agent-skills/blob/main/eval/README.md#running-eval-for-a-single-skill) section for the scoped procedure.

> ⚠️ **The number isn't scoped to your skill.** The harness attaches the *entire* skills directory (`AgentSkills(skills="./skills/")` in `eval/execute.py`) and the model self-selects — `target_skills:` in each prompt YAML is **reporting metadata only** and does not drive execution. Scoping filters the *prompt set*, not the skill set, so a run can post a healthy win rate on prompts where your skill never activated or where a different skill did the work. Before believing the number, check the recorded `activated_skills` field in `eval/results/responses/<version>/<pid>_skills.json` (also surfaced by the **Skills Activated** filter in `review.html`).

### Take-Home Stretch Goals

1. **Run the eval on the skill you modified in Module 2** — did your changes help, hurt, or stay neutral? The repo ships only **10** prompts for `imaging-study-design`, below the **n ≥ 30** minimum — regenerate with `--count 30` first rather than reusing the shipped set.
2. **Author a new skill from scratch** using the `CUSTOMIZING.md` template (`endoscopy-pixel-deid` or `ibd-endoscopic-endpoint-scoring`).
3. **Read `SKILL_DESIGN_GUIDE.md`** and diagnose *why* `quantitative-proteomics` wins only 30% — then propose the fix.
4. **Full capstone:** pick a skill → use it → spot a weakness → improve it → re-eval → observe the delta.

---

> ✅ **You're done.** Across the three modules you've used reasoning and pipeline skills on real R&D questions, extended a skill with your own lab's rules, and seen how to prove whether a change helps. Take the eval loop home and make one skill measurably better.
