from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    load_dotenv(find_dotenv(usecwd=True))


def getenv(name: str, default: str | None = None) -> str | None:
    load_env()
    return os.getenv(name, default)


def require_env(name: str) -> str:
    load_env()
    return os.environ[name]


def env_int(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    value = getenv(name)
    if value is None:
        return default
    return float(value)


def env_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")
