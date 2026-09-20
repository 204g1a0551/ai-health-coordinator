import re
from typing import Dict, Any, Optional, List, Tuple
from app.agents.state import AgentState
from app.services.location_service import location_service

DEPARTMENT_MAP = {
    "general physician": "General Medicine",
    "general physicians": "General Medicine",
    "general medicine": "General Medicine",
    "physician": "General Medicine",
    "physicians": "General Medicine",
    "gp": "General Medicine",
    "dermatologist": "Dermatology",
    "dermatologists": "Dermatology",
    "dermatology": "Dermatology",
    "skin": "Dermatology",
    "ent": "ENT",
    "ent doctor": "ENT",
    "ent doctors": "ENT",
    "ear nose throat": "ENT",
    "orthopedic": "Orthopedics",
    "orthopedics": "Orthopedics",
    "orthopedic doctor": "Orthopedics",
    "orthopedic doctors": "Orthopedics",
    "bone": "Orthopedics",
    "pediatric": "Pediatrics",
    "pediatrics": "Pediatrics",
    "pediatrician": "Pediatrics",
    "pediatricians": "Pediatrics",
    "child": "Pediatrics",
    "ophthalmologist": "Ophthalmology",
    "ophthalmologists": "Ophthalmology",
    "ophthalmology": "Ophthalmology",
    "eye": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "eye doctors": "Ophthalmology",
    "dental": "Dental",
    "dentist": "Dental",
    "dentists": "Dental",
    "teeth": "Dental",
}

LOCALITY_PATTERNS = [
    r"\b(?:near|around|in|at|close\s+to)\s+([a-zA-Z\s]+?)(?:\s+tomorrow|\s+today|\s+evening|\s+morning|$|\.|\?)",
    r"\b([a-zA-Z\s]+?)\s+(?:doctors?|physicians?|specialists?)\b",
]

KNOWN_LOCALITIES = [
    "koramangala",
    "indiranagar",
    "whitefield",
    "jayanagar",
    "hsr layout",
    "hsr",
    "bellandur",
    "cunningham road",
    "vasanth nagar",
    "hebbal",
    "bannerghatta road",
    "bannerghatta",
    "electronic city",
    "mg road",
    "central",
]


def extract_location_and_dept(text: str) -> Tuple[Optional[str], Optional[str], bool]:
    """
    Extracts locality, department/specialty preference, and whether 'near me' was requested.
    """
    lower = text.lower().strip()
    is_near_me = bool(re.search(r"\b(?:near\s+me|nearby|closest(?:\s+to\s+me)?)\b", lower))

    # 1. Department extraction
    matched_dept = None
    for kw in sorted(DEPARTMENT_MAP.keys(), key=len, reverse=True):
        dept = DEPARTMENT_MAP[kw]
        if re.search(rf"\b{kw}\b", lower):
            matched_dept = dept
            break

    if is_near_me:
        return None, matched_dept, True

    # 2. Known localities matching
    for loc in KNOWN_LOCALITIES:
        if loc in lower:
            return loc, matched_dept, False

    # 3. Regex pattern matching
    for pat in LOCALITY_PATTERNS:
        m = re.search(pat, lower)
        if m:
            candidate = m.group(1).strip()
            # Exclude common non-location words
            if candidate not in {"me", "here", "us", "any", "the", "a", "good", "best", "available"}:
                return candidate, matched_dept, False

    return None, matched_dept, False


def location_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Location Agent
    Responsibilities:
    1. Extract requested locality or location from query.
    2. If user says "near me", check for explicit browser coordinates or request permission.
    3. Never assume user location without permission.
    4. Convert location to latitude/longitude using controlled backend location service.
    5. Find nearby providers and calculate distance in km.
    6. Return structured SHOW_NEARBY_DOCTORS action without exposing raw coordinates.
    """
    user_msg = state.get("user_message", "")
    actions = list(state.get("actions", []))
    coords = state.get("user_coordinates")

    loc_query, dept_filter, is_near_me = extract_location_and_dept(user_msg)

    # Handle "near me" query without coordinates
    if is_near_me and not coords:
        actions.append({
            "type": "REQUEST_LOCATION_PERMISSION",
            "action": "REQUEST_LOCATION_PERMISSION",
            "payload": {
                "message": "To find doctors near you, please grant location permission or specify your locality (e.g., 'Doctors near Koramangala').",
                "suggestedLocalities": ["Koramangala", "Indiranagar", "Whitefield", "Jayanagar", "HSR Layout"],
            }
        })
        return {
            **state,
            "actions": actions,
            "final_response": "To find doctors near you, please allow location access or type your locality in Bengaluru (e.g. 'Doctors near Koramangala' or 'Doctors near Indiranagar').",
        }

    # Determine coordinates to search around
    target_lat: float = 12.9716
    target_lng: float = 77.5946
    location_display = "Bengaluru"

    if coords and ("lat" in coords and "lng" in coords):
        target_lat = float(coords["lat"])
        target_lng = float(coords["lng"])
        location_display = "Current Location"
    elif loc_query:
        geo = location_service.geocode_locality(loc_query)
        if geo:
            target_lat = geo["lat"]
            target_lng = geo["lng"]
            location_display = geo["display"]
        else:
            location_display = f"{loc_query.title()}, Bengaluru"
    elif is_near_me and coords:
        target_lat = float(coords["lat"])
        target_lng = float(coords["lng"])
        location_display = "Current Location"

    # Query nearby doctors through controlled backend service
    nearby_docs = location_service.find_nearby_doctors(
        target_lat=target_lat,
        target_lng=target_lng,
        department=dept_filter,
    )

    # Format structured output as specified in requirement
    structured_doctors = [
        {
            "id": d["id"],
            "name": d["name"],
            "department": d["department"],
            "hospital": d.get("hospital", ""),
            "locality": d.get("locality", ""),
            "consultationFee": d.get("consultationFee", ""),
            "consultationType": d.get("consultationType", ""),
            "rating": d.get("rating", 4.8),
            "experience": d.get("experience", ""),
            "availableStatus": d.get("availableStatus", "Available"),
            "distance_km": d["distance_km"],
            "slots": d.get("slots", []),
            "dataSource": d.get("dataSource", "Bengaluru Health Grid (Verified Provider)"),
        }
        for d in nearby_docs
    ]

    structured_result = {
        "action": "SHOW_NEARBY_DOCTORS",
        "location": location_display,
        "doctors": structured_doctors,
        "department": dept_filter or "All Departments",
    }

    actions.append({
        "type": "SHOW_NEARBY_DOCTORS",
        "action": "SHOW_NEARBY_DOCTORS",
        "payload": structured_result,
    })

    # If department was matched, also notify department state
    if dept_filter:
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "action": "UPDATE_DEPARTMENT",
            "payload": {
                "department": dept_filter,
                "reason": f"Nearby doctor search for {dept_filter} in {location_display}."
            }
        })

    # Prepare chat response strictly without raw coordinates
    top_docs = structured_doctors[:3]
    top_summary = ", ".join([f"{d['name']} ({d['department']}, {d['distance_km']} km away)" for d in top_docs])

    final_msg = (
        f"Found {len(structured_doctors)} verified healthcare providers near {location_display}. "
        f"Closest: {top_summary}. "
        f"The dashboard has been updated with distance information."
    )

    return {
        **state,
        "location_query": location_display,
        "suggested_department": dept_filter or state.get("suggested_department"),
        "nearby_doctors_result": structured_result,
        "actions": actions,
        "final_response": final_msg,
    }
