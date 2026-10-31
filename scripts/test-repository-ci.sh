#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="python:3.15-slim-bookworm@sha256:4e03260adeeebafccd084f3584e6b84823aba5651cfb53ef8a078ed441ddf9cd"

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/zwslcore-ci.XXXXXXXX")"
trap 'rm -rf -- "$TEMP_DIR"' EXIT

cd "$ROOT"

log() {
    printf '\n========== %s ==========\n' "$*"
}

fail() {
    printf '\nFAILED: %s\n' "$*" >&2
    exit 1
}

for cmd in python3 docker ruby; do
    command -v "$cmd" >/dev/null 2>&1 || fail "$cmd not found"
done

docker info >/dev/null || fail "Docker daemon unavailable"

[[ -f .env.example ]] || fail ".env.example missing"
[[ -f scripts/chaos.py ]] || fail "scripts/chaos.py missing"

TEMP_ENV="$TEMP_DIR/ci.env"
install -m 600 .env.example "$TEMP_ENV"

log "Repository baseline"
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -v

log "Shell syntax"
bash -n \
    scripts/install.sh \
    scripts/doctor.sh \
    scripts/smoke.sh \
    scripts/wait-runtime.sh \
    scripts/backup.sh \
    scripts/restore.sh \
    scripts/chaos.sh \
    scripts/bootstrap-wsl.sh \
    scripts/lib/env.sh

bash tests/test_env_loader.sh

log "Python compilation"
python3 -m py_compile \
    scripts/sync-free-models.py \
    scripts/models-dev.py \
    scripts/engineer.py \
    services/model_catalog/catalog.py \
    services/model_catalog/models_dev.py \
    services/model_catalog/selector.py

python3 -m compileall -q \
    services/provider/zeaz_provider \
    services/engineering

log "Engineering and Model Catalog tests"
python3 -m unittest \
    tests.test_model_catalog \
    tests.test_models_dev_catalog \
    tests.test_model_selector \
    tests.test_engineering_agents \
    tests.test_engineering_custom_agents \
    tests.test_engineering_delegation \
    tests.test_engineering_mcp \
    tests.test_engineering_change_snapshot \
    tests.test_engineering_tui \
    tests.test_engineering_reconcile \
    tests.test_engineering_control_plane \
    tests.test_engineering_transport_retry \
    tests.test_engineering_observability \
    -v

log "Chaos tests"
python3 scripts/chaos.py

log "Provider dependency lock"
docker run --rm \
    -v "$ROOT:/workspace" \
    -w /workspace \
    "$IMAGE" \
    sh -lc '
        set -eu
        python -m pip install --disable-pip-version-check "pip-tools==7.6.1"
        bash scripts/provider-lock.sh check
    '

log "Docker Compose validation"
docker compose --env-file "$TEMP_ENV" config --quiet

if grep -Eq '(^|:)(latest|main)$' .env.example; then
    fail "Mutable image tag found in .env.example"
fi

log "Provider Docker build"
docker compose --env-file "$TEMP_ENV" build provider

log "Provider Docker import smoke test"
docker compose --env-file "$TEMP_ENV" run --rm --no-deps \
    --entrypoint python provider \
    -c 'import sys, zeaz_provider; from zeaz_provider.main import app; print(sys.version); print(zeaz_provider.__file__); print(app.title)'

log "Provider hash-locked tests on Python 3.15"
docker run --rm \
    -v "$ROOT/services/provider:/src" \
    -w /src \
    "$IMAGE" \
    sh -lc '
        set -eu
        python -m pip install --disable-pip-version-check --require-hashes -r requirements.lock
        python -m pip install --no-cache-dir --no-build-isolation --no-deps .
        python -m unittest discover -s tests -v
        python -c "import sys, zeaz_provider; from zeaz_provider.main import app; print(sys.version); print(zeaz_provider.__file__); print(app.title)"
    '

log "Tracked secret filename check"
if git ls-files |
    grep -E '(^|/)(\.env|id_rsa|id_ed25519|.*\.pem|.*\.key)$' |
    grep -v '^\.env\.example$'; then
    fail "Potential secret-bearing tracked file found"
fi

log "GitHub Actions YAML syntax"
ruby -e '
require "yaml"
Dir.glob(".github/**/*.{yml,yaml}").each do |file|
  YAML.load_file(file)
  puts "OK #{file}"
end
'

log "LINUX REPOSITORY CI-EQUIVALENT CHECKS PASSED"
printf '\nHEAD: %s\n' "$(git rev-parse HEAD)"
printf '%s\n' \
    "Windows Installer job: NOT RUN" \
    "GitHub-hosted TruffleHog job: NOT RUN" \
    "GitHub Required Checks: NOT VERIFIED"
