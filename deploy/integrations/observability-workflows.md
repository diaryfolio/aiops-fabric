# Observability and workflow integrations

JSON stdout remains mandatory and is immediately collectable by Elastic, Splunk, Fluent Bit,
Vector, or an OpenTelemetry Collector. The Helm `otlpEndpoint` value is reserved intent and is not
consumed by the current applications; native OTLP metrics/traces remain planned. Direct backend
SDKs remain prohibited.

n8n is best for SaaS connectors and human-facing low-code flows, Temporal for durable business
transactions, and Argo Workflows for Kubernetes batch/GPU jobs. They remain behind the ViewSense AI®
start/status/signal/cancel contract and must use the MCP/policy boundaries for consequential tools.
The current durable built-in agent runtime is executable; workflow-provider adapters remain planned
until their provider conformance suites are implemented.
