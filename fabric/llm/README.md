# LLM Gateway Module

The LLM gateway provides the stable OpenAI-compatible inference boundary. Callers never receive provider URLs or credentials, so a local vLLM-class runtime and an approved external API remain interchangeable.

- Runtime: `viewsense_llm_gateway`
- Bundled test provider: `viewsense_mock_llm`
- Helm selection: `products.llm`
- External endpoints require explicit HTTPS trust, audience grants, and fail-closed egress rules.
