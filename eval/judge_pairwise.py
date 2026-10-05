"""Pairwise LLM-as-judge scoring — sends both responses in one call with randomized position."""
import json
import os
import random
import re
import time

from .judge import get_bedrock_client, sanitize_for_judge, DIMENSIONS, judge_model_id, _converse_scoring, _extract_judge_text

PAIRWISE_SYSTEM_PROMPT = """You are an expert evaluator for healthcare and life sciences AI responses.
You will see two responses (Response A and Response B) to the same domain question.
Score EACH response independently on 5 dimensions (0-100), then state which is better overall.

Dimensions:
- scientific_accuracy (0-100): Correctness of facts, mechanisms, citations, domain knowledge.
- coherence (0-100): Logical structure, clear reasoning chain, internal consistency.
- relevance (0-100): Addresses all parts of the prompt, appropriate depth, stays on topic.
- critical_thinking (0-100): Challenges assumptions, identifies limitations, considers alternatives.
- actionability (0-100): Provides concrete next steps, specific parameters, runnable commands.

You are a domain expert in {domain}. Evaluate as a peer reviewer using your own knowledge.

Return ONLY valid JSON:
{{"response_a": {{"scientific_accuracy": N, "coherence": N, "relevance": N, "critical_thinking": N, "actionability": N}}, "response_b": {{"scientific_accuracy": N, "coherence": N, "relevance": N, "critical_thinking": N, "actionability": N}}, "better": "A"|"B"|"tie", "reasoning": "2-3 sentence comparison justification"}}"""


def score_pairwise(
    client,
    prompt_text: str,
    baseline_text: str,
    skills_text: str,
    domain: str,
    model: str | None = None,
    retries: int = 3,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> dict:
    """Score two responses pairwise. Returns dict with scores for both + position mapping.

    model: None resolves at call time via judge_model_id() (EVAL_JUDGE_MODEL_ID
        env var > built-in fallback).
    max_tokens / temperature / retries: judge inference knobs. Defaults match
        the historical hardcoded values; run.py threads the eval/config.yaml
        values in so editing config is no longer silently ignored.
    """
    # Late-bound default: resolve the judge model at call time rather than as an
    # early-bound parameter default. Do NOT restore `= DEFAULT_JUDGE_MODEL_ID`
    # in the signature — that re-freezes the env read at import time.
    model = model or judge_model_id()
    clean_baseline = sanitize_for_judge(baseline_text)
    clean_skills = sanitize_for_judge(skills_text)

    # Randomize position to counter position bias
    if random.random() < 0.5:
        a_text, b_text = clean_baseline, clean_skills
        a_is = "baseline"
    else:
        a_text, b_text = clean_skills, clean_baseline
        a_is = "skills"

    sys_prompt = PAIRWISE_SYSTEM_PROMPT.format(domain=domain)
    user_prompt = f"Question:\n{prompt_text}\n\nResponse A:\n{a_text}\n\nResponse B:\n{b_text}"

    # Build inferenceConfig ONCE. temperature is included only when set (None
    # omits it); _converse_scoring additionally strips any parameter a model
    # rejects as deprecated/unsupported. The (possibly stripped) dict persists
    # across retry attempts so a known-bad parameter is never re-sent.
    inference_config = {"maxTokens": max_tokens}
    if temperature is not None:
        inference_config["temperature"] = temperature

    for attempt in range(retries):
        try:
            resp = _converse_scoring(client, model, sys_prompt, user_prompt, inference_config)
            text = _extract_judge_text(resp)
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Map back to baseline/skills based on position
                if a_is == "baseline":
                    baseline_scores = result.get("response_a", {})
                    skills_scores = result.get("response_b", {})
                    winner = {"A": "baseline", "B": "skills", "tie": "tie"}.get(result.get("better", "tie"), "tie")
                else:
                    baseline_scores = result.get("response_b", {})
                    skills_scores = result.get("response_a", {})
                    winner = {"A": "skills", "B": "baseline", "tie": "tie"}.get(result.get("better", "tie"), "tie")

                return {
                    "baseline": {d: baseline_scores.get(d, 0) for d in DIMENSIONS},
                    "skills": {d: skills_scores.get(d, 0) for d in DIMENSIONS},
                    "winner": winner,
                    "position": a_is,  # what was shown as A
                    "reasoning": result.get("reasoning", ""),
                }
            return {
                "baseline": {d: 0 for d in DIMENSIONS},
                "skills": {d: 0 for d in DIMENSIONS},
                # Unparseable judge output is a judge FAILURE, not a tie. Flag it
                # with winner=="error" so run.py drops the prompt rather than
                # recording a silent 5-5 tie from the all-zero scores.
                "winner": "error",
                "position": a_is,
                "reasoning": "Failed to parse judge response",
            }
        except Exception as e:
            if attempt < retries - 1 and any(
                x in str(e) for x in ["Throttling", "ServiceUnavailable", "Timeout"]
            ):
                time.sleep(2 ** attempt)
                continue
            return {
                "baseline": {d: 0 for d in DIMENSIONS},
                "skills": {d: 0 for d in DIMENSIONS},
                # A judge EXCEPTION must never silently become a tie. Flag it
                # with winner=="error" so run.py drops the prompt with a reason.
                "winner": "error",
                "position": a_is,
                "reasoning": f"Judge error: {e}",
            }
