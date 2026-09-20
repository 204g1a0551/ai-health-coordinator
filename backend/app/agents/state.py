from typing import TypedDict, List, Dict, Any, Optional


class SymptomItem(TypedDict):
    name: str
    duration: Optional[str]


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
    actions: List[AgentAction]
    final_response: str
