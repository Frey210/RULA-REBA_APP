from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.models.worker_enrollment_image import WorkerEnrollmentImage
from app.schemas.worker_enrollment import WorkerEnrollmentImageRead

router = APIRouter()
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png")}


@router.get("/{worker_id}/enrollment-images", response_model=list[WorkerEnrollmentImageRead])
def list_enrollment_images(
    worker_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[WorkerEnrollmentImageRead]:
    worker = _owned_worker(worker_id, current_user, db)
    images = db.scalars(
        select(WorkerEnrollmentImage)
        .where(WorkerEnrollmentImage.worker_id == worker.id)
        .order_by(WorkerEnrollmentImage.view)
    )
    return [_image_read(image) for image in images]


@router.put("/{worker_id}/enrollment-images/{view}", response_model=WorkerEnrollmentImageRead)
async def upload_enrollment_image(
    worker_id: str,
    view: Literal["front", "left", "right"],
    file: Annotated[UploadFile, File()],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WorkerEnrollmentImageRead:
    worker = _owned_worker(worker_id, current_user, db)
    content = await file.read(MAX_IMAGE_BYTES + 1)
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image must be 8 MB or smaller")

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image file") from exc

    if image_format not in ALLOWED_FORMATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JPEG and PNG images are supported")
    if width < 320 or height < 480:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Enrollment image must be at least 320x480")

    content_type, extension = ALLOWED_FORMATS[image_format]
    directory = settings.media_root / "worker-enrollments" / current_user.id / worker.id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{view}{extension}"
    temporary = directory / f"{view}.upload"
    temporary.write_bytes(content)
    temporary.replace(path)

    record = db.scalar(
        select(WorkerEnrollmentImage).where(
            WorkerEnrollmentImage.worker_id == worker.id,
            WorkerEnrollmentImage.view == view,
        )
    )
    if record is None:
        record = WorkerEnrollmentImage(
            worker_id=worker.id,
            view=view,
            file_path=str(path),
            content_type=content_type,
            file_size=len(content),
            width=width,
            height=height,
        )
        db.add(record)
    else:
        old_path = Path(record.file_path)
        if old_path != path:
            old_path.unlink(missing_ok=True)
        record.file_path = str(path)
        record.content_type = content_type
        record.file_size = len(content)
        record.width = width
        record.height = height
    db.commit()
    db.refresh(record)
    return _image_read(record)


@router.get("/{worker_id}/enrollment-images/{view}/content", response_class=FileResponse)
def get_enrollment_image(
    worker_id: str,
    view: Literal["front", "left", "right"],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    worker = _owned_worker(worker_id, current_user, db)
    record = db.scalar(
        select(WorkerEnrollmentImage).where(
            WorkerEnrollmentImage.worker_id == worker.id,
            WorkerEnrollmentImage.view == view,
        )
    )
    if record is None or not Path(record.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment image not found")
    return FileResponse(record.file_path, media_type=record.content_type, headers={"Cache-Control": "private, max-age=60"})


@router.delete("/{worker_id}/enrollment-images/{view}", status_code=status.HTTP_204_NO_CONTENT)
def delete_enrollment_image(
    worker_id: str,
    view: Literal["front", "left", "right"],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    worker = _owned_worker(worker_id, current_user, db)
    record = db.scalar(
        select(WorkerEnrollmentImage).where(
            WorkerEnrollmentImage.worker_id == worker.id,
            WorkerEnrollmentImage.view == view,
        )
    )
    if record:
        Path(record.file_path).unlink(missing_ok=True)
        db.delete(record)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _owned_worker(worker_id: str, current_user: User, db: Session) -> Worker:
    worker = db.get(Worker, worker_id)
    if worker is None or worker.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    return worker


def _image_read(image: WorkerEnrollmentImage) -> WorkerEnrollmentImageRead:
    return WorkerEnrollmentImageRead(
        id=image.id,
        worker_id=image.worker_id,
        view=image.view,
        content_type=image.content_type,
        file_size=image.file_size,
        width=image.width,
        height=image.height,
        updated_at=image.updated_at,
        image_url=f"/api/v1/workers/{image.worker_id}/enrollment-images/{image.view}/content",
    )
