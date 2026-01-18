from datetime import datetime

from sqlmodel import select

from haleonv3.db.crud.audit import log_model_changes
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

    address = claims.get("address") or {}
    country = address.get("country") or claims.get("country")

    updates = {
        "email": claims.get("email"),
        "given_name": claims.get("given_name"),
        "family_name": claims.get("family_name"),
        "country": country,
        "last_login_at": now,
        "updated_at": now,
    }

    before = {
        "email": user.email,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "country": user.country,
        "last_login_at": user.last_login_at,
        "updated_at": user.updated_at,
    }

    for field, new_val in updates.items():
        if new_val is not None:
            setattr(user, field, new_val)

    after = {
        "email": user.email,
        "given_name": user.given_name,
        "family_name": user.family_name,
        "country": user.country,
        "last_login_at": user.last_login_at,
        "updated_at": user.updated_at,
    }

    log_model_changes(
        session=session,
        table_name="users",
        record_pk=str(user.id),
        before=before,
        after=after,
        fields=updates.keys(),
        request_id=request_id,
        source="sso-login",
        actor_user_id=user.id,
        actor_identifier=user.immutable_id,
        actor_is_active=user.is_active,
        actor_is_validated=user.is_validated,
        actor_is_admin=user.is_admin,
    )

    session.add(user)
    session.commit()
    session.refresh(user)
    return user
