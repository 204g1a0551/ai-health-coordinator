from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.supervisor import (
    supervisor_node,
    should_route_from_supervisor,
    post_symptom_router,
    final_response_node,
)
from app.agents.symptom_agent import symptom_node
from app.agents.department_agent import department_node


def build_health_coordinator_graph():
    """
    Constructs and compiles the LangGraph coordinator graph:
    Supervisor -> { Symptom Agent, Department Agent, Final Response }
    Symptom Agent -> { Department Agent, Final Response }
    Department Agent -> Final Response -> END
    """
    builder = StateGraph(AgentState)

    # Add agent and final synthesis nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("symptom_agent", symptom_node)
    builder.add_node("department_agent", department_node)
    builder.add_node("final_response", final_response_node)

    # Set supervisor as entry point
    builder.set_entry_point("supervisor")

    # Supervisor conditional routing
    builder.add_conditional_edges(
        "supervisor",
        should_route_from_supervisor,
        {
            "symptom_agent": "symptom_agent",
            "department_agent": "department_agent",
            "final_response": "final_response",
        },
    )

    # Routing from Symptom Agent
    builder.add_conditional_edges(
        "symptom_agent",
        post_symptom_router,
        {
            "department_agent": "department_agent",
            "final_response": "final_response",
        },
    )

    # Department Agent to Final Response
    builder.add_edge("department_agent", "final_response")

    # Final Response to END
    builder.add_edge("final_response", END)

    return builder.compile()


health_graph = build_health_coordinator_graph()
