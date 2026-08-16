#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="viewsense-dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
STATE_DIR="${REPO_ROOT}/.viewsense/port-forward"
PID_FILE="${STATE_DIR}/manager.pid"
LOG_FILE="${STATE_DIR}/manager.log"
SCRIPT_PATH="${SCRIPT_DIR}/port-forward-dev.sh"

SERVICES=(gateway identity memory-gateway governance agent-runtime)
LOCAL_PORTS=(9443 9444 9445 9446 9447)
REMOTE_PORT=8443
CHILD_PIDS=()

usage() {
  cat <<'EOF'
Usage: scripts/port-forward-dev.sh <command>

Commands:
  foreground  Run all forwards in this terminal; Ctrl+C stops all of them.
  start       Start all forwards in the background.
  stop        Stop the background manager and all of its forwards.
  status      Show manager state and the configured local endpoints.
  logs        Follow the background manager log.
EOF
}

manager_pid() {
  if [[ -f "${PID_FILE}" ]]; then
    tr -d '[:space:]' <"${PID_FILE}"
  fi
}

valid_manager() {
  local pid="${1:-}"
  local command_line
  [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
  kill -0 "${pid}" 2>/dev/null || return 1
  command_line="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
  [[ "${command_line}" == *"port-forward-dev.sh run"* ]]
}

print_endpoints() {
  local index
  for index in "${!SERVICES[@]}"; do
    printf '  %-18s https://127.0.0.1:%s\n' "${SERVICES[$index]}" "${LOCAL_PORTS[$index]}"
  done
}

preflight() {
  command -v kubectl >/dev/null 2>&1 || {
    echo "kubectl is required" >&2
    return 1
  }
  kubectl get namespace "${NAMESPACE}" >/dev/null
  local service
  for service in "${SERVICES[@]}"; do
    kubectl -n "${NAMESPACE}" get service "${service}" >/dev/null
  done
}

cleanup() {
  trap - EXIT INT TERM
  local pid
  for pid in "${CHILD_PIDS[@]:-}"; do
    if [[ "${pid}" =~ ^[0-9]+$ ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
  for pid in "${CHILD_PIDS[@]:-}"; do
    if [[ "${pid}" =~ ^[0-9]+$ ]]; then
      wait "${pid}" 2>/dev/null || true
    fi
  done
  if [[ -f "${PID_FILE}" ]] && [[ "$(manager_pid)" == "$$" ]]; then
    rm -f -- "${PID_FILE}"
  fi
}

run_forwards() {
  preflight
  mkdir -p -- "${STATE_DIR}"
  trap cleanup EXIT INT TERM

  local index
  for index in "${!SERVICES[@]}"; do
    kubectl -n "${NAMESPACE}" port-forward \
      --address 127.0.0.1 \
      "service/${SERVICES[$index]}" \
      "${LOCAL_PORTS[$index]}:${REMOTE_PORT}" &
    CHILD_PIDS+=("$!")
  done

  echo "ViewSense development port-forwards are active:"
  print_endpoints
  echo "Press Ctrl+C to stop all forwards."

  while true; do
    for index in "${!CHILD_PIDS[@]}"; do
      if ! kill -0 "${CHILD_PIDS[$index]}" 2>/dev/null; then
        echo "Port-forward for ${SERVICES[$index]} stopped unexpectedly." >&2
        return 1
      fi
    done
    sleep 1
  done
}

start_background() {
  mkdir -p -- "${STATE_DIR}"
  local existing
  existing="$(manager_pid || true)"
  if valid_manager "${existing}"; then
    echo "Port-forward manager is already running with PID ${existing}."
    print_endpoints
    return 0
  fi
  if [[ -f "${PID_FILE}" ]]; then
    rm -f -- "${PID_FILE}"
  fi

  nohup "${SCRIPT_PATH}" run >"${LOG_FILE}" 2>&1 &
  local pid=$!
  printf '%s\n' "${pid}" >"${PID_FILE}"
  sleep 2
  if ! valid_manager "${pid}"; then
    echo "Port-forward manager failed to start. Recent log output:" >&2
    tail -n 30 "${LOG_FILE}" >&2 || true
    return 1
  fi
  echo "Port-forward manager started with PID ${pid}."
  print_endpoints
  echo "Stop it with: scripts/port-forward-dev.sh stop"
}

stop_background() {
  local pid
  pid="$(manager_pid || true)"
  if [[ -z "${pid}" ]]; then
    echo "No background port-forward manager is recorded."
    return 0
  fi
  if ! valid_manager "${pid}"; then
    echo "Stale manager PID file found; no matching process was stopped." >&2
    rm -f -- "${PID_FILE}"
    return 1
  fi
  kill "${pid}"
  local attempt
  for attempt in {1..20}; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      rm -f -- "${PID_FILE}"
      echo "Port-forward manager stopped."
      return 0
    fi
    sleep 0.25
  done
  echo "Port-forward manager did not stop within five seconds." >&2
  return 1
}

show_status() {
  local pid
  pid="$(manager_pid || true)"
  if valid_manager "${pid}"; then
    echo "Port-forward manager is running with PID ${pid}."
    print_endpoints
    return 0
  fi
  echo "Port-forward manager is not running."
  return 1
}

case "${1:-}" in
  foreground) run_forwards ;;
  start) start_background ;;
  stop) stop_background ;;
  status) show_status ;;
  logs)
    mkdir -p -- "${STATE_DIR}"
    touch "${LOG_FILE}"
    tail -f "${LOG_FILE}"
    ;;
  run) run_forwards ;;
  *) usage; exit 2 ;;
esac
