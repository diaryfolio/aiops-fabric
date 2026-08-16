# LLM Gateway Module

The LLM gateway provides the stable OpenAI-compatible inference boundary. Callers never receive provider URLs or credentials, so a local vLLM-class runtime and an approved external API remain interchangeable.

- Runtime: `viewsense_llm_gateway`
- Bundled test provider: `viewsense_mock_llm`
- Bundled credential-isolation adapter: `viewsense_openai_adapter` (OpenAI API)
- Helm selection: `products.llm`
- External endpoints require explicit HTTPS trust, audience grants, and fail-closed egress rules.

The OpenAI adapter is selected with `profiles/openai.yaml`. Only that pod receives the
`openai-credentials` Secret; it accepts the internal mTLS/scoped-token contract, fixes the configured
model server-side, minimizes outbound fields, and normalizes upstream errors without returning
credential-bearing diagnostics.
