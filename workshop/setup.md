# Pre-Workshop Setup — HCLS Agent Skills (90 min)

> ⚠️ **Complete ALL steps before the workshop. There is no setup time during the session.**

This guide is self-contained. Work through it top to bottom. Budget 10–15 minutes.

## 1. Prerequisites

You'll work in a **pre-provisioned Linux compute environment** supplied by the workshop event (AWS Workshop Studio). It already has everything the workshop needs:

- **git**, **Python 3.12+**, **uv**, and **Node.js** (for `npx`) are pre-installed.
- An **AI coding assistant that supports skills** is already installed and signed in.
- A stable internet connection is provided.

You still do two things yourself (Section 2): **pick your harness** and **install the skills**.

Pick **one** AI coding assistant and use it for the whole workshop. Both invoke skills the same way — prefix the skill's directory name with a forward slash (`/skill-name`):

- **Claude Code** — install steps in Section 2, Option A.
- **GitHub Copilot** — install steps in Section 2, Option B.

## 2. Clone and Install

Clone the repository, switch to the workshop branch, and `cd` into it:

```bash
git clone https://github.com/awslabs/hcls-agent-skills.git
cd hcls-agent-skills
git checkout workshop/life-sciences-rd-90min
```

The coding agent is already installed and authenticated — you only install the skills. Run the command for the harness you picked **from inside the cloned repo** (the install uses **Project** scope, which targets the current directory, so your working directory must be the repo):

**Option A — Claude Code:**

```bash
npx skills add awslabs/hcls-agent-skills -a claude-code
```

**Option B — GitHub Copilot:**

```bash
npx skills add awslabs/hcls-agent-skills -a github-copilot
```

The installer is interactive. You'll walk through these prompts in order — the answers below install all 42 skills project-local:

| # | Prompt | Answer |
|---|--------|--------|
| 1 | `Need to install the following packages: skills@1.7.0` / `Ok to proceed? (y)` | `y` |
| 2 | `Select skills to install` (multi-select of all 42) | accept **all 42** |
| 3 | `Installation scope` | **Project** |
| 4 | `Security Risk Assessments` table (see note below) | review, then continue |
| 5 | `Proceed with installation?` | `Yes` |
| 6 | `Install the find-skills skill?` (one-time, optional) | **No** |

Between prompts the CLI prints its source (`https://github.com/awslabs/hcls-agent-skills.git`), `Repository cloned`, `Found 42 skills`, an **Installation Summary** (each skill marked `copy ->` followed by the agent you selected), and finally `Installed 42 skills` with each listed as `(copied)` and its destination path.

**About the security table (prompt 4):** all 42 skills show **Gen `Safe`** and **Socket `0 alerts`**. On the **Snyk** column, most are `Low Risk`; exactly three show `Med Risk` — `claims-analytics`, `digital-pathology`, and `ehr-data-parsing` — all data-parsing skills. Full per-skill detail: https://skills.sh/awslabs/hcls-agent-skills. It is safe to answer `Yes` at prompt 5.

**The installer copies, it does not symlink.** Each skill is **copied** into your agent's skills directory, so the installed copy is an independent file — separate from the repo's `skills/` directory. The destination depends on your harness:

| Harness | Project destination |
|---------|---------------------|
| Claude Code (`-a claude-code`) | `.claude/skills/<skill-name>/` |
| GitHub Copilot (`-a github-copilot`) | `.agents/skills/<skill-name>/` |

Your agent discovers skills from there — invoke one directly with `/skill-name`, or let it auto-activate when your task matches the skill's `description`. Copilot CLI is available on all Copilot plans, including Free. Skills need no config file — each `SKILL.md` requires only `name` and `description` in its frontmatter.

> 💡 **Reproducibility:** pin the CLI version so a whole room installs identically — `npx skills@1.7.0 add awslabs/hcls-agent-skills -a claude-code`. The version observed for this workshop is **1.7.0**. If you declined find-skills at prompt 6, you can add it later with `npx skills add vercel-labs/skills@find-skills`.

> ⚠️ When the installer finishes it prints: *"Review skills before use; they run with full agent permissions."* These skills are MIT-0 and reviewed, but the caution is the installer's own — appropriate to keep in mind for regulated work.

## 3. Verify Skills Load

Launch your agent **inside the repo** and confirm skills are active by asking:

```text
What ACMG criteria would you apply to a BRCA1 frameshift variant?
```

The response should cite **specific criteria codes** (e.g., PVS1, PM2) — not just a generic discussion of variants. If it does, skills are loading correctly.

Both harnesses use the same explicit-invocation form: prefix the skill's directory name with a forward slash.

**Claude Code:** in a session started **inside the repo**, invoke `/genomic-variant-interpretation` explicitly (it also auto-activates when the question matches its description). For a baseline, the same question in a session started **outside the repo** (a directory with no `.claude/skills/`) will *not* cite specific codes.

**GitHub Copilot:** in a Copilot CLI session (or VS Code agent mode) started **inside the repo**, invoke `/genomic-variant-interpretation` explicitly. Confirm the skill is loaded with `/skills list` (or `/skills info genomic-variant-interpretation` for one skill); if you installed skills mid-session, run `/skills reload` — no restart needed. Copilot also auto-discovers skills from their `description`, so for a baseline you must ask in a session where the skills are **not** installed (or a prompt that doesn't name the skill).

## 4. Optional: Bedrock Access for Take-Home Eval

**Not required during the workshop.** Only needed for the Module 3 take-home assignment.

- An **AWS account** with Amazon Bedrock model access enabled for the **`global.`** cross-region inference profile.
- Models required:
  - `global.anthropic.claude-sonnet-5` — execution
  - `global.anthropic.claude-opus-5` — judge
- **Cost estimate:** ~$1–2 for a 10-prompt single-skill eval.

## 5. Troubleshooting

- **Skills not loading** → re-run the `npx skills add ...` command for your harness and confirm it completed without errors. For **Claude Code**, make sure you're running inside the repo where `.claude/skills/` exists. For **GitHub Copilot**, run `/skills list` to confirm the skill is loaded, and `/skills reload` if you added it mid-session.
- **Agent doesn't cite specific criteria** → the skills may not be discovered or referenced. For **Claude Code**, make sure you're running inside the repo where `.claude/skills/` exists. For **GitHub Copilot**, confirm `/skills list` shows the skill and invoke it explicitly with `/genomic-variant-interpretation`.

Still stuck? Send the failing command output to the organizer **before** the session.
