"""État d'authentification global avec simulation SSO."""

import reflex as rx
from typing import Optional
from datetime import datetime, timedelta
import uuid
from haleon.db.model.users import Users
from haleon.db.database import get_session
from haleon.db.crud.users import get_user_by_email, create_user, update_user
from haleon.auth.permissions import UserPermissions
from haleon.state.i18n_state import I18nState


class AuthState(I18nState):
    """État d'authentification global pour l'application."""
    
    state_auto_setters: bool = True
    
    # Session serveur persistante (stockée dans LocalStorage avec synchronisation entre onglets)
    # LocalStorage avec sync=True permet la persistance ET la synchronisation automatique entre tous les onglets
    # IMPORTANT: name="session_id" permet de partager la même clé LocalStorage
    # entre AuthState et ses sous-classes (admin pages, OOB, etc.).
    session_id: str = rx.LocalStorage(sync=True, name="session_id")
    
    # Utilisateur connecté (chargé depuis la BDD via session_id)
    current_user: Optional[Users] = None
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
    
    def load_user_from_session(self):
        """Charge l'utilisateur depuis la session serveur (session_id stocké dans LocalStorage)."""
        # LocalStorage avec sync=True permet la persistance ET la synchronisation automatique entre tous les onglets
        # La valeur est accessible comme une chaîne normale dans les méthodes Python
        session_id_to_use = self.session_id if self.session_id else ""
        print(f"[DEBUG load_user_from_session] Début - session_id (LocalStorage): '{session_id_to_use}'")
        
        # Vérifier si session_id existe
        if not session_id_to_use or session_id_to_use == "":
            print("[DEBUG load_user_from_session] Aucune session_id trouvée dans LocalStorage")
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
                # VÉRIFICATION D'EXPIRATION : Vérifier si la session a expiré
                session_start = user.last_connection or datetime.now()
                elapsed = (datetime.now() - session_start).total_seconds()
                
                if elapsed > self.session_duration:
                    # Session expirée - déconnecter l'utilisateur
                    print(f"[DEBUG load_user_from_session] Session expirée (élapsed: {elapsed:.0f}s, max: {self.session_duration}s)")
                    user.is_connected = False
                    session.add(user)
                    session.commit()
                    
                    # Nettoyer l'état
                    self.session_id = ""  # Vider LocalStorage
                    self.is_authenticated = False
                    self.current_user = None
                    self.accessible_apps = []
                    return
                
                # Session valide
                self.current_user = user
                self.is_authenticated = True
                self.session_start_time = session_start
                
                # Mettre à jour les permissions
                self.is_active = UserPermissions.is_active_user(user)
                self.is_validated = UserPermissions.is_validated_user(user)
                self.is_admin = UserPermissions.is_admin_user(user)
                
                # VIDER les apps - elles seront rechargées par le layout avec les bonnes vérifications
                self.accessible_apps = []
                self._loading_apps = False
                
                # Ne pas charger les applications ici, c'est fait dans le layout pour éviter les appels multiples
                # Les applications seront chargées automatiquement par le layout si nécessaire
            else:
                # Session invalide, nettoyer
                self.session_id = ""  # Vider LocalStorage
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
                # Mettre à jour l'utilisateur existant
                user = update_user(
                    session=session,
                    user=user,
                    family_name=family_name,
                    first_name=first_name,
                    country=country,
                    session_id=session_id,
                    is_connected=True,
                )
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
                        session_id=session_id,
                        is_connected=True,
                    )
                else:
                    # Créer un nouvel utilisateur avec is_admin=False par défaut
                    user = create_user(
                        session=session,
                        email=email,
                        family_name=family_name,
                        first_name=first_name,
                        country=country,
                        session_id=session_id,
                        is_admin=False,
                    )
                    # Selon le README, nouvel utilisateur = is_validated = False
                    user.is_validated = False
                    session.add(user)
                    session.commit()
                    session.refresh(user)
            
            # Stocker le session_id dans LocalStorage (PERSISTANT entre les onglets)
            # LocalStorage avec sync=True permet la persistance ET la synchronisation automatique entre tous les onglets
            self.session_id = session_id
            print(f"[DEBUG simulate_sso_login] Session ID sauvegardé dans LocalStorage: {session_id}")
            
            # Mettre à jour l'état Reflex (pour l'UI réactive)
            self.current_user = user
            self.is_authenticated = True
            self.session_start_time = session_start
            
            # Mettre à jour les permissions
            self.is_active = UserPermissions.is_active_user(user)
            self.is_validated = UserPermissions.is_validated_user(user)
            self.is_admin = UserPermissions.is_admin_user(user)
            
            # Charger les applications accessibles
            self.load_accessible_applications()
            
            # Afficher un toast de confirmation
            rx.toast.success(f"Connexion réussie ! Bienvenue {first_name} {family_name}")
            
        except Exception as e:
            rx.toast.error(f"Erreur lors de la connexion: {str(e)}")
        finally:
            session.close()
    
    def redirect_after_login(self):
        """Redirige vers la page d'accueil après connexion."""
        return rx.redirect("/home")
    
    def logout(self):
        """Déconnecte l'utilisateur."""
        if self.current_user:
            # Mettre à jour la BDD
            session_gen = get_session()
            session = next(session_gen)
            try:
                user = get_user_by_email(session, self.current_user.email)
                if user:
                    user.is_connected = False
                    session.add(user)
                    session.commit()
            finally:
                session.close()
        
        # Nettoyer la session serveur
        self.session_id = ""
        
        # Réinitialiser l'état Reflex
        self.current_user = None
        self.is_authenticated = False
        self.is_active = False
        self.is_validated = False
        self.is_admin = False
        self.session_start_time = None
        self.accessible_apps = []
    
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
            print("[DEBUG load_accessible_applications] Déjà en cours de chargement, ignoré")
            return
        
        # VÉRIFICATION STRICTE : utilisateur doit être authentifié ET current_user doit exister
        if not self.is_authenticated:
            print("[DEBUG load_accessible_applications] ÉCHEC: Utilisateur non authentifié")
            self.accessible_apps = []
            return
        
        if not self.current_user:
            print("[DEBUG load_accessible_applications] ÉCHEC: current_user est None")
            self.accessible_apps = []
            return
        
        if not self.current_user.is_active:
            print(f"[DEBUG load_accessible_applications] ÉCHEC: Utilisateur {self.current_user.email} n'est pas actif")
            self.accessible_apps = []
            return
        
        print(f"[DEBUG load_accessible_applications] Début - user: {self.current_user.email} (id={self.current_user.id}), is_active={self.current_user.is_active}, is_validated={self.current_user.is_validated}, is_admin={self.current_user.is_admin}")
        
        # FORCER le rechargement en vidant d'abord la liste pour éviter le cache
        self.accessible_apps = []
        self._loading_apps = True
        print(f"[DEBUG load_accessible_applications] Liste vidée, début du chargement...")
        
        from haleon.db.crud.applications import get_active_applications
        from haleon.auth.permissions import ApplicationPermissions
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            apps = get_active_applications(session)
            print(f"[DEBUG load_accessible_applications] {len(apps)} applications actives trouvées dans la BDD")
            
            # Filtrer selon les permissions et convertir en dict
            # SEULEMENT les apps avec un accès explicite seront ajoutées
            accessible_apps = []
            for app in apps:
                app_code = app.code if app.code else ""
                if not app_code:
                    print(f"[DEBUG load_accessible_applications] Application {app.name} (id={app.id}) a un code vide, IGNORÉE")
                    continue
                
                print(f"[DEBUG load_accessible_applications] Vérification accès pour app: {app.name} (code: {app_code}, id={app.id})")
                
                # VÉRIFICATION DIRECTE dans la BDD AVANT d'appeler can_access_app
                from haleon.db.crud.user_app_access import get_user_app_access
                direct_access_check = get_user_app_access(session, self.current_user.id, app.id)
                if direct_access_check:
                    print(f"[DEBUG load_accessible_applications] ⚠️  ACCÈS TROUVÉ DIRECTEMENT dans la BDD pour {app.name} (access_id={direct_access_check.id})")
                else:
                    print(f"[DEBUG load_accessible_applications] ⚠️  AUCUN ACCÈS dans la BDD pour {app.name} (user_id={self.current_user.id}, app_id={app.id})")
                
                # VÉRIFICATION CRITIQUE : can_access_app vérifie l'accès explicite
                can_access = ApplicationPermissions.can_access_app(self.current_user, app_code)
                
                if can_access:
                    print(f"[DEBUG load_accessible_applications] ✓ Application {app.name} AJOUTÉE (accès autorisé)")
                    accessible_apps.append({
                        "id": app.id,
                        "name": app.name,
                        "code": app.code,
                        "route": app.route,
                        "icon": app.icon or "",
                        "description": app.description or "",
                    })
                else:
                    print(f"[DEBUG load_accessible_applications] ✗ Application {app.name} EXCLUE (pas d'accès explicite)")
            
            print(f"[DEBUG load_accessible_applications] RÉSULTAT FINAL: {len(accessible_apps)} applications accessibles sur {len(apps)} applications actives")
            self.accessible_apps = accessible_apps
            # Incrémenter le trigger pour forcer la mise à jour
            self._refresh_apps_trigger += 1
        except Exception as e:
            print(f"[DEBUG load_accessible_applications] ERREUR lors du chargement: {e}")
            import traceback
            traceback.print_exc()
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

