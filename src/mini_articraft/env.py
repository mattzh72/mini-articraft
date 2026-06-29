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
