"""Observability — structured audit trail and pipeline tracking."""

from aegis.modules.observability.service import (
    dashboard_stats,
    emit,
    events_for_request,
    get_pipeline,
    list_active_pipelines,
    module_outputs_for_request,
    new_request_id,
    pipeline_advance,
    pipeline_set_status,
    pipeline_start,
    pipeline_touch_approval_wait,
    recent_completed,
    recent_events,
    reset_pipeline_state_for_tests,
)

__all__ = [
    "dashboard_stats",
    "emit",
    "events_for_request",
    "get_pipeline",
    "list_active_pipelines",
    "module_outputs_for_request",
    "new_request_id",
    "pipeline_advance",
    "pipeline_set_status",
    "pipeline_start",
    "pipeline_touch_approval_wait",
    "recent_completed",
    "recent_events",
    "reset_pipeline_state_for_tests",
]
