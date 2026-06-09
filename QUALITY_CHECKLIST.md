---
title: Quality Checklist
inclusion: fileMatch
fileMatchPattern: 'skills/*/SKILL.md'
---

# Skill Quality Checklist

Use this checklist when authoring or reviewing a skill. A skill should satisfy every item before merging.

## Frontmatter

- [ ] `name` is present and matches the directory name
- [ ] `description` is a clear one-sentence summary
- [ ] `version` follows semver
- [ ] `tags` include a `category:reasoning` or `category:pipeline` entry
- [ ] Pipeline skills: `validated_against` includes date and key package versions

## Structure

- [ ] Required sections present: **Overview**, **Usage**, **Core Concepts**
- [ ] File is under 500 lines
- [ ] **Response Format** section present (prevents coherence regression)
- [ ] Reasoning skills: Response Format includes "do not narrate" instruction for decision trees

## Content Quality

- [ ] Triggers are concrete (specific task phrases, not vague topics)
- [ ] Domain expertise is actionable (decision rules, checklists, commands) rather than generic background
- [ ] Skill is self-contained and works independently of other skills
- [ ] References are cited for any clinical, scientific, or regulatory claims

## Testing

- [ ] Tested with at least two representative example prompts in Kiro
- [ ] Example prompts and outputs contain no PII or PHI (use synthetic or public data)

## Sign-off

- [ ] Author has reviewed every item above
- [ ] Reviewer has reviewed every item above
