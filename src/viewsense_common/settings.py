from __future__ import annotations

import os
from pathlib import Path


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def read_required(name: str) -> str:
    return Path(required(name)).read_text(encoding="utf-8")


def csv(name: str, default: str = "") -> set[str]:
    return {item.strip() for item in os.getenv(name, default).split(",") if item.strip()}
