#!/usr/bin/env python3
"""Generate eval prompts for each HCLS skill via Bedrock Converse API."""

import argparse
import json
import re
from pathlib import Path

import boto3
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
SINGLE_DIR = ROOT / "eval" / "prompts" / "single"
CROSS_DIR = ROOT / "eval" / "prompts" / "cross"

MODEL_ID = "us.anthropic.claude-sonnet-4-6"

DOMAIN_MAP = {
    "genomic-variant-interpretation": "genomics",
    "variant-calling": "genomics",
    "rna-seq-analysis": "genomics",
    "ngs-quality-control": "genomics",
    "biomarker-discovery": "single-cell",
    "scrna-seq-pipeline": "single-cell",
    "cell-type-annotation": "single-cell",
    "trajectory-analysis": "single-cell",
    "imaging-study-design": "imaging",
    "digital-pathology": "imaging",
    "dicom-processing": "imaging",
    "radiology-preprocessing": "imaging",
    "structure-based-drug-design": "protein-structure",
    "protein-structure-analysis": "protein-structure",
    "molecular-docking": "protein-structure",
    "translational-research": "cross-domain",
    "ml-researcher": "cross-domain",
    "aws-genai-ml-architect": "cross-domain",
    "pharmacoepidemiology": "pharmacoepidemiology",
    "rwd-cohort-analysis": "pharmacoepidemiology",
    "clinical-data-standards": "clinical-data",
    "ehr-data-parsing": "clinical-data",
    "drug-repurposing": "drug-discovery",
    "cheminformatics": "drug-discovery",
    "quantitative-proteomics": "proteomics",
    "proteomics-analysis": "proteomics",
    "cdisc-compliance": "clinical-data-review",
    "edc-data-validation": "clinical-data-review",
    "multi-omics-integration": "multi-omics",
    "multi-omics-pipeline": "multi-omics",
    "claims-billing-rules": "healthcare-ops",
    "claims-analytics": "healthcare-ops",
    "risk-adjustment-strategy": "healthcare-ops",
    "risk-adjustment": "healthcare-ops",
    "pa-clinical-policy": "healthcare-ops",
    "pa-decision-automation": "healthcare-ops",
    "quality-measure-specification": "healthcare-ops",
    "quality-measures": "healthcare-ops",
}

CROSS_COMBOS = [
    {
        "id": "genomics-variant-pipeline",
        "skills": ["genomic-variant-interpretation", "variant-calling", "ngs-quality-control"],
        "domain": "genomics",
    },
    {
        "id": "drug-discovery-structural",
        "skills": ["drug-repurposing", "cheminformatics", "structure-based-drug-design"],
        "domain": "drug-discovery",
    },
    {
        "id": "pharma-rwd-clinical",
        "skills": ["pharmacoepidemiology", "rwd-cohort-analysis", "clinical-data-standards"],
        "domain": "pharmacoepidemiology",
    },
]

META_PROMPT = """\
You are generating a test question for evaluating an AI assistant's domain expertise.

Skill name: {name}
Skill description: {description}
Usage context: {usage}

Generate a single self-contained research question that:
1. Would naturally trigger this skill's domain
2. Provides enough specific context (data, parameters, constraints) that an expert could write a complete response without asking clarifying questions
3. Is 150-300 words
4. Requests multiple concrete deliverables (analysis, recommendations, code, or designs)
5. Includes realistic but fictional data (patient counts, gene names, specific parameters)

Output ONLY the question text, nothing else."""

CROSS_META_PROMPT = """\
You are generating a test question for evaluating an AI assistant's domain expertise.

This question must span ALL of the following skills simultaneously:

{skill_block}

Generate a single self-contained research question that:
1. Would naturally require expertise from ALL listed skills
2. Provides enough specific context (data, parameters, constraints) that an expert could write a complete response without asking clarifying questions
3. Is 200-400 words
4. Requests multiple concrete deliverables that touch each skill's domain
5. Includes realistic but fictional data (patient counts, gene names, specific parameters)

Output ONLY the question text, nothing else."""


def parse_skill_md(path: Path) -> dict | None:
    """Extract frontmatter fields from a SKILL.md file."""
    text = path.read_text()
    m = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not m:
        return None
    fm_text = m.group(1)
    # Simple key extraction (avoids yaml.safe_load failures on unquoted colons)
    def get_field(key):
        match = re.search(rf"^{key}:\s*(.+?)(?:\n[a-z]|\Z)", fm_text, re.MULTILINE | re.DOTALL)
        return match.group(1).strip() if match else ""
    name = get_field("name") or path.parent.name
    description = get_field("description")
    # Extract first paragraph after ## Usage
    usage_match = re.search(r"## Usage\n\n(.+?)(?:\n\n|\n##)", text, re.DOTALL)
    usage = usage_match.group(1).strip() if usage_match else get_field("usage")
    return {"name": name, "description": description, "usage": usage}


def call_bedrock(client, prompt: str) -> str:
    """Call Bedrock Converse API and return the text response."""
    resp = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.7},
    )
    return resp["output"]["message"]["content"][0]["text"].strip()


def write_prompt_yaml(path: Path, id_: str, prompt: str, skills: list[str], domain: str, difficulty: str = "intermediate"):
    """Write a prompt YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "id": id_,
        "prompt": prompt,
        "target_skills": skills,
        "domain": domain,
        "difficulty": difficulty,
    }
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True))


PROMPTS_PER_SKILL = 10
DIFFICULTY_SCHEDULE = ["easy"] * 3 + ["intermediate"] * 4 + ["hard"] * 3

META_PROMPT_N = """You are generating test question #{n} of {total} for evaluating an AI assistant's domain expertise.

Skill name: {name}
Skill description: {description}
Usage context: {usage}

Difficulty level: {difficulty}
- easy: straightforward application of the skill's core concepts
- intermediate: requires combining multiple concepts, realistic scenario
- hard: edge cases, conflicting evidence, requires deep expertise

Generate a single self-contained research question that:
1. Would naturally trigger this skill's domain
2. Provides enough specific context (data, parameters, constraints) that an expert could write a complete response without asking clarifying questions
3. Is 150-300 words
4. Requests multiple concrete deliverables (analysis, recommendations, code, or designs)
5. Includes realistic but fictional data (patient counts, gene names, specific parameters)
6. Is DIFFERENT from any previous question — cover a different aspect or sub-topic of the skill

Output ONLY the question text, nothing else."""


def main():
    parser = argparse.ArgumentParser(description="Generate eval prompts for HCLS skills")
    parser.add_argument("--force", action="store_true", help="Overwrite existing prompt files")
    parser.add_argument("--count", type=int, default=PROMPTS_PER_SKILL, help="Prompts per skill")
    args = parser.parse_args()

    client = boto3.client("bedrock-runtime", region_name="us-west-2")

    # --- Single-skill prompts (N per skill) ---
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    print(f"Found {len(skill_files)} skills, generating {args.count} prompts each")

    skill_cache: dict[str, dict] = {}
    for sf in skill_files:
        info = parse_skill_md(sf)
        if not info:
            print(f"  WARN: could not parse {sf}, skipping")
            continue
        name = info["name"]
        skill_cache[name] = info
        domain = DOMAIN_MAP.get(name, "unknown")

        for i in range(args.count):
            pid = f"{name}-{i+1:02d}"
            out = SINGLE_DIR / f"{pid}.yaml"
            if out.exists() and not args.force:
                continue
            difficulty = DIFFICULTY_SCHEDULE[i % len(DIFFICULTY_SCHEDULE)]
            try:
                prompt = call_bedrock(client, META_PROMPT_N.format(
                    n=i+1, total=args.count, difficulty=difficulty, **info))
                write_prompt_yaml(out, pid, prompt, [name], domain, difficulty)
                print(f"  OK   {pid} ({difficulty})")
            except Exception as e:
                print(f"  WARN {pid}: {e}")
        # Print summary for this skill
        existing = list(SINGLE_DIR.glob(f"{name}-*.yaml"))
        print(f"  {name}: {len(existing)}/{args.count} prompts")

    # --- Cross-skill prompts (N per combo) ---
    print(f"\nGenerating {args.count} prompts for each of {len(CROSS_COMBOS)} cross-skill combos")
    for combo in CROSS_COMBOS:
        blocks = []
        for s in combo["skills"]:
            info = skill_cache.get(s)
            if info:
                blocks.append(f"- Skill: {info['name']}\n  Description: {info['description']}\n  Usage: {info['usage']}")
        skill_block = "\n\n".join(blocks)

        for i in range(args.count):
            pid = f"{combo['id']}-{i+1:02d}"
            out = CROSS_DIR / f"{pid}.yaml"
            if out.exists() and not args.force:
                continue
            difficulty = DIFFICULTY_SCHEDULE[i % len(DIFFICULTY_SCHEDULE)]
            try:
                prompt = call_bedrock(client, CROSS_META_PROMPT.format(skill_block=skill_block))
                write_prompt_yaml(out, pid, prompt, combo["skills"], combo["domain"], difficulty)
                print(f"  OK   {pid}")
            except Exception as e:
                print(f"  WARN {pid}: {e}")
        existing = list(CROSS_DIR.glob(f"{combo['id']}-*.yaml"))
        print(f"  {combo['id']}: {len(existing)}/{args.count} prompts")

    print("\nDone.")


if __name__ == "__main__":
    main()
