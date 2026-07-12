# Design 10.2 - Runtime Topology and Request Flow

## Runtime Topology

```mermaid
flowchart LR
    U[Enterprise User or App] --> G[API Gateway and Auth]
    G --> F

    subgraph F[Fabric Layer]
        O[AI Orchestrator]
        W[Workflow Engine]
        L[LLM Gateway and Inference]
        M[Memory and RAG]
        X[MCP Runtime]
    end

    O --> W
    O --> L
    O --> M
    W --> X
    X --> E[Enterprise Systems and APIs]

    SEC[Security and Zero Trust] -.-> O
    SEC -.-> W
    SEC -.-> L
    SEC -.-> M
    SEC -.-> X

    OBS[Observability] -.-> O
    OBS -.-> W
    OBS -.-> L
    OBS -.-> M
    OBS -.-> X
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
