"""Attendance MCP's public application entry point."""

from attendance_mcp.app import create_app


def main() -> None:
    """Run the Streamable HTTP adapter."""
    import uvicorn

    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
