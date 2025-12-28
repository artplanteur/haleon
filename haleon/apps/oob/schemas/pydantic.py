"""Schémas Pydantic pour les données API de l'application OOB."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class IBPPurgDocItem(BaseModel):
    """Schéma pour IBPPurgDocItem."""
    IBPPurgDocInt: int
    SimulationVersionID: int
    IBPPurgTranspLoadID: int
    IBPPurgDocType: str
    IBPPurgDocExt: str
    IBPPurgDocItem: str
    IBPPurgDocIsFixed: bool
    IBPPurgDocIsFixedInReleaseProc: bool
    IBPPurgDocIsDeploymentRelevant: bool
    IBPPurgSOSAdditionalLaneID: str
    IBPPurgSOSModeOfTransport: str
    IBPPurgSOSShipToLocationID: str
    IBPPurgSOSShipFromLocationID: str
    IBPPurgSOSProductID: str
    PlanningAreaID: str
    VersionID: str
    SourceLogicalSystem: str


class PurchasingItem(BaseModel):
    """Schéma pour PurchasingItem."""
    IBPPurgReceiptElmntInt: int
    SimulationVersionID: int
    IBPPurgDocInt: int
    IBPPurgDocScheduleLine: int
    ProductID: str
    ShipToLocationID: str
    ShipFromLocationID: Optional[str] = None
    IBPPurgReceiptDateTime: datetime
    IBPPurgDeliveryDateTime: datetime
    IBPPurgRequirementDateTime: datetime
    IBPPurgReceiptQuantity: float
    IBPPurgOrderedQuantity: float
    IBPPurgRequirementQuantity: float
    ProductBaseUnit: str
    IBPReceiptIsPlngRlvt: bool
    IBPRequirementIsPlngRlvt: bool
    IBPMinRmngShelfLifeInSeconds: int
    IBPExpiryDateTime: datetime
    IBPPurgDocItem: IBPPurgDocItem


class DocumentType(BaseModel):
    """Schéma pour DocumentType."""
    code: str
    description: str


class DocumentTypes:
    """Classe pour gérer les types de documents."""
    
    def __init__(self):
        self._document_types: List[DocumentType] = [
            DocumentType(code="PO_ITM", description="Purchase Order Item"),
            DocumentType(code="STO_ITM", description="Stock Transfer Order"),
            DocumentType(code="PR_ITM", description="Production Receipts Item"),
            DocumentType(code="STR_ITM", description="Stock Transfer Requisition Item"),
            DocumentType(code="POIDELITM", description="Purchase Order Item Deletion"),
            DocumentType(code="STOIDELITM", description="Stock transfer Order Item Deletion"),
            DocumentType(code="LD_STR_ITM", description="Load Stock Transfer Requisition Item"),
            DocumentType(code="LD_PR_ITM", description="Load Production Item"),
            DocumentType(code="SPR_ITM", description="Special Production Item"),
            DocumentType(code="LD_SPR_ITM", description="Load Special Production Item"),
            DocumentType(code="SPO_ITM", description="Special Order Item"),
        ]
    
    def get_all(self) -> List[DocumentType]:
        """Retourne tous les types de documents."""
        return self._document_types
    
    def get_by_code(self, code: str) -> Optional[DocumentType]:
        """Retourne un type de document par son code."""
        for doc_type in self._document_types:
            if doc_type.code == code:
                return doc_type
        return None









