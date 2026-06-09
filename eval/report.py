"""Generate JSON and markdown evaluation reports."""
import json
import math
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import ttest_rel

DIMENSIONS = [
    "scientific_accuracy", "coherence", "relevance",
    "critical_thinking", "actionability",
]


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0


def _std(vals):
    if len(vals) < 2:
        return 0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _cohens_d_paired(diffs: list[float]) -> float:
    if not diffs or len(diffs) < 2:
        return 0.0
    m = _mean(diffs)
    s = _std(diffs)
    return round(m / s, 2) if s > 0 else 0.0


def _interpret_d(d: float) -> str:
    ad = abs(d)
    if ad >= 0.8: return "Large"
    if ad >= 0.5: return "Medium"
    if ad >= 0.2: return "Small"
    return "Negligible"


def _paired_ttest_p(baseline_vals: list[float], skills_vals: list[float]) -> float:
    """Return two-tailed p-value from scipy paired t-test."""
    if len(baseline_vals) < 2:
        return 1.0
    _, p = ttest_rel(skills_vals, baseline_vals)
    return float(p)


def _skill_from_id(prompt_id: str) -> str:
    """Extract skill name from prompt id like 'drug-repurposing-03'."""
    parts = prompt_id.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0]
    return prompt_id


def generate_report(scores: list[dict], results_dir: Path, judge_model: str, version: str = None, responses_dir: Path = None) -> dict:
    """Generate report from scored results."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        commit = "unknown"

    # Identify timeouts/errors (all-zero scores in either condition)
    valid_scores = []
    dropped = defaultdict(list)  # skill -> list of (prompt_id, reason)
    for s in scores:
        b_sum = sum(s["baseline"].values())
        sk_sum = sum(s["skills"].values())
        skill = _skill_from_id(s["id"])
        if b_sum == 0 and sk_sum == 0:
            dropped[skill].append((s["id"], "both"))
        elif b_sum == 0:
            dropped[skill].append((s["id"], "baseline"))
        elif sk_sum == 0:
            dropped[skill].append((s["id"], "skills"))
        else:
            valid_scores.append(s)

    # Compute per-prompt deltas (valid only)
    per_prompt = []
    for s in valid_scores:
        delta = {d: s["skills"].get(d, 0) - s["baseline"].get(d, 0) for d in DIMENSIONS}
        per_prompt.append({
            "id": s["id"], "domain": s["domain"],
            "target_skills": s["target_skills"],
            "baseline": {d: s["baseline"].get(d, 0) for d in DIMENSIONS},
            "skills": {d: s["skills"].get(d, 0) for d in DIMENSIONS},
            "delta": delta,
            "winner": s.get("winner", ""),
        })

    # Compute overall means
    n = len(per_prompt) or 1
    baseline_mean = {d: sum(p["baseline"][d] for p in per_prompt) / n for d in DIMENSIONS}
    skills_mean = {d: sum(p["skills"][d] for p in per_prompt) / n for d in DIMENSIONS}
    delta_mean = {d: skills_mean[d] - baseline_mean[d] for d in DIMENSIONS}
    overall_delta = sum(delta_mean.values()) / len(DIMENSIONS)

    # Per-skill aggregation
    skill_prompts = defaultdict(list)
    for p in per_prompt:
        skill = _skill_from_id(p["id"])
        skill_prompts[skill].append(p)

    per_skill = {}
    for skill, prompts in sorted(skill_prompts.items()):
        sk = {"n": len(prompts), "domain": prompts[0]["domain"]}
        for cond in ["baseline", "skills", "delta"]:
            sk[cond] = {}
            for d in DIMENSIONS:
                vals = [p[cond][d] for p in prompts]
                sk[cond][d] = {"mean": round(_mean(vals), 1), "std": round(_std(vals), 1)}
        # Paired t-test per dimension
        sk["pvalues"] = {}
        for d in DIMENSIONS:
            baseline_vals = [p["baseline"][d] for p in prompts]
            skills_vals = [p["skills"][d] for p in prompts]
            sk["pvalues"][d] = round(_paired_ttest_p(baseline_vals, skills_vals), 4)
        sk["mean_delta"] = round(_mean([
            sum(p["delta"].values()) / len(DIMENSIONS) for p in prompts
        ]), 1)
        per_skill[skill] = sk

    # Detect skill activation from response files
    activated_prompts = set()  # prompt IDs where intended skill was loaded
    if responses_dir is None:
        responses_dir = results_dir / "responses"
    if responses_dir.exists():
        for p in per_prompt:
            pid = p["id"]
            resp_file = responses_dir / f"{pid}_skills.json"
            if not resp_file.exists():
                continue
            resp_data = json.loads(resp_file.read_text())
            text = resp_data.get("text", "")
            # Detect loaded skills
            loaded = set(re.findall(r'/skills/([a-z0-9-]+)/SKILL\.md', text))
            preamble = text[:1000]
            for m in re.findall(r'(?:skill|read|load|check).*?([a-z]+-[a-z]+(?:-[a-z]+)*)', preamble, re.IGNORECASE):
                if (Path("skills") / m).is_dir():
                    loaded.add(m)
            target = set(p.get("target_skills", []))
            if target & loaded:
                activated_prompts.add(pid)

    # Skills-activated per-skill aggregation
    per_skill_activated = {}
    for skill, prompts in sorted(skill_prompts.items()):
        active_prompts = [p for p in prompts if p["id"] in activated_prompts]
        if not active_prompts:
            continue
        sk = {"n": len(active_prompts), "domain": active_prompts[0]["domain"]}
        for cond in ["baseline", "skills", "delta"]:
            sk[cond] = {}
            for d in DIMENSIONS:
                vals = [p[cond][d] for p in active_prompts]
                sk[cond][d] = {"mean": round(_mean(vals), 1), "std": round(_std(vals), 1)}
        sk["pvalues"] = {}
        for d in DIMENSIONS:
            baseline_vals = [p["baseline"][d] for p in active_prompts]
            skills_vals = [p["skills"][d] for p in active_prompts]
            sk["pvalues"][d] = round(_paired_ttest_p(baseline_vals, skills_vals), 4)
        sk["mean_delta"] = round(_mean([
            sum(p["delta"].values()) / len(DIMENSIONS) for p in active_prompts
        ]), 1)
        per_skill_activated[skill] = sk

    report = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": commit,
            "judge_model": judge_model,
            "num_prompts_total": len(scores),
            "num_prompts_valid": len(valid_scores),
            "num_dropped": sum(len(v) for v in dropped.values()),
            "num_skills": len(per_skill),
        },
        "summary": {
            "baseline_mean": {d: round(v, 1) for d, v in baseline_mean.items()},
            "skills_mean": {d: round(v, 1) for d, v in skills_mean.items()},
            "delta_mean": {d: round(v, 1) for d, v in delta_mean.items()},
            "overall_delta": round(overall_delta, 1),
        },
        "per_skill": per_skill,
        "per_prompt": per_prompt,
    }

    # Write JSON
    results_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"_{version}" if version else ""
    (results_dir / f"report{suffix}.json").write_text(json.dumps(report, indent=2))

    # Compute win rates and Cohen's d for v3 format
    def _prompt_win(p):
        # Use judge's explicit winner field if available (pairwise mode)
        w = p.get("winner", "")
        if w == "skills":
            return 1
        if w == "baseline":
            return 0
        if w == "tie":
            return 0.5
        # Fallback: compute from dimension scores
        s_sum = sum(p["skills"][d] for d in DIMENSIONS)
        b_sum = sum(p["baseline"][d] for d in DIMENSIONS)
        return 1 if s_sum > b_sum else (0 if s_sum < b_sum else 0.5)

    overall_wins = [_prompt_win(p) for p in per_prompt]
    overall_win_rate = round(_mean(overall_wins) * 100, 1) if overall_wins else 0

    dim_win_rates = {}
    dim_cohens = {}
    for d in DIMENSIONS:
        wins = [1 if p["skills"][d] > p["baseline"][d] else (0 if p["skills"][d] < p["baseline"][d] else 0.5) for p in per_prompt]
        dim_win_rates[d] = round(_mean(wins) * 100, 1) if wins else 0
        diffs = [p["skills"][d] - p["baseline"][d] for p in per_prompt]
        dim_cohens[d] = _cohens_d_paired(diffs)

    overall_diffs = [sum(p["skills"][d] - p["baseline"][d] for d in DIMENSIONS) / len(DIMENSIONS) for p in per_prompt]
    overall_cohens_d = _cohens_d_paired(overall_diffs)

    # Per-skill win rate and Cohen's d
    skill_win_rates = {}
    skill_cohens = {}
    for skill, prompts in skill_prompts.items():
        wins = [_prompt_win(p) for p in prompts]
        skill_win_rates[skill] = round(_mean(wins) * 100, 1)
        diffs = [sum(p["skills"][d] - p["baseline"][d] for d in DIMENSIONS) / len(DIMENSIONS) for p in prompts]
        skill_cohens[skill] = _cohens_d_paired(diffs)

    # Write markdown
    md = ["# HCLS Skills Evaluation Report\n"]
    md.append(f"**Date:** {report['metadata']['timestamp']}  ")
    md.append(f"**Commit:** {commit}  ")
    md.append(f"**Judge:** {judge_model}  ")
    md.append(f"**Prompts:** {len(valid_scores)} valid / {len(scores)} total ({sum(len(v) for v in dropped.values())} dropped due to timeout/error)\n")
    baseline_timeouts = sum(1 for v in dropped.values() for _, r in v if r in ("baseline", "both"))
    skills_timeouts = sum(1 for v in dropped.values() for _, r in v if r in ("skills", "both"))
    md.append(f"**Timeouts:** {baseline_timeouts} baseline, {skills_timeouts} skills\n")

    # Win Rate table
    md.append(f"## Win Rate: {overall_win_rate}%\n")
    md.append("| Dimension | Win Rate | Ties | Loss Rate |")
    md.append("|---|---|---|---|")
    for d in DIMENSIONS:
        wins = sum(1 for p in per_prompt if p["skills"][d] > p["baseline"][d])
        ties = sum(1 for p in per_prompt if p["skills"][d] == p["baseline"][d])
        losses = len(per_prompt) - wins - ties
        md.append(f"| {d} | {dim_win_rates[d]:.1f}% | {ties} | {round(losses/max(len(per_prompt),1)*100,1):.1f}% |")
    md.append(f"| **Overall** | **{overall_win_rate}%** | — | — |")
    md.append("")

    # Effect Size table
    md.append("## Effect Size (Cohen's d)\n")
    md.append("| Dimension | Cohen's d | Interpretation | Delta |")
    md.append("|---|---|---|---|")
    for d in DIMENSIONS:
        md.append(f"| {d} | {dim_cohens[d]:+.2f} | {_interpret_d(dim_cohens[d])} | {delta_mean[d]:+.1f} |")
    md.append(f"| **Overall** | **{overall_cohens_d:+.2f}** | **{_interpret_d(overall_cohens_d)}** | **{overall_delta:+.1f}** |")
    md.append("")

    # Per-Skill Results — include v3 comparison if available
    v3_path_psk = results_dir / "scores_v3.json"
    v3_skill_wr = {}
    if v3_path_psk.exists():
        _v3s = json.loads(v3_path_psk.read_text())
        _v3v = [s for s in _v3s if sum(s["baseline"].values()) > 0 and sum(s["skills"].values()) > 0]
        _v3sw = {}
        for s in _v3v:
            sk_name = _skill_from_id(s["id"])
            _v3sw.setdefault(sk_name, {"wins": 0, "n": 0})
            _v3sw[sk_name]["n"] += 1
            if s.get("winner") == "skills":
                _v3sw[sk_name]["wins"] += 1
        v3_skill_wr = {k: round(v["wins"]/v["n"]*100, 1) if v["n"] > 0 else 0 for k, v in _v3sw.items()}

    if v3_skill_wr:
        md.append("## Per-Skill Results (sorted by v3\u2192v4 change)\n")
        md.append("| Skill | Domain | N | v3 WR | v4 WR | Change | Cohen's d | Delta |")
        md.append("|---|---|---|---|---|---|---|---|")
        def _wr_change(s):
            return skill_win_rates.get(s, 0) - v3_skill_wr.get(s, skill_win_rates.get(s, 0))
        for skill in sorted(per_skill, key=_wr_change):
            sk = per_skill[skill]
            wr = skill_win_rates.get(skill, 0)
            cd = skill_cohens.get(skill, 0)
            v3wr = v3_skill_wr.get(skill, 0)
            change = wr - v3wr
            flag = " \u26a0\ufe0f" if change <= -20 else (" \u2705" if change >= 20 else "")
            md.append(f"| {skill} | {sk['domain']} | {sk['n']} | {v3wr:.0f}% | {wr:.0f}% | {change:+.0f}%{flag} | {cd:+.2f} | {sk['mean_delta']:+.1f} |")
    else:
        md.append("## Per-Skill Results\n")
        md.append("| Skill | Domain | N | Win Rate | Cohen's d | Delta |")
        md.append("|---|---|---|---|---|---|")
        for skill in sorted(per_skill, key=lambda s: skill_win_rates.get(s, 0), reverse=True):
            sk = per_skill[skill]
            wr = skill_win_rates.get(skill, 0)
            cd = skill_cohens.get(skill, 0)
            md.append(f"| {skill} | {sk['domain']} | {sk['n']} | {wr:.1f}% | {cd:+.2f} | {sk['mean_delta']:+.1f} |")
    md.append("")

    # Regressions
    regressions = [s for s, sk in per_skill.items() if sk["mean_delta"] < -2]
    if regressions:
        md.append("## ⚠️ Regressions (delta < -2)\n")
        for s in regressions:
            sk = per_skill[s]
            md.append(f"- **{s}** ({sk['domain']}): delta = {sk['mean_delta']:+.1f}, win rate = {skill_win_rates.get(s, 0):.1f}%")
        md.append("")

    # Skills-activated summary
    if per_skill_activated:
        n_activated = sum(sk["n"] for sk in per_skill_activated.values())
        activated_deltas = []
        for sk in per_skill_activated.values():
            activated_deltas.append(sk["mean_delta"])
        overall_activated = _mean(activated_deltas) if activated_deltas else 0
        md.append(f"## Skills-Activated Only (n={n_activated}/{len(per_prompt)}, overall delta: {overall_activated:+.1f})\n")
        md.append("*Filtered to prompts where the intended skill was actually loaded.*\n")
        md.append("| Skill | Domain | N (activated) | Win Rate | Cohen's d | Delta |")
        md.append("|---|---|---|---|---|---|")
        for skill in sorted(per_skill_activated, key=lambda s: per_skill_activated[s]["mean_delta"], reverse=True):
            sk = per_skill_activated[skill]
            # Compute win rate for activated prompts only
            active_prompts = [p for p in skill_prompts[skill] if p["id"] in activated_prompts]
            act_wins = [_prompt_win(p) for p in active_prompts]
            act_wr = round(_mean(act_wins) * 100, 1) if act_wins else 0
            act_diffs = [sum(p["skills"][d] - p["baseline"][d] for d in DIMENSIONS) / len(DIMENSIONS) for p in active_prompts]
            act_cd = _cohens_d_paired(act_diffs)
            md.append(f"| {skill} | {sk['domain']} | {sk['n']} | {act_wr:.1f}% | {act_cd:+.2f} | {sk['mean_delta']:+.1f} |")
        md.append("")

    # Per-skill detailed breakdown
    md.append("## Per-Skill Detailed Breakdown\n")
    for skill in sorted(per_skill, key=lambda s: skill_win_rates.get(s, 0), reverse=True):
        sk = per_skill[skill]
        n_dropped = len(dropped.get(skill, []))
        n_activated = per_skill_activated.get(skill, {}).get("n", 0)
        if n_dropped:
            n_b = sum(1 for _, r in dropped[skill] if r in ("baseline", "both"))
            n_s = sum(1 for _, r in dropped[skill] if r in ("skills", "both"))
            drop_note = f", {n_dropped} dropped (B:{n_b} S:{n_s})"
        else:
            drop_note = ""
        act_note = f", {n_activated}/{sk['n']} activated" if n_activated < sk['n'] else ""
        wr = skill_win_rates.get(skill, 0)
        cd = skill_cohens.get(skill, 0)
        md.append(f"### {skill} ({sk['domain']}, n={sk['n']}{drop_note}{act_note}, win rate: {wr:.1f}%, Cohen's d: {cd:+.2f})\n")
        md.append("| Dimension | Win Rate | Cohen's d | Delta |")
        md.append("|---|---|---|---|")
        prompts = skill_prompts[skill]
        for d in DIMENSIONS:
            d_wins = [1 if p["skills"][d] > p["baseline"][d] else (0 if p["skills"][d] < p["baseline"][d] else 0.5) for p in prompts]
            d_wr = round(_mean(d_wins) * 100, 1) if d_wins else 0
            d_diffs = [p["skills"][d] - p["baseline"][d] for p in prompts]
            d_cd = _cohens_d_paired(d_diffs)
            delta_d = sk["skills"][d]["mean"] - sk["baseline"][d]["mean"]
            md.append(f"| {d} | {d_wr:.1f}% | {d_cd:+.2f} | {delta_d:+.1f} |")
        md.append("")

    # Top 10 improvements
    top = sorted(per_skill.items(), key=lambda x: skill_win_rates.get(x[0], 0), reverse=True)[:10]
    md.append("## Top 10 Improvements\n")
    for s, sk in top:
        md.append(f"- **{s}** ({sk['domain']}): win rate = {skill_win_rates.get(s, 0):.1f}%, Cohen's d = {skill_cohens.get(s, 0):+.2f}, delta = {sk['mean_delta']:+.1f}")
    md.append("")

    # Top 10 decreases
    bottom = sorted(per_skill.items(), key=lambda x: skill_win_rates.get(x[0], 100))[:10]
    md.append("## Top 10 Decreases\n")
    for s, sk in bottom:
        md.append(f"- **{s}** ({sk['domain']}): win rate = {skill_win_rates.get(s, 0):.1f}%, Cohen's d = {skill_cohens.get(s, 0):+.2f}, delta = {sk['mean_delta']:+.1f}")
    md.append("")

    # v3 Comparison section
    v3_path = results_dir / "scores_v3.json"
    if v3_path.exists():
        v3_scores = json.loads(v3_path.read_text())
        # Filter valid v3 scores
        v3_valid = [s for s in v3_scores if sum(s["baseline"].values()) > 0 and sum(s["skills"].values()) > 0]
        v3_per_prompt = []
        for s in v3_valid:
            v3_per_prompt.append({
                "id": s["id"],
                "baseline": {d: s["baseline"].get(d, 0) for d in DIMENSIONS},
                "skills": {d: s["skills"].get(d, 0) for d in DIMENSIONS},
            })
        v3_wins = [1 if sum(p["skills"][d] for d in DIMENSIONS) > sum(p["baseline"][d] for d in DIMENSIONS) else (0 if sum(p["skills"][d] for d in DIMENSIONS) < sum(p["baseline"][d] for d in DIMENSIONS) else 0.5) for p in v3_per_prompt]
        v3_win_rate = round(_mean(v3_wins) * 100, 1) if v3_wins else 0
        v3_diffs = [sum(p["skills"][d] - p["baseline"][d] for d in DIMENSIONS) / len(DIMENSIONS) for p in v3_per_prompt]
        v3_cd = _cohens_d_paired(v3_diffs)
        v3_delta = round(_mean(v3_diffs), 1) if v3_diffs else 0

        md.append("## v3 → v4 Comparison\n")
        md.append("| Metric | v3 | v4 | Change |")
        md.append("|---|---|---|---|")
        md.append(f"| Win Rate | {v3_win_rate:.1f}% | {overall_win_rate:.1f}% | {overall_win_rate - v3_win_rate:+.1f}% |")
        md.append(f"| Cohen's d | {v3_cd:+.2f} | {overall_cohens_d:+.2f} | {overall_cohens_d - v3_cd:+.2f} |")
        md.append(f"| Delta | {v3_delta:+.1f} | {overall_delta:+.1f} | {overall_delta - v3_delta:+.1f} |")
        md.append(f"| N (valid) | {len(v3_valid)} | {len(valid_scores)} | {len(valid_scores) - len(v3_valid):+d} |")
        md.append("")

        # Updated skills comparison
        updated_skills = ["proteomics-analysis", "quantitative-proteomics", "cdisc-compliance",
                          "edc-data-validation", "scrna-seq-pipeline", "trajectory-analysis"]
        # Build v3 per-skill win rates
        v3_skill_prompts = defaultdict(list)
        for p in v3_per_prompt:
            v3_skill_prompts[_skill_from_id(p["id"])].append(p)

        md.append("### Updated Skills (v3 → v4)\n")
        md.append("| Skill | v3 Win Rate | v4 Win Rate | Change | v3 Delta | v4 Delta |")
        md.append("|---|---|---|---|---|---|")
        for skill in updated_skills:
            v3_sp = v3_skill_prompts.get(skill, [])
            v4_sp = skill_prompts.get(skill, [])
            if v3_sp:
                v3_sw = [1 if sum(p["skills"][d] for d in DIMENSIONS) > sum(p["baseline"][d] for d in DIMENSIONS) else (0 if sum(p["skills"][d] for d in DIMENSIONS) < sum(p["baseline"][d] for d in DIMENSIONS) else 0.5) for p in v3_sp]
                v3_swr = round(_mean(v3_sw) * 100, 1)
                v3_sd = round(_mean([sum(p["skills"][d] - p["baseline"][d] for d in DIMENSIONS) / len(DIMENSIONS) for p in v3_sp]), 1)
            else:
                v3_swr = 0
                v3_sd = 0
            v4_swr = skill_win_rates.get(skill, 0)
            v4_sd = per_skill[skill]["mean_delta"] if skill in per_skill else 0
            md.append(f"| {skill} | {v3_swr:.1f}% | {v4_swr:.1f}% | {v4_swr - v3_swr:+.1f}% | {v3_sd:+.1f} | {v4_sd:+.1f} |")
        md.append("")

    # Dropped prompts summary
    if dropped:
        total_dropped = sum(len(v) for v in dropped.values())
        md.append(f"## Dropped Prompts ({total_dropped} total — timeout or error in either condition)\n")
        md.append("| Skill | Dropped | Baseline | Skills | IDs |")
        md.append("|---|---|---|---|---|")
        for skill in sorted(dropped, key=lambda s: len(dropped[s]), reverse=True):
            entries = dropped[skill]
            n_b = sum(1 for _, r in entries if r in ("baseline", "both"))
            n_s = sum(1 for _, r in entries if r in ("skills", "both"))
            ids = ", ".join(f"{pid}({r[0].upper()})" for pid, r in entries)
            md.append(f"| {skill} | {len(entries)} | {n_b} | {n_s} | {ids} |")

    (results_dir / f"report{suffix}.md").write_text("\n".join(md))
    return report
