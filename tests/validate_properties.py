#!/usr/bin/env python3
"""Repo-wide property validation for HCLS Skills Expansion spec.

Covers Properties 1, 2, 3, 8, 9, 11 from the design document.
Run from the repo root: python tests/validate_properties.py
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AGENTS_DIR = REPO_ROOT / "agents"

EXCLUDED_FILES = {
    "IMPLEMENTATION-GAPS.md",
    "validate_properties.py",
}
EXCLUDED_DIRS = {".git", ".kiro", "node_modules", "__pycache__", "tests", "results"}

REQUIRED_FRONTMATTER = ["name", "description", "usage", "version", "tags"]

NON_INCLUSIVE_TERMS = ["whitelist", "blacklist", "master", "slave"]

errors = []


def error(prop: str, msg: str):
    errors.append(f"[{prop}] {msg}")


# -------------------------------------------------------------------------
# Property 1: Skill format uniformity
# -------------------------------------------------------------------------
def check_property_1():
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            error("P1", f"{entry.name}/ missing SKILL.md")
            continue

        content = skill_md.read_text()
        if not content.startswith("---"):
            error("P1", f"{entry.name}/SKILL.md missing YAML frontmatter")
            continue

        # Extract frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            error("P1", f"{entry.name}/SKILL.md malformed frontmatter")
            continue

        fm_text = parts[1]
        fm = {}
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key = line.split(":", 1)[0].strip()
                val = line.split(":", 1)[1].strip()
                fm[key] = val

        for field in REQUIRED_FRONTMATTER:
            if field not in fm:
                error("P1", f"{entry.name}/SKILL.md missing frontmatter field: {field}")

        if "name" in fm and fm["name"] != entry.name:
            error("P1", f"{entry.name}/SKILL.md name='{fm['name']}' != folder name")

        if "tags" in fm:
            tags_str = fm["tags"]
            if not tags_str.startswith("[skill"):
                # Check if first tag is skill
                if "skill" not in tags_str.split(",")[0]:
                    error("P1", f"{entry.name}/SKILL.md tags[0] is not 'skill'")


# -------------------------------------------------------------------------
# Property 2: No broken references
# -------------------------------------------------------------------------
def check_property_2():
    broken_pattern = re.compile(r"skill://\.\./skills/")
    flat_pattern = re.compile(r"skills/([\w-]+)\.md(?!\w)")

    for fpath in _iter_repo_files():
        if fpath.name in EXCLUDED_FILES:
            continue
        try:
            content = fpath.read_text(errors="ignore")
        except Exception:
            continue

        if broken_pattern.search(content):
            error("P2", f"{fpath.relative_to(REPO_ROOT)}: contains skill://../skills/ pattern")

        # Check skill:// URIs resolve to existing dirs
        for match in re.finditer(r"skill://([a-z0-9-]+)", content):
            skill_name = match.group(1)
            if not (SKILLS_DIR / skill_name).is_dir():
                error("P2", f"{fpath.relative_to(REPO_ROOT)}: skill://{skill_name} does not resolve to a skills/ directory")


# -------------------------------------------------------------------------
# Property 3: Self-containment
# -------------------------------------------------------------------------
def check_property_3():
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text()

        # No file:// references outside own folder
        for match in re.finditer(r'file://([^\s"]+)', content):
            ref = match.group(1)
            if ref.startswith("AGENTS") or ".." in ref:
                error("P3", f"{entry.name}/SKILL.md has external file:// ref: {ref}")

        # No skill:// cross-references
        if "skill://" in content:
            error("P3", f"{entry.name}/SKILL.md contains skill:// cross-reference")


# -------------------------------------------------------------------------
# Property 8: Agent bundle validity
# -------------------------------------------------------------------------
def check_property_8():
    for fpath in sorted(AGENTS_DIR.glob("*.json")):
        try:
            data = json.loads(fpath.read_text())
        except Exception as e:
            error("P8", f"{fpath.name}: invalid JSON: {e}")
            continue

        resources = data.get("resources", [])
        for res in resources:
            if res.startswith("skill://"):
                skill_name = res.replace("skill://", "")
                if not (SKILLS_DIR / skill_name).is_dir():
                    error("P8", f"{fpath.name}: skill://{skill_name} does not resolve")


# -------------------------------------------------------------------------
# Property 9: No hardcoded user paths or non-inclusive language
# -------------------------------------------------------------------------
def check_property_9():
    user_path_pattern = re.compile(r"/Users/\w+/")

    for fpath in _iter_repo_files():
        if fpath.name in EXCLUDED_FILES:
            continue
        try:
            content = fpath.read_text(errors="ignore")
        except Exception:
            continue

        if user_path_pattern.search(content):
            error("P9", f"{fpath.relative_to(REPO_ROOT)}: contains hardcoded /Users/ path")

        content_lower = content.lower()
        for term in NON_INCLUSIVE_TERMS:
            # Skip if it's in a "don't use" table or similar documentation context
            if term in content_lower:
                # Check it's not just documenting the term to avoid
                lines_with_term = [
                    l for l in content.split("\n")
                    if term in l.lower()
                    and "don't use" not in l.lower()
                    and "instead" not in l.lower()
                    and "avoid" not in l.lower()
                    and "| " not in l  # table rows documenting terms
                ]
                if lines_with_term:
                    error("P9", f"{fpath.relative_to(REPO_ROOT)}: contains non-inclusive term '{term}'")


# -------------------------------------------------------------------------
# Property 11: Script safety
# -------------------------------------------------------------------------
def check_property_11():
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.is_dir():
            continue

        for script in sorted(scripts_dir.glob("*.py")):
            content = script.read_text()

            if "argparse" not in content:
                error("P11", f"{script.relative_to(REPO_ROOT)}: does not use argparse")

            if "shell=True" in content:
                error("P11", f"{script.relative_to(REPO_ROOT)}: uses shell=True")


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _iter_repo_files():
    """Iterate over text files in the repo, excluding .git and binary files."""
    for fpath in REPO_ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in fpath.parts):
            continue
        if fpath.is_file() and fpath.suffix in (
            ".md", ".json", ".py", ".sh", ".txt", ".yaml", ".yml", ".toml",
        ):
            yield fpath


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main():
    print("Running property validations...\n")

    checks = [
        ("Property 1: Skill format uniformity", check_property_1),
        ("Property 2: No broken references", check_property_2),
        ("Property 3: Self-containment", check_property_3),
        ("Property 8: Agent bundle validity", check_property_8),
        ("Property 9: No hardcoded paths / inclusive language", check_property_9),
        ("Property 11: Script safety", check_property_11),
    ]

    for name, fn in checks:
        print(f"  Checking {name}...")
        fn()

    print()
    if errors:
        print(f"FAILED — {len(errors)} error(s):\n")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("ALL PROPERTIES PASSED ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()
