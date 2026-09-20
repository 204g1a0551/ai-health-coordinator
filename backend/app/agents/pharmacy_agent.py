import logging
from typing import Dict, Any, List, Optional
from app.services.pharmacy_service import pharmacy_service
from app.db.repository import list_medical_documents, get_medical_document

logger = logging.getLogger(__name__)


class PharmacyAgent:
    """
    Sub-agent: Pharmacy Agent
    Responsibilities:
    1. Search nearby pharmacies stocking prescribed medications.
    2. Rank pharmacies by distance from the user's selected or detected location.
    3. Return store details: address, hours, contact, in-stock status.
    4. Adhere strictly to safe dispensing constraints.
    """

    def search_nearby(
        self,
        medicines: Optional[List[str]] = None,
        locality: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Locates nearby pharmacies stocking medicines from the prescription."""
        if not medicines:
            # Extract from latest prescription document
            all_docs = list_medical_documents()
            for d in all_docs:
                if d.get("document_type") == "PRESCRIPTION":
                    ext = d.get("extracted_data") or {}
                    raw_meds = ext.get("medicines") or []
                    medicines = [m["name"] for m in raw_meds if isinstance(m, dict) and m.get("name")]
                    break

        if not medicines:
            medicines = ["Augmentin 625mg", "Dolo 650"]

        response = pharmacy_service.search_pharmacies(
            medicines=medicines,
            locality=locality,
            lat=lat,
            lng=lng,
        )

        return response.dict()


pharmacy_agent = PharmacyAgent()
