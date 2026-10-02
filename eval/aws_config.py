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


# Default model IDs use the global.* cross-region inference profile. Overridable
# via environment so the suite is not pinned to one profile family.
DEFAULT_EXECUTION_MODEL_ID = os.environ.get("EVAL_MODEL_ID", "global.anthropic.claude-sonnet-5")
DEFAULT_JUDGE_MODEL_ID = os.environ.get("EVAL_JUDGE_MODEL_ID", "global.anthropic.claude-opus-5")
