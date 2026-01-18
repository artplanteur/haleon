"""Simple cascading permissions for Haleon v3."""

from haleonv3.db.model.users import Users


class UserPermissions:
    @staticmethod
    def is_active_user(user: Users) -> bool:
        return bool(user and user.is_active)

    @staticmethod
    def is_validated_user(user: Users) -> bool:
        return bool(user and user.is_active and user.is_validated)

    @staticmethod
    def is_admin_user(user: Users) -> bool:
        return bool(user and user.is_active and user.is_validated and user.is_admin)
