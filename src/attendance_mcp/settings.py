"""Non-secret runtime configuration for the stateless adapter."""

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings owned by the adapter, never delegated credentials."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ATTENDANCE_MCP_",
        extra="ignore",
    )

    crmt_base_url: AnyHttpUrl = Field(description="Attendance CRMT REST base URL")
    request_timeout_seconds: float = Field(default=10, gt=0, le=30)
    runtime_environment: str = "development"
    log_redacted_keys: list[str] = Field(default_factory=list)
    log_redacted_values: list[SecretStr] = Field(default_factory=list)
