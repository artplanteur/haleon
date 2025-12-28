"""Opérations CRUD pour l'application OOB."""

from sqlmodel import Session, select
from typing import Optional, List
from haleon.apps.oob.db.models import OOBVendor, OOBComment, OOBUserVendorAccess
from haleon.db.model.users import Users
from haleon.db.audit_logger import AuditLogger


# ========== VENDOR CRUD ==========

def create_vendor(
    session: Session,
    code: str,
    description: Optional[str] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> OOBVendor:
    """Crée un nouveau vendor.
    
    Args:
        session: Session SQLModel
        code: Code du vendor (max 5 caractères)
        description: Description du vendor
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin", "seed")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        vendor = OOBVendor(
            code=code.upper()[:5],  # S'assurer que le code est en majuscules et max 5 caractères
            description=description,
        )
        session.add(vendor)
        session.commit()
        session.refresh(vendor)
    return vendor


def get_all_vendors(session: Session) -> List[OOBVendor]:
    """Récupère tous les vendors."""
    statement = select(OOBVendor).order_by(OOBVendor.code)
    return list(session.exec(statement).all())


def get_vendor_by_id(session: Session, vendor_id: int) -> Optional[OOBVendor]:
    """Récupère un vendor par son ID."""
    return session.get(OOBVendor, vendor_id)


def get_vendor_by_code(session: Session, code: str) -> Optional[OOBVendor]:
    """Récupère un vendor par son code."""
    statement = select(OOBVendor).where(OOBVendor.code == code.upper())
    return session.exec(statement).first()


def update_vendor(
    session: Session,
    vendor: OOBVendor,
    code: Optional[str] = None,
    description: Optional[str] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> OOBVendor:
    """Met à jour un vendor.
    
    Args:
        session: Session SQLModel
        vendor: Vendor à mettre à jour
        code: Nouveau code
        description: Nouvelle description
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        if code is not None:
            vendor.code = code.upper()[:5]
        if description is not None:
            vendor.description = description
        
        session.add(vendor)
        session.commit()
        session.refresh(vendor)
    return vendor


def delete_vendor(
    session: Session,
    vendor_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Supprime un vendor.
    
    Args:
        session: Session SQLModel
        vendor_id: ID du vendor à supprimer
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        vendor = session.get(OOBVendor, vendor_id)
        if vendor:
            # Supprimer d'abord toutes les dépendances (accès user<->vendor) liées à ce vendor
            accesses_stmt = select(OOBUserVendorAccess).where(OOBUserVendorAccess.vendor_id == vendor_id)
            vendor_accesses = list(session.exec(accesses_stmt).all())
            for acc in vendor_accesses:
                session.delete(acc)

            session.delete(vendor)
            session.commit()
            return True
    return False


# ========== COMMENT CRUD ==========

def create_comment(
    session: Session,
    doc_ext: str,
    username: str,
    comment: str,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> OOBComment:
    """Crée un nouveau commentaire.
    
    Args:
        session: Session SQLModel
        doc_ext: Numéro de PO
        username: Nom d'utilisateur
        comment: Texte du commentaire
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/page", "seed")
    """
    from haleon.db.audit_logger import AuditLogger
    # S'assurer que la table temporaire existe AVANT d'entrer dans le context manager
    try:
        AuditLogger._ensure_context_table(session)
    except Exception:
        session.rollback()
        AuditLogger._ensure_context_table(session)
    
    with AuditLogger.with_context(session, audit_user, audit_source):
        comment_obj = OOBComment(
            doc_ext=doc_ext,
            username=username,
            comment=comment,
        )
        session.add(comment_obj)
        session.commit()
        session.refresh(comment_obj)
    return comment_obj


def get_comments_by_doc_ext(session: Session, doc_ext: str) -> List[OOBComment]:
    """Récupère tous les commentaires pour un numéro de PO donné.
    
    Les commentaires sont triés par date de création croissante (du plus ancien au plus récent)
    pour afficher une conversation dans l'ordre chronologique.
    """
    statement = select(OOBComment).where(OOBComment.doc_ext == doc_ext).order_by(OOBComment.created_at.asc())
    return list(session.exec(statement).all())


def get_comment_by_id(session: Session, comment_id: int) -> Optional[OOBComment]:
    """Récupère un commentaire par son ID."""
    return session.get(OOBComment, comment_id)


def update_comment(
    session: Session,
    comment_id: int,
    comment: str,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> Optional[OOBComment]:
    """Met à jour un commentaire.
    
    Args:
        session: Session SQLModel
        comment_id: ID du commentaire à mettre à jour
        comment: Nouveau texte du commentaire
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/page")
    """
    from datetime import datetime
    import pytz
    swiss_tz = pytz.timezone("Europe/Zurich")
    
    from haleon.db.audit_logger import AuditLogger
    # S'assurer que la table temporaire existe AVANT d'entrer dans le context manager
    try:
        AuditLogger._ensure_context_table(session)
    except Exception:
        session.rollback()
        AuditLogger._ensure_context_table(session)
    
    with AuditLogger.with_context(session, audit_user, audit_source):
        comment_obj = session.get(OOBComment, comment_id)
        if comment_obj:
            comment_obj.comment = comment
            comment_obj.updated_at = datetime.now(swiss_tz)
            session.add(comment_obj)
            session.commit()
            session.refresh(comment_obj)
            return comment_obj
    return None


def delete_comment(
    session: Session,
    comment_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Supprime un commentaire.
    
    Args:
        session: Session SQLModel
        comment_id: ID du commentaire à supprimer
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/page")
    """
    from haleon.db.audit_logger import AuditLogger
    # S'assurer que la table temporaire existe AVANT d'entrer dans le context manager
    # Cela évite les erreurs si la session a été rollback précédemment
    try:
        AuditLogger._ensure_context_table(session)
    except Exception:
        # Si erreur, faire un rollback et réessayer
        session.rollback()
        AuditLogger._ensure_context_table(session)
    
    with AuditLogger.with_context(session, audit_user, audit_source):
        comment = session.get(OOBComment, comment_id)
        if comment:
            session.delete(comment)
            session.commit()
            return True
    return False


# ========== USER VENDOR ACCESS CRUD ==========

def grant_vendor_access(
    session: Session,
    user_id: int,
    vendor_id: int,
    granted_by: Optional[int] = None,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> OOBUserVendorAccess:
    """Accorde un accès utilisateur-vendor.
    
    Args:
        session: Session SQLModel
        user_id: ID de l'utilisateur
        vendor_id: ID du vendor
        granted_by: ID de l'utilisateur ayant accordé l'accès
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin", "seed")
    """
    # Vérifier si l'accès existe déjà
    existing = get_user_vendor_access(session, user_id, vendor_id)
    if existing:
        return existing
    
    # S'assurer que la table temporaire existe AVANT d'entrer dans le context manager
    from haleon.db.audit_logger import AuditLogger
    try:
        AuditLogger._ensure_context_table(session)
    except Exception:
        # Si erreur, faire un rollback et réessayer
        session.rollback()
        AuditLogger._ensure_context_table(session)
    
    with AuditLogger.with_context(session, audit_user, audit_source):
        access = OOBUserVendorAccess(
            user_id=user_id,
            vendor_id=vendor_id,
            granted_by=granted_by,
        )
        session.add(access)
        session.commit()
        session.refresh(access)
    return access


def revoke_vendor_access(
    session: Session,
    user_id: int,
    vendor_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Révoque un accès utilisateur-vendor.
    
    Args:
        session: Session SQLModel
        user_id: ID de l'utilisateur
        vendor_id: ID du vendor
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        access = get_user_vendor_access(session, user_id, vendor_id)
        if access:
            session.delete(access)
            session.commit()
            return True
    return False


def get_user_vendor_access(
    session: Session,
    user_id: int,
    vendor_id: int,
) -> Optional[OOBUserVendorAccess]:
    """Récupère un accès spécifique utilisateur-vendor."""
    statement = select(OOBUserVendorAccess).where(
        OOBUserVendorAccess.user_id == user_id,
        OOBUserVendorAccess.vendor_id == vendor_id,
    )
    return session.exec(statement).first()


def get_user_vendor_accesses(session: Session, user_id: int) -> List[OOBUserVendorAccess]:
    """Récupère tous les accès vendors pour un utilisateur."""
    statement = select(OOBUserVendorAccess).where(
        OOBUserVendorAccess.user_id == user_id
    ).order_by(OOBUserVendorAccess.created_at.desc())
    return list(session.exec(statement).all())


def get_vendors_for_user(session: Session, user_id: int) -> List[OOBVendor]:
    """Récupère tous les vendors auxquels un utilisateur a accès."""
    statement = select(OOBVendor).join(
        OOBUserVendorAccess,
        OOBVendor.id == OOBUserVendorAccess.vendor_id
    ).where(OOBUserVendorAccess.user_id == user_id)
    return list(session.exec(statement).all())


def can_user_access_vendor(
    session: Session,
    user_id: int,
    vendor_id: int,
) -> bool:
    """Vérifie si un utilisateur a accès à un vendor."""
    access = get_user_vendor_access(session, user_id, vendor_id)
    return access is not None


def get_all_user_vendor_accesses(session: Session) -> List[OOBUserVendorAccess]:
    """Récupère tous les accès utilisateur-vendor."""
    statement = select(OOBUserVendorAccess).order_by(OOBUserVendorAccess.created_at.desc())
    return list(session.exec(statement).all())


def delete_user_vendor_access(
    session: Session,
    access_id: int,
    audit_user: Optional[Users] = None,
    audit_source: Optional[str] = None,
) -> bool:
    """Supprime un accès utilisateur-vendor par son ID.
    
    Args:
        session: Session SQLModel
        access_id: ID de l'accès à supprimer
        audit_user: Utilisateur effectuant l'opération (pour l'audit)
        audit_source: Source de l'opération (ex: "oob/admin")
    """
    with AuditLogger.with_context(session, audit_user, audit_source):
        access = session.get(OOBUserVendorAccess, access_id)
        if access:
            session.delete(access)
            session.commit()
            return True
    return False









