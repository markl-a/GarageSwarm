#!/bin/bash
# Multi-Agent Worker - Entrypoint Script
# Handles tool validation, authentication checks, and worker startup

set -e

echo "=========================================="
echo "  Multi-Agent Worker - Starting Up"
echo "=========================================="

# ===== Environment Defaults =====
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export ENABLED_TOOLS="${ENABLED_TOOLS:-claude_code}"
export DEFAULT_TOOL="${DEFAULT_TOOL:-claude_code}"

# ===== Helper Functions =====

log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1"
}

check_tool_installed() {
    local tool=$1
    case $tool in
        claude_code)
            if command -v claude &> /dev/null; then
                log_info "Claude Code CLI is installed: $(claude --version 2>/dev/null || echo 'version unknown')"
                return 0
            else
                log_warn "Claude Code CLI is not installed"
                return 1
            fi
            ;;
        gemini_cli)
            if python -c "import google.generativeai" &> /dev/null; then
                log_info "Gemini (google-generativeai) is installed"
                return 0
            else
                log_warn "Gemini CLI is not installed"
                return 1
            fi
            ;;
        aider)
            if command -v aider &> /dev/null; then
                log_info "Aider is installed: $(aider --version 2>/dev/null || echo 'version unknown')"
                return 0
            else
                log_warn "Aider is not installed"
                return 1
            fi
            ;;
        openhands)
            if python -c "import openhands" &> /dev/null; then
                log_info "OpenHands is installed"
                return 0
            else
                log_warn "OpenHands is not installed"
                return 1
            fi
            ;;
        *)
            log_warn "Unknown tool: $tool"
            return 1
            ;;
    esac
}

check_tool_auth() {
    local tool=$1
    case $tool in
        claude_code)
            # Check for Claude config or API key
            # Claude CLI uses .credentials.json for OAuth, config.json for settings
            if [ -f "/root/.claude/.credentials.json" ] || [ -f "/root/.claude/config.json" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
                log_info "Claude Code authentication found"
                return 0
            else
                log_warn "Claude Code: No authentication found (set ANTHROPIC_API_KEY or mount ~/.claude)"
                return 1
            fi
            ;;
        gemini_cli)
            if [ -n "$GOOGLE_API_KEY" ]; then
                log_info "Gemini API key found"
                return 0
            else
                log_warn "Gemini: No API key found (set GOOGLE_API_KEY)"
                return 1
            fi
            ;;
        aider)
            # Aider can use multiple API keys
            if [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ] || [ -f "/root/.aider/.env" ]; then
                log_info "Aider authentication found"
                return 0
            else
                log_warn "Aider: No authentication found (set OPENAI_API_KEY/ANTHROPIC_API_KEY or mount ~/.aider)"
                return 1
            fi
            ;;
        openhands)
            if [ -n "$OPENAI_API_KEY" ] || [ -n "$ANTHROPIC_API_KEY" ]; then
                log_info "OpenHands authentication found"
                return 0
            else
                log_warn "OpenHands: No API key found"
                return 1
            fi
            ;;
        *)
            return 1
            ;;
    esac
}

# ===== Validate Enabled Tools =====

log_info "Checking enabled tools: $ENABLED_TOOLS"

IFS=',' read -ra TOOLS <<< "$ENABLED_TOOLS"
VALID_TOOLS=""

for tool in "${TOOLS[@]}"; do
    tool=$(echo "$tool" | xargs)  # Trim whitespace

    if check_tool_installed "$tool"; then
        if check_tool_auth "$tool"; then
            if [ -z "$VALID_TOOLS" ]; then
                VALID_TOOLS="$tool"
            else
                VALID_TOOLS="$VALID_TOOLS,$tool"
            fi
            log_info "Tool '$tool' is ready"
        else
            log_warn "Tool '$tool' is installed but authentication is missing"
        fi
    fi
done

if [ -z "$VALID_TOOLS" ]; then
    log_error "No valid tools available! At least one tool must be installed and authenticated."
    log_error "Please check your configuration and try again."
    exit 1
fi

export ENABLED_TOOLS="$VALID_TOOLS"
log_info "Valid tools for this session: $ENABLED_TOOLS"

# ===== Validate Default Tool =====

if ! echo "$VALID_TOOLS" | grep -q "$DEFAULT_TOOL"; then
    # Default tool not in valid tools, use first valid tool
    FIRST_TOOL=$(echo "$VALID_TOOLS" | cut -d',' -f1)
    log_warn "Default tool '$DEFAULT_TOOL' is not available, using '$FIRST_TOOL' instead"
    export DEFAULT_TOOL="$FIRST_TOOL"
fi

# ===== Check Backend Connection =====

log_info "Backend URL: ${BACKEND_URL:-http://host.docker.internal:8002}"

if [ -n "$BACKEND_URL" ]; then
    log_info "Waiting for backend to be available..."

    MAX_RETRIES=30
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -s -f "${BACKEND_URL}/api/v1/health" > /dev/null 2>&1; then
            log_info "Backend is available"
            break
        fi

        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            log_info "Backend not ready, retrying in 2 seconds... ($RETRY_COUNT/$MAX_RETRIES)"
            sleep 2
        fi
    done

    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        log_warn "Could not connect to backend after $MAX_RETRIES attempts"
        log_warn "Worker will continue but may fail to register"
    fi
fi

# ===== Display Configuration =====

echo ""
echo "=========================================="
echo "  Configuration Summary"
echo "=========================================="
echo "  Backend URL:    ${BACKEND_URL:-http://host.docker.internal:8002}"
echo "  Machine Name:   ${MACHINE_NAME:-docker-worker}"
echo "  Enabled Tools:  $ENABLED_TOOLS"
echo "  Default Tool:   $DEFAULT_TOOL"
echo "  Log Level:      $LOG_LEVEL"
echo "  Workspace:      /workspace"
echo "=========================================="
echo ""

# ===== Start Worker =====

log_info "Starting Multi-Agent Worker..."

# Execute the main command
exec "$@"
