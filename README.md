# Agent Skills for Healthcare & Life Sciences

[![License: MIT-0](https://img.shields.io/badge/License-MIT--0-yellow.svg)](./LICENSE)
[![Skills](https://img.shields.io/badge/Skills-38-brightgreen.svg)](./skills/)
[![Domains](https://img.shields.io/badge/Domains-11-blue.svg)](./skills/)
[![Works with](https://img.shields.io/badge/Works_with-Amazon_Quick_|_Kiro_|_Claude_Code_|_Codex-purple.svg)](#platform-compatibility)

A curated collection of agent skills for healthcare and life sciences (HCLS) workflows, following the [Agent Skills open standard](https://agentskills.io). **These 38 domain skills make any AI agent measurably better at HCLS questions.** In a [410-prompt pairwise evaluation](./eval/TECHNICAL_REPORT.md) (380 single-skill + 30 cross-skill) judged by Claude Opus 4.7, skills win **70%** of head-to-head comparisons, with **78% critical thinking** and **69% scientific accuracy** win rates. Skills work on 20+ platforms including Kiro, Amazon Quick, Amazon Bedrock AgentCore, AWS Strands SDK, Claude Code, OpenAI Codex, CrewAI, LangChain, and more.

Skills fall into two categories: **reasoning skills** encode methodology, decision frameworks, and domain expertise to guide the agent's thinking (e.g., ACMG variant classification, target trial emulation, HEDIS measure specification); **pipeline skills** encode tool-specific commands, code patterns, and parameter tables that produce runnable artifacts (e.g., GATK4 variant calling, RDKit cheminformatics, HL7v2 parsing). Together they make any AI agent a competent collaborator across [genomics](#genomics), [single-cell analysis](#single-cell-analysis), [medical imaging](#medical-imaging), [protein structure](#protein-structure), [translational research](#cross-domain), [pharmacoepidemiology](#pharmacoepidemiology--real-world-data), [clinical data](#clinical-data), [drug discovery](#drug-discovery), [proteomics](#proteomics), [clinical data review](#clinical-data-review), [multi-omics integration](#multi-omics-integration), [healthcare operations](#healthcare-operations), [machine learning](#cross-domain), and [AWS architecture](#cross-domain).

## Why Agent Skills for Healthcare & Life Sciences? 

The line between scientist and builder is fading. Molecular biologists want to classify variants from sequencing data, run single-cell analysis pipelines, and design validation studies all without waiting for IT to scope a project. AI agents like Amazon Quick and Kiro make this possible: universal tools that let a researcher go from question to working system in minutes.

Capability is no longer the bottleneck; methodology is. Every generation of LLMs grows more powerful and knowledgeable. They know facts but not *procedures*; the multi-step decision chains that domain experts internalize over years. They have "read every textbook" but never worked through the nuance of biology or patient care. When an epidemiologist asks an AI agent to emulate a target trial from claims data, adjust for time-varying confounding, or validate a risk stratification model, reproducible output must be both methodologically and scientifically sound and not just plausible. In regulated domains like healthcare and life sciences, the gap between plausible and correct has patient safety and compliance consequences.

Agent skills close this gap. A skill encodes the structured reasoning that experts follow, such as exact criteria, specific thresholds, failure modes that only experience teaches. Think of it as the computational equivalent of a lab protocol: instead of sitting in a binder, it actively guides the agent in real time. Three properties make this better than the alternatives:

1. **Better than long prompts.** Real research tasks require multi-step reasoning. Benchmarks like [LifeSciBench](https://openai.com/index/introducing-life-sci-bench/) show 79% of realistic life science tasks involve multiple decision steps. A monolithic system prompt is brittle, unversioned, and impossible to share across a team. A skill gives the agent a structured starting point: pre-encoded decision logic that's reproducible across users, sessions, and platforms.

2. **Portable and updateable.** These skills follow the open [Agent Skills standard](https://agentskills.io) and work across 20+ platforms (Kiro, Quick, Strands Agent SDK, AgentCore, Claude Code, Codex). When Center of Medicare and Medicaid Services publishes new HCC coefficients or ACMG updates classification criteria, you edit the skill to reflect that knowledge for all future work.

3. **Encodes what textbooks don't.** Skills capture tacit and institutional knowledge: which bioinformatics parameters work for your sequencer, which reagent vendor to trust, which clinical codes your payer actually accepts. The kind of judgment that lives in a senior scientist's head and takes years to transfer.

Our evaluation across 38 skills and 11 HCLS domains shows that skilled agents win 69.5% of head-to-head comparisons with critical thinking (the ability to apply the right framework, challenge assumptions, and flag limitations) improving most results (78% win rate, Cohen's d = 0.65). Response variance drops by up to 51%. Outputs become reproducible, not just occasionally correct. And the biggest gains appear exactly where unguided agents fail most: on the hard, multi-step regulatory and methodological questions where getting it wrong has consequences.

This is what raises the floor for every scientist without lowering the ceiling. Skills don't skip the learning; they provide scaffolding so a new postdoc's analysis meets the same methodological standard as the PI's while they build understanding of *why* each step matters. The work shifts from instructing the agent ("here's how to avoid immortal time bias") to exercising judgment at a higher level ("is a new-user active-comparator design even the right approach?").


## Skill Catalog

<details>
<summary>Click to expand full catalog (38 skills across 11 domains)</summary>

### Genomics

| Name | Category | Description |
| --- | --- | --- |
| [genomic-variant-interpretation](./skills/genomic-variant-interpretation/) | reasoning | ACMG/AMP variant classification, ClinVar evidence, computational predictor thresholds |
| [variant-calling](./skills/variant-calling/) | pipeline | BWA-MEM2, GATK4 HaplotypeCaller, joint genotyping, VQSR, Mutect2 |
| [rna-seq-analysis](./skills/rna-seq-analysis/) | pipeline | STAR/Salmon alignment, featureCounts, DESeq2 differential expression |
| [ngs-quality-control](./skills/ngs-quality-control/) | pipeline | FastQC, fastp, Picard metrics, mosdepth coverage, MultiQC |

### Single-Cell Analysis

| Name | Category | Description |
| --- | --- | --- |
| [biomarker-discovery](./skills/biomarker-discovery/) | reasoning | Prognostic vs predictive biomarkers, feature selection, validation design |
| [scrna-seq-pipeline](./skills/scrna-seq-pipeline/) | pipeline | Scanpy/AnnData processing: QC, normalization, HVG, PCA, UMAP, Leiden |
| [cell-type-annotation](./skills/cell-type-annotation/) | pipeline | CellTypist, SingleR, marker-based annotation, label transfer |
| [trajectory-analysis](./skills/trajectory-analysis/) | pipeline | Pseudotime, PAGA, RNA velocity (scVelo), CellRank fate probabilities |

### Medical Imaging

| Name | Category | Description |
| --- | --- | --- |
| [imaging-study-design](./skills/imaging-study-design/) | reasoning | Preprocessing strategy selection, DICOM de-ID risk, imaging biomarker choice |
| [digital-pathology](./skills/digital-pathology/) | pipeline | TIAToolbox, H-optimus-0, whole-slide image tiling and inference |
| [dicom-processing](./skills/dicom-processing/) | pipeline | DICOM parsing, NIfTI conversion, de-identification, BIDS organization |
| [radiology-preprocessing](./skills/radiology-preprocessing/) | pipeline | HD-BET skull stripping, N4 bias correction, ANTs/FSL registration |

### Protein Structure

| Name | Category | Description |
| --- | --- | --- |
| [structure-based-drug-design](./skills/structure-based-drug-design/) | reasoning | Druggability assessment, docking strategy, scoring function selection |
| [protein-structure-analysis](./skills/protein-structure-analysis/) | pipeline | PDB parsing, RMSD, Ramachandran, binding pocket detection (fpocket) |
| [molecular-docking](./skills/molecular-docking/) | pipeline | AutoDock Vina receptor/ligand prep, grid box, virtual screening |

### Cross-Domain

| Name | Category | Description |
| --- | --- | --- |
| [translational-research](./skills/translational-research/) | reasoning | T0-T4 translation stages, target validation, neuro hypothesis validation |
| [ml-researcher](./skills/ml-researcher/) | reasoning | ML experiment design, evaluation strategy, reporting standards for HCLS |
| [aws-genai-ml-architect](./skills/aws-genai-ml-architect/) | reasoning | AWS service selection, HIPAA compliance, MLOps for regulated workloads |

### Pharmacoepidemiology & Real-World Data

| Name | Category | Description |
| --- | --- | --- |
| [pharmacoepidemiology](./skills/pharmacoepidemiology/) | reasoning | New-user designs, target trial emulation, immortal time bias, propensity scores |
| [rwd-cohort-analysis](./skills/rwd-cohort-analysis/) | pipeline | Claims cohort identification, PDC adherence, Kaplan-Meier, Cox models, PS matching |

### Clinical Data

| Name | Category | Description |
| --- | --- | --- |
| [clinical-data-standards](./skills/clinical-data-standards/) | reasoning | MedDRA hierarchy, ICD-10 structure, SNOMED CT, LOINC, terminology mapping |
| [ehr-data-parsing](./skills/ehr-data-parsing/) | pipeline | HL7v2 message parsing, FHIR R4 extraction, format conversion, data quality |

### Drug Discovery

| Name | Category | Description |
| --- | --- | --- |
| [drug-repurposing](./skills/drug-repurposing/) | reasoning | Target-based vs phenotype-based repurposing, DGIdb, OpenTargets, translatability |
| [cheminformatics](./skills/cheminformatics/) | pipeline | RDKit descriptors, Lipinski/PAINS filtering, Morgan fingerprints, MMP analysis |

### Proteomics

| Name | Category | Description |
| --- | --- | --- |
| [quantitative-proteomics](./skills/quantitative-proteomics/) | reasoning | LFQ/TMT/DIA strategy, imputation methods, normalization, DE interpretation |

### Clinical Data Review

| Name | Category | Description |
| --- | --- | --- |
| [cdisc-compliance](./skills/cdisc-compliance/) | reasoning | SDTM/ADaM rules, FDA/PMDA expectations, controlled terminology, define.xml |
| [edc-data-validation](./skills/edc-data-validation/) | pipeline | EDC export validation, range checks, SDTM structure, CT validation |

### Multi-Omics Integration

| Name | Category | Description |
| --- | --- | --- |
| [multi-omics-integration](./skills/multi-omics-integration/) | reasoning | Early/intermediate/late integration, batch correction, partial overlap |
| [multi-omics-pipeline](./skills/multi-omics-pipeline/) | pipeline | ID mapping, ComBat batch correction, MOFA2, GSEA enrichment |

### Healthcare Operations

| Name | Category | Description |
| --- | --- | --- |
| [claims-billing-rules](./skills/claims-billing-rules/) | reasoning | CMS billing rules, NCCI edits, FWA patterns, upcoding/unbundling detection |
| [claims-analytics](./skills/claims-analytics/) | pipeline | X12 837/835 parsing, provider profiling, NCCI validation, duplicate detection |
| [risk-adjustment-strategy](./skills/risk-adjustment-strategy/) | reasoning | CMS-HCC V24/V28, disease hierarchies, RAF methodology, coding gap strategy |
| [risk-adjustment](./skills/risk-adjustment/) | pipeline | ICD-10-to-HCC crosswalk, RAF score calculation, Rx/lab proxy gap detection |
| [pa-clinical-policy](./skills/pa-clinical-policy/) | reasoning | Step therapy, medical necessity, LCD/NCD rules, Da Vinci PAS, appeals |
| [pa-decision-automation](./skills/pa-decision-automation/) | pipeline | X12 278/FHIR PAS parsing, rules engine, ML classifier, denial analysis |
| [hedis-measure-specification](./skills/hedis-measure-specification/) | reasoning | HEDIS measure structure, denominator/numerator/exclusion logic, NCQA audit, care gaps |
| [risk-stratification-indices](./skills/risk-stratification-indices/) | reasoning | LACE, Charlson, Elixhauser indices, SDOH Z-codes, ADI scoring |
| [quality-measures](./skills/quality-measures/) | pipeline | HEDIS calculation, enrollment checks, care gap detection, utilization rates |

</details>

## Installation

```bash
npx skills add awslabs/hcls-agent-skills
```

Or clone the repository for full control:

```bash
git clone https://github.com/awslabs/hcls-agent-skills.git
cd ./hcls-agent-skills
./install.sh --target <platform>
```

### Platform Compatibility

These skills follow the [Agent Skills open standard](https://agentskills.io) (`SKILL.md` + YAML frontmatter) and work across multiple AI assistants:

| Platform | Install Command | How It Works |
|----------|----------------|--------------|
| **Kiro IDE** | `./install.sh --target kiro` | Copies skills to `~/.kiro/skills/` and agent config to `~/.kiro/agents/` |
| **Kiro CLI** | `./install.sh --target kiro` | Same as above; switch with `/agent hcls` |
| **Claude Code** | `./install.sh --target claude-code` | Symlinks skills into `.claude/skills/` for auto-discovery |
| **Quick Desktop** | `./install.sh --target quick-desktop` | Prints upload instructions (GUI-only: Settings → Skills → Upload) |
| **GitHub Copilot, Cursor, Codex, Gemini CLI, 50+ others** | `npx skills add .` | Universal CLI from [vercel-labs/skills](https://github.com/vercel-labs/skills) |
| **CrewAI** | `skills=["./skills"]` | Native parameter on Agent class |
| **LangChain / LangGraph** | Documented pattern | Skills as prompt-driven specializations |
| **AWS Strands SDK** | `AgentSkills(skills="./skills/")` | Built-in plugin, deploys to Lambda/Fargate |
| **Claude Messages API** | Upload via Skills Management API | First-class `container` parameter with CRUD |

### Kiro (IDE & CLI)

```bash
./install.sh --target kiro

# In Kiro CLI, switch to the unified agent:
/agent hcls
```

Or load individual skills on the fly:
```
/context add ./hcls-agent-skills/skills/variant-calling/SKILL.md
```

#### Multi-Agent Mode (Kiro)

For context-efficient specialist routing (loads ~15K tokens per specialist instead of ~80K for all 38 skills):

```bash
./install.sh --target kiro --mode multiagent

# Switch to the coordinator:
/agent hcls-multiagent
```

The coordinator routes queries to 8 domain specialists:

| Specialist | Domain |
|-----------|--------|
| hcls-genomics | Variant classification, NGS pipelines, RNA-seq |
| hcls-omics | Single-cell, proteomics, multi-omics, biomarkers |
| hcls-imaging | DICOM, digital pathology, radiology preprocessing |
| hcls-drug-discovery | Docking, cheminformatics, drug repurposing, translational |
| hcls-clinical-data | HL7/FHIR, CDISC/SDTM, EDC validation |
| hcls-rwe | Pharmacoepidemiology, RWD cohorts, risk indices |
| hcls-healthcare-ops | Claims billing, risk adjustment, prior auth, HEDIS |
| hcls-ai-infra | ML experiment design, AWS architecture |

See [`docs/multiagent-architecture.md`](./docs/multiagent-architecture.md) for the full architecture.

### Amazon Quick

Amazon Quick loads skills via GUI upload of individual `SKILL.md` files:

```bash
# See which skills to upload and instructions
./install.sh --target quick-desktop
```

Upload path: **Settings → Capabilities → Skills → Upload** → select a `SKILL.md` file. Start with one domain and add more as needed. Follow the instructions in [Skills and agents](https://docs.aws.amazon.com/quick/latest/userguide/skills-and-agents-desktop.html) in the Amazon Quick documentation.

### Claude Code

```bash
# Install into your project (symlinks to repo, so updates propagate)
./install.sh --target claude-code --project-dir /path/to/your/project
```

Skills auto-activate when Claude Code detects relevant topics in your prompts. No agent config needed — Claude Code discovers skills from `.claude/skills/` automatically.

## Quick Start

Invoke a skill by describing the task in natural language — your agent will match on the skill's triggers:

```
> I have a new candidate biomarker for early-stage NSCLC. Help me design a validation study.
[agent loads translational-research skill]
```

Or request a pipeline skill explicitly:

```
> Use the digital-pathology skill to tile this SVS file at 20x with 512px tiles.
```

## Evaluation

An automated evaluation suite measures whether skills improve agent responses. See [`eval/README.md`](./eval/README.md) for full documentation.

**Quick run:**
```bash
conda activate drift-experiments
./install.sh --target kiro --path .
python -m eval.run --parallel 2 --version v1
python eval/build_review.py
open eval/results/review.html
```

**Latest results (pairwise, 410 prompts — 38 skills + 3 cross-skill categories):** Overall delta **+1.5**, skills win rate **69.5%**, critical thinking **+3.4**. Eval reports show 41 entries: 38 standalone skills plus 3 cross-skill prompt categories that test multi-skill activation. See [`eval/TECHNICAL_REPORT.md`](./eval/TECHNICAL_REPORT.md) for the full analysis.

## Customization

Want to modify a skill for your org, or create a new one? See [CUSTOMIZING.md](./CUSTOMIZING.md) and [SKILL_DESIGN_GUIDE.md](./SKILL_DESIGN_GUIDE.md) for practical guidance on adapting skills to your workflows.

## Contributing

New skills and improvements are welcome. See [CONTRIBUTING.md](./CONTRIBUTING.md) and the [QUALITY_CHECKLIST.md](./QUALITY_CHECKLIST.md) before submitting.

## License

[MIT-0](./LICENSE)
