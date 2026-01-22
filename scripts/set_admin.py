import sys

from sqlmodel import select

from haleonv3.db.database import get_session
from haleonv3.db.model.users import Users


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/set_admin.py <email>")
        return 1

    email = sys.argv[1].strip().lower()
    if not email:
        print("Email is required.")
        return 1

    with next(get_session()) as session:
        user = session.exec(select(Users).where(Users.email == email)).first()
        if not user:
            print(f"User not found for email: {email}")
            return 1

        user.is_active = True
        user.is_validated = True
        user.is_admin = True
        session.add(user)
        session.commit()

    print(f"Admin rights granted to: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
