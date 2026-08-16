from __future__ import annotations

import json
from pathlib import Path


def test_machine_readable_contracts_are_versioned_and_closed():
    root = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
    expected = {
        "agent-run-v1.schema.json",
        "evidence-event-v1.schema.json",
        "provider-passport-v1.schema.json",
        "trust-envelope-v1.schema.json",
    }
    assert {path.name for path in root.glob("*.json")} == expected
    for path in root.glob("*.json"):
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].endswith(path.name)
        assert schema["type"] == "object"
        assert schema["required"]
        assert schema["additionalProperties"] is False
