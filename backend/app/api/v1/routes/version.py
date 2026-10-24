from fastapi import APIRouter
import hashlib
import hmac

from app.core.config import settings

router = APIRouter()


@router.get("/version")
def version() -> dict[str, str]:
    profile_id = hmac.new(settings.jwt_secret_key.encode(),
        f"ergosight-profile-v1:{settings.database_url}".encode(), hashlib.sha256).hexdigest()
    return {"api_version": "1.0", "app": "ergoquipt", "app_version": "0.2.2", "profile_id": profile_id}

