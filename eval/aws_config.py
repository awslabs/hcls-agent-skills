"""Shared AWS configuration for the eval suite.

Centralizes region resolution and default Bedrock model IDs so execution,
generation, judging, and preflight all target ONE region and the same
model family instead of diverging.
"""
import os
from typing import Optional


def resolve_region() -> Optional[str]:
    """Resolve the AWS region for all eval Bedrock/STS clients.

    Precedence:
    1. AWS_REGION environment variable
    2. AWS_DEFAULT_REGION environment variable
    3. None — do NOT substitute a literal. Returning None lets boto3's own
       resolution chain (profile / config file / instance metadata) decide,
       so a single misconfigured default cannot silently send traffic to the
       wrong region.
    """
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or None


def region_kwargs() -> dict:
    """Return ``{"region_name": <region>}`` when a region is resolvable, else ``{}``.

    Spreading an empty dict means ``region_name`` is omitted entirely, so boto3
    (and the Strands ``BedrockModel``) apply their own region resolution rather
    than being overridden with ``region_name=None``.
    """
    region = resolve_region()
    return {"region_name": region} if region else {}


# Built-in fallback model IDs use the global.* cross-region inference profile.
# Kept as named module constants so they stay greppable and documented.
FALLBACK_EXECUTION_MODEL_ID = "global.anthropic.claude-sonnet-5"
FALLBACK_JUDGE_MODEL_ID = "global.anthropic.claude-opus-5"

# Built-in fallback for the execution output token ceiling. Set high enough that
# well-formed answers in BOTH conditions complete (skills responses are longer),
# while still bounding runaway generation. Raised from 8192 to 16384 because at
# 8192 a real 10-prompt ml-researcher run truncated 4 of 20 responses
# (ml-researcher 05_baseline, 08_baseline, 09_baseline, 09_skills), disqualifying
# 3 of 10 prompts from scoring. See execution_max_tokens().
FALLBACK_EXECUTION_MAX_TOKENS = 16384


# These are FUNCTIONS, not module constants, for the same reason resolve_region()
# is: the env var must be read at CALL time, not frozen at IMPORT time. An
# in-process consumer (a test, a notebook, a wrapper) that sets EVAL_MODEL_ID
# after importing this module must see its value, not a stale default. Do NOT
# "tidy" these back into import-time `X = os.environ.get(...)` constants.
def execution_model_id() -> str:
    """Resolve the execution Bedrock model: EVAL_MODEL_ID env var > built-in fallback."""
    return os.environ.get("EVAL_MODEL_ID") or FALLBACK_EXECUTION_MODEL_ID


def judge_model_id() -> str:
    """Resolve the judge Bedrock model: EVAL_JUDGE_MODEL_ID env var > built-in fallback."""
    return os.environ.get("EVAL_JUDGE_MODEL_ID") or FALLBACK_JUDGE_MODEL_ID


def execution_max_tokens() -> int:
    """Resolve the execution output token ceiling: EVAL_MAX_TOKENS env var > built-in fallback.

    A FUNCTION, not a module constant, for the same late-binding reason as
    execution_model_id(): EVAL_MAX_TOKENS must be read at CALL time so an
    in-process consumer that sets it after import still sees its value.
    """
    env = os.environ.get("EVAL_MAX_TOKENS")
    return int(env) if env else FALLBACK_EXECUTION_MAX_TOKENS


def no_region_message(error: object) -> str:
    """Shared actionable message for an unresolvable AWS region.

    Centralized so preflight (STS + Bedrock blocks) and generate_prompts emit
    identical guidance instead of three drifting copies of the same string.
    """
    return (
        "No AWS region configured. Set AWS_REGION (or AWS_DEFAULT_REGION), "
        "or set a default region in your AWS profile/config.\n"
        f"Error: {error}"
    )
