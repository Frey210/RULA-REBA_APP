from fastapi import APIRouter

router = APIRouter()


@router.get("/version")
def version() -> dict[str, str]:
    return {"api_version": "1.0", "app": "ergoquipt"}

