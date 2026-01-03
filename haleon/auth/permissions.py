"""Système de permissions en cascade pour Haleon."""

import logging
from haleon.db.model.users import Users
from haleon.db.model.applications import Applications
from haleon.db.database import get_session
from haleon.db.crud.user_app_access import get_user_app_access

logger = logging.getLogger("haleon.auth.permissions")

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
            logger.debug("can_access_app: user is None")
            return False
        
        if not user.is_active:
            logger.debug("can_access_app: user not active")
            return False
        
        if not app_code:
            logger.debug("can_access_app: app_code empty")
            return False
        
        # Normaliser le code en minuscule
        app_code_normalized = app_code.lower() if app_code else ""
        logger.debug("can_access_app start user=%s id=%s code=%s", user.email, user.id, app_code_normalized)
        
        # Récupérer l'application
        session_gen = get_session()
        session = next(session_gen)
        try:
            from haleon.db.crud.applications import get_application_by_code
            app = get_application_by_code(session, app_code_normalized)
            
            if not app:
                logger.debug("can_access_app: app not found (%s)", app_code_normalized)
                return False
            
            if not app.is_active:
                logger.debug("can_access_app: app not active (%s)", app_code_normalized)
                return False
            
            logger.debug("can_access_app: app found id=%s code=%s", app.id, app.code)
            
            # Vérifier le minimum_requirement (prérequis uniquement - ne donne pas l'accès)
            if not UserPermissions.can_access(user, app.minimum_requirement):
                logger.debug("can_access_app: minimum requirement not met (%s)", app.minimum_requirement)
                return False
            
            logger.debug("can_access_app: minimum requirement met (%s)", app.minimum_requirement)
            
            # VÉRIFICATION CRITIQUE : Un accès explicite dans UserApplicationAccess est OBLIGATOIRE
            access = get_user_app_access(session, user.id, app.id)
            
            if access is None:
                # PAS d'accès explicite → PAS d'accès (OBLIGATOIRE)
                logger.debug("can_access_app: no explicit access (user_id=%s app_id=%s)", user.id, app.id)
                return False
            
            # Un accès existe → accès autorisé
            logger.debug("can_access_app: access allowed (access_id=%s)", access.id)
            return True
        except Exception as e:
            logger.exception("can_access_app error for %s: %s", app_code, e)
            return False
        finally:
            session.close()







