from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.supervisor import (
    supervisor_node,
    should_route_from_supervisor,
    post_symptom_router,
    post_department_router,
    final_response_node,
)
from app.agents.symptom_agent import symptom_node
from app.agents.department_agent import department_node
from app.agents.doctor_slot_agent import doctor_slot_node


def build_health_coordinator_graph():
    """
    Constructs and compiles the full LangGraph coordinator:
    Supervisor -> { Symptom Agent, Department Agent, Doctor/Slot Agent, Final Response }
    Symptom Agent -> { Department Agent, Final Response }
    Department Agent -> { Doctor/Slot Agent, Final Response }
    Doctor/Slot Agent -> Final Response -> END
    """
    builder = StateGraph(AgentState)

    # 1. Add agent nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("symptom_agent", symptom_node)
    builder.add_node("department_agent", department_node)
    builder.add_node("doctor_slot_agent", doctor_slot_node)
    builder.add_node("final_response", final_response_node)

    # 2. Set supervisor as entry point
    builder.set_entry_point("supervisor")

    # 3. Conditional routing from supervisor
    builder.add_conditional_edges(
        "supervisor",
        should_route_from_supervisor,
        {
            "symptom_agent": "symptom_agent",
            "department_agent": "department_agent",
            "doctor_slot_agent": "doctor_slot_agent",
            "final_response": "final_response",
        },
    )

    # 4. Routing from Symptom Agent
    builder.add_conditional_edges(
        "symptom_agent",
        post_symptom_router,
        {
            "department_agent": "department_agent",
            "final_response": "final_response",
        },
    )

    # 5. Routing from Department Agent
    builder.add_conditional_edges(
        "department_agent",
        post_department_router,
        {
            "doctor_slot_agent": "doctor_slot_agent",
            "final_response": "final_response",
        },
    )

    # 6. Doctor/Slot Agent to Final Response
    builder.add_edge("doctor_slot_agent", "final_response")

    # 7. Final Response to END
    builder.add_edge("final_response", END)

    return builder.compile()


health_graph = build_health_coordinator_graph()
