"""Page admin OOB - Gestion des accès utilisateur-vendor."""

import reflex as rx
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.state.i18n_state import I18nState
from haleon.db.database import get_session
from haleon.apps.oob.db.crud import (
    get_all_user_vendor_accesses,
    grant_vendor_access,
    delete_user_vendor_access,
    get_user_vendor_access,
    get_all_vendors,
    create_vendor,
    update_vendor,
    delete_vendor,
    get_vendor_by_id,
    get_vendor_by_code,
)
from haleon.apps.oob.db.models import OOBUserVendorAccess, OOBVendor
from haleon.db.crud.users import get_all_users, get_user_by_session_id
from haleon.db.model.users import Users
from typing import Optional


class OOBAccessAdminState(I18nState):
    """État pour la gestion des accès OOB utilisateur-vendor."""
    
    state_auto_setters: bool = True
    
    # Onglet actif
    active_tab: str = "accesses"  # "accesses" ou "vendors"
    
    # Données pour l'onglet accès
    accesses: list[OOBUserVendorAccess] = []
    accesses_data: list[dict] = []
    users: list[Users] = []
    vendors: list[OOBVendor] = []
    users_lookup: list[dict] = []
    vendors_lookup: list[dict] = []
    _refresh_trigger: int = 0
    
    # Données pour l'onglet vendors
    vendors_data: list[dict] = []
    form_vendor_code: str = ""
    form_vendor_description: str = ""
    editing_vendor_id: Optional[int] = None
    show_vendor_form: bool = False
    search_vendor_admin: str = ""
    
    def show_unauthorized_toast(self):
        """Affiche un toast d'erreur pour accès non autorisé."""
        return rx.toast.error(
            self.t("access_denied", module="oob"),
            description=self.t("access_denied_description", module="oob")
        )
    
    # Formulaire d'ajout
    form_user_email: str = ""
    form_vendor_code: str = ""
    show_form: bool = False
    search_user: str = ""
    search_vendor: str = ""
    search_access: str = ""  # Recherche pour filtrer les accès
    
    def load_accesses(self):
        """Charge tous les accès depuis la BDD."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            accesses = get_all_user_vendor_accesses(session)
            self.accesses = accesses
            
            # Charger users et vendors si nécessaire
            if not self.users:
                self.load_users()
            if not self.vendors:
                self.load_vendors()
            
            # Créer des dicts de lookup
            users_dict = {u["id"]: u["email"] for u in self.users_lookup}
            vendors_dict = {v["id"]: v["code"] for v in self.vendors_lookup}
            vendors_description_dict = {v["id"]: v["description"] or "" for v in self.vendors_lookup}
            
            # Convertir accesses en dicts avec toutes les infos
            self.accesses_data = [
                {
                    "id": acc.id,
                    "user_id": acc.user_id,
                    "vendor_id": acc.vendor_id,
                    "user_email": users_dict.get(acc.user_id, "N/A"),
                    "vendor_code": vendors_dict.get(acc.vendor_id, "N/A"),
                    "vendor_description": vendors_description_dict.get(acc.vendor_id, ""),
                }
                for acc in accesses
            ]
            self._refresh_trigger += 1
        finally:
            session.close()
    
    def load_users(self):
        """Charge tous les utilisateurs."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            self.users = get_all_users(session)
            self.users_lookup = [
                {"id": u.id, "email": u.email, "name": f"{u.first_name or ''} {u.family_name or ''}".strip()}
                for u in self.users
            ]
        finally:
            session.close()
    
    def load_vendors(self):
        """Charge tous les vendors."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            from haleon.apps.oob.db.crud import get_all_vendors
            self.vendors = get_all_vendors(session)
            self.vendors_lookup = [
                {"id": v.id, "code": v.code, "description": v.description or ""}
                for v in self.vendors
            ]
        finally:
            session.close()
    
    def load_all(self):
        """Charge toutes les données."""
        self.load_accesses()
        self.load_users()
        self.load_vendors()
        self.load_vendors_data()
    
    def show_add_form(self):
        """Affiche le formulaire d'ajout."""
        self.load_users()
        self.load_vendors()
        self.show_form = True
    
    def hide_add_form(self):
        """Cache le formulaire d'ajout et réinitialise les champs."""
        self.show_form = False
        self.reset_form()
    
    def reset_form(self):
        """Réinitialise le formulaire."""
        self.form_user_email = ""
        self.form_vendor_code = ""
        self.search_user = ""
        self.search_vendor = ""
    
    @rx.var
    def filtered_user_emails(self) -> list[str]:
        """Retourne la liste des emails d'utilisateurs filtrés."""
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
    def filtered_vendor_codes(self) -> list[str]:
        """Retourne la liste des codes vendors filtrés."""
        if not self.search_vendor:
            return [v.code for v in self.vendors]
        search_lower = self.search_vendor.lower()
        return [
            v.code
            for v in self.vendors
            if search_lower in v.code.lower()
            or (v.description and search_lower in v.description.lower())
        ]
    
    def add_access(self):
        """Ajoute un nouvel accès utilisateur-vendor."""
        if not self.form_user_email or not self.form_vendor_code:
            return rx.toast.error(
                self.t_oob_validation_error,
                description=self.t_oob_select_user_and_vendor
            )
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Convertir l'email en user_id
            user_id = None
            for u in self.users:
                if u.email == self.form_user_email:
                    user_id = u.id
                    break
            
            if not user_id:
                return rx.toast.error(
                    self.t_oob_user_not_found,
                    description=self.t_oob_user_not_found_desc.replace("{email}", self.form_user_email)
                )
            
            # Convertir le code vendor en vendor_id
            vendor_id = None
            for v in self.vendors:
                if v.code == self.form_vendor_code:
                    vendor_id = v.id
                    break
            
            if not vendor_id:
                return rx.toast.error(
                    self.t_oob_vendor_not_found,
                    description=self.t_oob_vendor_not_found_desc.replace("{code}", self.form_vendor_code)
                )
            
            # Récupérer granted_by et current_user_db depuis l'utilisateur actuel
            granted_by = None
            current_user_db = None
            # Obtenir la valeur réelle du session_id depuis AuthState
            try:
                auth_state = AuthState()
                session_id_value = auth_state.session_id if auth_state.session_id else None
                if session_id_value and not isinstance(session_id_value, str):
                    if hasattr(session_id_value, '_var_value'):
                        session_id_value = session_id_value._var_value
                    elif hasattr(session_id_value, '_var_data') and session_id_value._var_data:
                        session_id_value = session_id_value._var_data.get('value', None)
                    else:
                        session_id_value = None
            except Exception as e:
                print(f"[DEBUG] Erreur lors de la récupération du session_id: {e}")
                import traceback
                traceback.print_exc()
                session_id_value = None
            
            if session_id_value:
                current_user_db = get_user_by_session_id(session, session_id_value)
                if current_user_db:
                    granted_by = current_user_db.id
            
            # Vérifier si l'accès existe déjà
            existing = get_user_vendor_access(session, user_id, vendor_id)
            if existing:
                return rx.toast.error(
                    self.t_oob_access_already_exists,
                    description=self.t_oob_access_already_exists_desc.replace("{email}", self.form_user_email).replace("{code}", self.form_vendor_code)
                )
            
            # Créer l'accès avec contexte d'audit
            grant_vendor_access(
                session=session,
                user_id=user_id,
                vendor_id=vendor_id,
                granted_by=granted_by,
                audit_user=current_user_db,
                audit_source="oob/admin",
            )
            
            # Recharger les accès
            self.load_accesses()
            self.hide_add_form()
            
            return rx.toast.success(
                self.t_oob_access_granted_success,
                description=self.t_oob_access_granted_success_desc.replace("{email}", self.form_user_email).replace("{code}", self.form_vendor_code)
            )
        except Exception as e:
            print(f"Erreur lors de l'ajout d'accès: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(
                self.t_oob_error_adding_access,
                description=self.t_oob_error_adding_access_desc.replace("{error}", str(e))
            )
        finally:
            session.close()
    
    def delete_access(self, access_id: int):
        """Supprime un accès."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Récupérer l'utilisateur actuel pour l'audit
            current_user_db = None
            try:
                auth_state = AuthState()
                session_id_value = auth_state.session_id if auth_state.session_id else None
                if session_id_value and not isinstance(session_id_value, str):
                    if hasattr(session_id_value, '_var_value'):
                        session_id_value = session_id_value._var_value
                    elif hasattr(session_id_value, '_var_data') and session_id_value._var_data:
                        session_id_value = session_id_value._var_data.get('value', None)
                if session_id_value:
                    current_user_db = get_user_by_session_id(session, session_id_value)
            except:
                pass
            
            if delete_user_vendor_access(session, access_id, audit_user=current_user_db, audit_source="oob/admin"):
                rx.toast.success(self.t_oob_access_revoked_success)
                self.load_accesses()
            else:
                rx.toast.error(self.t_oob_error_revoking_access)
        except Exception as e:
            rx.toast.error(self.t_oob_error_generic.replace("{error}", str(e)))
        finally:
            session.close()
    
    # ========== MÉTHODES POUR GÉRER LES VENDORS ==========
    
    def load_vendors_data(self):
        """Charge tous les vendors pour l'onglet vendors."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            vendors = get_all_vendors(session)
            self.vendors_data = [
                {
                    "id": v.id,
                    "code": v.code,
                    "description": v.description or "",
                }
                for v in vendors
            ]
            self._refresh_trigger += 1
        finally:
            session.close()
    
    def show_add_vendor_form(self):
        """Affiche le formulaire d'ajout de vendor."""
        self.editing_vendor_id = None
        self.form_vendor_code = ""
        self.form_vendor_description = ""
        self.show_vendor_form = True
    
    def show_edit_vendor_form(self, vendor_id: int):
        """Affiche le formulaire d'édition de vendor."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            vendor = get_vendor_by_id(session, vendor_id)
            if vendor:
                self.editing_vendor_id = vendor_id
                self.form_vendor_code = vendor.code
                self.form_vendor_description = vendor.description or ""
                self.show_vendor_form = True
        finally:
            session.close()
    
    def hide_vendor_form(self):
        """Cache le formulaire de vendor."""
        self.show_vendor_form = False
        self.editing_vendor_id = None
        self.form_vendor_code = ""
        self.form_vendor_description = ""
    
    def save_vendor(self):
        """Sauvegarde un vendor (création ou modification)."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Récupérer l'utilisateur actuel pour l'audit
            current_user_db = None
            try:
                auth_state = AuthState()
                session_id_value = auth_state.session_id if auth_state.session_id else None
                if session_id_value and not isinstance(session_id_value, str):
                    if hasattr(session_id_value, '_var_value'):
                        session_id_value = session_id_value._var_value
                    elif hasattr(session_id_value, '_var_data') and session_id_value._var_data:
                        session_id_value = session_id_value._var_data.get('value', None)
                if session_id_value:
                    current_user_db = get_user_by_session_id(session, session_id_value)
            except:
                pass
            
            if self.editing_vendor_id:
                # Modification : on ne modifie QUE la description, pas le code
                vendor = get_vendor_by_id(session, self.editing_vendor_id)
                if not vendor:
                    return rx.toast.error(self.t_oob_vendor_not_found)
                
                update_vendor(
                    session=session,
                    vendor=vendor,
                    code=None,  # Ne pas modifier le code
                    description=self.form_vendor_description.strip() if self.form_vendor_description else None,
                    audit_user=current_user_db,
                    audit_source="oob/admin",
                )
                rx.toast.success(
                    self.t_oob_vendor_updated,
                    description=self.t_oob_vendor_updated_desc.replace("{code}", vendor.code)
                )
            else:
                # Création : le code est obligatoire
                if not self.form_vendor_code or len(self.form_vendor_code.strip()) == 0:
                    return rx.toast.error(
                        self.t_oob_code_required,
                        description=self.t_oob_code_required_desc
                    )
                
                if len(self.form_vendor_code.strip()) > 5:
                    return rx.toast.error(
                        self.t_oob_code_invalid,
                        description=self.t_oob_code_invalid_desc
                    )
                
                code_upper = self.form_vendor_code.strip().upper()
                existing = get_vendor_by_code(session, code_upper)
                if existing:
                    return rx.toast.error(
                        self.t_oob_code_already_used,
                        description=self.t_oob_code_already_used_desc.replace("{code}", code_upper)
                    )
                
                create_vendor(
                    session=session,
                    code=code_upper,
                    description=self.form_vendor_description.strip() if self.form_vendor_description else None,
                    audit_user=current_user_db,
                    audit_source="oob/admin",
                )
                rx.toast.success(
                    self.t_oob_vendor_created,
                    description=self.t_oob_vendor_created_desc.replace("{code}", code_upper)
                )
            
            # Recharger les données
            self.load_vendors_data()
            self.load_vendors()  # Recharger aussi pour l'onglet accès
            self.hide_vendor_form()
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du vendor: {e}")
            import traceback
            traceback.print_exc()
            rx.toast.error(
                self.t_oob_error_saving_vendor,
                description=self.t_oob_error_saving_vendor_desc.replace("{error}", str(e))
            )
        finally:
            session.close()
    
    def delete_vendor_action(self, vendor_id: int):
        """Supprime un vendor."""
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Récupérer l'utilisateur actuel pour l'audit
            current_user_db = None
            try:
                auth_state = AuthState()
                session_id_value = auth_state.session_id if auth_state.session_id else None
                if session_id_value and not isinstance(session_id_value, str):
                    if hasattr(session_id_value, '_var_value'):
                        session_id_value = session_id_value._var_value
                    elif hasattr(session_id_value, '_var_data') and session_id_value._var_data:
                        session_id_value = session_id_value._var_data.get('value', None)
                if session_id_value:
                    current_user_db = get_user_by_session_id(session, session_id_value)
            except:
                pass
            
            vendor = get_vendor_by_id(session, vendor_id)
            if not vendor:
                return rx.toast.error(self.t_oob_vendor_not_found)
            
            vendor_code = vendor.code
            
            if delete_vendor(session, vendor_id, audit_user=current_user_db, audit_source="oob/admin"):
                rx.toast.success(
                    self.t_oob_vendor_deleted,
                    description=self.t_oob_vendor_deleted_desc.replace("{code}", vendor_code)
                )
                self.load_vendors_data()
                self.load_vendors()  # Recharger aussi pour l'onglet accès
            else:
                rx.toast.error(self.t_oob_error_deleting_vendor)
        except Exception as e:
            rx.toast.error(self.t_oob_error_generic.replace("{error}", str(e)))
        finally:
            session.close()
    
    @rx.var
    def filtered_accesses_data(self) -> list[dict]:
        """Retourne la liste des accès filtrés pour l'onglet accès."""
        if not self.search_access:
            return self.accesses_data
        search_lower = self.search_access.lower()
        return [
            acc for acc in self.accesses_data
            if search_lower in acc["user_email"].lower()
            or search_lower in acc["vendor_code"].lower()
            or search_lower in (acc["vendor_description"] or "").lower()
        ]
    
    @rx.var
    def filtered_vendors_data(self) -> list[dict]:
        """Retourne la liste des vendors filtrés pour l'onglet vendors."""
        if not self.search_vendor_admin:
            return self.vendors_data
        search_lower = self.search_vendor_admin.lower()
        return [
            v for v in self.vendors_data
            if search_lower in v["code"].lower()
            or search_lower in (v["description"] or "").lower()
        ]


def oob_access_admin_page() -> rx.Component:
    """Page de gestion des accès OOB utilisateur-vendor."""
    
    def access_row(access_data: dict):
        """Ligne d'un accès dans la table."""
        return rx.table.row(
            rx.table.cell(rx.text(access_data["user_email"])),
            rx.table.cell(rx.text(access_data["vendor_code"], weight="bold")),
            rx.table.cell(
                rx.cond(
                    access_data["vendor_description"],
                    rx.text(access_data["vendor_description"], color="gray", size="2"),
                    rx.text("—", color="gray", size="2"),
                ),
            ),
            rx.table.cell(
                rx.button(
                    OOBAccessAdminState.t_oob_delete,
                    on_click=lambda: OOBAccessAdminState.delete_access(access_data["id"]),
                    color_scheme="red",
                    size="2",
                ),
            ),
        )
    
    # ========== ONGLET 1 : GESTION DES ACCÈS ==========
    def accesses_tab_content():
        """Contenu de l'onglet gestion des accès."""
        return rx.vstack(
            rx.heading(OOBAccessAdminState.t_oob_user_access_management, size="7", weight="bold", margin_bottom="4", padding_left="4"),
            # Barre de recherche et bouton ajouter
            rx.hstack(
                rx.input(
                    placeholder=OOBAccessAdminState.t_oob_search_access,
                    value=OOBAccessAdminState.search_access,
                    on_change=OOBAccessAdminState.set_search_access,
                    width="400px",
                    size="3",
                ),
                rx.button(
                    OOBAccessAdminState.t_oob_add_access,
                    on_click=OOBAccessAdminState.show_add_form,
                    size="3",
                    color_scheme="blue",
                ),
                spacing="3",
                width="100%",
                justify="start",
            ),
            # Table
            rx.cond(
                OOBAccessAdminState.filtered_accesses_data,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(OOBAccessAdminState.t_oob_user),
                            rx.table.column_header_cell(OOBAccessAdminState.t_oob_vendor),
                            rx.table.column_header_cell("Description"),
                            rx.table.column_header_cell(OOBAccessAdminState.t_oob_actions),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            OOBAccessAdminState.filtered_accesses_data,
                            access_row,
                        ),
                    ),
                    width="100%",
                ),
                rx.text(OOBAccessAdminState.t_oob_no_access, size="4", color="gray"),
            ),
            spacing="6",
            width="100%",
            padding="6",
        )
    
    # ========== ONGLET 2 : GESTION DES VENDORS ==========
    def vendors_tab_content():
        """Contenu de l'onglet gestion des vendors."""
        def vendor_row(vendor_data: dict):
            """Ligne d'un vendor dans la table."""
            return rx.table.row(
                rx.table.cell(rx.text(vendor_data["code"], weight="bold")),
                rx.table.cell(
                    rx.cond(
                        vendor_data["description"],
                        rx.text(vendor_data["description"], color="gray"),
                        rx.text("—", color="gray"),
                    ),
                ),
                rx.table.cell(
                    rx.hstack(
                        rx.button(
                            "✏️ Modifier",
                            on_click=lambda: OOBAccessAdminState.show_edit_vendor_form(vendor_data["id"]),
                            color_scheme="blue",
                            size="2",
                            variant="outline",
                        ),
                        rx.button(
                            "🗑️ Supprimer",
                            on_click=lambda: OOBAccessAdminState.delete_vendor_action(vendor_data["id"]),
                            color_scheme="red",
                            size="2",
                            variant="outline",
                        ),
                        spacing="2",
                    ),
                ),
            )
        
        return rx.vstack(
            rx.heading(OOBAccessAdminState.t_oob_vendor_management, size="7", weight="bold", margin_bottom="4", padding_left="4"),
            # Bouton ajouter et recherche
            rx.hstack(
                rx.input(
                    placeholder="Rechercher un vendor...",
                    value=OOBAccessAdminState.search_vendor_admin,
                    on_change=OOBAccessAdminState.set_search_vendor_admin,
                    width="300px",
                    size="3",
                ),
                rx.button(
                    "➕ Ajouter un vendor",
                    on_click=OOBAccessAdminState.show_add_vendor_form,
                    size="3",
                    color_scheme="green",
                ),
                spacing="3",
                width="100%",
                justify="start",
            ),
            # Table des vendors
            rx.cond(
                OOBAccessAdminState.filtered_vendors_data,
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Code"),
                            rx.table.column_header_cell("Description"),
                            rx.table.column_header_cell("Actions"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            OOBAccessAdminState.filtered_vendors_data,
                            vendor_row,
                        ),
                    ),
                    width="100%",
                ),
                rx.text("Aucun vendor trouvé", size="4", color="gray"),
            ),
            spacing="6",
            width="100%",
            padding="6",
        )
    
    # Formulaire modal pour vendor
    def vendor_form_modal():
        """Formulaire modal pour ajouter/modifier un vendor."""
        return rx.cond(
            OOBAccessAdminState.show_vendor_form,
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
                    on_click=OOBAccessAdminState.hide_vendor_form,
                    class_name="popup-overlay",
                ),
                # Formulaire modal
                rx.box(
                    rx.card(
                        rx.vstack(
                            # Header
                            rx.hstack(
                                rx.heading(
                                    rx.cond(
                                        OOBAccessAdminState.editing_vendor_id,
                                        "Modifier le vendor",
                                        "Ajouter un vendor",
                                    ),
                                    size="6",
                                ),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=OOBAccessAdminState.hide_vendor_form,
                                ),
                                width="100%",
                                align="center",
                                padding_bottom="2",
                            ),
                            rx.divider(),
                            # Formulaire
                            rx.vstack(
                                rx.vstack(
                                    rx.text("Code (max 5 caractères)", size="2", color="gray", weight="medium"),
                                    rx.cond(
                                        OOBAccessAdminState.editing_vendor_id,
                                        # Mode édition : code en lecture seule
                                        rx.input(
                                            value=OOBAccessAdminState.form_vendor_code,
                                            width="100%",
                                            size="3",
                                            is_read_only=True,
                                            disabled=True,
                                        ),
                                        # Mode création : code modifiable
                                        rx.input(
                                            placeholder="Ex: ACME",
                                            value=OOBAccessAdminState.form_vendor_code,
                                            on_change=OOBAccessAdminState.set_form_vendor_code,
                                            width="100%",
                                            size="3",
                                            max_length=5,
                                        ),
                                    ),
                                    spacing="1",
                                    width="100%",
                                ),
                                rx.vstack(
                                    rx.text("Description", size="2", color="gray", weight="medium"),
                                    rx.text_area(
                                        placeholder="Description du vendor...",
                                        value=OOBAccessAdminState.form_vendor_description,
                                        on_change=OOBAccessAdminState.set_form_vendor_description,
                                        width="100%",
                                        rows="3",
                                        size="3",
                                    ),
                                    spacing="1",
                                    width="100%",
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            rx.divider(),
                            # Actions
                            rx.hstack(
                                rx.button(
                                    "Annuler",
                                    on_click=OOBAccessAdminState.hide_vendor_form,
                                    variant="outline",
                                    size="3",
                                ),
                                rx.button(
                                    rx.cond(
                                        OOBAccessAdminState.editing_vendor_id,
                                        "Modifier",
                                        "Créer",
                                    ),
                                    on_click=OOBAccessAdminState.save_vendor,
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
                        width="600px",
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
        )
    
    # Contenu principal avec onglets
    content = rx.vstack(
        rx.heading("Administration OOB", size="8", text_align="center", width="100%", margin_bottom="6", padding_left="4"),
        # Onglets
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger(OOBAccessAdminState.t_oob_user_vendor_access_tab, value="accesses"),
                rx.tabs.trigger(OOBAccessAdminState.t_oob_vendor_management_tab, value="vendors"),
                default_value="accesses",
            ),
            rx.tabs.content(
                accesses_tab_content(),
                value="accesses",
            ),
            rx.tabs.content(
                vendors_tab_content(),
                value="vendors",
            ),
            value=OOBAccessAdminState.active_tab,
            on_change=OOBAccessAdminState.set_active_tab,
            width="100%",
        ),
        # Formulaire modal pour accès (existant)
        rx.cond(
            OOBAccessAdminState.show_form,
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
                    on_click=OOBAccessAdminState.hide_add_form,
                    class_name="popup-overlay",
                ),
                # Formulaire modal
                rx.box(
                    rx.card(
                        rx.vstack(
                            # Header
                            rx.hstack(
                                rx.heading(OOBAccessAdminState.t_oob_add_access_title, size="6"),
                                rx.spacer(),
                                rx.button(
                                    "✕",
                                    variant="ghost",
                                    size="2",
                                    on_click=OOBAccessAdminState.hide_add_form,
                                ),
                                width="100%",
                                align="center",
                                padding_bottom="2",
                            ),
                            rx.divider(),
                            # Formulaire
                            rx.vstack(
                                rx.input(
                                    placeholder=OOBAccessAdminState.t_oob_search_user_email,
                                    value=OOBAccessAdminState.search_user,
                                    on_change=OOBAccessAdminState.set_search_user,
                                    width="100%",
                                    size="3",
                                ),
                                rx.select(
                                    OOBAccessAdminState.filtered_user_emails,
                                    placeholder=OOBAccessAdminState.t_oob_select_user_email,
                                    value=OOBAccessAdminState.form_user_email,
                                    on_change=OOBAccessAdminState.set_form_user_email,
                                    width="100%",
                                    size="3",
                                ),
                                rx.input(
                                    placeholder=OOBAccessAdminState.t_oob_search_vendor_code,
                                    value=OOBAccessAdminState.search_vendor,
                                    on_change=OOBAccessAdminState.set_search_vendor,
                                    width="100%",
                                    size="3",
                                ),
                                rx.select(
                                    OOBAccessAdminState.filtered_vendor_codes,
                                    placeholder=OOBAccessAdminState.t_oob_select_vendor_code,
                                    value=OOBAccessAdminState.form_vendor_code,
                                    on_change=OOBAccessAdminState.set_form_vendor_code,
                                    width="100%",
                                    size="3",
                                ),
                                rx.text(
                                    OOBAccessAdminState.t_oob_required_fields,
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
                                    OOBAccessAdminState.t_oob_cancel,
                                    on_click=OOBAccessAdminState.hide_add_form,
                                    variant="outline",
                                    size="3",
                                ),
                                rx.button(
                                    OOBAccessAdminState.t_oob_add,
                                    on_click=OOBAccessAdminState.add_access,
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
        # Formulaire modal pour vendor
        vendor_form_modal(),
        spacing="6",
        width="100%",
        padding="6",
    )
    
    return rx.fragment(
        # Afficher un toast d'erreur si l'utilisateur n'est pas admin
        rx.cond(
            ~AuthState.is_admin,
            rx.box(
                on_mount=OOBAccessAdminState.show_unauthorized_toast
            ),
        ),
        # Contenu principal ou message d'erreur
        rx.cond(
            AuthState.is_admin,
            layout(content),
            layout(
                rx.center(
                    rx.vstack(
                        rx.heading(OOBAccessAdminState.t_oob_access_denied, size="9", color="red.600"),
                        rx.text(
                            OOBAccessAdminState.t_oob_access_denied_description,
                            size="5",
                            color="gray.500",
                            text_align="center",
                        ),
                        rx.button(
                            OOBAccessAdminState.t_oob_back_to_home,
                            on_click=rx.redirect("/home"),
                            size="4",
                            color_scheme="blue",
                            margin_top="4",
                        ),
                        spacing="4",
                        align="center",
                        padding="8",
                    ),
                    min_height="60vh",
                ),
            ),
        ),
    )









