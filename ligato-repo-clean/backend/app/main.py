"""FastAPI entrypoint for the Ligato AI Vision prototype."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import mms, voice, webrtc
from .store import store


def create_app() -> FastAPI:
    app = FastAPI(title="Ligato AI Vision", version="0.1.0")
    app.include_router(voice.router)
    app.include_router(mms.router)
    app.include_router(webrtc.router)

    @app.get("/")
    def root():
        return {"service": "ligato-ai-vision", "status": "ok"}

    @app.get("/debug/sessions")
    def sessions():
        data = []
        for sid, s in store._by_sid.items():  # prototype-only debug endpoint
            data.append({"call_sid": sid, "caller": s.caller, "events": s.events[-50:]})
        return JSONResponse(data)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
