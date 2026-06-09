#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -t 1 ]; then
  GREEN='\033[0;32m' YELLOW='\033[1;33m' RESET='\033[0m'
else
  GREEN='' YELLOW='' RESET=''
fi

info()    { printf "${YELLOW}%s${RESET}\n" "$*"; }
success() { printf "${GREEN}%s${RESET}\n" "$*"; }

usage() {
  cat <<EOF
Usage: $(basename "$0") --target <kiro|claude-code|quick-desktop> [OPTIONS]

Targets:
  kiro            Copy skills and agent config to ~/.kiro/ (or --path)
  claude-code     Symlink skills into .claude/skills/ in a project directory
  quick-desktop   Print manual upload instructions

Options:
  --target TARGET       Target platform (required)
  --mode MODE           Install mode: single (default) or multiagent
  --path DIR            Install to DIR/.kiro/ instead of ~/.kiro/ (kiro target only)
  --project-dir DIR     Project directory for claude-code (default: .)
  --help                Show this help

Examples:
  ./install.sh --target kiro                          # Single agent, all 38 skills
  ./install.sh --target kiro --mode multiagent        # Coordinator + 8 specialists
  ./install.sh --target kiro --path .                 # Install locally to ./.kiro/
  ./install.sh --target kiro --path . --mode multiagent
  ./install.sh --target claude-code                   # Symlink into ./.claude/skills/
EOF
  exit "${1:-0}"
}

TARGET="" PROJECT_DIR="." KIRO_PATH="" MODE="single"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)      TARGET="${2:-}"; shift 2 ;;
    --mode)        MODE="${2:-}"; shift 2 ;;
    --path)        KIRO_PATH="${2:-}"; shift 2 ;;
    --project-dir) PROJECT_DIR="${2:-}"; shift 2 ;;
    --help)        usage 0 ;;
    *)             echo "Unknown option: $1"; usage 1 ;;
  esac
done

[[ -z "$TARGET" ]] && { echo "Error: --target is required."; usage 1; }

SKILL_COUNT="$(find "$SCRIPT_DIR/skills" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"

install_kiro() {
  local dest="${KIRO_PATH:-$HOME}/.kiro"
  mkdir -p "$dest/skills" "$dest/agents"
  cp -r "$SCRIPT_DIR"/skills/* "$dest/skills/"
  cp "$SCRIPT_DIR/agents/hcls-agent.json" "$dest/agents/"
  success "Installed $SKILL_COUNT HCLS skills to $dest/skills/ and agent config to $dest/agents/hcls-agent.json"
  if [[ -z "$KIRO_PATH" ]]; then
    info "Switch to the agent with: /agent hcls"
  else
    info "Skills installed to $dest/"
  fi
}

install_kiro_multiagent() {
  local dest="${KIRO_PATH:-$HOME}/.kiro"
  mkdir -p "$dest/skills" "$dest/agents"
  cp -r "$SCRIPT_DIR"/skills/* "$dest/skills/"
  cp "$SCRIPT_DIR"/agents/multiagent/kiro/*.json "$dest/agents/"
  local agent_count
  agent_count="$(find "$SCRIPT_DIR/agents/multiagent/kiro" -name '*.json' | wc -l | tr -d ' ')"
  success "Installed $SKILL_COUNT HCLS skills and $agent_count multiagent configs to $dest/"
  info "Coordinator: hcls-multiagent (routes to 8 domain specialists)"
  if [[ -z "$KIRO_PATH" ]]; then
    info "Switch to the coordinator with: /agent hcls-multiagent"
  fi
}

install_claude_code() {
  local dest="$PROJECT_DIR/.claude/skills"
  mkdir -p "$dest"
  for skill_dir in "$SCRIPT_DIR"/skills/*/; do
    ln -sfn "$skill_dir" "$dest/$(basename "$skill_dir")"
  done
  success "Installed $SKILL_COUNT HCLS skills as symlinks in .claude/skills/"
  info "Skills will auto-activate in Claude Code when relevant topics are discussed."
}

print_domain() { printf "\n%s\n" "$1:"; shift; for s in "$@"; do echo "  skills/$s/SKILL.md"; done; }

install_quick_desktop() {
  info "Quick Desktop requires manual upload of each SKILL.md file."
  info "Recommended skills to start with (by domain):"
  print_domain "Genomics" genomic-variant-interpretation variant-calling rna-seq-analysis ngs-quality-control
  print_domain "Single-Cell Analysis" biomarker-discovery scrna-seq-pipeline cell-type-annotation trajectory-analysis
  print_domain "Medical Imaging" imaging-study-design digital-pathology dicom-processing radiology-preprocessing
  print_domain "Protein Structure" structure-based-drug-design protein-structure-analysis molecular-docking
  print_domain "Cross-Domain" translational-research ml-researcher aws-genai-ml-architect
  print_domain "Pharmacoepidemiology & Real-World Data" pharmacoepidemiology rwd-cohort-analysis
  print_domain "Clinical Data" clinical-data-standards ehr-data-parsing
  print_domain "Drug Discovery" drug-repurposing cheminformatics
  print_domain "Proteomics" quantitative-proteomics proteomics-analysis
  print_domain "Clinical Data Review" cdisc-compliance edc-data-validation
  print_domain "Multi-Omics Integration" multi-omics-integration multi-omics-pipeline
  print_domain "Healthcare Operations" claims-billing-rules claims-analytics risk-adjustment-strategy \
    risk-adjustment pa-clinical-policy pa-decision-automation hedis-measure-specification \
    risk-stratification-indices quality-measures
  echo ""
  info "To upload: Settings → Capabilities → Skills → Upload → select a SKILL.md file"
  info "Tip: Start with one domain (e.g., genomics) and add more as needed."
}

case "$TARGET" in
  kiro)
    if [[ "$MODE" == "multiagent" ]]; then
      install_kiro_multiagent
    else
      install_kiro
    fi
    ;;
  claude-code)   install_claude_code ;;
  quick-desktop) install_quick_desktop ;;
  *)             echo "Unknown target: $TARGET"; usage 1 ;;
esac
