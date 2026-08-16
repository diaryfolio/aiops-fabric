#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
namespace="viewsense-dev"
context="$(kubectl config current-context)"
cluster_name="${VS_K3D_CLUSTER:-${context#k3d-}}"

if [[ "${namespace}" != "viewsense-dev" || -z "${cluster_name}" ]]; then
  echo "refusing deployment because the namespace or cluster name is invalid" >&2
  exit 1
fi

"${repo_root}/scripts/bootstrap-dev-pki.sh"
set -a
source "${repo_root}/.env.viewsense"
set +a

: "${VS_GATEWAY_CLIENT_SECRET:?missing gateway secret}"
: "${VS_ORCHESTRATOR_CLIENT_SECRET:?missing orchestrator secret}"
: "${VS_INGESTION_CLIENT_SECRET:?missing ingestion secret}"
: "${VS_LLM_GATEWAY_CLIENT_SECRET:?missing LLM gateway secret}"
: "${VS_MEMORY_GATEWAY_CLIENT_SECRET:?missing memory gateway secret}"
: "${VS_MCP_GATEWAY_CLIENT_SECRET:?missing MCP gateway secret}"
: "${VS_SMOKE_CLIENT_SECRET:?missing smoke secret}"
: "${VS_MEMORY_DB_PASSWORD:?missing memory DB password}"
: "${VS_REGISTRY_DB_PASSWORD:?missing registry DB password}"
: "${VS_GOVERNANCE_DB_PASSWORD:?missing governance DB password}"
: "${VS_AGENT_DB_PASSWORD:?missing agent DB password}"

docker build --target runtime -t viewsense-core:dev "${repo_root}"
if [[ "${context}" == k3d-* ]]; then
  docker pull pgvector/pgvector:pg16-bookworm
  docker pull postgres:16-bookworm
  k3d image import viewsense-core:dev pgvector/pgvector:pg16-bookworm postgres:16-bookworm \
    --cluster "${cluster_name}"
fi

kubectl apply -f "${repo_root}/deploy/kubernetes/base/namespace.yaml"

apply_secret() {
  local secret_name="$1"
  shift
  kubectl -n "${namespace}" create secret generic "${secret_name}" "$@" \
    --dry-run=client -o yaml | kubectl apply -f -
}

for service in identity gateway orchestrator ingestion llm-gateway mock-llm memory-gateway memory-postgres mcp-gateway mock-mcp governance agent-runtime smoke; do
  apply_secret "tls-${service}" \
    --from-file=ca.crt="${repo_root}/.viewsense/pki/${service}/ca.crt" \
    --from-file=tls.crt="${repo_root}/.viewsense/pki/${service}/tls.crt" \
    --from-file=tls.key="${repo_root}/.viewsense/pki/${service}/tls.key"
done

apply_secret identity-public --from-file=signing.pub="${repo_root}/.viewsense/identity-signing.pub"
apply_secret identity-material \
  --from-file=signing.key="${repo_root}/.viewsense/identity-signing.key" \
  --from-file=clients.json="${repo_root}/.viewsense/clients.json"
apply_secret workload-credentials \
  --from-literal=gateway="${VS_GATEWAY_CLIENT_SECRET}" \
  --from-literal=orchestrator="${VS_ORCHESTRATOR_CLIENT_SECRET}" \
  --from-literal=ingestion="${VS_INGESTION_CLIENT_SECRET}" \
  --from-literal=llm-gateway="${VS_LLM_GATEWAY_CLIENT_SECRET}" \
  --from-literal=memory-gateway="${VS_MEMORY_GATEWAY_CLIENT_SECRET}" \
  --from-literal=mcp-gateway="${VS_MCP_GATEWAY_CLIENT_SECRET}" \
  --from-literal=smoke="${VS_SMOKE_CLIENT_SECRET}"
apply_secret memory-db-credentials \
  --from-literal=password="${VS_MEMORY_DB_PASSWORD}" \
  --from-literal=url="postgresql://viewsense_memory:${VS_MEMORY_DB_PASSWORD}@memory-db:5432/viewsense_memory"
apply_secret registry-db-credentials \
  --from-literal=password="${VS_REGISTRY_DB_PASSWORD}" \
  --from-literal=url="postgresql://viewsense_registry:${VS_REGISTRY_DB_PASSWORD}@registry-db:5432/viewsense_registry"
apply_secret governance-db-credentials \
  --from-literal=password="${VS_GOVERNANCE_DB_PASSWORD}" \
  --from-literal=url="postgresql://viewsense_governance:${VS_GOVERNANCE_DB_PASSWORD}@governance-db:5432/viewsense_governance"
apply_secret agent-db-credentials \
  --from-literal=password="${VS_AGENT_DB_PASSWORD}" \
  --from-literal=url="postgresql://viewsense_agent:${VS_AGENT_DB_PASSWORD}@agent-db:5432/viewsense_agent"

kubectl apply -k "${repo_root}/deploy/kubernetes/base"
kubectl -n "${namespace}" rollout status statefulset/memory-db --timeout=180s
kubectl -n "${namespace}" rollout status statefulset/registry-db --timeout=180s
kubectl -n "${namespace}" rollout status statefulset/governance-db --timeout=180s
kubectl -n "${namespace}" rollout status statefulset/agent-db --timeout=180s
for deployment in identity gateway orchestrator ingestion llm-gateway mock-llm memory-gateway memory-postgres mcp-gateway mock-mcp governance agent-runtime; do
  # TLS keys, signing material, workload credentials, and the mutable development
  # image are loaded at process start. Restart and wait sequentially so the small
  # development cluster never surges every service at the same time.
  kubectl -n "${namespace}" rollout restart "deployment/${deployment}"
  kubectl -n "${namespace}" rollout status "deployment/${deployment}" --timeout=180s
done
kubectl -n "${namespace}" get pods -o wide
