from __future__ import annotations


class MiniArticraftError(Exception):
    """Base error for mini-articraft."""


class SDKError(MiniArticraftError):
    """Base error for the mini-articraft SDK."""


class ValidationError(SDKError):
    """Raised when an articulated object definition is invalid."""


class ModelError(MiniArticraftError):
    """Raised when the model response cannot be used."""
