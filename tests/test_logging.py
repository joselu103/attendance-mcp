import asyncio
import logging
from uuid import UUID

import httpx
import structlog

from attendance_mcp.app import create_app
from attendance_mcp.logging import (
    REDACTED,
    _redactor,
    configure_logging,
    uvicorn_log_config,
)
from attendance_mcp.settings import Settings


def test_local_logging_uses_debug_console_renderer_and_quiet_external_logs() -> None:
    configure_logging(environment="development")

    config = structlog.get_config()

    assert logging.getLogger().level == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("fastmcp").getEffectiveLevel() == logging.WARNING
    assert type(config["processors"][-1]) is structlog.dev.ConsoleRenderer
    assert config["processors"][-1]._colors is True


def test_non_local_logging_uses_info_json_renderer() -> None:
    configure_logging(environment="production")

    config = structlog.get_config()

    assert logging.getLogger().level == logging.WARNING
    assert type(config["processors"][-1]) is structlog.processors.JSONRenderer


def test_external_debug_opt_in_enables_external_loggers() -> None:
    configure_logging(environment="development", external_debug=True)

    assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.DEBUG
    assert logging.getLogger("fastmcp").getEffectiveLevel() == logging.DEBUG


def test_uvicorn_config_keeps_access_logs_and_quiets_framework_logs() -> None:
    config = uvicorn_log_config(external_debug=False)

    assert config["loggers"]["uvicorn"]["level"] == "WARNING"
    assert config["loggers"]["uvicorn.error"]["level"] == "WARNING"
    assert config["loggers"]["uvicorn.access"]["level"] == "INFO"


async def _context() -> dict[str, object]:
    return structlog.contextvars.get_contextvars()


def test_standard_metadata_and_context_flow_across_async_work_then_clear() -> None:
    configure_logging(environment="production")
    processors = structlog.get_config()["processors"][:-1]

    async def emit() -> dict[str, object]:
        event: dict[str, object] = {"event": "completed"}
        structlog.contextvars.bind_contextvars(correlation_id="correlation-1")
        assert (await asyncio.create_task(_context())) == {
            "correlation_id": "correlation-1"
        }
        for processor in processors:
            event = processor(None, "info", event)
        structlog.contextvars.clear_contextvars()
        return event

    result = asyncio.run(emit())

    assert result["correlation_id"] == "correlation-1"
    assert result["level"] == "info"
    assert result["timestamp"].endswith("Z")
    assert {"module", "func_name", "lineno"}.issubset(result)
    assert structlog.contextvars.get_contextvars() == {}


def test_request_lifecycle_logs_safe_health_events_with_a_generated_trace_id(
    monkeypatch,
) -> None:
    events: list[tuple[str, str, dict[str, object]]] = []

    class CapturingLogger:
        def info(self, event: str, **values: object) -> None:
            events.append(("info", event, values))

        def warning(self, event: str, **values: object) -> None:
            events.append(("warning", event, values))

        def exception(self, event: str, **values: object) -> None:
            events.append(("exception", event, values))

    monkeypatch.setattr("attendance_mcp.http_lifecycle.logger", CapturingLogger())

    async def exercise() -> None:
        app = create_app(Settings(crmt_base_url="https://crmt.example"))
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="https://mcp.example"
            ) as client,
        ):
            response = await client.get("/health")
        assert response.status_code == 200

    asyncio.run(exercise())

    assert [(level, event) for level, event, _ in events] == [
        ("info", "http_request_received"),
        ("info", "http_request_completed"),
    ]
    trace_id = events[0][2]["trace_id"]
    assert isinstance(trace_id, str)
    assert UUID(trace_id)
    assert events[0][2] == {"route": "/health", "trace_id": trace_id}
    assert events[1][2]["route"] == "/health"
    assert events[1][2]["trace_id"] == trace_id
    assert events[1][2]["result_state"] == "completed"
    assert events[1][2]["status_code"] == 200
    assert isinstance(events[1][2]["duration_ms"], int)


def test_redaction_is_recursive_and_does_not_mutate_caller_data() -> None:
    value = {
        "Authorization": "Bearer delegated-token",
        "nested": [{"custom-secret": "value"}, "visible configured-value"],
    }

    redacted = _redactor(["custom-secret"], ["configured-value"])(None, "info", value)

    assert redacted == {
        "Authorization": REDACTED,
        "nested": [{"custom-secret": REDACTED}, f"visible {REDACTED}"],
    }
    assert value["Authorization"] == "Bearer delegated-token"
    assert value["nested"][0]["custom-secret"] == "value"


def test_redaction_applies_to_formatted_exceptions() -> None:
    configure_logging(environment="production", sensitive_values=["secret-value"])
    processors = structlog.get_config()["processors"][:-1]
    try:
        raise RuntimeError("secret-value")
    except RuntimeError:
        event: dict[str, object] = {"event": "failed", "exc_info": True}
        for processor in processors:
            event = processor(None, "error", event)

    assert "secret-value" not in event["exception"]
    assert REDACTED in event["exception"]
