from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import TokenPair, TokenRefresh, UserLogin, UserRead, UserRegister

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Annotated[Session, Depends(get_db)]) -> User:
    email = payload.email.lower()
    username = payload.username.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if db.scalar(select(User.id).where(User.username == username)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already registered")

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    return _issue_tokens(user, db)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: TokenRefresh, db: Annotated[Session, Depends(get_db)]) -> TokenPair:
    now = datetime.now(UTC)
    token_digest = _refresh_token_digest(payload.refresh_token)
    stored_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_digest,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    if stored_token is None:
        legacy_candidates = db.scalars(
            select(RefreshToken).where(
                RefreshToken.token_hash.not_like("sha256:%"),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        stored_token = next(
            (
                candidate
                for candidate in legacy_candidates
                if verify_password(payload.refresh_token, candidate.token_hash)
            ),
            None,
        )
    if stored_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = db.get(User, stored_token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unavailable")
    stored_token.revoked_at = now
    return _issue_tokens(user, db)


@router.get("/me", response_model=UserRead)
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


def _issue_tokens(user: User, db: Session) -> TokenPair:
    refresh_token = token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=_refresh_token_digest(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return TokenPair(access_token=create_access_token(user.id), refresh_token=refresh_token)


def _refresh_token_digest(refresh_token: str) -> str:
    return f"sha256:{sha256(refresh_token.encode('utf-8')).hexdigest()}"
