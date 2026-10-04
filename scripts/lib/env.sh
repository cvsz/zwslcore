#!/usr/bin/env bash
# Safe dotenv reader for zwslcore shell scripts.
# Reads KEY=VALUE literally without eval/source so values containing shell metacharacters
# such as ';', spaces, '$', '&' or URLs cannot execute shell code.

dotenv_get() {
  local file="$1"
  local key="$2"
  local default_value="${3-}"
  local line value

  [[ -f "$file" ]] || {
    printf '%s' "$default_value"
    return 0
  }

  line="$(grep -m1 -E "^[[:space:]]*${key}=" "$file" 2>/dev/null || true)"
  if [[ -z "$line" ]]; then
    printf '%s' "$default_value"
    return 0
  fi

  value="${line#*=}"

  # Support simple single/double quoted dotenv values without interpreting escapes.
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi

  printf '%s' "$value"
}
