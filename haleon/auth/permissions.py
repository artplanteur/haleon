"""Système de permissions en cascade pour Haleon."""

from haleon.db.model.users import Users
from haleon.db.model.applications import Applications
from haleon.db.database import get_session
from haleon.db.crud.user_app_access import get_user_app_access


class UserPermissions:
    """Gestion des permissions utilisateur en cascade."""
    
    @staticmethod
    def is_active_user(user: Users) -> bool:
        """Vérifie si l'utilisateur est actif."""
        return user.is_active
    
    @staticmethod
    def is_validated_user(user: Users) -> bool:
        """Vérifie si l'utilisateur est validé (nécessite d'être actif)."""
        if not UserPermissions.is_active_user(user):
            return False
        return user.is_validated
    
    @staticmethod
    def is_admin_user(user: Users) -> bool:
        """Vérifie si l'utilisateur est admin (nécessite d'être validé)."""
        if not UserPermissions.is_validated_user(user):
            return False
        return user.is_admin
    
    @staticmethod
    def can_access(user: Users, level: str) -> bool:
        """
        Vérifie l'accès à un niveau donné.
        Niveaux : "active", "validated", "admin"
        """
        if level == "active":
            return UserPermissions.is_active_user(user)
        elif level == "validated":
            return UserPermissions.is_validated_user(user)
        elif level == "admin":
            return UserPermissions.is_admin_user(user)
        return False


class ApplicationPermissions:
    """Gestion des permissions d'accès aux applications."""
    
    @staticmethod
    def can_access_app(user: Users, app_code: str) -> bool:
        """
        Vérifie si l'utilisateur peut accéder à une application.
        
        SIMPLE : Un accès explicite dans UserApplicationAccess est OBLIGATOIRE.
        Le minimum_requirement sert uniquement de prérequis pour qu'un admin puisse accorder un accès,
        mais ne donne PAS l'accès automatiquement.
        
        Logique :
        1. Vérifier que l'utilisateur existe et est actif
        2. Récupérer l'application (doit exister et être active)
        3. Vérifier le minimum_requirement (prérequis uniquement)
        4. Vérifier s'il existe un accès explicite dans UserApplicationAccess
           - Si OUI → accès autorisé
           - Si NON → PAS d'accès (RETOURNE FALSE)
        """
        # VÉRIFICATION STRICTE : utilisateur doit exister et être actif
        if not user:
            print(f"[DEBUG can_access_app] ÉCHEC: Utilisateur est None")
            return False
        
        if not user.is_active:
            print(f"[DEBUG can_access_app] ÉCHEC: Utilisateur {user.email if user else 'None'} n'est pas actif")
            return False
        
        if not app_code:
            print(f"[DEBUG can_access_app] ÉCHEC: app_code est vide")
            return False
        
        # Normaliser le code en minuscule
        app_code_normalized = app_code.lower() if app_code else ""
        print(f"[DEBUG can_access_app] Début vérification - user: {user.email} (id={user.id}), app_code: {app_code} (normalisé: {app_code_normalized})")
        
        # Récupérer l'application
        session_gen = get_session()
        session = next(session_gen)
        try:
            from haleon.db.crud.applications import get_application_by_code
            app = get_application_by_code(session, app_code_normalized)
            
            if not app:
                print(f"[DEBUG can_access_app] ÉCHEC: Application '{app_code_normalized}' non trouvée")
                return False
            
            if not app.is_active:
                print(f"[DEBUG can_access_app] ÉCHEC: Application '{app.name}' n'est pas active")
                return False
            
            print(f"[DEBUG can_access_app] Application trouvée: {app.name} (id={app.id}, code={app.code}, minimum_requirement={app.minimum_requirement})")
            
            # Vérifier le minimum_requirement (prérequis uniquement - ne donne pas l'accès)
            if not UserPermissions.can_access(user, app.minimum_requirement):
                print(f"[DEBUG can_access_app] ÉCHEC: Utilisateur ne satisfait pas le minimum_requirement '{app.minimum_requirement}'")
                return False
            
            print(f"[DEBUG can_access_app] Minimum requirement satisfait: {app.minimum_requirement}")
            
            # VÉRIFICATION CRITIQUE : Un accès explicite dans UserApplicationAccess est OBLIGATOIRE
            access = get_user_app_access(session, user.id, app.id)
            
            if access is None:
                # PAS d'accès explicite → PAS d'accès (OBLIGATOIRE)
                print(f"[DEBUG can_access_app] ÉCHEC CRITIQUE: Aucun accès explicite trouvé pour user_id={user.id}, app_id={app.id} (code={app.code})")
                print(f"[DEBUG can_access_app] RETOUR: False (pas d'accès explicite dans UserApplicationAccess)")
                return False
            
            # Un accès existe → accès autorisé
            print(f"[DEBUG can_access_app] SUCCÈS: Accès trouvé (id={access.id}) → ACCÈS AUTORISÉ")
            return True
        except Exception as e:
            print(f"[DEBUG can_access_app] ERREUR lors de la vérification d'accès à l'application {app_code}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            session.close()







