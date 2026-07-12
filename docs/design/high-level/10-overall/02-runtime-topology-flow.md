# Design 10.2 - Runtime Topology and Request Flow

## Runtime Topology

```mermaid
flowchart LR
    U[Enterprise User / App / Agent] --> IGW[Ingress + API Gateway\nOIDC/OAuth2 + WAF + Rate Limits]
    IGW --> ORCH[AI Orchestrator API\nSession, Policy, Routing]

    ORCH --> WF[Workflow Engine\nn8n or Tines]
    ORCH --> MEM[Context Service\nRAG + Memory Policies]
    ORCH --> LLMGW[LLM Gateway\nOpenAI-Compatible API]

    WF --> MCPRT[MCP Runtime Layer\nHosted MCP Servers]
    MCPRT --> DS[Enterprise Systems\nDBs, SaaS, Internal APIs]

    MEM --> VDB[Vector DB Cluster\nQdrant/Milvus/pgvector]
    MEM --> META[Metadata + Catalog Store\nPostgreSQL/Object Store]
    MEM --> REDIS[Redis Cache\nContext + Embeddings Cache]

    LLMGW --> INF[Inference Layer\nvLLM/Ollama/Triton]
    INF --> GPU[GPU Node Pools\nKEDA/Knative Autoscaling]

    ORCH --> MQ[Queue Bus\nNATS/Kafka/RabbitMQ]
    WF --> MQ
    MEM --> MQ
```

## End-to-End Request Flow

1. User or application authenticates via enterprise IdP and enters through API gateway.
2. Gateway validates token, tenant scope, and policy controls.
3. Orchestrator routes request by model, workflow, and policy.
4. Workflow engine executes deterministic logic and tool loops.
5. Context service performs retrieval and context assembly.
6. LLM gateway normalizes and routes inference request.
7. Inference layer streams response and returns control to orchestrator.
8. Async telemetry and persistence are emitted through queue and storage paths.

## Decoupling Constraints

- No direct cross-service database reads.
- API and event contracts only between domains.
- Async message bus for non-blocking side effects.
