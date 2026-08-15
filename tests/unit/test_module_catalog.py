from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_ROOT = REPO_ROOT / "fabric"
EXPECTED_MODULES = {
    "agents",
    "core",
    "governance",
    "identity",
    "ingestion",
    "llm",
    "mcp-registry",
    "memory",
    "observability",
    "workflows",
}
MATURITY = {"implemented-reference", "partial-reference", "contract-only"}
PROVIDER_STATUS = {"bundled", "external", "planned"}
HELM_ROOTS = {"products", "modules", "datastores", "networkPolicy", "global"}


def test_module_catalog_is_complete_and_resolves_repository_paths():
    json.loads((CATALOG_ROOT / "module.schema.json").read_text(encoding="utf-8"))
    actual_modules = {
        path.name for path in CATALOG_ROOT.iterdir() if path.is_dir() and path.name != "charts"
    }
    assert actual_modules == EXPECTED_MODULES

    for name in sorted(EXPECTED_MODULES):
        module_dir = CATALOG_ROOT / name
        readme = module_dir / "README.md"
        manifest = module_dir / "module.json"
        assert readme.is_file() and readme.stat().st_size > 100, name
        assert manifest.is_file(), name

        document = json.loads(manifest.read_text(encoding="utf-8"))
        assert document["apiVersion"] == "fabric.viewsense.io/v1alpha1"
        assert document["kind"] == "Module"
        assert document["metadata"]["name"] == name
        assert document["metadata"]["title"]

        spec = document["spec"]
        assert set(spec) == {
            "maturity",
            "implementationPaths",
            "contractPaths",
            "helmPaths",
            "dataOwnership",
            "providers",
        }
        assert spec["maturity"] in MATURITY
        assert spec["contractPaths"]
        assert spec["dataOwnership"]
        assert spec["providers"]
        if spec["maturity"] == "implemented-reference":
            assert spec["implementationPaths"], name
        if spec["maturity"] == "contract-only":
            assert not spec["implementationPaths"], name

        for repository_path in spec["implementationPaths"] + spec["contractPaths"]:
            assert (REPO_ROOT / repository_path).is_file(), f"{name}: {repository_path}"
        for helm_path in spec["helmPaths"]:
            assert helm_path.split(".", 1)[0] in HELM_ROOTS, f"{name}: {helm_path}"
        for provider in spec["providers"]:
            assert set(provider) == {"name", "status"}
            assert provider["name"]
            assert provider["status"] in PROVIDER_STATUS
