"""Voice-call handler. TwiML + Claude with tool use.

For the prototype we use Twilio's built-in speech recognition and TTS via TwiML
(<Gather input="speech"> + <Say>). This is easy to set up and demonstrates the full flow.

For production-grade latency you'd replace TwiML with Twilio Media Streams → a streaming
speech-to-text (Deepgram / AssemblyAI / OpenAI Realtime) → Claude → a streaming TTS (ElevenLabs
/ OpenAI Realtime). The tool-use loop below is identical in both cases; only the audio path
changes.

The voice agent owns the conversation. The only time it "uses" MMS is by invoking the
`request_media_from_caller` tool, which triggers an outbound SMS asking the customer to text
a photo. The tool then blocks waiting for a vision result on the session queue. Once the
result arrives, the agent gets it as a tool_result and keeps talking.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from anthropic import AsyncAnthropic
from fastapi import APIRouter, Form
from fastapi.responses import Response

from .config import settings
from .mms import send_media_request, send_job_summary
from .prompts import voice_system_prompt
from .store import CallSession, store


router = APIRouter()
client = AsyncAnthropic(api_key=settings.anthropic_api_key)


# -----------------------------
# Tools the voice agent can call
# -----------------------------
TOOLS = [
    {
        "name": "request_media_from_caller",
        "description": (
            "Send an MMS to the caller asking them to text a photo or short video of a specific "
            "thing. Use this whenever you need to SEE something to give correct guidance. The "
            "tool will block until the vision analysis completes and returns a structured result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Short description of what you want a photo of, e.g. 'the leak under the sink'.",
                },
                "timeout_seconds": {"type": "number", "default": 120},
            },
            "required": ["reason"],
        },
    },
    {
        "name": "book_appointment",
        "description": "Reserve a dispatch slot. Flag emergency if active damage is occurring.",
        "input_schema": {
            "type": "object",
            "properties": {
                "emergency": {"type": "boolean"},
                "preferred_window": {"type": "string", "description": "e.g. 'tonight' or 'tomorrow 8-10 AM'"},
                "summary": {"type": "string", "description": "One-sentence summary to brief the tech."},
            },
            "required": ["emergency", "summary"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": "Hand off to the on-call human tech for complex or safety-critical situations.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
    {
        "name": "end_call",
        "description": "Signal that the agent is done and the caller should hang up.",
        "input_schema": {"type": "object", "properties": {"farewell": {"type": "string"}}, "required": ["farewell"]},
    },
]


# -----------------------------
# Agent loop
# -----------------------------
async def _run_tool(session: CallSession, name: str, args: dict[str, Any]) -> str:
    """Execute one agent-invoked tool and return the tool_result payload (as a string)."""
    if name == "request_media_from_caller":
        reason = args.get("reason", "the problem")
        timeout = float(args.get("timeout_seconds", 120))
        try:
            sid = send_media_request(session.caller, reason)
            session.log("mms", "request_sent", sid=sid, reason=reason)
        except Exception as e:
            session.log("mms", "request_error", error=str(e))
            return json.dumps({"error": f"failed to send MMS: {e}"})

        try:
            result = await asyncio.wait_for(session.pending_vision.get(), timeout=timeout)
            return json.dumps(result)
        except asyncio.TimeoutError:
            return json.dumps({"error": "customer did not send a photo within the timeout"})

    if name == "book_appointment":
        session.log("sys", "appointment_booked", **args)
        # In a real deployment, call your CRM / dispatch here.
        summary = args.get("summary", "Plumbing job")
        try:
            send_job_summary(session.caller, f"Summary: {summary}. Tech will be prepped.")
        except Exception:
            pass
        return json.dumps({"ok": True, "confirmation": "booked"})

    if name == "escalate_to_human":
        session.log("sys", "escalate", **args)
        return json.dumps({"ok": True})

    if name == "end_call":
        session.log("sys", "end_call", **args)
        return json.dumps({"ok": True})

    return json.dumps({"error": f"unknown tool {name}"})


async def _agent_turn(session: CallSession, user_utterance: str) -> str:
    """Take a single customer utterance, run the agent loop (incl. tools), return the spoken reply."""
    session.messages.append({"role": "user", "content": user_utterance})
    session.log("voice", "stt", text=user_utterance)

    # Tool loop
    for _ in range(6):  # safety cap
        resp = await client.messages.create(
            model=settings.voice_model,
            max_tokens=500,
            system=voice_system_prompt(),
            tools=TOOLS,
            messages=session.messages,
        )
        session.messages.append({"role": "assistant", "content": resp.content})

        # Collect text + any tool_use blocks
        text_parts = [b.text for b in resp.content if b.type == "text"]
        tool_uses = [b for b in resp.content if b.type == "tool_use"]

        if resp.stop_reason != "tool_use" or not tool_uses:
            reply = " ".join(text_parts).strip() or "One moment, please."
            session.log("voice", "tts", text=reply)
            return reply

        # Execute each tool concurrently-ish (serial is fine for prototype).
        tool_results = []
        for tu in tool_uses:
            result = await _run_tool(session, tu.name, dict(tu.input))
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tu.id, "content": result}
            )
        session.messages.append({"role": "user", "content": tool_results})
        # Loop again so the model can respond after the tool result.

    # Fallback if we blew through the cap.
    return "Let me transfer you to a person who can help."


# -----------------------------
# TwiML webhooks
# -----------------------------
def _twiml(body: str) -> Response:
    return Response(content=body, media_type="application/xml")


@router.post("/voice/incoming")
async def voice_incoming(
    CallSid: str = Form(...),
    From: str = Form(...),
):
    """Twilio calls this when the call connects."""
    store.start(CallSid, From)
    greeting = (
        f"Hi, you've reached {settings.business_name}. This is Alex, an AI assistant. "
        "What's going on?"
    )
    action = f"{settings.public_base_url}/voice/turn"
    return _twiml(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew-Neural">{greeting}</Say>
  <Gather input="speech" action="{action}" method="POST" speechTimeout="auto" enhanced="true" language="en-US"/>
  <Say>Sorry, I didn't catch that. Goodbye.</Say>
</Response>"""
    )


@router.post("/voice/turn")
async def voice_turn(
    CallSid: str = Form(...),
    SpeechResult: str = Form(""),
):
    """Twilio calls this after each <Gather> completes with the recognized speech."""
    session = store.get(CallSid)
    if session is None:
        return _twiml("<Response><Say>Session expired.</Say><Hangup/></Response>")

    reply = await _agent_turn(session, SpeechResult or "(silence)")
    action = f"{settings.public_base_url}/voice/turn"

    # Detect end-of-call signal from the agent's last tool calls.
    ended = any(
        isinstance(m.get("content"), list)
        and any(b.get("type") == "tool_use" and b.get("name") == "end_call" for b in m["content"])
        for m in session.messages
    )
    if ended:
        return _twiml(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew-Neural">{reply}</Say>
  <Hangup/>
</Response>"""
        )

    return _twiml(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew-Neural">{reply}</Say>
  <Gather input="speech" action="{action}" method="POST" speechTimeout="auto" enhanced="true" language="en-US"/>
</Response>"""
    )


@router.post("/voice/status")
async def voice_status(CallSid: str = Form(...), CallStatus: str = Form(...)):
    """Call status webhook. Cleans up session when the call ends."""
    if CallStatus in {"completed", "busy", "failed", "no-answer", "canceled"}:
        store.end(CallSid)
    return {"ok": True}
