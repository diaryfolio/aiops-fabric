#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="viewsense-dev"
model="$("${repo_root}/scripts/read-model-config.sh")"

if [[ "$(kubectl config current-context)" != k3d-* ]]; then
  echo "refusing to update the development adapter outside a k3d context" >&2
  exit 1
fi
kubectl get namespace "${namespace}" >/dev/null
if ! kubectl -n "${namespace}" get secret openai-credentials >/dev/null 2>&1; then
  echo "OpenAI is not configured; run make openai-enable first" >&2
  exit 1
fi
kubectl -n "${namespace}" get deployment openai-adapter >/dev/null

# The validated model value is non-secret. Patching stringData.model preserves the existing API key.
kubectl -n "${namespace}" patch secret openai-credentials \
  --type=merge \
  --patch "{\"stringData\":{\"model\":\"${model}\"}}" >/dev/null
kubectl -n "${namespace}" rollout restart deployment/openai-adapter
kubectl -n "${namespace}" rollout status deployment/openai-adapter --timeout=180s
echo "ViewSense OpenAI adapter now uses model ${model}; the API key was not read or replaced."
