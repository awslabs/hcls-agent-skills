"""Pre-flight credential validation for the eval suite."""
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoRegionError

try:
    from .aws_config import region_kwargs, DEFAULT_EXECUTION_MODEL_ID
except ImportError:  # run as a standalone script
    from aws_config import region_kwargs, DEFAULT_EXECUTION_MODEL_ID


class PreflightError(Exception):
    """Raised when credential pre-flight checks fail."""


def validate_credentials(model_id: str | None = None) -> dict:
    """Validate AWS credentials before eval execution.

    Checks:
    1. sts:GetCallerIdentity — confirms valid credentials
    2. bedrock:ListFoundationModels — confirms Bedrock access

    Returns caller identity dict on success.
    Raises PreflightError with actionable message on failure.
    """
    # Resolve None to the same default the executor uses (DEFAULT_EXECUTION_MODEL_ID),
    # so preflight reports — and reasons about — the model that will actually run.
    model_id = model_id or DEFAULT_EXECUTION_MODEL_ID
    # 1. Validate credentials via STS
    try:
        sts = boto3.client("sts", **region_kwargs())
        identity = sts.get_caller_identity()
    except NoRegionError as e:
        # Caught before BotoCoreError (its superclass) so the message is legible:
        # a missing region should not masquerade as a credentials problem.
        raise PreflightError(
            "No AWS region configured. Set AWS_REGION (or AWS_DEFAULT_REGION), "
            "or set a default region in your AWS profile/config.\n"
            f"Error: {e}"
        ) from e
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
        raise PreflightError(
            "No AWS region configured. Set AWS_REGION (or AWS_DEFAULT_REGION), "
            "or set a default region in your AWS profile/config.\n"
            f"Error: {e}"
        ) from e
    except (BotoCoreError, ClientError) as e:
        raise PreflightError(
            f"Bedrock access check failed. Ensure your role has bedrock:ListFoundationModels permission.\n"
            f"Error: {e}"
        ) from e

    print("✓ Bedrock access confirmed")
    print(f"✓ Execution model: {model_id}")
    return {"account": account, "arn": arn}
