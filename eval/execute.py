"""Execute kiro-cli prompts under baseline and skills conditions."""
import asyncio
import json
import os
import re
import tempfile
from pathlib import Path
from subprocess import DEVNULL, PIPE

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def ensure_eval_agent(skills_path: str = ".kiro/skills") -> None:
    """Create .kiro/agents/hcls-eval.json if it doesn't exist."""
    agent_file = Path(".kiro/agents/hcls-eval.json")
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "name": "hcls-eval",
        "description": "HCLS evaluation agent with all domain skills",
        "resources": [f"skill://{skills_path}/**/SKILL.md"],
        "tools": ["*"],
    }
    agent_file.write_text(json.dumps(config, indent=2))


async def execute_prompt(
    prompt_id: str,
    prompt_text: str,
    condition: str,
    results_dir: Path,
    timeout: int = 180,
    kiro_cmd: str = "kiro-cli",
) -> dict:
    """Execute a prompt under a condition, return {text, cached}."""
    cache_file = results_dir / f"{prompt_id}_{condition}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text()) | {"cached": True}

    cmd = [kiro_cmd, "chat", "--no-interactive", "--trust-all-tools"]
    if condition == "skills":
        cmd.extend(["--agent", "hcls-eval"])
    cmd.append(prompt_text)

    # Baseline runs from a temp dir with no .kiro/ to prevent skill auto-discovery
    cwd = None
    if condition == "baseline":
        cwd = tempfile.mkdtemp(prefix="hcls-eval-baseline-")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdin=DEVNULL, stdout=PIPE, stderr=PIPE, cwd=cwd
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

    result = {"id": prompt_id, "condition": condition, "text": text}
    cache_file.write_text(json.dumps(result, indent=2))
    return result | {"cached": False}


async def run_all(
    prompts: list[dict],
    results_dir: Path,
    parallel: int = 1,
    timeout: int = 180,
    kiro_cmd: str = "kiro-cli",
) -> list[dict]:
    """Execute all prompts under both conditions."""
    ensure_eval_agent()
    results_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(parallel)

    async def run_one(prompt, condition):
        async with sem:
            return await execute_prompt(
                prompt["id"], prompt["prompt"], condition,
                results_dir, timeout, kiro_cmd,
            )

    tasks = []
    for p in prompts:
        for cond in ["baseline", "skills"]:
            tasks.append(run_one(p, cond))
    return await asyncio.gather(*tasks)
