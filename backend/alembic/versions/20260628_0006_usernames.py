"""add usernames

Revision ID: 20260628_0006
Revises: 20260627_0005
Create Date: 2026-06-28 01:00:00
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260628_0006"
down_revision: str | None = "20260627_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, email FROM users ORDER BY created_at, id")).fetchall()
    used: set[str] = set()
    for user_id, email in users:
        base = re.sub(r"[^a-z0-9._-]", "-", str(email).split("@", 1)[0].lower()).strip("-._")
        base = (base or "user")[:42]
        if len(base) < 3:
            base = f"{base}-user"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base[:42]}-{suffix}"
            suffix += 1
        used.add(candidate)
        connection.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :user_id"),
            {"username": candidate, "user_id": user_id},
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(length=50), nullable=False)
        batch_op.create_index("ix_users_username", ["username"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_username")
        batch_op.drop_column("username")
