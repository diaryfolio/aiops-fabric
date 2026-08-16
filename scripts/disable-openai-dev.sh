#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="viewsense-dev"

if [[ "$(kubectl config current-context)" != k3d-* ]]; then
  echo "refusing to change the development adapter outside a k3d context" >&2
  exit 1
fi
kubectl get namespace "${namespace}" >/dev/null

# Restore the default provider route before removing the adapter or its credential.
kubectl apply -k "${repo_root}/deploy/kubernetes/base"
kubectl -n "${namespace}" rollout status deployment/llm-gateway --timeout=180s

kubectl -n "${namespace}" get \
  deployment/openai-adapter \
  service/openai-adapter \
  serviceaccount/openai-adapter \
  networkpolicy/llm-gateway-openai-egress \
  networkpolicy/openai-adapter-policy \
  secret/openai-credentials \
  secret/tls-openai-adapter \
  --ignore-not-found
kubectl -n "${namespace}" delete \
  deployment/openai-adapter \
  service/openai-adapter \
  serviceaccount/openai-adapter \
  networkpolicy/llm-gateway-openai-egress \
  networkpolicy/openai-adapter-policy \
  secret/openai-credentials \
  secret/tls-openai-adapter \
  --ignore-not-found
echo "ViewSense AI® now routes to the deterministic mock LLM; the development OpenAI Secret was deleted."
