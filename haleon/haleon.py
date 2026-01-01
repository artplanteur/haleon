"""Point d'entrée principal de l'application Haleon v1."""

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
from haleon.pages.auth.callback import auth_callback_page

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

# Ajouter toutes les routes
app.add_page(index, route="/")
app.add_page(home_page, route="/home")
app.add_page(app_view_page, route="/apps/[app_code]", on_load=AppViewState.on_load)
# SSO callback (IdP redirect target)
app.add_page(auth_callback_page, route="/auth/callback", on_load=AuthState.finish_sso_login_from_router)
# Pages admin avec chargement automatique via on_load
app.add_page(users_admin_page, route="/admin/users", on_load=UsersAdminState.load_users)
app.add_page(applications_admin_page, route="/admin/applications", on_load=ApplicationsAdminState.load_applications)
app.add_page(access_admin_page, route="/admin/access", on_load=AccessAdminState.load_all)
app.add_page(overview_admin_page, route="/admin/overview", on_load=OverviewAdminState.load_statistics)
# Page admin OOB
app.add_page(oob_access_admin_page, route="/admin/oob/access", on_load=OOBAccessAdminState.load_all)
# Page OOB avec chargement automatique via on_load
app.add_page(oob_page, route="/apps/oob", on_load=OOBState.on_mount)
