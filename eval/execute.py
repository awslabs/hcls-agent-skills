"""Execute prompts under baseline and skills conditions.

Supports two backends:
- 'strands': AWS Strands Agents SDK with AgentSkills plugin (default, no kiro-cli needed)
- 'kiro-cli': Original kiro-cli subprocess invocation (requires kiro-cli installed)
"""
import asyncio
import json
import logging
import re
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from subprocess import DEVNULL, PIPE

try:
    from .aws_config import region_kwargs, execution_model_id, execution_max_tokens
except ImportError:  # imported as a top-level module
    from aws_config import region_kwargs, execution_model_id, execution_max_tokens

logger = logging.getLogger(__name__)

# ─── Fail-fast counter for auth/throttle errors ──────────────────────────────

_AUTH_THROTTLE_CODES = {"ExpiredTokenException", "UnrecognizedClientException",
                        "InvalidSignatureException", "AccessDeniedException",
                        "ThrottlingException", "TooManyRequestsException"}
_MAX_CONSECUTIVE_FAILURES = 3
_consecutive_auth_errors = 0


class EvalAbortError(Exception):
    """Raised when too many consecutive auth/throttle errors occur."""


def _check_fail_fast(error: Exception) -> None:
    """Increment counter on auth/throttle errors; abort after threshold."""
    global _consecutive_auth_errors
    error_code = getattr(error, "response", {}).get("Error", {}).get("Code", "")
    error_name = type(error).__name__
    if error_code in _AUTH_THROTTLE_CODES or error_name in _AUTH_THROTTLE_CODES:
        _consecutive_auth_errors += 1
        if _consecutive_auth_errors >= _MAX_CONSECUTIVE_FAILURES:
            raise EvalAbortError(
                f"Aborting: {_consecutive_auth_errors} consecutive auth/throttle errors. "
                f"Last error: {error}"
            ) from error
    else:
        _consecutive_auth_errors = 0


def _reset_fail_fast() -> None:
    """Reset counter on successful execution."""
    global _consecutive_auth_errors
    _consecutive_auth_errors = 0


# None means "not overridden" — resolve from aws_config at call time.
# Set by run.py's --model for a module-level override. Do NOT initialize this
# to a resolved model ID: that would re-freeze the value at import time and
# defeat the whole point of execution_model_id() being a function.
DEFAULT_MODEL_ID: str | None = None
DEFAULT_SKILLS_PATH = "./skills/"
DEFAULT_BACKEND = "strands"
EXTRA_TOOLS: list[str] = []

# None means "not overridden" — resolve from aws_config at call time, exactly
# like DEFAULT_MODEL_ID. Set by run.py's --max-tokens. Do NOT initialize this to
# a resolved int: that re-freezes the value at import time and defeats the whole
# point of execution_max_tokens() being a function.
DEFAULT_MAX_TOKENS: int | None = None


def _resolve_model_id(model_id: str | None) -> str:
    """Resolve the effective execution model, late-bound at call time.

    Precedence: explicit argument > module-level DEFAULT_MODEL_ID override
    > execution_model_id() (EVAL_MODEL_ID env var > built-in fallback). Do NOT
    fold this into a default-argument expression — that re-freezes at def time.
    """
    return model_id or DEFAULT_MODEL_ID or execution_model_id()


def _resolve_max_tokens(max_tokens: int | None) -> int:
    """Resolve the effective execution max_tokens, late-bound at call time.

    Precedence: explicit argument > module-level DEFAULT_MAX_TOKENS override
    > execution_max_tokens() (EVAL_MAX_TOKENS env var > built-in fallback).
    Mirrors _resolve_model_id; do NOT fold into a default-argument expression.

    CRITICAL: the baseline and skills conditions MUST receive the IDENTICAL
    value. The arms may differ ONLY in skill availability — never in token
    ceiling — or the comparison is confounded. This resolver is condition-blind
    by design; keep it that way.
    """
    return max_tokens or DEFAULT_MAX_TOKENS or execution_max_tokens()


def _is_max_tokens_error(e: Exception) -> bool:
    """True if ``e`` is Strands' MaxTokensReachedException.

    Imported defensively: try the documented path, then fall back to matching
    on the class name so a moved import path across strands versions cannot
    silently stop us from recognising truncation. The import is kept inside the
    function so execute.py stays importable without strands installed.
    """
    try:
        from strands.types.exceptions import MaxTokensReachedException
        if isinstance(e, MaxTokensReachedException):
            return True
    except Exception:
        pass
    return type(e).__name__ == "MaxTokensReachedException"


def _recover_partial_text(agent) -> str:
    """Pull the partial assistant text Strands preserves when it truncates.

    MaxTokensReachedException itself carries only a message string; the
    truncated content is appended to the conversation history (see strands'
    recover_message_on_max_tokens_reached). Returns "" if nothing is
    recoverable, so callers can fall back to a bare marker.
    """
    try:
        for msg in reversed(agent.messages):
            if msg.get("role") != "assistant":
                continue
            parts = [b["text"] for b in msg.get("content", []) if "text" in b]
            if parts:
                return "\n".join(parts).strip()
    except (AttributeError, TypeError, KeyError):
        pass
    return ""

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _get_harness_version(backend: str) -> str:
    """Return the version string for the execution harness."""
    if backend == "strands":
        from importlib.metadata import version
        return f"strands-agents=={version('strands-agents')}"
    else:
        import subprocess
        try:
            out = subprocess.run(["kiro-cli", "--version"], capture_output=True, text=True, timeout=5)
            return f"kiro-cli=={out.stdout.strip().split()[-1]}" if out.returncode == 0 else "kiro-cli==unknown"
        except Exception:
            return "kiro-cli==unknown"


def ensure_eval_agent(skills_path: str = ".kiro/skills") -> None:
    """Create .kiro/agents/hcls-eval.json if it doesn't exist (kiro-cli backend only)."""
    agent_file = Path(".kiro/agents/hcls-eval.json")
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "name": "hcls-eval",
        "description": "HCLS evaluation agent with all domain skills",
        "resources": [f"skill://{skills_path}/**/SKILL.md"],
        "tools": ["*"],
    }
    agent_file.write_text(json.dumps(config, indent=2))


# ─── Strands backend ─────────────────────────────────────────────────────────

def _get_extra_tools():
    """Build tool instances from EXTRA_TOOLS list."""
    from strands.tools import tool
    tools = []
    if "think" in EXTRA_TOOLS:
        @tool
        def think(thought: str) -> str:
            """Use this tool to think step-by-step about complex problems before responding."""
            return "Thought recorded."
        tools.append(think)
    return tools


def _strands_build_agent(condition: str, model_id: str | None = None, max_tokens: int | None = None):
    """Build a Strands Agent for the given condition."""
    # Late-bound default: resolve DEFAULT_MODEL_ID at call time, not def time.
    # An early-bound `= DEFAULT_MODEL_ID` freezes the value when the function is
    # defined, so a later CLI/module override would be ignored. Do NOT "tidy"
    # this back to a default-argument expression.
    model_id = _resolve_model_id(model_id)
    # Same-value invariant: both conditions share ONE max_tokens (see
    # _resolve_max_tokens). The arms may differ only in skill availability, so
    # never make this condition-dependent.
    max_tokens = _resolve_max_tokens(max_tokens)
    from strands import Agent
    from strands.models.bedrock import BedrockModel
    try:
        from strands import AgentSkills
    except ImportError:
        from strands.vended_plugins.skills import AgentSkills

    # Resolve region the same way as every other client; region_name is omitted
    # (not passed as None) when unresolved so BedrockModel keeps its own default.
    # Strands' BedrockModel only sends maxTokens when configured, so we pass it
    # explicitly rather than inheriting an unknown provider default.
    model = BedrockModel(model_id=model_id, max_tokens=max_tokens, **region_kwargs())
    extra_tools = _get_extra_tools()
    if condition == "skills":
        skills_plugin = AgentSkills(skills=DEFAULT_SKILLS_PATH)
        return Agent(model=model, tools=extra_tools, plugins=[skills_plugin], callback_handler=None)
    return Agent(model=model, tools=extra_tools, callback_handler=None)


def _strands_invoke(agent, prompt_text: str) -> dict:
    """Invoke Strands agent and return response text + activated skills."""
    result = agent(prompt_text)
    text = str(result)
    # Extract activated skills from the agent's conversation messages
    activated_skills = []
    try:
        for msg in agent.messages:
            for block in msg.get("content", []):
                if "toolUse" in block and block["toolUse"].get("name") == "skills":
                    skill_name = block["toolUse"]["input"].get("skill_name", "")
                    if skill_name:
                        activated_skills.append(skill_name)
    except (AttributeError, TypeError, KeyError):
        pass
    # Prepend skill activation markers for detect_skill_flags() in build_review.py
    if activated_skills:
        markers = "\n".join(f"Reading skill: /skills/{s}/SKILL.md" for s in activated_skills)
        text = markers + "\n" + text
    return {"text": text, "activated_skills": activated_skills}


# Module-level shared executor to avoid per-call shutdown killing connections
_STRANDS_EXECUTOR = ThreadPoolExecutor(max_workers=10)


async def _execute_strands(
    prompt_id: str, prompt_text: str, condition: str,
    results_dir: Path, timeout: int, model_id: str, max_tokens: int | None = None,
) -> dict:
    """Execute via Strands SDK."""
    loop = asyncio.get_event_loop()
    agent = None
    try:
        agent = _strands_build_agent(condition, model_id, max_tokens)
        future = loop.run_in_executor(_STRANDS_EXECUTOR, _strands_invoke, agent, prompt_text)
        response = await asyncio.wait_for(future, timeout=timeout)
        _reset_fail_fast()
        return response
    except asyncio.TimeoutError:
        logger.warning(f"Timeout for {prompt_id} ({condition})")
        return {"text": "[TIMEOUT]", "activated_skills": []}
    except EvalAbortError:
        raise
    except Exception as e:
        # Handle MaxTokensReachedException SPECIFICALLY, before the generic
        # branch, so a truncated-but-partial response is preserved rather than
        # discarded. Matched version-robustly because the import path has
        # drifted across strands releases (see _is_max_tokens_error).
        if _is_max_tokens_error(e):
            effective_max = _resolve_max_tokens(max_tokens)
            partial = _recover_partial_text(agent)
            logger.warning(
                f"Truncated response for {prompt_id} ({condition}): model hit the "
                f"max_tokens={effective_max} output limit. Raise it with --max-tokens "
                f"or EVAL_MAX_TOKENS. Error: {e}"
            )
            # [TRUNCATED] marker keeps this distinguishable from [TIMEOUT]/[ERROR]
            # so run.py can treat it as not-validly-scorable.
            text = f"[TRUNCATED] {partial}" if partial else "[TRUNCATED]"
            return {"text": text, "activated_skills": [], "truncated": True}
        _check_fail_fast(e)
        logger.error(f"Error for {prompt_id} ({condition}): {e}")
        return {"text": f"[ERROR] {type(e).__name__}: {e}", "activated_skills": []}


# ─── kiro-cli backend ────────────────────────────────────────────────────────

DEFAULT_KIRO_MODEL: str | None = None  # Set via CLI --kiro-model flag


async def _execute_kiro(
    prompt_id: str, prompt_text: str, condition: str,
    results_dir: Path, timeout: int, kiro_cmd: str,
) -> dict:
    """Execute via kiro-cli subprocess (original implementation)."""
    cmd = [kiro_cmd, "chat", "--no-interactive", "--trust-all-tools", "--agent-engine", "v1"]
    if DEFAULT_KIRO_MODEL:
        cmd.extend(["--model", DEFAULT_KIRO_MODEL])
    if condition == "skills":
        cmd.extend(["--agent", "hcls-eval"])
    cmd.append(prompt_text)

    # Both conditions run from temp dirs to avoid polluting the project root.
    # Skills condition gets a symlink to .kiro/ so skill resources are discoverable.
    cwd = tempfile.mkdtemp(prefix="hcls-eval-baseline-" if condition == "baseline" else "hcls-eval-skills-")
    env = None
    if condition == "baseline":
        import os
        env = os.environ.copy()
        env["KIRO_HOME"] = cwd  # prevent loading ~/.kiro/ MCP configs
    elif condition == "skills":
        import os, shutil
        # Symlink .kiro into the temp dir so kiro-cli finds agent config + skills
        project_kiro = Path.cwd() / ".kiro"
        if project_kiro.exists():
            os.symlink(project_kiro, Path(cwd) / ".kiro")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdin=DEVNULL, stdout=PIPE, stderr=PIPE, cwd=cwd, env=env
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = _ANSI_RE.sub("", stdout.decode("utf-8", errors="replace"))
        if proc.returncode != 0:
            text = f"[ERROR] {stderr.decode('utf-8', errors='replace')}"
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        text = "[TIMEOUT]"
    except FileNotFoundError:
        text = "[ERROR] kiro-cli not found"

    return {"text": text, "activated_skills": []}


# ─── Public API ──────────────────────────────────────────────────────────────

async def execute_prompt(
    prompt_id: str,
    prompt_text: str,
    condition: str,
    results_dir: Path,
    timeout: int = 180,
    kiro_cmd: str = "kiro-cli",
    model_id: str | None = None,
    backend: str = DEFAULT_BACKEND,
    max_tokens: int | None = None,
) -> dict:
    """Execute a prompt under a condition, return {id, condition, text, cached}.

    Caches results to disk. Skips execution if cache file already exists.

    model_id: Bedrock model ID for the strands backend. None resolves at call
        time via: explicit argument > module DEFAULT_MODEL_ID override >
        execution_model_id() (EVAL_MODEL_ID env var > built-in fallback).
    max_tokens: output token ceiling for the strands backend. None resolves at
        call time via: explicit argument > module DEFAULT_MAX_TOKENS override >
        execution_max_tokens() (EVAL_MAX_TOKENS env var > built-in fallback).
    """
    # Late-bound default (see _strands_build_agent): resolve here so metadata
    # records the model actually used and CLI/module overrides take effect.
    model_id = _resolve_model_id(model_id)
    # Resolve the token ceiling here too so metadata self-documents the run's
    # limit. Both conditions resolve the SAME value — never condition-dependent.
    max_tokens = _resolve_max_tokens(max_tokens)
    cache_file = results_dir / f"{prompt_id}_{condition}.json"
    if cache_file.exists():
        cached = json.loads(cache_file.read_text())
        cached_text = cached.get("text", "")
        # Transient failures must NOT be served from cache: re-invoke so the next
        # run gets a real attempt. [ERROR] (endpoint/throttle/auth) and [TIMEOUT]
        # are transient. [TRUNCATED] is NOT transient — it carries real partial
        # model output — so it REMAINS a valid cache hit. This also self-heals
        # any already-poisoned entries written before the write-guard below.
        if not (cached_text.startswith("[ERROR]") or cached_text.startswith("[TIMEOUT]")):
            return cached | {"cached": True}

    if backend == "kiro-cli":
        response = await _execute_kiro(prompt_id, prompt_text, condition, results_dir, timeout, kiro_cmd)
    else:
        response = await _execute_strands(prompt_id, prompt_text, condition, results_dir, timeout, model_id, max_tokens)

    text = response["text"]
    activated_skills = response.get("activated_skills", [])

    result = {"id": prompt_id, "condition": condition, "text": text}
    if activated_skills:
        result["activated_skills"] = activated_skills
    result["metadata"] = {
        "backend": backend,
        "model": (DEFAULT_KIRO_MODEL or "auto") if backend == "kiro-cli" else model_id,
        "max_tokens": max_tokens,
        "tools": EXTRA_TOOLS if EXTRA_TOOLS else [],
        "skills_path": DEFAULT_SKILLS_PATH if condition == "skills" else None,
        "harness_version": _get_harness_version(backend),
    }
    # Surface truncation so downstream (run.py/report.py) can account for it and
    # a run's partial responses are attributable, not silently dropped.
    if response.get("truncated"):
        result["metadata"]["truncated"] = True
    # Only cache non-transient outcomes. [ERROR] (endpoint/throttle/auth) and
    # [TIMEOUT] are transient failures: caching them POISONS subsequent runs by
    # serving the error back instead of retrying, so we leave NO cache entry.
    # [TRUNCATED] is DIFFERENT — it contains real partial model output, so it IS
    # cached (and stays distinguishable downstream from a transient failure).
    is_transient_failure = text.startswith("[ERROR]") or text.startswith("[TIMEOUT]")
    if not is_transient_failure:
        cache_file.write_text(json.dumps(result, indent=2))
    return result | {"cached": False}


async def run_all(
    prompts: list[dict],
    results_dir: Path,
    parallel: int = 1,
    timeout: int = 180,
    kiro_cmd: str = "kiro-cli",
    model_id: str | None = None,
    backend: str = DEFAULT_BACKEND,
    max_tokens: int | None = None,
) -> list[dict]:
    """Execute all prompts under both conditions.

    Args:
        prompts: List of dicts with 'id' and 'prompt' keys.
        results_dir: Directory to cache response JSON files.
        parallel: Max concurrent executions.
        timeout: Seconds before killing a single execution.
        kiro_cmd: Command for kiro-cli backend.
        model_id: Bedrock model ID for strands backend. None resolves at call
            time via: explicit argument > module DEFAULT_MODEL_ID override >
            execution_model_id() (EVAL_MODEL_ID env var > built-in fallback).
        backend: 'strands' (default) or 'kiro-cli'.
        max_tokens: output token ceiling for strands backend. None resolves at
            call time via: explicit argument > module DEFAULT_MAX_TOKENS override
            > execution_max_tokens() (EVAL_MAX_TOKENS env var > built-in
            fallback). The SAME value is used for BOTH conditions — the arms may
            differ ONLY in skill availability, never in token ceiling.
    """
    # Late-bound default (see _strands_build_agent): resolve here so a CLI
    # --model override of DEFAULT_MODEL_ID is honored. Do NOT restore
    # `= DEFAULT_MODEL_ID` in the signature.
    model_id = _resolve_model_id(model_id)
    # Resolve once for the whole run so every prompt and both conditions share
    # the identical ceiling (see _resolve_max_tokens).
    max_tokens = _resolve_max_tokens(max_tokens)
    if backend == "kiro-cli":
        ensure_eval_agent()
    results_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(parallel)

    async def run_one(prompt, condition):
        async with sem:
            return await execute_prompt(
                prompt["id"], prompt["prompt"], condition,
                results_dir, timeout, kiro_cmd, model_id, backend, max_tokens,
            )

    tasks = []
    for p in prompts:
        for cond in ["baseline", "skills"]:
            tasks.append(run_one(p, cond))
    return await asyncio.gather(*tasks)
