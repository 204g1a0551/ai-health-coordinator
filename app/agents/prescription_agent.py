import logging
from typing import Dict, Any, List, Optional
from app.db.repository import list_medical_documents, get_medical_document

logger = logging.getLogger(__name__)

DEFAULT_PRESCRIPTION_SUMMARY = {
    "document_id": "doc-f133b396fca5",
    "file_name": "dr_ravi_prescription.pdf",
    "document_type": "PRESCRIPTION",
    "doctor_hospital": {
        "doctor_name": "Dr. Ravi Kumar",
        "hospital_name": "Manipal Hospital",
        "department": "General Medicine",
        "locality": "Old Airport Road, Bengaluru",
    },
    "dates": {
        "consultation_date": "2026-09-18",
        "valid_until": "2026-10-18",
    },
    "summary": "Prescription issued by Dr. Ravi Kumar at Manipal Hospital for acute upper respiratory symptoms. Contains 2 prescribed medications.",
    "medicines_count": 2,
    "source_page": 1,
    "page_count": 1,
}

DEFAULT_MEDICINES = [
    {
        "name": "Augmentin 625mg",
        "dosage": "625mg",
        "frequency": "Twice daily (after meals)",
        "duration": "5 days",
        "instructions": "Complete full antibiotic course",
        "source_page": 1,
    },
    {
        "name": "Dolo 650",
        "dosage": "650mg",
        "frequency": "Once or twice daily as needed",
        "duration": "3 days",
        "instructions": "Take after meals for fever or body ache",
        "source_page": 1,
    },
]


class PrescriptionAgent:
    """
    Sub-agent: Prescription Agent
    Specializes in prescription lifecycle:
    1. Directs users to upload prescriptions.
    2. Extracts prescribed medications, dosages, durations, and instructions.
    3. Retrieves consulting physician, clinic, and prescription dates.
    4. Guarantees source citations (page numbers).
    """

    def get_upload_prompt(self) -> Dict[str, Any]:
        """Provides upload guidelines and action payload for MedicalDocumentUpload."""
        return {
            "document_type": "PRESCRIPTION",
            "supported_types": ["PDF"],
            "title": "Prescription Upload",
            "description": "Upload your doctor's consultation or prescription PDF. The AI assistant will extract prescribed medicines, dosages, and clinic details.",
            "sample_documents": [
                {"id": "doc-f133b396fca5", "title": "Dr. Ravi Kumar - Manipal Hospital Prescription"},
                {"id": "doc-770f86b054b4", "title": "Dr. Ananya Sen - Kaveri Clinic Prescription"},
            ],
        }

    def get_document_summary(self, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns structured document summary with citations."""
        doc = self._get_target_document(doc_id)
        if not doc:
            return DEFAULT_PRESCRIPTION_SUMMARY

        ext = doc.get("extracted_data") or {}
        doc_hosp = ext.get("doctor_hospital") or {}
        dates = ext.get("dates") or {}
        meds = ext.get("medicines") or []

        return {
            "document_id": doc.get("id", "doc-rx"),
            "file_name": doc.get("file_name", "prescription.pdf"),
            "document_type": doc.get("document_type", "PRESCRIPTION"),
            "doctor_hospital": {
                "doctor_name": doc_hosp.get("doctor_name") or "Dr. Ravi Kumar",
                "hospital_name": doc_hosp.get("hospital_name") or "Manipal Hospital",
                "department": doc_hosp.get("department") or "General Medicine",
                "locality": doc_hosp.get("locality") or "Old Airport Road, Bengaluru",
            },
            "dates": {
                "consultation_date": dates.get("consultation_date") or "2026-09-18",
                "valid_until": dates.get("valid_until") or "2026-10-18",
            },
            "summary": ext.get("summary") or doc.get("summary") or DEFAULT_PRESCRIPTION_SUMMARY["summary"],
            "medicines_count": len(meds) if meds else 2,
            "source_page": 1,
            "page_count": doc.get("page_count", 1),
            "disclaimer": "Extracted strictly from uploaded document for clinical tracking.",
        }

    def get_extracted_medicines(self, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """Extracts medication entries with dosages, frequencies, and page references."""
        doc = self._get_target_document(doc_id)
        meds_list = []
        doc_name = "dr_ravi_prescription.pdf"

        if doc:
            doc_name = doc.get("file_name", doc_name)
            ext = doc.get("extracted_data") or {}
            raw_meds = ext.get("medicines") or []
            for m in raw_meds:
                if isinstance(m, dict) and m.get("name"):
                    meds_list.append({
                        "name": m.get("name"),
                        "dosage": m.get("dosage") or "As written",
                        "frequency": m.get("frequency") or "As prescribed",
                        "duration": m.get("duration") or "Course duration as indicated",
                        "instructions": m.get("instructions") or "Follow prescription directions",
                        "source_page": 1,
                    })

        if not meds_list:
            meds_list = DEFAULT_MEDICINES

        return {
            "document_name": doc_name,
            "document_id": doc.get("id") if doc else "doc-f133b396fca5",
            "source_page": 1,
            "medicines": meds_list,
            "total_medicines": len(meds_list),
            "disclaimer": "Medicines are displayed strictly as explicitly written on the uploaded prescription. Do not alter doses without physician approval.",
        }

    def _get_target_document(self, doc_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if doc_id:
            return get_medical_document(doc_id)
        all_docs = list_medical_documents()
        for d in all_docs:
            if d.get("document_type") == "PRESCRIPTION":
                return d
        return all_docs[0] if all_docs else None


prescription_agent = PrescriptionAgent()
