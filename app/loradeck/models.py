from __future__ import annotations

from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gateway_url: str = Field(default="", max_length=300)
    poll_interval: int = Field(default=60, ge=15, le=3600)

    @field_validator("gateway_url")
    @classmethod
    def validate_gateway_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            return ""
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("gateway_url muss eine absolute http(s)-URL sein")
        if parsed.username or parsed.password:
            raise ValueError("gateway_url darf keine Zugangsdaten enthalten")
        if parsed.query or parsed.fragment:
            raise ValueError("gateway_url darf keine Query oder Fragment enthalten")
        if parsed.path not in {"", "/"}:
            raise ValueError("gateway_url darf keinen Pfad enthalten")
        return value.rstrip("/")
