import pytest

from app.config import settings
from app.core.db import init_database
from app.modules import backup_recovery, human_loop, observability
from app.modules.agents.repository import clear_all_for_tests as clear_agents
from app.modules.policy_engine.repository import clear_all_for_tests as clear_policies


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "sqlite_path", str(tmp_path / "gateway.db"))
    monkeypatch.setattr(settings, "log_dir", str(tmp_path / "logs"))
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "strict_block_delete_production", False)
    monkeypatch.setattr(settings, "audit_payload_mode", "full")
    human_loop.reset_state()
    observability.reset_pipeline_state_for_tests()
    backup_recovery.reset_snapshots()
    init_database()
    clear_agents()
    clear_policies()
    yield tmp_path
    human_loop.reset_state()
    observability.reset_pipeline_state_for_tests()
    backup_recovery.reset_snapshots()
    clear_agents()
    clear_policies()
