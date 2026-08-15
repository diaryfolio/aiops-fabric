# ViewSense Test and Validation Guide

Run commands from the repository root. Development PKI and credentials are generated under `.viewsense/` and `.env.viewsense`; both are ignored by Git. Never reuse them outside the isolated development environment.

## 1. Static and unit validation

```bash
make lint
make unit
make catalog-check
helm lint fabric/charts/viewsense
kubectl kustomize deploy/kubernetes/base >/dev/null
```

Expected: Ruff succeeds, all Pytest tests pass, every `fabric/*` module descriptor resolves, Helm reports zero failures, and Kustomize renders without an error.

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

Expected: all Deployments and all three StatefulSets are ready, and `viewsense-smoke` completes successfully.

## 4. Direct memory API validation

The memory gateway is internal and uses both mutual TLS and an audience/scoped bearer token. Open two terminals and keep these processes running:

```bash
kubectl -n viewsense-dev port-forward service/identity 9444:8443
```

```bash
kubectl -n viewsense-dev port-forward service/memory-gateway 9445:8443
```

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

## 5. Provider governance and evidence API validation

Keep the identity port-forward from section 4 running and expose the governance API:

```bash
kubectl -n viewsense-dev port-forward service/governance 9446:8443
```

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

## 6. Negative authorization validation

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

## 7. API schema and JSON logs

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
