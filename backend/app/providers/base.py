from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseHealthcareProvider(ABC):
    """
    Abstract interface for healthcare provider services.
    Allows swapping mock / seeded local providers with real healthcare provider APIs
    (e.g., Practo, Apollo 24/7, Manipal Hospitals API, Cerner/Epic FHIR).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the healthcare data provider."""
        pass

    @abstractmethod
    def search_doctors(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        locality: Optional[str] = None,
        hospital_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search doctors matching query, department, locality, or hospital."""
        pass

    @abstractmethod
    def search_hospitals(
        self,
        query: Optional[str] = None,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search hospitals and clinics by name or locality/area."""
        pass

    @abstractmethod
    def get_doctor_details(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed doctor profile including hospital, clinic, address, and consultation info."""
        pass

    @abstractmethod
    def get_available_slots(
        self,
        doctor_id: str,
        date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve available consultation time slots for a specific doctor."""
        pass

    @abstractmethod
    def search_by_department(
        self,
        department: str,
        locality: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve doctors and clinics for a specific medical department."""
        pass

    @abstractmethod
    def search_by_location(
        self,
        locality: str,
        department: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve healthcare providers and doctors in a specific Bengaluru locality/area."""
        pass
