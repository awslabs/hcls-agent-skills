# Translational Research Skill Demo: Skilled vs Unskilled Comparison

## Purpose

Demonstrates how the `translational-research` skill produces systematic, framework-driven target validation assessments versus a base model's expert-opinion-style response. The skill enforces a structured decision methodology (T-staging, convergence audit, kill criteria) that the base model skips.

## Why This Skill Matters: Domain Context

### The Problem: 90% of Drug Programs Fail, Mostly Due to Undisciplined Translation

The pharmaceutical industry spends ~$2.6B per approved drug, with a 90% clinical failure rate. The majority of failures aren't bad science — they're bad decision-making: advancing programs without clear gates, testing biology with clinical endpoints too early, or ignoring modality-specific barriers until it's too late. Translational research is where these expensive mistakes originate.

### Why a Generic LLM Gets This Wrong

1. **No kill criteria = no discipline.** A base model will list "risks" and "considerations" but won't name the specific result that should stop a program. In drug development, the most valuable output is often "stop" — killing a doomed program at $2M saves $200M downstream. Without explicit kill criteria, teams default to optimism bias and continue spending.

2. **T-staging is not intuitive.** The distinction between "mechanism exists" (T0), "it translates to humans" (T1), and "it works in a controlled trial" (T2) determines what evidence is needed next. A T0 program needs genetic convergence and functional validation; a T1 program needs PK/PD and target engagement. Proposing a Phase 2 trial for a T0 hypothesis wastes years and hundreds of millions.

3. **Convergence thresholds prevent premature advancement.** The skill requires ≥3 of 4 genetic convergence criteria (GWAS, rare-variant, eQTL colocalization, Mendelian randomization) before endorsing a target. This isn't arbitrary — it reflects the empirical observation that targets with <3 lines of human genetic evidence fail at 2-3× the rate of those with ≥3. A generic model will say "the genetics look promising" without quantifying how many independent lines of evidence actually exist.

4. **CNS drug development has modality-specific gates.** For a CNS antibody, blood-brain barrier penetration isn't a "nice to have" — it's existential. IgG antibodies achieve ~0.1% brain penetration. If you need 70% receptor occupancy and your Kd is 1nM, you need ~1nM free brain concentration, which requires ~1μM plasma concentration at 0.1% penetration — likely infeasible. The skill forces this calculation before committing to IND-enabling studies ($15-30M for a biologic). A generic model mentions BBB as one concern among many rather than as a blocking gate.

5. **"Decision it enables" prevents activity without purpose.** In academic and early-stage pharma, teams propose experiments because they're interesting or publishable — not because they enable a specific go/no-go decision. The skill forces every proposed experiment to name the decision it unlocks. This is the difference between a $50M research program and a $50M decision engine.

### What the Skill Encodes

The skill encodes a **4-step decision framework** (Orient → Audit → Decide → Flag) that mirrors how the best translational medicine teams operate:

- **Orient (T-staging)**: Forces the user to locate their hypothesis on the bench-to-bedside continuum before proposing next steps. This prevents the #1 failure mode: applying T2 evidence standards to a T0 hypothesis, or vice versa.
- **Audit (convergence checklist)**: Provides a quantitative threshold (≥3/4 criteria) for target enthusiasm, preventing premature commitment based on a single line of evidence.
- **Decide (minimum experiment)**: Recommends the cheapest, fastest experiment that resolves the biggest uncertainty — not the most comprehensive study. This embodies the "fail fast, fail cheap" principle that separates efficient programs from expensive ones.
- **Flag (failure modes)**: Forces explicit acknowledgment of what could go wrong, counteracting the confirmation bias that kills drug programs.

This framework is reproducible across team members, therapeutic areas, and modalities. It doesn't require a 20-year veteran to interpret — a junior scientist can follow the same decision tree and reach defensible conclusions.

---

## Prompt

```
We have GWAS data showing a significant locus near TREM2 for late-onset Alzheimer's disease, plus a rare-variant burden test showing loss-of-function variants increase risk 3-fold. We want to develop a TREM2 agonist antibody. Is this ready for IND-enabling studies? What's the next gate?
```

## How to Identify the Skilled Response

| Signal | With Skill | Without Skill |
|--------|-----------|---------------|
| **T-stage classification** | Opens with "T0" or "T0→T1 gate" — mandatory first step | Jumps into discussion without staging |
| **Convergence checklist** | Scores ≥3/4 criteria: GWAS, rare-variant, eQTL colocalization, cis-pQTL MR | Lists evidence without scoring against a threshold |
| **Kill criterion** | Names a specific falsifiable result that kills the program (e.g., "≥70% RO not achievable → program dies") | Vague "risks to consider" |
| **"Decision it enables"** | Every proposed experiment has an explicit decision column | Lists experiments without decision framing |
| **BBB as "gate not afterthought"** | Near-verbatim from skill; flags as blocking issue | Mentions BBB as one concern among many |
| **Free concentration / Kp,uu** | Demands unbound brain concentration, not total | Generic PK discussion |
| **Opening format** | ≤3 sentence recommendation first | Longer, less structured opening |
| **Failure modes section** | Explicit "Failure Modes Flagged" before closing | Scattered throughout or absent |
| **"Do not advance" language** | Direct: "do not advance to IND-enabling work until X" | Softer: "consider addressing before proceeding" |

## Skilled Response Characteristics (with `translational-research` skill)

The skilled agent applies the skill's 4-step framework in order:

1. **Orient** — classifies T-stage (T0), names next T-gate (T0→T1: proof of PD effect in human microglia in CNS)
2. **Audit** — scores convergence checklist (2/4, below ≥3/4 threshold), identifies weakest links ranked
3. **Decide** — recommends minimum experiments with "decision it enables" for each
4. **Flag** — explicit failure modes section before closing

Key outputs:
- Convergence: GWAS ✅, rare-variant ✅, eQTL ❓, MR ❓ → "2/4, below threshold for enthusiasm"
- Kill criterion: CNS exposure insufficient for ≥70% receptor occupancy
- BBB flagged as existential/blocking risk for antibody modality
- Recommends computational analyses first (MR + colocalization, weeks not months) before committing to expensive NHP studies
- Names specific datasets (Kosoy et al. for microglial eQTL, Olink/SomaScan for cis-pQTL)

## Unskilled Response Characteristics (without skill)

The base model produces excellent clinical science but:
- No T-stage classification
- No convergence checklist with scoring threshold
- No explicit kill criterion (what result stops the program)
- No "decision it enables" framing for proposed experiments
- Longer opening without the ≤3 sentence recommendation-first format
- Reads as expert opinion rather than systematic framework application
- Still mentions BBB and iPSC-microglia — but as discussion points, not as gates with go/no-go criteria

## Key Takeaway

> Both responses are scientifically sound. The difference is methodology: the skilled response applies a reproducible decision framework (T-stage → convergence audit → kill criterion → minimum experiment) that any team member can follow. The unskilled response requires a domain expert to interpret and prioritize.

## Evaluation Results (v4)

The `translational-research` skill achieved:
- **100% win rate** (10/10 prompts)
- **Cohen's d: +2.07** (large effect — second highest in the eval)
- **+5.1 critical thinking delta**
- **+2.5 scientific accuracy delta**
- **+20% improvement** from v3 → v4
