from datetime import datetime

from sqlmodel import select

from haleonv3.db.crud.logs import log_change
from haleonv3.db.model.users import Users


def upsert_user_from_claims(session, claims: dict, request_id: str | None = None):
    immutable_id = claims.get("immutable_id")
    if not immutable_id:
        raise ValueError("missing immutable_id in claims")

    user = session.exec(
        select(Users).where(Users.immutable_id == immutable_id)
    ).first()

    now = datetime.utcnow()

    if not user:
        user = Users(
            immutable_id=immutable_id,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    updates = {
        "email": claims.get("email"),
        "first_name": claims.get("first_name"),
        "family_name": claims.get("family_name"),
        "country": claims.get("country"),
        "last_login_at": now,
        "updated_at": now,
    }

    for field, new_val in updates.items():
        old_val = getattr(user, field)
        if new_val is not None and old_val != new_val:
            log_change(
                session=session,
                table_name="users",
                record_pk=str(user.id),
                field_name=field,
                old_value=str(old_val) if old_val is not None else None,
                new_value=str(new_val),
                request_id=request_id,
                source="sso-login",
                actor_user_id=user.id,
                actor_identifier=user.immutable_id,
                actor_is_active=user.is_active,
                actor_is_validated=user.is_validated,
                actor_is_admin=user.is_admin,
            )
            setattr(user, field, new_val)

    session.add(user)
    session.commit()
    session.refresh(user)
    return user
