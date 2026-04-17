"""WebRTC signaling for the live video-call feature.

The customer's browser and the AI agent service exchange SDP offers/answers through this
WebSocket. The actual audio/video pipe is peer-to-peer via WebRTC — our server only
signals and (in production) relays keyframes to the vision model for periodic analysis.

This is a minimal echo-style signaling server suitable for a prototype. For a real
deployment, pair it with a media server (e.g., LiveKit, mediasoup, Daily) so the AI agent
can receive video frames server-side and run them through Claude Sonnet on a cadence.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class SignalHub:
    def __init__(self) -> None:
        self._rooms: dict[str, list[WebSocket]] = {}

    async def join(self, room: str, ws: WebSocket) -> None:
        self._rooms.setdefault(room, []).append(ws)

    async def leave(self, room: str, ws: WebSocket) -> None:
        self._rooms.get(room, []).remove(ws) if ws in self._rooms.get(room, []) else None

    async def relay(self, room: str, sender: WebSocket, message: dict) -> None:
        for peer in list(self._rooms.get(room, [])):
            if peer is sender:
                continue
            try:
                await peer.send_json(message)
            except Exception:
                pass


hub = SignalHub()


@router.websocket("/rtc/signal/{room}")
async def rtc_signal(ws: WebSocket, room: str):
    await ws.accept()
    await hub.join(room, ws)
    try:
        while True:
            data = await ws.receive_json()
            await hub.relay(room, ws, data)
    except WebSocketDisconnect:
        await hub.leave(room, ws)
    except Exception:
        await hub.leave(room, ws)
