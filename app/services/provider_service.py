import os
from typing import Dict, Any, List, Optional
from app.providers.base import BaseHealthcareProvider
from app.providers.bengaluru_provider import BengaluruSeededProvider
from app.services.redis_service import redis_service


class HealthcareProviderService:
    """
    Healthcare Provider Service layer for Bengaluru.
    Acts as the controlled data broker between LangGraph agents and the active provider,
    handling Redis caching and data sanitization.

    Architecture:
    Doctor/Slot Agent -> Healthcare Provider Service -> Redis Cache -> External Provider/DB
    """

    def __init__(self, provider: Optional[BaseHealthcareProvider] = None):
        # Default to Bengaluru Seeded Provider; easily replaceable with real APIs
        self._provider: BaseHealthcareProvider = provider or BengaluruSeededProvider()

    @property
    def provider(self) -> BaseHealthcareProvider:
        return self._provider

    def set_provider(self, new_provider: BaseHealthcareProvider) -> None:
        """Dynamically replace provider (e.g., when connecting a real healthcare API)."""
        self._provider = new_provider

    # ----------------------------------------------------------------------
    # Controlled Backend Tools for Doctor/Slot Agent
    # ----------------------------------------------------------------------
    def search_doctors(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        locality: Optional[str] = None,
        hospital_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controlled tool: Search doctors matching name, department, locality, or hospital."""
        cache_key = f"bengaluru:doctors:{query or '*'}:{department or '*'}:{locality or '*'}:{hospital_id or '*'}"
        cached = redis_service.get_cached_healthcare_data(cache_key)
        if cached is not None:
            return cached

        results = self._provider.search_doctors(
            query=query,
            department=department,
            locality=locality,
            hospital_id=hospital_id,
        )
        redis_service.set_cached_healthcare_data(cache_key, results, ttl=3600)
        return results

    def search_hospitals(
        self,
        query: Optional[str] = None,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controlled tool: Search hospitals and clinics in Bengaluru."""
        cache_key = f"bengaluru:hospitals:{query or '*'}:{locality or '*'}"
        cached = redis_service.get_cached_healthcare_data(cache_key)
        if cached is not None:
            return cached

        results = self._provider.search_hospitals(query=query, locality=locality)
        redis_service.set_cached_healthcare_data(cache_key, results, ttl=3600)
        return results

    def get_doctor_details(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Controlled tool: Retrieve doctor details by ID or name."""
        cache_key = f"bengaluru:doctor:{doctor_id}"
        cached = redis_service.get_cached_healthcare_data(cache_key)
        if cached is not None:
            return cached

        details = self._provider.get_doctor_details(doctor_id)
        if details:
            redis_service.set_cached_healthcare_data(cache_key, details, ttl=3600)
        return details

    def get_available_slots(
        self,
        doctor_id: str,
        date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controlled tool: Retrieve consultation slots for a doctor with caching."""
        cache_key = f"bengaluru:slots:{doctor_id}:{date or 'tomorrow'}:{period or 'all'}"
        cached = redis_service.get_cached_healthcare_data(cache_key)
        if cached is not None:
            return cached

        slots = self._provider.get_available_slots(doctor_id, date=date, period=period)
        redis_service.set_cached_healthcare_data(cache_key, slots, ttl=600)
        return slots

    def search_by_department(
        self,
        department: str,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controlled tool: Search doctors by medical department."""
        return self.search_doctors(department=department, locality=locality)

    def search_by_location(
        self,
        locality: str,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Controlled tool: Search doctors by Bengaluru locality/area."""
        return self.search_doctors(locality=locality, department=department)


# Global singleton instance
provider_service = HealthcareProviderService()
