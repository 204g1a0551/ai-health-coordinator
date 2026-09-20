import math
import re
from typing import Dict, Any, List, Optional, Tuple
from app.services.provider_service import provider_service
from app.services.redis_service import redis_service

# Bengaluru localities registry with representative center coordinates
BENGALURU_LOCALITY_COORDINATES: Dict[str, Dict[str, float]] = {
    "koramangala": {"lat": 12.9352, "lng": 77.6245, "display": "Koramangala, Bengaluru"},
    "indiranagar": {"lat": 12.9784, "lng": 77.6408, "display": "Indiranagar, Bengaluru"},
    "whitefield": {"lat": 12.9698, "lng": 77.7499, "display": "Whitefield, Bengaluru"},
    "jayanagar": {"lat": 12.9308, "lng": 77.5838, "display": "Jayanagar, Bengaluru"},
    "hsr": {"lat": 12.9121, "lng": 77.6446, "display": "HSR Layout, Bengaluru"},
    "hsr layout": {"lat": 12.9121, "lng": 77.6446, "display": "HSR Layout, Bengaluru"},
    "bellandur": {"lat": 12.9260, "lng": 77.6762, "display": "Bellandur, Bengaluru"},
    "cunningham road": {"lat": 12.9866, "lng": 77.5975, "display": "Cunningham Road, Bengaluru"},
    "vasanth nagar": {"lat": 12.9866, "lng": 77.5975, "display": "Vasanth Nagar, Bengaluru"},
    "hebbal": {"lat": 13.0358, "lng": 77.5970, "display": "Hebbal, Bengaluru"},
    "bannerghatta": {"lat": 12.8942, "lng": 77.5991, "display": "Bannerghatta Road, Bengaluru"},
    "bannerghatta road": {"lat": 12.8942, "lng": 77.5991, "display": "Bannerghatta Road, Bengaluru"},
    "electronic city": {"lat": 12.8452, "lng": 77.6602, "display": "Electronic City, Bengaluru"},
    "mg road": {"lat": 12.9756, "lng": 77.6066, "display": "MG Road, Bengaluru"},
    "central": {"lat": 12.9756, "lng": 77.6066, "display": "Central Bengaluru"},
    "bengaluru": {"lat": 12.9716, "lng": 77.5946, "display": "Bengaluru Central"},
}

# Facility coordinates for Bengaluru healthcare providers
FACILITY_COORDINATES: Dict[str, Tuple[float, float]] = {
    "hosp-manipal-hal": (12.9592, 77.6534),           # Manipal HAL, Old Airport Rd
    "hosp-apollo-bannerghatta": (12.8942, 77.5991),   # Apollo Bannerghatta Rd
    "hosp-fortis-cunningham": (12.9866, 77.5975),     # Fortis Cunningham Rd
    "hosp-aster-hebbal": (13.0558, 77.5925),          # Aster CMI Hebbal
    "hosp-sakra-bellandur": (12.9312, 77.6874),       # Sakra World Bellandur
    "hosp-cloudnine-jayanagar": (12.9320, 77.5840),   # Cloudnine Jayanagar
    "clinic-kaveri-indiranagar": (12.9719, 77.6412),  # Kaveri Clinic Indiranagar
    "clinic-narayana-hsr": (12.9121, 77.6446),        # Narayana Clinic HSR Layout
    "clinic-columbia-whitefield": (12.9553, 77.7314), # Columbia Asia Whitefield
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS points using Haversine formula.
    Returns distance in kilometers rounded to 1 decimal place.
    """
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)


class LocationService:
    """
    Controlled backend location service for Bengaluru.
    Enforces privacy by keeping coordinates backend-side and sending only
    required distance and locality metadata to agents and UI.
    """

    def geocode_locality(self, locality_query: str) -> Optional[Dict[str, Any]]:
        """
        Controlled Geocoding Tool:
        Translates human locality names (e.g. 'Koramangala') into lat/lng and canonical name.
        """
        if not locality_query:
            return None

        clean = locality_query.lower().strip()
        for key, info in BENGALURU_LOCALITY_COORDINATES.items():
            if key in clean or clean in key:
                return {
                    "lat": info["lat"],
                    "lng": info["lng"],
                    "display": info["display"],
                    "key": key,
                }

        # Fallback for unrecognized Bengaluru sub-areas to Bengaluru Central
        return {
            "lat": 12.9716,
            "lng": 77.5946,
            "display": f"{locality_query.title()}, Bengaluru",
            "key": "bengaluru",
        }

    def find_nearby_doctors(
        self,
        target_lat: float,
        target_lng: float,
        department: Optional[str] = None,
        max_distance_km: float = 25.0,
    ) -> List[Dict[str, Any]]:
        """
        Controlled Backend Tool:
        Queries healthcare provider service, computes Haversine distances to each doctor's
        facility, and returns doctors sorted by ascending distance.
        """
        # Cache key based on rounded coordinates to prevent redundant computations
        cache_key = f"location:nearby:{round(target_lat, 2)}:{round(target_lng, 2)}:{department or 'all'}"
        cached = redis_service.get_cached_data(cache_key)
        if cached and isinstance(cached, list):
            return cached

        all_doctors = provider_service.search_doctors(department=department)

        scored_doctors = []
        for doc in all_doctors:
            hosp_id = doc.get("hospitalId", "")
            coords = FACILITY_COORDINATES.get(hosp_id)

            if not coords:
                # Default locality lookup if specific facility coordinate missing
                loc_key = doc.get("locality", "").lower()
                loc_match = self.geocode_locality(loc_key)
                if loc_match:
                    coords = (loc_match["lat"], loc_match["lng"])
                else:
                    coords = (12.9716, 77.5946)

            dist_km = haversine_km(target_lat, target_lng, coords[0], coords[1])

            # Also pull available slot times
            slots = provider_service.get_available_slots(doc["id"])
            slot_times = [s["time"] for s in slots if s.get("isAvailable", True)]

            doctor_item = {
                "id": doc["id"],
                "name": doc["name"],
                "department": doc["department"],
                "hospital": doc.get("hospital", "Bengaluru Hospital"),
                "locality": doc.get("locality", "Bengaluru"),
                "address": doc.get("address", ""),
                "consultationFee": doc.get("consultationFee", "₹600"),
                "consultationType": doc.get("consultationType", "In-Person"),
                "experience": doc.get("experience", ""),
                "rating": doc.get("rating", 4.8),
                "availableStatus": doc.get("availableStatus", "Available"),
                "distance_km": dist_km,
                "slots": slot_times,
                "dataSource": doc.get("dataSource", "Bengaluru Health Grid (Verified Provider)"),
            }
            scored_doctors.append(doctor_item)

        # Sort strictly by distance (closest first)
        scored_doctors.sort(key=lambda d: d["distance_km"])

        # Cache nearby search for 15 minutes
        redis_service.set_cached_data(cache_key, scored_doctors, ttl_seconds=900)
        return scored_doctors


# Global singleton instance
location_service = LocationService()
