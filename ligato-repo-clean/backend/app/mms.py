"""MMS send/receive. Twilio is the carrier.

MMS is strictly a media channel in the Ligato Vision product:
- Outbound: one-line prompts from the voice agent asking for a photo/video, plus short
  confirmations ("Got it — reviewing now ✅").
- Inbound: images / short videos from the caller. These are handed to the vision pipeline
  and the result is pushed back into the voice agent's context.

The voice agent never sends guidance or long prose over MMS.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import PlainTextResponse
from twilio.rest import Client as TwilioClient

from .config import settings
from .store import store
from .vision import analyze_image, fetch_twilio_media

router = APIRouter()

_twilio: TwilioClient | None = None


def twilio() -> TwilioClient:
    global _twilio
    if _twilio is None:
        _twilio = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
    return _twilio


def send_sms(to: str, body: str, media_url: str | None = None) -> str:
    """Send an SMS/MMS. Returns the Twilio message SID."""
    kwargs: dict = {"to": to, "from_": settings.twilio_phone_number, "body": body}
    if media_url:
        kwargs["media_url"] = [media_url]
    msg = twilio().messages.create(**kwargs)
    return msg.sid


def send_media_request(caller: str, reason: str) -> str:
    """Ask the caller to text a photo/video. One short message. Nothing else on MMS."""
    body = (
        f"Hi! Alex here from {settings.business_name}. Please send a photo or short video of "
        f"{reason} to this number and I'll review it on our call. 📸"
    )
    return send_sms(caller, body)


def send_receipt(caller: str) -> str:
    return send_sms(caller, "Got it — reviewing now ✅")


def send_job_summary(caller: str, summary: str) -> str:
    return send_sms(caller, f"📄 {summary}")


@router.post("/sms/incoming", response_class=PlainTextResponse)
async def sms_incoming(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    NumMedia: int = Form(0),
    MessageSid: str = Form(...),
):
    """Twilio inbound MMS webhook. Feeds media into the active voice session's vision pipeline."""
    session = store.get_by_caller(From)
    session and session.log("mms", "inbound", sid=MessageSid, num_media=NumMedia, body=Body)

    if NumMedia == 0:
        # Text-only message. We don't accept conversational SMS in this product.
        return PlainTextResponse(
            "<Response><Message>Thanks — please text a photo or video. "
            "For questions, please call us.</Message></Response>",
            media_type="application/xml",
        )

    # Immediate short receipt so the customer knows we got the media.
    try:
        send_receipt(From)
    except Exception:
        pass

    # Pull the first media item (we can extend to multiple).
    form = await request.form()
    media_url = form.get("MediaUrl0")
    media_type = form.get("MediaContentType0", "image/jpeg")

    if session is None:
        # No active call — we still analyze and text back a brief confirmation.
        return PlainTextResponse("<Response></Response>", media_type="application/xml")

    # Run vision analysis and hand result into the voice agent's pending queue.
    try:
        image_bytes, detected_type = await fetch_twilio_media(media_url)
        result = await analyze_image(image_bytes, detected_type or media_type, caller_context="")
        session.log("sys", "vision.result", **{k: v for k, v in result.items() if k != "raw"})
        await session.pending_vision.put({"media_url": media_url, "media_type": detected_type, "analysis": result})
    except Exception as e:
        session.log("sys", "vision.error", error=str(e))

    # Twilio expects valid TwiML, even empty.
    return PlainTextResponse("<Response></Response>", media_type="application/xml")
