"""Run Claude vision analysis on an MMS-delivered image.

Twilio delivers media via HTTPS URLs that require basic auth with your Twilio credentials.
We fetch the bytes, base64-encode them, and hand them to Claude Sonnet.
"""
from __future__ import annotations

import base64
from typing import Any

import httpx
from anthropic import AsyncAnthropic

from .config import settings
from .prompts import vision_system_prompt


client = AsyncAnthropic(api_key=settings.anthropic_api_key)


async def fetch_twilio_media(media_url: str) -> tuple[bytes, str]:
    """Download a Twilio-hosted media URL and return (bytes, content_type)."""
    auth = (settings.twilio_account_sid, settings.twilio_auth_token)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as http:
        r = await http.get(media_url, auth=auth)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "image/jpeg")


async def analyze_image(image_bytes: bytes, media_type: str, caller_context: str = "") -> dict[str, Any]:
    """Ask Claude Sonnet to describe the plumbing issue in the image."""
    if media_type.startswith("video/"):
        # For the prototype we don't frame-extract; we note the limitation.
        return {
            "emergency": False,
            "issue_type": "video_unsupported",
            "description": "Video frames not extracted in prototype — ask customer to send a still photo.",
            "confidence": 0.0,
            "recommended_next_step": "Ask the customer to send a still photo instead of a video.",
            "safety_notes": "",
        }

    b64 = base64.standard_b64encode(image_bytes).decode("ascii")
    user_prefix = (
        f"Caller context (from voice transcript so far):\n{caller_context}\n\n"
        "Analyze this image and respond with the structured fields described in the system prompt."
        if caller_context
        else "Analyze this image and respond with the structured fields described in the system prompt."
    )

    resp = await client.messages.create(
        model=settings.vision_model,
        max_tokens=500,
        system=vision_system_prompt(),
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                    {"type": "text", "text": user_prefix},
                ],
            }
        ],
    )
    text = "".join(block.text for block in resp.content if block.type == "text")
    # Parse key/value lines emitted by the vision model into a dict.
    fields: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip().lstrip("-").strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        fields[k.strip().lower().replace(" ", "_")] = v.strip()
    fields.setdefault("raw", text)
    return fields
