"""Page admin - Gestion des utilisateurs."""

import reflex as rx
import json
from typing import Optional
from haleon.auth.auth_state import AuthState
from haleon.auth.permissions import UserPermissions
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.state.i18n_state import I18nState
from haleon.db.database import get_session
from haleon.db.crud.users import get_all_users
from haleon.db.model.users import Users
from haleon.db.audit_logger import AuditLogger

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




class UsersAdminState(AuthState):
    """État pour la gestion des utilisateurs."""
    
    state_auto_setters: bool = True
    
    users: list[Users] = []
    search_query: str = ""
    
    def show_unauthorized_toast(self):
        """Affiche un toast d'erreur pour accès non autorisé."""
        # Debug: vérifier pourquoi l'accès est refusé
        print(f"[DEBUG show_unauthorized_toast] Vérification des permissions:")
        print(f"  - is_authenticated: {self.is_authenticated}")
        print(f"  - current_user: {self.current_user}")
        print(f"  - is_admin: {self.is_admin}")
        print(f"  - session_id: {self.session_id}")
        if self.current_user:
            print(f"  - current_user.is_admin (BDD): {self.current_user.is_admin}")
            print(f"  - current_user.is_validated: {self.current_user.is_validated}")
            print(f"  - current_user.is_active: {self.current_user.is_active}")
        
        return rx.toast.error(
            self.t("access_denied"),
            description=self.t("access_denied_description")
        )
    
    def on_mount(self):
        """Charge les traductions et les utilisateurs au chargement de la page."""
        # Charger les traductions
        super().on_mount()
        # #region agent log
        _debug_log("users.py:on_mount", "on_mount called in State class", {"state_id": id(self)}, "A")
        # #endregion
        # S'assurer que l'utilisateur est chargé depuis la session (hérité de AuthState)
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
            # Debug: vérifier les valeurs après chargement
            print(f"[DEBUG users.py:on_mount] Après load_user_from_session:")
            print(f"  - is_authenticated: {self.is_authenticated}")
            print(f"  - current_user: {self.current_user}")
            print(f"  - is_admin: {self.is_admin}")
            if self.current_user:
                print(f"  - current_user.is_admin (BDD): {self.current_user.is_admin}")
        self.load_users()
    
    def load_users(self):
        """Charge tous les utilisateurs depuis la BDD."""
        # #region agent log
        _debug_log("users.py:load_users", "load_users called", {"users_before": len(self.users) if self.users else 0}, "B")
        # #endregion
        try:
            session_gen = get_session()
            # #region agent log
            _debug_log("users.py:load_users", "session_gen obtained", {}, "C")
            # #endregion
            session = next(session_gen)
            # #region agent log
            _debug_log("users.py:load_users", "session created", {}, "C")
            # #endregion
            try:
                users = get_all_users(session)
                # #region agent log
                _debug_log("users.py:load_users", "users fetched from DB", {"count": len(users) if users else 0}, "C")
                # #endregion
                self.users = users
                # #region agent log
                _debug_log("users.py:load_users", "users state updated", {"count": len(self.users) if self.users else 0}, "C")
                # #endregion
            except Exception as e:
                # #region agent log
                _debug_log("users.py:load_users", "ERROR in try block", {"error": str(e), "type": type(e).__name__}, "C")
                # #endregion
                raise
        except Exception as e:
            # #region agent log
            _debug_log("users.py:load_users", "ERROR in load_users", {"error": str(e), "type": type(e).__name__}, "C")
            # #endregion
        finally:
            try:
                session.close()
                # #region agent log
                _debug_log("users.py:load_users", "session closed", {}, "C")
                # #endregion
            except:
                pass
    
    @rx.var
    def filtered_users(self) -> list[Users]:
        """Filtre les utilisateurs selon la recherche."""
        # #region agent log
        _debug_log("users.py:filtered_users", "filtered_users computed", {"users_count": len(self.users) if self.users else 0, "search_query": self.search_query}, "D")
        # #endregion
        if not self.search_query:
            return self.users
        
        query_lower = self.search_query.lower()
        filtered = []
        for user in self.users:
            # Recherche dans email, prénom, nom, pays
            email_match = user.email.lower() if user.email else ""
            first_name_match = user.first_name.lower() if user.first_name else ""
            family_name_match = user.family_name.lower() if user.family_name else ""
            country_match = user.country.lower() if user.country else ""
            
            if (query_lower in email_match or 
                query_lower in first_name_match or 
                query_lower in family_name_match or 
                query_lower in country_match):
                filtered.append(user)
        
        return filtered
    
    def toggle_active(self, user_id: int):
        """Active/désactive un utilisateur avec cascade."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                # Utiliser self.session_id directement car UsersAdminState hérite de AuthState
                session_id_value = self.session_id if self.session_id else None
                current_user_db = get_user_by_session_id(session, session_id_value) if session_id_value else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                user = session.get(Users, user_id)
                if user:
                    new_active_state = not user.is_active
                    
                    with AuditLogger.with_context(session, current_user_db, "admin/users"):
                        user.is_active = new_active_state

                        if not new_active_state:
                            user.is_validated = False
                            user.is_admin = False

                        session.add(user)
                        session.commit()
                        session.refresh(user)

                    toast_msg = rx.toast.success(
                        self.t("user_activated") if new_active_state else self.t("user_deactivated"),
                        description=self.t("dependencies_updated") if not new_active_state else "",
                    )
                    self.load_users()
                    return toast_msg
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors du toggle active: {e}")
            return rx.toast.error("Erreur lors de la modification")
    
    def toggle_validated(self, user_id: int):
        """Valide/invalide un utilisateur avec cascade."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                # Utiliser self.session_id directement car UsersAdminState hérite de AuthState
                session_id_value = self.session_id if self.session_id else None
                current_user_db = get_user_by_session_id(session, session_id_value) if session_id_value else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                user = session.get(Users, user_id)
                if user:
                    if not UserPermissions.is_active_user(user):
                        return rx.toast.error(
                            self.t("cannot_validate"),
                            description=self.t("must_be_active")
                        )

                    new_validated_state = not user.is_validated

                    if new_validated_state and not UserPermissions.is_active_user(user):
                        return rx.toast.error(
                            self.t("cannot_validate"),
                            description=self.t("must_be_active")
                        )

                    with AuditLogger.with_context(session, current_user_db, "admin/users"):
                        user.is_validated = new_validated_state

                        if not new_validated_state:
                            user.is_admin = False

                        session.add(user)
                        session.commit()
                        session.refresh(user)

                    toast_msg = rx.toast.success(
                        self.t("user_validated") if new_validated_state else self.t("user_invalidated"),
                        description=self.t("dependencies_updated") if not new_validated_state else "",
                    )
                    self.load_users()
                    return toast_msg
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors du toggle validated: {e}")
            return rx.toast.error(self.t("modification_error"))
    
    def toggle_admin(self, user_id: int):
        """Donne/retire les droits admin à un utilisateur avec cascade."""
        try:
            session_gen = get_session()
            session = next(session_gen)
            try:
                # --- VÉRIFICATION DE SÉCURITÉ ---
                from haleon.db.crud.users import get_user_by_session_id
                # Utiliser self.session_id directement car UsersAdminState hérite de AuthState
                session_id_value = self.session_id if self.session_id else None
                current_user_db = get_user_by_session_id(session, session_id_value) if session_id_value else None
                if not current_user_db or not UserPermissions.is_admin_user(current_user_db):
                    return self.show_unauthorized_toast()
                # --- FIN DE LA VÉRIFICATION ---

                if current_user_db and current_user_db.id == user_id:
                    return rx.toast.error(
                        self.t("action_forbidden", default="Action interdite"),
                        description=self.t("cannot_remove_yourself", default="Vous ne pouvez pas vous retirer vous-même du statut admin")
                    )

                user = session.get(Users, user_id)
                if user:
                    new_admin_state = not user.is_admin

                    if new_admin_state and not UserPermissions.is_validated_user(user):
                        return rx.toast.error(
                            self.t("cannot_make_admin"),
                            description=self.t("must_be_validated")
                        )

                    with AuditLogger.with_context(session, current_user_db, "admin/users"):
                        user.is_admin = new_admin_state

                        session.add(user)
                        session.commit()
                        session.refresh(user)

                    toast_msg = rx.toast.success(
                        self.t("user_admin") if new_admin_state else self.t("user_not_admin")
                    )
                    self.load_users()
                    return toast_msg
            finally:
                session.close()
        except Exception as e:
            print(f"Erreur lors du toggle admin: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(self.t("modification_error"))


def users_admin_page() -> rx.Component:
    """Page de gestion des utilisateurs avec table filtrable."""
    
    def user_row(user: Users):
        """Ligne d'un utilisateur dans la table."""
        # Vérifier si c'est l'utilisateur actuel pour désactiver le toggle admin
        is_current_user = rx.cond(
            AuthState.current_user,
            AuthState.current_user.id == user.id,
            False,
        )
        
        return rx.table.row(
            rx.table.cell(
                rx.text(user.email, weight="bold", size="3"),
            ),
            rx.table.cell(
                rx.cond(
                    user.first_name,
                    rx.text(user.first_name, size="3"),
                    rx.text(UsersAdminState.t_na, size="3", color="gray"),
                ),
            ),
            rx.table.cell(
                rx.cond(
                    user.family_name,
                    rx.text(user.family_name, size="3"),
                    rx.text(UsersAdminState.t_na, size="3", color="gray"),
                ),
            ),
            rx.table.cell(
                rx.cond(
                    user.country,
                    rx.text(user.country, size="3"),
                    rx.text(UsersAdminState.t_na, size="3", color="gray"),
                ),
            ),
            rx.table.cell(
                rx.hstack(
                    rx.switch(
                        checked=user.is_active,
                        on_change=lambda: UsersAdminState.toggle_active(user.id),
                        disabled=~AuthState.is_admin,
                    ),
                    rx.cond(
                        user.is_active,
                        rx.badge(UsersAdminState.t_active, color_scheme="green", size="1"),
                        rx.badge(UsersAdminState.t_inactive, color_scheme="gray", size="1"),
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.table.cell(
                rx.hstack(
                    rx.switch(
                        checked=user.is_validated,
                        on_change=lambda: UsersAdminState.toggle_validated(user.id),
                        disabled=~AuthState.is_admin | ~user.is_active,
                    ),
                    rx.cond(
                        user.is_validated,
                        rx.badge(UsersAdminState.t_validated, color_scheme="blue", size="1"),
                        rx.badge(UsersAdminState.t_not_validated, color_scheme="gray", size="1"),
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.table.cell(
                rx.hstack(
                    rx.switch(
                        checked=user.is_admin,
                        on_change=lambda: UsersAdminState.toggle_admin(user.id),
                        disabled=~AuthState.is_admin | is_current_user | ~user.is_validated | ~user.is_active,
                    ),
                    rx.cond(
                        user.is_admin,
                        rx.badge(UsersAdminState.t_admin, color_scheme="purple", size="1"),
                        rx.badge(UsersAdminState.t_not_admin, color_scheme="gray", size="1"),
                    ),
                    spacing="2",
                    align="center",
                ),
            ),
        )
    
    content = rx.vstack(
        rx.heading(UsersAdminState.t_users_management, size="8", text_align="center", width="100%"),
        # Barre de recherche
        rx.hstack(
            rx.input(
                placeholder=UsersAdminState.t_search_by_email,
                value=UsersAdminState.search_query,
                on_change=UsersAdminState.set_search_query,
                width="100%",
                max_width="600px",
                size="3",
            ),
            spacing="3",
            width="100%",
            justify="start",
        ),
        # Table des utilisateurs
        rx.cond(
            UsersAdminState.filtered_users,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(UsersAdminState.t_email_col),
                        rx.table.column_header_cell(UsersAdminState.t_first_name_col),
                        rx.table.column_header_cell(UsersAdminState.t_last_name_col),
                        rx.table.column_header_cell(UsersAdminState.t_country_col),
                        rx.table.column_header_cell(UsersAdminState.t_active),
                        rx.table.column_header_cell(UsersAdminState.t_validated),
                        rx.table.column_header_cell(UsersAdminState.t_admin),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        UsersAdminState.filtered_users,
                        user_row,
                    ),
                ),
                width="100%",
                variant="surface",
            ),
            rx.text(UsersAdminState.t_no_users_found, size="4", color="gray", padding="4"),
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
                on_mount=UsersAdminState.show_unauthorized_toast
            ),
        ),
        # Contenu principal ou message d'erreur
        rx.cond(
            AuthState.is_admin,
            layout(content),
            layout(
                access_denied_callout(
                    UsersAdminState.t_access_denied,
                    UsersAdminState.t_access_denied_description,
                    UsersAdminState.t_back_to_home,
                    "/home",
                ),
            ),
        ),
    )

