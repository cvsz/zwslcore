#!/usr/bin/env bash
#
# ZEAZ ORC Persistent Runner
# OpenCode + tmux + Session Recovery + Logging
#
# Repository: ~/zwslcore
# Default Session: ZEAZDEV Claude Gateway Bootstrap
#

set -uo pipefail
umask 077

ROOT="$HOME/zwslcore"
SCRIPT="$ROOT/zeaz-orc.sh"

TMUX_SESSION="zeaz-orc"

SESSION_ID="ses_e71da4e81ffe9qxZJEWKgKxhxk"

LOG_DIR="$HOME/zeaz-orc-logs"
STATE_DIR="$HOME/.local/state/zeaz-orc"

LOCK_FILE="$STATE_DIR/runner.lock"
STATUS_FILE="$STATE_DIR/status"

RESUME_PROMPT="Resume ZEAZDEV Claude Gateway Bootstrap.

First inspect the previous session context and current repository state.

Preserve all existing work and uncommitted changes.
Do not repeat completed tasks.

Continue the original ZEAZ Gateway engineering objectives:

1. Implement and verify LOCAL_ONLY cost policy.
2. Implement route-level cost policy.
3. Enforce local-only routing at runtime.
4. Configure zeaz-claude route with Ollama Qwen.
5. Complete isolated Provider virtual environment setup.
6. Run unit, integration and regression tests.
7. Verify Anthropic Messages API compatibility.
8. Verify OpenCode and Claude Code CLI compatibility.
9. Review security, secrets, network isolation and failure modes.
10. Update technical documentation and operational instructions.

Security and governance restrictions:

- Never expose secrets or credentials.
- Never print complete environment variables.
- Never bypass tests, security checks or approval gates.
- Never deploy or restart production services without explicit approval.
- Never rotate credentials without explicit approval.
- Never modify public ingress or Cloudflare configuration without approval.
- Never commit, push, approve, merge or bypass branch protection without authorization.
- Preserve all existing user changes.
- Do not claim tests or deployments succeeded without evidence.

Continue all authorized work without unnecessary pauses.

Produce a final evidence-based report containing:
- Completed
- Verified
- Partial
- Blocked
- Files changed
- Tests executed and results
- Security findings
- Remaining risks
- Next actions."

# --------------------------------------------------
# Utilities
# --------------------------------------------------

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: Required command not found: $1"
        return 1
    }
}

init_directories() {
    if [[ -L "$STATE_DIR" ]]; then
        echo "ERROR: State directory must not be a symbolic link: $STATE_DIR" >&2
        return 1
    fi

    mkdir -p "$LOG_DIR" "$STATE_DIR" || {
        echo "ERROR: Cannot create ZEAZ ORC directories." >&2
        return 1
    }

    chmod 700 "$LOG_DIR" "$STATE_DIR" || {
        echo "ERROR: Cannot secure ZEAZ ORC directories." >&2
        return 1
    }

    if [[ -L "$STATE_DIR" || ! -d "$STATE_DIR" ]]; then
        echo "ERROR: Invalid state directory: $STATE_DIR" >&2
        return 1
    fi
}

is_tmux_running() {
    tmux has-session -t "$TMUX_SESSION" 2>/dev/null
}

is_opencode_running() {
    pgrep -af '[o]pencode run' >/dev/null 2>&1
}

LOCK_HELD=0

# FD 9 is the sole lock handle. Every long-lived child/pipeline must close it.
# Never unlink runner.lock while any runner may be active.
release_lock() {
    if [[ "${LOCK_HELD:-0}" == "1" ]]; then
        flock -u 9 2>/dev/null || true
        exec 9>&-
        LOCK_HELD=0
    fi
}

hold_shell() {
    release_lock
    echo
    echo "======================================"
    echo "ZEAZ ORC runner stopped."
    echo "The tmux pane will remain available."
    echo "======================================"
    exec bash -i
}

# --------------------------------------------------
# Worker
# --------------------------------------------------

worker() {
    local mode="${1:-resume}"
    local rc=0
    local tee_rc=0
    local -a pipeline_status=()
    local log_file

    case "$mode" in
        resume|master) ;;
        *)
            echo "ERROR: Unknown worker mode: $mode"
            hold_shell
            return
            ;;
    esac

    cd "$ROOT" || {
        echo "ERROR: Repository unavailable: $ROOT"
        hold_shell
    }

    init_directories

    require_command opencode || hold_shell
    require_command flock || hold_shell
    require_command tee || hold_shell

    # Keep the lock inode stable: never truncate or remove this file.
    if [[ -L "$LOCK_FILE" || ( -e "$LOCK_FILE" && ! -f "$LOCK_FILE" ) ]]; then
        echo "ERROR: Lock path must be a regular, non-symlink file: $LOCK_FILE" >&2
        hold_shell
        return
    fi

    ( umask 077; : >> "$LOCK_FILE" ) || {
        echo "ERROR: Cannot create or open lock file: $LOCK_FILE" >&2
        hold_shell
        return
    }

    chmod 600 "$LOCK_FILE" || {
        echo "ERROR: Cannot secure lock file: $LOCK_FILE" >&2
        hold_shell
        return
    }

    # Prevent duplicate ORC workers. Append mode avoids truncating shared state.
    exec 9>>"$LOCK_FILE"

    if ! flock -n 9; then
        echo "ERROR: Another ZEAZ ORC runner holds the shared lock."
        exec 9>&-
        hold_shell
        return
    fi

    LOCK_HELD=1

    trap 'release_lock' EXIT
    trap 'release_lock; exit 130' INT
    trap 'release_lock; exit 143' TERM

    log_file="$LOG_DIR/zeaz-orc-$(date '+%Y%m%d-%H%M%S' 9>&-).log"

    {
        echo "======================================"
        echo "ZEAZ ORC EXECUTION"
        echo "======================================"
        echo "Date: $(date --iso-8601=seconds 9>&-)"
        echo "Repository: $ROOT"
        echo "Mode: $mode"
        echo "Session: $SESSION_ID"
        echo "OpenCode: $(opencode --version 9>&- 2>&1)"
        echo "Log: $log_file"
        echo "======================================"
    } 9>&- | tee "$log_file" 9>&-

    echo "RUNNING" > "$STATUS_FILE"

    if [[ "$mode" == "resume" ]]; then

        log "Checking previous OpenCode session..." 9>&- |
            tee -a "$log_file" 9>&-

        if ! opencode session list --max-count 30 9>&- 2>&1 |
             tee -a "$log_file" 9>&- |
             grep -Fq -- "$SESSION_ID" 9>&-; then

            echo "ERROR: Previous session not found."
            echo "Aborting to prevent accidental session creation."
            echo "BLOCKED" > "$STATUS_FILE"
            hold_shell
        fi

        log "Resuming existing session..." 9>&- |
            tee -a "$log_file" 9>&-

        opencode run \
            --auto \
            --session "$SESSION_ID" \
            "$RESUME_PROMPT" \
            9>&- 2>&1 | tee -a "$log_file" 9>&-

        pipeline_status=("${PIPESTATUS[@]}")
        rc="${pipeline_status[0]:-1}"
        tee_rc="${pipeline_status[1]:-1}"
        if [[ "$rc" -eq 0 && "$tee_rc" -ne 0 ]]; then
            rc="$tee_rc"
        fi

    elif [[ "$mode" == "master" ]]; then

        if [[ ! -s "$ROOT/ORC_MASTER_PROMPT.md" ]]; then
            echo "ERROR: ORC_MASTER_PROMPT.md missing or empty."
            echo "BLOCKED" > "$STATUS_FILE"
            hold_shell
        fi

        log "Starting from master prompt..." 9>&- |
            tee -a "$log_file" 9>&-

        opencode run \
            --auto \
            --title "ZEAZ ORC - Autonomous Gateway Engineering" \
            "$(cat "$ROOT/ORC_MASTER_PROMPT.md" 9>&-)" \
            9>&- 2>&1 | tee -a "$log_file" 9>&-

        pipeline_status=("${PIPESTATUS[@]}")
        rc="${pipeline_status[0]:-1}"
        tee_rc="${pipeline_status[1]:-1}"
        if [[ "$rc" -eq 0 && "$tee_rc" -ne 0 ]]; then
            rc="$tee_rc"
        fi

    else
        echo "ERROR: Unknown worker mode: $mode"
        hold_shell
    fi

    if [[ "$rc" -eq 0 ]]; then
        echo "COMPLETED" > "$STATUS_FILE"
    else
        echo "FAILED: $rc" > "$STATUS_FILE"
    fi

    {
        echo
        echo "======================================"
        echo "ZEAZ ORC FINISHED"
        echo "Exit code: $rc"
        echo "Finished: $(date --iso-8601=seconds 9>&-)"
        echo "Log: $log_file"
        echo "======================================"
    } 9>&- | tee -a "$log_file" 9>&-

    # Release lock before keeping the interactive shell alive.
    release_lock
    trap - EXIT INT TERM

    hold_shell
}

# --------------------------------------------------
# Start tmux worker
# --------------------------------------------------

start_worker() {
    local mode="${1:-resume}"
    local tmux_command

    cd "$ROOT" || exit 1

    require_command tmux || return 1
    require_command opencode || return 1

    if is_opencode_running; then
        echo "ERROR: An OpenCode run process already exists."
        echo "Inspect it before starting another worker."
        pgrep -af '[o]pencode run'
        return 1
    fi

    if is_tmux_running; then
        echo "Existing tmux session: $TMUX_SESSION"
        echo
        echo "Attach:"
        echo "  $SCRIPT attach"
        echo
        echo "To run worker inside the existing pane:"
        echo "  bash '$SCRIPT' worker $mode"
        return 0
    fi

    printf -v tmux_command 'bash %q worker %q' "$SCRIPT" "$mode"

    log "Creating tmux session: $TMUX_SESSION"

    tmux new-session \
        -d \
        -s "$TMUX_SESSION" \
        "$tmux_command" || return 1

    sleep 2

    if is_tmux_running; then
        echo "ZEAZ ORC tmux session created."
        echo "Attach with: $SCRIPT attach"
    else
        echo "ERROR: tmux session exited during startup."
        return 1
    fi
}

# --------------------------------------------------
# Status
# --------------------------------------------------

status() {
    echo "======================================"
    echo "ZEAZ ORC STATUS"
    echo "======================================"

    echo
    echo "Repository:"
    git -C "$ROOT" status --short --branch 2>&1

    echo
    echo "tmux:"

    if is_tmux_running; then
        tmux list-panes \
            -t "$TMUX_SESSION" \
            -a \
            -F 'Pane=#{pane_index} Command=#{pane_current_command} PID=#{pane_pid} Dead=#{pane_dead} Exit=#{pane_dead_status}'
    else
        echo "No tmux session."
    fi

    echo
    echo "OpenCode run processes:"
    pgrep -af '[o]pencode run' || true

    echo
    echo "Background OpenCode service:"
    pgrep -af '[o]pencode serve' || true

    echo
    echo "Last status:"
    if [[ -f "$STATUS_FILE" ]]; then
        cat "$STATUS_FILE"
    else
        echo "No status recorded."
    fi

    echo
    echo "Recent logs:"
    find "$LOG_DIR" \
        -maxdepth 1 \
        -type f \
        -name '*.log' \
        -printf '%T@ %p\n' 2>/dev/null |
        sort -nr |
        head -10 |
        cut -d' ' -f2-

    echo "======================================"
}

# --------------------------------------------------
# Logs
# --------------------------------------------------

show_logs() {
    local latest

    latest=$(find "$LOG_DIR" \
        -maxdepth 1 \
        -type f \
        -name '*.log' \
        -printf '%T@ %p\n' 2>/dev/null |
        sort -nr |
        head -1 |
        cut -d' ' -f2-)

    if [[ -z "$latest" ]]; then
        echo "No ZEAZ ORC logs found."
        return 1
    fi

    echo "Log: $latest"
    tail -n 100 -f "$latest"
}

# --------------------------------------------------
# Attach
# --------------------------------------------------

attach_worker() {
    if ! is_tmux_running; then
        echo "ERROR: No tmux session: $TMUX_SESSION"
        return 1
    fi

    tmux attach-session -t "$TMUX_SESSION"
}

# --------------------------------------------------
# Explicit stale-session replacement
# --------------------------------------------------

replace_stale() {
    if is_opencode_running; then
        echo "ERROR: OpenCode run process still exists."
        pgrep -af '[o]pencode run'
        echo "Refusing to terminate the existing tmux session."
        return 1
    fi

    if is_tmux_running; then
        echo "Removing stale tmux session: $TMUX_SESSION"
        tmux kill-session -t "$TMUX_SESSION" || return 1
    fi

    start_worker resume
}

# --------------------------------------------------
# Main
# --------------------------------------------------

main() {
    local action="${1:-help}"

    init_directories

    case "$action" in

        worker)
            worker "${2:-resume}"
            ;;

        start)
            start_worker resume
            ;;

        start-new)
            start_worker master
            ;;

        resume)
            worker resume
            ;;

        master)
            worker master
            ;;

        attach)
            attach_worker
            ;;

        status)
            status
            ;;

        logs)
            show_logs
            ;;

        replace-stale)
            replace_stale
            ;;

        help|--help|-h)
            cat <<'HELP'

ZEAZ ORC Persistent Runner

Commands:

  start
      Start existing OpenCode session inside tmux.

  start-new
      Start using ORC_MASTER_PROMPT.md in a new OpenCode session.

  resume
      Resume existing session in current terminal.

  master
      Run master prompt in current terminal.

  attach
      Attach to existing tmux session.

  status
      Inspect process, tmux, repository and logs.

  logs
      Follow the latest execution log.

  replace-stale
      Replace tmux session only when no OpenCode run process exists.

  worker resume
      Internal: run session recovery worker.

  worker master
      Internal: run master prompt worker.

Examples:

  ~/zwslcore/zeaz-orc.sh status
  ~/zwslcore/zeaz-orc.sh start
  ~/zwslcore/zeaz-orc.sh attach
  ~/zwslcore/zeaz-orc.sh logs

HELP
            ;;

        *)
            echo "Unknown command: $action"
            echo "Run: $SCRIPT help"
            return 1
            ;;
    esac
}

main "$@"
