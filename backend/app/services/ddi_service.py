import json
import logging
import re
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from app.db.repository import get_medical_document, list_medical_documents
from app.models.ddi import (
    DDIInteraction,
    DDIInteractionResponse,
    NormalizedMedicine,
)

logger = logging.getLogger(__name__)

RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
RXNORM_SOURCE = "RxNorm / RxNav (U.S. National Library of Medicine)"
NOT_VERIFIED_MESSAGE = "Interaction information could not be verified from the configured source."
RECOMMENDATION = (
    "Consult a qualified healthcare professional before changing, stopping, "
    "or combining medicines. Do not change the prescribed dose."
)


class DDIService:
    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout_seconds = timeout_seconds
        self._source_unavailable = False

    def _get_json(self, path: str, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        url = f"{RXNORM_BASE_URL}/{path}?{urlencode(params)}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "AIHealthCoordinator/1.0"})
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            logger.warning("RxNorm request failed for %s: %s", path, exc)
            self._source_unavailable = True
            return None

    def normalize_medicine(self, name: str) -> Optional[Dict[str, str]]:
        cleaned = re.sub(r"\s+", " ", name.strip())
        if not cleaned:
            return None
        result = self._get_json(
            "approximateTerm.json",
            {"term": cleaned, "maxEntries": "5", "option": "0"},
        )
        candidates = (result or {}).get("approximateGroup", {}).get("candidate", [])
        if isinstance(candidates, dict):
            candidates = [candidates]
        if not candidates:
            return None
        best = max(candidates, key=lambda candidate: float(candidate.get("score", 0) or 0))
        rxcui = best.get("rxcui")
        if not rxcui:
            return None
        properties = self._get_json(
            f"rxcui/{quote(str(rxcui), safe='')}/properties.json",
            {},
        )
        name_from_source = (
            (properties or {}).get("properties", {}).get("name")
            or best.get("name")
            or cleaned
        )
        return {"rxcui": str(rxcui), "name": str(name_from_source)}

    def _extract_interactions(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        groups = payload.get("fullInteractionTypeGroup", [])
        if isinstance(groups, dict):
            groups = [groups]
        interactions: List[Dict[str, Any]] = []
        for group in groups:
            for interaction_type in group.get("fullInteractionType", []) or []:
                for interaction in interaction_type.get("fullInteraction", []) or []:
                    interactions.append({
                        "description": interaction.get("description"),
                        "severity": interaction.get("severity"),
                        "source": group.get("sourceName") or RXNORM_SOURCE,
                    })
        return interactions

    def check_documents(
        self,
        document_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None,
    ) -> DDIInteractionResponse:
        self._source_unavailable = False
        documents = (
            [get_medical_document(doc_id) for doc_id in document_ids or []]
            if document_ids
            else list_medical_documents(user_id)
        )
        documents = [document for document in documents if document]
        names: Dict[str, Dict[str, Any]] = {}
        for document in documents:
            extracted = document.get("extracted_data") or {}
            for medicine in extracted.get("medicines", []) or []:
                raw_name = str(medicine.get("name", "")).strip() if isinstance(medicine, dict) else ""
                if not raw_name:
                    continue
                key = re.sub(r"[^a-z0-9]+", " ", raw_name.lower()).strip()
                if key:
                    names.setdefault(key, {"name": raw_name, "document_ids": []})
                    if document.get("id") not in names[key]["document_ids"]:
                        names[key]["document_ids"].append(document.get("id"))

        normalized: List[NormalizedMedicine] = []
        verified_by_rxcui: Dict[str, NormalizedMedicine] = {}
        for entry in names.values():
            source_match = self.normalize_medicine(entry["name"])
            if source_match is None:
                normalized.append(NormalizedMedicine(
                    originalName=entry["name"],
                    sourceDocumentIds=entry["document_ids"],
                    status="UNVERIFIED",
                    message="Medicine name could not be verified by RxNorm.",
                ))
                continue
            item = NormalizedMedicine(
                originalName=entry["name"],
                normalizedName=source_match["name"],
                rxcui=source_match["rxcui"],
                sourceDocumentIds=entry["document_ids"],
                status="VERIFIED",
            )
            existing = verified_by_rxcui.get(source_match["rxcui"])
            if existing:
                existing.source_document_ids = sorted(
                    set(existing.source_document_ids + item.source_document_ids)
                )
            else:
                verified_by_rxcui[source_match["rxcui"]] = item
                normalized.append(item)

        interactions: List[DDIInteraction] = []
        verified = list(verified_by_rxcui.items())
        for (rxcui_a, medicine_a), (rxcui_b, medicine_b) in combinations(verified, 2):
            payload = self._get_json("interaction/list.json", {"rxcui": f"{rxcui_a}+{rxcui_b}"})
            if payload is None:
                continue
            for item in self._extract_interactions(payload):
                description = item.get("description") or "Potential interaction reported by the configured source."
                interactions.append(DDIInteraction(
                    medicineA=medicine_a.normalized_name or medicine_a.original_name,
                    medicineB=medicine_b.normalized_name or medicine_b.original_name,
                    interactionDescription=description,
                    severity=item.get("severity"),
                    category=item.get("severity"),
                    source=item.get("source") or RXNORM_SOURCE,
                    warning="Do not stop or change a prescribed medicine based on this result alone.",
                    recommendation=RECOMMENDATION,
                ))

        if self._source_unavailable:
            status = "UNAVAILABLE"
            message = NOT_VERIFIED_MESSAGE
        elif not verified:
            status = "NO_VERIFIED_MEDICINES"
            message = NOT_VERIFIED_MESSAGE
        elif interactions:
            status = "VERIFIED"
            message = "Potential medicine interactions were identified by the configured medical database."
        else:
            status = "VERIFIED_NO_INTERACTION_REPORTED"
            message = (
                "The configured database did not report a potential interaction "
                "for the verified medicine pairs checked. This is not a guarantee of safety."
            )

        return DDIInteractionResponse(
            medicines=normalized,
            interactions=interactions,
            unresolvedMedicines=[item.original_name for item in normalized if item.status != "VERIFIED"],
            databaseStatus=status,
            message=message,
            disclaimer=(
                "Interaction checking is informational and is not a diagnosis or treatment recommendation. "
                "Consult a qualified healthcare professional."
            ),
        )


ddi_service = DDIService()
