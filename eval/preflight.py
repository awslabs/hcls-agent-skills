"""Pre-flight credential validation for the eval suite."""
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoRegionError

try:
    from .aws_config import (
        region_kwargs, execution_model_id, judge_model_id, no_region_message,
    )
except ImportError:  # run as a standalone script
    from aws_config import (
        region_kwargs, execution_model_id, judge_model_id, no_region_message,
    )


class PreflightError(Exception):
    """Raised when credential pre-flight checks fail."""


# Error-code classification for the model probe, paralleling the
# _AUTH_THROTTLE_CODES set in execute.py. Codes meaning the model genuinely
# cannot be used hard-fail; transient codes only warn (see _probe_model).
_PROBE_HARD_FAIL_CODES = {
    "AccessDeniedException", "ValidationException", "ResourceNotFoundException",
    "UnrecognizedClientException", "InvalidSignatureException", "ExpiredTokenException",
}
_PROBE_TRANSIENT_CODES = {
    "ThrottlingException", "TooManyRequestsException", "ServiceUnavailableException",
    "InternalServerException", "ModelTimeoutException",
}


def _probe_model(runtime, model_id: str, role: str, flag: str, env_var: str,
                 config_hint: bool = False) -> None:
    """Prove a model is actually invocable via a minimal Converse call.

    list_foundation_models does NOT enumerate global.* cross-region inference
    profiles, so reporting a model as "available" from that call checks nothing.
    A tiny Converse (maxTokens=1, a one-word message) is the only check that
    exercises IAM + model enablement + region routing together, at ~1-2 tokens.
    """
    try:
        runtime.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "ping"}]}],
            inferenceConfig={"maxTokens": 1},
        )
    except NoRegionError as e:
        # Caught before BotoCoreError (its superclass) so a missing region does
        # not masquerade as a model-access problem.
        raise PreflightError(no_region_message(e)) from e
    except (BotoCoreError, ClientError) as e:
        # Extract the error code the same way execute.py does, with a
        # type-name fallback for BotoCoreErrors that carry no response dict.
        error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
        error_name = type(e).__name__
        is_transient = (error_code in _PROBE_TRANSIENT_CODES
                        or error_name in _PROBE_TRANSIENT_CODES)
        is_hard_fail = (error_code in _PROBE_HARD_FAIL_CODES
                        or error_name in _PROBE_HARD_FAIL_CODES)
        if is_transient and not is_hard_fail:
            # Transient errors (throttling, timeouts, 5xx) only prove the probe
            # could not complete — not that the model is unusable. Warn and
            # continue: the eval runs in workshops where a whole room hits
            # Bedrock at once, so a 1-token probe getting throttled must not
            # abort the entire cohort. Keep this separate from the hard-fail
            # path so a future contributor does not collapse it back into one.
            print(
                f"⚠ {role} model '{model_id}' could not be verified due to a "
                f"transient error; execution may still fail later for the same "
                f"reason.\n  Error: {e}"
            )
            return
        # AccessDeniedException (a ClientError) on a specific model is the most
        # common restricted-account failure; name the exact model and every
        # override path so the message is directly actionable. Unknown codes
        # fail closed here as well.
        overrides = [f"the {flag} CLI flag", f"the {env_var} environment variable"]
        if config_hint:
            overrides.append("the judge.model field in eval/config.yaml")
        raise PreflightError(
            f"{role} model '{model_id}' is not invocable in this account/region.\n"
            f"Override it with one of: {', '.join(overrides)}.\n"
            f"Error: {e}"
        ) from e


def validate_credentials(
    exec_model: str | None = None,
    judge_model: str | None = None,
    check_execution: bool = True,
    check_judge: bool = False,
    skip_model_check: bool = False,
) -> dict:
    """Validate AWS credentials and model invocability before eval execution.

    Checks:
    1. sts:GetCallerIdentity — confirms valid credentials
    2. bedrock:ListFoundationModels — confirms Bedrock control-plane access
    3. A minimal bedrock-runtime Converse against each model that will be used,
       proving it is actually invocable (step 1-2 never touch the model itself).

    check_execution / check_judge gate which models are probed, so a run can
    validate either, both, or neither. skip_model_check bypasses step 3 only.

    exec_model / judge_model: None resolves at call time via execution_model_id()
    / judge_model_id() so preflight reports the model that will actually run.

    Returns caller identity dict on success.
    Raises PreflightError with actionable message on failure.
    """
    # Resolve None to the same defaults the executor/judge use, so preflight
    # reports — and probes — the models that will actually run.
    exec_model = exec_model or execution_model_id()
    judge_model = judge_model or judge_model_id()
    # 1. Validate credentials via STS
    try:
        sts = boto3.client("sts", **region_kwargs())
        identity = sts.get_caller_identity()
    except NoRegionError as e:
        # Caught before BotoCoreError (its superclass) so the message is legible:
        # a missing region should not masquerade as a credentials problem.
        raise PreflightError(no_region_message(e)) from e
    except (BotoCoreError, ClientError) as e:
        raise PreflightError(
            f"AWS credentials invalid or expired. Run 'aws sts get-caller-identity' to debug.\n"
            f"Error: {e}"
        ) from e

    account = identity["Account"]
    arn = identity["Arn"]
    print(f"✓ AWS credentials valid: account={account}, arn={arn}")

    # 2. Validate Bedrock access
    try:
        bedrock = boto3.client("bedrock", **region_kwargs())
        bedrock.list_foundation_models()
    except NoRegionError as e:
        # Caught before BotoCoreError (its superclass) so the message is legible:
        # a missing region should not masquerade as a Bedrock permissions failure.
        raise PreflightError(no_region_message(e)) from e
    except (BotoCoreError, ClientError) as e:
        raise PreflightError(
            f"Bedrock access check failed. Ensure your role has bedrock:ListFoundationModels permission.\n"
            f"Error: {e}"
        ) from e

    print("✓ Bedrock access confirmed")

    # 3. Prove each model that will run is actually invocable. Build the runtime
    # client only when we will probe, so skip_model_check avoids a needless
    # client (and any region resolution it would force).
    if skip_model_check:
        if check_execution:
            print(f"✓ Execution model: {exec_model} (invocation check skipped)")
        if check_judge:
            print(f"✓ Judge model: {judge_model} (invocation check skipped)")
    else:
        runtime = boto3.client("bedrock-runtime", **region_kwargs())
        if check_execution:
            _probe_model(runtime, exec_model, "Execution", "--model", "EVAL_MODEL_ID")
            print(f"✓ Execution model: {exec_model}")
        if check_judge:
            _probe_model(runtime, judge_model, "Judge", "--judge-model",
                         "EVAL_JUDGE_MODEL_ID", config_hint=True)
            print(f"✓ Judge model: {judge_model}")
    return {"account": account, "arn": arn}
