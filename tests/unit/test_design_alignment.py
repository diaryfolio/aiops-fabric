from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN_ROOT = REPO_ROOT / "docs/design/high-level"
CONFORMANCE = DESIGN_ROOT / "00-implementation-conformance.md"
ROUTE_PATTERN = re.compile(
    r'@app\.(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']'
)


def test_implementation_conformance_lists_every_runtime_route():
    documented = CONFORMANCE.read_text(encoding="utf-8")
    discovered: set[str] = set()
    for source in (REPO_ROOT / "src").glob("viewsense_*/app.py"):
        discovered.update(ROUTE_PATTERN.findall(source.read_text(encoding="utf-8")))
    discovered.discard("/healthz")
    assert discovered
    assert not {route for route in discovered if route not in documented}


def test_every_high_level_design_uses_balanced_mermaid():
    for document in DESIGN_ROOT.rglob("*.md"):
        text = document.read_text(encoding="utf-8")
        assert "```mermaid" in text, document
        in_fence = False
        mermaid_fences = 0
        for line in text.splitlines():
            if line == "```mermaid" and not in_fence:
                in_fence = True
                mermaid_fences += 1
            elif line == "```" and in_fence:
                in_fence = False
        assert mermaid_fences >= 1, document
        assert not in_fence, document


def test_unshipped_integrations_are_not_claimed_ready():
    catalog = json.loads(
        (REPO_ROOT / "fabric/product-catalog.json").read_text(encoding="utf-8")
    )
    products = {product["id"]: product for product in catalog["products"]}
    for product_id in {
        "spire",
        "vllm",
        "openai-compatible-external",
        "unstructured-compatible-external",
        "mcp-streamable-http-adapter",
        "n8n",
        "temporal",
        "argo-workflows",
    }:
        assert products[product_id]["readiness"] == "planned", product_id
    assert products["otel-collector"]["readiness"] == "configuration-ready"
    assert "native application OTLP export is planned" in products["otel-collector"]["notes"]


def test_network_policy_does_not_allow_unused_runtime_edges():
    policies = (REPO_ROOT / "deploy/kubernetes/base/network-policies.yaml").read_text(
        encoding="utf-8"
    )
    gateway = policies.split("name: gateway-policy", 1)[1].split("---", 1)[0]
    orchestrator = policies.split("name: orchestrator-policy", 1)[1].split("---", 1)[0]
    assert "app.kubernetes.io/name: ingestion" not in gateway
    assert "app.kubernetes.io/name: mcp-gateway" not in orchestrator

    values = (REPO_ROOT / "fabric/charts/viewsense/values.yaml").read_text(encoding="utf-8")
    orchestrator_values = values.split("  orchestrator:", 1)[1].split("  governance:", 1)[0]
    assert "mcp-gateway" not in orchestrator_values
