"""Safe, correlation-aware structured logging for the adapter runtime."""

import logging
import sys
from collections.abc import Iterable, Mapping
from typing import Any

import structlog

REDACTED = "[REDACTED]"
DEFAULT_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "password",
        "secret",
        "client_secret",
        "api_key",
        "cookie",
        "set_cookie",
    }
)


def configure_logging(
    *,
    environment: str,
    sensitive_keys: Iterable[str] = (),
    sensitive_values: Iterable[str] = (),
) -> None:
    """Configure deterministic, safe output for the active runtime environment."""
    is_local = environment.casefold() in {"local", "development"}
    level = logging.DEBUG if is_local else logging.INFO
    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_local
        else structlog.processors.JSONRenderer()
    )
    processors = _shared_processors(sensitive_keys, sensitive_values) + [renderer]
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=level, force=True
    )
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )


def _shared_processors(
    sensitive_keys: Iterable[str], sensitive_values: Iterable[str]
) -> list[structlog.types.Processor]:
    redact = _redactor(sensitive_keys, sensitive_values)
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.MODULE,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
        structlog.processors.format_exc_info,
        redact,
    ]


def _redactor(
    sensitive_keys: Iterable[str], sensitive_values: Iterable[str]
) -> structlog.types.Processor:
    keys = DEFAULT_SENSITIVE_KEYS | {
        _normalise_key(key) for key in sensitive_keys if key.strip()
    }
    values = tuple(value for value in sensitive_values if value)

    def redact(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return _redact(event_dict, keys, values)

    return redact


def _redact(value: Any, keys: frozenset[str], sensitive_values: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED
            if isinstance(key, str) and _normalise_key(key) in keys
            else _redact(item, keys, sensitive_values)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, keys, sensitive_values) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item, keys, sensitive_values) for item in value)
    if isinstance(value, str):
        for sensitive_value in sensitive_values:
            value = value.replace(sensitive_value, REDACTED)
    return value


def _normalise_key(key: str) -> str:
    return key.casefold().replace("-", "_")
