from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.supervisor import supervisor_node, should_route, final_response_node
from app.agents.symptom_agent import symptom_node


def build_health_coordinator_graph():
    """
    Constructs and compiles the LangGraph for Healthcare Coordination:
    User Message -> Supervisor -> (Symptom Agent if symptoms present) -> Final Response -> END
    """
    builder = StateGraph(AgentState)

    # 1. Add agent nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("symptom_agent", symptom_node)
    builder.add_node("final_response", final_response_node)

    # 2. Entry point
    builder.set_entry_point("supervisor")

    # 3. Conditional routing from supervisor
    builder.add_conditional_edges(
        "supervisor",
        should_route,
        {
            "symptom_agent": "symptom_agent",
            "final_response": "final_response",
        },
    )

    # 4. Routing from symptom agent to final response
    builder.add_edge("symptom_agent", "final_response")

    # 5. Final response to END
    builder.add_edge("final_response", END)

    return builder.compile()


health_graph = build_health_coordinator_graph()
