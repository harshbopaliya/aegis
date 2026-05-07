from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Production-grade configuration with fail-safe defaults.
    
    All security-sensitive operations default to deny/block.
    Override via environment variables with ASG_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="ASG_",
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== Application Settings ==========
    app_name: str = "Aegis"
    app_version: str = "1.0.0"
    environment: str = Field(default="production", description="Environment: development, staging, production")
    debug: bool = False
    
    # ========== Server Settings ==========
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    request_timeout: int = 30
    keepalive_timeout: int = 65

    # ========== CORS & Security ==========
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    trusted_hosts: str = "localhost,127.0.0.1"
    require_https: bool = Field(default=True, description="Enforce HTTPS in production")
    cors_max_age: int = 600

    # ========== OpenAI Configuration ==========
    openai_api_key: str | None = Field(default=None, description="OpenAI API key for AI agent demo (get from https://platform.openai.com/api-keys)")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use for agent")
    openai_timeout: int = 60

    # ========== Paths & Storage ==========
    log_dir: str = "logs"
    data_dir: str = "data"
    sqlite_path: str = "data/gateway.db"
    backup_dir: str = "data/backups"
    
    # ========== Logging ==========
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_format: str = Field(default="json", description="Log format: json or standard")
    
    # ========== Safety Policy Settings ==========
    # When True, DELETE in production is a hard policy block (skip downstream simulation).
    strict_block_delete_production: bool = True
    risk_threshold_approval: int = 70
    sensitive_tables: frozenset[str] = frozenset({
        "users",
        "payments", 
        "audit_log",
        "production_orders",
        "api_keys",
        "credentials",
        "secrets",
    })

    # ========== Agent Management ==========
    # Multi-agent: when True, POST /v1/actions must use an agent_id registered via /v1/agents.
    require_agent_registration: bool = True
    # When True, the registered agent row's role overrides the client-supplied role (recommended for prod).
    enforce_agent_roles_from_registry: bool = True
    max_agents: int = 100

    # ========== Approval & HITL ==========
    human_approval_timeout_seconds: int = 3600
    require_approval_on_high_risk: bool = True
    approval_escalation_levels: int = 2

    # ========== Audit & Observability ==========
    # Audit modes: full (dev), redact (default), encrypt (requires fernet_key)
    audit_payload_mode: str = Field(default="redact", description="Audit mode: full, redact, encrypt")
    # Only enable on locked-down ops workstations
    audit_decrypt_allowed: bool = False
    audit_retention_days: int = 365
    max_audit_events_in_memory: int = 10000

    # ========== Encryption ==========
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    fernet_key: str | None = None
    encrypt_backup_files: bool = True
    encrypt_database: bool = False

    # ========== Rate Limiting ==========
    enable_rate_limiting: bool = True
    rate_limit_requests_per_minute: int = 1000
    rate_limit_actions_per_minute: int = 100

    # ========== Database ==========
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False  # Set to True only in development

    # ========== Backup & Recovery ==========
    enable_auto_backup: bool = True
    backup_interval_hours: int = 6
    backup_retention_days: int = 30
    max_backup_files: int = 120

    # ========== Validation ==========
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in {"development", "staging", "production"}:
            raise ValueError("environment must be one of: development, staging, production")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of: {valid_levels}")
        return v.upper()

    @field_validator("audit_payload_mode")
    @classmethod
    def validate_audit_mode(cls, v: str) -> str:
        if v not in {"full", "redact", "encrypt"}:
            raise ValueError("audit_payload_mode must be one of: full, redact, encrypt")
        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Validate encryption configuration
        if self.audit_payload_mode == "encrypt" and not self.fernet_key:
            raise ValueError("fernet_key required when audit_payload_mode is 'encrypt'")
        if self.encrypt_backup_files and not self.fernet_key:
            raise ValueError("fernet_key required when encrypt_backup_files is True")
        # Production security checks
        if self.environment == "production":
            if self.debug:
                raise ValueError("debug mode not allowed in production")
            if self.require_https is False:
                raise ValueError("require_https must be True in production")


settings = Settings()
