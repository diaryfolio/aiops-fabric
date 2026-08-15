{{- define "viewsense.labels" -}}
app.kubernetes.io/part-of: viewsense
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "viewsense.moduleEnabled" -}}
{{- $name := index . 0 -}}
{{- $module := index . 1 -}}
{{- $root := index . 2 -}}
{{- if and $module.enabled (or (ne $name "identity") (eq $root.Values.products.identity.product "development")) (or (ne $name "mock-llm") (eq $root.Values.products.llm.product "mock-openai-compatible")) (or (ne $name "memory-postgres") (eq $root.Values.products.memory.product "postgres-pgvector")) (or (ne $name "mock-mcp") $root.Values.products.mcp.mockProviderEnabled) -}}true{{- else -}}false{{- end -}}
{{- end }}

{{- define "viewsense.destinationEnabled" -}}
{{- $destination := index . 0 -}}
{{- $root := index . 1 -}}
{{- if or (and (eq $destination "mock-llm") (ne $root.Values.products.llm.product "mock-openai-compatible")) (and (eq $destination "memory-postgres") (ne $root.Values.products.memory.product "postgres-pgvector")) -}}false{{- else -}}true{{- end -}}
{{- end }}
