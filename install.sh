#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SCOPE="user"
SKILLS_ONLY=false
DRY_RUN=false
FORCE=false

usage() {
    echo "Usage: install.sh [OPTIONS]"
    echo ""
    echo "Install session-flow skills, agents, and commands."
    echo ""
    echo "Options:"
    echo "  --scope user|project  Install to ~/.claude/ (default) or .claude/ in current dir"
    echo "  --skills-only         Skip agents and commands"
    echo "  --dry-run             Preview what would be installed"
    echo "  --force               Overwrite existing files"
    echo "  -h, --help            Show this help"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --scope) SCOPE="$2"; shift 2 ;;
        --skills-only) SKILLS_ONLY=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ "$SCOPE" == "user" ]]; then
    TARGET="$HOME/.claude"
elif [[ "$SCOPE" == "project" ]]; then
    TARGET=".claude"
else
    echo "Error: --scope must be 'user' or 'project'"
    exit 1
fi

if [[ ! -d "$TARGET" ]]; then
    echo "Error: $TARGET does not exist. Is Claude Code installed?"
    echo "  For user scope: Claude Code creates ~/.claude/ on first run."
    echo "  For project scope: Run 'mkdir -p .claude' first."
    exit 1
fi

install_file() {
    local src="$1"
    local dest="$2"
    local skip_if_exists="${3:-false}"

    if [[ "$DRY_RUN" == "true" ]]; then
        if [[ -f "$dest" && "$FORCE" != "true" ]]; then
            if [[ "$skip_if_exists" == "true" ]]; then
                echo "  SKIP (exists): $dest"
            else
                echo "  SKIP (exists, use --force): $dest"
            fi
        else
            echo "  INSTALL: $dest"
        fi
        return
    fi

    if [[ -f "$dest" && "$FORCE" != "true" ]]; then
        if [[ "$skip_if_exists" == "true" ]]; then
            echo "  Skipped (exists): $dest"
        else
            echo "  Skipped (exists, use --force to overwrite): $dest"
        fi
        return
    fi

    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    echo "  Installed: $dest"
}

echo "session-flow installer"
echo "  Source: $REPO_DIR"
echo "  Target: $TARGET"
echo "  Scope:  $SCOPE"
echo ""

echo "Skills:"
for skill_dir in "$REPO_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    install_file "$skill_dir/SKILL.md" "$TARGET/skills/$skill_name/SKILL.md"
done

if [[ "$SKILLS_ONLY" != "true" ]]; then
    echo ""
    echo "Agents:"
    for agent_file in "$REPO_DIR"/agents/*.md; do
        agent_name="$(basename "$agent_file")"
        install_file "$agent_file" "$TARGET/agents/$agent_name" true
    done

    echo ""
    echo "Commands:"
    for cmd_file in "$REPO_DIR"/commands/*.md; do
        cmd_name="$(basename "$cmd_file")"
        install_file "$cmd_file" "$TARGET/commands/$cmd_name"
    done
fi

echo ""
if [[ "$DRY_RUN" == "true" ]]; then
    echo "Dry run complete. No files were modified."
else
    echo "Done. Run /session-init in Claude Code to set up your project."
fi
