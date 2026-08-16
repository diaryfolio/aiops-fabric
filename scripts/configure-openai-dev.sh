#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="viewsense-dev"
model="$("${repo_root}/scripts/read-model-config.sh")"
openai_api_key="${OPENAI_API_KEY:-}"
unset OPENAI_API_KEY

cleanup() {
  unset openai_api_key
}
trap cleanup EXIT INT TERM

if [[ "$(kubectl config current-context)" != k3d-* ]]; then
  echo "refusing to configure the development adapter outside a k3d context" >&2
  exit 1
fi
kubectl get namespace "${namespace}" >/dev/null
for file in ca.crt tls.crt tls.key; do
  if [[ ! -f "${repo_root}/.viewsense/pki/openai-adapter/${file}" ]]; then
    echo "missing OpenAI adapter PKI; run make k8s-deploy first" >&2
    exit 1
  fi
done
if [[ -z "${openai_api_key}" ]]; then
  read -r -s -p "OpenAI API key (input is hidden): " openai_api_key </dev/tty
  printf '\n' >/dev/tty
fi
if [[ -z "${openai_api_key}" || "${openai_api_key}" == *$'\n'* ]]; then
  echo "OpenAI API key is empty or invalid" >&2
  exit 1
fi
kubectl -n "${namespace}" create secret generic tls-openai-adapter \
  --from-file=ca.crt="${repo_root}/.viewsense/pki/openai-adapter/ca.crt" \
  --from-file=tls.crt="${repo_root}/.viewsense/pki/openai-adapter/tls.crt" \
  --from-file=tls.key="${repo_root}/.viewsense/pki/openai-adapter/tls.key" \
  --dry-run=client -o yaml | kubectl apply -f -

printf '%s' "${openai_api_key}" | kubectl -n "${namespace}" create secret generic openai-credentials \
  --from-file=api-key=/dev/stdin \
  --from-literal=model="${model}" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -k "${repo_root}/deploy/kubernetes/overlays/openai"
kubectl -n "${namespace}" rollout status deployment/openai-adapter --timeout=180s
kubectl -n "${namespace}" rollout status deployment/llm-gateway --timeout=180s
echo "ViewSense now routes model requests through the OpenAI adapter using model ${model}."
