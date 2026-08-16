#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="viewsense-dev"

if [[ "${namespace}" != "viewsense-dev" ]]; then
  echo "refusing to run outside the ViewSense development namespace" >&2
  exit 1
fi

kubectl -n "${namespace}" delete job viewsense-smoke --ignore-not-found --wait=true
kubectl apply -f "${repo_root}/deploy/kubernetes/tests/smoke-job.yaml"
if ! kubectl -n "${namespace}" wait --for=condition=complete job/viewsense-smoke --timeout=180s; then
  kubectl -n "${namespace}" logs job/viewsense-smoke
  exit 1
fi
kubectl -n "${namespace}" logs job/viewsense-smoke

probe_network_path() {
  local source_deployment="$1"
  local target_service="$2"
  local expected="$3"
  local status

  set +e
  kubectl -n "${namespace}" exec "deployment/${source_deployment}" -- \
    python -c 'import socket,sys; s=socket.socket(); s.settimeout(3); code=s.connect_ex((sys.argv[1], int(sys.argv[2]))); s.close(); sys.exit(0 if code == 0 else 42)' \
    "${target_service}" 8443 >/dev/null 2>&1
  status=$?
  set -e

  if [[ "${expected}" == "allowed" && "${status}" -ne 0 ]]; then
    echo "expected ${source_deployment} -> ${target_service} to be reachable" >&2
    exit 1
  fi
  if [[ "${expected}" == "blocked" && "${status}" -ne 42 ]]; then
    echo "expected ${source_deployment} -> ${target_service} to be blocked; probe status=${status}" >&2
    exit 1
  fi
  echo "network path ${source_deployment} -> ${target_service}: ${expected}"
}

# Pair each denied path with a required path from the same source pod. This avoids
# reporting a broken source pod or DNS failure as NetworkPolicy enforcement.
probe_network_path gateway orchestrator allowed
probe_network_path gateway ingestion blocked
probe_network_path orchestrator memory-gateway allowed
probe_network_path orchestrator mcp-gateway blocked
echo "ViewSense CNI policy probes passed"
