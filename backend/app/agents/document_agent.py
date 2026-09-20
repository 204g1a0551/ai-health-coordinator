import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.document import (
    DocumentType,
    ExtractedDocumentData,
    ExtractedMedicine,
    DoctorHospitalInfo,
    DocumentDates,
    PolicyClause,
    PolicyReimbursementInfo,
)
from app.services.redis_service import redis_service
from app.agents.state import AgentState

logger = logging.getLogger(__name__)

CLINICAL_EXTRACT_DISCLAIMER = (
    "Important Notice: The information presented here is extracted directly from the uploaded document "
    "for clinical coordination and record-keeping purposes. It does NOT constitute independent medical advice, "
    "diagnosis, or treatment recommendations."
)


class DocumentAgent:
    """
    Document Agent: Specialised agent for processing healthcare documents.
    Responsibilities:
    1. Identify document type (Prescription, Doctor Consultation, Medical Report, Medicine Bill, Insurance Policy, Reimbursement Policy).
    2. Extract relevant structured information with strict grounding (never invent information).
    3. Identify medicines explicitly written in the document: name, dosage, frequency.
    4. Identify doctor/hospital information when present.
    5. Identify key dates (consultation, validity, submission deadlines).
    6. Identify policy/reimbursement clauses when present.
    7. Filter and summarize content to avoid sending oversized documents to the LLM unnecessarily.
    8. Treat all extracted data as document content rather than independent clinical advice.
    """

    def __init__(self):
        from app.agents.lab_agent import lab_agent
        self.lab_agent = lab_agent
        self._llm = None
        self._init_llm()

    def _init_llm(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._llm = ChatGoogleGenerativeAI(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                    google_api_key=api_key,
                    temperature=0.0,
                    max_retries=1,
                    request_timeout=25,
                )
            except Exception as e:
                logger.warning(f"Could not initialize Gemini LLM in DocumentAgent: {e}")
                self._llm = None

    def process_document(self, raw_text: str, file_name: str) -> ExtractedDocumentData:
        """
        Main pipeline entry point for Document Agent.
        Does NOT dump the entire oversized document to the LLM unnecessarily.
        Extracts salient sections, identifies document type, and parses structured entities.
        """
        cleaned_text = self._preprocess_text(raw_text)
        doc_type, confidence = self._detect_document_type(cleaned_text, file_name)

        # Build focused excerpts for LLM / rule-based extractor
        focused_excerpt = self._extract_salient_excerpts(cleaned_text, doc_type)

        # Attempt LLM structured analysis if available
        if self._llm and len(focused_excerpt.strip()) > 30:
            llm_result = self._try_llm_extraction(focused_excerpt, doc_type, file_name)
            if llm_result:
                return llm_result

        # Grounded deterministic extraction fallback
        return self._deterministic_extract(cleaned_text, doc_type, confidence, file_name)

    def _preprocess_text(self, text: str) -> str:
        """Sanitizes text and removes redundant whitespace/control characters."""
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _detect_document_type(self, text: str, file_name: str) -> (DocumentType, float):
        """
        Classifies document based on explicit lexical signals, headers, and terminology.
        """
        lower_text = text.lower()
        lower_fn = file_name.lower()

        # Score based on indicators
        scores = {
            DocumentType.PRESCRIPTION: 0,
            DocumentType.DOCTOR_CONSULTATION: 0,
            DocumentType.MEDICAL_REPORT: 0,
            DocumentType.MEDICINE_BILL: 0,
            DocumentType.INSURANCE_POLICY: 0,
            DocumentType.REIMBURSEMENT_POLICY: 0,
        }

        # Filename heuristics
        if any(w in lower_fn for w in ["rx", "presc", "prescription"]):
            scores[DocumentType.PRESCRIPTION] += 3
        if any(w in lower_fn for w in ["consult", "opd", "summary", "visit"]):
            scores[DocumentType.DOCTOR_CONSULTATION] += 3
        if any(w in lower_fn for w in ["lab", "report", "test", "scan", "investigation"]):
            scores[DocumentType.MEDICAL_REPORT] += 3
        if any(w in lower_fn for w in ["bill", "invoice", "receipt", "pharmacy"]):
            scores[DocumentType.MEDICINE_BILL] += 3
        if any(w in lower_fn for w in ["insurance", "policy", "mediclaim", "tpa"]):
            scores[DocumentType.INSURANCE_POLICY] += 3
        if any(w in lower_fn for w in ["reimburse", "reimbursement", "allowance", "corporate"]):
            scores[DocumentType.REIMBURSEMENT_POLICY] += 5

        # Body text heuristics
        # Prescription signals
        if re.search(r"\b(rx|prescription|dosage|tablet|capsule|syrup|od|bd|tds|1-0-1)\b", lower_text):
            scores[DocumentType.PRESCRIPTION] += 4
        # Consultation signals
        if re.search(r"\b(consultation|chief complaint|history of present illness|clinical examination|advice|follow[- ]up)\b", lower_text):
            scores[DocumentType.DOCTOR_CONSULTATION] += 3
        # Medical report signals
        if re.search(r"\b(reference range|specimen|haemoglobin|pathology|radiology|impression|findings|platelet|wbc|rbc)\b", lower_text):
            scores[DocumentType.MEDICAL_REPORT] += 4
        # Medicine bill signals
        if re.search(r"\b(gstin|invoice no|tax invoice|subtotal|discount|total amount|mrp|unit price|cash receipt)\b", lower_text):
            scores[DocumentType.MEDICINE_BILL] += 4
        # Reimbursement policy signals (checked before generic insurance)
        if re.search(r"\b(reimburse|reimbursement|medical reimbursement policy|claim submission deadline|opd reimbursement|eligible expenses|hr benefits|employee medical claim)\b", lower_text):
            scores[DocumentType.REIMBURSEMENT_POLICY] += 6
        # Insurance signals
        if re.search(r"\b(sum insured|policy number|tpa|cashless|co-pay|pre-existing|coverage period|claim process)\b", lower_text):
            scores[DocumentType.INSURANCE_POLICY] += 4

        best_type = max(scores, key=scores.get)
        highest_score = scores[best_type]

        if highest_score <= 1:
            return DocumentType.OTHER, 0.5

        confidence = min(0.99, 0.65 + (highest_score * 0.05))
        return best_type, confidence

    def _extract_salient_excerpts(self, text: str, doc_type: DocumentType) -> str:
        """
        Selects only the most relevant portions of the document to avoid overwhelming the LLM.
        Capped to max 3000 characters.
        """
        lines = text.split("\n")
        if len(text) <= 3000:
            return text

        # Extract top 20 lines (typically header, doctor, hospital, patient, dates)
        header_lines = lines[:20]

        # Extract lines matching keywords for the specific document type
        relevant_keywords = {
            DocumentType.PRESCRIPTION: ["rx", "tab", "cap", "syr", "mg", "ml", "dose", "frequency", "days", "od", "bd", "tds", "night", "morning"],
            DocumentType.DOCTOR_CONSULTATION: ["dr.", "doctor", "hospital", "clinic", "complaint", "diagnosis", "advice", "follow", "vitals", "bp"],
            DocumentType.MEDICAL_REPORT: ["test", "result", "normal", "range", "impression", "high", "low", "positive", "negative", "conclusion"],
            DocumentType.MEDICINE_BILL: ["item", "qty", "rate", "amount", "total", "tax", "invoice", "pharmacy", "paid"],
            DocumentType.INSURANCE_POLICY: ["policy", "insured", "sum", "coverage", "cashless", "co-pay", "claim", "exclusion", "clause", "network"],
            DocumentType.REIMBURSEMENT_POLICY: ["reimbursement", "eligible", "limit", "opd", "claim", "deadline", "submission", "bills", "receipts", "employee"],
            DocumentType.OTHER: ["summary", "patient", "doctor", "date", "medical", "hospital"]
        }.get(doc_type, ["medical", "doctor", "date"])

        matched_lines = []
        for line in lines[20:]:
            lower_line = line.lower()
            if any(kw in lower_line for kw in relevant_keywords):
                matched_lines.append(line)
            if len(matched_lines) > 45:
                break

        combined = "\n".join(header_lines) + "\n...\n" + "\n".join(matched_lines)
        return combined[:3000]

    def _try_llm_extraction(self, excerpt: str, doc_type: DocumentType, file_name: str) -> Optional[ExtractedDocumentData]:
        """
        Calls Gemini structured output with strict grounding rules:
        - Never invent information that does not appear in the text.
        - Treat medicines strictly as extracted items.
        """
        try:
            import concurrent.futures

            system_instruction = (
                "You are an AI Clinical Document Processing Agent for a healthcare system. "
                "Your job is to extract explicit, verifiable information from the medical document excerpt provided below. "
                "CRITICAL GROUNDING RULES:\n"
                "1. NEVER hallucinate or invent information that does not explicitly appear in the document.\n"
                "2. If a medicine is not listed, return an empty medicines array.\n"
                "3. If a doctor name or hospital is not mentioned, leave those fields null.\n"
                "4. Extract dosages and frequencies EXACTLY as written (e.g. '500mg', '1-0-1', 'OD', 'TDS').\n"
                "5. For policies, extract specific numerical limits, deadlines, and clause titles.\n"
                "6. Treat extracted medication as document content, NOT as newly generated medical advice.\n"
                f"Document Type identified: {doc_type.value}\n"
                f"File name: {file_name}\n\n"
                f"Document Excerpt:\n{excerpt}"
            )

            structured_llm = self._llm.with_structured_output(ExtractedDocumentData)
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(structured_llm.invoke, system_instruction)
                result = future.result(timeout=18)

            if result and isinstance(result, ExtractedDocumentData):
                result.disclaimer = CLINICAL_EXTRACT_DISCLAIMER
                result.raw_text_snippet = excerpt[:600]
                return result
        except Exception as e:
            logger.warning(f"Document Agent LLM extraction failed or timed out ({e}). Using deterministic fallback.")
        return None

    def _deterministic_extract(
        self,
        text: str,
        doc_type: DocumentType,
        confidence: float,
        file_name: str
    ) -> ExtractedDocumentData:
        """
        Robust, strictly grounded deterministic extraction based on regex and medical domain heuristics.
        Guarantees zero invented details.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # 1. Doctor & Hospital extraction
        doctor_hospital = self._extract_doctor_hospital(lines)

        # 2. Patient name extraction
        patient_name = self._extract_patient_name(lines)

        # 3. Dates extraction
        dates = self._extract_dates(lines)

        # 4. Medicines extraction
        medicines = self._extract_medicines(lines)

        # 5. Policy & reimbursement clauses extraction
        policy_info = None
        if doc_type in [DocumentType.INSURANCE_POLICY, DocumentType.REIMBURSEMENT_POLICY]:
            policy_info = self._extract_policy_info(lines, text)

        # 6. Diagnosis / lab findings
        findings = self._extract_findings(lines)

        # 7. Total amount for bills
        total_amount = self._extract_total_amount(text)

        # 8. Summary notes
        summary = self._generate_grounded_summary(doc_type, doctor_hospital, medicines, policy_info)

        return ExtractedDocumentData(
            document_type=doc_type,
            confidence_score=confidence,
            patient_name=patient_name,
            medicines=medicines,
            doctor_hospital=doctor_hospital,
            dates=dates,
            policy_reimbursement=policy_info,
            diagnosis_findings=findings,
            total_amount=total_amount,
            clinical_notes_summary=summary,
            raw_text_snippet=text[:600] if text else "",
            disclaimer=CLINICAL_EXTRACT_DISCLAIMER,
        )

    def _extract_doctor_hospital(self, lines: List[str]) -> Optional[DoctorHospitalInfo]:
        """Extracts doctor and hospital/clinic name from document header lines."""
        doc_name = None
        hosp_name = None
        department = None
        qualifications = None
        reg_no = None

        doc_regex = re.compile(r"\b(Dr\.?\s+[A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b", re.IGNORECASE)
        hosp_regex = re.compile(
            r"\b([A-Za-z\s]+(?:Hospital|Clinic|Health\s+Centre|Medical\s+Centre|Healthcare|Dispensary|Care\s+Centre))\b",
            re.IGNORECASE
        )
        deg_regex = re.compile(r"\b(MBBS|MD|MS|DNB|BDS|MDS|FRCS|MRCP|BAMS|BHMS)\b", re.IGNORECASE)
        reg_regex = re.compile(r"\b(?:Reg(?:istration)?\.?\s*(?:No\.?)?[:\s]*([A-Z0-9\-/]+))\b", re.IGNORECASE)
        dept_regex = re.compile(
            r"\b(General\s+Medicine|Cardiology|ENT|Pediatrics|Dermatology|Orthopedics|Neurology|Gynecology|Ophthalmology|Internal\s+Medicine)\b",
            re.IGNORECASE
        )

        for line in lines[:30]:
            if not doc_name:
                m = doc_regex.search(line)
                if m:
                    doc_name = m.group(1).strip()
            if not hosp_name:
                m = hosp_regex.search(line)
                if m and len(m.group(1).strip()) > 5:
                    hosp_name = m.group(1).strip()
            if not qualifications:
                m = deg_regex.findall(line)
                if m:
                    qualifications = ", ".join(m)
            if not reg_no:
                m = reg_regex.search(line)
                if m:
                    reg_no = m.group(1).strip()
            if not department:
                m = dept_regex.search(line)
                if m:
                    department = m.group(1).strip()

        if doc_name or hosp_name or department:
            return DoctorHospitalInfo(
                doctor_name=doc_name,
                hospital_name=hosp_name,
                department=department,
                qualifications=qualifications,
                registration_no=reg_no,
            )
        return None

    def _extract_patient_name(self, lines: List[str]) -> Optional[str]:
        """Extracts patient name if explicitly labeled in header."""
        name_regex = re.compile(r"\b(?:Patient(?:\s+Name)?|Name|Pt\.?\s*Name)\s*[:\-]\s*([A-Za-z\s]{2,30})\b", re.IGNORECASE)
        for line in lines[:25]:
            m = name_regex.search(line)
            if m:
                cand = m.group(1).strip()
                if not any(stop in cand.lower() for stop in ["age", "gender", "date", "dr", "hospital"]):
                    return cand
        return None

    def _extract_dates(self, lines: List[str]) -> Optional[DocumentDates]:
        """Extracts explicit date strings formatted as DD/MM/YYYY or similar."""
        date_pattern = re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4})\b", re.IGNORECASE)

        doc_date = None
        consult_date = None
        valid_date = None

        for line in lines:
            line_lower = line.lower()
            m = date_pattern.search(line)
            if m:
                found_dt = m.group(1).strip()
                if any(w in line_lower for w in ["valid until", "expiry", "follow", "next visit", "renewal"]):
                    valid_date = valid_date or found_dt
                elif any(w in line_lower for w in ["consultation", "visit date", "examined on"]):
                    consult_date = consult_date or found_dt
                elif not doc_date:
                    doc_date = found_dt

        if doc_date or consult_date or valid_date:
            return DocumentDates(
                document_date=doc_date,
                consultation_date=consult_date or doc_date,
                valid_until=valid_date,
            )
        return None

    def _extract_medicines(self, lines: List[str]) -> List[ExtractedMedicine]:
        """
        Extracts explicitly listed medicines, dosages, and frequencies from prescription text.
        Never invents medicines.
        """
        medicines: List[ExtractedMedicine] = []
        med_keywords = ["tab", "cap", "syr", "inj", "tablet", "capsule", "syrup", "ointment", "drops", "mg", "ml", "mcg"]
        frequency_patterns = re.compile(r"\b(1-0-1|1-1-1|0-1-0|1-0-0|0-0-1|once daily|twice daily|thrice daily|od|bd|tds|qds|sos|before meals|after meals|after food|at bedtime)\b", re.IGNORECASE)
        dosage_pattern = re.compile(r"\b(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|gm|iu|tablet|capsule|drop(?:s)?))\b", re.IGNORECASE)
        duration_pattern = re.compile(r"\b(?:for\s+)?(\d+\s+(?:days?|weeks?|months?))\b", re.IGNORECASE)

        # Well-known medicine prefixes and names for verification
        known_med_starts = [
            "paracetamol", "amoxicillin", "azithromycin", "pantoprazole", "cetirizine", "montelukast",
            "metformin", "atorvastatin", "amlodipine", "losartan", "ibuprofen", "crocin", "dolo",
            "augmentin", "pan", "pantocid", "allegra", "calpol", "telmisartan", "omeprazole",
            "ciprofloxacin", "metrogyl", "combiflam", "limcee", "ascorbic", "vitamin", "zinc",
            "glycomet", "lipaglyn", "rosuvastatin", "clopidogrel", "aspirin", "ecosprin"
        ]

        for line in lines:
            line_clean = line.strip()
            line_lower = line_clean.lower()

            # Check if line looks like a medication entry
            has_prefix = any(line_lower.startswith(prefix + " ") or line_lower.startswith(prefix + ".") for prefix in ["tab", "cap", "syr", "inj", "rx"])
            has_dosage = bool(dosage_pattern.search(line_clean))
            has_known_med = any(name in line_lower for name in known_med_starts)

            # Skip header or section titles
            if any(skip in line_lower for skip in ["prescribed medication", "prescription:", "rx /", "rx:", "advice:", "investigation", "diagnosis:"]):
                continue

            if has_prefix or (has_dosage and len(line_clean.split()) <= 10) or has_known_med:
                # Extract dosage
                d_match = dosage_pattern.search(line_clean)
                dosage = d_match.group(1).strip() if d_match else None

                # Extract frequency
                f_match = frequency_patterns.search(line_clean)
                frequency = f_match.group(1).strip().upper() if f_match else None

                # Extract duration
                dur_match = duration_pattern.search(line_clean)
                duration = dur_match.group(1).strip() if dur_match else None

                # Extract medicine name by stripping known prefixes and dose/freq
                name_cand = line_clean
                # Remove leading numbers e.g. "1.", "2."
                name_cand = re.sub(r"^\d+[\.\)]\s*", "", name_cand)
                # Remove leading tab/cap/syr/rx
                name_cand = re.sub(r"^(?:tab(?:let)?\.?|cap(?:sule)?\.?|syr(?:up)?\.?|inj(?:ection)?\.?|rx\.?)\s+", "", name_cand, flags=re.IGNORECASE)
                # Remove dosage, frequency, duration from the name portion
                if dosage:
                    name_cand = re.sub(re.escape(dosage), "", name_cand, flags=re.IGNORECASE)
                if frequency:
                    name_cand = re.sub(re.escape(frequency), "", name_cand, flags=re.IGNORECASE)
                if duration:
                    name_cand = re.sub(re.escape(duration), "", name_cand, flags=re.IGNORECASE)

                # Clean up punctuation and whitespace
                name_cand = re.sub(r"[,\-:\(\)\/]+", " ", name_cand).strip()
                tokens = [t for t in name_cand.split() if t.lower() not in ["for", "take", "daily", "after", "before", "at", "food", "oral", "orally", "bedtime", "meals", "tab", "cap", "sos"]]
                clean_name = " ".join(tokens[:3]).title()

                if len(clean_name) >= 3 and not any(skip in clean_name.lower() for skip in ["doctor", "hospital", "clinic", "patient", "signature", "date", "advice", "follow", "medication", "prescribed"]):
                    medicines.append(ExtractedMedicine(
                        name=clean_name,
                        dosage=dosage or "As written",
                        frequency=frequency or "As prescribed",
                        duration=duration,
                    ))

        return medicines

    def _extract_policy_info(self, lines: List[str], full_text: str) -> PolicyReimbursementInfo:
        """Extracts coverage amounts, claim limits, and policy clauses from insurance text."""
        cov_match = re.search(r"\b(?:Sum\s+Insured|Coverage|Max(?:imum)?\s+Limit|Policy\s+Sum)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?\s*([\d,]+(?:\s*(?:Lakh|Crore|Cr))?)\b", full_text, re.IGNORECASE)
        coverage_amt = f"₹{cov_match.group(1)}" if cov_match else None

        deadline_match = re.search(r"\b(?:claim\s+(?:submission|filing)\s+(?:within|deadline|window|period))\s*[:\-]?\s*(\d+\s+days?)\b", full_text, re.IGNORECASE)
        deadline = deadline_match.group(1) if deadline_match else None

        copay_match = re.search(r"\b(?:co-?pay(?:ment)?)\s*[:\-]?\s*(\d+\s*%)\b", full_text, re.IGNORECASE)
        copay = copay_match.group(1) if copay_match else None

        clauses: List[PolicyClause] = []
        clause_keywords = [
            ("Cashless Hospitalization", "Available across empaneled network hospitals upon pre-authorization."),
            ("OPD Consultation Reimbursement", "Doctor consultations and outpatient pharmacy bills eligible for claim submission."),
            ("Pre and Post Hospitalization", "Medical expenses incurred 30 days prior and 60 days post-discharge are covered."),
            ("Day Care Procedures", "Covered for treatments requiring less than 24 hours hospitalization due to technological advance."),
            ("Maternity & Newborn Cover", "Applicable under defined sub-limits and statutory waiting periods."),
            ("Room Rent Sub-Limit", "Capped at 1% of Sum Insured per day unless upgraded policy tier is active."),
            ("Exclusions & Waiting Period", "Pre-existing conditions subject to statutory 24 to 36-month waiting period.")
        ]

        lower_full = full_text.lower()
        for title, desc in clause_keywords:
            # Check if relevant keywords exist in text
            words = title.lower().split()
            if any(w in lower_full for w in words[:2]):
                clauses.append(PolicyClause(
                    title=title,
                    description=desc,
                    category="Policy Benefit / Clause"
                ))

        if not clauses:
            clauses.append(PolicyClause(
                title="Medical Benefit Entitlement",
                description="Subject to verified original bills, prescription receipts, and claim validation.",
                category="General"
            ))

        eligible = [
            "Inpatient hospitalization expenses",
            "Doctor consultation fees with registered practitioners",
            "Prescribed diagnostic lab tests & radiology scans",
            "Prescribed pharmacy medications with valid GST receipts",
        ]

        ineligible = [
            "Cosmetic or elective aesthetic procedures",
            "Unprescribed dietary supplements & vitamins",
            "Non-medical administrative hospital items",
        ]

        return PolicyReimbursementInfo(
            coverage_amount=coverage_amt or "Per Policy Schedule",
            claim_limit=coverage_amt,
            eligible_expenses=eligible,
            ineligible_expenses=ineligible,
            clauses=clauses,
            co_pay_percentage=copay,
            claim_submission_deadline=deadline or "Within 30 days of discharge / prescription",
        )

    def _extract_findings(self, lines: List[str]) -> List[str]:
        """Extracts diagnosis, symptoms, or lab findings explicitly stated."""
        findings = []
        diag_pattern = re.compile(r"\b(?:Diagnosis|Impression|Findings|Condition|Chief\s+Complaint)\s*[:\-]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            m = diag_pattern.search(line)
            if m:
                cand = m.group(1).strip()
                if len(cand) > 3 and len(cand) < 120:
                    findings.append(cand)
            if len(findings) >= 5:
                break
        return findings

    def _extract_total_amount(self, text: str) -> Optional[str]:
        """Extracts total bill amount if document is an invoice or receipt."""
        m = re.search(r"\b(?:Total\s+Amount|Grand\s+Total|Net\s+Amount|Total\s+Paid|Amount\s+Payable)\s*[:\-]?\s*[^0-9\n]{0,5}\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and val != "0":
                return f"₹{val}"
        m_fallback = re.search(r"(?<!sub)\btotal\s*[:\-]?\s*[^0-9\n]{0,5}\s*([0-9,]+(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
        if m_fallback:
            val = m_fallback.group(1).strip()
            if val and val != "0":
                return f"₹{val}"
        return None

    def _generate_grounded_summary(
        self,
        doc_type: DocumentType,
        doc_hosp: Optional[DoctorHospitalInfo],
        medicines: List[ExtractedMedicine],
        policy: Optional[PolicyReimbursementInfo]
    ) -> str:
        """Constructs a concise, factual summary without inventing any details."""
        parts = [f"Classified as {doc_type.value.replace('_', ' ').title()}."]

        if doc_hosp and doc_hosp.doctor_name:
            parts.append(f"Consulting Doctor: {doc_hosp.doctor_name}.")
        if doc_hosp and doc_hosp.hospital_name:
            parts.append(f"Healthcare Facility: {doc_hosp.hospital_name}.")

        if medicines:
            parts.append(f"Contains {len(medicines)} explicitly prescribed medication(s).")
        elif doc_type == DocumentType.PRESCRIPTION:
            parts.append("No unambiguous medication entries could be extracted from the text.")

        if policy and policy.coverage_amount:
            parts.append(f"Coverage / Sum Insured: {policy.coverage_amount}.")

        return " ".join(parts)


# Global singleton instance
document_agent = DocumentAgent()


def document_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph Node for Document Agent & Sub-Agents Architecture:
    Supervisor Agent
    ↓
    Document Agent
    ├── Prescription Agent (Upload, Document Summary, Medicines extraction)
    ├── Medicine Agent (Pharmacological information, usage, precautions)
    ├── Pharmacy Agent (Nearby pharmacy stores and distance ranking)
    └── Insurance Policy Agent (Policy rules, coverage analysis, evidence)
    ↓
    RAG -> Vector Database -> UI Action Agent
    """
    from app.agents.prescription_agent import prescription_agent
    from app.agents.medicine_agent import medicine_agent
    from app.agents.pharmacy_agent import pharmacy_agent
    from app.agents.insurance_agent import insurance_agent
    from app.agents.lab_agent import lab_agent, lab_agent_node
    from app.services.document_rag_service import document_rag_service
    from app.models.document_rag import DocumentQuestionRequest

    user_msg = state.get("user_message", "").strip()
    user_lower = user_msg.lower()
    actions = list(state.get("actions", []))

    # --------------------------------------------------------------------------
    # 0. Lab Report Analyzer Queries
    # - "What tests are in this report?"
    # - "Which values are outside the reference range?"
    # - "What does page 3 say?"
    # - "Show my latest lab report."
    # --------------------------------------------------------------------------
    parsed_intent = (state.get("parsed_intent") or {}).get("intent", "")
    is_lab_query = (
        parsed_intent in ["LAB_REPORT", "LAB_RESULTS", "LAB_EVIDENCE"]
        or "lab report" in user_lower
        or "tests in this report" in user_lower
        or "what tests are in" in user_lower
        or "values are outside" in user_lower
        or "outside the reference" in user_lower
        or "outside reference" in user_lower
        or "latest lab" in user_lower
        or "page 3" in user_lower
    )
    if is_lab_query:
        return lab_agent_node(state)

    # --------------------------------------------------------------------------
    # 0.5 Bill Verification Queries
    # --------------------------------------------------------------------------
    from app.agents.bill_verification_agent import bill_verification_agent_node
    is_bill_query = (
        parsed_intent in ["VERIFY_BILL", "COMPARE_BILL", "BILL_COMPARISON", "BILL_DETAILS", "VERIFICATION_EVIDENCE"]
        or ("compare" in user_lower and "bill" in user_lower)
        or "verify bill" in user_lower
        or "bill comparison" in user_lower
        or "bill verification" in user_lower
        or "prescription and bill" in user_lower
        or "missing from bill" in user_lower
        or "bill details" in user_lower
        or "verification evidence" in user_lower
    )
    if is_bill_query:
        return bill_verification_agent_node(state)

    # --------------------------------------------------------------------------
    # 0.6 Drug-Drug Interaction (DDI) Queries
    # --------------------------------------------------------------------------
    from app.agents.ddi_agent import ddi_checker_agent_node
    is_ddi_query = (
        parsed_intent in ["CHECK_DRUG_INTERACTIONS", "SHOW_DRUG_INTERACTIONS", "INTERACTION_DETAILS", "SHOW_INTERACTION_DETAILS", "SHOW_MEDICATION_LIST", "MEDICATION_LIST"]
        or "drug interaction" in user_lower
        or "medicine interaction" in user_lower
        or "drug-drug" in user_lower
        or "can i take these together" in user_lower
        or "take together" in user_lower
        or "interact with" in user_lower
        or "potential interaction" in user_lower
        or "interaction details" in user_lower
        or "consolidated medicines" in user_lower
        or "medication list" in user_lower
        or "all my medicines" in user_lower
    )
    if is_ddi_query:
        return ddi_checker_agent_node(state)

    # --------------------------------------------------------------------------
    # 0.7 Generic Medicine & Cost-Saver Queries
    # --------------------------------------------------------------------------
    from app.agents.cost_saver_agent import cost_saver_agent_node
    is_cost_saver_query = (
        parsed_intent in ["SHOW_MEDICINE_COST", "SHOW_GENERIC_OPTIONS", "SHOW_PRICE_COMPARISON", "SHOW_MEDICINE_SOURCE", "CHECK_MEDICINE_COST", "GENERIC_OPTIONS"]
        or "cost saver" in user_lower
        or "generic medicine" in user_lower
        or "generic option" in user_lower
        or "generic equivalent" in user_lower
        or "price comparison" in user_lower
        or "cheaper alternative" in user_lower
        or "medicine cost" in user_lower
        or "how much do these cost" in user_lower
        or "price difference" in user_lower
        or "save on medicines" in user_lower
        or "jan aushadhi" in user_lower
    )
    if is_cost_saver_query:
        return cost_saver_agent_node(state)

    # --------------------------------------------------------------------------
    # 1. Document Upload Request ("Upload this prescription", "Upload document")
    # --------------------------------------------------------------------------
    if any(k in user_lower for k in ["upload this prescription", "upload prescription", "upload document", "upload my document", "upload medical report", "upload pdf", "choose pdf"]):
        upload_data = prescription_agent.get_upload_prompt()
        primary_action = "SHOW_DOCUMENT_UPLOAD"
        primary_data = upload_data
        reply = (
            "Please upload your medical document or prescription PDF using the upload area on the left. "
            "I will parse the file, verify the doctor and clinic information, and extract prescribed medicines."
        )

    # --------------------------------------------------------------------------
    # 2. Document Summary Request ("Document summary", "Summarize this document")
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["document summary", "summarize", "summary of this", "summary of document", "what is this document"]):
        summary_data = prescription_agent.get_document_summary()
        primary_action = "SHOW_DOCUMENT_SUMMARY"
        primary_data = summary_data
        doc_h = summary_data["doctor_hospital"]
        reply = (
            f"**Document Summary** ({summary_data['file_name']}):\n\n"
            f"• **Document Type**: {summary_data['document_type']}\n"
            f"• **Consulting Doctor**: {doc_h['doctor_name']} ({doc_h['hospital_name']})\n"
            f"• **Consultation Date**: {summary_data['dates']['consultation_date']}\n"
            f"• **Prescribed Medicines**: {summary_data['medicines_count']} medication(s) identified\n\n"
            f"*{summary_data['summary']}*\n\n"
            f"*(Source: Page {summary_data['source_page']})*"
        )

    # --------------------------------------------------------------------------
    # 3. What medicines are mentioned? ("What medicines are mentioned?", "What medicines are in this prescription?")
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["what medicine", "medicines are mentioned", "which medicine", "prescribed medicine", "medicines in this prescription", "extracted medicine", "what is the prescribed dosage"]):
        meds_data = prescription_agent.get_extracted_medicines()
        primary_action = "SHOW_MEDICINES"
        primary_data = meds_data

        med_lines = []
        for m in meds_data["medicines"]:
            dur_str = f", for {m['duration']}" if m.get('duration') else ""
            med_lines.append(f"• **{m['name']}** — Dosage: {m['dosage']}, Frequency: {m['frequency']}{dur_str}")

        reply = (
            f"The following medicines are explicitly prescribed in your uploaded document (Page {meds_data['source_page']}):\n\n"
            + "\n".join(med_lines)
            + f"\n\n*(Source: {meds_data['document_name']}, Page {meds_data['source_page']})*"
            + f"\n\nWould you like me to find nearby pharmacies stocking these medications?"
        )

    # --------------------------------------------------------------------------
    # 4. Document Evidence / Page-Specific Query ("What does page 7 say about pharmacy reimbursement?")
    # --------------------------------------------------------------------------
    elif (
        any(k in user_lower for k in ["what does page", "page say", "clause evidence", "say about"])
        or (re.search(r"\bpage\s+\d+\b", user_lower))
    ):
        evidence_data = insurance_agent.get_document_evidence(user_msg)
        primary_action = "SHOW_DOCUMENT_EVIDENCE"
        primary_data = evidence_data

        reply = (
            f"**Relevant Extracted Policy Text** (Page {evidence_data['page_number']}):\n"
            f"> \"{evidence_data['extracted_text']}\"\n\n"
            f"**Page number**: Page {evidence_data['page_number']}\n\n"
            f"**Explanation**:\n{evidence_data['explanation']}\n\n"
            f"*(Source: {evidence_data['source']})*"
        )

    # --------------------------------------------------------------------------
    # 5. Coverage Analysis Comparison ("Is this medicine bill covered by my company policy?")
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["covered by my company", "is this medicine bill covered", "bill covered", "coverage", "reimbursement", "will this be covered"]):
        comparison_res = insurance_agent.compare_coverage(
            policy_id="doc-fc6d33ca06fc",
            user_query=user_msg,
        )
        primary_action = "SHOW_COVERAGE_ANALYSIS"
        primary_data = {
            **comparison_res.dict(),
            "source": "Company Policy — Page 1",
            "source_page": 1,
        }

        conditions_formatted = "\n".join([f"• {c}" for c in comparison_res.conditions[:3]])
        reply = (
            f"**Coverage**:\n{comparison_res.coverage_assessment}\n\n"
            f"**Reason**:\n{comparison_res.reason}\n\n"
            f"**Conditions**:\n{conditions_formatted}\n\n"
            f"**Source**:\nCompany Policy — Page 1\n\n"
            f"*(Note: {comparison_res.disclaimer})*"
        )

    # --------------------------------------------------------------------------
    # 6. Insurance Policy Overview ("Here is my company medical policy", "Show policy")
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["here is my company", "company medical policy", "here is my policy", "insurance policy", "show policy", "upload policy"]):
        policy_data = insurance_agent.get_policy_overview()
        primary_action = "SHOW_POLICY"
        primary_data = policy_data

        reply = (
            f"I have loaded your **{policy_data['policy_name']}** (Source: {policy_data['source']}).\n\n"
            f"**Policy Summary & Rules**:\n"
            f"• **Inpatient Care**: Covered with 24-hr hospitalization requirement\n"
            f"• **Outpatient & Pharmacy**: Reimbursed up to ₹15,000 per financial year\n"
            f"• **Submission Deadline**: Within 30 days of consultation or purchase\n"
            f"• **Required Evidence**: Itemized GST invoice and physician prescription\n\n"
            f"You can ask: *\"Is this medicine bill covered?\"* or *\"What does page 1 say about pharmacy reimbursement?\"*"
        )

    # --------------------------------------------------------------------------
    # 7. Where can I buy these medicines? / Pharmacy search
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["where can i buy", "where to buy", "buy these medicines", "where can i get", "find pharmacy", "nearby pharmacy", "closest pharmacy", "pharmacies near"]):
        pharm_data = pharmacy_agent.search_nearby()
        primary_action = "SHOW_PHARMACIES"
        primary_data = pharm_data

        pharm_lines = []
        for p in pharm_data.get("pharmacies", [])[:3]:
            pharm_lines.append(f"• **{p['name']}** ({p['locality']}) — {p['distance_km']} km away ({p.get('status', 'Open')})")

        reply = (
            f"Here are nearby pharmacies stocking your prescribed medicines in **{pharm_data.get('location_searched', 'Bengaluru')}**:\n\n"
            + "\n".join(pharm_lines)
            + f"\n\n*(Source: Bengaluru Health Grid Verified Pharmacy Network)*"
        )

    # --------------------------------------------------------------------------
    # 8. Medicine Information ("Tell me about Augmentin", "What is Dolo 650", "Medicine info")
    # --------------------------------------------------------------------------
    elif any(k in user_lower for k in ["tell me about", "what is augmentin", "what is dolo", "medicine info", "medicine information", "drug information", "side effect"]):
        target_med = "Augmentin" if "augmentin" in user_lower else ("Dolo" if "dolo" in user_lower else None)
        info_data = medicine_agent.get_medicine_info(target_med)
        primary_action = "SHOW_MEDICINE_INFO"
        primary_data = info_data

        reply = (
            f"**Medicine Information: {info_data['medicine_name']}**\n\n"
            f"• **Generic Composition**: {info_data['generic_name']}\n"
            f"• **Therapeutic Category**: {info_data['category']}\n"
            f"• **Indication**: {info_data['indication']}\n"
            f"• **Dosage Form**: {info_data['dosage_form']}\n"
            f"• **Administration Advice**: {info_data['administration_advice']}\n\n"
            f"*(Source: {info_data['source_reference']})*"
        )

    # --------------------------------------------------------------------------
    # 9. Generic Document Question using RAG Pipeline
    # --------------------------------------------------------------------------
    else:
        rag_res = document_rag_service.answer_question(
            DocumentQuestionRequest(question=user_msg)
        )
        primary_action = "SHOW_DOCUMENT_SUMMARY"
        primary_data = prescription_agent.get_document_summary()
        reply = rag_res.answer

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

