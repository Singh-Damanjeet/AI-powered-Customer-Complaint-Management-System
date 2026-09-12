"""Errors used by AI-powered complaint processing services."""


class AIResponseValidationError(RuntimeError):
    """Raised when structured AI output remains invalid after retrying."""


__all__ = ["AIResponseValidationError"]
