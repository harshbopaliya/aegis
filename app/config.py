from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Fail-safe defaults: block when uncertain."""

    model_config = SettingsConfigDict(
        env_prefix="ASG_",
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Canonical name for OpenAI: OPENAI_API_KEY (shell or project-root .env).
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"

    log_dir: str = "logs"
    data_dir: str = "data"
    sqlite_path: str = "data/gateway.db"
    backup_dir: str = "data/backups"

    # When True, DELETE in production is a hard policy block (skip downstream simulation).
    strict_block_delete_production: bool = False
    risk_threshold_approval: int = 70
    sensitive_tables: frozenset[str] = frozenset({"users", "payments", "audit_log", "production_orders"})

    # Multi-agent: when True, POST /v1/actions must use an agent_id registered via /v1/agents.
    require_agent_registration: bool = False
    # When True, the registered agent row's role overrides the client-supplied role (recommended for prod).
    enforce_agent_roles_from_registry: bool = False

    # Audit: full (dev), redact (default pilot), encrypt (requires fernet_key).
    audit_payload_mode: str = "redact"
    # Only enable on locked-down ops workstations — allows decrypting encrypted audit blobs in the UI.
    audit_decrypt_allowed: bool = False

    # Fernet key (generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    fernet_key: str | None = None

    # Copy SQLite to backup_dir; optionally encrypt file at rest (requires fernet_key).
    encrypt_backup_files: bool = False


settings = Settings()
