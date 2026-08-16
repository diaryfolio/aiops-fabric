#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
staging="${repo_root}/docs-site"

if [[ "${staging}" != "${repo_root}/docs-site" || -z "${repo_root}" ]]; then
  echo "refusing to use an unexpected documentation staging path" >&2
  exit 1
fi
if [[ -e "${staging}" ]]; then
  if [[ ! -d "${staging}" || -L "${staging}" ]]; then
    echo "refusing to replace non-directory or linked staging path: ${staging}" >&2
    exit 1
  fi
  echo "Refreshing generated documentation staging directory: ${staging}"
  rm -rf -- "${staging}"
fi
mkdir -p "${staging}"

documents=(
  "CLAUDE.md"
  "QUICKSTART.md"
  "TECHNICAL_README.md"
  "contracts/README.md"
  "deploy/integrations/README.md"
  "deploy/integrations/keycloak.md"
  "deploy/integrations/observability-workflows.md"
  "deploy/integrations/spire.md"
  "docs/publishing.md"
  "docs/design/high-level/README.md"
  "docs/design/high-level/design_01.md"
  "docs/design/high-level/00-implementation-conformance.md"
  "docs/design/high-level/10-overall/01-objective-principles.md"
  "docs/design/high-level/10-overall/02-runtime-topology-flow.md"
  "docs/design/high-level/10-overall/03-api-integration-standards.md"
  "docs/design/high-level/10-overall/04-component-breakdown.md"
  "docs/design/high-level/10-overall/05-operations-and-roadmap.md"
  "docs/design/high-level/20-deployment/01-deployment-topology-sizing.md"
  "docs/design/high-level/30-security/01-zero-trust.md"
  "docs/design/high-level/40-ops/01-day2-operations-sre.md"
  "docs/design/high-level/50-roadmap/01-roadmap-maturity.md"
  "docs/design/high-level/60-enterprise/01-enterprise-integration-controls.md"
  "docs/design/high-level/70-agentic/01-agent-runtime-ingestion-workflows.md"
  "docs/design/high-level/80-future/01-sovereign-control-evidence-fabric.md"
  "docs/prompts/governance/README.md"
  "docs/prompts/governance/design-sync-checklist.md"
  "docs/prompts/governance/design-sync-guardrail.prompt.md"
  "docs/prompts/governance/major-change-policy.md"
  "docs/prompts/governance/major-change-template.md"
  "fabric/PRODUCTS.md"
  "fabric/README.md"
  "fabric/agents/README.md"
  "fabric/charts/viewsense/README.md"
  "fabric/core/README.md"
  "fabric/governance/README.md"
  "fabric/identity/README.md"
  "fabric/ingestion/README.md"
  "fabric/llm/README.md"
  "fabric/mcp-registry/README.md"
  "fabric/memory/README.md"
  "fabric/observability/README.md"
  "fabric/workflows/README.md"
  "tests/README.md"
)

cp "${repo_root}/README.md" "${staging}/index.md"
for document in "${documents[@]}"; do
  if [[ ! -f "${repo_root}/${document}" ]]; then
    echo "missing published documentation source: ${document}" >&2
    exit 1
  fi
  mkdir -p "$(dirname "${staging}/${document}")"
  cp "${repo_root}/${document}" "${staging}/${document}"
done

cd "${repo_root}"
zensical build --clean --strict
