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
