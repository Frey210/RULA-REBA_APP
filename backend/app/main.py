from fastapi import FastAPI
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.api.ws import ws_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app):
    from app.services.device_monitor import monitor_devices

    async def monitor():
        while True:
            try:
                await asyncio.to_thread(monitor_devices)
            except Exception:
                logging.getLogger(__name__).exception("Device monitor failed")
            await asyncio.sleep(3)

    task = asyncio.create_task(monitor())

    async def evidence():
        from app.services.snapshot_capture import capture_pending_evidence
        while True:
            try:
                await asyncio.to_thread(capture_pending_evidence)
            except Exception:
                logging.getLogger(__name__).exception("Evidence capture failed")
            await asyncio.sleep(0.2)

    evidence_task = asyncio.create_task(evidence())
    yield
    task.cancel()
    evidence_task.cancel()
    await asyncio.gather(task, evidence_task, return_exceptions=True)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.2.2", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router)
    return app


app = create_app()
