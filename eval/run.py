#!/usr/bin/env python3
"""HCLS Skills Evaluation Suite — run the full pipeline."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml

try:
    from .execute import run_all, ensure_eval_agent
    from . import execute as _ex
    from .judge import get_bedrock_client, score_response, DIMENSIONS
    from .judge_pairwise import score_pairwise
    from .report import generate_report
    from .preflight import validate_credentials, PreflightError
    from .execute import EvalAbortError
    from .aws_config import FALLBACK_JUDGE_MODEL_ID, FALLBACK_EXECUTION_MAX_TOKENS
except ImportError:
    from execute import run_all, ensure_eval_agent
    import execute as _ex
    from judge import get_bedrock_client, score_response, DIMENSIONS
    from judge_pairwise import score_pairwise
    from report import generate_report
    from preflight import validate_credentials, PreflightError
    from execute import EvalAbortError
    from aws_config import FALLBACK_JUDGE_MODEL_ID, FALLBACK_EXECUTION_MAX_TOKENS


def load_prompts(prompts_dir: Path) -> list[dict]:
    """Load all prompt YAML files."""
    prompts = []
    for d in [prompts_dir / "single", prompts_dir / "cross"]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.yaml")):
            prompts.append(yaml.safe_load(f.read_text()))
    return prompts


def main():
    parser = argparse.ArgumentParser(description="HCLS Skills Evaluation Suite")
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--prompts-dir", type=Path, default=Path("eval/prompts"))
    parser.add_argument("--results-dir", type=Path, default=Path("eval/results"))
    parser.add_argument("--skip-execution", action="store_true")
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("eval/config.yaml"))
    parser.add_argument("--version", type=str, default=None, help="Version label (e.g., v2). Saves scores as scores_<version>.json")
    parser.add_argument("--pairwise", action="store_true", help="Use pairwise judge (both responses in one call, randomized position)")
    parser.add_argument("--backend", type=str, default="strands", choices=["strands", "kiro-cli"],
                        help="Execution backend: 'strands' (default, uses Bedrock directly) or 'kiro-cli' (requires kiro subscription)")
    parser.add_argument("--skills", type=str, default=None,
                        help="Path to skills directory (default: ./skills/)")
    parser.add_argument("--model", type=str, default=None,
                        help="Bedrock model ID for execution (strands backend only). "
                             "Precedence: --model > EVAL_MODEL_ID env var > built-in fallback.")
    parser.add_argument("--judge-model", type=str, default=None,
                        help="Bedrock model ID for the LLM judge. Precedence: --judge-model > "
                             "EVAL_JUDGE_MODEL_ID env var > eval/config.yaml > built-in fallback.")
    parser.add_argument("--skip-model-check", action="store_true",
                        help="Skip the preflight Converse probe that verifies each model is invocable "
                             "(credential/region checks still run).")
    parser.add_argument("--max-tokens", type=int, default=None,
                        help="Max output tokens for execution (strands backend only). Precedence: "
                             "--max-tokens > EVAL_MAX_TOKENS env var > eval/config.yaml > built-in "
                             "fallback. Applied IDENTICALLY to both conditions.")
    parser.add_argument("--tools", type=str, nargs="*", default=None,
                        help="Extra tools for both conditions (e.g., --tools think). Strands backend only.")
    parser.add_argument("--kiro-model", type=str, default=None,
                        help="Pin kiro-cli model (e.g., claude-sonnet-4.5). kiro-cli backend only.")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    # Judge model precedence (identical shape to execution's, with config.yaml as
    # an extra judge-only tier): --judge-model > EVAL_JUDGE_MODEL_ID env var >
    # eval/config.yaml > built-in fallback. This single value is used for BOTH
    # scoring and generate_report so the report never names a different model
    # than the one that judged.
    judge_model = (
        args.judge_model
        or os.environ.get("EVAL_JUDGE_MODEL_ID")
        or cfg.get("judge", {}).get("model")
        or FALLBACK_JUDGE_MODEL_ID
    )
    # Execution max_tokens precedence (same shape as the judge model's, with
    # config.yaml as an extra tier): --max-tokens > EVAL_MAX_TOKENS env var >
    # eval/config.yaml > built-in fallback. This SINGLE value feeds BOTH the
    # baseline and skills conditions — the arms may differ ONLY in skill
    # availability, never in token ceiling, or the comparison is confounded.
    max_tokens = (
        args.max_tokens
        or (int(os.environ["EVAL_MAX_TOKENS"]) if os.environ.get("EVAL_MAX_TOKENS") else None)
        or cfg.get("execution", {}).get("max_tokens")
        or FALLBACK_EXECUTION_MAX_TOKENS
    )
    # Judge inference knobs read from config so editing eval/config.yaml is not
    # silently ignored (they were previously hardcoded in the judge modules).
    # Thread them from the loaded config, as the judge model already is.
    judge_cfg = cfg.get("judge", {})
    judge_max_tokens = judge_cfg.get("max_tokens", 2048)
    judge_temperature = judge_cfg.get("temperature", 0.0)
    judge_retries = judge_cfg.get("retries", 3)
    prompts = load_prompts(args.prompts_dir)
    print(f"Loaded {len(prompts)} prompts")

    # Pre-flight: validate credentials before spending time on execution. Probe
    # the execution model only when execution will run, the judge model only
    # when judging will run; skip entirely if both phases are skipped.
    if not (args.skip_execution and args.skip_judge):
        print("\n=== Pre-flight credential check ===")
        try:
            validate_credentials(
                exec_model=args.model,
                judge_model=judge_model,
                check_execution=not args.skip_execution,
                check_judge=not args.skip_judge,
                skip_model_check=args.skip_model_check,
            )
        except PreflightError as e:
            print(f"\n✗ Pre-flight failed:\n{e}", file=sys.stderr)
            sys.exit(1)

    # Override config with CLI args. Mutate the single execute-module object
    # bound at import (_ex) so overrides land on the same module the running
    # code reads — importing it again here could bind a distinct object under
    # the top-level-script invocation style and silently drop the overrides.
    if args.skills:
        _ex.DEFAULT_SKILLS_PATH = args.skills
    if args.model:
        _ex.DEFAULT_MODEL_ID = args.model
    # Pin the run-wide execution token ceiling on the shared execute module so
    # every execute_prompt call (both conditions) resolves the identical value.
    _ex.DEFAULT_MAX_TOKENS = max_tokens
    if args.tools:
        _ex.EXTRA_TOOLS = args.tools
    if args.kiro_model:
        _ex.DEFAULT_KIRO_MODEL = args.kiro_model

    responses_dir = args.results_dir / "responses" / args.version if args.version else args.results_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Execute
    if not args.skip_execution:
        print("\n=== Executing prompts ===")
        try:
            asyncio.run(run_all(
                prompts, responses_dir,
                parallel=args.parallel,
                timeout=cfg["execution"]["timeout_seconds"],
                kiro_cmd=cfg["execution"]["kiro_cmd"],
                model_id=args.model,
                backend=args.backend,
                max_tokens=max_tokens,
            ))
        except EvalAbortError as e:
            print(f"\n✗ {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Responses cached in {responses_dir}")

    # Step 2: Judge
    if not args.skip_judge:
        print("\n=== Scoring responses ===")
        client = get_bedrock_client()
        scores_filename = f"scores_{args.version}.json" if args.version else "scores.json"

        # Load existing scores for caching
        scores_file = args.results_dir / scores_filename
        existing_scores = {}
        if scores_file.exists():
            for s in json.loads(scores_file.read_text()):
                existing_scores[s["id"]] = s

        scored = []
        for p in prompts:
            pid = p["id"]
            domain = p.get("domain", "healthcare")
            entry = {"id": pid, "domain": domain, "target_skills": p.get("target_skills", [])}

            # Check if we already have valid scores for this prompt
            cached = existing_scores.get(pid)
            needs_rescore = False
            if cached:
                for cond in ["baseline", "skills"]:
                    resp_file = responses_dir / f"{pid}_{cond}.json"
                    if resp_file.exists():
                        resp_data = json.loads(resp_file.read_text())
                        text = resp_data.get("text", "")
                        # Rescore if response is valid but score is zero (was previously timed out)
                        if not (text.startswith("[TIMEOUT]") or text.startswith("[ERROR]") or text.startswith("[TRUNCATED]")) and sum(cached.get(cond, {}).values()) == 0:
                            needs_rescore = True
                            break

            if cached and not needs_rescore:
                entry["baseline"] = cached["baseline"]
                entry["skills"] = cached["skills"]
                entry["baseline_reasoning"] = cached.get("baseline_reasoning", "")
                entry["skills_reasoning"] = cached.get("skills_reasoning", "")
                # Carry the verdict/drop metadata forward too. Copying only the
                # score dicts stripped a cached pairwise prompt's `winner` and any
                # `dropped`/`drop_reason`, re-emitting a truncated/error prompt as
                # neither validly scored nor dropped (limbo). Preserve every
                # verdict field so cache reuse is faithful.
                for k in ("winner", "position", "reasoning", "dropped", "drop_reason"):
                    if k in cached:
                        entry[k] = cached[k]
                scored.append(entry)
                continue

            # Score fresh
            if args.pairwise:
                # Pairwise: send both responses in one call
                b_file = responses_dir / f"{pid}_baseline.json"
                s_file = responses_dir / f"{pid}_skills.json"
                b_text = json.loads(b_file.read_text()).get("text", "") if b_file.exists() else ""
                s_text = json.loads(s_file.read_text()).get("text", "") if s_file.exists() else ""
                if (b_text.startswith("[TIMEOUT]") or b_text.startswith("[ERROR]") or b_text.startswith("[TRUNCATED]") or
                    s_text.startswith("[TIMEOUT]") or s_text.startswith("[ERROR]") or s_text.startswith("[TRUNCATED]") or not b_text or not s_text):
                    # A transient failure ([ERROR]/[TIMEOUT]), a truncated partial
                    # ([TRUNCATED]), or an empty body is NOT validly scorable:
                    # record the prompt as DROPPED with a reason rather than
                    # letting the all-zero scores become a counted tie.
                    entry["baseline"] = {d: 0 for d in DIMENSIONS}
                    entry["skills"] = {d: 0 for d in DIMENSIONS}
                    entry["dropped"] = True
                    # A [TRUNCATED] arm is a real but token-capped answer, not a
                    # failure, so it earns its OWN honest reason distinct from
                    # response_error — conflating them hides a token-ceiling
                    # problem behind a generic error label. It is STILL dropped:
                    # scoring a truncated answer against a complete one is unfair.
                    if b_text.startswith("[TRUNCATED]") or s_text.startswith("[TRUNCATED]"):
                        entry["drop_reason"] = "response_truncated"
                    else:
                        entry["drop_reason"] = "response_error"
                else:
                    result = score_pairwise(client, p["prompt"], b_text, s_text, domain, judge_model,
                                            retries=judge_retries, max_tokens=judge_max_tokens,
                                            temperature=judge_temperature)
                    entry["baseline"] = result["baseline"]
                    entry["skills"] = result["skills"]
                    entry["position"] = result["position"]
                    entry["reasoning"] = result.get("reasoning", "")
                    # A judge failure (exception or unparseable output) is flagged
                    # by score_pairwise with winner=="error". It MUST be dropped
                    # with a reason, never silently recorded as a 5-5 tie.
                    if result.get("winner") == "error":
                        entry["dropped"] = True
                        entry["drop_reason"] = "judge_error"
                    else:
                        entry["winner"] = result["winner"]
            else:
                # Independent: score each response separately
                for cond in ["baseline", "skills"]:
                    cache_file = responses_dir / f"{pid}_{cond}.json"
                    if not cache_file.exists():
                        entry[cond] = {d: 0 for d in DIMENSIONS}
                        continue
                    resp_data = json.loads(cache_file.read_text())
                    text = resp_data.get("text", "")
                    if text.startswith("[TIMEOUT]") or text.startswith("[ERROR]") or text.startswith("[TRUNCATED]"):
                        entry[cond] = {d: 0 for d in DIMENSIONS}
                    else:
                        scores = score_response(client, p["prompt"], text, domain, judge_model,
                                                retries=judge_retries, max_tokens=judge_max_tokens,
                                                temperature=judge_temperature)
                        entry[cond] = {d: scores.get(d, 0) for d in DIMENSIONS}
                        entry[cond + "_reasoning"] = scores.get("reasoning", "")
            scored.append(entry)
            print(f"  Scored {pid}")

        # Reconciliation invariant: EVERY prompt in the scores list must end up
        # either validly scored or explicitly dropped with a reason — never
        # limbo (neither). A prompt is "valid" iff it carries a pairwise `winner`
        # or at least one non-zero score; anything else that is not already
        # flagged dropped is force-dropped here (e.g. a pre-drop-machinery cache
        # entry with zero scores whose arms are now truncated). The assert makes
        # num_valid + num_dropped reconcile with num_total and prevents silent
        # regression of this guarantee.
        def _is_valid(e: dict) -> bool:
            return (
                "winner" in e
                or sum(e.get("baseline", {}).values()) > 0
                or sum(e.get("skills", {}).values()) > 0
            )

        for entry in scored:
            if not entry.get("dropped") and not _is_valid(entry):
                entry["dropped"] = True
                entry["drop_reason"] = "unscored"
        assert all(e.get("dropped") or _is_valid(e) for e in scored), (
            "reconciliation failed: a prompt is neither validly scored nor dropped"
        )

        (args.results_dir / scores_filename).write_text(json.dumps(scored, indent=2))
    else:
        scores_filename = f"scores_{args.version}.json" if args.version else "scores.json"
        scored = json.loads((args.results_dir / scores_filename).read_text())

    # Step 3: Report
    print("\n=== Generating report ===")
    version_suffix = f"_{args.version}" if args.version else ""
    report = generate_report(scored, args.results_dir, judge_model, version=args.version, responses_dir=responses_dir, execution_model=args.model, prompts_dir=args.prompts_dir)
    overall = report["summary"]["overall_delta"]
    print(f"Overall delta: {overall:+.1f}")
    print(f"Report: {args.results_dir / f'report{version_suffix}.md'}")

    sys.exit(0 if overall >= 0 else 1)


if __name__ == "__main__":
    main()
