# Observability and workflow integrations

JSON stdout remains mandatory and is immediately collectable by Elastic, Splunk, Fluent Bit, or
Vector. The OpenTelemetry profile expects an independently managed Collector/Operator and an OTLP
endpoint; direct backend SDKs remain prohibited.

n8n is best for SaaS connectors and human-facing low-code flows, Temporal for durable business
transactions, and Argo Workflows for Kubernetes batch/GPU jobs. They remain behind the ViewSense
start/status/signal/cancel contract and must use the MCP/policy boundaries for consequential tools.
The current durable built-in agent runtime is executable; workflow-provider adapters remain planned
until their provider conformance suites are implemented.
