"""API client for the OOB app (real API + simulation fallback).

This module keeps the existing public contract used by OOBState:
- fetch_purchasing_items(...) -> List[PurchasingItem]
- authenticate() -> bool
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime, timedelta
import logging

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from haleon.apps.oob.schemas.pydantic import PurchasingItem, IBPPurgDocItem

logger = logging.getLogger("haleon.apps.oob.api")

# -------------------------
# ENV loading
# -------------------------
# Existing behavior: apps/.env
apps_dir = Path(__file__).parent.parent
apps_env_file = apps_dir / ".env"
if apps_env_file.exists():
    load_dotenv(apps_env_file)

# Your temp_api.py behavior: ./config/.env (optional)
config_env_file = Path("config") / ".env"
if config_env_file.exists():
    load_dotenv(config_env_file)


# -------------------------
# Real API configuration
# -------------------------
BASE_URL = os.getenv("BASE_URL", "")
PURCHASING_ENDPOINT = os.getenv("PURCHASING_ENDPOINT", "")

# Support both naming conventions.
API_USER = os.getenv("API_USER") or os.getenv("API_LOGIN")
API_PASSWORD = os.getenv("API_PASSWORD")

# SSL verification control
# NOTE (per your request): verify MUST be False.
# If you ever need to re-enable, set API_VERIFY_SSL=true and change the default below.
API_VERIFY_SSL: bool = os.getenv("API_VERIFY_SSL", "false").strip().lower() in ("true", "1", "yes")

# Hard guard: never allow SSL verification disabled in production.
ENV = os.getenv("ENV", "dev").strip().lower()
if ENV == "prod" and API_VERIFY_SSL is False:
    raise RuntimeError("API_VERIFY_SSL=false is forbidden in prod (set API_VERIFY_SSL=true).")

# Resource name can vary depending on your OData service.
PURCHASING_ITEMS_RESOURCE = os.getenv("PURCHASING_ITEMS_RESOURCE", "IBPPurgReceiptElmnt")


def _real_api_configured() -> bool:
    return bool(BASE_URL and PURCHASING_ENDPOINT and API_USER and API_PASSWORD)


# -------------------------
# Real API client (from temp_api.py)
# -------------------------
class APS_API_Client:
    def __init__(self):
        self.base_url = BASE_URL
        self.user = API_USER
        self.password = API_PASSWORD
        self.auth = HTTPBasicAuth(self.user, self.password) if self.user and self.password else None

    def fetch(self, endpoint: str, headers=None, params=None, page_size: int = 5000) -> List[dict]:
        full_url = f"{self.base_url}{endpoint}"
        query_params = params.copy() if params else {}
        query_params.update({"$top": page_size, "$count": "true"})

        all_data: List[dict] = []
        skip = 0

        while True:
            query_params["$skip"] = skip
            response = requests.get(
                full_url,
                headers=headers,
                params=query_params,
                auth=self.auth,
                verify=API_VERIFY_SSL,  # requested: False
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("value", []) if isinstance(data, dict) else []
            all_data.extend(items)
            if len(items) < page_size:
                break
            skip += page_size

        return all_data


class Purchasing(APS_API_Client):
    def __init__(self):
        super().__init__()
        self.base_url = f"{self.base_url}{PURCHASING_ENDPOINT}"


# -------------------------
# Simulation fallback (kept)
# -------------------------
def _get_document_types() -> List[dict]:
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


def _generate_fake_purchasing_items(
    count: int = 50, vendor_codes: Optional[List[str]] = None
) -> List[PurchasingItem]:
    items: List[PurchasingItem] = []
    doc_type_list = _get_document_types()

    if not vendor_codes:
        vendor_codes = ["ACME", "TECH", "GLOB", "EURO", "ASIA"]

    base_date = datetime.now()

    for i in range(count):
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
            IBPMinRmngShelfLifeInSeconds=86400 * (7 + (i % 30)),
            IBPExpiryDateTime=expiry_date,
            IBPPurgDocItem=doc_item,
        )

        items.append(purchasing_item)

    return items


# -------------------------
# Public API used by OOBState
# -------------------------
def fetch_purchasing_items(
    date_min: Optional[datetime] = None,
    date_max: Optional[datetime] = None,
    ship_from: Optional[str] = None,
    ship_to: Optional[str] = None,
    doc_types: Optional[List[str]] = None,
    vendor_codes: Optional[List[str]] = None,
) -> List[PurchasingItem]:
    """Fetch PurchasingItem list from the real API; fallback to simulated data."""
    if _real_api_configured():
        try:
            api = Purchasing()

            # Try to load nested doc item in a single call if supported by the service.
            params: dict[str, Any] = {"$expand": "IBPPurgDocItem"}
            raw = api.fetch(PURCHASING_ITEMS_RESOURCE, params=params, page_size=5000)

            parsed: List[PurchasingItem] = []
            for obj in raw:
                # Pydantic v2
                if hasattr(PurchasingItem, "model_validate"):
                    parsed.append(PurchasingItem.model_validate(obj))
                else:
                    parsed.append(PurchasingItem(**obj))

            # Client-side filters (kept consistent with previous behavior)
            items = parsed
            if date_min:
                items = [it for it in items if it.IBPPurgReceiptDateTime >= date_min]
            if date_max:
                items = [it for it in items if it.IBPPurgReceiptDateTime <= date_max]
            if ship_from:
                items = [
                    it
                    for it in items
                    if it.ShipFromLocationID and ship_from.upper() in it.ShipFromLocationID.upper()
                ]
            if ship_to:
                items = [it for it in items if ship_to.upper() in it.ShipToLocationID.upper()]
            if doc_types:
                items = [it for it in items if it.IBPPurgDocItem.IBPPurgDocType in doc_types]
            if vendor_codes:
                items = [it for it in items if it.ShipFromLocationID and it.ShipFromLocationID in vendor_codes]

            return items
        except Exception as e:
            logger.warning("Real API fetch failed (%s). Falling back to simulated data.", e)

    return _generate_fake_purchasing_items(50, vendor_codes=vendor_codes)


def authenticate() -> bool:
    """Return True if real API settings are present."""
    return _real_api_configured()









