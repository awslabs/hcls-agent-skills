"""Generate JSON and markdown evaluation reports."""
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scipy.stats import ttest_rel

try:
    from .aws_config import resolve_region, execution_model_id
except ImportError:  # imported as a top-level module
    from aws_config import resolve_region, execution_model_id

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


def generate_report(scores: list[dict], results_dir: Path, judge_model: str, version: str = None, responses_dir: Path = None, region: str | None = None, execution_model: str | None = None, prompts_dir: Path | None = None) -> dict:
    """Generate report from scored results."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        commit = "unknown"

    try:
        git_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True
        ).strip())
    except Exception:
        git_dirty = False

    # Resolve region/executor model at report time when the caller did not
    # supply them, so a report always records which region and model produced
    # it even when invoked without those values threaded through.
    if region is None:
        region = resolve_region()
    if execution_model is None:
        # The executor resolves its model as model_id or DEFAULT_MODEL_ID or
        # execution_model_id() (eval/execute.py); this fallback only consults
        # execution_model_id(). Callers who override the executor model
        # out-of-band (e.g. setting _ex.DEFAULT_MODEL_ID) MUST pass
        # execution_model explicitly or the report will misname the executor.
        execution_model = execution_model_id()

    # Fingerprint the prompt set so a reader can tell which prompts produced the
    # report. Files are hashed by their path RELATIVE to prompts_dir (not the
    # absolute path) so the fingerprint is portable across machines and
    # checkouts; sorting on that relative path also makes it independent of
    # filesystem glob order.
    prompt_set_dir = None
    prompt_set_hash = None
    num_prompt_files = 0
    if prompts_dir is not None and prompts_dir.exists():
        pd = prompts_dir.resolve()
        repo_root = Path(__file__).resolve().parent.parent
        try:
            prompt_set_dir = str(pd.relative_to(repo_root))
        except ValueError:
            prompt_set_dir = str(pd)
        # Match load_prompts() in run.py: *.yaml under single/ and cross/.
        prompt_files = []
        for sub in ["single", "cross"]:
            sub_dir = pd / sub
            if sub_dir.exists():
                prompt_files.extend(sub_dir.glob("*.yaml"))
        prompt_files.sort(key=lambda f: f.relative_to(pd).as_posix())
        # Report generation must never raise here: a full multi-hundred-prompt
        # eval run has already completed and its results are in hand — they must
        # be written out. If a prompt file is unreadable, vanished (TOCTOU), or
        # is a directory named *.yaml, fall back to a sentinel hash rather than
        # discarding the entire run's results.
        h = hashlib.sha256()
        try:
            for f in prompt_files:
                h.update(f.relative_to(pd).as_posix().encode("utf-8"))
                h.update(f.read_bytes())
                num_prompt_files += 1
            prompt_set_hash = f"sha256:{h.hexdigest()}"
        except OSError:
            # "unavailable" is distinct from None, which means no prompts_dir
            # was given; num_prompt_files holds the count hashed before failing.
            prompt_set_hash = "unavailable"

    # Identify timeouts/errors (all-zero scores in either condition)
    valid_scores = []
    dropped = defaultdict(list)  # skill -> list of (prompt_id, reason)
    for s in scores:
        b_sum = sum(s["baseline"].values())
        sk_sum = sum(s["skills"].values())
        skill = _skill_from_id(s["id"])
        # Explicit drop set by run.py: a transient-failure response body or a
        # judge call that raised / failed to parse. Honor it FIRST, even if a
        # score was (defensively) non-zero, so a judge error can NEVER become a
        # counted tie. num_dropped (below) therefore always reflects these.
        if s.get("dropped"):
            dropped[skill].append((s["id"], s.get("drop_reason", "both")))
            continue
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
            # Check activated_skills key first (Strands backend)
            loaded = set(resp_data.get("activated_skills", []))
            # Also detect from response text (kiro-cli backend)
            loaded.update(re.findall(r'/skills/([a-z0-9-]+)/SKILL\.md', text))
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
            "git_dirty": git_dirty,
            "aws_region": region,
            "execution_model": execution_model,
            "judge_model": judge_model,
            "prompt_set_dir": prompt_set_dir,
            "prompt_set_hash": prompt_set_hash,
            "num_prompt_files": num_prompt_files,
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
    md.append(f"**Region:** {region}  ")
    md.append(f"**Executor:** {execution_model}  ")
    md.append(f"**Judge:** {judge_model}  ")
    md.append(f"**Prompt set:** {prompt_set_hash}  ")
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

    # Per-Skill Results — simple table sorted by win rate
    md.append("## Per-Skill Results\n")
    md.append("| Skill | Domain | N | Activated | Win Rate | Cohen's d | Delta |")
    md.append("|---|---|---|---|---|---|---|")
    for skill in sorted(per_skill, key=lambda s: skill_win_rates.get(s, 0), reverse=True):
        sk = per_skill[skill]
        wr = skill_win_rates.get(skill, 0)
        cd = skill_cohens.get(skill, 0)
        n_act = sum(1 for p in skill_prompts[skill] if p["id"] in activated_prompts)
        md.append(f"| {skill} | {sk['domain']} | {sk['n']} | {n_act}/{sk['n']} | {wr:.0f}% | {cd:+.2f} | {sk['mean_delta']:+.1f} |")
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

    # Activation Confusion Matrix (win rate by activation pattern)
    patterns = {"clean": [], "intended_plus_same": [], "intended_plus_cross": [], "only_unintended": [], "no_skill": []}
    if responses_dir and responses_dir.exists():
        for p in per_prompt:
            pid = p["id"]
            resp_file = responses_dir / f"{pid}_skills.json"
            if not resp_file.exists():
                patterns["no_skill"].append(pid)
                continue
            resp_data = json.loads(resp_file.read_text())
            text = resp_data.get("text", "")
            loaded = set(resp_data.get("activated_skills", []))
            loaded.update(re.findall(r'/skills/([a-z0-9-]+)/SKILL\.md', text))
            target = set(p.get("target_skills", []))
            if not loaded:
                patterns["no_skill"].append(pid)
            elif not (target & loaded):
                patterns["only_unintended"].append(pid)
            elif loaded - target:
                # Has both intended and extra
                extra_domains = set()
                for s in (loaded - target):
                    if (Path("skills") / s).is_dir():
                        extra_domains.add("same")  # simplified
                patterns["intended_plus_same"].append(pid)
            else:
                patterns["clean"].append(pid)

        def _winner_from_scores(s):
            w = s.get("winner", "")
            if w in ("skills", "baseline", "tie"):
                return w
            s_sum = sum(s["skills"][d] for d in DIMENSIONS)
            b_sum = sum(s["baseline"][d] for d in DIMENSIONS)
            return "skills" if s_sum > b_sum else ("baseline" if b_sum > s_sum else "tie")

        winners = {s["id"]: _winner_from_scores(s) for s in scores}
        md.append("## Skill Activation Confusion Matrix\n")
        md.append("| Pattern | Count | Win Rate | Wins | Losses | Ties |")
        md.append("|---|---|---|---|---|---|")
        pattern_labels = {
            "clean": "Only intended skill(s)",
            "intended_plus_same": "Intended + extra skills",
            "intended_plus_cross": "Intended + cross-domain extra",
            "only_unintended": "Only unintended skill(s)",
            "no_skill": "No skill loaded",
        }
        for key, label in pattern_labels.items():
            pids = patterns[key]
            count = len(pids)
            if count == 0:
                md.append(f"| {label} | 0 | — | 0 | 0 | 0 |")
                continue
            wins = sum(1 for pid in pids if winners.get(pid) == "skills")
            losses = sum(1 for pid in pids if winners.get(pid) == "baseline")
            ties = count - wins - losses
            wr = round(wins / count * 100, 1)
            md.append(f"| {label} | {count} | {wr}% | {wins} | {losses} | {ties} |")
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
