"""Configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    vision_model: str = os.getenv("VISION_MODEL", "claude-sonnet-4-6")
    voice_model: str = os.getenv("VOICE_MODEL", "claude-sonnet-4-6")
    business_name: str = os.getenv("BUSINESS_NAME", "Your Plumbing Co.")
    business_hours: str = os.getenv("BUSINESS_HOURS", "Mon-Fri 8-6")
    after_hours_rate: str = os.getenv("AFTER_HOURS_RATE", "emergency rate")


settings = Settings()
