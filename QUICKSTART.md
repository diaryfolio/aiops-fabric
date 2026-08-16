# ViewSense Quick Start

This guide covers the development lifecycle: install once, start an existing cluster, enable an
OpenAI provider without rebuilding everything, expose APIs locally, test the suite, and stop it
without losing data.

Run every command from the repository root.

## Prerequisites

Install Docker, `kubectl`, `k3d`, Helm, `curl`, and `jq`. Docker must be running.

```bash
docker info >/dev/null
kubectl version --client
k3d version
helm version --short
```

## Which command do I need?

| Situation | Command | Effect |
|---|---|---|
| first installation | `make k8s-deploy` | builds/imports images and installs `viewsense-dev` |
| normal daily use | no deployment command | Kubernetes workloads remain running |
| cluster exists but is stopped | `k3d cluster start cks` | starts the existing cluster and retained data |
| application or manifests changed | `make k8s-deploy` | rebuilds and rolls out the development suite |
| run automated integration test | `make k8s-test` | runs the namespaced smoke Job |
| enable OpenAI on an installed suite | `make openai-enable` | prompts for the key and switches the LLM route |
| rebuild and then enable OpenAI | `make openai-enable-fresh` | full deployment followed by secure configuration |
| expose APIs on localhost | `make ports-start` | starts the five managed port-forwards |
| stop local API access | `make ports-stop` | stops only the port-forwards; workloads keep running |

## First installation

Create the development cluster only if `cks` is not already listed:

```bash
k3d cluster list
k3d cluster create cks --agents 1
kubectl config use-context k3d-cks
make k8s-deploy
make k8s-test
```

`make k8s-deploy` is intentionally a full installation/update. Messages about pulling PostgreSQL
images, creating `k3d-cks-tools`, and importing images are expected. The tools node is temporary and
lets k3d copy local Docker images into the Kubernetes nodes. This is not an OpenAI model download.

Do not run `k3d cluster create` when `cks` already exists. Use the daily startup procedure instead.

## Normal daily startup

Docker and the k3d cluster may already be running. Check before starting anything:

```bash
k3d cluster list
kubectl config current-context
kubectl -n viewsense-dev get pods
```

Expected: cluster `cks` shows its server/agent running, the context is `k3d-cks`, and application
pods show `Running` with ready containers. A completed `viewsense-smoke` pod is normal.

If `cks` exists but is stopped:

```bash
k3d cluster start cks
kubectl config use-context k3d-cks
kubectl -n viewsense-dev wait --for=condition=Available deployment --all --timeout=180s
```

Kubernetes restarts the existing workloads. You do not need `make k8s-deploy`, and database volumes
remain attached to the existing cluster.

## Enable OpenAI securely

On an already installed suite, run:

```bash
make openai-enable
```

Enter the API key at the hidden prompt. Do not put it in the command, an environment file, Helm
values, documentation, chat, or Git. The setup script pipes it directly to the namespaced
`openai-credentials` Secret. Only `openai-adapter` references that Secret.

Set a non-secret model choice separately if required:

```bash
VS_OPENAI_MODEL=gpt-4.1-mini make openai-enable
```

Use `make openai-enable-fresh` only when the ViewSense image or Kubernetes resources also need to be
rebuilt. Normal key or model configuration does not need an image import.

Confirm configuration without displaying the Secret value:

```bash
kubectl -n viewsense-dev get deployment openai-adapter
kubectl -n viewsense-dev get secret openai-credentials \
  -o jsonpath='{.metadata.name}{" configured\n"}'
kubectl -n viewsense-dev get deployment llm-gateway \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="VS_LLM_PROVIDER_AUDIENCE")].value}{"\n"}'
```

Expected provider audience: `openai-adapter`. Do not print the Secret with `-o yaml` or decode its
data fields.

## Expose the development APIs

Start all forwards in the background:

```bash
make ports-start
make ports-status
```

| API | Local endpoint |
|---|---|
| public gateway | `https://127.0.0.1:9443` |
| development identity | `https://127.0.0.1:9444` |
| memory gateway | `https://127.0.0.1:9445` |
| governance | `https://127.0.0.1:9446` |
| agent runtime | `https://127.0.0.1:9447` |

For a foreground session where `Ctrl+C` stops every forward:

```bash
make ports
```

## Test ViewSense

Run the automated Kubernetes smoke test:

```bash
make k8s-test
```

Expected final output:

```text
ViewSense end-to-end smoke tests passed
```

With the default route, the smoke test uses the deterministic mock LLM. With the OpenAI route
enabled, inference steps use the configured OpenAI account and may incur API charges.

For the copy-and-paste API test that writes a harmless memory and then asks OpenAI a curl prompt
whose answer must use that memory, follow
[Real OpenAI memory-grounding validation](tests/README.md#5-real-openai-memory-grounding-validation).
The same test guide contains direct memory, durable-agent, governance, negative-authorization, and
observability checks.

## Stop or pause

Stop only the localhost forwards while leaving ViewSense live:

```bash
make ports-stop
```

Return to the mock LLM and delete the development OpenAI Secret:

```bash
make openai-disable
```

Pause the whole development cluster while retaining its workloads and volumes:

```bash
k3d cluster stop cks
```

Resume it later with `k3d cluster start cks`. Do not delete the cluster unless you intentionally
want to remove its Kubernetes resources and cluster-managed data.

## Troubleshooting

```bash
kubectl config current-context
k3d cluster list
kubectl -n viewsense-dev get pods
kubectl -n viewsense-dev get events --sort-by=.lastTimestamp
kubectl -n viewsense-dev logs deployment/llm-gateway --tail=50
kubectl -n viewsense-dev logs deployment/openai-adapter --tail=50
scripts/port-forward-dev.sh logs
```

- Wrong context: run `kubectl config use-context k3d-cks`.
- `viewsense-dev` missing: perform the first installation.
- Local port already in use: stop older manual `kubectl port-forward` processes before starting the
  managed forwarder.
- OpenAI `401`/`403`: rotate or correct the provider key, then rerun `make openai-enable`.
- OpenAI `429`: check project quota, rate limits, and spend controls; ViewSense will not silently
  fall back to a different provider.

This development setup uses local PKI, a development issuer, single replicas, and Kubernetes
Secrets. Production requires enterprise identity, external secret management, constrained egress,
high availability, backups, policy admission, and the controls in the
[technical guide](TECHNICAL_README.md).
