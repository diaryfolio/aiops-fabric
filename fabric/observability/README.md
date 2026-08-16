# Observability Module

The reference implements vendor-neutral JSON Lines runtime/request logs and `X-Request-ID`
propagation. It records inbound `traceparent` but does not propagate distributed traces. Production
metrics, tracing, immutable audit routing, buffering, redaction, and Elastic/Splunk exporters remain
collector/application integration work.

- Runtime foundation: `viewsense_common.logging`
- Helm selection: future observability overlay; no collector is bundled yet
- Production maturity requires backend ingestion, dashboards, alerts, audit evidence, and failure testing.
