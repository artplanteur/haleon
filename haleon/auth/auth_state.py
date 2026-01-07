"""État d'authentification global avec simulation SSO."""

import reflex as rx
from typing import Optional
from datetime import datetime
import uuid
import os
import logging
from http.cookies import SimpleCookie
from haleon.db.model.users import Users
from haleon.db.database import get_session
from haleon.db.crud.users import (
    get_user_by_email,
    create_user,
    update_user,
    login_user,
    touch_user_last_seen,
    logout_user,
)
from haleon.auth.permissions import UserPermissions
from haleon.state.i18n_state import I18nState
from sqlmodel import SQLModel

logger = logging.getLogger("haleon.auth")

class UserView(SQLModel):
    """UI-safe snapshot of a user (NOT an ORM object)."""

    id: Optional[int] = None
    email: str = ""
    family_name: Optional[str] = None
    first_name: Optional[str] = None
    country: Optional[str] = None

    is_connected: bool = False
    is_validated: bool = False
    is_active: bool = False
    is_admin: bool = False

    last_login_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    last_connection: Optional[datetime] = None  # legacy


class AuthState(I18nState):
    """État d'authentification global pour l'application."""
    
    state_auto_setters: bool = True
    
    # Session ID (server-side), read from the HttpOnly cookie in request headers.
    # IMPORTANT: Do NOT use rx.Cookie here if you want HttpOnly security.
    session_id: str = ""

    # Utilisateur connecté (snapshot sérialisable)
    current_user: Optional[UserView] = None
    is_authenticated: bool = False
    
    # Permissions (mises à jour automatiquement)
    is_active: bool = False
    is_validated: bool = False
    is_admin: bool = False
    
    # Session (pour l'affichage)
    session_start_time: Optional[datetime] = None
    session_duration: int = 3600  # 1 heure en secondes
    
    # Applications accessibles (stockées comme liste de dict pour rx.foreach)
    accessible_apps: list[dict] = []
    _refresh_apps_trigger: int = 0  # Trigger pour forcer le rechargement des applications
    _loading_apps: bool = False  # Flag pour éviter les appels multiples

    # SSO is handled server-side by /auth/login and /auth/callback (HttpOnly cookie).
    sso_error: str = ""
    # Default to fake login for local/dev when no .env is present.
    # Set to True (and provide SSO env vars) to enable real SSO.
    sso_use_real: bool = False

    def _cookie_session_id(self) -> str:
        """Read the HttpOnly `session_id` cookie from router headers (server-side)."""
        headers = (self.router_data or {}).get("headers") or {}
        cookie_header = headers.get("cookie") or ""
        if not cookie_header:
            return ""
        try:
            c = SimpleCookie()
            c.load(cookie_header)
            return (c.get("session_id").value if c.get("session_id") else "") or ""
        except Exception:
            return ""

    def _auth_backend(self) -> str:
        """Backend base URL for auth endpoints (dev: http://localhost:8000)."""
        return (os.getenv("BACKEND_BASE_URL") or "http://localhost:8000").rstrip("/")

    def _auth_url(self, path: str) -> str:
        base = self._auth_backend()
        if not path.startswith("/"):
            path = "/" + path
        return base + path

    def _to_user_view(self, user: Optional[Users]) -> Optional[UserView]:
        """Convert ORM Users -> UI-safe snapshot."""
        if not user:
            return None
        return UserView(
            id=getattr(user, "id", None),
            email=getattr(user, "email", "") or "",
            family_name=getattr(user, "family_name", None),
            first_name=getattr(user, "first_name", None),
            country=getattr(user, "country", None),
            is_connected=bool(getattr(user, "is_connected", False)),
            is_validated=bool(getattr(user, "is_validated", False)),
            is_active=bool(getattr(user, "is_active", False)),
            is_admin=bool(getattr(user, "is_admin", False)),
            last_login_at=getattr(user, "last_login_at", None),
            last_seen_at=getattr(user, "last_seen_at", None),
            last_connection=getattr(user, "last_connection", None),
        )
    
    def load_user_from_session(self):
        """Charge l'utilisateur depuis la session (cookie HttpOnly session_id)."""
        session_id_to_use = self._cookie_session_id()
        self.session_id = session_id_to_use  # server-side copy for DB lookups
        logger.debug("load_user_from_session start (cookie session_id present=%s)", bool(session_id_to_use))
        
        # Vérifier si session_id existe
        if not session_id_to_use or session_id_to_use == "":
            logger.debug("load_user_from_session: no session_id cookie")
            self.is_authenticated = False
            self.current_user = None
            self.accessible_apps = []  # VIDER les apps si pas de session
            return
        
        # Charger l'utilisateur depuis la BDD en utilisant le session_id
        session_gen = get_session()
        session = next(session_gen)
        try:
            from haleon.db.crud.users import get_user_by_session_id
            user = get_user_by_session_id(session, session_id_to_use)
            
            if user and user.is_connected:
                # VÉRIFICATION D'EXPIRATION : session idle timeout basé sur last_seen_at
                now = datetime.now()
                last_seen = (
                    user.last_seen_at
                    or user.last_login_at
                    or user.last_connection
                    or now
                )
                elapsed = (now - last_seen).total_seconds()
                
                if elapsed > self.session_duration:
                    # Session expirée - déconnecter l'utilisateur
                    logger.info("session expired (elapsed=%ss, max=%ss)", int(elapsed), int(self.session_duration))
                    logout_user(session=session, user=user, audit_user=None, audit_source="auth/expire")
                    
                    # Nettoyer l'état
                    self.session_id = ""
                    self.is_authenticated = False
                    self.current_user = None
                    self.accessible_apps = []
                    # Clear HttpOnly cookie via backend route.
                    return rx.redirect(self._auth_url("/auth/logout"))
                
                # Session valide
                # Mettre à jour last_seen_at (heartbeat) côté serveur.
                user = touch_user_last_seen(session=session, user=user, audit_user=None, audit_source="auth/seen")
                user_view = self._to_user_view(user)
                self.current_user = user_view
                self.is_authenticated = bool(user_view and user_view.is_connected)
                # Pour l'UI: compte à rebours basé sur le dernier "seen".
                self.session_start_time = (user_view.last_seen_at if user_view else None) or now
                # Mettre à jour les permissions
                self.is_active = UserPermissions.is_active_user(user_view) if user_view else False
                self.is_validated = UserPermissions.is_validated_user(user_view) if user_view else False
                self.is_admin = UserPermissions.is_admin_user(user_view) if user_view else False
                
                # VIDER les apps - elles seront rechargées par le layout avec les bonnes vérifications
                self.accessible_apps = []
                self._loading_apps = False
                
                # Ne pas charger les applications ici, c'est fait dans le layout pour éviter les appels multiples
                # Les applications seront chargées automatiquement par le layout si nécessaire
            else:
                # Session invalide, nettoyer
                self.session_id = ""
                self.is_authenticated = False
                self.current_user = None
                self.accessible_apps = []  # VIDER les apps si session invalide
        finally:
            session.close()
    
    def get_session_remaining_time(self) -> int:
        """Calcule le temps restant de la session en secondes."""
        if not self.session_start_time or not self.current_user:
            return 0
        elapsed = (datetime.now() - self.session_start_time).total_seconds()
        remaining = self.session_duration - elapsed
        return max(0, int(remaining))
    
    @rx.var
    def get_session_remaining_formatted(self) -> str:
        """Retourne le temps restant formaté (MM:SS)."""
        remaining = self.get_session_remaining_time()
        minutes = remaining // 60
        seconds = remaining % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def simulate_sso_login(self):
        """Simule une connexion SSO avec John Doe."""
        # ==========================================================
        # DELETE WHEN REAL SSO IS LIVE:
        # - Remove this whole method
        # - Switch UI login button to `start_sso_login`
        # ==========================================================
        # Données de l'utilisateur de test
        email = "john.doe@haleon.com"
        first_name = "John"
        family_name = "Doe"
        country = "FR"
        
        # Générer un ID de session unique
        session_id = str(uuid.uuid4())
        session_start = datetime.now()
        
        # Récupérer ou créer l'utilisateur dans la BDD
        session_gen = get_session()
        session = next(session_gen)
        try:
            user = get_user_by_email(session, email)
            
            if user:
                # Mettre à jour le profil puis login (timestamps + session_id)
                user = update_user(
                    session=session,
                    user=user,
                    family_name=family_name,
                    first_name=first_name,
                    country=country,
                    audit_user=None,
                    audit_source="auth/login",
                )
                user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/login")
            else:
                # Créer un nouvel utilisateur (is_validated = False par défaut selon le README)
                # Vérifier dynamiquement dans la BDD si l'utilisateur existe déjà avec des droits admin
                # (peut arriver si le seed a créé l'utilisateur avant la connexion)
                existing_user = get_user_by_email(session, email)
                if existing_user:
                    # L'utilisateur existe déjà (créé par le seed), utiliser ses permissions existantes
                    user = update_user(
                        session=session,
                        user=existing_user,
                        family_name=family_name,
                        first_name=first_name,
                        country=country,
                        audit_user=None,
                        audit_source="auth/login",
                    )
                    user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/login")
                else:
                    # Créer un nouvel utilisateur avec is_admin=False par défaut
                    user = create_user(
                        session=session,
                        email=email,
                        family_name=family_name,
                        first_name=first_name,
                        country=country,
                        is_admin=False,
                        is_connected=False,
                        audit_user=None,
                        audit_source="auth/login",
                    )
                    # Selon le README, nouvel utilisateur = is_validated = False
                    user.is_validated = False
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                    user = login_user(session=session, user=user, session_id=session_id, audit_user=None, audit_source="auth/login")
            
            # DEV ONLY: this does NOT set an HttpOnly cookie (real SSO uses /auth/login + /auth/callback).
            # We keep the server-side copy for consistency with the rest of the state.
            self.session_id = session_id
            logger.debug("simulate_sso_login issued session (dev only)")
            
            # Mettre à jour l'état Reflex (pour l'UI réactive) - snapshot (pas ORM)
            user_view = self._to_user_view(user)
            self.current_user = user_view
            self.is_authenticated = bool(user_view and user_view.is_connected)
            self.session_start_time = (user_view.last_seen_at if user_view else None) or session_start
            
            # Mettre à jour les permissions
            self.is_active = UserPermissions.is_active_user(user_view) if user_view else False
            self.is_validated = UserPermissions.is_validated_user(user_view) if user_view else False
            self.is_admin = UserPermissions.is_admin_user(user_view) if user_view else False
            
            # Charger les applications accessibles
            self.load_accessible_applications()
            
            # Afficher un toast de confirmation
            rx.toast.success(f"Connexion réussie ! Bienvenue {first_name} {family_name}")
            
        except Exception as e:
            rx.toast.error(f"Erreur lors de la connexion: {str(e)}")
        finally:
            session.close()
    
    def start_sso_login(self):
        """Start SSO redirect (server-side).

        /auth/login starts the PKCE flow and redirects to the IdP.
        /auth/callback completes it and sets the HttpOnly session cookie.
        """
        if not self.sso_use_real:
            # DEV mode: keep dummy SSO user, but set HttpOnly cookie server-side.
            return rx.redirect(self._auth_url("/auth/dev-login"))
        return rx.redirect(self._auth_url("/auth/login"))

    def redirect_after_login(self):
        """Redirige vers la page d'accueil après connexion."""
        return rx.redirect("/home")
    
    def logout(self):
        """Déconnecte l'utilisateur."""
        # Clear Reflex state immediately.
        self.session_id = ""
        self.current_user = None
        self.is_authenticated = False
        self.is_active = False
        self.is_validated = False
        self.is_admin = False
        self.session_start_time = None
        self.accessible_apps = []
        # Clear HttpOnly cookie server-side.
        return rx.redirect(self._auth_url("/auth/logout"))
    
    def can_access_level(self, level: str) -> bool:
        """Vérifie l'accès à un niveau donné (active, validated, admin)."""
        if not self.current_user:
            return False
        return UserPermissions.can_access(self.current_user, level)
    
    def get_current_user_id(self) -> Optional[int]:
        """Retourne l'ID de l'utilisateur actuellement connecté (pour usage dans d'autres states)."""
        if not self.current_user:
            return None
        return self.current_user.id
    
    @rx.var
    def get_user_initials(self) -> str:
        """Retourne les initiales de l'utilisateur."""
        if not self.current_user:
            return "??"
        
        initials = ""
        if self.current_user.first_name:
            initials += self.current_user.first_name[0].upper()
        if self.current_user.family_name:
            initials += self.current_user.family_name[0].upper()
        
        return initials if initials else "U"
    
    def load_accessible_applications(self):
        """Charge les applications accessibles et les stocke dans accessible_apps.
        
        IMPORTANT : Seules les applications avec un accès explicite dans UserApplicationAccess
        seront ajoutées à la liste. Pas d'accès = pas d'application visible.
        """
        # Éviter les appels multiples : vérifier si déjà en cours
        if self._loading_apps:
            logger.debug("load_accessible_applications: already loading, skip")
            return
        
        # VÉRIFICATION STRICTE : utilisateur doit être authentifié ET current_user doit exister
        if not self.is_authenticated:
            logger.debug("load_accessible_applications: not authenticated")
            self.accessible_apps = []
            return
        
        if not self.current_user:
            logger.debug("load_accessible_applications: current_user is None")
            self.accessible_apps = []
            return
        
        if not self.current_user.is_active:
            logger.debug("load_accessible_applications: user not active")
            self.accessible_apps = []
            return
        
        logger.debug(
            "load_accessible_applications start user=%s id=%s active=%s validated=%s admin=%s",
            self.current_user.email,
            self.current_user.id,
            self.current_user.is_active,
            self.current_user.is_validated,
            self.current_user.is_admin,
        )
        
        # FORCER le rechargement en vidant d'abord la liste pour éviter le cache
        self.accessible_apps = []
        self._loading_apps = True
        logger.debug("load_accessible_applications: list cleared, loading...")
        
        from haleon.db.crud.applications import get_active_applications
        from haleon.auth.permissions import ApplicationPermissions
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            apps = get_active_applications(session)
            logger.debug("load_accessible_applications: %s active apps in DB", len(apps))
            
            # Filtrer selon les permissions et convertir en dict
            # SEULEMENT les apps avec un accès explicite seront ajoutées
            accessible_apps = []
            for app in apps:
                app_code = app.code if app.code else ""
                if not app_code:
                    logger.debug("load_accessible_applications: app id=%s has empty code, skip", app.id)
                    continue
                
                logger.debug("load_accessible_applications: check access app=%s code=%s id=%s", app.name, app_code, app.id)
                
                # VÉRIFICATION DIRECTE dans la BDD AVANT d'appeler can_access_app
                from haleon.db.crud.user_app_access import get_user_app_access
                direct_access_check = get_user_app_access(session, self.current_user.id, app.id)
                if direct_access_check:
                    logger.debug("load_accessible_applications: direct access found (access_id=%s)", direct_access_check.id)
                else:
                    logger.debug("load_accessible_applications: no direct access (user_id=%s app_id=%s)", self.current_user.id, app.id)
                
                # VÉRIFICATION CRITIQUE : can_access_app vérifie l'accès explicite
                can_access = ApplicationPermissions.can_access_app(self.current_user, app_code)
                
                if can_access:
                    logger.debug("load_accessible_applications: app added (allowed)")
                    accessible_apps.append({
                        "id": app.id,
                        "name": app.name,
                        "code": app.code,
                        "route": app.route,
                        "icon": app.icon or "",
                        "description": app.description or "",
                    })
                else:
                    logger.debug("load_accessible_applications: app excluded (no explicit access)")
            
            logger.debug("load_accessible_applications done: accessible=%s of total=%s", len(accessible_apps), len(apps))
            self.accessible_apps = accessible_apps
            # Incrémenter le trigger pour forcer la mise à jour
            self._refresh_apps_trigger += 1
        except Exception as e:
            logger.exception("load_accessible_applications error: %s", e)
            self.accessible_apps = []
        finally:
            self._loading_apps = False
            session.close()
    
    def force_reload_applications(self):
        """Force le rechargement des applications accessibles.
        
        SIMPLE : Vide la liste et recharge depuis la BDD.
        Le trigger sera incrémenté par load_accessible_applications().
        """
        # Vider la liste pour forcer le rechargement
        self.accessible_apps = []
        # Réinitialiser le flag de chargement pour permettre le rechargement
        self._loading_apps = False
        # Recharger les applications (qui incrémentera le trigger)
        self.load_accessible_applications()
    
    @rx.var
    def get_accessible_applications(self) -> list:
        """Retourne les applications accessibles (pour compatibilité)."""
        return self.accessible_apps
    
    def redirect(self, url: str):
        """Redirige vers une URL."""
        return rx.redirect(url)
    
    def redirect_to_home(self):
        """Redirige vers la page d'accueil."""
        return rx.redirect("/home")
    
    def redirect_to_login(self):
        """Redirige vers la page d'accueil (connexion via navbar)."""
        return rx.redirect("/")
    
    def handle_login_and_redirect(self):
        """Gère la connexion et redirige."""
        # Faire la connexion
        self.simulate_sso_login()
        # Rediriger vers home
        return rx.redirect("/home")
    
    def handle_unauthorized_access(self):
        """Affiche un toast d'erreur et redirige vers la page d'accueil."""
        # Afficher le toast d'erreur
        rx.toast.error(
            "Accès refusé",
            description="Vous n'avez pas les droits d'administration nécessaires pour accéder à cette page."
        )
        # Rediriger vers la page d'accueil
        return rx.redirect("/home")

