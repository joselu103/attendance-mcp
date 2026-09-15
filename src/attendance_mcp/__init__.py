"""Attendance MCP's public application entry point."""

from attendance_mcp.app import create_app
from attendance_mcp.logging import configure_logging, uvicorn_log_config
from attendance_mcp.settings import Settings


def main() -> None:
    """Run the Streamable HTTP adapter."""
    import uvicorn

    settings = Settings()
    configure_logging(
        environment=settings.runtime_environment,
        external_debug=settings.log_external_debug,
        sensitive_keys=settings.log_redacted_keys,
        sensitive_values=(
            value.get_secret_value() for value in settings.log_redacted_values
        ),
    )
    uvicorn.run(
        create_app(settings),
        host="0.0.0.0",
        port=8000,
        log_config=uvicorn_log_config(external_debug=settings.log_external_debug),
    )
