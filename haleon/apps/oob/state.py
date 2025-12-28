"""État Reflex pour l'application OOB."""

import reflex as rx
from typing import List, Optional, Any
from datetime import datetime, timedelta
from haleon.db.database import get_session
from haleon.apps.oob.api.client import fetch_purchasing_items
from haleon.apps.oob.db.crud import (
    create_comment,
    get_comments_by_doc_ext,
    update_comment,
    delete_comment,
    get_comment_by_id,
)
from haleon.apps.oob.schemas.pydantic import PurchasingItem
from haleon.auth.auth_state import AuthState
from haleon.auth.permissions import ApplicationPermissions


class OOBState(AuthState):
    """État pour l'application OOB - hérite de AuthState pour l'authentification."""
    
    state_auto_setters: bool = True
    
    @rx.var
    def is_user_admin(self) -> bool:
        """Vérifie si l'utilisateur actuel est admin via current_user."""
        if not self.current_user:
            return False
        return self.current_user.is_admin if self.current_user.is_admin else False
    
    # Flag pour indiquer si l'utilisateur a accès à OOB
    has_oob_access: bool = False
    
    # Données principales
    purchasing_items: List[dict] = []
    selected_po: str = ""
    sort_column: str = ""
    sort_direction: str = "asc"  # "asc" or "desc"
    comments: List[dict] = []
    comment_text: str = ""  # Texte du commentaire en cours de saisie
    editing_comment_id: Optional[int] = None  # ID du commentaire en cours d'édition
    editing_comment_text: str = ""  # Texte du commentaire en cours d'édition
    
    # Filtres (avec persistance dans LocalStorage)
    date_min: str = rx.LocalStorage(sync=True)
    date_max: str = rx.LocalStorage(sync=True)
    ship_from: str = rx.LocalStorage(sync=True)
    ship_to: str = rx.LocalStorage(sync=True)
    doc_types: List[str] = []  # Liste normale, sera synchronisée manuellement via doc_types_storage
    doc_types_storage: str = rx.LocalStorage(sync=True)  # Stockage JSON pour doc_types
    search_query: str = rx.LocalStorage(sync=True)
    
    # État UI
    loading: bool = False
    doc_types_dropdown_open: bool = False
    
    @staticmethod
    def _get_document_types() -> List[dict]:
        """Retourne la liste des types de documents disponibles."""
        return [
            {"code": "PO_ITM", "description": "Purchase Order Item"},
            {"code": "STO_ITM", "description": "Stock Transfer Order"},
            {"code": "PR_ITM", "description": "Production Receipts Item"},
            {"code": "STR_ITM", "description": "Stock Transfer Requisition Item"},
            {"code": "POIDELITM", "description": "Purchase Order Item Deletion"},
            {"code": "STOIDELITM", "description": "Stock transfer Order Item Deletion"},
            {"code": "LD_STR_ITM", "description": "Load Stock Transfer Requisition Item"},
            {"code": "LD_PR_ITM", "description": "Load Production Item"},
            {"code": "SPR_ITM", "description": "Special Production Item"},
            {"code": "LD_SPR_ITM", "description": "Load Special Production Item"},
            {"code": "SPO_ITM", "description": "Special Order Item"},
        ]
    
    def on_mount(self):
        """Charge les données au chargement de la page (comme dans les pages admin)."""
        print("[DEBUG OOBState.on_mount] Début du chargement des données OOB")
        # S'assurer que l'utilisateur est chargé depuis la session (hérité de AuthState)
        if not self.is_authenticated or not self.current_user:
            self.load_user_from_session()
        
        # Vérifier que l'utilisateur a accès à l'application OOB
        if not self.current_user:
            print("[DEBUG OOBState.on_mount] Aucun utilisateur connecté")
            self.has_oob_access = False
            return
        
        # DEBUG: Vérifier les valeurs de is_admin
        print(f"[DEBUG OOBState.on_mount] is_admin (AuthState): {self.is_admin}")
        print(f"[DEBUG OOBState.on_mount] current_user.is_admin (BDD): {self.current_user.is_admin if self.current_user else 'None'}")
        print(f"[DEBUG OOBState.on_mount] is_authenticated: {self.is_authenticated}")
        print(f"[DEBUG OOBState.on_mount] is_validated: {self.is_validated}")
        print(f"[DEBUG OOBState.on_mount] is_active: {self.is_active}")
        
        has_access = ApplicationPermissions.can_access_app(self.current_user, "oob")
        self.has_oob_access = has_access
        
        if not has_access:
            print("[DEBUG OOBState.on_mount] Accès refusé à l'application OOB")
            return
        
        # Initialiser les dates par défaut (30 derniers jours) SEULEMENT si elles ne sont pas déjà dans LocalStorage
        if not self.date_min or self.date_min == "":
            today = datetime.now()
            self.date_min = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        if not self.date_max or self.date_max == "":
            today = datetime.now()
            self.date_max = today.strftime("%Y-%m-%d")
        
        # Restaurer doc_types depuis LocalStorage (stocké en JSON)
        if self.doc_types_storage:
            try:
                import json
                self.doc_types = json.loads(self.doc_types_storage) if self.doc_types_storage else []
            except:
                self.doc_types = []
        else:
            self.doc_types = []
        
        print(f"[DEBUG OOBState.on_mount] Dates: {self.date_min} -> {self.date_max} (depuis LocalStorage ou défaut)")
        print(f"[DEBUG OOBState.on_mount] Filtres restaurés - ship_from: '{self.ship_from}', ship_to: '{self.ship_to}', search: '{self.search_query}', doc_types: {self.doc_types}")
        # Charger les items automatiquement (comme dans les pages admin)
        self.load_items()
        print("[DEBUG OOBState.on_mount] Chargement des items terminé")
        # Si une PO est déjà sélectionnée, charger ses commentaires
        if self.selected_po:
            self.load_comments()
    
    def load_items(self):
        """Charge les purchasing items depuis l'API simulée."""
        print(f"[DEBUG load_items] Début du chargement - loading={self.loading}")
        self.loading = True
        
        # Obtenir une session pour récupérer les vendors
        session_gen = get_session()
        session = next(session_gen)
        
        try:
            # Convertir les dates string en datetime
            date_min_dt = None
            date_max_dt = None
            
            if self.date_min:
                try:
                    date_min_dt = datetime.strptime(self.date_min, "%Y-%m-%d")
                    print(f"[DEBUG load_items] date_min_dt: {date_min_dt}")
                except ValueError as e:
                    print(f"[DEBUG load_items] Erreur parsing date_min: {e}")
                    pass
            
            if self.date_max:
                try:
                    date_max_dt = datetime.strptime(self.date_max, "%Y-%m-%d")
                    # Ajouter un jour pour inclure toute la journée
                    date_max_dt = date_max_dt + timedelta(days=1)
                    print(f"[DEBUG load_items] date_max_dt: {date_max_dt}")
                except ValueError as e:
                    print(f"[DEBUG load_items] Erreur parsing date_max: {e}")
                    pass
            
            # Récupérer les vendors auxquels l'utilisateur a accès
            vendor_codes = []
            if self.current_user:
                from haleon.apps.oob.db.crud import get_vendors_for_user
                user_vendors = get_vendors_for_user(session, self.current_user.id)
                vendor_codes = [v.code for v in user_vendors]
                print(f"[DEBUG load_items] Utilisateur a accès à {len(vendor_codes)} vendors: {vendor_codes}")
            
            print(f"[DEBUG load_items] Appel fetch_purchasing_items avec filtres: ship_from={self.ship_from}, ship_to={self.ship_to}, doc_types={self.doc_types}, vendor_codes={vendor_codes}")
            # Récupérer les items depuis l'API
            items = fetch_purchasing_items(
                date_min=date_min_dt,
                date_max=date_max_dt,
                ship_from=self.ship_from if self.ship_from else None,
                ship_to=self.ship_to if self.ship_to else None,
                doc_types=self.doc_types if self.doc_types else None,
                vendor_codes=vendor_codes if vendor_codes else None,
            )
            
            print(f"[DEBUG load_items] {len(items)} items récupérés depuis l'API")
            
            # Convertir les Pydantic models en dicts pour Reflex
            # Aplatir les données pour éviter les dictionnaires imbriqués (Reflex a du mal avec ça)
            # Formater les dates pour l'affichage (YYYY-MM-DD HH:MM)
            def format_date_for_display(dt):
                """Formate une date datetime en format lisible."""
                if not dt:
                    return ""
                try:
                    date_str = dt.isoformat()
                    date_part = date_str[:10] if len(date_str) >= 10 else date_str
                    time_part = date_str[11:16] if len(date_str) >= 16 else ""
                    if time_part:
                        return f"{date_part} {time_part}"
                    return date_part
                except:
                    return str(dt)
            
            self.purchasing_items = [
                {
                    "IBPPurgReceiptElmntInt": item.IBPPurgReceiptElmntInt,
                    "SimulationVersionID": item.SimulationVersionID,
                    "IBPPurgDocInt": item.IBPPurgDocInt,
                    "IBPPurgDocScheduleLine": item.IBPPurgDocScheduleLine,
                    "ProductID": item.ProductID,
                    "ShipToLocationID": item.ShipToLocationID,
                    "ShipFromLocationID": item.ShipFromLocationID or "",
                    "IBPPurgReceiptDateTime": item.IBPPurgReceiptDateTime.isoformat(),
                    "IBPPurgReceiptDateTimeFormatted": format_date_for_display(item.IBPPurgReceiptDateTime),
                    "IBPPurgDeliveryDateTime": item.IBPPurgDeliveryDateTime.isoformat(),
                    "IBPPurgDeliveryDateTimeFormatted": format_date_for_display(item.IBPPurgDeliveryDateTime),
                    "IBPPurgRequirementDateTime": item.IBPPurgRequirementDateTime.isoformat(),
                    "IBPPurgRequirementDateTimeFormatted": format_date_for_display(item.IBPPurgRequirementDateTime),
                    "IBPPurgReceiptQuantity": item.IBPPurgReceiptQuantity,
                    "IBPPurgOrderedQuantity": item.IBPPurgOrderedQuantity,
                    "IBPPurgRequirementQuantity": item.IBPPurgRequirementQuantity,
                    "ProductBaseUnit": item.ProductBaseUnit,
                    "IBPReceiptIsPlngRlvt": item.IBPReceiptIsPlngRlvt,
                    "IBPRequirementIsPlngRlvt": item.IBPRequirementIsPlngRlvt,
                    "IBPMinRmngShelfLifeInSeconds": item.IBPMinRmngShelfLifeInSeconds,
                    "IBPExpiryDateTime": item.IBPExpiryDateTime.isoformat(),
                    # Propriétés aplaties de IBPPurgDocItem
                    "IBPPurgDocExt": item.IBPPurgDocItem.IBPPurgDocExt,
                    "IBPPurgDocType": item.IBPPurgDocItem.IBPPurgDocType,
                    "IBPPurgDocItem_Item": item.IBPPurgDocItem.IBPPurgDocItem,
                }
                for item in items
            ]
            print(f"[DEBUG load_items] {len(self.purchasing_items)} items chargés dans le state")
            
            # Filtrer les items selon les accès vendors de l'utilisateur
            if vendor_codes:
                # Filtrer pour ne garder que les items dont ShipFromLocationID correspond à un vendor auquel l'utilisateur a accès
                # Exclure les items sans vendor (ShipFromLocationID vide ou None)
                filtered_items = [
                    item for item in self.purchasing_items
                    if item.get("ShipFromLocationID") and item.get("ShipFromLocationID") in vendor_codes
                ]
                print(f"[DEBUG load_items] {len(self.purchasing_items)} items avant filtrage, {len(filtered_items)} après filtrage par vendor")
                self.purchasing_items = filtered_items
        except Exception as e:
            print(f"Erreur lors du chargement des items: {e}")
            import traceback
            traceback.print_exc()
            rx.toast.error(self.t("error_loading_data", module="oob"))
        finally:
            session.close()
            self.loading = False
            print(f"[DEBUG load_items] Fin du chargement - loading={self.loading}")
    
    def select_po(self, doc_ext: str):
        """Sélectionne une PO et charge ses commentaires."""
        self.selected_po = doc_ext
        self.comment_text = ""  # Réinitialiser le champ de commentaire
        self.load_comments()
    
    def load_comments(self):
        """Charge les commentaires pour la PO sélectionnée."""
        if not self.selected_po:
            self.comments = []
            return
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            comment_objs = get_comments_by_doc_ext(session, self.selected_po)
            print(f"[DEBUG load_comments] PO sélectionnée: {self.selected_po}, {len(comment_objs)} commentaires trouvés")
            
            # Identifier les utilisateurs uniques dans l'ordre d'apparition
            seen_users = {}
            user_index = 0
            
            # Palette dans l'ordre : blanc, noir, vibrant green, dark blue-grey
            color_palette = [
                "rgba(255, 255, 255, 0.05)",   # White avec 95% transparence
                "rgba(0, 0, 0, 0.05)",         # Black avec 95% transparence
                "rgba(79, 219, 39, 0.05)",    # Vibrant Green avec 95% transparence
                "rgba(62, 90, 132, 0.05)",    # Dark Blue-Grey avec 95% transparence
            ]
            
            # Assigner les couleurs dans l'ordre d'apparition
            self.comments = []
            for c in comment_objs:
                # Si c'est un nouvel utilisateur, lui assigner la couleur suivante
                if c.username not in seen_users:
                    seen_users[c.username] = {
                        "color": color_palette[user_index % len(color_palette)],
                        "border_color": color_palette[user_index % len(color_palette)],  # Même couleur pour la bordure
                    }
                    user_index += 1
                
                # Formater les dates pour l'affichage (format lisible: DD/MM/YYYY HH:MM)
                def format_date_readable(dt):
                    """Formate une date en format lisible DD/MM/YYYY HH:MM"""
                    if not dt:
                        return None
                    try:
                        if isinstance(dt, datetime):
                            return dt.strftime("%d/%m/%Y %H:%M")
                        # Si c'est une string, essayer de la parser
                        if isinstance(dt, str):
                            # Format ISO: 2025-12-27T14:56:02
                            if 'T' in dt:
                                dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                                return dt_obj.strftime("%d/%m/%Y %H:%M")
                            return dt
                        return str(dt)
                    except:
                        return str(dt)
                
                created_at_str = format_date_readable(c.created_at)
                updated_at_str = format_date_readable(c.updated_at) if c.updated_at else None
                
                self.comments.append({
                    "id": c.id,
                    "doc_ext": c.doc_ext,
                    "username": c.username,
                    "username_display": c.username.split("@")[0] if "@" in c.username else c.username,  # Formaté côté serveur
                    "comment": c.comment,
                    "created_at": created_at_str,
                    "updated_at": updated_at_str,
                    # Ajouter les couleurs pour le code couleur des commentaires
                    "user_color": seen_users[c.username]["color"],
                    "user_border_color": seen_users[c.username]["border_color"],
                })
            
            print(f"[DEBUG load_comments] Commentaires chargés: {len(self.comments)}, {len(seen_users)} utilisateurs uniques")
        except Exception as e:
            print(f"Erreur lors du chargement des commentaires: {e}")
            import traceback
            traceback.print_exc()
            self.comments = []
        finally:
            session.close()
    
    def submit_comment(self, comment_text: str = ""):
        """Soumet un nouveau commentaire."""
        # Utiliser comment_text du paramètre ou de l'état
        text_to_submit = comment_text if comment_text else self.comment_text
        
        if not self.selected_po:
            return rx.toast.error(self.t("select_po_before_comment", module="oob"))
        
        if not text_to_submit or not text_to_submit.strip():
            return rx.toast.error(self.t("enter_comment", module="oob"))
        
        # Récupérer l'email de l'utilisateur connecté
        # Utiliser current_user qui est déjà chargé dans AuthState
        if not self.current_user:
            return rx.toast.error(self.t("must_be_logged_in", module="oob"))
        
        username = self.current_user.email
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            
            # Récupérer l'utilisateur actuel pour l'audit
            from haleon.db.crud.users import get_user_by_email
            current_user_db = get_user_by_email(session, username)
            
            # Créer le commentaire
            create_comment(
                session=session,
                doc_ext=self.selected_po,
                username=username,
                comment=text_to_submit.strip(),
                audit_user=current_user_db,
                audit_source="oob/page",
            )
            
            # Réinitialiser le champ de commentaire
            self.comment_text = ""
            
            # Recharger les commentaires
            self.load_comments()
            
            return rx.toast.success(self.t("comment_added_success", module="oob"))
        except Exception as e:
            print(f"Erreur lors de l'ajout du commentaire: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(self.t("error_adding_comment", module="oob"))
        finally:
            session.close()
    
    def start_edit_comment(self, comment_id: int):
        """Démarre l'édition d'un commentaire."""
        if not self.current_user:
            return rx.toast.error(self.t("cannot_edit_comment", module="oob"))
        
        # Trouver le commentaire dans la liste
        comment_to_edit = None
        for c in self.comments:
            if c["id"] == comment_id:
                comment_to_edit = c
                break
        
        if not comment_to_edit:
            return rx.toast.error(self.t("error_updating_comment", module="oob"))
        
        # Vérifier que l'utilisateur est le propriétaire du commentaire
        if comment_to_edit["username"] != self.current_user.email:
            return rx.toast.error(self.t("cannot_edit_comment", module="oob"))
        
        # Démarrer l'édition
        self.editing_comment_id = comment_id
        self.editing_comment_text = comment_to_edit["comment"]
    
    def cancel_edit_comment(self):
        """Annule l'édition d'un commentaire."""
        self.editing_comment_id = None
        self.editing_comment_text = ""
    
    def update_comment(self, comment_id: int, new_text: str = ""):
        """Met à jour un commentaire existant."""
        if not self.current_user:
            return rx.toast.error(self.t("cannot_edit_comment", module="oob"))
        
        text_to_update = new_text if new_text else self.editing_comment_text
        
        if not text_to_update or not text_to_update.strip():
            return rx.toast.error(self.t("fill_required_fields", module="common"))
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Vérifier que le commentaire existe et appartient à l'utilisateur
            comment_obj = get_comment_by_id(session, comment_id)
            if not comment_obj:
                return rx.toast.error(self.t("error_updating_comment", module="oob"))
            
            if comment_obj.username != self.current_user.email:
                return rx.toast.error(self.t("cannot_edit_comment", module="oob"))
            
            # Récupérer l'utilisateur actuel pour l'audit
            from haleon.db.crud.users import get_user_by_email
            current_user_db = get_user_by_email(session, self.current_user.email)
            
            # Mettre à jour le commentaire
            updated_comment = update_comment(
                session=session,
                comment_id=comment_id,
                comment=text_to_update.strip(),
                audit_user=current_user_db,
                audit_source="oob/page",
            )
            
            if not updated_comment:
                return rx.toast.error(self.t("error_updating_comment", module="oob"))
            
            # Réinitialiser l'état d'édition
            self.editing_comment_id = None
            self.editing_comment_text = ""
            
            # Recharger les commentaires
            self.load_comments()
            
            return rx.toast.success(self.t("comment_updated", module="oob"))
        except Exception as e:
            print(f"Erreur lors de la modification du commentaire: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(self.t("error_updating_comment", module="oob"))
        finally:
            session.close()
    
    def delete_comment(self, comment_id: int):
        """Supprime un commentaire."""
        if not self.current_user:
            return rx.toast.error(self.t("cannot_delete_comment", module="oob"))
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            # Vérifier que le commentaire existe et appartient à l'utilisateur
            comment_obj = get_comment_by_id(session, comment_id)
            if not comment_obj:
                return rx.toast.error(self.t("error_deleting_comment", module="oob"))
            
            if comment_obj.username != self.current_user.email:
                return rx.toast.error(self.t("cannot_delete_comment", module="oob"))
            
            # Récupérer l'utilisateur actuel pour l'audit
            from haleon.db.crud.users import get_user_by_email
            current_user_db = get_user_by_email(session, self.current_user.email)
            
            # Supprimer le commentaire
            success = delete_comment(session, comment_id, audit_user=current_user_db, audit_source="oob/page")
            
            if not success:
                return rx.toast.error(self.t("error_deleting_comment", module="oob"))
            
            # Recharger les commentaires
            self.load_comments()
            
            return rx.toast.success(self.t("comment_deleted", module="oob"))
        except Exception as e:
            print(f"Erreur lors de la suppression du commentaire: {e}")
            import traceback
            traceback.print_exc()
            return rx.toast.error(self.t("error_deleting_comment", module="oob"))
        finally:
            session.close()
    
    @rx.var
    def current_user_email(self) -> str:
        """Retourne l'email de l'utilisateur connecté."""
        if not self.current_user:
            return ""
        return self.current_user.email if self.current_user.email else ""
    
    def apply_filters(self):
        """Applique les filtres et recharge les items."""
        self.load_items()
    
    def is_doc_type_selected(self, doc_type_code: str) -> bool:
        """Vérifie si un type de document est sélectionné."""
        return doc_type_code in self.doc_types
    
    def get_doc_type_checked(self, doc_type_code: str):
        """Retourne True si le type de document est sélectionné (pour Reflex)."""
        return doc_type_code in self.doc_types
    
    def toggle_doc_type(self, doc_type_code: str, checked: bool):
        """Ajoute ou retire un type de document des filtres."""
        if checked:
            if doc_type_code not in self.doc_types:
                self.doc_types.append(doc_type_code)
        else:
            if doc_type_code in self.doc_types:
                self.doc_types.remove(doc_type_code)
        # Sauvegarder dans LocalStorage
        import json
        self.doc_types_storage = json.dumps(self.doc_types)
    
    @rx.var
    def is_all_doc_types_selected(self) -> bool:
        """Vérifie si tous les types de documents sont sélectionnés."""
        all_codes = [dt["code"] for dt in self._get_document_types()]
        return len(self.doc_types) == len(all_codes) and all(code in self.doc_types for code in all_codes)
    
    def toggle_all_doc_types(self, checked: bool):
        """Sélectionne ou désélectionne tous les types de documents."""
        if checked:
            self.doc_types = [dt["code"] for dt in self._get_document_types()]
        else:
            self.doc_types = []
        # Sauvegarder dans LocalStorage
        import json
        self.doc_types_storage = json.dumps(self.doc_types)
    
    @rx.var
    def doc_types_with_state(self) -> List[dict]:
        """Retourne la liste des types de documents avec leur état de sélection."""
        return [
            {
                "code": dt["code"],
                "description": dt["description"],
                "checked": dt["code"] in self.doc_types,
            }
            for dt in self._get_document_types()
        ]
    
    def set_sort_column(self, column: str):
        """Définit la colonne de tri. Clic 1: asc, Clic 2: desc, Clic 3: réinitialiser."""
        if self.sort_column == column:
            if self.sort_direction == "asc":
                # Passer à desc
                self.sort_direction = "desc"
            elif self.sort_direction == "desc":
                # Réinitialiser le tri
                self.sort_column = ""
                self.sort_direction = "asc"
        else:
            # Nouvelle colonne, commencer par asc
            self.sort_column = column
            self.sort_direction = "asc"
    
    @rx.var
    def filtered_items(self) -> list[dict]:
        """Filtre les items selon la recherche et les trie."""
        print(f"[DEBUG filtered_items] purchasing_items count: {len(self.purchasing_items) if self.purchasing_items else 0}")
        print(f"[DEBUG filtered_items] search_query: '{self.search_query}'")
        
        # Filtrer selon la recherche
        if not self.search_query:
            items = self.purchasing_items
        else:
            query_lower = self.search_query.lower()
            items = []
            for item in self.purchasing_items:
                if (
                    query_lower in item.get("ProductID", "").lower()
                    or query_lower in item.get("ShipToLocationID", "").lower()
                    or query_lower in item.get("ShipFromLocationID", "").lower()
                    or query_lower in item.get("IBPPurgDocExt", "").lower()
                ):
                    items.append(item)
        
        # Trier si une colonne est sélectionnée
        if self.sort_column and items:
            # Mapping des colonnes affichées vers les clés des données
            column_mapping = {
                "Receipt Elmt": "IBPPurgReceiptElmntInt",
                "Product ID": "ProductID",
                "Ship To": "ShipToLocationID",
                "Ship From": "ShipFromLocationID",
                "Receipt Qty": "IBPPurgReceiptQuantity",
                "Ordered Qty": "IBPPurgOrderedQuantity",
                "Requirement Qty": "IBPPurgRequirementQuantity",
                "Doc Ext": "IBPPurgDocExt",
                "Doc Type": "IBPPurgDocType",
                "Receipt Date": "IBPPurgReceiptDateTimeFormatted",
                "Delivery Date": "IBPPurgDeliveryDateTimeFormatted",
                "Requirement Date": "IBPPurgRequirementDateTimeFormatted",
            }
            
            key = column_mapping.get(self.sort_column)
            if key:
                reverse = self.sort_direction == "desc"
                items = sorted(items, key=lambda x: str(x.get(key, "")), reverse=reverse)
                print(f"[DEBUG filtered_items] Trié par {self.sort_column} ({self.sort_direction})")
        
        print(f"[DEBUG filtered_items] Après filtrage et tri: {len(items)} items")
        return items
    
    def _get_data_table_items_list(self) -> list[dict]:
        """Prépare les données pour le tableau avec les colonnes formatées (méthode helper)."""
        items = self.filtered_items
        print(f"[DEBUG _get_data_table_items_list] filtered_items count: {len(items) if items else 0}")
        
        if not items or len(items) == 0:
            print("[DEBUG _get_data_table_items_list] Aucun item à formater")
            return []
        
        # Créer une liste de dicts avec les clés correspondant aux colonnes du tableau
        # S'assurer que toutes les valeurs sont des strings non vides (utiliser "—" pour les valeurs vides)
        formatted_data = []
        for item in items:
            formatted_data.append({
                "Receipt Elmt": str(item.get("IBPPurgReceiptElmntInt", "")) or "",
                "Product ID": str(item.get("ProductID", "")) or "",
                "Ship To": str(item.get("ShipToLocationID", "")) or "",
                "Ship From": str(item.get("ShipFromLocationID", "")) or "—",
                "Receipt Qty": str(item.get("IBPPurgReceiptQuantity", "")) or "",
                "Ordered Qty": str(item.get("IBPPurgOrderedQuantity", "")) or "",
                "Requirement Qty": str(item.get("IBPPurgRequirementQuantity", "")) or "",
                "Doc Ext": str(item.get("IBPPurgDocExt", "")) or "",
                "Doc Type": str(item.get("IBPPurgDocType", "")) or "",
                "Receipt Date": str(item.get("IBPPurgReceiptDateTimeFormatted", "")) or "",
                "Delivery Date": str(item.get("IBPPurgDeliveryDateTimeFormatted", "")) or "",
                "Requirement Date": str(item.get("IBPPurgRequirementDateTimeFormatted", "")) or "",
            })
        
        print(f"[DEBUG _get_data_table_items_list] {len(formatted_data)} items formatés pour le tableau")
        if len(formatted_data) > 0:
            print(f"[DEBUG _get_data_table_items_list] Première ligne: {formatted_data[0]}")
            print(f"[DEBUG _get_data_table_items_list] Clés de la première ligne: {list(formatted_data[0].keys())}")
        return formatted_data
    
    def select_po_from_row(self, row_data: dict):
        """Sélectionne une PO depuis une ligne du tableau."""
        doc_ext = row_data.get("Doc Ext", "")
        print(f"[DEBUG select_po_from_row] Sélection de PO: {doc_ext}")
        if doc_ext:
            self.selected_po = doc_ext
            self.load_comments()
            return rx.toast.info(f"PO {doc_ext} sélectionnée")
    
    @rx.var
    def data_table_items(self) -> list[dict]:
        """Prépare les données pour le tableau (retourne une liste de dicts)."""
        return self._get_data_table_items_list()
    
    @rx.var
    def has_data_table_items(self) -> bool:
        """Vérifie si la liste contient des données."""
        items = self.data_table_items
        result = len(items) > 0 if items else False
        print(f"[DEBUG has_data_table_items] items={len(items) if items else 0}, result={result}")
        return result
    
    @rx.var
    def has_comments(self) -> bool:
        """Vérifie si des commentaires existent pour la PO sélectionnée."""
        return len(self.comments) > 0 if self.comments else False
    
    def download_excel(self):
        """Télécharge les données au format Excel (simulation)."""
        # Pour l'instant, on simule juste avec un toast
        # L'implémentation réelle nécessiterait une bibliothèque comme openpyxl
        return rx.toast.info(self.t("excel_export_not_implemented", module="oob"))
    
    @staticmethod
    def get_user_color(username: str) -> str:
        """Génère une couleur cohérente et visible basée sur le nom d'utilisateur.
        Chaque utilisateur aura toujours la même couleur pour bien le distinguer."""
        import hashlib
        hash_obj = hashlib.md5(username.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Palette basée uniquement sur les 4 couleurs HALEON dans l'ordre :
        # 1. White: #FFFFFF (RGB: 255, 255, 255) - reste blanc, pas de transparence
        # 2. Black: #000000 (RGB: 0, 0, 0)
        # 3. Vibrant Green: #4FDB27 (RGB: 79, 219, 39)
        # 4. Dark Blue-Grey: #3E5A84 (RGB: 62, 90, 132)
        # Transparence à 95% (opacity 0.05) pour que le texte reste lisible
        # Chaque utilisateur aura toujours la même couleur
        colors = [
            "rgba(255, 255, 255, 0.05)",   # White avec 95% transparence
            "rgba(0, 0, 0, 0.05)",         # Black avec 95% transparence
            "rgba(79, 219, 39, 0.05)",    # Vibrant Green avec 95% transparence
            "rgba(62, 90, 132, 0.05)",    # Dark Blue-Grey avec 95% transparence
            "rgba(255, 255, 255, 0.05)",   # White (répétition)
            "rgba(0, 0, 0, 0.05)",         # Black (répétition)
            "rgba(79, 219, 39, 0.05)",    # Vibrant Green (répétition)
            "rgba(62, 90, 132, 0.05)",    # Dark Blue-Grey (répétition)
            "rgba(255, 255, 255, 0.05)",   # White (répétition)
            "rgba(0, 0, 0, 0.05)",         # Black (répétition)
            "rgba(79, 219, 39, 0.05)",    # Vibrant Green (répétition)
            "rgba(62, 90, 132, 0.05)",    # Dark Blue-Grey (répétition)
        ]
        
        color_index = hash_int % len(colors)
        return colors[color_index]
    
    @staticmethod
    def get_user_border_color(username: str) -> str:
        """Génère une couleur de bordure cohérente et discrète mais visible basée sur le nom d'utilisateur."""
        import hashlib
        hash_obj = hashlib.md5(username.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        
        # Palette de couleurs de bordure discrètes mais VISIBLES (niveau 500-600)
        # Chaque utilisateur aura toujours la même couleur de bordure
        colors = [
            "blue.500",     # Bleu visible
            "purple.500",   # Violet visible
            "pink.500",     # Rose visible
            "orange.500",   # Orange visible
            "yellow.600",   # Jaune visible
            "green.500",    # Vert visible
            "teal.500",     # Sarcelle visible
            "cyan.500",     # Cyan visible
            "indigo.500",   # Indigo visible
            "violet.500",   # Violet visible
            "fuchsia.500",  # Fuchsia visible
            "emerald.500",  # Émeraude visible
        ]
        
        color_index = hash_int % len(colors)
        print(f"[DEBUG get_user_border_color] Utilisateur: {username}, bordure: {colors[color_index]}")
        return colors[color_index]









