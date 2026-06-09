"""LLM-as-judge scoring via Amazon Bedrock."""
import json
import os
import re
import time

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator for healthcare and life sciences AI responses.
Score the following response to a domain-specific question on 5 dimensions, each 0-100.

Dimensions:
- scientific_accuracy (0-100): Correctness of facts, mechanisms, citations, domain knowledge.
- coherence (0-100): Logical structure, clear reasoning chain, internal consistency.
- relevance (0-100): Addresses all parts of the prompt, appropriate depth, stays on topic.
- critical_thinking (0-100): Challenges assumptions, identifies limitations, considers alternatives.
- actionability (0-100): Provides concrete next steps, specific parameters, runnable commands.

You are a domain expert in {domain}. Evaluate as a peer reviewer using your own knowledge.

Return ONLY valid JSON:
{{"scientific_accuracy": N, "coherence": N, "relevance": N, "critical_thinking": N, "actionability": N, "reasoning": "2-3 sentence justification"}}"""

DIMENSIONS = [
    "scientific_accuracy", "coherence", "relevance",
    "critical_thinking", "actionability",
]


def get_bedrock_client():
    """Create a Bedrock Runtime client from environment."""
    import boto3

    session_kwargs = {}
    if profile := os.environ.get("AWS_PROFILE"):
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    region = os.environ.get("AWS_REGION", "us-west-2")
    return session.client("bedrock-runtime", region_name=region)


def sanitize_for_judge(text: str) -> str:
    """Strip tool-call artifacts so the judge only sees substantive content."""
    lines = text.split("\n")
    filtered = []
    skip_until_blank = False
    for line in lines:
        # Skip tool usage headers and their output
        if any(p in line for p in [
            "(using tool:", "Batch fs_read operation", "↱ Operation",
            "Successfully read", "Completed in 0.", "Reading file:",
            ".kiro/skills/", "SKILL.md", "fs_read", "fs_write",
            "I'll share my reasoning process",
            "operations processed",
            " ⋮",
            "- Summary:",
        ]):
            skip_until_blank = True
            continue
        if skip_until_blank:
            if line.strip() == "":
                skip_until_blank = False
            continue
        # Skip lines that are just tool status markers
        if re.match(r"^\s*[✓✗↱►▶⋮]\s", line):
            continue
        # Skip leading > quote markers from tool output
        if line.strip().startswith("> ") and "skill" in line.lower():
            continue
        filtered.append(line)
    # Remove leading blank lines
    result = "\n".join(filtered).lstrip("\n")
    return result


def score_response(
    client,
    prompt_text: str,
    response_text: str,
    domain: str,
    model: str = "us.anthropic.claude-opus-4-7",
    retries: int = 3,
) -> dict:
    """Score a response on 5 dimensions. Returns dict with scores + reasoning."""
    sys_prompt = JUDGE_SYSTEM_PROMPT.format(domain=domain)
    clean_response = sanitize_for_judge(response_text)
    user_prompt = f"Question:\n{prompt_text}\n\nResponse to evaluate:\n{clean_response}"

    for attempt in range(retries):
        try:
            resp = client.converse(
                modelId=model,
                system=[{"text": sys_prompt}],
                messages=[{"role": "user", "content": [{"text": user_prompt}]}],
                inferenceConfig={"maxTokens": 2048},
            )
            text = resp["output"]["message"]["content"][0]["text"]
            json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if json_match:
                scores = json.loads(json_match.group())
                for d in DIMENSIONS:
                    if d not in scores:
                        scores[d] = 0
                return scores
            return {d: 0 for d in DIMENSIONS} | {
                "reasoning": "Failed to parse judge response"
            }
        except Exception as e:
            if attempt < retries - 1 and any(
                x in str(e) for x in ["Throttling", "ServiceUnavailable", "Timeout"]
            ):
                time.sleep(2**attempt)
                continue
            return {d: 0 for d in DIMENSIONS} | {"reasoning": f"Judge error: {e}"}
