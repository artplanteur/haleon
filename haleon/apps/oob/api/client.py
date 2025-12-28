"""Client API simulé pour l'application OOB."""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from haleon.apps.oob.schemas.pydantic import PurchasingItem, IBPPurgDocItem

# Charger les variables d'environnement depuis apps/.env
apps_dir = Path(__file__).parent.parent
env_file = apps_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)

# Récupérer les credentials
API_LOGIN = os.getenv("API_LOGIN")
API_PASSWORD = os.getenv("API_PASSWORD")


def _api_credentials_configured() -> bool:
    """Retourne True si les credentials API sont configurés via l'environnement."""
    return bool(API_LOGIN and API_PASSWORD)


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


def _generate_fake_purchasing_items(count: int = 50, vendor_codes: Optional[List[str]] = None) -> List[PurchasingItem]:
    """Génère des données fictives de PurchasingItem pour la simulation.
    
    Args:
        count: Nombre d'items à générer
        vendor_codes: Liste des codes de vendors à utiliser pour ShipFromLocationID. Si None, utilise des codes génériques.
    """
    items = []
    doc_type_list = _get_document_types()
    
    # Si aucun vendor code fourni, utiliser des codes génériques
    if not vendor_codes:
        vendor_codes = ["ACME", "TECH", "GLOB", "EURO", "ASIA"]
    
    base_date = datetime.now()
    
    for i in range(count):
        # Générer un IBPPurgDocItem
        doc_type = doc_type_list[i % len(doc_type_list)]
        doc_ext = f"PO{i+1000:06d}"
        
        doc_item = IBPPurgDocItem(
            IBPPurgDocInt=i + 1,
            SimulationVersionID=1,
            IBPPurgTranspLoadID=i + 100,
            IBPPurgDocType=doc_type["code"],
            IBPPurgDocExt=doc_ext,
            IBPPurgDocItem=f"ITEM{i+1:04d}",
            IBPPurgDocIsFixed=(i % 3 == 0),
            IBPPurgDocIsFixedInReleaseProc=(i % 5 == 0),
            IBPPurgDocIsDeploymentRelevant=(i % 7 == 0),
            IBPPurgSOSAdditionalLaneID=f"LANE{i+1:03d}",
            IBPPurgSOSModeOfTransport=["TRUCK", "SHIP", "PLANE"][i % 3],
            IBPPurgSOSShipToLocationID=f"LOC{i+1:04d}",
            IBPPurgSOSShipFromLocationID=f"LOC{(i+10):04d}",
            IBPPurgSOSProductID=f"PROD{i+1:06d}",
            PlanningAreaID=f"AREA{i+1:03d}",
            VersionID="V1",
            SourceLogicalSystem="SAP",
        )
        
        # Générer un PurchasingItem
        receipt_date = base_date + timedelta(days=i % 30)
        delivery_date = receipt_date + timedelta(days=7 + (i % 14))
        requirement_date = receipt_date - timedelta(days=2 + (i % 5))
        expiry_date = delivery_date + timedelta(days=30 + (i % 60))
        
        purchasing_item = PurchasingItem(
            IBPPurgReceiptElmntInt=i + 1,
            SimulationVersionID=1,
            IBPPurgDocInt=i + 1,
            IBPPurgDocScheduleLine=i + 1,
            ProductID=f"PROD{i+1:06d}",
            ShipToLocationID=f"LOC{i+1:04d}",
            ShipFromLocationID=vendor_codes[i % len(vendor_codes)] if i % 2 == 0 else None,
            IBPPurgReceiptDateTime=receipt_date,
            IBPPurgDeliveryDateTime=delivery_date,
            IBPPurgRequirementDateTime=requirement_date,
            IBPPurgReceiptQuantity=100.0 + (i * 10.5),
            IBPPurgOrderedQuantity=150.0 + (i * 12.3),
            IBPPurgRequirementQuantity=120.0 + (i * 11.0),
            ProductBaseUnit="PC",
            IBPReceiptIsPlngRlvt=(i % 2 == 0),
            IBPRequirementIsPlngRlvt=(i % 3 == 0),
            IBPMinRmngShelfLifeInSeconds=86400 * (7 + (i % 30)),  # 7-37 jours
            IBPExpiryDateTime=expiry_date,
            IBPPurgDocItem=doc_item,
        )
        
        items.append(purchasing_item)
    
    return items


def fetch_purchasing_items(
    date_min: Optional[datetime] = None,
    date_max: Optional[datetime] = None,
    ship_from: Optional[str] = None,
    ship_to: Optional[str] = None,
    doc_types: Optional[List[str]] = None,
    vendor_codes: Optional[List[str]] = None,
) -> List[PurchasingItem]:
    """Simule un appel API pour récupérer les PurchasingItem.
    
    Args:
        date_min: Date minimale pour filtrer
        date_max: Date maximale pour filtrer
        ship_from: Filtrer par ShipFromLocationID
        ship_to: Filtrer par ShipToLocationID
        doc_types: Liste des types de documents à inclure
    
    Returns:
        Liste de PurchasingItem correspondant aux critères
    """
    # Vérifier les credentials (simulation)
    # On ne doit jamais fallback sur des credentials par défaut.
    if not _api_credentials_configured():
        print("Warning: API_LOGIN/API_PASSWORD not set. Using simulated data only (apps/.env).")
    
    # Générer des données fictives
    all_items = _generate_fake_purchasing_items(50, vendor_codes=vendor_codes)
    
    # Appliquer les filtres
    filtered_items = all_items
    
    if date_min:
        filtered_items = [
            item for item in filtered_items
            if item.IBPPurgReceiptDateTime >= date_min
        ]
    
    if date_max:
        filtered_items = [
            item for item in filtered_items
            if item.IBPPurgReceiptDateTime <= date_max
        ]
    
    if ship_from:
        filtered_items = [
            item for item in filtered_items
            if item.ShipFromLocationID and ship_from.upper() in item.ShipFromLocationID.upper()
        ]
    
    if ship_to:
        filtered_items = [
            item for item in filtered_items
            if ship_to.upper() in item.ShipToLocationID.upper()
        ]
    
    if doc_types:
        filtered_items = [
            item for item in filtered_items
            if item.IBPPurgDocItem.IBPPurgDocType in doc_types
        ]
    
    return filtered_items


def authenticate() -> bool:
    """Simule l'authentification API.
    
    Returns:
        True si les credentials sont valides
    """
    return _api_credentials_configured()









