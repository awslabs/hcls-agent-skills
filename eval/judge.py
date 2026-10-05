"""LLM-as-judge scoring via Amazon Bedrock."""
import json
import logging
import os
import re
import time

try:
    from .aws_config import region_kwargs, judge_model_id
except ImportError:  # run as a standalone module
    from aws_config import region_kwargs, judge_model_id

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

logger = logging.getLogger(__name__)

# Inference-config keys that are SAFE to drop if a model rejects them as
# deprecated/unsupported. maxTokens is deliberately NOT listed — it must never
# be stripped. We detect rejections from the ValidationException MESSAGE, never
# a hardcoded model allowlist, so any model that starts rejecting a knob (e.g.
# Claude Opus 5 rejects `temperature` outright) is handled with no code change.
_STRIPPABLE_INFERENCE_PARAMS = ("temperature", "topP", "topK")


def _deprecated_inference_param(error: Exception, inference_config: dict) -> str | None:
    """Return the inferenceConfig key to strip if ``error`` is a Bedrock
    ValidationException complaining that an inference parameter is
    deprecated/unsupported, else None.

    Matches on the error MESSAGE (and the botocore error Code), not a model
    allowlist, so the recovery is model-agnostic. Bedrock phrases these as e.g.
    "'temperature' is deprecated for this model".
    """
    name = type(error).__name__
    code = ""
    resp = getattr(error, "response", None)
    if isinstance(resp, dict):
        code = resp.get("Error", {}).get("Code", "")
    if name != "ValidationException" and code != "ValidationException":
        return None
    msg = str(error).lower()
    if not any(k in msg for k in ("deprecated", "unsupported", "not supported", "isn't supported")):
        return None
    for param in _STRIPPABLE_INFERENCE_PARAMS:
        if param.lower() in msg and param in inference_config:
            return param
    return None


def _converse_scoring(client, model, sys_prompt, user_prompt, inference_config):
    """Run one Converse scoring call, with a one-shot recovery for a
    deprecated/unsupported inference parameter.

    If Bedrock rejects an inference parameter as deprecated/unsupported, strip
    ONLY that parameter from ``inference_config`` (in place) and retry ONCE, so
    the harness does not DIE on a ValidationException like "'temperature' is
    deprecated for this model". The mutation persists in the caller's dict, so
    subsequent attempts/prompts in the same loop never re-send the known-bad
    parameter. Any other exception propagates unchanged to the caller's retry
    loop (throttling retry vs. judge-error return).
    """
    try:
        return client.converse(
            modelId=model,
            system=[{"text": sys_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig=inference_config,
        )
    except Exception as e:
        param = _deprecated_inference_param(e, inference_config)
        if param is None:
            raise
        del inference_config[param]
        logger.warning(
            "Judge model %s rejected inference parameter '%s' as deprecated/"
            "unsupported; stripped it and retried once.", model, param,
        )
        return client.converse(
            modelId=model,
            system=[{"text": sys_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig=inference_config,
        )


def _extract_judge_text(resp: dict) -> str:
    """Return the first text block from a Bedrock Converse response.

    We SCAN every content block for the first one carrying a "text" key rather
    than indexing ``content[0]``: Claude Opus 5 (and other reasoning models) can
    emit a ``reasoningContent`` block BEFORE the text block, so a blind
    ``content[0]["text"]`` raises a bare, undiagnosable ``KeyError: 'text'``.

    When the output token budget is exhausted the model can return reasoning
    with NO text block at all (stopReason="max_tokens"). In that case we raise an
    EXPLICIT error naming the stopReason and the block types actually present,
    so the operator sees e.g. "judge returned no text block (stopReason=
    max_tokens, blocks=['reasoningContent'])" instead of a cryptic KeyError.
    """
    content = resp.get("output", {}).get("message", {}).get("content", []) or []
    for block in content:
        if isinstance(block, dict) and "text" in block:
            return block["text"]
    block_types = sorted({k for b in content if isinstance(b, dict) for k in b})
    raise ValueError(
        f"judge returned no text block (stopReason={resp.get('stopReason')}, "
        f"blocks={block_types})"
    )


def get_bedrock_client():
    """Create a Bedrock Runtime client from environment."""
    import boto3

    session_kwargs = {}
    if profile := os.environ.get("AWS_PROFILE"):
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    # Region resolves via the shared helper (AWS_REGION -> AWS_DEFAULT_REGION ->
    # boto3's own chain); region_name is omitted entirely when unresolved.
    return session.client("bedrock-runtime", **region_kwargs())


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
    model: str | None = None,
    retries: int = 3,
    max_tokens: int = 2048,
    temperature: float = 0.0,
) -> dict:
    """Score a response on 5 dimensions. Returns dict with scores + reasoning.

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
    sys_prompt = JUDGE_SYSTEM_PROMPT.format(domain=domain)
    clean_response = sanitize_for_judge(response_text)
    user_prompt = f"Question:\n{prompt_text}\n\nResponse to evaluate:\n{clean_response}"

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
