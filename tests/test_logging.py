import asyncio
import logging

import structlog
from starlette.types import Message, Receive, Scope, Send

from attendance_mcp.app import _RequestLoggingMiddleware
from attendance_mcp.logging import REDACTED, _redactor, configure_logging


def test_local_logging_uses_debug_console_renderer() -> None:
    configure_logging(environment="development")

    config = structlog.get_config()

    assert logging.getLogger().level == logging.DEBUG
    assert type(config["processors"][-1]) is structlog.dev.ConsoleRenderer
    assert config["processors"][-1]._colors is True


def test_non_local_logging_uses_info_json_renderer() -> None:
    configure_logging(environment="production")

    config = structlog.get_config()

    assert logging.getLogger().level == logging.INFO
    assert type(config["processors"][-1]) is structlog.processors.JSONRenderer


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


async def _context() -> dict[str, object]:
    return structlog.contextvars.get_contextvars()


def test_request_middleware_clears_context_between_requests() -> None:
    seen: list[dict[str, object]] = []

    async def application(_: Scope, __: Receive, send: Send) -> None:
        seen.append(structlog.contextvars.get_contextvars())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def call(headers: list[tuple[bytes, bytes]]) -> None:
        scope: Scope = {"type": "http", "headers": headers}

        async def receive() -> Message:
            return {"type": "http.disconnect"}

        async def send(_: Message) -> None:
            return None

        await _RequestLoggingMiddleware(application)(scope, receive, send)

    async def exercise() -> None:
        await call([(b"x-correlation-id", b"11111111-1111-1111-1111-111111111111")])
        await call([])

    asyncio.run(exercise())

    assert seen == [{"correlation_id": "11111111-1111-1111-1111-111111111111"}, {}]
    assert structlog.contextvars.get_contextvars() == {}


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
