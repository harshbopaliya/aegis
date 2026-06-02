"""
Aegis backend adapters package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aegis.adapters.base import ApprovalQueue, ExecutionBackend, StorageBackend

_storage_backend: StorageBackend | None = None
_approval_queue: ApprovalQueue | None = None
_execution_backend: ExecutionBackend | None = None


def get_storage() -> StorageBackend:
    """Get the active storage backend, defaulting to SQLite."""
    global _storage_backend
    if _storage_backend is None:
        from aegis.adapters.sqlite import SQLiteStorageBackend

        _storage_backend = SQLiteStorageBackend()
    return _storage_backend


def set_storage(backend: StorageBackend) -> None:
    """Set the active storage backend."""
    global _storage_backend
    _storage_backend = backend


def get_approval_queue() -> ApprovalQueue:
    """Get the active approval queue backend, defaulting to SQLite/Memory."""
    global _approval_queue
    if _approval_queue is None:
        from aegis.adapters.sqlite import SQLiteApprovalQueue

        _approval_queue = SQLiteApprovalQueue()
    return _approval_queue


def set_approval_queue(queue: ApprovalQueue) -> None:
    """Set the active approval queue backend."""
    global _approval_queue
    _approval_queue = queue


def get_execution() -> ExecutionBackend:
    """Get the active execution backend, defaulting to SQLite/demo."""
    global _execution_backend
    if _execution_backend is None:
        from aegis.adapters.sqlite import SQLiteExecutionBackend

        _execution_backend = SQLiteExecutionBackend()
    return _execution_backend


def set_execution(backend: ExecutionBackend) -> None:
    """Set the active execution backend."""
    global _execution_backend
    _execution_backend = backend
