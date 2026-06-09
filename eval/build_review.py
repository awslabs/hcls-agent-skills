#!/usr/bin/env python3
"""Build a self-contained HTML review page from eval results."""
import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import yaml
from scipy.stats import ttest_rel

DIMS = ["scientific_accuracy", "coherence", "relevance", "critical_thinking", "actionability"]
MAX_RESPONSE_CHARS = None  # No truncation — show full responses


def _mean(v):
    return sum(v) / len(v) if v else 0


def _skill_from_id(pid):
    parts = pid.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and parts[1].isdigit() else pid


def _paired_p(b, s):
    if len(b) < 2:
        return 1.0
    _, p = ttest_rel(s, b)
    return float(p)


def detect_skill_flags(responses: dict, prompts_meta: dict) -> dict[str, dict]:
    """Detect which skills were loaded in each skills response."""
    flags = {}
    for pid, resps in responses.items():
        text = resps.get("skills", "")
        if not text:
            flags[pid] = {"labels": ["no_skill_loaded"], "loaded": [], "target": []}
            continue

        # Detect loaded skills
        loaded = set()
        loaded.update(re.findall(r'/skills/([a-z0-9-]+)/SKILL\.md', text))
        preamble = text[:1000]
        for m in re.findall(r'(?:skill|read|load|check).*?([a-z]+-[a-z]+(?:-[a-z]+)*)', preamble, re.IGNORECASE):
            if (Path("skills") / m).is_dir():
                loaded.add(m)

        target = set(prompts_meta.get(pid, []))
        labels = []
        if not loaded:
            labels.append("no_skill_loaded")
        else:
            if target & loaded:
                labels.append("intended_loaded")
            if loaded - target:
                labels.append("unintended_loaded")
            if target - loaded:
                labels.append("intended_not_loaded")

        flags[pid] = {"labels": labels, "loaded": sorted(loaded), "target": sorted(target)}
    return flags


def load_skill_content(skills_dir: Path) -> dict[str, str]:
    """Load SKILL.md content for each skill."""
    content = {}
    for f in sorted(skills_dir.glob("*/SKILL.md")):
        content[f.parent.name] = f.read_text()
    return content


def load_prompts(prompts_dir: Path) -> tuple[dict[str, str], dict[str, list[str]]]:
    prompts = {}
    targets = {}
    for d in ("single", "cross"):
        p = prompts_dir / d
        if not p.exists():
            continue
        for f in sorted(p.glob("*.yaml")):
            doc = yaml.safe_load(f.read_text())
            pid = f.stem
            prompts[pid] = doc.get("prompt", "")
            targets[pid] = doc.get("target_skills", [])
    return prompts, targets


def load_responses(resp_dir: Path) -> dict[str, dict[str, str]]:
    responses: dict[str, dict[str, str]] = defaultdict(dict)
    for f in sorted(resp_dir.glob("*.json")):
        name = f.stem  # e.g. variant-calling-01_skills
        if "_baseline" in name:
            pid = name.replace("_baseline", "")
            cond = "baseline"
        elif "_skills" in name:
            pid = name.replace("_skills", "")
            cond = "skills"
        else:
            continue
        doc = json.loads(f.read_text())
        text = doc.get("text", "")
        if MAX_RESPONSE_CHARS and len(text) > MAX_RESPONSE_CHARS:
            text = text[:MAX_RESPONSE_CHARS] + "\n\n[... truncated ...]"
        responses[pid][cond] = text
    return dict(responses)


def build_skill_data(scores):
    by_skill = defaultdict(list)
    for s in scores:
        by_skill[_skill_from_id(s["id"])].append(s)

    skills = []
    for skill, items in sorted(by_skill.items()):
        domain = items[0].get("domain", "")
        n = len(items)
        dim_stats = {}
        for d in DIMS:
            bv = [i["baseline"][d] for i in items]
            sv = [i["skills"][d] for i in items]
            delta = _mean(sv) - _mean(bv)
            p = _paired_p(bv, sv)
            dim_stats[d] = {"baseline": round(_mean(bv), 1), "skills": round(_mean(sv), 1),
                            "delta": round(delta, 1), "p": round(p, 4), "sig": p < 0.05}

        overall_b = [_mean([i["baseline"][d] for d in DIMS]) for i in items]
        overall_s = [_mean([i["skills"][d] for d in DIMS]) for i in items]
        overall_delta = round(_mean(overall_s) - _mean(overall_b), 1)

        prompt_details = []
        for i in items:
            pd = {"id": i["id"], "baseline_scores": i["baseline"], "skills_scores": i["skills"],
                  "baseline_reasoning": i.get("baseline_reasoning", ""),
                  "skills_reasoning": i.get("skills_reasoning", ""),
                  "reasoning": i.get("reasoning", ""),
                  "winner": i.get("winner", ""),
                  "position": i.get("position", "")}
            prompt_details.append(pd)

        skills.append({"skill": skill, "domain": domain, "n": n,
                       "overall_delta": overall_delta, "dims": dim_stats,
                       "prompts": prompt_details})

    skills.sort(key=lambda x: -x["overall_delta"])
    return skills


def compute_summary(scores):
    dim_means = {}
    for d in DIMS:
        bv = [s["baseline"][d] for s in scores]
        sv = [s["skills"][d] for s in scores]
        dim_means[d] = {"baseline": round(_mean(bv), 1), "skills": round(_mean(sv), 1),
                        "delta": round(_mean(sv) - _mean(bv), 1)}
    overall_b = [_mean([s["baseline"][d] for d in DIMS]) for s in scores]
    overall_s = [_mean([s["skills"][d] for d in DIMS]) for s in scores]
    return {"n": len(scores), "overall_delta": round(_mean(overall_s) - _mean(overall_b), 1),
            "dims": dim_means}


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>HCLS Skills Eval Review</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f7fa;color:#1a1a2e;line-height:1.5;padding:20px;max-width:1400px;margin:0 auto}
h1{font-size:1.6rem;margin-bottom:8px}
.header{background:#fff;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:16px}
.stat-card{background:#f8f9fb;border-radius:8px;padding:12px;text-align:center}
.stat-card .label{font-size:.75rem;color:#666;text-transform:uppercase}
.stat-card .value{font-size:1.4rem;font-weight:700}
.pos{color:#16a34a}.neg{color:#dc2626}.neu{color:#666}
.skill-section{background:#fff;border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.skill-header{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.skill-name{font-size:1.2rem;font-weight:700}
.badge{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.75rem;font-weight:600}
.badge-domain{background:#e0e7ff;color:#3730a3}
.dim-table{width:100%;border-collapse:collapse;margin:12px 0;font-size:.85rem}
.dim-table th,.dim-table td{padding:6px 10px;text-align:center;border-bottom:1px solid #eee}
.dim-table th{background:#f8f9fb;font-weight:600}
details{margin-top:12px}
summary{cursor:pointer;font-weight:600;color:#4338ca;font-size:.9rem}
summary:hover{text-decoration:underline}
.prompt-item{border:1px solid #e5e7eb;border-radius:8px;margin:8px 0;padding:12px}
.prompt-text{background:#fef9c3;border-radius:6px;padding:12px;margin:8px 0;font-size:.85rem;white-space:pre-wrap;word-wrap:break-word}
.response-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:8px;max-width:1400px;margin-left:auto;margin-right:auto}
@media(max-width:800px){.response-grid{grid-template-columns:1fr}}
.response-col h4{font-size:.85rem;margin-bottom:6px}
.response-col{overflow:hidden;min-width:0}
.score-pills{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px}
.pill{padding:2px 8px;border-radius:10px;font-size:.7rem;font-weight:600;color:#fff}
.pill-green{background:#16a34a}.pill-yellow{background:#ca8a04}.pill-red{background:#dc2626}
.judge-reasoning{background:#eff6ff;border-left:3px solid #3b82f6;padding:6px 10px;margin:6px 0;font-size:.8rem;font-style:italic;color:#1e40af;border-radius:4px}
.flag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:.65rem;font-weight:600;margin:2px}
.flag-intended{background:#dcfce7;color:#166534}.flag-unintended{background:#fef9c3;color:#854d0e}.flag-missing{background:#fee2e2;color:#991b1b}.flag-none{background:#f3f4f6;color:#374151}
.response-text{background:#f8f9fb;border-radius:6px;padding:12px;font-size:.82rem;white-space:pre-wrap;word-wrap:break-word;word-break:break-word;overflow-wrap:break-word;max-height:500px;overflow-y:auto;line-height:1.6;overflow-x:hidden}
.response-text .md-h1{font-size:1.1em;font-weight:700;margin:8px 0 4px}
.response-text .md-h2{font-size:1em;font-weight:700;margin:8px 0 4px}
.response-text .md-h3{font-size:.95em;font-weight:700;margin:6px 0 4px}
.response-text .md-code{display:block;background:#1e1e2e;color:#cdd6f4;padding:10px;border-radius:6px;font-family:"Fira Code",monospace;font-size:.8rem;overflow-x:auto;margin:6px 0;white-space:pre}
.response-text .md-bold{font-weight:700}
.response-text .md-li{padding-left:16px}
.response-text .md-table{border-collapse:collapse;margin:8px 0;font-size:.8rem;width:100%}
.response-text .md-table th,.response-text .md-table td{border:1px solid #ddd;padding:4px 8px;text-align:left}
.response-text .md-table th{background:#f0f0f0;font-weight:600}
</style></head><body>
<div class="header">
<h1>HCLS Skills Eval &mdash; Interactive Review</h1>
<p id="subtitle"></p>
<div class="summary-grid" id="summary-grid"></div>
<details style="margin-top:12px"><summary style="font-size:.85rem;color:#4338ca;cursor:pointer">📋 Judging Methodology</summary>
<div style="font-size:.82rem;margin-top:8px;line-height:1.6">
<h4 style="margin-bottom:6px">Scoring Dimensions</h4>
<table class="dim-table" style="text-align:left">
<tr><th>Dimension</th><th>Definition</th></tr>
<tr><td><b>Scientific Accuracy</b></td><td>Correctness of facts, mechanisms, citations, domain knowledge. Deduct for hallucinated references, wrong mechanisms, incorrect parameter values, or outdated information.</td></tr>
<tr><td><b>Coherence</b></td><td>Logical structure, clear reasoning chain, internal consistency. Deduct for contradictions, disorganized flow, or unclear explanations.</td></tr>
<tr><td><b>Relevance</b></td><td>Addresses all parts of the prompt, appropriate depth, stays on topic. Deduct for missing requested sections, tangential content, or superficial treatment.</td></tr>
<tr><td><b>Critical Thinking</b></td><td>Challenges assumptions, identifies limitations, considers alternatives, flags uncertainties, questions premises when warranted.</td></tr>
<tr><td><b>Actionability</b></td><td>Provides concrete next steps, specific parameters, runnable commands, implementable designs, or clear decision criteria.</td></tr>
</table>
<h4 style="margin:12px 0 6px">Metrics</h4>
<p style="font-size:.8rem;margin-bottom:6px">The judge scores each response on a 0-100 scale per dimension. Because LLM judges compress scores into a narrow range (typically 78-96), raw scores are converted to more interpretable metrics:</p>
<table class="dim-table" style="text-align:left">
<tr><th>Metric</th><th>Definition</th><th>Interpretation</th></tr>
<tr><td><b>Win Rate</b></td><td>Percentage of prompts where the judge scored the skills condition higher than baseline on a given dimension.</td><td>50% = no difference. &gt;60% = meaningful advantage. &gt;70% = strong advantage.</td></tr>
<tr><td><b>Cohen's d</b></td><td>Effect size: mean score difference divided by pooled standard deviation. Measures how large the improvement is relative to natural variance.</td><td>0.2 = small, 0.5 = medium, 0.8 = large. Values &gt;0.5 indicate a practically meaningful effect.</td></tr>
</table>
<h4 style="margin:12px 0 6px">Pairwise Protocol</h4>
<p style="font-size:.8rem">Both responses sent in a single judge call as Response A / Response B. Position randomized 50/50 per prompt. Tool-call artifacts stripped from both responses (sanitized). Judge scores both on all dimensions and declares a winner.</p>
<p style="margin-top:8px"><b>Pairwise (v3):</b> Both responses sent in one call, sanitized, position randomized. Most sensitive method for detecting quality differences.</p>
</div></details>
</div>
<div id="skills-container"></div>
<script>
const DATA = __DATA_PLACEHOLDER__;

let currentVersion = DATA.version_labels[DATA.version_labels.length-1]; // latest by default
let currentFilter = 'all'; // 'all' or 'activated'
let winRateFilter = 'any'; // 'any', 'low', 'mid', 'high'
let winRateDim = 'overall'; // 'overall' or a dimension name
let cohensDMin = -999; // disabled

function dc(d){return d>0?'pos':d<0?'neg':'neu'}
function pillClass(v){return v>80?'pill-green':v>=60?'pill-yellow':'pill-red'}
function esc(s){const d=document.createElement('div');d.textContent=s;return d.innerHTML}

function filterPrompts(prompts){
  if(currentFilter==='all')return prompts;
  // 'activated': only prompts where intended or unintended skill loaded
  return prompts.filter(pr=>{
    const fl=DATA.skill_flags[pr.id];
    if(!fl)return false;
    return fl.labels.includes('intended_loaded')||fl.labels.includes('unintended_loaded');
  });
}

function recomputeSummary(skills){
  let allB=[],allS=[],winners={skills:0,baseline:0,tie:0};
  for(let sk of skills){
    for(let pr of sk.prompts){
      allB.push(DIMS.reduce((a,d)=>a+pr.baseline_scores[d],0)/5);
      allS.push(DIMS.reduce((a,d)=>a+pr.skills_scores[d],0)/5);
      if(pr.winner)winners[pr.winner]=(winners[pr.winner]||0)+1;
    }
  }
  const n=allB.length||1;
  const dims={};
  for(let d of DIMS){
    let bvals=[],svals=[];
    for(let sk of skills)for(let pr of sk.prompts){bvals.push(pr.baseline_scores[d]);svals.push(pr.skills_scores[d])}
    const bm=bvals.reduce((a,v)=>a+v,0)/n;
    const sm=svals.reduce((a,v)=>a+v,0)/n;
    const deltas=bvals.map((b,i)=>svals[i]-b);
    const md=deltas.reduce((a,v)=>a+v,0)/n;
    const sd=Math.sqrt(deltas.reduce((a,v)=>a+(v-md)**2,0)/(n-1))||1;
    const cd=md/sd;
    // Per-dim win rate
    let sw=0,bw=0;
    deltas.forEach(d=>{if(d>0)sw++;else if(d<0)bw++});
    dims[d]={baseline:+bm.toFixed(1),skills:+sm.toFixed(1),delta:+md.toFixed(1),cohens_d:+cd.toFixed(2),win_skills:sw,win_baseline:bw,win_tie:n-sw-bw};
  }
  const overall=+(allS.reduce((a,v)=>a+v,0)/n - allB.reduce((a,v)=>a+v,0)/n).toFixed(1);
  const oDeltas=allB.map((b,i)=>allS[i]-b);
  const oMd=oDeltas.reduce((a,v)=>a+v,0)/n;
  const oSd=Math.sqrt(oDeltas.reduce((a,v)=>a+(v-oMd)**2,0)/(n-1))||1;
  return {n,overall_delta:overall,cohens_d:+(oMd/oSd).toFixed(2),dims,winners};
}
function fmtMd(raw){
  let lines=raw.split('\n'),out=[],inCode=false,codeBuf=[],inTable=false,tableBuf=[];
  for(let l of lines){
    if(l.startsWith('```')){
      if(inTable){out.push(renderTable(tableBuf));tableBuf=[];inTable=false}
      if(inCode){out.push('<span class="md-code">'+esc(codeBuf.join('\n'))+'</span>');codeBuf=[];inCode=false}
      else{inCode=true}
      continue}
    if(inCode){codeBuf.push(l);continue}
    // Table detection
    if(/^\|(.+\|)+\s*$/.test(l.trim())){
      if(!inTable){inTable=true;tableBuf=[]}
      tableBuf.push(l);continue}
    if(inTable){out.push(renderTable(tableBuf));tableBuf=[];inTable=false}
    if(l.startsWith('### '))out.push('<span class="md-h3">'+esc(l.slice(4))+'</span>');
    else if(l.startsWith('## '))out.push('<span class="md-h2">'+esc(l.slice(3))+'</span>');
    else if(l.startsWith('# '))out.push('<span class="md-h1">'+esc(l.slice(2))+'</span>');
    else if(/^[-*] /.test(l))out.push('<span class="md-li">&bull; '+esc(l.slice(2))+'</span>');
    else{let e=esc(l).replace(/\*\*(.+?)\*\*/g,'<span class="md-bold">$1</span>');out.push(e)}
  }
  if(inCode&&codeBuf.length)out.push('<span class="md-code">'+esc(codeBuf.join('\n'))+'</span>');
  if(inTable)out.push(renderTable(tableBuf));
  return out.join('\n')
}
function renderTable(rows){
  if(rows.length<2)return rows.map(r=>esc(r)).join('\n');
  let html='<table class="md-table">';
  let hdr=rows[0].split('|').filter(c=>c.trim());
  html+='<tr>'+hdr.map(c=>'<th>'+esc(c.trim())+'</th>').join('')+'</tr>';
  for(let i=1;i<rows.length;i++){
    let cells=rows[i].split('|').filter(c=>c.trim());
    if(cells.every(c=>/^[-:]+$/.test(c.trim())))continue; // skip separator
    html+='<tr>'+cells.map(c=>'<td>'+esc(c.trim())+'</td>').join('')+'</tr>';
  }
  return html+'</table>'
}

const DIMS=["scientific_accuracy","coherence","relevance","critical_thinking","actionability"];
const DLABEL={"scientific_accuracy":"Sci.Acc","coherence":"Coher","relevance":"Relev","critical_thinking":"Crit.Think","actionability":"Action"};

function render(){
  let skills=DATA.versions[currentVersion];

  // Apply filter: rebuild skills with filtered prompts and recomputed stats
  let filteredSkills=skills.map(sk=>{
    const fp=filterPrompts(sk.prompts);
    if(fp.length===0)return null;
    // Recompute per-skill dim stats from filtered prompts
    const dims={};
    for(let d of DIMS){
      const bv=fp.map(p=>p.baseline_scores[d]);
      const sv=fp.map(p=>p.skills_scores[d]);
      const bm=bv.reduce((a,v)=>a+v,0)/bv.length;
      const sm2=sv.reduce((a,v)=>a+v,0)/sv.length;
      dims[d]={baseline:+bm.toFixed(1),skills:+sm2.toFixed(1),delta:+(sm2-bm).toFixed(1),p:sk.dims[d].p,sig:sk.dims[d].sig};
    }
    const overallDelta=+(DIMS.reduce((a,d)=>a+dims[d].delta,0)/5).toFixed(1);
    return {...sk, prompts:fp, n:fp.length, dims, overall_delta:overallDelta};
  }).filter(sk=>sk!==null);
  filteredSkills.sort((a,b)=>b.overall_delta-a.overall_delta);

  // Recompute summary from filtered data
  const sm=recomputeSummary(filteredSkills);

  // Filter tabs
  let ft='<div style="margin-bottom:12px"><b>Filter:</b> ';
  const filters=[['all','All Prompts'],['activated','Skills Activated']];
  for(let [k,label] of filters){
    if(k===currentFilter)ft+=`<span class="badge" style="background:#059669;color:#fff;margin:0 4px">${label}</span>`;
    else ft+=`<a href="#" onclick="currentFilter='${k}';render();return false" style="margin:0 4px">${label}</a>`;
  }
  ft+='</div>';

  // Version toggle
  let vt='<div style="margin-bottom:12px"><b>Version:</b> ';
  for(let v of DATA.version_labels){
    if(v===currentVersion)vt+=`<span class="badge" style="background:#4338ca;color:#fff;margin:0 4px">${v}</span>`;
    else vt+=`<a href="#" onclick="currentVersion='${v}';render();return false" style="margin:0 4px">${v}</a>`;
  }
  vt+='</div>';

  // Skill-level filters
  let sf='<div style="margin-bottom:12px;display:flex;gap:16px;flex-wrap:wrap;align-items:center">';
  // Win rate filter
  sf+=`<span><b>Win Rate:</b> `;
  const wrOpts=[['any','Any'],['low','<50%'],['mid','50-70%'],['high','>70%']];
  for(let [k,label] of wrOpts){
    if(k===winRateFilter)sf+=`<span class="badge" style="background:#7c3aed;color:#fff;margin:0 2px;font-size:.75rem">${label}</span>`;
    else sf+=`<a href="#" onclick="winRateFilter='${k}';render();return false" style="margin:0 2px;font-size:.8rem">${label}</a>`;
  }
  sf+=` <select onchange="winRateDim=this.value;render()" style="font-size:.75rem;padding:1px 4px;border-radius:4px;border:1px solid #ccc">`;
  sf+=`<option value="overall"${winRateDim==='overall'?' selected':''}>overall</option>`;
  for(let d of DIMS)sf+=`<option value="${d}"${winRateDim===d?' selected':''}>${DLABEL[d]}</option>`;
  sf+=`</select></span>`;
  sf+='</div>';

  // Apply skill-level filters
  function getSkillWinRate(sk,dim){
    if(dim==='overall'){let w=0;sk.prompts.forEach(pr=>{if(pr.winner==='skills')w++});return sk.n>0?w/sk.n*100:0}
    let w=0;sk.prompts.forEach(pr=>{if(pr.skills_scores[dim]>pr.baseline_scores[dim])w++});return sk.n>0?w/sk.n*100:0;
  }
  function getSkillCohensD(sk){
    const dels=sk.prompts.map(pr=>DIMS.reduce((a,d)=>a+pr.skills_scores[d]-pr.baseline_scores[d],0)/5);
    const m=dels.reduce((a,v)=>a+v,0)/(dels.length||1);
    const sd=Math.sqrt(dels.reduce((a,v)=>a+(v-m)**2,0)/((dels.length-1)||1))||1;
    return m/sd;
  }
  filteredSkills=filteredSkills.filter(sk=>{
    const wr=getSkillWinRate(sk,winRateDim);
    if(winRateFilter==='low'&&wr>=50)return false;
    if(winRateFilter==='mid'&&(wr<50||wr>70))return false;
    if(winRateFilter==='high'&&wr<=70)return false;
    const cd=getSkillCohensD(sk);
    if(cd<cohensDMin)return false;
    return true;
  });

  // Summary
  const sg=document.getElementById('summary-grid');
  let h=`<div class="stat-card"><div class="label">Overall</div><div class="value pos">${sm.winners&&sm.n?(sm.winners.skills/sm.n*100).toFixed(1)+'%':'—'}</div><div style="font-size:.65rem;color:#888">d=${sm.cohens_d} · Δ${sm.overall_delta>0?'+':''}${sm.overall_delta}</div></div>`;
  for(let d of DIMS){const v=sm.dims[d];h+=`<div class="stat-card"><div class="label">${DLABEL[d]}</div><div class="value ${dc(v.delta)}">${(v.win_skills/sm.n*100).toFixed(0)}%</div><div style="font-size:.65rem;color:#888">d=${v.cohens_d} · Δ${v.delta>0?'+':''}${v.delta}</div></div>`}
  sg.innerHTML=h;
  document.getElementById('subtitle').innerHTML=ft+vt+sf+`${filteredSkills.length} skills, ${sm.n} prompts`;

  // Use filteredSkills for rendering
  skills=filteredSkills;

  // Skills
  const sc=document.getElementById('skills-container');
  let shtml='';
  for(let sk of skills){
    // Compute per-skill win rate and Cohen's d
    let skWins=0;
    sk.prompts.forEach(pr=>{if(pr.winner==='skills')skWins++;});
    const skWinPct=sk.n>0?(skWins/sk.n*100).toFixed(0):'0';
    const skDeltas=sk.prompts.map(pr=>DIMS.reduce((a,d)=>a+pr.skills_scores[d]-pr.baseline_scores[d],0)/5);
    const skMd=skDeltas.reduce((a,v)=>a+v,0)/(skDeltas.length||1);
    const skSd=Math.sqrt(skDeltas.reduce((a,v)=>a+(v-skMd)**2,0)/((skDeltas.length-1)||1))||1;
    const skCd=(skMd/skSd).toFixed(2);

    let s=`<div class="skill-section"><div class="skill-header"><span class="skill-name">${esc(sk.skill)}</span><span class="badge badge-domain">${esc(sk.domain)}</span><span style="font-size:.8rem;color:#666">n=${sk.n}</span></div>`;
    s+=`<table class="dim-table"><tr><th></th><th>Overall</th>`;
    for(let d of DIMS)s+=`<th>${DLABEL[d]}</th>`;
    s+=`</tr><tr><td><b>Win Rate</b></td><td class="pos">${skWinPct}%</td>`;for(let d of DIMS){let w=0;sk.prompts.forEach(pr=>{if(pr.skills_scores[d]>pr.baseline_scores[d])w++});s+=`<td class="pos">${(w/sk.n*100).toFixed(0)}%</td>`}
    s+=`</tr><tr><td><b>Cohen's d</b></td><td class="${dc(parseFloat(skCd))}">${skCd}</td>`;for(let d of DIMS){const dels=sk.prompts.map(pr=>pr.skills_scores[d]-pr.baseline_scores[d]);const m=dels.reduce((a,v)=>a+v,0)/dels.length;const sd=Math.sqrt(dels.reduce((a,v)=>a+(v-m)**2,0)/((dels.length-1)||1))||1;s+=`<td class="${dc(m)}">${(m/sd).toFixed(2)}</td>`}
    s+=`</tr><tr><td><b>Δ</b></td><td class="${dc(sk.overall_delta)}">${sk.overall_delta>0?'+':''}${sk.overall_delta}</td>`;for(let d of DIMS){const v=sk.dims[d];s+=`<td class="${dc(v.delta)}">${v.delta>0?'+':''}${v.delta}</td>`}
    s+=`</tr></table>`;
    const skillMd=DATA.skill_content[sk.skill]||'';
    if(skillMd){s+=`<details style="margin:8px 0"><summary style="font-size:.85rem;color:#6b21a8;cursor:pointer">📄 View Skill Definition</summary><div class="response-text" style="max-height:600px;overflow-y:auto;margin-top:6px">${fmtMd(skillMd)}</div></details>`}
    else{
      // Cross-skill combo — collect all constituent skill contents as tabs
      const tabSkills=[];
      const seen=new Set();
      for(let pr of sk.prompts){
        const fl=DATA.skill_flags[pr.id];
        if(fl&&fl.target){fl.target.forEach(t=>{if(!seen.has(t)&&DATA.skill_content[t]){seen.add(t);tabSkills.push(t)}})}
      }
      if(tabSkills.length){
        const tabId='combo-'+sk.skill.replace(/[^a-z0-9]/g,'');
        s+=`<details style="margin:8px 0"><summary style="font-size:.85rem;color:#6b21a8;cursor:pointer">📄 View Skill Definitions (${tabSkills.length} skills)</summary>`;
        s+=`<div style="margin-top:6px"><div style="display:flex;gap:4px;margin-bottom:8px">`;
        tabSkills.forEach((t,i)=>{s+=`<button onclick="document.querySelectorAll('.${tabId}-tab').forEach(e=>e.style.display='none');document.getElementById('${tabId}-${i}').style.display='block';this.parentElement.querySelectorAll('button').forEach(b=>b.style.background='#f0f0f0');this.style.background='#4338ca';this.style.color='#fff'" style="padding:4px 12px;border:none;border-radius:6px;cursor:pointer;font-size:.8rem;${i===0?'background:#4338ca;color:#fff':'background:#f0f0f0;color:#333'}">${t}</button>`});
        s+=`</div>`;
        tabSkills.forEach((t,i)=>{s+=`<div id="${tabId}-${i}" class="${tabId}-tab" style="display:${i===0?'block':'none'}"><div class="response-text" style="max-height:600px;overflow-y:auto">${fmtMd(DATA.skill_content[t])}</div></div>`});
        s+=`</div></details>`;
      }
    }
    s+=`<details><summary>Individual prompts (${sk.prompts.length})</summary>`;
    for(let pr of sk.prompts){
      const pt=DATA.prompts[pr.id]||'';
      const br=DATA.responses[pr.id]||{};
      s+=`<details class="prompt-item"><summary>${esc(pr.id)}`;
      // Inline scores preview — show per-dim win/loss indicators
      const bs=pr['baseline_scores'],ss=pr['skills_scores'];
      let dimWins=0,dimLosses=0;
      for(let d of DIMS){if(ss[d]>bs[d])dimWins++;else if(ss[d]<bs[d])dimLosses++}
      const dimTies=5-dimWins-dimLosses;
      s+=` <span style="font-size:.75rem;margin-left:8px">`;
      s+=`<span class="pos">▲${dimWins}</span> <span class="neg">▼${dimLosses}</span> <span class="neu">=${dimTies}</span>`;
      if(pr.winner)s+=` <span style="font-weight:600;color:${pr.winner==='skills'?'#16a34a':pr.winner==='baseline'?'#dc2626':'#666'}">${pr.winner}</span>`;
      s+=`</span>`;
      const fl=DATA.skill_flags[pr.id];
      if(fl){const flagMap={"intended_loaded":["✓","flag-intended"],"unintended_loaded":["⚠","flag-unintended"],"intended_not_loaded":["✗","flag-missing"],"no_skill_loaded":["○","flag-none"]};for(let l of fl.labels){const[txt,cls]=flagMap[l]||["?","flag-none"];s+=`<span class="flag ${cls}" style="margin-left:4px">${txt}</span>`}}
      s+=`</summary>`;
      if(pt)s+=`<div class="prompt-text">${esc(pt)}</div>`;
      // Show pairwise reasoning + winner if available (v3)
      if(pr.reasoning){
        // Replace Response A/B with actual condition names based on position
        let rText=pr.reasoning;
        // pr.position tells us what was shown as A (from scores_v3.json)
        // We need to get it from DATA — add position to prompt_details
        const pos=pr.position||'';
        if(pos==='baseline'){
          rText=rText.replace(/Response A/g,'Baseline').replace(/Response B/g,'Skills');
          rText=rText.replace(/response A/g,'Baseline').replace(/response B/g,'Skills');
          rText=rText.replace(/\bA's\b/g,"Baseline's").replace(/\bB's\b/g,"Skills'");
          rText=rText.replace(/\bA\b(?='s|\s+(?:is|has|does|was|also|correctly|demonstrates|provides|includes|uses|handles|covers|offers|shows|gives|adds|lacks|misses|fails))/g,'Baseline');
          rText=rText.replace(/\bB\b(?='s|\s+(?:is|has|does|was|also|correctly|demonstrates|provides|includes|uses|handles|covers|offers|shows|gives|adds|lacks|misses|fails))/g,'Skills');
        } else if(pos==='skills'){
          rText=rText.replace(/Response A/g,'Skills').replace(/Response B/g,'Baseline');
          rText=rText.replace(/response A/g,'Skills').replace(/response B/g,'Baseline');
          rText=rText.replace(/\bA's\b/g,"Skills'").replace(/\bB's\b/g,"Baseline's");
          rText=rText.replace(/\bA\b(?='s|\s+(?:is|has|does|was|also|correctly|demonstrates|provides|includes|uses|handles|covers|offers|shows|gives|adds|lacks|misses|fails))/g,'Skills');
          rText=rText.replace(/\bB\b(?='s|\s+(?:is|has|does|was|also|correctly|demonstrates|provides|includes|uses|handles|covers|offers|shows|gives|adds|lacks|misses|fails))/g,'Baseline');
        }
        s+=`<div class="judge-reasoning"><b>Judge (pairwise):</b> ${esc(rText)}${pr.winner?` <b>Winner: ${pr.winner}</b>`:''}</div>`;
      }
      s+=`<div class="response-grid">`;
      for(let cond of ['baseline','skills']){
        const scores=pr[cond+'_scores'];
        const other=cond==='baseline'?pr['skills_scores']:pr['baseline_scores'];
        const reasoning=pr[cond+'_reasoning']||'';
        s+=`<div class="response-col"><h4>${cond==='baseline'?'Baseline':'Skills'}</h4><div class="score-pills">`;
        for(let d of DIMS){
          const won=scores[d]>other[d];const lost=scores[d]<other[d];
          const icon=won?'▲':lost?'▼':'=';
          const cls=won?'pill-green':lost?'pill-red':'pill-yellow';
          s+=`<span class="pill ${cls}">${icon} ${DLABEL[d]}</span>`;
        }
        s+=`</div>`;
        if(cond==='skills'){
          const fl=DATA.skill_flags[pr.id];
          if(fl){
            s+=`<div style="margin:4px 0">`;
            const flagMap={"intended_loaded":["✓ Intended loaded","flag-intended"],"unintended_loaded":["⚠ Unintended loaded","flag-unintended"],"intended_not_loaded":["✗ Intended not loaded","flag-missing"],"no_skill_loaded":["○ No skill loaded","flag-none"]};
            for(let l of fl.labels){const[txt,cls]=flagMap[l]||[l,"flag-none"];s+=`<span class="flag ${cls}">${txt}</span>`}
            if(fl.loaded.length)s+=`<span style="font-size:.7rem;color:#666;margin-left:4px">loaded: ${fl.loaded.join(', ')}</span>`;
            s+=`</div>`;
          }
        }
        if(reasoning)s+=`<div class="judge-reasoning"><b>Judge:</b> ${esc(reasoning)}</div>`;
        s+=`<div class="response-text">${fmtMd(br[cond]||'(no response)')}</div></div>`;
      }
      s+=`</div></details>`;
    }
    s+=`</details></div>`;
    shtml+=s;
  }
  sc.innerHTML=shtml;
}
render();
</script></body></html>"""


def main():
    parser = argparse.ArgumentParser(description="Build HTML review from eval results")
    parser.add_argument("--eval-dir", type=Path, default=Path(__file__).parent,
                        help="Root eval directory")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output HTML path (default: eval/results/review.html)")
    parser.add_argument("--version", type=str, default=None,
                        help="Build for a single version only (e.g., v3)")
    args = parser.parse_args()

    results_dir = args.eval_dir / "results"
    prompts_dir = args.eval_dir / "prompts"
    output = args.output or results_dir / (f"review_{args.version}.html" if args.version else "review.html")

    # Load score versions
    score_versions = {}
    if args.version:
        f = results_dir / f"scores_{args.version}.json"
        if f.exists():
            score_versions[args.version] = json.loads(f.read_text())
    else:
        for f in sorted(results_dir.glob("scores*.json")):
            name = f.stem
            label = name.replace("scores_", "").replace("scores", "v1")
            score_versions[label] = json.loads(f.read_text())

    if not score_versions:
        print("No scores files found")
        return

    prompts, targets = load_prompts(prompts_dir)
    # Load responses — merge from all versioned subdirectories
    responses = {}
    if args.version:
        resp_dir = results_dir / "responses" / args.version
        if not resp_dir.exists():
            resp_dir = results_dir / "responses"
        responses = load_responses(resp_dir)
    else:
        # Multi-version: load from each version's subdirectory, latest wins on conflict
        for label in sorted(score_versions.keys()):
            resp_dir = results_dir / "responses" / label
            if resp_dir.exists():
                responses.update(load_responses(resp_dir))
        # Fall back to flat directory if nothing found
        if not responses:
            responses = load_responses(results_dir / "responses")
    skill_content = load_skill_content(Path("skills"))
    skill_flags = detect_skill_flags(responses, targets)

    # Build skill data per version
    all_versions = {}
    all_summaries = {}
    for label, scores in score_versions.items():
        all_versions[label] = build_skill_data(scores)
        all_summaries[label] = compute_summary(scores)

    embedded = json.dumps({"versions": all_versions, "summaries": all_summaries,
                           "prompts": prompts, "responses": responses,
                           "skill_content": skill_content,
                           "skill_flags": skill_flags,
                           "version_labels": list(score_versions.keys())},
                          ensure_ascii=False)

    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", embedded)
    output.write_text(html)

    n_prompts = sum(len(s["prompts"]) for s in list(all_versions.values())[0])
    print(f"Wrote {output} — {n_prompts} prompts, {len(score_versions)} version(s): {list(score_versions.keys())}")


if __name__ == "__main__":
    main()
