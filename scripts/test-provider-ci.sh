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

PYTHON_IMAGE="python:3.15-slim-bookworm@sha256:4e03260adeeebafccd084f3584e6b84823aba5651cfb53ef8a078ed441ddf9cd"

log() {
    printf '\n[%s] %s\n' "$(date -Is)" "$*"
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

[[ -f "${PROVIDER_DIR}/requirements.lock" ]] ||
    fail "Provider requirements.lock not found"

[[ -f "${PROVIDER_DIR}/pyproject.toml" ]] ||
    fail "Provider pyproject.toml not found"

[[ -f "${REPO_ROOT}/scripts/provider-lock.sh" ]] ||
    fail "Provider lock validation script not found"

command -v docker >/dev/null 2>&1 ||
    fail "Docker CLI not found"

log "Checking Docker daemon"

docker info >/dev/null ||
    fail "Docker daemon is unavailable"

log "Repository: ${REPO_ROOT}"
log "Provider: ${PROVIDER_DIR}"
log "Python image: ${PYTHON_IMAGE}"

# --------------------------------------------------
# Step 1: Verify dependency lock
# Matches CI pip-tools lock check
# --------------------------------------------------

log "Step 1/2: Verify Provider dependency lock"

docker run --rm \
    --volume "${REPO_ROOT}:/workspace" \
    --workdir /workspace \
    "${PYTHON_IMAGE}" \
    sh -lc '
        set -eu
        python -m pip install \
            --disable-pip-version-check \
            "pip-tools==7.6.1"
        bash scripts/provider-lock.sh check
    ' ||
    fail "Provider dependency lock verification failed"

# --------------------------------------------------
# Step 2: Install locked dependencies and run tests
# Matches CI Provider Docker test command
# --------------------------------------------------

log "Step 2/2: Run Provider tests using Python 3.15"

docker run --rm \
    --volume "${PROVIDER_DIR}:/src" \
    --workdir /src \
    "${PYTHON_IMAGE}" \
    sh -lc '
        set -eu

        python -m pip install \
            --disable-pip-version-check \
            --require-hashes \
            -r requirements.lock

        python -m pip install \
            --no-cache-dir \
            --no-build-isolation \
            --no-deps .

        python -m unittest discover \
            -s tests \
            -v

        python -c "
import sys
import zeaz_provider
from zeaz_provider.main import app

print(\"Python:\", sys.version)
print(\"Package:\", zeaz_provider.__file__)
print(\"Application:\", app.title)
"
    ' ||
    fail "Provider CI-equivalent test failed"

log "Provider CI-equivalent checks PASSED"
