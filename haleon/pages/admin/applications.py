"""Page admin - Gestion des applications."""

import reflex as rx
from pathlib import Path
import json
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.state.i18n_state import I18nState
from haleon.db.database import get_session
from haleon.db.crud.applications import (
    get_all_applications,
    create_application,
    delete_application,
    update_application,
    get_application_by_id,
)
from haleon.db.model.applications import Applications

# #region agent log
def _debug_log(location, message, data=None, hypothesis_id=None):
    try:
        with open(r"c:\python\haleonv1\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": hypothesis_id or "A",
                "location": location,
                "message": message,
                "data": data or {},
                "timestamp": __import__("time").time() * 1000
            }) + "\n")
    except:
        pass
# #endregion


class ApplicationsAdminState(AuthState):
    """État pour la gestion des applications."""
    
    state_auto_setters: bool = True
    
    def show_unauthorized_toast(self):
        """Affiche un toast d'erreur pour accès non autorisé."""
        return rx.toast.error(
            self.t("access_denied"),
            description=self.t("access_denied_description")
        )
    
    applications: list[Applications] = []
    _refresh_trigger: int = 0  # Variable pour forcer la mise à jour  # Version dict pour éviter les problèmes de Var
    available_folders: list[str] = []
    search_query: str = ""
    
    # Formulaire d'ajout
    form_folder: str = ""
    form_name: str = ""
    form_code: str = ""
    form_description: str = ""
    form_icon: str = ""
    show_form: bool = False
    
    # Formulaire d'édition
    editing_app_id: int = -1
    edit_name: str = ""
    edit_description: str = ""
    edit_icon: str = ""
    edit_is_active: bool = True
    show_edit_form: bool = False
    
    def on_mount(self):
        """Charge les traductions et les applications au chargement de la page."""
        # Charger les traductions
        super().on_mount()
        # #region agent log
        _debug_log("applications.py:on_mount", "on_mount called in State class", {"state_id": id(self)}, "A")
        # #endregion
        self.load_applications()
    
    def _normalize_existing_codes(self, session):
        """Normalise les codes existants : première lettre majuscule, reste minuscule (ex: 'Oob')."""
        from haleon.db.crud.applications import update_application
        normalized_count = 0
        for app in self.applications:
            if app.code:
                # Normaliser en minuscule
                normalized_code = app.code.lower() if app.code else ""
                if app.code != normalized_code:
                    old_code = app.code
                    new_code = normalized_code
                    # Mettre à jour le code et la route
                    update_application(
                        session=session,
                        app=app,
                        route=f"/apps/{new_code.lower()}",
                    )
                    # Mettre à jour directement le code (update_application ne le fait pas)
                    app.code = new_code
                    session.add(app)
                    session.commit()
                    session.refresh(app)
                    normalized_count += 1
                    print(f"[DEBUG] Code normalisé: '{old_code}' -> '{new_code}' pour l'application '{app.name}'")
        return normalized_count > 0
    
    def _fix_routes_silently(self, session):
        """Corrige silencieusement les routes existantes de /app/ vers /apps/.
        
        Returns:
            bool: True si des routes ont été corrigées, False sinon
        """
        try:
            apps = get_all_applications(session)
            routes_fixed = False
            for app in apps:
                # Si la route commence par /app/ (sans 's'), la corriger
                if app.route.startswith("/app/") and not app.route.startswith("/apps/"):
                    new_route = app.route.replace("/app/", "/apps/", 1)
                    update_application(
                        session=session,
                        app=app,
                        route=new_route,
                    )
                    routes_fixed = True
            return routes_fixed
        except Exception as e:
            print(f"Erreur lors de la correction silencieuse des routes: {e}")
            return False
    
    def fix_routes(self):
        """Corrige les routes existantes de /app/ vers /apps/ (méthode publique avec toast)."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                apps = get_all_applications(session)
                updated_count = 0
                for app in apps:
                    # Si la route commence par /app/ (sans 's'), la corriger
                    if app.route.startswith("/app/") and not app.route.startswith("/apps/"):
                        new_route = app.route.replace("/app/", "/apps/", 1)
                        update_application(
                            session=session,
                            app=app,
                            route=new_route,
                        )
                        updated_count += 1
                
                if updated_count > 0:
                    # Recharger les applications après correction
                    self.load_applications()
                    return rx.toast.success(
                        "Routes corrigées",
                        description=f"{updated_count} route(s) mise(s) à jour de /app/ vers /apps/"
                    )
                return rx.toast.info("Aucune route à corriger", description="Toutes les routes sont déjà au format /apps/")
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors de la correction des routes: {e}")
            return rx.toast.error(f"Erreur lors de la correction des routes: {str(e)}")
    
    def load_applications(self):
        """Charge toutes les applications depuis la BDD et corrige automatiquement les routes."""
        # #region agent log
        _debug_log("applications.py:load_applications", "load_applications called", {"applications_before": len(self.applications) if self.applications else 0}, "B")
        # #endregion
        try:
            session_gen = get_session()
            # #region agent log
            _debug_log("applications.py:load_applications", "session_gen obtained", {}, "C")
            # #endregion
            session = next(session_gen)
            # #region agent log
            _debug_log("applications.py:load_applications", "session created", {}, "C")
            # #endregion
            try:
                apps = get_all_applications(session)
                # #region agent log
                _debug_log("applications.py:load_applications", "apps fetched from DB", {"count": len(apps) if apps else 0}, "C")
                # #endregion
                self.applications = apps
                # #region agent log
                _debug_log("applications.py:load_applications", "applications state updated", {"count": len(self.applications) if self.applications else 0}, "C")
                # #endregion
                # Forcer la mise à jour en modifiant le trigger
                self._refresh_trigger += 1
                # #region agent log
                _debug_log("applications.py:load_applications", "refresh_trigger incremented", {"trigger": self._refresh_trigger}, "D")
                # #endregion
                
                # Normaliser les codes existants en majuscules
                codes_normalized = self._normalize_existing_codes(session)
                # Corriger automatiquement les routes existantes de /app/ vers /apps/
                routes_fixed = self._fix_routes_silently(session)
                # Si des codes ou routes ont été corrigés, recharger les applications
                if codes_normalized or routes_fixed:
                    apps = get_all_applications(session)
                    self.applications = apps
                    self._refresh_trigger += 1
            except Exception as e:
                # #region agent log
                _debug_log("applications.py:load_applications", "ERROR in try block", {"error": str(e), "type": type(e).__name__}, "C")
                # #endregion
                raise
        except Exception as e:
            # #region agent log
            _debug_log("applications.py:load_applications", "ERROR in load_applications", {"error": str(e), "type": type(e).__name__}, "C")
            # #endregion
        finally:
            try:
                session.close()
                # #region agent log
                _debug_log("applications.py:load_applications", "session closed", {}, "C")
                # #endregion
            except:
                pass
    
    @rx.var
    def filtered_applications(self) -> list[Applications]:
        """Filtre les applications selon la recherche."""
        # Utiliser _refresh_trigger pour forcer le recalcul
        _ = self._refresh_trigger
        # #region agent log
        _debug_log("applications.py:filtered_applications", "filtered_applications computed", {"applications_count": len(self.applications) if self.applications else 0, "search_query": self.search_query, "trigger": self._refresh_trigger}, "D")
        # #endregion
        
        if not self.search_query:
            return self.applications
        
        query_lower = self.search_query.lower()
        filtered = []
        for app in self.applications:
            # Recherche dans nom, code, description, route
            name_match = (app.name or "").lower()
            code_match = (app.code or "").lower()
            description_match = (app.description or "").lower()
            route_match = (app.route or "").lower()
            
            if (query_lower in name_match or 
                query_lower in code_match or 
                query_lower in description_match or 
                query_lower in route_match):
                filtered.append(app)
        
        return filtered
    
    def scan_apps_folder(self):
        """Scanne le dossier haleon/apps/ pour trouver les dossiers disponibles."""
        from pathlib import Path
        # Chemin vers haleon/apps/
        current_file = Path(__file__)
        apps_path = current_file.parent.parent.parent.parent / "haleon" / "apps"
        folders = []
        if apps_path.exists():
            for item in apps_path.iterdir():
                if item.is_dir() and not item.name.startswith("__"):
                    folders.append(item.name)
        self.available_folders = folders
    
    def show_add_form(self):
        """Affiche le formulaire d'ajout."""
        self.scan_apps_folder()
        self.show_form = True
    
    def set_form_folder(self, value: str):
        """Setter pour form_folder qui remplit automatiquement form_code."""
        self.form_folder = value
        # Remplir automatiquement le code avec le nom du dossier normalisé si le code est vide
        if value and not self.form_code:
            # Normaliser en minuscule
            self.form_code = value.lower()
    
    def set_form_code(self, value: str):
        """Setter pour form_code avec normalisation automatique en temps réel."""
        # Normaliser en minuscule
        if value:
            # Supprimer les espaces et normaliser en minuscule
            cleaned = value.strip()
            normalized = cleaned.lower() if cleaned else ""
            self.form_code = normalized
        else:
            self.form_code = ""
    
    def hide_add_form(self):
        """Cache le formulaire d'ajout."""
        self.show_form = False
        self.reset_form()
    
    def reset_form(self):
        """Réinitialise le formulaire."""
        self.form_folder = ""
        self.form_name = ""
        self.form_code = ""
        self.form_description = ""
        self.form_icon = ""
    
    def add_application(self):
        """Ajoute une nouvelle application."""
        if not self.form_folder or not self.form_name or not self.form_code:
            return rx.toast.error(
                self.t("validation_error"),
                description=self.t("fill_required_fields")
            )

        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                from haleon.auth.permissions import UserPermissions
                current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                code_normalized = self.form_code
                route = f"/apps/{code_normalized}"

                new_app = create_application(
                    session=session,
                    name=self.form_name,
                    code=code_normalized,
                    route=route,
                    description=self.form_description if self.form_description else None,
                    icon=self.form_icon if self.form_icon else None,
                )

                self.load_applications()
                self.hide_add_form()

                return rx.toast.success(
                    self.t("application_added"),
                    description=f"{self.t('application_added')}: '{self.form_name}'"
                )
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors de l'ajout d'application: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(
                self.t("error_occurred"),
                description=f"{self.t('error_occurred')}: {str(e)}"
            )
    
    def show_edit_form_from_app(self, app: Applications):
        """Affiche le formulaire d'édition pour une application (accepte l'objet directement)."""
        self.editing_app_id = app.id
        self.edit_name = app.name
        self.edit_description = app.description if app.description else ""
        self.edit_icon = app.icon if app.icon else ""
        self.edit_is_active = app.is_active
        self.show_edit_form = True
    
    def show_edit_form(self, app_id):
        """Affiche le formulaire d'édition pour une application (accepte Var ou int)."""
        # Reflex convertira automatiquement la Var en int lors de l'appel
        session_gen = get_session()
        session = next(session_gen)
        try:
            app = get_application_by_id(session, app_id)
            if app:
                self.editing_app_id = app_id
                self.edit_name = app.name
                self.edit_description = app.description if app.description else ""
                self.edit_icon = app.icon if app.icon else ""
                self.edit_is_active = app.is_active
                self.show_edit_form = True
        finally:
            session.close()
    
    def hide_edit_form(self):
        """Cache le formulaire d'édition."""
        self.show_edit_form = False
        self.editing_app_id = -1
        self.edit_name = ""
        self.edit_description = ""
        self.edit_icon = ""
        self.edit_is_active = True
    
    def update_app(self):
        """Met à jour une application."""
        if not self.edit_name:
            return rx.toast.error(
                "Erreur de validation",
                description="Le nom est obligatoire"
            )

        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                from haleon.auth.permissions import UserPermissions
                current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                app = get_application_by_id(session, self.editing_app_id)
                if not app:
                    return rx.toast.error("Application introuvable")

                route = app.route
                if route.startswith("/app/") and not route.startswith("/apps/"):
                    route = route.replace("/app/", "/apps/", 1)

                update_application(
                    session=session,
                    app=app,
                    name=self.edit_name,
                    description=self.edit_description if self.edit_description else None,
                    icon=self.edit_icon if self.edit_icon else None,
                    is_active=self.edit_is_active,
                    route=route,
                )

                self.load_applications()
                self.hide_edit_form()

                return rx.toast.success(
                    self.t("application_updated"),
                    description=f"{self.t('application_updated')}: '{self.edit_name}'"
                )
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors de la mise à jour d'application: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(
                self.t("error_occurred"),
                description=f"{self.t('error_occurred')}: {str(e)}"
            )
    
    def toggle_app_active_from_app(self, app: Applications):
        """Toggle le statut actif/inactif d'une application (accepte l'objet directement)."""
        return self.toggle_app_active(app.id)
    
    def toggle_app_active(self, app_id):
        """Toggle le statut actif/inactif d'une application (accepte Var ou int)."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                from haleon.auth.permissions import UserPermissions
                current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                app = get_application_by_id(session, app_id)
                if app:
                    new_active_state = not app.is_active
                    update_application(
                        session=session,
                        app=app,
                        is_active=new_active_state,
                    )
                    self.load_applications()
                    return rx.toast.success(
                        self.t("application_activated" if new_active_state else "application_deactivated", default=f"Application {'activée' if new_active_state else 'désactivée'}"),
                        description=self.t("status_updated", default="Le statut de l'application a été modifié")
                    )
                else:
                    return rx.toast.error(self.t("application_not_found", default="Application introuvable"))
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors du toggle actif: {e}")
            return rx.toast.error(self.t("modification_error"))
    
    def delete_app_from_app(self, app: Applications):
        """Supprime une application (accepte l'objet directement)."""
        return self.delete_app(app.id)
    
    def delete_app(self, app_id):
        """Supprime une application (accepte Var ou int)."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                from haleon.auth.permissions import UserPermissions
                current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                app = get_application_by_id(session, app_id)
                if app:
                    app_code = app.code
                    if delete_application(session, app_id):
                        self.load_applications()
                        return rx.toast.success(
                            self.t("application_deleted"),
                            description=f"{self.t('application_deleted')}: '{app_code}'"
                        )
                    else:
                        return rx.toast.error(self.t("deletion_error", default="Erreur lors de la suppression"))
                else:
                    return rx.toast.error(self.t("application_not_found", default="Application introuvable"))
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors de la suppression: {e}")
            return rx.toast.error(
                self.t("error_occurred"),
                description=f"{self.t('error_occurred')}: {str(e)}"
            )


def applications_admin_page() -> rx.Component:
    """Page de gestion des applications."""
    
    def app_row(app: Applications):
        """Ligne d'une application dans la table."""
        return rx.table.row(
            rx.table.cell(rx.text(app.name, weight="bold", size="3")),
            rx.table.cell(rx.text(app.code, size="3")),
            rx.table.cell(
                rx.text(
                    rx.cond(
                        app.description,
                        app.description,
                        ApplicationsAdminState.t_na,
                    ),
                    size="3",
                ),
            ),
            rx.table.cell(
                rx.text(
                    rx.cond(
                        app.icon,
                        app.icon,
                        ApplicationsAdminState.t_na,
                    ),
                    size="3",
                ),
            ),
            rx.table.cell(rx.text(app.route, size="3")),
            rx.table.cell(
                rx.hstack(
                    rx.switch(
                        checked=app.is_active,
                        on_change=lambda: ApplicationsAdminState.toggle_app_active_from_app(app),
                        color_scheme="green",
                    ),
                    rx.cond(
                        app.is_active,
                        rx.badge(ApplicationsAdminState.t_active, color_scheme="green", size="1"),
                        rx.badge(ApplicationsAdminState.t_inactive, color_scheme="gray", size="1"),
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.table.cell(
                rx.hstack(
                    rx.button(
                        ApplicationsAdminState.t_edit_application,
                        on_click=lambda: ApplicationsAdminState.show_edit_form_from_app(app),
                        color_scheme="blue",
                        size="2",
                    ),
                    rx.button(
                        ApplicationsAdminState.t_delete_application,
                        on_click=lambda: ApplicationsAdminState.delete_app_from_app(app),
                        color_scheme="red",
                        size="2",
                    ),
                    spacing="2",
                ),
            ),
        )
    
    content = rx.vstack(
        rx.heading(ApplicationsAdminState.t_applications_management, size="8", text_align="center", width="100%"),
        # Barre de recherche et bouton ajouter
        rx.hstack(
            rx.input(
                placeholder=ApplicationsAdminState.t_search_applications,
                value=ApplicationsAdminState.search_query,
                on_change=ApplicationsAdminState.set_search_query,
                width="300px",
                size="3",
            ),
            rx.button(
                ApplicationsAdminState.t_add_application,
                on_click=ApplicationsAdminState.show_add_form,
                size="3",
                color_scheme="blue",
            ),
            spacing="3",
            width="100%",
            justify="start",
        ),
        # Formulaire modal au-dessus de la grid
        rx.cond(
            ApplicationsAdminState.show_form,
            rx.fragment(
                # Overlay
                rx.box(
                    position="fixed",
                    top="0",
                    left="0",
                    right="0",
                    bottom="0",
                    background_color="rgba(0, 0, 0, 0.5)",
                    z_index="9998",
                    on_click=ApplicationsAdminState.hide_add_form,
                    class_name="popup-overlay",
                ),
                # Formulaire modal
                rx.box(
                    rx.card(
                        rx.vstack(
                            # Header
                            rx.hstack(
                                rx.heading(ApplicationsAdminState.t_add_application, size="6"),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=ApplicationsAdminState.hide_add_form,
                                ),
                                width="100%",
                                align="center",
                                padding_bottom="2",
                            ),
                            rx.divider(),
                            # Formulaire
                            rx.vstack(
                                rx.select(
                                    ApplicationsAdminState.available_folders,
                                    placeholder=ApplicationsAdminState.t_select_folder,
                                    value=ApplicationsAdminState.form_folder,
                                    on_change=ApplicationsAdminState.set_form_folder,
                                    size="3",
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder=ApplicationsAdminState.t_application_name + " *",
                                    value=ApplicationsAdminState.form_name,
                                    on_change=ApplicationsAdminState.set_form_name,
                                    size="3",
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder=ApplicationsAdminState.t_application_code + " *",
                                    value=ApplicationsAdminState.form_code,
                                    on_change=ApplicationsAdminState.set_form_code,
                                    size="3",
                                    width="100%",
                                ),
                                rx.text_area(
                                    placeholder=ApplicationsAdminState.t_application_description,
                                    value=ApplicationsAdminState.form_description,
                                    on_change=ApplicationsAdminState.set_form_description,
                                    size="3",
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder=ApplicationsAdminState.t_application_icon,
                                    value=ApplicationsAdminState.form_icon,
                                    on_change=ApplicationsAdminState.set_form_icon,
                                    size="3",
                                    width="100%",
                                ),
                                rx.text(
                                    ApplicationsAdminState.t_required_fields,
                                    size="2",
                                    color="gray",
                                    padding_top="2",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.divider(),
                            # Actions
                            rx.hstack(
                                rx.button(
                                    ApplicationsAdminState.t_cancel,
                                    on_click=ApplicationsAdminState.hide_add_form,
                                    variant="outline",
                                    size="3",
                                ),
                                rx.button(
                                    ApplicationsAdminState.t_add,
                                    on_click=ApplicationsAdminState.add_application,
                                    color_scheme="green",
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                justify="end",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        padding="32px",
                        width="700px",
                        max_width="95vw",
                    ),
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    z_index="9999",
                    class_name="popup-content",
                    bg=rx.color_mode_cond("white", "#0f172a"),
                ),
            ),
        ),
        # Formulaire d'édition modal
        rx.cond(
            ApplicationsAdminState.show_edit_form,
            rx.fragment(
                # Overlay
                rx.box(
                    position="fixed",
                    top="0",
                    left="0",
                    right="0",
                    bottom="0",
                    background_color="rgba(0, 0, 0, 0.5)",
                    z_index="9998",
                    on_click=ApplicationsAdminState.hide_edit_form,
                    class_name="popup-overlay",
                ),
                # Formulaire modal
                rx.box(
                    rx.card(
                        rx.vstack(
                            # Header
                            rx.hstack(
                                rx.heading(ApplicationsAdminState.t_edit_application, size="6"),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=ApplicationsAdminState.hide_edit_form,
                                ),
                                width="100%",
                                align="center",
                                padding_bottom="2",
                            ),
                            rx.divider(),
                            # Formulaire
                            rx.vstack(
                                rx.input(
                                    placeholder=ApplicationsAdminState.t_application_name + " *",
                                    value=ApplicationsAdminState.edit_name,
                                    on_change=ApplicationsAdminState.set_edit_name,
                                    size="3",
                                    width="100%",
                                ),
                                rx.text_area(
                                    placeholder=ApplicationsAdminState.t_application_description,
                                    value=ApplicationsAdminState.edit_description,
                                    on_change=ApplicationsAdminState.set_edit_description,
                                    size="3",
                                    width="100%",
                                ),
                                rx.input(
                                    placeholder=ApplicationsAdminState.t_application_icon,
                                    value=ApplicationsAdminState.edit_icon,
                                    on_change=ApplicationsAdminState.set_edit_icon,
                                    size="3",
                                    width="100%",
                                ),
                                rx.hstack(
                                    rx.text(ApplicationsAdminState.t_active + ":", weight="bold", size="3"),
                                    rx.switch(
                                        checked=ApplicationsAdminState.edit_is_active,
                                        on_change=ApplicationsAdminState.set_edit_is_active,
                                        color_scheme="green",
                                    ),
                                    spacing="3",
                                    width="100%",
                                    align="center",
                                ),
                                rx.text(
                                    ApplicationsAdminState.t_code_route_readonly,
                                    size="2",
                                    color="gray",
                                    padding_top="2",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            rx.divider(),
                            # Actions
                            rx.hstack(
                                rx.button(
                                    ApplicationsAdminState.t_cancel,
                                    on_click=ApplicationsAdminState.hide_edit_form,
                                    variant="outline",
                                    size="3",
                                ),
                                rx.button(
                                    ApplicationsAdminState.t_save,
                                    on_click=ApplicationsAdminState.update_app,
                                    color_scheme="green",
                                    size="3",
                                ),
                                spacing="3",
                                width="100%",
                                justify="end",
                            ),
                            spacing="4",
                            width="100%",
                        ),
                        padding="32px",
                        width="700px",
                        max_width="95vw",
                    ),
                    position="fixed",
                    top="50%",
                    left="50%",
                    transform="translate(-50%, -50%)",
                    z_index="9999",
                    class_name="popup-content",
                    bg=rx.color_mode_cond("white", "#0f172a"),
                ),
            ),
        ),
        # Table des applications
        rx.cond(
            ApplicationsAdminState.filtered_applications,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(ApplicationsAdminState.t_name),
                        rx.table.column_header_cell(ApplicationsAdminState.t_code),
                        rx.table.column_header_cell(ApplicationsAdminState.t_description),
                        rx.table.column_header_cell(ApplicationsAdminState.t_icon),
                        rx.table.column_header_cell(ApplicationsAdminState.t_route),
                        rx.table.column_header_cell(ApplicationsAdminState.t_status),
                        rx.table.column_header_cell(ApplicationsAdminState.t_actions),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        ApplicationsAdminState.filtered_applications,
                        app_row,
                    ),
                ),
                width="100%",
                variant="surface",
            ),
            rx.text(
                rx.cond(
                    ApplicationsAdminState.search_query,
                    ApplicationsAdminState.t_no_applications_found,
                    ApplicationsAdminState.t_no_applications,
                ),
                size="4",
                color="gray",
                padding="4",
            ),
        ),
        spacing="6",
        width="100%",
        padding="6",
    )
    
    return rx.fragment(
        # Afficher un toast d'erreur si l'utilisateur n'est pas admin
        rx.cond(
            ~AuthState.is_admin,
            rx.box(
                on_mount=ApplicationsAdminState.show_unauthorized_toast
            ),
        ),
        # Contenu principal ou message d'erreur
        rx.cond(
            AuthState.is_admin,
            layout(content),
            layout(
                access_denied_callout(
                    ApplicationsAdminState.t_access_denied,
                    ApplicationsAdminState.t_access_denied_description,
                    ApplicationsAdminState.t_back_to_home,
                    "/home",
                ),
            ),
        ),
    )

