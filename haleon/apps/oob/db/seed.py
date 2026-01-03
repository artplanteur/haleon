"""Script de seed pour l'application OOB - Ajoute des données de test."""

import os
import logging
from haleon.db.database import get_session
from haleon.db.crud.users import get_user_by_email
from haleon.apps.oob.db.crud import (
    create_vendor,
    get_vendor_by_code,
    grant_vendor_access,
    get_all_vendors,
)
from haleon.apps.oob.db.models import OOBVendor, OOBComment
from haleon.db.audit_logger import AuditLogger
from haleon.db.triggers import disable_all_audit_triggers, enable_all_audit_triggers
from datetime import datetime, timedelta
import random
import pytz

swiss_tz = pytz.timezone("Europe/Zurich")
logger = logging.getLogger("haleon.apps.oob.seed")


def seed_oob_data(disable_triggers: bool = None):
    """Ajoute des données de test pour l'application OOB.
    
    Args:
        disable_triggers: Si True, désactive les triggers d'audit pendant le seed.
                              Si None, utilise la variable d'environnement SEED_DISABLE_AUDIT_TRIGGERS
                              (par défaut: True en développement, False en production)
    
    Note:
        En production, il est recommandé de garder les triggers activés pour auditer
        tous les changements, même ceux effectués par le seed.
        En développement, la désactivation évite les erreurs liées à _audit_context.
    """
    session_gen = get_session()
    session = next(session_gen)
    
    # Déterminer si on doit désactiver les triggers
    # Par défaut: True en développement (évite erreurs), False en production (audit important)
    if disable_triggers is None:
        # Vérifier la variable d'environnement, ou détecter l'environnement
        env_disable = os.getenv("SEED_DISABLE_AUDIT_TRIGGERS", "").lower()
        if env_disable in ("true", "1", "yes"):
            disable_triggers = True
        elif env_disable in ("false", "0", "no"):
            disable_triggers = False
        else:
            # Par défaut: désactiver en développement (évite erreurs)
            # En production, définir SEED_DISABLE_AUDIT_TRIGGERS=false pour garder l'audit
            # Détection automatique: si on est en production (variable d'environnement)
            is_production = os.getenv("ENVIRONMENT", "").lower() in ("production", "prod", "live")
            disable_triggers = not is_production  # False en production (audit activé), True en dev
    
    # Désactiver les triggers d'audit si demandé
    # Les triggers seront réactivés à la fin dans le bloc finally
    triggers_were_disabled = False
    try:
        if disable_triggers:
            logger.debug("Disabling audit triggers for seed...")
            disable_all_audit_triggers(session)
            triggers_were_disabled = True
        else:
            logger.debug("Audit triggers remain enabled (production mode)")
            # S'assurer que la table temporaire existe si les triggers sont actifs
            try:
                AuditLogger._ensure_context_table(session)
            except Exception:
                session.rollback()
                AuditLogger._ensure_context_table(session)
        
        # Vérifier si des données existent déjà
        existing_vendors = get_all_vendors(session)
        if existing_vendors:
            logger.debug("OOB data already exists; continuing to add test comments.")
            # Ne pas retourner, continuer pour ajouter les commentaires
        
        logger.debug("Seeding OOB data...")
        
        # 1. Créer des vendors
        vendors_data = [
            ("ACME", "ACME Corporation - Fournisseur principal"),
            ("TECH", "Tech Solutions Inc. - Équipements techniques"),
            ("GLOB", "Global Supplies Ltd. - Matières premières"),
            ("EURO", "European Logistics - Services logistiques"),
            ("ASIA", "Asia Pacific Trading - Import/Export"),
        ]
        
        vendors = []
        for code, description in vendors_data:
            existing = get_vendor_by_code(session, code)
            if not existing:
                vendor = create_vendor(session, code, description, audit_user=None, audit_source="seed")
                vendors.append(vendor)
                logger.debug("Vendor created: %s", vendor.code)
            else:
                vendors.append(existing)
                logger.debug("Vendor exists: %s", existing.code)
        
        # 2. Créer des conversations de test sur différentes PO
        # Récupérer les utilisateurs disponibles
        john_doe = get_user_by_email(session, "john.doe@haleon.com")
        alice = get_user_by_email(session, "alice.martin@haleon.com")
        bob = get_user_by_email(session, "bob.dupont@haleon.com")
        
        if not john_doe:
            logger.warning("John Doe not found; skipping comment creation.")
        else:
            # Conversations de test - Format: (PO, username, comment, delay_seconds)
            # Le delay_seconds permet de simuler des commentaires à des moments différents
            conversations = [
                # Conversation 1: PO001034 - Discussion sur une commande urgente
                ("PO001034", "john.doe@haleon.com", "Commande urgente - Livraison prévue sous 48h", 0),
                ("PO001034", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Vérification des stocks en cours. Je confirme la disponibilité.", 300),
                ("PO001034", "john.doe@haleon.com", "Parfait, merci Alice. Je contacte le fournisseur pour confirmer.", 600),
                ("PO001034", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "OK, je mets à jour le système avec les nouvelles informations.", 900),
                
                # Conversation 2: PO001035 - Négociation de prix
                ("PO001035", "john.doe@haleon.com", "Négociation des prix avec le fournisseur en cours.", 0),
                ("PO001035", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Quel est le prix proposé actuellement ?", 200),
                ("PO001035", "john.doe@haleon.com", "Le fournisseur propose 15% de réduction si on commande avant la fin du mois.", 400),
                ("PO001035", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "C'est intéressant. Je valide cette option.", 600),
                
                # Conversation 3: PO001036 - Validation de commande
                ("PO001036", "john.doe@haleon.com", "Commande validée - En attente de confirmation du fournisseur.", 0),
                ("PO001036", "bob.dupont@haleon.com" if bob else "john.doe@haleon.com", "J'ai reçu la confirmation, tout est bon pour procéder.", 180),
                ("PO001036", "john.doe@haleon.com", "Excellent, je finalise la commande.", 360),
                
                # Conversation 4: PO001037 - Problème de qualité
                ("PO001037", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Problème de qualité détecté lors de la réception.", 0),
                ("PO001037", "john.doe@haleon.com", "Pouvez-vous me donner plus de détails sur le problème ?", 120),
                ("PO001037", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Certains articles présentent des défauts mineurs. Photos envoyées par email.", 240),
                ("PO001037", "john.doe@haleon.com", "Je contacte le fournisseur pour un échange. Merci pour le signalement.", 360),
                
                # Conversation 5: PO001038 - Retard de livraison (conversation complète)
                ("PO001038", "john.doe@haleon.com", "Livraison retardée - Le fournisseur annonce un délai supplémentaire de 7 jours.", 0),
                ("PO001038", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Quelle est la raison du retard ?", 150),
                ("PO001038", "john.doe@haleon.com", "Problème logistique côté fournisseur. Ils s'engagent à livrer avant le 15.", 300),
                ("PO001038", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "D'accord, je mets à jour le planning. On prévient le client ?", 450),
                ("PO001038", "john.doe@haleon.com", "Oui, je m'en occupe. Je les contacte aujourd'hui.", 600),
                ("PO001038", "bob.dupont@haleon.com" if bob else "john.doe@haleon.com", "Client informé, ils comprennent la situation.", 750),
                
                # Conversation 6: PO001039 - Annulation de commande
                ("PO001039", "john.doe@haleon.com", "Commande annulée - Remboursement en cours de traitement.", 0),
                ("PO001039", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Raison de l'annulation ?", 100),
                ("PO001039", "john.doe@haleon.com", "Changement de besoin client. Le remboursement devrait être effectif sous 5 jours ouvrés.", 200),
                
                # Conversation 7: PO001040 - Qualité excellente
                ("PO001040", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Excellente qualité - Recommandation pour futures commandes.", 0),
                ("PO001040", "john.doe@haleon.com", "Merci pour le retour. Je note ce fournisseur comme prioritaire.", 180),
                ("PO001040", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Parfait, je mets à jour la fiche fournisseur.", 360),
                
                # Conversation 8: PO001041 - Ajustement de quantité
                ("PO001041", "john.doe@haleon.com", "Quantité ajustée selon demande client - Réduction de 20%.", 0),
                ("PO001041", "bob.dupont@haleon.com" if bob else "john.doe@haleon.com", "Le fournisseur confirme l'ajustement ?", 120),
                ("PO001041", "john.doe@haleon.com", "Oui, confirmation reçue. Nouvelle quantité: 800 unités au lieu de 1000.", 240),
                
                # Conversation 9: PO001042 - Validation financière
                ("PO001042", "john.doe@haleon.com", "En attente de validation financière.", 0),
                ("PO001042", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "J'ai envoyé le dossier hier. Réponse attendue demain.", 200),
                ("PO001042", "john.doe@haleon.com", "Parfait, je fais un suivi si pas de réponse d'ici 48h.", 400),
                
                # Conversation 10: PO001043 - Expédition
                ("PO001043", "john.doe@haleon.com", "Commande expédiée - Suivi en cours. Numéro de tracking: TRK-2024-001043.", 0),
                ("PO001043", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Merci, je mets à jour le système avec le numéro de suivi.", 150),
                ("PO001043", "john.doe@haleon.com", "Livraison prévue le 20/01. Je vous tiens informé.", 300),
                
                # Conversation 11: PO001044 - Réception partielle
                ("PO001044", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Réception partielle effectuée - 60% des articles reçus.", 0),
                ("PO001044", "john.doe@haleon.com", "Quand est prévue la réception du reste ?", 180),
                ("PO001044", "alice.martin@haleon.com" if alice else "john.doe@haleon.com", "Le fournisseur indique une livraison complémentaire sous 3 jours.", 360),
                ("PO001044", "john.doe@haleon.com", "D'accord, je mets à jour le planning.", 540),
            ]
            
            # Créer les commentaires avec des timestamps simulés
            base_time = datetime.now(swiss_tz) - timedelta(days=5)  # Il y a 5 jours
            
            for doc_ext, username, comment_text, delay_seconds in conversations:
                try:
                    # Vérifier que l'utilisateur existe
                    user = get_user_by_email(session, username)
                    if not user:
                        logger.warning("User %s not found; skipping comment.", username)
                        continue
                    
                    # Vérifier si ce commentaire existe déjà (éviter les doublons)
                    from haleon.apps.oob.db.crud import get_comments_by_doc_ext
                    existing_comments = get_comments_by_doc_ext(session, doc_ext)
                    # Vérifier si un commentaire identique existe déjà (même PO, même utilisateur, même texte)
                    comment_exists = any(
                        c.username == username and c.comment == comment_text
                        for c in existing_comments
                    )
                    if comment_exists:
                        logger.debug("Comment already exists for %s by %s; skipping.", doc_ext, username)
                        continue
                    
                    # Calculer le timestamp avec le délai
                    comment_time = base_time + timedelta(seconds=delay_seconds)
                    
                    # Créer le commentaire avec le timestamp personnalisé
                    if triggers_were_disabled:
                        # Les triggers sont désactivés, pas besoin du contexte d'audit
                        comment_obj = OOBComment(
                            doc_ext=doc_ext,
                            username=username,
                            comment=comment_text,
                            created_at=comment_time,
                        )
                        session.add(comment_obj)
                        session.commit()
                        session.refresh(comment_obj)
                    else:
                        # Les triggers sont actifs, utiliser le contexte d'audit
                        with AuditLogger.with_context(session, None, "seed"):
                            comment_obj = OOBComment(
                                doc_ext=doc_ext,
                                username=username,
                                comment=comment_text,
                                created_at=comment_time,
                            )
                            session.add(comment_obj)
                            session.commit()
                            session.refresh(comment_obj)
                    
                    logger.debug(
                        "Comment created doc_ext=%s username=%s at=%s",
                        doc_ext,
                        username,
                        comment_time.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                except Exception as e:
                    logger.exception("Error creating comment for %s: %s", doc_ext, e)
        
        # 3. Créer des accès utilisateur-vendor
        if john_doe and vendors:
            # John Doe a accès à tous les vendors
            for vendor in vendors:
                try:
                    grant_vendor_access(
                        session=session,
                        user_id=john_doe.id,
                        vendor_id=vendor.id,
                        granted_by=john_doe.id if john_doe.is_admin else None,
                        audit_user=None,
                        audit_source="seed",
                    )
                    logger.debug("Vendor access granted: %s -> %s", john_doe.email, vendor.code)
                except Exception as e:
                    # Ignorer si l'accès existe déjà
                    pass
        
        if alice and vendors:
            # Alice a accès à 2 vendors aléatoires
            selected_vendors = random.sample(vendors, min(2, len(vendors)))
            for vendor in selected_vendors:
                try:
                    grant_vendor_access(
                        session=session,
                        user_id=alice.id,
                        vendor_id=vendor.id,
                        granted_by=john_doe.id if john_doe else None,
                        audit_user=None,
                        audit_source="seed",
                    )
                    logger.debug("Vendor access granted: %s -> %s", alice.email, vendor.code)
                except Exception as e:
                    pass
        
        if bob and vendors:
            # Bob a accès à 1 vendor aléatoire
            selected_vendor = random.choice(vendors)
            try:
                grant_vendor_access(
                    session=session,
                    user_id=bob.id,
                    vendor_id=selected_vendor.id,
                    granted_by=john_doe.id if john_doe else None,
                    audit_user=None,
                    audit_source="seed",
                )
                logger.debug("Vendor access granted: %s -> %s", bob.email, selected_vendor.code)
            except Exception as e:
                pass
        
        session.commit()
        logger.info("OOB seeding completed successfully")
        
    except Exception as e:
        logger.exception("OOB seeding failed: %s", e)
        session.rollback()
    finally:
        # Réactiver les triggers d'audit si on les a désactivés
        if triggers_were_disabled:
            try:
                logger.debug("Re-enabling audit triggers...")
                enable_all_audit_triggers(session)
                logger.debug("Audit triggers re-enabled")
            except Exception as e:
                logger.warning("Failed to re-enable audit triggers: %s", e)
        session.close()


if __name__ == "__main__":
    seed_oob_data()
