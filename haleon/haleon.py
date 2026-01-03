"""Point d'entrée principal de l'application Haleon v1."""

import os
import logging
import reflex as rx
from haleon.pages.index import index
from haleon.pages.home import home_page
from haleon.pages.app_view import app_view_page, AppViewState
from haleon.auth.auth_state import AuthState
from haleon.pages.admin.users import users_admin_page, UsersAdminState
from haleon.pages.admin.applications import applications_admin_page, ApplicationsAdminState
from haleon.pages.admin.access import access_admin_page, AccessAdminState
from haleon.pages.admin.overview import overview_admin_page, OverviewAdminState
from haleon.apps.oob.admin.access import oob_access_admin_page, OOBAccessAdminState
from haleon.apps.oob.page import page as oob_page
from haleon.apps.oob.state import OOBState
from haleon.auth.http_auth_routes import mount_http_auth_routes

# Logging: keep console clean by default (only warnings/errors).
# Override with LOG_LEVEL=INFO/DEBUG when you actually want verbose output.
_log_level = os.getenv("LOG_LEVEL", "WARNING").strip().upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.WARNING),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Initialiser la base de données
from haleon.db.database import init_db
from haleon.db.seed import seed_database
from haleon.apps.oob.db.seed import seed_oob_data
init_db()
# Seed avec utilisateurs de test (John Doe admin + 2 autres utilisateurs)
seed_database()
# Seed avec données OOB de test (vendors, comments, accès)
seed_oob_data()

# Créer l'application
# Le thème CSS dans assets/theme.css est automatiquement chargé par Reflex
app = rx.App()

# Backend auth routes (HttpOnly cookies).
# These live on the backend Starlette app (app._api).
mount_http_auth_routes(app._api)

# Ajouter toutes les routes
app.add_page(index, route="/")
app.add_page(home_page, route="/home")
app.add_page(app_view_page, route="/apps/[app_code]", on_load=AppViewState.on_load)
# Pages admin avec chargement automatique via on_load
app.add_page(users_admin_page, route="/admin/users", on_load=UsersAdminState.load_users)
app.add_page(applications_admin_page, route="/admin/applications", on_load=ApplicationsAdminState.load_applications)
app.add_page(access_admin_page, route="/admin/access", on_load=AccessAdminState.load_all)
app.add_page(overview_admin_page, route="/admin/overview", on_load=OverviewAdminState.load_statistics)
# Page admin OOB
app.add_page(oob_access_admin_page, route="/admin/oob/access", on_load=OOBAccessAdminState.load_all)
# Page OOB avec chargement automatique via on_load
app.add_page(oob_page, route="/apps/oob", on_load=OOBState.on_mount)
