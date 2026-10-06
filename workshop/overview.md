# HCLS Agent Skills — Workshop Overview

**Workshop:** Agent Skills for Life Sciences R&D

**Duration:** 90 minutes

**Format:** Hands-on, copy-paste driven. You run every prompt yourself.

This guide walks you through *using* skills, *extending* them with your own org knowledge, and *evaluating* whether your changes actually help. Every exercise gives you an exact prompt, step-by-step instructions, and a "what to look for" contrast between the skilled and unskilled response.

---

## Prerequisites

> ⚠️ **Setup must be complete before you start.** This lab assumes you finished the [setup guide](setup.md): the `hcls-agent-skills` repo cloned, the skills installed, and an editor open on the repo. This guide contains **no setup steps** — if skills aren't active in your agent, go back to [setup.md](setup.md) first.


---

## How to Use This Guide

Each exercise follows the same three-part rhythm:

1. **The prompt** — copy it verbatim into your agent. Do not paraphrase.
2. **The steps** — run with the skill active, then run the same prompt again with no skill active.
3. **What to look for** — the specific signals that separate a skilled response from a base-model answer.

> 💡 **Tip:** The whole point is the *contrast*. A skilled response and an unskilled response can both sound confident. You are training your eye to spot which one is actually applying a rigorous, reproducible framework versus generating plausible prose.

---

## Modules

- **[Module 1: Using Skills (30 min)](module-1.md)** — Four hands-on exercises across two use cases. For each, you run the prompt with no skill, then with the skill, then diff the two. Use Case 1 is a neuroimaging Alzheimer's trial pairing `imaging-study-design` and `translational-research`; Use Case 2 is a pharmacogenomics claims study pairing `genomic-variant-interpretation` and `pharmacoepidemiology`. Each use case gives you one single-skill exercise and one two-skill exercise, so you see both how a skill sharpens an answer and how two skills divide a problem.

- **[Module 2: Extending & Creating Skills (30 min)](module-2.md)** — Start with instructor-led skill design principles, then do the core exercise: add your own lab-specific rules to `imaging-study-design` (endoscopic trial-eligibility scoring plus endoscopy-specific pixel-data de-identification) and watch the agent's answer change, then validate the edited skill with `tests/validate_skill.py`. Closes with an instructor walkthrough of authoring a new skill from scratch, including the frontmatter contract and body shape.

- **[Module 3: Evaluating Skills — Take-Home (10 min)](module-3.md)** — An instructor-presented reference card for the take-home evaluation loop. Covers how the pairwise eval works (win rate, Cohen's d, critical thinking as the north star), which pre-computed results in `eval/` to browse, and a take-home assignment with stretch goals to run the eval on the skill you modified and to author and evaluate your own.

