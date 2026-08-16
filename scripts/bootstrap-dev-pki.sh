#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_dir="${repo_root}/.viewsense"
pki_dir="${runtime_dir}/pki"
env_file="${repo_root}/.env.viewsense"

# Database credentials must survive PKI/client regeneration because Compose keeps
# provider data in named volumes. Rotating these implicitly would strand those
# volumes behind passwords the application no longer knows.
existing_env_value() {
  local key="$1"
  local line
  [[ -f "${env_file}" ]] || return 1
  while IFS= read -r line; do
    if [[ "${line}" == "${key}="* ]]; then
      printf '%s' "${line#*=}"
      return 0
    fi
  done <"${env_file}"
  return 1
}

preserved_memory_db_password="$(existing_env_value VS_MEMORY_DB_PASSWORD || true)"
preserved_registry_db_password="$(existing_env_value VS_REGISTRY_DB_PASSWORD || true)"
preserved_governance_db_password="$(existing_env_value VS_GOVERNANCE_DB_PASSWORD || true)"
preserved_agent_db_password="$(existing_env_value VS_AGENT_DB_PASSWORD || true)"

if [[ -f "${env_file}" && -f "${pki_dir}/ca.crt" && -f "${pki_dir}/governance/tls.crt" \
  && -f "${pki_dir}/agent-runtime/tls.crt" \
  && -f "${pki_dir}/openai-adapter/tls.crt" \
  && -f "${runtime_dir}/clients.json" ]] \
  && grep -q '"ingestion"' "${runtime_dir}/clients.json" \
  && grep -q '"openai-adapter"' "${runtime_dir}/clients.json" \
  && grep -q '"can_delegate_tenant"' "${runtime_dir}/clients.json" \
  && grep -q '^VS_GOVERNANCE_DB_PASSWORD=' "${env_file}" \
  && grep -q '^VS_AGENT_DB_PASSWORD=' "${env_file}"; then
  echo "ViewSense development credentials already exist in ${runtime_dir}"
  exit 0
fi

if [[ -d "${runtime_dir}" ]]; then
  if find "${runtime_dir}" -type l -print -quit | grep -q .; then
    echo "refusing to rotate development credentials because .viewsense contains a symbolic link" >&2
    exit 1
  fi
  find "${runtime_dir}" -type f -exec chmod u+w {} +
fi
if [[ -f "${env_file}" ]]; then
  chmod u+w "${env_file}"
fi

umask 077
mkdir -p "${pki_dir}"
openssl genrsa -out "${pki_dir}/ca.key" 3072 >/dev/null 2>&1
openssl req -x509 -new -key "${pki_dir}/ca.key" -sha256 -days 30 \
  -subj "/O=ViewSense Development/CN=ViewSense Development CA" \
  -out "${pki_dir}/ca.crt"

services=(identity gateway orchestrator ingestion llm-gateway memory-gateway memory-postgres mcp-gateway mock-llm openai-adapter mock-mcp governance agent-runtime smoke)
for service in "${services[@]}"; do
  service_dir="${pki_dir}/${service}"
  mkdir -p "${service_dir}"
  cp "${pki_dir}/ca.crt" "${service_dir}/ca.crt"
  openssl genrsa -out "${service_dir}/tls.key" 2048 >/dev/null 2>&1
  openssl req -new -key "${service_dir}/tls.key" -subj "/O=ViewSense Development/CN=${service}" \
    -out "${service_dir}/tls.csr"
  cat >"${service_dir}/extensions.cnf" <<EOF
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
subjectAltName=DNS:${service},DNS:${service}.viewsense-dev.svc,DNS:${service}.viewsense-dev.svc.cluster.local,DNS:localhost,IP:127.0.0.1
EOF
  openssl x509 -req -in "${service_dir}/tls.csr" -CA "${pki_dir}/ca.crt" \
    -CAkey "${pki_dir}/ca.key" -CAcreateserial -out "${service_dir}/tls.crt" \
    -days 7 -sha256 -extfile "${service_dir}/extensions.cnf" >/dev/null 2>&1
  rm "${service_dir}/tls.csr" "${service_dir}/extensions.cnf"
done

openssl genrsa -out "${runtime_dir}/identity-signing.key" 3072 >/dev/null 2>&1
openssl rsa -in "${runtime_dir}/identity-signing.key" -pubout \
  -out "${runtime_dir}/identity-signing.pub" >/dev/null 2>&1

random_secret() { openssl rand -hex 24; }
cli_secret="$(random_secret)"
gateway_secret="$(random_secret)"
orchestrator_secret="$(random_secret)"
ingestion_secret="$(random_secret)"
llm_gateway_secret="$(random_secret)"
memory_gateway_secret="$(random_secret)"
mcp_gateway_secret="$(random_secret)"
smoke_secret="$(random_secret)"
if [[ "${preserved_memory_db_password}" =~ ^[[:xdigit:]]{48}$ ]]; then
  memory_db_password="${preserved_memory_db_password}"
else
  memory_db_password="$(random_secret)"
fi
if [[ "${preserved_registry_db_password}" =~ ^[[:xdigit:]]{48}$ ]]; then
  registry_db_password="${preserved_registry_db_password}"
else
  registry_db_password="$(random_secret)"
fi
if [[ "${preserved_governance_db_password}" =~ ^[[:xdigit:]]{48}$ ]]; then
  governance_db_password="${preserved_governance_db_password}"
else
  governance_db_password="$(random_secret)"
fi
if [[ "${preserved_agent_db_password}" =~ ^[[:xdigit:]]{48}$ ]]; then
  agent_db_password="${preserved_agent_db_password}"
else
  agent_db_password="$(random_secret)"
fi

cat >"${runtime_dir}/clients.json" <<EOF
{
  "viewsense-cli": {"secret": "${cli_secret}", "tenant_id": "tenant-a", "grants": {"gateway": ["api.invoke"]}},
  "gateway": {"secret": "${gateway_secret}", "can_delegate_tenant": true, "grants": {"orchestrator": ["orchestrate.invoke"]}},
  "orchestrator": {"secret": "${orchestrator_secret}", "can_delegate_tenant": true, "grants": {"memory-gateway": ["memory.read", "memory.write"], "llm-gateway": ["llm.invoke"], "mcp-gateway": ["mcp.invoke"]}},
  "ingestion": {"secret": "${ingestion_secret}", "can_delegate_tenant": true, "grants": {"memory-gateway": ["memory.write"]}},
  "llm-gateway": {"secret": "${llm_gateway_secret}", "can_delegate_tenant": true, "grants": {"mock-llm": ["provider.invoke"], "openai-adapter": ["provider.invoke"]}},
  "memory-gateway": {"secret": "${memory_gateway_secret}", "can_delegate_tenant": true, "grants": {"memory-postgres": ["provider.invoke"]}},
  "mcp-gateway": {"secret": "${mcp_gateway_secret}", "can_delegate_tenant": true, "grants": {"mock-mcp": ["provider.invoke"]}},
  "smoke": {"secret": "${smoke_secret}", "tenant_id": "tenant-a", "grants": {"gateway": ["api.invoke"], "ingestion": ["ingest.write"], "memory-gateway": ["memory.read", "memory.write"], "mcp-gateway": ["mcp.admin", "mcp.invoke"], "governance": ["governance.admin", "governance.read", "evidence.write"], "agent-runtime": ["agent.run", "agent.approve"]}}
}
EOF

cat >"${env_file}" <<EOF
VS_CLI_CLIENT_SECRET=${cli_secret}
VS_GATEWAY_CLIENT_SECRET=${gateway_secret}
VS_ORCHESTRATOR_CLIENT_SECRET=${orchestrator_secret}
VS_INGESTION_CLIENT_SECRET=${ingestion_secret}
VS_LLM_GATEWAY_CLIENT_SECRET=${llm_gateway_secret}
VS_MEMORY_GATEWAY_CLIENT_SECRET=${memory_gateway_secret}
VS_MCP_GATEWAY_CLIENT_SECRET=${mcp_gateway_secret}
VS_SMOKE_CLIENT_SECRET=${smoke_secret}
VS_MEMORY_DB_PASSWORD=${memory_db_password}
VS_REGISTRY_DB_PASSWORD=${registry_db_password}
VS_GOVERNANCE_DB_PASSWORD=${governance_db_password}
VS_AGENT_DB_PASSWORD=${agent_db_password}
EOF

chmod 0600 "${env_file}"
chmod 0444 "${runtime_dir}/clients.json" "${runtime_dir}/identity-signing.key" "${runtime_dir}/identity-signing.pub"
find "${pki_dir}" -type f -exec chmod 0444 {} +
echo "Created short-lived ViewSense development PKI and credentials in ${runtime_dir}"
