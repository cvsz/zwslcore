#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd
)"

REPO_ROOT="$(
    cd -- "${SCRIPT_DIR}/.." &&
    pwd
)"

PROVIDER_DIR="${REPO_ROOT}/services/provider"
VENV_PYTHON="${PROVIDER_DIR}/.venv/bin/python3"

log() {
    printf '\n[%s] %s\n' \
        "$(date -Is)" "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

# --------------------------------------------------
# Preflight
# --------------------------------------------------

[[ -d "$PROVIDER_DIR" ]] ||
    fail "Provider directory not found: ${PROVIDER_DIR}"

[[ -d "${PROVIDER_DIR}/tests" ]] ||
    fail "Provider tests directory not found"

if [[ -x "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    fail "Python 3 not found"
fi

log "Repository: ${REPO_ROOT}"
log "Provider: ${PROVIDER_DIR}"
log "Python: ${PYTHON}"

# --------------------------------------------------
# Python environment
# --------------------------------------------------

"$PYTHON" --version ||
    fail "Python runtime check failed"

"$PYTHON" -m unittest --help >/dev/null ||
    fail "Python unittest module unavailable"

# --------------------------------------------------
# Provider tests
# --------------------------------------------------

log "Running Provider unittest discovery"

(
    cd "$PROVIDER_DIR"

    export PYTHONPATH="${PROVIDER_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

    "$PYTHON" -m unittest discover \
        -s tests \
        -v
) || fail "Provider unittest failed"

# --------------------------------------------------
# Import smoke test
# --------------------------------------------------

log "Running Provider import smoke test"

(
    export PYTHONPATH="${PROVIDER_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

    "$PYTHON" -c '
import zeaz_provider
from zeaz_provider.main import app

print("Package:", zeaz_provider.__file__)
print("Application:", app.title)
'
) || fail "Provider import smoke test failed"

log "Provider tests and import smoke test PASSED"
