# ViewSense Test and Validation Guide

Run commands from the repository root. Development PKI and credentials are generated under `.viewsense/` and `.env.viewsense`; both are ignored by Git. Never reuse them outside the isolated development environment.

## 1. Static and unit validation

```bash
make lint
make unit
make catalog-check
make profile-check
helm lint fabric/charts/viewsense
kubectl kustomize deploy/kubernetes/base >/dev/null
```

Expected: Ruff succeeds, all Pytest tests pass, every `fabric/*` module descriptor and product
catalog entry resolves, the default plus all curated Helm profiles render with zero failures, and
Kustomize renders without an error.

Inspect what a profile actually creates; a value naming an external product is not proof that the
upstream operator/product was installed:

```bash
helm template viewsense fabric/charts/viewsense \
  -f fabric/charts/viewsense/profiles/enterprise-suite.yaml |
kubectl apply --dry-run=client -f - >/dev/null
```

## 2. Docker Compose integration

```bash
make compose-up
make compose-test
```

If local port-forwards already use `9443` or `9444`, select alternate loopback ports; service-to-service
traffic and the smoke test remain on the private Compose networks:

```bash
VS_GATEWAY_HOST_PORT=19543 VS_IDENTITY_HOST_PORT=19544 make compose-up
make compose-test
```

Expected final line:

```text
ViewSense end-to-end smoke tests passed
```

Stop application containers while retaining development database volumes:

```bash
docker compose --env-file .env.viewsense down --remove-orphans
```

## 3. Kubernetes deployment and integration

The development scripts refuse to use a namespace other than `viewsense-dev`.

```bash
kubectl config current-context
make k8s-deploy
make k8s-test
kubectl get pods -n viewsense-dev
```

Expected: all Deployments and all four StatefulSets (memory, registry, governance, and agent) are
ready, and `viewsense-smoke` completes successfully.

## 4. Direct memory API validation

The memory gateway is internal and uses both mutual TLS and an audience/scoped bearer token. Start
all commonly tested APIs in one foreground terminal; `Ctrl+C` stops every forward:

```bash
make ports
```

Alternatively, manage them in the background:

```bash
make ports-start
make ports-status
make ports-stop
```

The manager exposes the public gateway `9443`, identity `9444`, memory `9445`, governance `9446`,
and agent runtime `9447` on `127.0.0.1` only. Background logs are available with
`scripts/port-forward-dev.sh logs`.

In a third terminal, load the development credentials without printing them and request a short-lived token:

```bash
set -a
source .env.viewsense
set +a

TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=memory-gateway" \
    --data-urlencode "scope=memory.read memory.write" \
    https://localhost:9444/oauth2/token |
  jq -r '.access_token'
)"

test -n "${TOKEN}" && test "${TOKEN}" != "null" && echo "Access token obtained"
```

Write a memory:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "owner_id": "api-demo-user",
    "content": "The ViewSense production region is London.",
    "metadata": {
      "source": "manual-api-test",
      "classification": "internal"
    }
  }' \
  https://localhost:9445/v1/memories |
jq
```

Search memory:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "owner_id": "api-demo-user",
    "query": "Where is the production region?",
    "limit": 5
  }' \
  https://localhost:9445/v1/memories/search |
jq
```

Expected: the write returns an ID and the search returns the London record in `items`.

## 5. Real OpenAI memory-grounding validation

This optional test incurs OpenAI API usage. Never paste the key into chat, a command argument, a
values file, or Git. Configure the isolated adapter using the hidden terminal prompt (the default
model is `gpt-4.1-mini`):

```bash
make openai-enable
make ports-start
```

`openai-enable` expects the base suite to be installed, stores the key in the
`openai-credentials` Kubernetes Secret, and switches only the LLM gateway route. The key is mounted
only in `openai-adapter`; the gateway, orchestrator, memory services, and client never receive it.
Use `make openai-enable-fresh` only when an image rebuild and base rollout are also required.

Load the generated development client secret and obtain separate least-privilege tokens:

```bash
set -a
source .env.viewsense
set +a

MEMORY_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=memory-gateway" \
    --data-urlencode "scope=memory.write" \
    https://localhost:9444/oauth2/token | jq -r '.access_token'
)"

GATEWAY_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=gateway" \
    --data-urlencode "scope=api.invoke" \
    https://localhost:9444/oauth2/token | jq -r '.access_token'
)"
```

Insert a harmless, unique test memory:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${MEMORY_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "owner_id": "openai-memory-demo",
    "content": "For the ViewSense integration test, the approval phrase is cobalt-canary-731.",
    "metadata": {"source":"openai-memory-test","classification":"internal"}
  }' \
  https://localhost:9445/v1/memories | jq
```

Now prompt the public API. `remember:false` avoids writing the answer back into memory:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${GATEWAY_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "user_id": "openai-memory-demo",
    "input": "What is the ViewSense integration test approval phrase? Answer with only the phrase.",
    "remember": false
  }' \
  https://localhost:9443/v1/responses |
jq '{output_text, memory_hits, model, request_id}'
```

Expected: `memory_hits` is at least `1`, `output_text` contains `cobalt-canary-731`, and `model`
shows the configured OpenAI model. This proves the answer path used the inserted tenant/owner-bound
memory; it does not by itself certify production data-residency or model quality controls.

Return to the deterministic mock and delete the development OpenAI Secret:

```bash
make openai-disable
make ports-stop
```

## 6. Durable agent API validation

Keep the forwards from section 4 running; the agent runtime is already available on port `9447`.

Request the least-privileged run token and create an idempotent bounded run:

```bash
AGENT_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=agent-runtime" \
    --data-urlencode "scope=agent.run" \
    https://localhost:9444/oauth2/token | jq -r '.access_token'
)"

RUN="$(
  curl --silent --show-error --fail-with-body \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --header "Authorization: Bearer ${AGENT_TOKEN}" \
    --header "Idempotency-Key: agent-api-demo-0001" \
    --header "Content-Type: application/json" \
    --data '{"objective":"Validate a governed change","max_steps":5,"max_tool_calls":2,"max_cost_units":20}' \
    https://localhost:9447/v1/agent-runs
)"
echo "${RUN}" | jq
RUN_ID="$(echo "${RUN}" | jq -r '.id')"
```

Repeating the create with the same key returns the same ID with
`"idempotent_replay":true`. Advance it to a human approval pause:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${AGENT_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"action":"start","expected_version":1}' \
  "https://localhost:9447/v1/agent-runs/${RUN_ID}:resume" | jq

curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${AGENT_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"action":"request_approval","expected_version":2}' \
  "https://localhost:9447/v1/agent-runs/${RUN_ID}:resume" | jq
```

An `agent.run` token cannot approve. This must return `403`:

```bash
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${AGENT_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"action":"approve","expected_version":3}' \
  "https://localhost:9447/v1/agent-runs/${RUN_ID}:resume"
```

Obtain `agent.approve`, approve version 3, then use `agent.run` to checkpoint version 4 and complete
version 5. Inspect the final ordered event history:

```bash
APPROVAL_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=agent-runtime" \
    --data-urlencode "scope=agent.approve" \
    https://localhost:9444/oauth2/token | jq -r '.access_token'
)"

curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${APPROVAL_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"action":"approve","expected_version":3,"reason":"change approved"}' \
  "https://localhost:9447/v1/agent-runs/${RUN_ID}:resume" | jq

for step in 'checkpoint 4' 'complete 5'; do
  set -- ${step}
  curl --silent --show-error --fail-with-body \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --header "Authorization: Bearer ${AGENT_TOKEN}" \
    --header "Content-Type: application/json" \
    --data "{\"action\":\"$1\",\"expected_version\":$2}" \
    "https://localhost:9447/v1/agent-runs/${RUN_ID}:resume" | jq
done

curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${AGENT_TOKEN}" \
  "https://localhost:9447/v1/agent-runs/${RUN_ID}/events" | jq
```

Expected: the terminal state is `completed`; events are sequences 1 through 6. A stale
`expected_version`, invalid state transition, or exhausted step budget returns `409`.

## 7. Provider governance and evidence API validation

Keep the forwards from section 4 running; governance is already available on port `9446`.

Request an administrator token and register a draft provider passport. A provider cannot submit
`"status":"admitted"`; only the evaluated admission endpoint can make that transition.

```bash
GOVERNANCE_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=governance" \
    --data-urlencode "scope=governance.admin" \
    https://localhost:9444/oauth2/token |
  jq -r '.access_token'
)"

curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${GOVERNANCE_TOKEN}" \
  --header "Content-Type: application/json" \
  --request PUT \
  --data '{
    "name":"manual-llm",
    "kind":"llm",
    "endpoint":"https://llm.enterprise.example/v1",
    "protocols":{"inference":"openai-compatible-v1"},
    "capabilities":{"chat":true,"streaming":true},
    "residencies":["gb"],
    "data_classifications":["internal"],
    "owner":"enterprise-ai-platform",
    "status":"draft",
    "expires_at":"2099-01-01T00:00:00Z"
  }' \
  https://localhost:9446/v1/provider-passports/manual-llm |
jq
```

Record a passing evaluation and request admission:

```bash
curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${GOVERNANCE_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"suite":"security-baseline","passed":true,"scores":{"pass_rate":1.0},"policy_version":"manual-v1"}' \
  https://localhost:9446/v1/provider-passports/manual-llm/evaluations |
jq

curl --silent --show-error --fail-with-body \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${GOVERNANCE_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{
    "required_capabilities":["chat"],
    "allowed_residencies":["gb"],
    "data_classification":"internal",
    "required_evaluation_suites":["security-baseline"],
    "policy_version":"manual-v1"
  }' \
  https://localhost:9446/v1/provider-passports/manual-llm:admit |
jq
```

Expected: the admission response contains `"admitted": true`. The end-to-end smoke test also
writes and reads a payload-minimized evidence event and verifies that tenant spoofing through
`X-ViewSense-Tenant` is rejected.

## 8. Negative authorization validation

A request without a bearer token must return `401`:

```bash
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Content-Type: application/json" \
  --data '{"owner_id":"api-demo-user","query":"London"}' \
  https://localhost:9445/v1/memories/search
```

Request a read-only token, then attempt a write. The write must return `403`:

```bash
READ_TOKEN="$(
  curl --silent --show-error --fail \
    --cacert .viewsense/pki/smoke/ca.crt \
    --cert .viewsense/pki/smoke/tls.crt \
    --key .viewsense/pki/smoke/tls.key \
    --user "smoke:${VS_SMOKE_CLIENT_SECRET}" \
    --header "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=client_credentials" \
    --data-urlencode "audience=memory-gateway" \
    --data-urlencode "scope=memory.read" \
    https://localhost:9444/oauth2/token |
  jq -r '.access_token'
)"

curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${READ_TOKEN}" \
  --header "Content-Type: application/json" \
  --data '{"owner_id":"api-demo-user","content":"must be denied"}' \
  https://localhost:9445/v1/memories
```

An otherwise valid token accompanied by an unsigned tenant header must return `400`:

```bash
curl --silent --output /dev/null --write-out '%{http_code}\n' \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  --header "Authorization: Bearer ${READ_TOKEN}" \
  --header "X-ViewSense-Tenant: attacker-selected-tenant" \
  --header "Content-Type: application/json" \
  --data '{"owner_id":"api-demo-user","query":"London"}' \
  https://localhost:9445/v1/memories/search
```

## 9. Mem0, OPA, Keycloak, SPIRE, workflow, and telemetry profiles

These checks separate repository evidence from tests that require the selected enterprise product.

### Mem0 adapter

```bash
helm template viewsense fabric/charts/viewsense \
  -f fabric/charts/viewsense/profiles/mem0-oss.yaml >/dev/null
kubectl -n viewsense-dev create secret generic mem0-credentials \
  --from-literal=api-key='replace-from-secret-manager' \
  --dry-run=client -o yaml
```

Before installation, deploy an authenticated Mem0 OSS REST server over HTTPS in the configured
`memory-platform` namespace and make its pod labels/port match `mem0.inCluster`. For a remote Mem0
endpoint disable `inCluster` and set explicit egress CIDRs. Run create/search through the ViewSense memory gateway, not
directly from applications. The conformance pass must cover missing/wrong API key, upstream timeout,
malformed response, tenant/owner isolation, limits, metadata, export/restore, and failure without
fallback. For Mem0 Platform use `mem0-platform-adapter`; the adapter translates `/v1` paths while the
ViewSense API remains unchanged.

### OPA

```bash
helm template viewsense fabric/charts/viewsense \
  -f fabric/charts/viewsense/profiles/enterprise-suite.yaml |
awk '/name: opa/{found=1} found{print} /name: opa-policy/{exit}'
```

In a test namespace, prove admission allow and deny, then stop OPA and prove provider admission
returns `503` rather than bypassing policy. Validate policy-bundle rollback and ensure inputs contain
metadata only. The supported chart profile embeds OPA beside governance. A remote OPA endpoint is a
future hardened profile because it also needs workload authentication, CA trust, explicit egress,
and equivalent outage evidence.

### Keycloak or another OIDC provider

Configure issuer, JWKS URL, audience, tenant claim, and scope claim. Test a valid user/service token,
then wrong issuer, wrong audience, missing `api.invoke`, missing tenant, disabled user, expired token,
key rotation, JWKS outage, and a token sent directly to an internal service. Only the valid edge
request may produce an internal Trust Envelope.

### SPIRE

The profile records workload-identity intent but does not install SPIRE. After installing the pinned
upstream hardened charts, validate:

```bash
kubectl get pods -A -l app.kubernetes.io/name=spire-server
kubectl get pods -A -l app.kubernetes.io/name=spire-agent
kubectl get csidriver
kubectl -n viewsense-dev get pod -o json |
jq -r '.items[].spec.serviceAccountName' | sort -u
```

Each workload must receive only its registered SPIFFE ID. Test SVID rotation, expired/unregistered
identity denial, trust-bundle rotation, server/agent restart, and direct pod traffic that bypasses the
SDS proxy/mesh. mTLS identity does not replace audience/scoped authorization.

### Workflows and observability

n8n, Temporal, and Argo selections currently record planned integration intent; installation is not
a workflow-adapter test. OpenTelemetry selection similarly identifies the expected collector. JSON
stdout is the validated baseline. Send logs through the chosen collector to Elastic/Splunk and prove
single-line JSON parsing, request correlation, Kubernetes metadata enrichment, redaction, backpressure,
and that tokens/prompts/memory/tool payloads are absent.

## 10. API schema and JSON logs

Download the live OpenAPI document:

```bash
curl --silent --show-error --fail \
  --cacert .viewsense/pki/smoke/ca.crt \
  --cert .viewsense/pki/smoke/tls.crt \
  --key .viewsense/pki/smoke/tls.key \
  https://localhost:9445/openapi.json |
jq '.info, .paths | keys'
```

Inspect correlated JSON logs without exposing request bodies:

```bash
kubectl logs -n viewsense-dev deployment/memory-gateway --tail=20
kubectl logs -n viewsense-dev deployment/memory-postgres --tail=20
```

## Scope and safety

- The `smoke` client, local issuer, static CA, mock providers, and deterministic embeddings are development-only.
- Do not expose identity, memory, model, MCP, or provider services through public ingress.
- Direct internal API tests use the fixed-tenant `smoke` identity. Unsigned tenant headers are rejected; public and internal tenant context comes from the signed Trust Envelope.
- Production validation additionally requires CNI negative connectivity tests, enterprise IdP/workload identity, external secret rotation, backup/restore, HA/failure exercises, and SIEM/OTel evidence.

## Validation evidence matrix

| Capability | Repository-validated | Requires selected environment |
|---|---|---|
| built-in agent | unit, Compose, Kubernetes state/approval/idempotency smoke | HA, restore, autonomous worker/tool replay |
| PostgreSQL/pgvector memory | unit, Compose, Kubernetes create/search | production scale, PITR, re-index |
| Mem0 | adapter normalization/security unit and Helm profile | live OSS/Platform conformance, backup/export, outage |
| OPA | fail-closed code path and sidecar profile rendering | live allow/deny/outage and bundle lifecycle |
| OIDC/Keycloak | verifier boundary and profile rendering | realm/claims, MFA/session/key rotation/outage |
| SPIRE | topology/profile/preflight documentation | live SVID/SDS rotation and spoof/expiry denial |
| workflows | catalog/profile intent only | adapter contract; no provider is validated yet |
| JSON logs | runtime and smoke inspection | OTel/Elastic/Splunk routing, alert and backpressure |
