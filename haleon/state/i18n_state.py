"""État pour la gestion de l'internationalisation (i18n)."""

import json
import logging
import reflex as rx
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("haleon.state.i18n")

class I18nState(rx.State):
    """État pour gérer les traductions de l'application."""
    
    locale: str = rx.LocalStorage(sync=True)
    _translations: Dict[str, Dict[str, str]] = {}
    
    def on_mount(self):
        """Charge les traductions au montage du composant."""
        # Initialiser la locale à "en" si elle n'est pas définie
        if not self.locale or self.locale == "":
            self.locale = "en"
        self.load_translations()
    
    def load_translations(self):
        """Charge les fichiers de traduction depuis le dossier locale."""
        base_dir = Path(__file__).parent.parent.parent
        locale_dir = base_dir / "locale" / self.locale
        
        if not locale_dir.exists():
            logger.warning("Locale directory not found: %s", locale_dir)
            return
        
        self._translations = {}
        for json_file in locale_dir.glob("*.json"):
            module_name = json_file.stem
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    self._translations[module_name] = json.load(f)
            except Exception as e:
                logger.exception("Error loading translation file %s: %s", json_file, e)
    
    def set_locale(self, new_locale: str):
        """Change la locale et recharge les traductions."""
        if new_locale not in ["en", "fr", "es", "pt", "ar"]:
            return
        self.locale = new_locale
        self.load_translations()
    
    @rx.var
    def translations_common(self) -> Dict[str, str]:
        """Retourne les traductions du module common."""
        if not self._translations:
            self.load_translations()
        return self._translations.get("common", {}) or {}
    
    @rx.var
    def translations_oob(self) -> Dict[str, str]:
        """Retourne les traductions du module oob."""
        if not self._translations:
            self.load_translations()
        return self._translations.get("oob", {}) or {}
    
    def _get_translation(self, key: str, module: str = "common", default: Optional[str] = None) -> str:
        """Helper pour obtenir une traduction (usage interne)."""
        if not self._translations:
            self.load_translations()
        translations = self._translations.get(module, {})
        return translations.get(key, default or key)
    
    def t(self, key: str, module: str = "common", default: Optional[str] = None) -> str:
        """Retourne la traduction pour une clé donnée (pour usage dans les méthodes d'état)."""
        if not self._translations:
            self.load_translations()
        
        translations = self._translations.get(module, {})
        return translations.get(key, default or key)
    
    @rx.var
    def current_locale(self) -> str:
        """Retourne la locale actuelle."""
        return self.locale
    
    @rx.var
    def is_french(self) -> bool:
        """Retourne True si la locale est française."""
        return self.locale == "fr"
    
    @rx.var
    def is_english(self) -> bool:
        """Retourne True si la locale est anglaise."""
        return self.locale == "en"
    
    @rx.var
    def current_locale_flag_url(self) -> str:
        """Retourne l'URL du drapeau correspondant à la locale actuelle."""
        flag_map = {
            "fr": "https://flagsapi.com/FR/shiny/32.png",
            "en": "https://flagsapi.com/GB/shiny/32.png",
            "es": "https://flagsapi.com/ES/shiny/32.png",
            "pt": "https://flagsapi.com/PT/shiny/32.png",
            "ar": "https://flagsapi.com/SA/shiny/32.png",
        }
        # Retourne l'URL du drapeau ou le drapeau GB par défaut
        return flag_map.get(self.locale, "https://flagsapi.com/GB/shiny/32.png")
    
    # @rx.var spécifiques pour les clés de traduction les plus utilisées
    @rx.var
    def t_active(self) -> str:
        """Traduction pour 'active'."""
        return self._get_translation("active")
    
    @rx.var
    def t_validated(self) -> str:
        """Traduction pour 'validated'."""
        return self._get_translation("validated")
    
    @rx.var
    def t_admin(self) -> str:
        """Traduction pour 'admin'."""
        return self._get_translation("admin")
    
    @rx.var
    def t_na(self) -> str:
        """Traduction pour 'na'."""
        return self._get_translation("na")
    
    @rx.var
    def t_user_info(self) -> str:
        """Traduction pour 'user_info'."""
        return self._get_translation("user_info")
    
    @rx.var
    def t_email(self) -> str:
        """Traduction pour 'email'."""
        return self._get_translation("email")
    
    @rx.var
    def t_first_name(self) -> str:
        """Traduction pour 'first_name'."""
        return self._get_translation("first_name")
    
    @rx.var
    def t_last_name(self) -> str:
        """Traduction pour 'last_name'."""
        return self._get_translation("last_name")
    
    @rx.var
    def t_country(self) -> str:
        """Traduction pour 'country'."""
        return self._get_translation("country")
    
    @rx.var
    def t_remaining_time(self) -> str:
        """Traduction pour 'remaining_time'."""
        return self._get_translation("remaining_time")
    
    @rx.var
    def t_logout(self) -> str:
        """Traduction pour 'logout'."""
        return self._get_translation("logout")
    
    @rx.var
    def t_menu(self) -> str:
        """Traduction pour 'menu'."""
        return self._get_translation("menu")
    
    @rx.var
    def t_administration(self) -> str:
        """Traduction pour 'administration'."""
        return self._get_translation("administration")
    
    @rx.var
    def t_users(self) -> str:
        """Traduction pour 'users'."""
        return self._get_translation("users")
    
    @rx.var
    def t_applications(self) -> str:
        """Traduction pour 'applications'."""
        return self._get_translation("applications")
    
    @rx.var
    def t_access(self) -> str:
        """Traduction pour 'access'."""
        return self._get_translation("access")
    
    @rx.var
    def t_overview(self) -> str:
        """Traduction pour 'overview'."""
        return self._get_translation("overview")
    
    @rx.var
    def t_settings(self) -> str:
        """Traduction pour 'settings'."""
        return self._get_translation("settings")
    
    @rx.var
    def t_dark_mode(self) -> str:
        """Traduction pour 'dark_mode'."""
        return self._get_translation("dark_mode")
    
    @rx.var
    def t_light_mode(self) -> str:
        """Traduction pour 'light_mode'."""
        return self._get_translation("light_mode")
    
    @rx.var
    def t_language(self) -> str:
        """Traduction pour 'language'."""
        return self._get_translation("language")
    
    @rx.var
    def t_login_with_john_doe(self) -> str:
        """Traduction pour 'login_with_john_doe'."""
        return self._get_translation("login_with_john_doe")
    
    @rx.var
    def t_inactive(self) -> str:
        """Traduction pour 'inactive'."""
        return self._get_translation("inactive")
    
    @rx.var
    def t_not_validated(self) -> str:
        """Traduction pour 'not_validated'."""
        return self._get_translation("not_validated")
    
    @rx.var
    def t_not_admin(self) -> str:
        """Traduction pour 'not_admin'."""
        return self._get_translation("not_admin")
    
    @rx.var
    def t_users_management(self) -> str:
        """Traduction pour 'users_management'."""
        return self._get_translation("users_management")
    
    @rx.var
    def t_email_col(self) -> str:
        """Traduction pour 'email_col'."""
        return self._get_translation("email_col")
    
    @rx.var
    def t_first_name_col(self) -> str:
        """Traduction pour 'first_name_col'."""
        return self._get_translation("first_name_col")
    
    @rx.var
    def t_last_name_col(self) -> str:
        """Traduction pour 'last_name_col'."""
        return self._get_translation("last_name_col")
    
    @rx.var
    def t_country_col(self) -> str:
        """Traduction pour 'country_col'."""
        return self._get_translation("country_col")
    
    @rx.var
    def t_no_users_found(self) -> str:
        """Traduction pour 'no_users_found'."""
        return self._get_translation("no_users_found")
    
    @rx.var
    def t_access_denied(self) -> str:
        """Traduction pour 'access_denied'."""
        return self._get_translation("access_denied")
    
    @rx.var
    def t_access_denied_description(self) -> str:
        """Traduction pour 'access_denied_description'."""
        return self._get_translation("access_denied_description")
    
    @rx.var
    def t_back_to_home(self) -> str:
        """Traduction pour 'back_to_home'."""
        return self._get_translation("back_to_home")
    
    @rx.var
    def t_access_management(self) -> str:
        """Traduction pour 'access_management'."""
        return self._get_translation("access_management")
    
    @rx.var
    def t_add_access(self) -> str:
        """Traduction pour 'add_access'."""
        return self._get_translation("add_access")
    
    @rx.var
    def t_search_user_or_app(self) -> str:
        """Traduction pour 'search_user_or_app'."""
        return self._get_translation("search_user_or_app")
    
    @rx.var
    def t_add_access_title(self) -> str:
        """Traduction pour 'add_access_title'."""
        return self._get_translation("add_access_title")
    
    @rx.var
    def t_search_user_email(self) -> str:
        """Traduction pour 'search_user_email'."""
        return self._get_translation("search_user_email")
    
    @rx.var
    def t_select_user_email(self) -> str:
        """Traduction pour 'select_user_email'."""
        return self._get_translation("select_user_email")
    
    @rx.var
    def t_search_application(self) -> str:
        """Traduction pour 'search_application'."""
        return self._get_translation("search_application")
    
    @rx.var
    def t_select_application(self) -> str:
        """Traduction pour 'select_application'."""
        return self._get_translation("select_application")
    
    @rx.var
    def t_required_fields(self) -> str:
        """Traduction pour 'required_fields'."""
        return self._get_translation("required_fields")
    
    @rx.var
    def t_cancel(self) -> str:
        """Traduction pour 'cancel'."""
        return self._get_translation("cancel")
    
    @rx.var
    def t_add(self) -> str:
        """Traduction pour 'add'."""
        return self._get_translation("add")
    
    @rx.var
    def t_user(self) -> str:
        """Traduction pour 'user'."""
        return self._get_translation("user")
    
    @rx.var
    def t_application(self) -> str:
        """Traduction pour 'application'."""
        return self._get_translation("application")
    
    @rx.var
    def t_actions(self) -> str:
        """Traduction pour 'actions'."""
        return self._get_translation("actions")
    
    @rx.var
    def t_delete(self) -> str:
        """Traduction pour 'delete'."""
        return self._get_translation("delete")
    
    @rx.var
    def t_no_access_found(self) -> str:
        """Traduction pour 'no_access_found'."""
        return self._get_translation("no_access_found")
    
    @rx.var
    def t_no_access(self) -> str:
        """Traduction pour 'no_access'."""
        return self._get_translation("no_access")
    
    @rx.var
    def t_applications_management(self) -> str:
        """Traduction pour 'applications_management'."""
        return self._get_translation("applications_management")
    
    @rx.var
    def t_search_applications(self) -> str:
        """Traduction pour 'search_applications'."""
        return self._get_translation("search_applications")
    
    @rx.var
    def t_add_application(self) -> str:
        """Traduction pour 'add_application'."""
        return self._get_translation("add_application")
    
    @rx.var
    def t_edit_application(self) -> str:
        """Traduction pour 'edit_application'."""
        return self._get_translation("edit_application")
    
    @rx.var
    def t_delete_application(self) -> str:
        """Traduction pour 'delete_application'."""
        return self._get_translation("delete_application")
    
    @rx.var
    def t_select_folder(self) -> str:
        """Traduction pour 'select_folder'."""
        return self._get_translation("select_folder")
    
    @rx.var
    def t_application_name(self) -> str:
        """Traduction pour 'application_name'."""
        return self._get_translation("application_name")
    
    @rx.var
    def t_application_code(self) -> str:
        """Traduction pour 'application_code'."""
        return self._get_translation("application_code")
    
    @rx.var
    def t_application_description(self) -> str:
        """Traduction pour 'application_description'."""
        return self._get_translation("application_description")
    
    @rx.var
    def t_application_icon(self) -> str:
        """Traduction pour 'application_icon'."""
        return self._get_translation("application_icon")
    
    @rx.var
    def t_name(self) -> str:
        """Traduction pour 'name'."""
        return self._get_translation("name")
    
    @rx.var
    def t_code(self) -> str:
        """Traduction pour 'code'."""
        return self._get_translation("code")
    
    @rx.var
    def t_description(self) -> str:
        """Traduction pour 'description'."""
        return self._get_translation("description")
    
    @rx.var
    def t_icon(self) -> str:
        """Traduction pour 'icon'."""
        return self._get_translation("icon")
    
    @rx.var
    def t_route(self) -> str:
        """Traduction pour 'route'."""
        return self._get_translation("route")
    
    @rx.var
    def t_status(self) -> str:
        """Traduction pour 'status'."""
        return self._get_translation("status")
    
    @rx.var
    def t_no_applications_found(self) -> str:
        """Traduction pour 'no_applications_found'."""
        return self._get_translation("no_applications_found")
    
    @rx.var
    def t_no_applications(self) -> str:
        """Traduction pour 'no_applications'."""
        return self._get_translation("no_applications")
    
    @rx.var
    def t_save(self) -> str:
        """Traduction pour 'save'."""
        return self._get_translation("save")
    
    @rx.var
    def t_code_route_readonly(self) -> str:
        """Traduction pour 'code_route_readonly'."""
        return self._get_translation("code_route_readonly", default="* Le code et la route ne peuvent pas être modifiés")
    
    @rx.var
    def t_core_tables_statistics(self) -> str:
        """Traduction pour 'core_tables_statistics'."""
        return self._get_translation("core_tables_statistics", default="Statistiques des tables core")
    
    @rx.var
    def t_application_tables(self) -> str:
        """Traduction pour 'application_tables'."""
        return self._get_translation("application_tables", default="Tables des applications")
    
    @rx.var
    def t_table(self) -> str:
        """Traduction pour 'table'."""
        return self._get_translation("table", default="Table")
    
    @rx.var
    def t_structure(self) -> str:
        """Traduction pour 'structure'."""
        return self._get_translation("structure", default="Structure")
    
    @rx.var
    def t_data_preview(self) -> str:
        """Traduction pour 'data_preview'."""
        return self._get_translation("data_preview", default="Aperçu des données")
    
    @rx.var
    def t_no_tables_found(self) -> str:
        """Traduction pour 'no_tables_found'."""
        return self._get_translation("no_tables_found", default="Aucune table trouvée pour cette application")
    
    @rx.var
    def t_select_app_to_see_tables(self) -> str:
        """Traduction pour 'select_app_to_see_tables'."""
        return self._get_translation("select_app_to_see_tables", default="Sélectionnez une application ci-dessus pour voir ses tables")
    
    @rx.var
    def t_columns(self) -> str:
        """Traduction pour 'columns'."""
        return self._get_translation("columns")
    
    @rx.var
    def t_search_by_email(self) -> str:
        """Traduction pour 'search_by_email'."""
        return self._get_translation("search_by_email", default="Rechercher par email, prénom, nom ou pays...")
    
    # Traductions OOB
    @rx.var
    def t_oob_purchasing_items(self) -> str:
        """Traduction pour 'purchasing_items' (module oob)."""
        return self._get_translation("purchasing_items", module="oob")
    
    @rx.var
    def t_oob_search_placeholder(self) -> str:
        """Traduction pour 'search_placeholder' (module oob)."""
        return self._get_translation("search_placeholder", module="oob")
    
    @rx.var
    def t_oob_download_excel(self) -> str:
        """Traduction pour 'download_excel' (module oob)."""
        return self._get_translation("download_excel", module="oob")
    
    @rx.var
    def t_oob_filters(self) -> str:
        """Traduction pour 'filters' (module oob)."""
        return self._get_translation("filters", module="oob")
    
    @rx.var
    def t_oob_document_types(self) -> str:
        """Traduction pour 'document_types' (module oob)."""
        return self._get_translation("document_types", module="oob")
    
    @rx.var
    def t_oob_select_types(self) -> str:
        """Traduction pour 'select_types' (module oob)."""
        return self._get_translation("select_types", module="oob")
    
    @rx.var
    def t_oob_select_all(self) -> str:
        """Traduction pour 'select_all' (module oob)."""
        return self._get_translation("select_all", module="oob")
    
    @rx.var
    def t_oob_period(self) -> str:
        """Traduction pour 'period' (module oob)."""
        return self._get_translation("period", module="oob")
    
    @rx.var
    def t_oob_from(self) -> str:
        """Traduction pour 'from' (module oob)."""
        return self._get_translation("from", module="oob")
    
    @rx.var
    def t_oob_to(self) -> str:
        """Traduction pour 'to' (module oob)."""
        return self._get_translation("to", module="oob")
    
    @rx.var
    def t_oob_locations(self) -> str:
        """Traduction pour 'locations' (module oob)."""
        return self._get_translation("locations", module="oob")
    
    @rx.var
    def t_oob_ship_from(self) -> str:
        """Traduction pour 'ship_from' (module oob)."""
        return self._get_translation("ship_from", module="oob")
    
    @rx.var
    def t_oob_ship_to(self) -> str:
        """Traduction pour 'ship_to' (module oob)."""
        return self._get_translation("ship_to", module="oob")
    
    @rx.var
    def t_oob_filter(self) -> str:
        """Traduction pour 'filter' (module oob)."""
        return self._get_translation("filter", module="oob")
    
    @rx.var
    def t_oob_product_id(self) -> str:
        """Traduction pour 'product_id' (module oob)."""
        return self._get_translation("product_id", module="oob")
    
    @rx.var
    def t_oob_ship_to_location(self) -> str:
        """Traduction pour 'ship_to_location' (module oob)."""
        return self._get_translation("ship_to_location", module="oob")
    
    @rx.var
    def t_oob_ship_from_location(self) -> str:
        """Traduction pour 'ship_from_location' (module oob)."""
        return self._get_translation("ship_from_location", module="oob")
    
    @rx.var
    def t_oob_receipt_quantity(self) -> str:
        """Traduction pour 'receipt_quantity' (module oob)."""
        return self._get_translation("receipt_quantity", module="oob")
    
    @rx.var
    def t_oob_ordered_quantity(self) -> str:
        """Traduction pour 'ordered_quantity' (module oob)."""
        return self._get_translation("ordered_quantity", module="oob")
    
    @rx.var
    def t_oob_doc_ext(self) -> str:
        """Traduction pour 'doc_ext' (module oob)."""
        return self._get_translation("doc_ext", module="oob")
    
    @rx.var
    def t_oob_doc_type(self) -> str:
        """Traduction pour 'doc_type' (module oob)."""
        return self._get_translation("doc_type", module="oob")
    
    @rx.var
    def t_oob_receipt_date(self) -> str:
        """Traduction pour 'receipt_date' (module oob)."""
        return self._get_translation("receipt_date", module="oob")
    
    @rx.var
    def t_oob_delivery_date(self) -> str:
        """Traduction pour 'delivery_date' (module oob)."""
        return self._get_translation("delivery_date", module="oob")
    
    @rx.var
    def t_oob_requirement_date(self) -> str:
        """Traduction pour 'requirement_date' (module oob)."""
        return self._get_translation("requirement_date", module="oob")
    
    @rx.var
    def t_oob_no_items(self) -> str:
        """Traduction pour 'no_items' (module oob)."""
        return self._get_translation("no_items", module="oob")
    
    @rx.var
    def t_oob_line_details(self) -> str:
        """Traduction pour 'line_details' (module oob)."""
        return self._get_translation("line_details", module="oob", default="Détails de la ligne")
    
    @rx.var
    def t_oob_select_po(self) -> str:
        """Traduction pour 'select_po' (module oob)."""
        return self._get_translation("select_po", module="oob")
    
    @rx.var
    def t_oob_add_comment(self) -> str:
        """Traduction pour 'add_comment' (module oob)."""
        return self._get_translation("add_comment", module="oob")
    
    @rx.var
    def t_oob_comment_placeholder(self) -> str:
        """Traduction pour 'comment_placeholder' (module oob)."""
        return self._get_translation("comment_placeholder", module="oob")
    
    @rx.var
    def t_oob_send(self) -> str:
        """Traduction pour 'send' (module oob)."""
        return self._get_translation("send", module="oob")
    
    @rx.var
    def t_oob_comments(self) -> str:
        """Traduction pour 'comments' (module oob)."""
        return self._get_translation("comments", module="oob")
    
    @rx.var
    def t_oob_no_comments(self) -> str:
        """Traduction pour 'no_comments' (module oob)."""
        return self._get_translation("no_comments", module="oob")
    
    @rx.var
    def t_oob_oob_access_management(self) -> str:
        """Traduction pour 'oob_access_management' (module oob)."""
        return self._get_translation("oob_access_management", module="oob")
    
    @rx.var
    def t_oob_add_access(self) -> str:
        """Traduction pour 'add_access' (module oob)."""
        return self._get_translation("add_access", module="oob")
    
    @rx.var
    def t_oob_add_access_title(self) -> str:
        """Traduction pour 'add_access_title' (module oob)."""
        return self._get_translation("add_access_title", module="oob")
    
    @rx.var
    def t_oob_search_user_email(self) -> str:
        """Traduction pour 'search_user_email' (module oob)."""
        return self._get_translation("search_user_email", module="oob")
    
    @rx.var
    def t_oob_select_user_email(self) -> str:
        """Traduction pour 'select_user_email' (module oob)."""
        return self._get_translation("select_user_email", module="oob")
    
    @rx.var
    def t_oob_search_vendor_code(self) -> str:
        """Traduction pour 'search_vendor_code' (module oob)."""
        return self._get_translation("search_vendor_code", module="oob")
    
    @rx.var
    def t_oob_select_vendor_code(self) -> str:
        """Traduction pour 'select_vendor_code' (module oob)."""
        return self._get_translation("select_vendor_code", module="oob")
    
    @rx.var
    def t_oob_required_fields(self) -> str:
        """Traduction pour 'required_fields' (module oob)."""
        return self._get_translation("required_fields", module="oob")
    
    @rx.var
    def t_oob_cancel(self) -> str:
        """Traduction pour 'cancel' (module oob)."""
        return self._get_translation("cancel", module="oob")
    
    @rx.var
    def t_oob_add(self) -> str:
        """Traduction pour 'add' (module oob)."""
        return self._get_translation("add", module="oob")
    
    @rx.var
    def t_oob_user(self) -> str:
        """Traduction pour 'user' (module oob)."""
        return self._get_translation("user", module="oob")
    
    @rx.var
    def t_oob_vendor(self) -> str:
        """Traduction pour 'vendor' (module oob)."""
        return self._get_translation("vendor", module="oob")
    
    @rx.var
    def t_oob_actions(self) -> str:
        """Traduction pour 'actions' (module oob)."""
        return self._get_translation("actions", module="oob")
    
    @rx.var
    def t_oob_delete(self) -> str:
        """Traduction pour 'delete' (module oob)."""
        return self._get_translation("delete", module="oob")
    
    @rx.var
    def t_oob_no_access(self) -> str:
        """Traduction pour 'no_access' (module oob)."""
        return self._get_translation("no_access", module="oob")
    
    @rx.var
    def t_oob_access_denied(self) -> str:
        """Traduction pour 'access_denied' (module oob)."""
        return self._get_translation("access_denied", module="oob")
    
    @rx.var
    def t_oob_access_denied_description(self) -> str:
        """Traduction pour 'access_denied_description' (module oob)."""
        return self._get_translation("access_denied_description", module="oob")
    
    @rx.var
    def t_oob_back_to_home(self) -> str:
        """Traduction pour 'back_to_home' (module oob)."""
        return self._get_translation("back_to_home", module="oob")
    
    @rx.var
    def t_oob_edit(self) -> str:
        """Traduction pour 'edit' (module oob)."""
        return self._get_translation("edit", module="oob")
    
    @rx.var
    def t_oob_edit_comment(self) -> str:
        """Traduction pour 'edit_comment' (module oob)."""
        return self._get_translation("edit_comment", module="oob")
    
    @rx.var
    def t_oob_save(self) -> str:
        """Traduction pour 'save' (module oob)."""
        return self._get_translation("save", module="oob")
    
    @rx.var
    def t_oob_modified(self) -> str:
        """Traduction pour 'modified' (module oob)."""
        return self._get_translation("modified", module="oob")
    
    @rx.var
    def t_oob_on(self) -> str:
        """Traduction pour 'on' (module oob)."""
        return self._get_translation("on", module="oob")
    
    @rx.var
    def t_oob_posted_on(self) -> str:
        """Traduction pour 'posted_on' (module oob)."""
        return self._get_translation("posted_on", module="oob")
    
    @rx.var
    def t_oob_last_modified(self) -> str:
        """Traduction pour 'last_modified' (module oob)."""
        return self._get_translation("last_modified", module="oob")
    
    @rx.var
    def t_oob_modified_on(self) -> str:
        """Traduction pour 'modified_on' (module oob)."""
        return self._get_translation("modified_on", module="oob")
    
    @rx.var
    def t_welcome_to_haleon(self) -> str:
        """Traduction pour 'welcome_to_haleon'."""
        return self._get_translation("welcome_to_haleon")
    
    @rx.var
    def t_select_app_from_nav(self) -> str:
        """Traduction pour 'select_app_from_nav'."""
        return self._get_translation("select_app_from_nav")
    
    @rx.var
    def t_available_applications(self) -> str:
        """Traduction pour 'available_applications'."""
        return self._get_translation("available_applications")
    
    @rx.var
    def t_no_applications_available(self) -> str:
        """Traduction pour 'no_applications_available'."""
        return self._get_translation("no_applications_available")
    
    @rx.var
    def t_account_must_be_validated(self) -> str:
        """Traduction pour 'account_must_be_validated'."""
        return self._get_translation("account_must_be_validated")
    
    @rx.var
    def t_access_button(self) -> str:
        """Traduction pour 'access' (bouton)."""
        return self._get_translation("access")
    
    @rx.var
    def t_no_description(self) -> str:
        """Traduction pour 'no_description'."""
        return self._get_translation("no_description")
    
    @rx.var
    def t_you_are_connected(self) -> str:
        """Traduction pour 'you_are_connected'."""
        return self._get_translation("you_are_connected")
    
    @rx.var
    def t_go_to_home(self) -> str:
        """Traduction pour 'go_to_home'."""
        return self._get_translation("go_to_home")
    
    @rx.var
    def t_connect_to_access(self) -> str:
        """Traduction pour 'connect_to_access'."""
        return self._get_translation("connect_to_access")
    
    @rx.var
    def t_access_denied_title(self) -> str:
        """Traduction pour 'access_denied_title'."""
        return self._get_translation("access_denied_title")
    
    @rx.var
    def t_no_rights_for_app(self) -> str:
        """Traduction pour 'no_rights_for_app'."""
        return self._get_translation("no_rights_for_app")
    
    @rx.var
    def t_account_not_active(self) -> str:
        """Traduction pour 'account_not_active'."""
        return self._get_translation("account_not_active")
    
    @rx.var
    def t_app_not_active(self) -> str:
        """Traduction pour 'app_not_active' (sans placeholder)."""
        return self._get_translation("app_not_active")
    
    @rx.var
    def t_app_requires_admin(self) -> str:
        """Traduction pour 'app_requires_admin'."""
        return self._get_translation("app_requires_admin")
    
    @rx.var
    def t_account_must_be_validated_for_app(self) -> str:
        """Traduction pour 'account_must_be_validated_for_app'."""
        return self._get_translation("account_must_be_validated_for_app")
    
    @rx.var
    def t_no_rights_for_app_with_requirement(self) -> str:
        """Traduction pour 'no_rights_for_app_with_requirement' (sans placeholder)."""
        return self._get_translation("no_rights_for_app_with_requirement")
    
    @rx.var
    def t_no_specific_access(self) -> str:
        """Traduction pour 'no_specific_access' (sans placeholder)."""
        return self._get_translation("no_specific_access")
    
    @rx.var
    def t_must_be_connected(self) -> str:
        """Traduction pour 'must_be_connected'."""
        return self._get_translation("must_be_connected")
    
    @rx.var
    def t_application_colon(self) -> str:
        """Traduction pour 'application_colon' (sans placeholder)."""
        return self._get_translation("application_colon")
    
    @rx.var
    def t_app_no_custom_page(self) -> str:
        """Traduction pour 'app_no_custom_page'."""
        return self._get_translation("app_no_custom_page")
    
    @rx.var
    def t_application_not_found_title(self) -> str:
        """Traduction pour 'application_not_found_title'."""
        return self._get_translation("application_not_found_title")
    
    @rx.var
    def t_no_app_found_with_code(self) -> str:
        """Traduction pour 'no_app_found_with_code'."""
        return self._get_translation("no_app_found_with_code")
    
    @rx.var
    def t_requirement_qty(self) -> str:
        """Traduction pour 'requirement_qty'."""
        return self._get_translation("requirement_qty")
    
    @rx.var
    def t_oob_user_access_management(self) -> str:
        """Traduction pour 'user_access_management' (module oob)."""
        return self._get_translation("user_access_management", module="oob")
    
    @rx.var
    def t_oob_vendor_management(self) -> str:
        """Traduction pour 'vendor_management' (module oob)."""
        return self._get_translation("vendor_management", module="oob")
    
    @rx.var
    def t_oob_user_vendor_access_tab(self) -> str:
        """Traduction pour 'user_vendor_access_tab' (module oob)."""
        return self._get_translation("user_vendor_access_tab", module="oob")
    
    @rx.var
    def t_oob_vendor_management_tab(self) -> str:
        """Traduction pour 'vendor_management_tab' (module oob)."""
        return self._get_translation("vendor_management_tab", module="oob")
    
    @rx.var
    def t_oob_search_access(self) -> str:
        """Traduction pour 'search_access' (module oob)."""
        return self._get_translation("search_access", module="oob")
    
    @rx.var
    def t_oob_validation_error(self) -> str:
        """Traduction pour 'validation_error' (module oob)."""
        return self._get_translation("validation_error", module="oob")
    
    @rx.var
    def t_oob_select_user_and_vendor(self) -> str:
        """Traduction pour 'select_user_and_vendor' (module oob)."""
        return self._get_translation("select_user_and_vendor", module="oob")
    
    @rx.var
    def t_oob_user_not_found(self) -> str:
        """Traduction pour 'user_not_found' (module oob)."""
        return self._get_translation("user_not_found", module="oob")
    
    @rx.var
    def t_oob_user_not_found_desc(self) -> str:
        """Traduction pour 'user_not_found_desc' (module oob)."""
        return self._get_translation("user_not_found_desc", module="oob")
    
    @rx.var
    def t_oob_vendor_not_found(self) -> str:
        """Traduction pour 'vendor_not_found' (module oob)."""
        return self._get_translation("vendor_not_found", module="oob")
    
    @rx.var
    def t_oob_vendor_not_found_desc(self) -> str:
        """Traduction pour 'vendor_not_found_desc' (module oob)."""
        return self._get_translation("vendor_not_found_desc", module="oob")
    
    @rx.var
    def t_oob_access_already_exists(self) -> str:
        """Traduction pour 'access_already_exists' (module oob)."""
        return self._get_translation("access_already_exists", module="oob")
    
    @rx.var
    def t_oob_access_already_exists_desc(self) -> str:
        """Traduction pour 'access_already_exists_desc' (module oob)."""
        return self._get_translation("access_already_exists_desc", module="oob")
    
    @rx.var
    def t_oob_access_granted_success(self) -> str:
        """Traduction pour 'access_granted_success' (module oob)."""
        return self._get_translation("access_granted_success", module="oob")
    
    @rx.var
    def t_oob_access_granted_success_desc(self) -> str:
        """Traduction pour 'access_granted_success_desc' (module oob)."""
        return self._get_translation("access_granted_success_desc", module="oob")
    
    @rx.var
    def t_oob_error_adding_access(self) -> str:
        """Traduction pour 'error_adding_access' (module oob)."""
        return self._get_translation("error_adding_access", module="oob")
    
    @rx.var
    def t_oob_error_adding_access_desc(self) -> str:
        """Traduction pour 'error_adding_access_desc' (module oob)."""
        return self._get_translation("error_adding_access_desc", module="oob")
    
    @rx.var
    def t_oob_access_revoked_success(self) -> str:
        """Traduction pour 'access_revoked_success' (module oob)."""
        return self._get_translation("access_revoked_success", module="oob")
    
    @rx.var
    def t_oob_error_revoking_access(self) -> str:
        """Traduction pour 'error_revoking_access' (module oob)."""
        return self._get_translation("error_revoking_access", module="oob")
    
    @rx.var
    def t_oob_vendor_updated(self) -> str:
        """Traduction pour 'vendor_updated' (module oob)."""
        return self._get_translation("vendor_updated", module="oob")
    
    @rx.var
    def t_oob_vendor_updated_desc(self) -> str:
        """Traduction pour 'vendor_updated_desc' (module oob)."""
        return self._get_translation("vendor_updated_desc", module="oob")
    
    @rx.var
    def t_oob_code_required(self) -> str:
        """Traduction pour 'code_required' (module oob)."""
        return self._get_translation("code_required", module="oob")
    
    @rx.var
    def t_oob_code_required_desc(self) -> str:
        """Traduction pour 'code_required_desc' (module oob)."""
        return self._get_translation("code_required_desc", module="oob")
    
    @rx.var
    def t_oob_code_invalid(self) -> str:
        """Traduction pour 'code_invalid' (module oob)."""
        return self._get_translation("code_invalid", module="oob")
    
    @rx.var
    def t_oob_code_invalid_desc(self) -> str:
        """Traduction pour 'code_invalid_desc' (module oob)."""
        return self._get_translation("code_invalid_desc", module="oob")
    
    @rx.var
    def t_oob_code_already_used(self) -> str:
        """Traduction pour 'code_already_used' (module oob)."""
        return self._get_translation("code_already_used", module="oob")
    
    @rx.var
    def t_oob_code_already_used_desc(self) -> str:
        """Traduction pour 'code_already_used_desc' (module oob)."""
        return self._get_translation("code_already_used_desc", module="oob")
    
    @rx.var
    def t_oob_vendor_created(self) -> str:
        """Traduction pour 'vendor_created' (module oob)."""
        return self._get_translation("vendor_created", module="oob")
    
    @rx.var
    def t_oob_vendor_created_desc(self) -> str:
        """Traduction pour 'vendor_created_desc' (module oob)."""
        return self._get_translation("vendor_created_desc", module="oob")
    
    @rx.var
    def t_oob_error_saving_vendor(self) -> str:
        """Traduction pour 'error_saving_vendor' (module oob)."""
        return self._get_translation("error_saving_vendor", module="oob")
    
    @rx.var
    def t_oob_error_saving_vendor_desc(self) -> str:
        """Traduction pour 'error_saving_vendor_desc' (module oob)."""
        return self._get_translation("error_saving_vendor_desc", module="oob")
    
    @rx.var
    def t_oob_vendor_deleted(self) -> str:
        """Traduction pour 'vendor_deleted' (module oob)."""
        return self._get_translation("vendor_deleted", module="oob")
    
    @rx.var
    def t_oob_vendor_deleted_desc(self) -> str:
        """Traduction pour 'vendor_deleted_desc' (module oob)."""
        return self._get_translation("vendor_deleted_desc", module="oob")
    
    @rx.var
    def t_oob_error_deleting_vendor(self) -> str:
        """Traduction pour 'error_deleting_vendor' (module oob)."""
        return self._get_translation("error_deleting_vendor", module="oob")
    
    @rx.var
    def t_oob_error_generic(self) -> str:
        """Traduction pour 'error_generic' (module oob)."""
        return self._get_translation("error_generic", module="oob")



