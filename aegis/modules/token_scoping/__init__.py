"""Token scoping — RBAC and agent registry resolution."""

from aegis.modules.token_scoping.service import evaluate, resolve_registry

__all__ = ["evaluate", "resolve_registry"]
