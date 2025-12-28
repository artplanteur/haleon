"""Page dynamique pour charger les applications."""

import reflex as rx
from typing import Optional, Callable
from haleon.auth.auth_state import AuthState
from haleon.components.layout import layout
from haleon.components.callouts import access_denied_callout
from haleon.apps.loader import get_application_page
from haleon.db.database import get_session
from haleon.db.crud.applications import get_application_by_code
# Importer directement les pages des applications connues
try:
    from haleon.apps.oob.page import page as oob_page
except ImportError:
    oob_page = None


class AppViewState(AuthState):
    """État pour la page d'application - hérite de AuthState pour l'authentification."""
    
    # Note: app_code est automatiquement injecté par Reflex depuis la route [app_code]
    # Il ne faut PAS le déclarer ici car Reflex le fait automatiquement
    
    current_app_name: str = ""
    current_app_code: str = ""
    app_found: bool = False
    app_page_loaded: bool = False
    has_access: bool = True  # Par défaut True, sera mis à False si accès refusé
    access_denied_reason: str = ""
    _app_page_func: Optional[Callable] = None  # Fonction page() chargée dynamiquement
    
    def on_load(self):
        """Charge l'application au chargement de la page."""
        # S'assurer que l'utilisateur est chargé depuis la session (hérité de AuthState)
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        
        # app_code est automatiquement injecté par Reflex depuis la route [app_code]
        # Il est accessible via self.app_code sans avoir besoin de le déclarer
        if hasattr(self, 'app_code') and self.app_code:
            print(f"[DEBUG on_load] app_code injecté par Reflex: '{self.app_code}'")
            self.load_app(self.app_code)
        else:
            print(f"[DEBUG on_load] ✗ app_code non disponible ou vide")
            print(f"[DEBUG on_load] Attributs disponibles: {[a for a in dir(self) if not a.startswith('_')]}")
    
    def show_access_denied_toast(self):
        """Affiche un toast d'erreur pour accès refusé."""
        return rx.toast.error(
            self.t("access_denied_title"),
            description=self.access_denied_reason or self.t("no_rights_for_app")
        )
    
    def load_app(self, code: str):
        """Charge les informations de l'application et vérifie les permissions."""
        print(f"[DEBUG load_app] Code reçu: '{code}'")
        
        # Normaliser le code en minuscule pour correspondre aux URLs et aux dossiers
        # La recherche dans get_application_by_code est insensible à la casse
        code_normalized = code.lower() if code else ""
        print(f"[DEBUG load_app] Code normalisé (minuscule): '{code_normalized}'")
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            app = get_application_by_code(session, code_normalized)
            print(f"[DEBUG load_app] Application trouvée: {app.name if app else 'None'} (code: {app.code if app else 'None'})")
            if app:
                self.current_app_name = app.name
                self.current_app_code = app.code
                self.app_found = True
                
                # Mettre à jour le code de l'application courante dans SidebarState pour le menu
                from haleon.components.sidebar import SidebarState
                SidebarState.current_app_code_for_menu = app.code
                
                # Vérifier les permissions d'accès
                from haleon.auth.permissions import ApplicationPermissions
                
                # Utiliser directement self.current_user qui est hérité de AuthState
                # S'assurer que l'utilisateur est chargé depuis la session
                if not self.is_authenticated or not self.current_user:
                    # Essayer de charger depuis la session
                    self.load_user_from_session()
                
                user = self.current_user
                if user:
                    # Vérifier les permissions (utiliser le code de l'application trouvée)
                    if ApplicationPermissions.can_access_app(user, app.code):
                        self.has_access = True
                        # Essayer de charger la page de l'application dynamiquement
                        # Le loader cherche le dossier de manière insensible à la casse
                        print(f"[DEBUG load_app] Tentative de chargement de la page pour code: '{app.code}'")
                        app_page_func = get_application_page(app.code, app.code)
                        if app_page_func:
                            print(f"[DEBUG load_app] ✓ Fonction page() trouvée pour '{app.code}'")
                            # Stocker la fonction pour l'utiliser plus tard
                            self._app_page_func = app_page_func
                            # Tester l'appel de la fonction pour vérifier qu'elle fonctionne
                            try:
                                test_component = app_page_func()
                                print(f"[DEBUG load_app] ✓ Composant créé avec succès")
                                self.app_page_loaded = True
                            except Exception as e:
                                print(f"[DEBUG load_app] ✗ Erreur lors de la création du composant: {e}")
                                import traceback
                                traceback.print_exc()
                                self.app_page_loaded = False
                                self._app_page_func = None
                        else:
                            print(f"[DEBUG load_app] ✗ Aucune fonction page() trouvée pour '{app.code}'")
                            self.app_page_loaded = False
                            self._app_page_func = None
                    else:
                        self.has_access = False
                        # Déterminer la raison du refus
                        if not user.is_active:
                            self.access_denied_reason = self.t("account_not_active")
                        elif not app.is_active:
                            # Utiliser format pour remplacer {name}
                            app_not_active_template = self.t("app_not_active")
                            self.access_denied_reason = app_not_active_template.replace("{name}", app.name)
                        else:
                            # Vérifier le minimum_requirement
                            from haleon.auth.permissions import UserPermissions
                            if not UserPermissions.can_access(user, app.minimum_requirement):
                                if app.minimum_requirement == "admin":
                                    self.access_denied_reason = self.t("app_requires_admin")
                                elif app.minimum_requirement == "validated":
                                    self.access_denied_reason = self.t("account_must_be_validated_for_app")
                                else:
                                    # Utiliser format pour remplacer {requirement}
                                    no_rights_template = self.t("no_rights_for_app_with_requirement")
                                    self.access_denied_reason = no_rights_template.replace("{requirement}", app.minimum_requirement)
                            else:
                                # Utiliser format pour remplacer {name}
                                no_specific_template = self.t("no_specific_access")
                                self.access_denied_reason = no_specific_template.replace("{name}", app.name)
                else:
                    self.has_access = False
                    self.access_denied_reason = self.t("must_be_connected")
            else:
                self.app_found = False
                self.current_app_name = ""
                self.current_app_code = ""
                self.has_access = True  # Si l'app n'est pas trouvée, on affiche le message "introuvable" au lieu d'accès refusé
                self.access_denied_reason = ""
        finally:
            session.close()
    
    def get_app_page_component(self):
        """Charge et retourne le composant de la page de l'application."""
        # Utiliser la fonction stockée dans _app_page_func
        if self._app_page_func:
            try:
                return self._app_page_func()
            except Exception as e:
                print(f"[DEBUG get_app_page_component] Erreur: {e}")
                return None
        return None


def app_view_page() -> rx.Component:
    """Page pour afficher une application chargée dynamiquement."""
    
    # Message par défaut si pas de page personnalisée - sera construit dynamiquement
    def default_msg():
        """Message par défaut si pas de page personnalisée."""
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
    
    # Créer le composant OOB une seule fois (si disponible)
    _oob_component = oob_page() if oob_page else None
    
    def app_page_content():
        """Affiche la page de l'application si elle existe."""
        # Le composant a été chargé dans load_app() et stocké dans _app_page_func
        # Pour OOB, utiliser directement le composant importé (plus rapide et plus fiable)
        app_code = AppViewState.current_app_code
        
        # Pour OOB, utiliser directement le composant importé (insensible à la casse)
        is_oob = (
            (app_code == "OOB") | 
            (app_code == "oob") | 
            (app_code == "Oob") |
            (app_code == "OoB") |
            (app_code == "oOB")
        )
        
        # Si c'est OOB et que le composant est disponible, l'utiliser
        # Sinon, afficher le message par défaut
        # Note: Le composant chargé dynamiquement via le loader sera utilisé
        # si app_page_loaded est True, mais pour l'instant on utilise seulement OOB directement
        # Note: on_mount est déjà appelé dans la page OOB elle-même
        return rx.cond(
            is_oob & (_oob_component is not None),
            _oob_component,
            default_msg(),
        )
    
    def default_content():
        """Contenu par défaut si l'application n'est pas trouvée."""
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
        """Contenu affiché lorsque l'accès est refusé."""
        return layout(
            access_denied_callout(
                AppViewState.t_access_denied_title,
                AppViewState.access_denied_reason,
                AppViewState.t_back_to_home,
                "/home",
            )
        )
    
    return rx.fragment(
        # Afficher un toast d'erreur si l'accès est refusé
        rx.cond(
            AppViewState.app_found & ~AppViewState.has_access,
            rx.box(
                on_mount=AppViewState.show_access_denied_toast
            ),
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
                            # Afficher la page de l'application
                            app_page_content(),
                            layout(
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
                            ),
                        ),
                        access_denied_content(),
                    ),
                default_content(),
            ),
            rx.box(
                on_mount=rx.redirect("/")
            ),
        ),
    )
