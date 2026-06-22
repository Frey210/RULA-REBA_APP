from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.schemas.worker import WorkerCreate, WorkerRead, WorkerUpdate

router = APIRouter()


@router.get("", response_model=list[WorkerRead])
def list_workers(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[Worker]:
    return list(
        db.scalars(
            select(Worker)
            .where(Worker.owner_user_id == current_user.id)
            .order_by(Worker.created_at.desc())
        )
    )


@router.post("", response_model=WorkerRead, status_code=status.HTTP_201_CREATED)
def create_worker(
    payload: WorkerCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Worker:
    worker = Worker(owner_user_id=current_user.id, **payload.model_dump())
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.patch("/{worker_id}", response_model=WorkerRead)
def update_worker(
    worker_id: str,
    payload: WorkerUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Worker:
    worker = db.get(Worker, worker_id)
    if worker is None or worker.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(worker, key, value)
    db.commit()
    db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_worker(
    worker_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    worker = db.get(Worker, worker_id)
    if worker is None or worker.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    worker.is_active = False
    db.commit()

