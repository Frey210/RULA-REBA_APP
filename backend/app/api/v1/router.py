from fastapi import APIRouter

from app.api.v1.routes import auth, camera_nodes, device_pairings, scoring, sessions, version, worker_enrollments, workers

api_router = APIRouter()
api_router.include_router(version.router, tags=["version"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workers.router, prefix="/workers", tags=["workers"])
api_router.include_router(worker_enrollments.router, prefix="/workers", tags=["worker-enrollment"])
api_router.include_router(camera_nodes.router, prefix="/camera-nodes", tags=["camera-nodes"])
api_router.include_router(device_pairings.router, prefix="/device-pairings", tags=["device-pairings"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["scoring"])
