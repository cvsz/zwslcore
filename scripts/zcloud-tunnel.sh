#!/usr/bin/env bash
# Opt-in Cloud Shell connector lifecycle; does not install cloudflared or expose SSH.
set -Eeuo pipefail
umask 077

CONFIG="${ZCLOUD_CONFIG:-$HOME/.cloudflared/config.yml}"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/zwslcore-cloudflared"
PIDFILE="$STATE/supervisor.pid"
LOGFILE="$STATE/connector.log"
LOCKFILE="$STATE/connector.lock"
SELF="$(realpath "${BASH_SOURCE[0]}")"

mkdir -p "$STATE"
chmod 700 "$STATE"

supervisor_pid() {
  local pid cmd
  [[ -f "$PIDFILE" ]] || return 1
  read -r pid < "$PIDFILE" || return 1
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline")"
  [[ "$cmd" == *"$SELF supervise"* ]] || return 1
  printf '%s\n' "$pid"
}
preflight() {
  command -v cloudflared >/dev/null || { echo "cloudflared not installed" >&2; return 1; }
  [[ -f "$CONFIG" && ! -L "$CONFIG" ]] || { echo "Config missing or symlink: $CONFIG" >&2; return 1; }
  local perms
  perms="$(stat -c %a "$CONFIG")"
  if (( (8#$perms & 8#077) != 0 )); then
    echo "Config permissions expose credentials or origin metadata; require mode 0600" >&2
    return 1
  fi
  cloudflared tunnel --config "$CONFIG" ingress validate >/dev/null
  local name
  name="$(sed -n 's/^[[:space:]]*tunnel:[[:space:]]*//p' "$CONFIG" | head -1)"
  [[ -n "$name" ]] || { echo "Config missing tunnel ID" >&2; return 1; }
  if [[ -n "${ZCLOUD_TUNNEL_ID:-}" && "$name" != "$ZCLOUD_TUNNEL_ID" ]]; then
    echo "Tunnel ID mismatch; refusing to start" >&2; return 1
  fi
}
run_supervisor() {
  exec 9>"$LOCKFILE"
  flock -n 9 || { echo "Another supervisor owns the lock" >&2; return 1; }
  echo "$$" > "$PIDFILE"
  local child=""
  cleanup() {
    trap - TERM INT EXIT
    if [[ -n "$child" ]]; then
      kill -TERM "$child" 2>/dev/null || true
      wait "$child" 2>/dev/null || true
    fi
    if [[ -f "$PIDFILE" ]] && [[ "$(cat "$PIDFILE")" == "$$" ]]; then rm -f "$PIDFILE"; fi
  }
  trap cleanup TERM INT EXIT
  while :; do
    cloudflared tunnel --config "$CONFIG" run >>"$LOGFILE" 2>&1 &
    child="$!"
    wait "$child" || true
    child=""
    sleep 15 &
    child="$!"
    wait "$child" || true
    child=""
  done
}
case "${1:-status}" in
  preflight) preflight; echo "preflight: OK" ;;
  supervise) preflight; run_supervisor ;;
  start)
    preflight
    if pid="$(supervisor_pid)"; then echo "Supervisor running: $pid"; exit 0; fi
    # Do not compete with a manually started connector on the same config.
    if pgrep -u "$(id -u)" -x cloudflared >/dev/null; then
      echo "Existing cloudflared detected: inspect before starting a second connector" >&2
      exit 1
    fi
    nohup "$SELF" supervise </dev/null >/dev/null 2>&1 &
    sleep 1
    supervisor_pid >/dev/null || { echo "Failed to start; inspect $LOGFILE" >&2; exit 1; }
    echo "Supervisor started"
    ;;
  stop)
    if pid="$(supervisor_pid)"; then
      kill -TERM "$pid"
      for ((i=0;i<50;i++)); do
        if ! kill -0 "$pid" 2>/dev/null || ! supervisor_pid >/dev/null; then
          echo "Managed supervisor stopped"; exit 0
        fi
        sleep 0.1
      done
      echo "Supervisor did not stop within 5 seconds; investigate before restart" >&2
      exit 1
    else
      echo "No managed supervisor running"
    fi
    ;;
  restart) "$SELF" stop; "$SELF" start ;;
  status)
    if pid="$(supervisor_pid)"; then echo "Supervisor RUNNING pid=$pid"; else echo "Supervisor STOPPED"; fi
    echo "Config: $CONFIG"
    ;;
  logs) touch "$LOGFILE"; tail -n 80 "$LOGFILE" ;;
  install-autostart)
    # Shell startup is best effort, not a boot-level service.
    # The literal $HOME must expand when the user's shell later reads this line.
    # shellcheck disable=SC2016
    line='[ -x "$HOME/zwslcore/scripts/zcloud-tunnel.sh" ] && "$HOME/zwslcore/scripts/zcloud-tunnel.sh" start >/dev/null 2>&1 || true'
    if ! grep -Fq 'scripts/zcloud-tunnel.sh" start' "$HOME/.bashrc" 2>/dev/null; then
      printf '\n# zwslcore Cloud Shell tunnel (opt-in)\n%s\n' "$line" >> "$HOME/.bashrc"
    fi
    echo "Interactive shell startup hook installed; no VM boot guarantee"
    ;;
  *) echo "Usage: $0 {preflight|start|stop|restart|status|logs|install-autostart}" >&2; exit 2 ;;
esac
