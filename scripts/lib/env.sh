#!/usr/bin/env bash
# Safe dotenv reader for zwslcore shell scripts.
# Reads KEY=VALUE literally without eval/source so values containing shell metacharacters
# such as ';', spaces, '$', '&' or URLs cannot execute shell code.

dotenv_get() {
  local file="$1"
  local key="$2"
  local default_value="${3-}"
  local line value

  if [[ -L "$file" || ( -e "$file" && ! -f "$file" ) ]]; then
    printf 'Refusing non-regular or symlink environment file: %s\n' "$file" >&2
    return 2
  fi

  [[ -f "$file" ]] || {
    printf '%s' "$default_value"
    return 0
  }

  # Docker Compose resolves duplicate keys in a file using the last value.
  # Read the same occurrence so diagnostics and runtime config agree.
  line="$(grep -E "^[[:space:]]*${key}=" "$file" 2>/dev/null | tail -n 1 || true)"
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

write_curl_auth_header() {
  local file="$1"
  local key="$2"
  if [[ "$key" == *$'\r'* || "$key" == *$'\n'* ]]; then
    printf 'Refusing an API key containing a line break\n' >&2
    return 2
  fi
  (umask 077; printf 'Authorization: Bearer %s\n' "$key" >"$file") || return
  chmod 600 "$file"
}
