"""Page admin - Gestion des accès utilisateur-application."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.state.i18n_state import I18nState
from haleon.db.database import get_session
from haleon.db.crud.user_app_access import (
    get_all_user_app_accesses,
    grant_user_app_access,
    revoke_user_app_access,
)
from haleon.db.crud.users import get_all_users
from haleon.db.crud.applications import get_all_applications
from haleon.db.model.user_app_access import UserApplicationAccess
from haleon.db.model.users import Users
from haleon.db.model.applications import Applications


class AccessAdminState(AuthState):
    """État pour la gestion des accès."""
    
    state_auto_setters: bool = True
    
    accesses: list[UserApplicationAccess] = []
    accesses_data: list[dict] = []  # Version dict pour l'affichage
    users: list[Users] = []
    applications: list[Applications] = []
    users_lookup: list[dict] = []  # Liste de dict pour lookup
    applications_lookup: list[dict] = []  # Liste de dict pour lookup
    _refresh_trigger: int = 0  # Variable pour forcer la mise à jour
    _cache_buster: int = 0  # Variable pour forcer la régénération du cache
    _should_reload_apps: bool = False  # Flag pour indiquer qu'il faut recharger les apps
    search_query: str = ""  # Recherche pour filtrer les accès
    
    def show_unauthorized_toast(self):
        """Affiche un toast d'erreur pour accès non autorisé."""
        return rx.toast.error(
            self.t("access_denied"),
            description=self.t("access_denied_description")
        )
    
    # Formulaire d'ajout
    form_user_email: str = ""  # Sélection par email
    form_application_name: str = ""  # Sélection par nom (label) - RENOMMÉ depuis form_application_id
    show_form: bool = False
    search_user: str = ""
    search_app: str = ""
    
    def on_mount(self):
        """Charge les traductions et les données au chargement de la page."""
        # Charger les traductions
        super().on_mount()
        # S'assurer que la session partagée est lue et que l'utilisateur est chargé pour CET état.
        # (Sinon self.session_id peut être vide et les checks admin échouent.)
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        self.load_all()
    
    def load_accesses(self):
        """Charge tous les accès depuis la BDD."""
        # --- SERVER-SIDE ADMIN GATE (read access) ---
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        if not self.is_admin:
            self.accesses = []
            self.accesses_data = []
            self.users = []
            self.applications = []
            self.users_lookup = []
            self.applications_lookup = []
            return self.show_unauthorized_toast()
        # --- END GATE ---

        session_gen = get_session()
        session = next(session_gen)
        try:
            accesses = get_all_user_app_accesses(session)
            self.accesses = accesses
            
            # Charger users et apps si nécessaire
            if not self.users:
                self.load_users()
            if not self.applications:
                self.load_applications()
            
            # Créer des dicts de lookup
            users_dict = {u["id"]: u["email"] for u in self.users_lookup}
            apps_dict = {a["id"]: a["name"] for a in self.applications_lookup}
            
            # Convertir accesses en dicts avec toutes les infos
            self.accesses_data = [
                {
                    "id": acc.id,
                    "user_id": acc.user_id,
                    "application_id": acc.application_id,
                    "user_email": users_dict.get(acc.user_id, "N/A"),
                    "app_name": apps_dict.get(acc.application_id, "N/A"),
                }
                for acc in accesses
            ]
            # Forcer la mise à jour en modifiant le trigger
            self._refresh_trigger += 1
        finally:
            session.close()
    
    _refresh_trigger: int = 0  # Variable pour forcer la mise à jour
    
    def load_users(self):
        """Charge tous les utilisateurs."""
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        if not self.is_admin:
            self.users = []
            self.users_lookup = []
            return
        session_gen = get_session()
        session = next(session_gen)
        try:
            self.users = get_all_users(session)
            # Créer une liste de dict pour lookup
            self.users_lookup = [{"id": u.id, "email": u.email, "name": f"{u.first_name or ''} {u.family_name or ''}".strip()} for u in self.users]
        finally:
            session.close()
    
    def load_applications(self):
        """Charge toutes les applications."""
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        if not self.is_admin:
            self.applications = []
            self.applications_lookup = []
            return
        session_gen = get_session()
        session = next(session_gen)
        try:
            self.applications = get_all_applications(session)
            # Créer une liste de dict pour lookup
            self.applications_lookup = [{"id": a.id, "name": a.name, "code": a.code} for a in self.applications]
        finally:
            session.close()
    
    def load_all(self):
        """Charge toutes les données."""
        # Gate once here too (prevents any accidental reads).
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        if not self.is_admin:
            self.accesses = []
            self.accesses_data = []
            self.users = []
            self.applications = []
            self.users_lookup = []
            self.applications_lookup = []
            return self.show_unauthorized_toast()
        self.load_accesses()
        self.load_users()
        self.load_applications()
    
    def show_add_form(self):
        """Affiche le formulaire d'ajout."""
        self.load_users()
        self.load_applications()
        self.show_form = True
    
    def hide_add_form(self):
        """Cache le formulaire d'ajout et réinitialise les champs."""
        self.show_form = False
        self.reset_form()
    
    def reset_form(self):
        """Réinitialise le formulaire."""
        self.form_user_email = ""
        self.form_application_name = ""
        self.search_user = ""
        self.search_app = ""
    
    def set_form_application_name(self, value: str):
        """Setter explicite pour form_application_name (pour forcer la régénération du cache)."""
        self.form_application_name = value
    
    @rx.var
    def filtered_user_emails(self) -> list[str]:
        """Retourne la liste des emails d'utilisateurs filtrés (sélection par email)."""
        if not self.search_user:
            return [u.email for u in self.users]
        search_lower = self.search_user.lower()
        return [
            u.email
            for u in self.users
            if search_lower in u.email.lower()
            or (u.first_name and search_lower in u.first_name.lower())
            or (u.family_name and search_lower in u.family_name.lower())
        ]
    
    @rx.var
    def filtered_application_names(self) -> list[str]:
        """Retourne la liste des noms d'applications filtrées (sélection par nom)."""
        if not self.search_app:
            return [a.name for a in self.applications]
        search_lower = self.search_app.lower()
        return [
            a.name
            for a in self.applications
            if search_lower in a.name.lower()
            or search_lower in a.code.lower()
        ]
    
    @rx.var
    def filtered_accesses_data(self) -> list[dict]:
        """Filtre les accès selon la recherche."""
        if not self.search_query:
            return self.accesses_data
        
        query_lower = self.search_query.lower()
        filtered = []
        for acc in self.accesses_data:
            # Recherche dans email utilisateur et nom application
            user_email = (acc.get("user_email") or "").lower()
            app_name = (acc.get("app_name") or "").lower()
            
            if query_lower in user_email or query_lower in app_name:
                filtered.append(acc)
        
        return filtered
    
    def get_user_email_by_id(self, user_id: int) -> str:
        """Récupère l'email d'un utilisateur par son ID."""
        for u in self.users_lookup:
            if u["id"] == user_id:
                return u["email"]
        return "N/A"
    
    def get_app_name_by_id(self, app_id: int) -> str:
        """Récupère le nom d'une application par son ID."""
        for a in self.applications_lookup:
            if a["id"] == app_id:
                return a["name"]
        return "N/A"
    
    def add_access(self):
        """Ajoute un nouvel accès (sélection utilisateur par email, application par nom)."""
        if not self.form_user_email or not self.form_application_name:
            yield rx.toast.error(
                self.t("validation_error"),
                description=self.t("validation_error_desc")
            )
            return

        session_gen = get_session()
        session = next(session_gen)
        try:
            # --- VÉRIFICATION DE SÉCURITÉ ---
            from haleon.db.crud.users import get_user_by_session_id
            from haleon.auth.permissions import UserPermissions
            current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
            if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                yield self.show_unauthorized_toast()
                return
            # --- FIN DE LA VÉRIFICATION ---

            user_id = None
            for u in self.users:
                if u.email == self.form_user_email:
                    user_id = u.id
                    break

            if not user_id:
                yield rx.toast.error(
                    self.t("user_not_found"),
                    description=self.t("user_not_found_desc").replace("{email}", self.form_user_email)
                )
                return

            app_id = None
            for a in self.applications:
                if a.name == self.form_application_name:
                    app_id = a.id
                    break

            if not app_id:
                yield rx.toast.error(
                    self.t("application_not_found"),
                    description=self.t("application_not_found_desc").replace("{name}", self.form_application_name)
                )
                return

            from haleon.db.crud.users import get_user_by_id
            from haleon.db.crud.applications import get_application_by_id

            user = get_user_by_id(session, user_id)
            app = get_application_by_id(session, app_id)

            if not user or not app:
                yield rx.toast.error("Erreur", description="Utilisateur ou Application introuvable")
                return

            if not UserPermissions.can_access(user, app.minimum_requirement):
                requirement_text = {"active": "actif", "validated": "validé", "admin": "administrateur"}.get(app.minimum_requirement, app.minimum_requirement)
                yield rx.toast.error(
                    self.t("prerequisite_not_met"),
                    description=self.t("prerequisite_not_met_desc").replace("{email}", user.email).replace("{requirement}", requirement_text).replace("{name}", app.name)
                )
                return

            from haleon.db.crud.user_app_access import get_user_app_access
            if get_user_app_access(session, user_id, app_id):
                yield rx.toast.error(
                    self.t("access_already_exists"),
                    description=self.t("access_already_exists_desc").replace("{email}", user.email).replace("{name}", app.name)
                )
                return

            grant_user_app_access(
                session=session,
                user_id=user_id,
                application_id=app_id,
                granted_by=current_user_db.id,
                audit_user=current_user_db,
                audit_source="admin/access",
            )

            self.load_accesses()
            self.hide_add_form()

            yield rx.toast.success(
                self.t("access_granted_success"),
                description=self.t("access_granted_success_desc").replace("{email}", self.form_user_email).replace("{name}", self.form_application_name)
            )
        except Exception as e:
            yield rx.toast.error(
                self.t("error_adding_access"),
                description=self.t("error_adding_access_desc").replace("{error}", str(e))
            )
        finally:
            session.close()
    
    def reload_user_applications(self):
        """Recharge les applications accessibles pour l'utilisateur actuel."""
        self._should_reload_apps = False
        # Réinitialiser accessible_apps pour forcer le rechargement au prochain rendu
        # Le layout détectera que accessible_apps est vide et rechargera automatiquement
        if self.is_authenticated:
            self.accessible_apps = []
            self._loading_apps = False
    
    def delete_access(self, access_id: int, user_id: int, app_id: int):
        """Supprime un accès."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            # --- VÉRIFICATION DE SÉCURITÉ ---
            from haleon.db.crud.users import get_user_by_session_id
            from haleon.auth.permissions import UserPermissions
            current_user_db = get_user_by_session_id(session, self.session_id) if self.session_id else None
            if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                yield self.show_unauthorized_toast()
                return
            # --- FIN DE LA VÉRIFICATION ---

            if revoke_user_app_access(session, user_id, app_id, audit_user=current_user_db, audit_source="admin/access"):
                self.load_accesses()
                yield rx.toast.success(self.t("access_revoked_success"))
            else:
                yield rx.toast.error(self.t("error_revoking_access"))
        except Exception as e:
            yield rx.toast.error(self.t("error_adding_access_desc").replace("{error}", str(e)))
        finally:
            session.close()


def access_admin_page() -> rx.Component:
    """Page de gestion des accès."""
    
    def access_row(access_data: dict):
        """Ligne d'un accès dans la table."""
        return rx.table.row(
            rx.table.cell(
                rx.text(access_data["user_email"], weight="medium", size="3"),
            ),
            rx.table.cell(
                rx.text(access_data["app_name"], weight="medium", size="3"),
            ),
            rx.table.cell(
                rx.button(
                    AccessAdminState.t_delete,
                    on_click=lambda: AccessAdminState.delete_access(access_data["id"], access_data["user_id"], access_data["application_id"]),
                    color_scheme="red",
                    size="2",
                    variant="outline",
                ),
            ),
        )
    
    content = rx.vstack(
        rx.heading(AccessAdminState.t_access_management, size="8", text_align="center", width="100%"),
        # Barre d'actions : recherche et bouton ajouter
        rx.hstack(
            rx.input(
                placeholder=AccessAdminState.t_search_user_or_app,
                value=AccessAdminState.search_query,
                on_change=AccessAdminState.set_search_query,
                width="100%",
                max_width="600px",
                flex="1",
                size="3",
            ),
            rx.button(
                AccessAdminState.t_add_access,
                on_click=AccessAdminState.show_add_form,
                size="3",
                color_scheme="blue",
            ),
            spacing="3",
            width="100%",
            justify="start",
        ),
        # Formulaire modal au-dessus de la grid
        rx.cond(
            AccessAdminState.show_form,
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
                    on_click=AccessAdminState.hide_add_form,
                    class_name="popup-overlay",
                ),
                # Formulaire modal
                rx.box(
                    rx.card(
                        rx.vstack(
                            # Header
                            rx.hstack(
                                rx.heading(AccessAdminState.t_add_access_title, size="6"),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=AccessAdminState.hide_add_form,
                                ),
                                width="100%",
                                align="center",
                                padding_bottom="2",
                            ),
                            rx.divider(),
                            # Formulaire
                            rx.vstack(
                                rx.input(
                                    placeholder=AccessAdminState.t_search_user_email,
                                    value=AccessAdminState.search_user,
                                    on_change=AccessAdminState.set_search_user,
                                    width="100%",
                                    size="3",
                                ),
                                rx.select(
                                    AccessAdminState.filtered_user_emails,
                                    placeholder=AccessAdminState.t_select_user_email,
                                    value=AccessAdminState.form_user_email,
                                    on_change=AccessAdminState.set_form_user_email,
                                    width="100%",
                                    size="3",
                                ),
                                rx.input(
                                    placeholder=AccessAdminState.t_search_application,
                                    value=AccessAdminState.search_app,
                                    on_change=AccessAdminState.set_search_app,
                                    width="100%",
                                    size="3",
                                ),
                                rx.select(
                                    AccessAdminState.filtered_application_names,
                                    placeholder=AccessAdminState.t_select_application,
                                    value=AccessAdminState.form_application_name,
                                    on_change=AccessAdminState.set_form_application_name,
                                    width="100%",
                                    size="3",
                                ),
                                rx.text(
                                    AccessAdminState.t_required_fields,
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
                                    AccessAdminState.t_cancel,
                                    on_click=AccessAdminState.hide_add_form,
                                    variant="outline",
                                    size="3",
                                ),
                                rx.button(
                                    AccessAdminState.t_add,
                                    on_click=AccessAdminState.add_access,
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
        # Table des accès
            rx.cond(
            AccessAdminState.filtered_accesses_data,
                rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(AccessAdminState.t_user),
                        rx.table.column_header_cell(AccessAdminState.t_application),
                        rx.table.column_header_cell(AccessAdminState.t_actions),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        AccessAdminState.filtered_accesses_data,
                        access_row,
                    ),
                ),
                width="100%",
                variant="surface",
            ),
            rx.cond(
                AccessAdminState.search_query,
                rx.text(AccessAdminState.t_no_access_found, size="4", color="gray", padding="4"),
                rx.text(AccessAdminState.t_no_access, size="4", color="gray", padding="4"),
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
                on_mount=AccessAdminState.show_unauthorized_toast
            ),
        ),
        # Recharger les applications si nécessaire (après ajout d'accès pour l'utilisateur actuel)
        rx.cond(
            AccessAdminState._should_reload_apps,
            rx.box(
                on_mount=AccessAdminState.reload_user_applications
            ),
        ),
        # Contenu principal ou message d'erreur
        rx.cond(
            AuthState.is_admin,
            layout(content),
            layout(
                access_denied_callout(
                    AccessAdminState.t_access_denied,
                    AccessAdminState.t_access_denied_description,
                    AccessAdminState.t_back_to_home,
                    "/home",
                ),
            ),
        ),
    )

