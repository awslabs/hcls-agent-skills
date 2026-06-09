#!/usr/bin/env python3
"""HCLS Skills Evaluation Suite — run the full pipeline."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import yaml

try:
    from .execute import run_all, ensure_eval_agent
    from .judge import get_bedrock_client, score_response, DIMENSIONS
    from .judge_pairwise import score_pairwise
    from .report import generate_report
except ImportError:
    from execute import run_all, ensure_eval_agent
    from judge import get_bedrock_client, score_response, DIMENSIONS
    from judge_pairwise import score_pairwise
    from report import generate_report


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
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    prompts = load_prompts(args.prompts_dir)
    print(f"Loaded {len(prompts)} prompts")

    responses_dir = args.results_dir / "responses" / args.version if args.version else args.results_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Execute
    if not args.skip_execution:
        print("\n=== Executing prompts ===")
        asyncio.run(run_all(
            prompts, responses_dir,
            parallel=args.parallel,
            timeout=cfg["execution"]["timeout_seconds"],
            kiro_cmd=cfg["execution"]["kiro_cmd"],
        ))
        print(f"Responses cached in {responses_dir}")

    # Step 2: Judge
    if not args.skip_judge:
        print("\n=== Scoring responses ===")
        client = get_bedrock_client()
        judge_model = cfg["judge"]["model"]
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
                        if not (text.startswith("[TIMEOUT]") or text.startswith("[ERROR]")) and sum(cached.get(cond, {}).values()) == 0:
                            needs_rescore = True
                            break

            if cached and not needs_rescore:
                entry["baseline"] = cached["baseline"]
                entry["skills"] = cached["skills"]
                entry["baseline_reasoning"] = cached.get("baseline_reasoning", "")
                entry["skills_reasoning"] = cached.get("skills_reasoning", "")
                scored.append(entry)
                continue

            # Score fresh
            if args.pairwise:
                # Pairwise: send both responses in one call
                b_file = responses_dir / f"{pid}_baseline.json"
                s_file = responses_dir / f"{pid}_skills.json"
                b_text = json.loads(b_file.read_text()).get("text", "") if b_file.exists() else ""
                s_text = json.loads(s_file.read_text()).get("text", "") if s_file.exists() else ""
                if (b_text.startswith("[TIMEOUT]") or b_text.startswith("[ERROR]") or
                    s_text.startswith("[TIMEOUT]") or s_text.startswith("[ERROR]") or not b_text or not s_text):
                    entry["baseline"] = {d: 0 for d in DIMENSIONS}
                    entry["skills"] = {d: 0 for d in DIMENSIONS}
                else:
                    result = score_pairwise(client, p["prompt"], b_text, s_text, domain, judge_model)
                    entry["baseline"] = result["baseline"]
                    entry["skills"] = result["skills"]
                    entry["winner"] = result["winner"]
                    entry["position"] = result["position"]
                    entry["reasoning"] = result.get("reasoning", "")
            else:
                # Independent: score each response separately
                for cond in ["baseline", "skills"]:
                    cache_file = responses_dir / f"{pid}_{cond}.json"
                    if not cache_file.exists():
                        entry[cond] = {d: 0 for d in DIMENSIONS}
                        continue
                    resp_data = json.loads(cache_file.read_text())
                    text = resp_data.get("text", "")
                    if text.startswith("[TIMEOUT]") or text.startswith("[ERROR]"):
                        entry[cond] = {d: 0 for d in DIMENSIONS}
                    else:
                        scores = score_response(client, p["prompt"], text, domain, judge_model)
                        entry[cond] = {d: scores.get(d, 0) for d in DIMENSIONS}
                        entry[cond + "_reasoning"] = scores.get("reasoning", "")
            scored.append(entry)
            print(f"  Scored {pid}")

        (args.results_dir / scores_filename).write_text(json.dumps(scored, indent=2))
    else:
        scores_filename = f"scores_{args.version}.json" if args.version else "scores.json"
        scored = json.loads((args.results_dir / scores_filename).read_text())

    # Step 3: Report
    print("\n=== Generating report ===")
    version_suffix = f"_{args.version}" if args.version else ""
    report = generate_report(scored, args.results_dir, cfg["judge"]["model"], version=args.version)
    overall = report["summary"]["overall_delta"]
    print(f"Overall delta: {overall:+.1f}")
    print(f"Report: {args.results_dir / f'report{version_suffix}.md'}")

    sys.exit(0 if overall >= 0 else 1)


if __name__ == "__main__":
    main()
