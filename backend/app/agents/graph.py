from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.supervisor import (
    supervisor_node,
    should_route_from_supervisor,
    post_symptom_router,
    post_department_router,
    post_doctor_slot_router,
    final_response_node,
)
from app.agents.symptom_agent import symptom_node
from app.agents.department_agent import department_node
from app.agents.doctor_slot_agent import doctor_slot_node
from app.agents.appointment_agent import appointment_node
from app.agents.patient_info_agent import patient_info_node
from app.agents.location_agent import location_node
from app.agents.llm_agent import llm_node
from app.agents.ui_agent import ui_action_node


def build_health_coordinator_graph():
    """
    Constructs and compiles the full LangGraph coordinator:
    LLM Node -> Supervisor -> Domain Agents -> UI Agent (Action Layer) -> Final Response -> END
    """
    builder = StateGraph(AgentState)

    # Add agent nodes
    builder.add_node("llm_node", llm_node)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("patient_info_agent", patient_info_node)
    builder.add_node("location_agent", location_node)
    builder.add_node("symptom_agent", symptom_node)
    builder.add_node("department_agent", department_node)
    builder.add_node("doctor_slot_agent", doctor_slot_node)
    builder.add_node("appointment_agent", appointment_node)
    builder.add_node("ui_agent", ui_action_node)
    builder.add_node("final_response", final_response_node)

    # Set LLM intent extraction as entry point
    builder.set_entry_point("llm_node")
    builder.add_edge("llm_node", "supervisor")

    # Supervisor conditional routing
    builder.add_conditional_edges(
        "supervisor",
        should_route_from_supervisor,
        {
            "patient_info_agent": "patient_info_agent",
            "location_agent": "location_agent",
            "appointment_agent": "appointment_agent",
            "symptom_agent": "symptom_agent",
            "department_agent": "department_agent",
            "doctor_slot_agent": "doctor_slot_agent",
            "final_response": "final_response",
        },
    )

    # Routing from Symptom Agent
    builder.add_conditional_edges(
        "symptom_agent",
        post_symptom_router,
        {
            "department_agent": "department_agent",
            "ui_agent": "ui_agent",
        },
    )

    # Routing from Department Agent
    builder.add_conditional_edges(
        "department_agent",
        post_department_router,
        {
            "doctor_slot_agent": "doctor_slot_agent",
            "ui_agent": "ui_agent",
        },
    )

    # Routing from Doctor/Slot Agent (routes to Appointment Agent if booking, else UI Agent)
    builder.add_conditional_edges(
        "doctor_slot_agent",
        post_doctor_slot_router,
        {
            "appointment_agent": "appointment_agent",
            "ui_agent": "ui_agent",
        },
    )

    # Routing from Domain Agents to UI Agent
    builder.add_edge("patient_info_agent", "ui_agent")
    builder.add_edge("location_agent", "ui_agent")
    builder.add_edge("appointment_agent", "ui_agent")

    # UI Action Layer routes to Final Response synthesis
    builder.add_edge("ui_agent", "final_response")

    # Final Response to END
    builder.add_edge("final_response", END)

    return builder.compile()


health_graph = build_health_coordinator_graph()
