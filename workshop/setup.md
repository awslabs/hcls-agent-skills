# Pre-Workshop Setup — HCLS Agent Skills (90 min)

> ⚠️ **Complete ALL steps before the workshop. There is no setup time during the session.**

This guide is self-contained. Work through it top to bottom, then confirm readiness with the checklist in Section 5. Budget 20–30 minutes.

## 1. Prerequisites

- A laptop (macOS, Linux, or Windows) with:
  - **git** — verify with `git --version`
  - **Python 3.12+** — verify with `python --version` (or `python3 --version`)
  - **uv** — install from https://docs.astral.sh/uv/ (verify with `uv --version`)
- An **AI coding assistant that supports skills**: Kiro (recommended), Claude Code, Amazon Quick, or any of the 20+ supported platforms.
- A stable **internet connection** to clone the repo and install dependencies.

## 2. Clone and Install

Clone the repository:

```bash
git clone https://github.com/awslabs/hcls-agent-skills.git
cd hcls-agent-skills
```

Then install the skills for **your** platform.

**Kiro (recommended):**

```bash
./install.sh --target kiro
```

In Kiro CLI, switch to the unified agent with `/agent hcls`.

**Claude Code:**

```bash
npx skills add awslabs/hcls-agent-skills -a claude-code
```

**Any other platform (GitHub Copilot, Cursor, Codex, Gemini CLI, and more):**

```bash
npx skills add .
```

**Amazon Quick:** upload individual `SKILL.md` files via **Settings → Capabilities → Skills → Upload**. Run `./install.sh --target quick-desktop` for the full list and instructions.

## 3. Install the Validator

Create a virtual environment, install dev dependencies, and run the validator.

**macOS / Linux:**

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
python tests/validate_skill.py
```

**Windows (PowerShell)** — same commands, but activate the venv differently:

```powershell
uv venv --python 3.12
.venv\Scripts\Activate.ps1
uv pip install -e ".[dev]"
python tests/validate_skill.py
```

**Expected result:** all skills pass validation.

## 4. Verify Skills Load

Launch your agent and confirm skills are active.

**Kiro CLI:** run `/agent hcls`, then ask:

```text
What ACMG criteria would you apply to a BRCA1 frameshift variant?
```

The response should cite **specific criteria codes** (e.g., PVS1, PM2) — not just a generic discussion of variants. If it does, skills are loading correctly.

**Kiro IDE:** confirm the skills appear in the skills panel.

**Other platforms:** ask the same question above and verify the answer references specific ACMG codes.

## 5. Verification Checklist

Screenshot this checklist once every box is ticked and send it to the workshop organizer to confirm readiness:

- [ ] Repository cloned
- [ ] Skills installed for my platform
- [ ] `python tests/validate_skill.py` passes
- [ ] Agent loads skills and responds with domain-specific content (cites PVS1/PM2)

## 6. Optional: Bedrock Access for Take-Home Eval

**Not required during the workshop.** Only needed for the Module 3 take-home assignment.

- An **AWS account** with Amazon Bedrock model access enabled in **us-east-1**.
- Models required:
  - `us.anthropic.claude-sonnet-4-6` — execution
  - `us.anthropic.claude-opus-4-7` — judge
- **Cost estimate:** ~$1–2 for a 10-prompt single-skill eval.

## 7. Troubleshooting

- **Skills not loading** → check the install path and re-run `./install.sh --target kiro` (or the install command for your platform).
- **`validate_skill.py` fails** → ensure you are on Python 3.12+ and that `uv pip install -e ".[dev]"` completed without errors. Confirm your venv is activated.
- **Agent doesn't cite specific criteria** → the skills may not be on the context path. Load one directly:

  ```text
  /context add skills/genomic-variant-interpretation/SKILL.md
  ```

Still stuck? Send your checklist screenshot plus the failing command output to the organizer **before** the session.
