"""Pairwise LLM-as-judge scoring — sends both responses in one call with randomized position."""
import json
import os
import random
import re
import time

from .judge import get_bedrock_client, sanitize_for_judge, DIMENSIONS

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
    model: str = "us.anthropic.claude-opus-4-7",
    retries: int = 3,
) -> dict:
    """Score two responses pairwise. Returns dict with scores for both + position mapping."""
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

    for attempt in range(retries):
        try:
            resp = client.converse(
                modelId=model,
                system=[{"text": sys_prompt}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={"maxTokens": 2048},
            )
            text = resp["output"]["message"]["content"][0]["text"]
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
                "winner": "tie",
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
                "winner": "tie",
                "position": a_is,
                "reasoning": f"Judge error: {e}",
            }
