# Observability Module

The reference implements vendor-neutral JSON Lines runtime/request logs and correlation propagation. Production metrics, distributed traces, immutable audit routing, buffering, redaction, and Elastic/Splunk exporters belong in an OTel-compatible collector layer.

- Runtime foundation: `viewsense_common.logging`
- Helm selection: future observability overlay; no collector is bundled yet
- Production maturity requires backend ingestion, dashboards, alerts, audit evidence, and failure testing.
