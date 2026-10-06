#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
provider_dir="$repo_root/services/provider"
mode="${1:-check}"
expected_pip_tools="7.6.1"

if [[ "$mode" != "check" && "$mode" != "update" ]]; then
  echo "Usage: $0 [check|update]" >&2
  exit 2
fi

if ! command -v pip-compile >/dev/null 2>&1; then
  echo "pip-compile is required; install pip-tools==$expected_pip_tools" >&2
  exit 2
fi

actual_pip_tools="$(pip-compile --version | awk '{print $NF}')"
if [[ "$actual_pip_tools" != "$expected_pip_tools" ]]; then
  echo "Expected pip-tools $expected_pip_tools, found $actual_pip_tools" >&2
  exit 2
fi

python_minor="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$python_minor" != "3.14" ]]; then
  echo "The Provider lock targets Python 3.14; use Python 3.14 to compile or check it" >&2
  exit 2
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
cp "$provider_dir/pyproject.toml" "$tmp_dir/pyproject.toml"
if [[ -f "$provider_dir/requirements.lock" ]]; then
  cp "$provider_dir/requirements.lock" "$tmp_dir/requirements.lock"
fi
export CUSTOM_COMPILE_COMMAND='pip-compile --all-build-deps --allow-unsafe --generate-hashes --output-file=requirements.lock pyproject.toml'
upgrade_args=()
if [[ "$mode" == "update" ]]; then
  upgrade_args+=(--upgrade)
fi
(
  cd "$tmp_dir"
  pip-compile \
    --quiet \
    --no-config \
    --allow-unsafe \
    --strip-extras \
    --generate-hashes \
    --reuse-hashes \
    --all-build-deps \
    --resolver=backtracking \
    --no-emit-index-url \
    --no-emit-options \
    "${upgrade_args[@]}" \
    --output-file=requirements.lock \
    pyproject.toml
)

if [[ "$mode" == "update" ]]; then
  install -m 0644 "$tmp_dir/requirements.lock" "$provider_dir/requirements.lock"
  echo "Updated services/provider/requirements.lock"
  exit 0
fi

if ! cmp -s "$provider_dir/requirements.lock" "$tmp_dir/requirements.lock"; then
  echo "Provider dependency lock drift detected. Run 'make provider-lock' with Python 3.14 and pip-tools $expected_pip_tools." >&2
  diff -u "$provider_dir/requirements.lock" "$tmp_dir/requirements.lock" || true
  exit 1
fi

echo "Provider dependency lock is current."
