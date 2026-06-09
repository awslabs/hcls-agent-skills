# Agent Configs

## Recommended: `hcls-agent.json`

The unified HCLS agent loads all 38 domain skills. This is the simplest way to get full coverage — Kiro will activate the relevant skill(s) based on your prompt.

```bash
# Install with the script
./install.sh --target kiro

# Or manually
cp agents/hcls-agent.json ~/.kiro/agents/
cp -r skills/* ~/.kiro/skills/

# Then in Kiro CLI
/agent hcls
```

## Domain-Specific Bundles

If you only work in one domain and want a lighter config:

| Bundle | File | Skills |
|--------|------|--------|
| Genomics | `genomics.json` | genomic-variant-interpretation, variant-calling, rna-seq-analysis, ngs-quality-control |
| ML Researcher | `ml-researcher.json` | ml-researcher, aws-genai-ml-architect (+ arxiv MCP server) |
| Translational Research | `translational-research.json` | translational-research |

These load fewer skills and activate faster, but you lose cross-domain coverage.

## Creating Your Own Bundle

Agent configs are JSON files that reference skills:

```json
{
  "name": "my-bundle",
  "description": "Custom HCLS workflow",
  "tools": ["*"],
  "allowedTools": ["fs_read", "execute_bash"],
  "resources": [
    "skill://variant-calling",
    "skill://biomarker-discovery"
  ]
}
```

Mix any skills from `skills/` to create a bundle for your workflow.
