from typing import TypedDict, List, Dict, Any, Optional


class SymptomItem(TypedDict):
    name: str
    duration: Optional[str]


class UIAction(TypedDict):
    action: str
    payload: Dict[str, Any]
    type: Optional[str]


class AgentAction(TypedDict):
    type: str
    payload: Dict[str, Any]


class AgentState(TypedDict):
    user_message: str
    session_id: str
    route: str
    symptoms: List[SymptomItem]
    suggested_department: Optional[str]
    department_reason: Optional[str]
    doctor_slot_results: Optional[Dict[str, Any]]
    appointment_action_result: Optional[Dict[str, Any]]
    patient_info: Optional[Dict[str, Any]]
    location_query: Optional[str]
    user_coordinates: Optional[Dict[str, float]]
    nearby_doctors_result: Optional[Dict[str, Any]]
    parsed_intent: Optional[Dict[str, Any]]
    clarification_question: Optional[str]
    actions: List[Dict[str, Any]]
    pharmacy_results: Optional[Dict[str, Any]]
    multi_departments: Optional[List[Dict[str, Any]]]
    primary_ui_action: Optional[str]
    primary_ui_data: Optional[Dict[str, Any]]
    final_response: str

