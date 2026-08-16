# LLM Gateway Module

The LLM gateway provides the stable OpenAI-compatible inference boundary. Callers never receive
provider URLs or credentials. The deterministic mock and credential-isolated OpenAI adapter are
executable; local vLLM/Ollama and other external providers require adapters that remain planned.

- Runtime: `viewsense_llm_gateway`
- Bundled test provider: `viewsense_mock_llm`
- Bundled credential-isolation adapter: `viewsense_openai_adapter` (OpenAI API)
- Helm selection: `products.llm`
- Planned external endpoints require a ViewSense-compatible mTLS/JWT adapter, explicit HTTPS trust,
  audience grants, and fail-closed egress rules. A vanilla OpenAI-compatible endpoint is not enough.

The OpenAI adapter is selected with `profiles/openai.yaml`. Only that pod receives the
`openai-credentials` Secret; it accepts the internal mTLS/scoped-token contract, fixes the configured
model server-side, minimizes outbound fields, and normalizes upstream errors without returning
credential-bearing diagnostics.
