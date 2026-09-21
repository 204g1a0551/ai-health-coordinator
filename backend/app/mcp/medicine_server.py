"""
Medicine MCP Server
Standardized access to drug normalization, pharmacology references, DDI interactions, and generic pricing.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.pharmacy_service import pharmacy_service
from app.services.ddi_service import ddi_service, RXNORM_KNOWLEDGE_BASE
from app.services.cost_saver_service import cost_saver_service, VERIFIED_MEDICINE_PRICE_CATALOG


class MedicineMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="medicine_mcp",
            description="Pharmacological Registry, Drug-Drug Interaction, and Generic Medicine Pricing MCP Server",
        )
        self._register_medicine_tools()

    def _register_medicine_tools(self):
        # 1. search_medicine
        self.register_tool(
            MCPTool(
                name="search_medicine",
                description="Search pharmacopoeia reference database for active ingredients, dosage forms, and indications",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Medicine name or brand to search"},
                    },
                    "required": ["query"],
                },
                allowed_agents=["medicine_agent", "supervisor", "medicine_search_agent", "cost_saver_agent", "ddi_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_medicine,
        )

        # 2. normalize_medicine_name
        self.register_tool(
            MCPTool(
                name="normalize_medicine_name",
                description="Normalize a brand name or clinical acronym to its canonical generic active ingredient and RxNorm ID",
                input_schema={
                    "type": "object",
                    "properties": {
                        "raw_name": {"type": "string", "description": "Raw or brand medicine name (e.g. Dolo 650, Plavix)"},
                    },
                    "required": ["raw_name"],
                },
                allowed_agents=["medicine_agent", "supervisor", "medicine_search_agent", "ddi_agent", "cost_saver_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_normalize_medicine_name,
        )

        # 3. get_medicine_information
        self.register_tool(
            MCPTool(
                name="get_medicine_information",
                description="Retrieve clinical pharmacological details, therapeutic class, schedule, and storage instructions",
                input_schema={
                    "type": "object",
                    "properties": {
                        "medicine_name": {"type": "string", "description": "Medicine or active ingredient name"},
                    },
                    "required": ["medicine_name"],
                },
                allowed_agents=["medicine_agent", "supervisor", "medicine_search_agent", "ddi_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_medicine_information,
        )

        # 4. check_drug_interaction
        self.register_tool(
            MCPTool(
                name="check_drug_interaction",
                description="Check clinical drug-drug interaction (DDI) pair between two medications with severity and mechanism",
                input_schema={
                    "type": "object",
                    "properties": {
                        "medicine_a": {"type": "string", "description": "First medicine name or active ingredient"},
                        "medicine_b": {"type": "string", "description": "Second medicine name or active ingredient"},
                    },
                    "required": ["medicine_a", "medicine_b"],
                },
                allowed_agents=["ddi_agent", "medicine_agent", "supervisor"],
                cache_ttl_seconds=600,
            ),
            self._handle_check_drug_interaction,
        )

        # 5. find_generic_information
        self.register_tool(
            MCPTool(
                name="find_generic_information",
                description="Lookup bioequivalent Jan Aushadhi / PMBJP generic alternatives and equivalence standards",
                input_schema={
                    "type": "object",
                    "properties": {
                        "medicine_name": {"type": "string", "description": "Prescribed medicine name"},
                    },
                    "required": ["medicine_name"],
                },
                allowed_agents=["cost_saver_agent", "medicine_agent", "supervisor"],
                cache_ttl_seconds=600,
            ),
            self._handle_find_generic_information,
        )

        # 6. get_medicine_price
        self.register_tool(
            MCPTool(
                name="get_medicine_price",
                description="Retrieve side-by-side brand vs generic price comparison benchmarked against NPPA/PMBJP datasets",
                input_schema={
                    "type": "object",
                    "properties": {
                        "medicine_name": {"type": "string", "description": "Medicine name"},
                    },
                    "required": ["medicine_name"],
                },
                allowed_agents=["cost_saver_agent", "medicine_agent", "supervisor"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_medicine_price,
        )

    # --------------------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------------------
    def _handle_search_medicine(self, query: str) -> Dict[str, Any]:
        info = pharmacy_service.get_medicine_info(query)
        norm = ddi_service.normalize_medicine_name(query)
        return {
            "query": query,
            "generic_name": info.generic_name,
            "therapeutic_class": info.therapeutic_class,
            "common_usage_category": info.common_usage_category,
            "form": info.form,
            "schedule": info.schedule,
            "storage_instructions": info.storage_instructions,
            "rxcui": norm.rxcui if norm else None,
            "source": "Indian Pharmacopoeia & Public Reference Database",
        }

    def _handle_normalize_medicine_name(self, raw_name: str) -> Dict[str, Any]:
        norm = ddi_service.normalize_medicine_name(raw_name)
        if not norm:
            return {
                "raw_name": raw_name,
                "normalized": False,
                "generic_name": raw_name.strip().title(),
                "rxnorm_id": None,
                "source": "Clinical Heuristic Normalization",
            }
        return {
            "raw_name": raw_name,
            "normalized": True,
            "generic_name": norm.normalized_name,
            "display_name": norm.brand_name or norm.normalized_name.title(),
            "rxnorm_id": norm.rxnorm_id,
            "source": "RxNorm / Clinical Pharmacology Database",
        }

    def _handle_get_medicine_information(self, medicine_name: str) -> Dict[str, Any]:
        info = pharmacy_service.get_medicine_info(medicine_name)
        return {
            "medicine_name": medicine_name,
            "generic_name": info.generic_name,
            "therapeutic_class": info.therapeutic_class,
            "schedule": info.schedule,
            "storage_instructions": info.storage_instructions,
            "verified_public_data": info.verified_public_data,
            "source": "Indian Pharmacopoeia & Central Drugs Standard Control Organisation (CDSCO)",
        }

    def _handle_check_drug_interaction(self, medicine_a: str, medicine_b: str) -> Dict[str, Any]:
        norm_a = ddi_service.normalize_medicine_name(medicine_a)
        norm_b = ddi_service.normalize_medicine_name(medicine_b)
        pair = ddi_service.check_interaction_pair(norm_a, norm_b)
        if not pair:
            return {
                "medicine_a": medicine_a,
                "medicine_b": medicine_b,
                "has_interaction": False,
                "severity": "None Identified",
                "clinical_description": "No documented clinically significant interaction identified in verified reference knowledge base.",
                "source": "RxNorm / Clinical Pharmacology Database",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "disclaimer": "Clinical interaction data is informational. Consult your physician or pharmacist.",
            }
        return {
            "medicine_a": pair.medicine_a.normalized_name,
            "medicine_b": pair.medicine_b.normalized_name,
            "has_interaction": True,
            "severity": pair.severity.value,
            "clinical_description": pair.description,
            "clinical_effect": pair.clinical_effect,
            "warning": pair.warning,
            "recommendation": pair.recommendation,
            "source": pair.source,
            "disclaimer": "Informational only. Do not stop or modify medications without doctor consultation.",
        }

    def _handle_find_generic_information(self, medicine_name: str) -> Dict[str, Any]:
        comp = cost_saver_service.evaluate_medicine_comparison(medicine_name)
        if not comp or not comp.generic_equivalent:
            return {
                "medicine_name": medicine_name,
                "has_generic_option": False,
                "message": f"No direct Jan Aushadhi generic equivalent registered for '{medicine_name}'.",
                "disclaimer": "Ask your doctor or pharmacist before changing or substituting any medication.",
            }
        return {
            "medicine_name": medicine_name,
            "has_generic_option": True,
            "active_ingredient": comp.prescribed_medicine.active_ingredient,
            "strength": comp.prescribed_medicine.strength,
            "dosage_form": comp.prescribed_medicine.dosage_form,
            "prescribed_brand": comp.prescribed_medicine.model_dump() if hasattr(comp.prescribed_medicine, "model_dump") else comp.prescribed_medicine.dict(),
            "generic_equivalent": comp.generic_equivalent.model_dump() if hasattr(comp.generic_equivalent, "model_dump") else comp.generic_equivalent.dict(),
            "equivalence_level": comp.equivalence_level.value,
            "equivalence_notes": comp.equivalence_notes,
            "price_difference": comp.price_difference,
            "savings_percentage": comp.savings_percentage,
            "disclaimer": "Ask your doctor or pharmacist before changing or substituting a medicine.",
            "source": comp.prescribed_medicine.source,
        }

    def _handle_get_medicine_price(self, medicine_name: str) -> Dict[str, Any]:
        comp = cost_saver_service.evaluate_medicine_comparison(medicine_name)
        if not comp:
            return {
                "medicine_name": medicine_name,
                "price_available": False,
                "message": f"Pricing data unavailable for '{medicine_name}'.",
            }
        return {
            "medicine_name": medicine_name,
            "price_available": True,
            "brand_price": comp.prescribed_medicine.listed_price,
            "brand_pack": comp.prescribed_medicine.pack_size,
            "generic_price": comp.generic_equivalent.listed_price if comp.generic_equivalent else None,
            "generic_pack": comp.generic_equivalent.pack_size if comp.generic_equivalent else None,
            "savings_amount": comp.price_difference,
            "savings_percentage": comp.savings_percentage,
            "source": comp.prescribed_medicine.source,
        }


medicine_mcp_server = MedicineMCPServer()
