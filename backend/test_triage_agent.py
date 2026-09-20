from app.agents.triage_agent import detect_red_flags, triage_node


def make_state(message: str):
    return {
        "user_message": message,
        "session_id": "test-session",
        "actions": [],
        "symptoms": [],
        "route": "",
        "final_response": "",
        "country_region": "IN",
        "normal_workflow_allowed": True,
    }


def test_detects_each_red_flag_category():
    examples = {
        "severe crushing chest pain": "chest_pain",
        "I am struggling to breathe": "breathing_difficulty",
        "one side of my face is drooping": "stroke_signs",
        "the bleeding won't stop": "uncontrolled_bleeding",
        "I passed out": "loss_of_consciousness",
        "I am having a seizure": "seizure",
        "my throat is closing and my face is swelling": "severe_allergic_reaction",
        "I want to kill myself": "self_harm_danger",
    }
    for message, category in examples.items():
        assert category in detect_red_flags(message)


def test_non_emergency_message_continues():
    assert detect_red_flags("I have a mild headache and want to book a doctor") == []


def test_negated_red_flags_do_not_trigger():
    assert detect_red_flags("I do not have chest pain and I am not suicidal") == []


def test_emergency_output_blocks_normal_workflow_and_exposes_actions():
    result = triage_node(make_state("I have severe chest pain"))

    assert result["triage_status"] == "EMERGENCY"
    assert result["triage_reason"] == "Potential emergency symptoms detected"
    assert result["matched_categories"] == ["chest_pain"]
    assert result["route"] == "EMERGENCY_WORKFLOW"
    assert result["triage_action"] == "EMERGENCY_WORKFLOW"
    assert result["normal_workflow_allowed"] is False
    assert result["primary_ui_action"] == "SHOW_EMERGENCY_ALERT"
    assert {action["action"] for action in result["actions"]} == {
        "SHOW_EMERGENCY_ALERT",
        "SHOW_EMERGENCY_CONTACTS",
        "SHOW_EMERGENCY_DEPARTMENTS",
        "BLOCK_NORMAL_WORKFLOW",
    }
    assert result["primary_ui_data"]["contacts"][0]["number"] == "112"
    assert result["primary_ui_data"]["contacts"][0]["source_url"] == "https://112.gov.in/"


def test_normal_output_allows_normal_workflow():
    result = triage_node(make_state("Can you find a general physician nearby?"))

    assert result["triage_status"] == "NORMAL"
    assert result["normal_workflow_allowed"] is True
    assert result["triage_action"] == "CONTINUE_WORKFLOW"
    assert "actions" in result and result["actions"] == []
