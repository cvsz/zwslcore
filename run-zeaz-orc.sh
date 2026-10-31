#!/usr/bin/env bash

set -uo pipefail
umask 077

ROOT="$HOME/zwslcore"
STATE_DIR="$HOME/.local/state/zeaz-orc"
LOCK_FILE="$STATE_DIR/runner.lock"

SESSION_ID="ses_e71da4e81ffe9qxZJEWKgKxhxk"
LOG="$HOME/zwslcore-orc-resume-$(date +%Y%m%d-%H%M%S).log"

LOCK_HELD=0

# FD 9 is the sole lock handle. Child processes must not inherit it.
# Never unlink runner.lock while any runner may be active.
release_lock() {
    if [[ "${LOCK_HELD:-0}" == "1" ]]; then
        flock -u 9 2>/dev/null || true
        exec 9>&-
        LOCK_HELD=0
    fi
}

echo "===== ZEAZ ORC ====="
echo "Working directory: $ROOT"
echo "Log: $LOG"
echo

cd "$ROOT" || exit 1

for command in opencode flock tee; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "ERROR: Required command not found: $command"
        exit 127
    fi
done

if [[ -L "$STATE_DIR" ]]; then
    echo "ERROR: State directory must not be a symbolic link: $STATE_DIR" >&2
    exit 1
fi

mkdir -p "$STATE_DIR" || {
    echo "ERROR: Cannot create state directory: $STATE_DIR" >&2
    exit 1
}
chmod 700 "$STATE_DIR" || {
    echo "ERROR: Cannot secure state directory: $STATE_DIR" >&2
    exit 1
}

if [[ -L "$STATE_DIR" || ! -d "$STATE_DIR" ]]; then
    echo "ERROR: Invalid state directory: $STATE_DIR" >&2
    exit 1
fi

if [[ -L "$LOCK_FILE" || ( -e "$LOCK_FILE" && ! -f "$LOCK_FILE" ) ]]; then
    echo "ERROR: Lock path must be a regular, non-symlink file: $LOCK_FILE" >&2
    exit 1
fi

( umask 077; : >> "$LOCK_FILE" ) || {
    echo "ERROR: Cannot create or open lock file: $LOCK_FILE" >&2
    exit 1
}
chmod 600 "$LOCK_FILE" || {
    echo "ERROR: Cannot secure lock file: $LOCK_FILE" >&2
    exit 1
}

# Append mode keeps the shared lock inode stable and avoids truncation.
exec 9>>"$LOCK_FILE"

if ! flock -n 9; then
    echo "ERROR: Another ZEAZ ORC runner holds the shared lock."
    exec 9>&-
    exit 1
fi

LOCK_HELD=1

trap 'release_lock' EXIT
trap 'release_lock; exit 130' INT
trap 'release_lock; exit 143' TERM

if ! opencode session list --max-count 20 9>&- |
     grep -Fq -- "$SESSION_ID" 9>&-; then
    echo "ERROR: Previous session ID not found."
    echo "Aborting to avoid creating an unintended session."
    exit 1
fi

echo "===== STARTING ORC ====="

opencode run \
    --auto \
    --session "$SESSION_ID" \
    "Resume ZEAZDEV Claude Gateway Bootstrap. Inspect the previous session context and current repository state first. Preserve all existing work. Do not repeat completed tasks. Continue the original ZEAZ Gateway objectives, including LOCAL_ONLY enforcement, Provider configuration, isolated virtual environment, tests, and Claude Code/OpenCode compatibility. Verify all changes with actual test evidence. Do not deploy, rotate credentials, modify public ingress, commit, push, approve, or merge without the required explicit authorization. Continue authorized work without unnecessary pauses. Produce a final evidence-based report." \
    9>&- 2>&1 | tee "$LOG" 9>&-

PIPELINE_STATUS=("${PIPESTATUS[@]}")
RC="${PIPELINE_STATUS[0]:-1}"
TEE_RC="${PIPELINE_STATUS[1]:-1}"
if [[ "$RC" -eq 0 && "$TEE_RC" -ne 0 ]]; then
    RC="$TEE_RC"
fi

echo
echo "===== OPENCODE FINISHED ====="
echo "Exit code: $RC"
echo "Log: $LOG"

release_lock
trap - EXIT INT TERM

echo
echo "Lock released. Shell remains open for diagnostics."
exec bash -i
