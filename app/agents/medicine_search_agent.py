import logging
from typing import Dict, Any, List, Optional
from app.models.pharmacy import MedicineSearchResponse
from app.services.pharmacy_service import pharmacy_service
from app.db.repository import get_medical_document, list_medical_documents

logger = logging.getLogger(__name__)


class MedicineSearchAgent:
    """
    Medicine Search Agent
    Responsibilities:
    1. Read medicine names explicitly extracted from uploaded prescription documents.
    2. Search public pharmacological reference data for each medicine.
    3. Coordinate with location service to find nearby pharmacies/stores.
    4. Provide distance-ranked store availability.
    5. Adhere to clinical safety constraints:
       - Never recommend medicines.
       - Never change dosage.
       - Never substitute medicines.
       - Never instruct the user to take medication.
       - Only operate on explicitly extracted document items.
    """

    def search_for_document(
        self,
        doc_id: Optional[str] = None,
        locality: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> MedicineSearchResponse:
        """
        Extracts medicines from specified document (or latest prescription)
        and executes nearby pharmacy search in the user's area.
        """
        doc = None
        if doc_id:
            doc = get_medical_document(doc_id)
        else:
            all_docs = list_medical_documents()
            # Find first prescription document
            for d in all_docs:
                if d.get("document_type") == "PRESCRIPTION":
                    doc = d
                    break
            if not doc and all_docs:
                doc = all_docs[0]

        medicine_names: List[str] = []
        if doc and doc.get("extracted_data"):
            ext = doc["extracted_data"]
            if isinstance(ext, dict):
                meds = ext.get("medicines", [])
                for m in meds:
                    if isinstance(m, dict) and m.get("name"):
                        medicine_names.append(m["name"])

        # If no document was uploaded or no medicines found, return empty with clear message
        if not medicine_names:
            return MedicineSearchResponse(
                medicines_searched=[],
                medicine_details=[],
                location_searched=locality or "Bengaluru",
                pharmacies=[],
                total_pharmacies_found=0,
                disclaimer="No explicitly prescribed medicines found in the selected document. Please upload a valid prescription PDF first.",
            )

        return pharmacy_service.search_pharmacies(
            medicines=medicine_names,
            locality=locality,
            lat=lat,
            lng=lng,
        )

    def search_explicit_medicines(
        self,
        medicines: List[str],
        locality: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> MedicineSearchResponse:
        """
        Finds public info and nearby pharmacies for a list of explicitly extracted medicines.
        """
        clean_meds = [m.strip() for m in medicines if m and m.strip()]
        return pharmacy_service.search_pharmacies(
            medicines=clean_meds,
            locality=locality,
            lat=lat,
            lng=lng,
        )


medicine_search_agent = MedicineSearchAgent()


def medicine_search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph Node: Medicine Search Agent
    Coordinates document extraction, public pharmacological data, and nearby pharmacy search.
    """
    parsed = state.get("parsed_intent") or {}
    locality = state.get("location_query") or parsed.get("location") or "Koramangala"
    user_coords = state.get("user_coordinates")
    lat = user_coords.get("lat") if user_coords else None
    lng = user_coords.get("lng") if user_coords else None

    # Search for medicines from uploaded document
    search_res = medicine_search_agent.search_for_document(
        locality=locality,
        lat=lat,
        lng=lng,
    )

    if not search_res.medicines_searched:
        msg = (
            "I could not find any explicitly prescribed medicines in your uploaded documents. "
            "Please upload a valid prescription PDF under **Medical Documents** first so I can find "
            "where your medicines are available."
        )
    else:
        med_lines = []
        for m in search_res.medicine_details:
            cls = m.therapeutic_class or "Prescription medicine"
            summary = m.public_summary or "Common clinical use"
            med_lines.append(f"* **{m.medicine_name}**: {cls} ({summary})")

        pharm_lines = []
        for p in search_res.pharmacies[:4]:
            timing = "24x7 Open" if p.is_24x7 else p.timing
            pharm_lines.append(
                f"* **{p.name}** ({p.distance_km} km away)\n"
                f"  Address: {p.address}\n"
                f"  Timing: {timing} | Phone: {p.phone}"
            )

        med_text = "\n".join(med_lines)
        pharm_text = "\n".join(pharm_lines)

        msg = (
            f"Here are the medicines explicitly extracted from your prescription:\n\n"
            f"**Medicine:**\n{med_text}\n\n"
            f"**Nearby pharmacies ({search_res.location_searched}):**\n{pharm_text}\n\n"
            f"*(Safety Notice: {search_res.disclaimer})*"
        )

    res_dict = search_res.dict()
    pharmacy_action = {
        "action": "SHOW_PHARMACIES",
        "data": res_dict,
        "payload": res_dict,
        "type": "SHOW_PHARMACIES",
    }

    return {
        **state,
        "pharmacy_results": res_dict,
        "actions": [pharmacy_action],
        "final_response": msg,
    }
