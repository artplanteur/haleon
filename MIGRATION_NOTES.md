## Migration Notes

New tables:
- `vendor` (code, description, portfolio, is_active, timestamps)
- `user_vendor_access` (user_id, vendor_id, access_level, timestamps)
- `user_role` (user_id, app, role, timestamps)

Steps (SQLite):
1) Stop the app.
2) Create tables (if not using migrations, delete and recreate DB or run SQL DDL).
3) Restart the app (init_db will create missing tables).

Notes:
- No vendor seed data is required.
- Local OOB admin is determined by `user_role` entries where `app="oob"` and `role="admin"`.
