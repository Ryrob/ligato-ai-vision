# Ligato AI Vision — Backend Prototype

A runnable scaffold for the voice-driven, MMS-visual product. The voice agent (Claude) runs the
whole customer conversation. When it needs to *see* the problem, it calls a tool that sends an
MMS to the caller asking for a photo. The inbound MMS is analyzed by Claude's vision model and
the result is fed back into the voice agent's context — all without the customer ever switching
apps.

## Architecture

```
      ┌──────────────────────────┐
      │        Customer         │
      │  (phone on voice call)  │
      └──┬─────────────────┬────┘
         │ audio           │ MMS (photo/video)
         ▼                 ▼
   ┌──────────────┐    ┌────────────────┐
   │   Twilio     │    │    Twilio      │
   │    Voice     │    │   Messaging    │
   └──────┬───────┘    └────────┬───────┘
          │ webhook              │ webhook
          ▼                      ▼
      ┌────────────────────────────────┐
      │       FastAPI Service          │
      │  ┌──────────┐  ┌───────────┐   │
      │  │ voice.py │  │  mms.py   │   │
      │  └────┬─────┘  └────┬──────┘   │
      │       │ tool use     │          │
      │       ▼              ▼          │
      │   Claude Sonnet   Claude Sonnet │
      │   (voice agent)   (vision)      │
      └────────────────────────────────┘
```

Key design rules:

- **Voice is the brain.** All reasoning, guidance, and customer interaction happens over voice.
- **MMS is the eye.** Only photos/videos go over MMS, plus short one-line confirmations from the
  service (e.g., "Got it — reviewing now ✅").
- **One phone number.** Customers call it. They also text their photo to it. They never have to
  remember two numbers.
- **Session join key = phone number.** An inbound MMS is routed to the active voice session for
  that caller.

## Files

- `app/main.py` — FastAPI entrypoint.
- `app/voice.py` — `/voice/incoming` + `/voice/turn` Twilio webhooks and the Claude voice-agent
  loop with tool use. Tools: `request_media_from_caller`, `book_appointment`,
  `escalate_to_human`, `end_call`.
- `app/mms.py` — `/sms/incoming` webhook + helpers for sending the short MMS prompts and
  confirmations.
- `app/vision.py` — Claude vision pipeline that returns structured fields back into the voice
  agent.
- `app/webrtc.py` — minimal WebSocket signaling for the live video + screen-share path.
- `app/store.py` — in-memory session store keyed by call SID and caller phone number.
- `app/prompts.py` — system prompts for the voice agent and vision analyst.
- `app/config.py` — env-based settings.

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in ANTHROPIC_API_KEY, Twilio creds, PUBLIC_BASE_URL
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

Expose locally for Twilio webhooks (ngrok or similar):

```bash
ngrok http 8000
# then set PUBLIC_BASE_URL in .env to the https URL
```

Point your Twilio number's webhooks at:

- Voice — `POST {PUBLIC_BASE_URL}/voice/incoming`
- Voice status — `POST {PUBLIC_BASE_URL}/voice/status`
- Messaging — `POST {PUBLIC_BASE_URL}/sms/incoming`

## Testing without Twilio

You can run a synthetic session by hitting the endpoints with `curl`:

```bash
# Simulate a call starting
curl -X POST localhost:8000/voice/incoming \
  -d "CallSid=TESTCALL" -d "From=+15551230001"

# Simulate a customer utterance
curl -X POST localhost:8000/voice/turn \
  -d "CallSid=TESTCALL" -d "SpeechResult=my faucet is leaking under the sink"
```

## Production-path notes

- **Latency.** TwiML's `<Gather>` has 500–900 ms of turn-taking overhead. For a conversational
  feel, swap to Twilio Media Streams + a streaming STT (Deepgram/OpenAI Realtime) and a
  streaming TTS (ElevenLabs/OpenAI Realtime). The Claude tool-use loop in `voice.py` stays the
  same.
- **Storage.** Replace the in-memory `SessionStore` with Redis. Persist call transcripts +
  vision results to your CRM for the tech handoff.
- **Videos.** The prototype rejects videos. In production, frame-extract with ffmpeg and send
  2–4 frames to the vision model. Or accept a short clip and use a video-capable model.
- **Live video call.** `webrtc.py` is signaling only. Pair it with LiveKit (or mediasoup) so the
  agent service can subscribe to the customer's video track and sample frames for Claude.
