import logging
import re
from typing import Dict, Any, List, Optional

from app.models.lab_report import (
    LabReportData,
    LabTestResult,
    LabQuestionResponse,
    LabEvidenceResponse,
)
from app.services.lab_report_service import LabReportService
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class LabReportAgent:
    """
    Lab Report Intelligence Agent.
    Strictly follows clinical guardrails:
    - Extracts test name, result, unit, reference range, report date, laboratory name.
    - Marks values outside reference ranges without diagnosing diseases or generating medical conclusions.
    - Grounded RAG with exact document and page references.
    """

    def __init__(self):
        self.service = LabReportService()

    def get_report(self, doc_id: Optional[str] = None) -> LabReportData:
        if doc_id:
            return self.service.get_report_data(doc_id)
        return self.service.get_latest_lab_report()

    def get_results(self, doc_id: Optional[str] = None) -> List[LabTestResult]:
        report = self.get_report(doc_id)
        return report.tests

    def answer_query(self, question: str, doc_id: Optional[str] = None) -> LabQuestionResponse:
        return self.service.answer_lab_query(question, doc_id)

    def get_page_evidence(self, page_num: int, query: str = "", doc_id: Optional[str] = None) -> LabEvidenceResponse:
        return self.service.get_page_evidence(page_num, query, doc_id)


lab_agent = LabReportAgent()


def lab_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent node for processing laboratory report questions and generating dynamic UI actions:
    - SHOW_LAB_REPORT: Complete lab report overview
    - SHOW_LAB_RESULTS: Tabular test results with reference range status badges
    - SHOW_LAB_EVIDENCE: Page-grounded verification evidence
    """
    user_msg = state.get("user_message") or ""
    if not user_msg:
        messages = state.get("messages", [])
        user_msg = messages[-1].get("content", "") if messages else ""
    user_lower = user_msg.lower().strip()
    actions = list(state.get("actions", []))

    # Identify query intent
    is_evidence = bool(re.search(r"\bpage\s+\d+\b", user_lower) or "page 3" in user_lower or "evidence" in user_lower)
    is_results = any(k in user_lower for k in [
        "what test", "which test", "tests in this", "outside the reference", "outside reference",
        "reference range", "abnormal", "elevated", "high or low", "results", "values"
    ])
    is_report_overview = any(k in user_lower for k in [
        "latest lab", "show my latest", "lab report", "upload lab", "show lab report"
    ])

    if is_evidence:
        page_match = re.search(r"\bpage\s+(\d+)\b", user_lower)
        page_num = int(page_match.group(1)) if page_match else 3
        evidence = lab_agent.get_page_evidence(page_num=page_num, query=user_msg)

        primary_action = "SHOW_LAB_EVIDENCE"
        primary_data = evidence.dict()

        tests_summary = "\n".join([
            f"• **{t.test_name}**: {t.result} {t.unit} (Ref: {t.reference_range} {t.unit}) — *{t.status.replace('_', ' ').title()}*"
            for t in evidence.relevant_tests
        ])

        reply = (
            f"### Laboratory Report Evidence — Page {evidence.page_number}\n\n"
            f"**Extracted Text from {evidence.document_name}**:\n"
            f"> \"{evidence.extracted_text}\"\n\n"
            f"**Panel Tests on Page {evidence.page_number}**:\n{tests_summary}\n\n"
            f"**Page Findings**:\n{evidence.explanation}\n\n"
            f"*(Note: {evidence.disclaimer})*"
        )

    elif is_results or "outside" in user_lower:
        q_res = lab_agent.answer_query(user_msg)
        primary_action = "SHOW_LAB_RESULTS"
        
        report = lab_agent.get_report()
        primary_data = {
            "document_id": report.document_id,
            "document_name": report.file_name,
            "laboratory_name": report.laboratory_name,
            "report_date": report.report_date,
            "total_tests": report.total_tests,
            "out_of_range_count": report.out_of_range_count,
            "tests": [t.dict() for t in (q_res.referenced_tests if q_res.referenced_tests else report.tests)],
            "question": user_msg,
            "disclaimer": report.disclaimer,
        }
        reply = q_res.answer

    else:
        # Default / Overview: SHOW_LAB_REPORT
        report = lab_agent.get_report()
        primary_action = "SHOW_LAB_REPORT"
        primary_data = report.dict()

        out_tests = [t for t in report.tests if t.is_out_of_range]
        out_summary = ", ".join([f"{t.test_name} ({t.result} {t.unit})" for t in out_tests[:4]])
        if len(out_tests) > 4:
            out_summary += f", and {len(out_tests) - 4} more"

        reply = (
            f"### Laboratory Report: {report.file_name}\n\n"
            f"• **Laboratory**: {report.laboratory_name}\n"
            f"• **Report Date**: {report.report_date}\n"
            f"• **Total Tests Analyzed**: {report.total_tests} tests across {report.page_count} pages\n"
            f"• **Outside Stated Reference Range**: **{report.out_of_range_count} test(s)** ({out_summary})\n\n"
            f"You can ask me questions like:\n"
            f"• *\"What tests are in this report?\"*\n"
            f"• *\"Which values are outside the reference range?\"*\n"
            f"• *\"What does page 3 say?\"*\n\n"
            f"*(Note: {report.disclaimer})*"
        )

    actions.append({
        "type": primary_action,
        "action": primary_action,
        "payload": primary_data,
    })

    return {
        **state,
        "actions": actions,
        "primary_ui_action": primary_action,
        "primary_ui_data": primary_data,
        "final_response": reply,
    }
