"""Page dynamique pour charger les applications."""

import reflex as rx
from typing import Optional, Callable
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.apps.loader import get_application_page
from haleon.db.database import get_session
from haleon.db.crud.applications import get_application_by_code


class AppViewState(AuthState):
    """État pour la page d'application - hérite de AuthState pour l'authentification."""

    current_app_name: str = ""
    current_app_code: str = ""
    app_found: bool = False
    app_page_loaded: bool = False
    has_access: bool = True
    access_denied_reason: str = ""

    # ⚠️ On stocke la fonction page(), PAS le composant
    _app_page_func: Optional[Callable] = None

    def on_load(self):
        """Charge l'application au chargement de la page."""
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()

        if hasattr(self, "app_code") and self.app_code:
            self.load_app(self.app_code)

    def show_access_denied_toast(self):
        return rx.toast.error(
            self.t("access_denied_title"),
            description=self.access_denied_reason or self.t("no_rights_for_app"),
        )

    def load_app(self, code: str):
        code_normalized = code.lower() if code else ""

        session_gen = get_session()
        session = next(session_gen)
        try:
            app = get_application_by_code(session, code_normalized)

            if not app:
                self.app_found = False
                self.current_app_name = ""
                self.current_app_code = ""
                self.app_page_loaded = False
                self._app_page_func = None
                return

            self.app_found = True
            self.current_app_name = app.name
            self.current_app_code = app.code

            from haleon.components.sidebar import SidebarState
            SidebarState.current_app_code_for_menu = app.code

            from haleon.auth.permissions import ApplicationPermissions, UserPermissions

            user = self.current_user
            if not user or not ApplicationPermissions.can_access_app(user, app.code):
                self.has_access = False

                if not user:
                    self.access_denied_reason = self.t("must_be_connected")
                elif not user.is_active:
                    self.access_denied_reason = self.t("account_not_active")
                elif not app.is_active:
                    self.access_denied_reason = self.t("app_not_active").replace("{name}", app.name)
                elif not UserPermissions.can_access(user, app.minimum_requirement):
                    self.access_denied_reason = self.t("no_rights_for_app")
                else:
                    self.access_denied_reason = self.t("no_specific_access").replace("{name}", app.name)

                self.app_page_loaded = False
                self._app_page_func = None
                return

            # ✅ Accès autorisé → charger la page
            self.has_access = True
            page_func = get_application_page(app.code, app.code)

            if page_func:
                try:
                    page_func()  # test
                    self._app_page_func = page_func
                    self.app_page_loaded = True
                except Exception:
                    self._app_page_func = None
                    self.app_page_loaded = False
            else:
                self._app_page_func = None
                self.app_page_loaded = False

        finally:
            session.close()


# ✅ FONCTION DE RENDU HORS STATE (OBLIGATOIRE)
def render_dynamic_app_page() -> rx.Component:
    if AppViewState._app_page_func:
        return AppViewState._app_page_func()
    return rx.fragment()


def app_view_page() -> rx.Component:
    """Page pour afficher une application chargée dynamiquement."""

    def default_msg():
        return layout(
            rx.center(
                rx.vstack(
                    rx.heading(
                        rx.cond(
                            AppViewState.current_app_name,
                            AppViewState.t_application_colon + AppViewState.current_app_name,
                            AppViewState.t_application_colon,
                        ),
                        size="8",
                    ),
                    rx.text(AppViewState.t_app_no_custom_page, size="3", color="gray"),
                    spacing="4",
                    align="center",
                ),
                min_height="70vh",
            )
        )

    def default_content():
        return layout(
            rx.center(
                rx.vstack(
                    rx.heading(AppViewState.t_application_not_found_title, size="8"),
                    rx.text(AppViewState.t_no_app_found_with_code, size="4", color="gray"),
                    spacing="4",
                    align="center",
                ),
                min_height="70vh",
            )
        )

    def access_denied_content():
        return layout(
            access_denied_callout(
                AppViewState.t_access_denied_title,
                AppViewState.access_denied_reason,
                AppViewState.t_back_to_home,
                "/home",
            )
        )

    return rx.fragment(
        # Toast accès refusé
        rx.cond(
            AppViewState.app_found & ~AppViewState.has_access,
            rx.box(on_mount=AppViewState.show_access_denied_toast),
        ),

        # Contenu principal
        rx.cond(
            AppViewState.is_authenticated,
            rx.cond(
                AppViewState.app_found,
                rx.cond(
                    AppViewState.has_access,
                    rx.cond(
                        AppViewState.app_page_loaded,
                        render_dynamic_app_page(),  # ✅ DYNAMIQUE
                        default_msg(),
                    ),
                    access_denied_content(),
                ),
                default_content(),
            ),
            rx.box(on_mount=rx.redirect("/")),
        ),
    )
