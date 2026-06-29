from __future__ import annotations

from dotenv import find_dotenv, load_dotenv


def load_env() -> None:
    load_dotenv(find_dotenv(usecwd=True))
