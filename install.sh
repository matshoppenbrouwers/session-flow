#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
SCOPE="user"
SKILLS_ONLY=false
DRY_RUN=false
FORCE=false

# The self-contained support package: the runtime entrypoint, its Python package,
# and every support file an installed skill entry may name. Removing an item here
# removes it from the install; tests/test_installation.py checks that.
SUPPORT_PACKAGE=("scripts/session-flow.py" "scripts/session_flow" "references" "THIRD_PARTY_NOTICES.md")
RUNTIME_ENTRYPOINT="scripts/session-flow.py"
RUNTIME_DESCRIPTOR="session-flow-runtime.json"
PYTHON_MINIMUM="3.9"

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
    echo ""
    echo "Prerequisite: Python $PYTHON_MINIMUM or newer, reachable as python3. The installed"
    echo "runtime scripts/session-flow.py requires it, so machines without Python cannot"
    echo "run the plugin. The installer verifies the staged runtime before activating skills."
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

    if [[ ! -f "$src" ]]; then
        echo "Error: missing source file $src"
        echo "  Run install.sh from a complete session-flow checkout."
        exit 1
    fi

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

find_files() {
    local root="$1"
    local exclude="${2:-}"

    if [[ ! -d "$root" ]]; then
        echo "Error: missing source directory $root" >&2
        echo "  Run install.sh from a complete session-flow checkout." >&2
        exit 1
    fi

    find "$root" -name __pycache__ -prune -o -type f ! -name "${exclude:-.}" -print0
}

install_tree() {
    local src_root="${1%/}"
    local dest_root="${2%/}"
    local exclude="${3:-}"
    local file rel

    while IFS= read -r -d '' file; do
        rel="${file#"$src_root"/}"
        install_file "$file" "$dest_root/$rel"
    done < <(find_files "$src_root" "$exclude")
}

missing_in_tree() {
    local src_root="${1%/}"
    local dest_root="${2%/}"
    local exclude="${3:-}"
    local file rel

    while IFS= read -r -d '' file; do
        rel="${file#"$src_root"/}"
        [[ -f "$dest_root/$rel" ]] || echo "$dest_root/$rel"
    done < <(find_files "$src_root" "$exclude")
}

install_support_package() {
    local resource

    for resource in "${SUPPORT_PACKAGE[@]}"; do
        if [[ -d "$REPO_DIR/$resource" ]]; then
            install_tree "$REPO_DIR/$resource" "$TARGET/$resource"
        else
            install_file "$REPO_DIR/$resource" "$TARGET/$resource"
        fi
    done
}

missing_support_package() {
    local resource

    for resource in "${SUPPORT_PACKAGE[@]}"; do
        if [[ -d "$REPO_DIR/$resource" ]]; then
            missing_in_tree "$REPO_DIR/$resource" "$TARGET/$resource"
        else
            [[ -f "$TARGET/$resource" ]] || echo "$TARGET/$resource"
        fi
    done
}

package_version() {
    local manifest="$REPO_DIR/.claude-plugin/plugin.json"
    local version

    version="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$manifest" 2>/dev/null | head -1)"
    if [[ -z "$version" ]]; then
        echo "Error: cannot read the package version from $manifest" >&2
        echo "  Run install.sh from a complete session-flow checkout." >&2
        exit 1
    fi
    printf '%s' "$version"
}

protocol_version() {
    local entrypoint="$REPO_DIR/$RUNTIME_ENTRYPOINT"
    local protocol

    protocol="$(sed -n 's/^PROTOCOL_VERSION[[:space:]]*=[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$entrypoint" 2>/dev/null | head -1)"
    if [[ -z "$protocol" ]]; then
        echo "Error: cannot read PROTOCOL_VERSION from $entrypoint" >&2
        echo "  Run install.sh from a complete session-flow checkout." >&2
        exit 1
    fi
    printf '%s' "$protocol"
}

# Generated output, so it is rewritten on every install instead of being
# preserved like an authored file. Paths are relative to the skill directory so
# a standalone entry resolves the runtime without scanning for an installed copy.
write_runtime_descriptor() {
    local skill_dest="${1%/}"
    local dest="$skill_dest/$RUNTIME_DESCRIPTOR"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "  INSTALL: $dest"
        return
    fi

    mkdir -p "$skill_dest"
    cat > "$dest" <<DESCRIPTOR
{
  "package": "session-flow",
  "version": "$PACKAGE_VERSION",
  "protocol": $PROTOCOL,
  "python_minimum": "$PYTHON_MINIMUM",
  "entrypoint": "../../$RUNTIME_ENTRYPOINT",
  "package_root": "../..",
  "references": "../../references"
}
DESCRIPTOR
    echo "  Installed: $dest"
}

python_install_instruction() {
    echo "$1Install Python $PYTHON_MINIMUM or newer (Debian/Ubuntu: 'sudo apt install python3';"
    echo "$1macOS: 'brew install python3') and expose it as python3. Machines without Python"
    echo "$1cannot run session-flow."
}

verify_runtime() {
    local entrypoint="$TARGET/$RUNTIME_ENTRYPOINT"
    local report

    if ! command -v python3 >/dev/null 2>&1; then
        echo "  Warning: python3 is not on PATH, so the staged runtime was not verified."
        python_install_instruction "    "
        echo "    Then check with: python3 $entrypoint doctor"
        return 0
    fi

    if report="$(python3 -B "$entrypoint" doctor --project-root "$TARGET" 2>&1)"; then
        echo "  Verified: python3 $entrypoint doctor"
        return 0
    fi

    # The runtime guard answers on the protocol, so its own diagnosis is more useful
    # than a report that the package is incomplete.
    if [[ "$report" == *unsupported-runtime* ]]; then
        echo "Error: python3 is older than $PYTHON_MINIMUM, so the staged runtime refused to run."
        python_install_instruction "  "
        echo "  Entry files were not activated. Install a newer Python and re-run install.sh."
        exit 1
    fi

    echo "Error: the staged support package did not answer 'doctor'."
    echo "  Entry files were not activated. Re-run install.sh from a complete session-flow checkout."
    exit 1
}

require_present() {
    local what="$1"
    local missing="$2"

    [[ -z "$missing" ]] && return 0

    echo "Error: $what is incomplete after copying:"
    echo "$missing" | sed 's/^/    /'
    echo "  Entry files were not activated. Re-run install.sh with write access to $TARGET."
    exit 1
}

PACKAGE_VERSION="$(package_version)"
PROTOCOL="$(protocol_version)"

echo "session-flow installer"
echo "  Source:   $REPO_DIR"
echo "  Target:   $TARGET"
echo "  Scope:    $SCOPE"
echo "  Package:  $PACKAGE_VERSION (protocol $PROTOCOL)"
echo "  Requires: Python $PYTHON_MINIMUM or newer as python3"
echo ""

echo "Support package:"
install_support_package
if [[ "$DRY_RUN" != "true" ]]; then
    require_present "support package" "$(missing_support_package)"
    verify_runtime
fi

echo ""
echo "Skills:"
for skill_dir in "$REPO_DIR"/skills/*/; do
    skill_name="$(basename "$skill_dir")"
    skill_dest="$TARGET/skills/$skill_name"

    install_tree "$skill_dir" "$skill_dest" SKILL.md
    if [[ "$DRY_RUN" != "true" ]]; then
        require_present "$skill_name resources" "$(missing_in_tree "$skill_dir" "$skill_dest" SKILL.md)"
    fi
    write_runtime_descriptor "$skill_dest"
    install_file "$skill_dir/SKILL.md" "$skill_dest/SKILL.md"
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
    echo "  Runtime: python3 $TARGET/$RUNTIME_ENTRYPOINT doctor"
fi
