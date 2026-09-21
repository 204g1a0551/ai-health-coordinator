import re
import math
from typing import Dict, Any, List, Optional, Tuple

# ==============================================================================
# Comprehensive Medical Big Data Corpus
# Mapped across 16 medical specialties with 500+ symptoms, lab findings, and diseases.
# Includes deep lab markers: Platelets, Hemoglobin, Creatinine, HbA1c, TSH, Bilirubin.
# ==============================================================================
MEDICAL_BIGDATA_CORPUS = [
    # --------------------------------------------------------------------------
    # 1. Hematology (Blood Disorders, Platelet Abnormalities, Coagulation)
    # --------------------------------------------------------------------------
    {
        "department": "Hematology",
        "primary_symptom": "Low Platelets / Thrombocytopenia",
        "severity": "High",
        "keywords": [
            "platelet", "platelets", "platelet count", "low platelets", "platelet drop",
            "thrombocytopenia", "platelet deficiency", "platelets dropping", "platelet levels",
            "low platelet count", "platelet count 50000", "platelet count 20000", "platelet count 80000",
            "dengue platelets", "dengue platelet drop", "petechiae", "purpura", "easy bruising",
            "spontaneous bleeding", "bleeding gums with low platelets", "unexplained bruises",
            "prolonged bleeding", "blood clotting issue", "idiopathic thrombocytopenic purpura", "itp",
            "anemia", "low hemoglobin", "severe anemia", "pale skin and fatigue", "hemolytic anemia",
            "leukemia", "blood cancer screening", "high wbc count", "leukocytosis", "abnormal cbc report",
            "cbc report platelets", "bone marrow disorder", "sickle cell", "thalassemia", "coagulopathy"
        ],
        "description": "Evaluation of blood components, platelet counts, coagulation, anemia, and hematologic disorders."
    },

    # --------------------------------------------------------------------------
    # 2. Gastroenterology (Digestive, Liver, Stomach, Intestinal)
    # --------------------------------------------------------------------------
    {
        "department": "Gastroenterology",
        "primary_symptom": "Gastrointestinal Disorder",
        "severity": "Medium",
        "keywords": [
            "stomach pain", "stomach ache", "abdominal pain", "belly pain", "severe stomach cramps",
            "acid reflux", "heartburn", "gerd", "gastric burning", "gastritis", "stomach burning",
            "indigestion", "dyspepsia", "bloating", "gas pain", "excessive belching", "sour burps",
            "peptic ulcer", "stomach ulcer", "duodenal ulcer", "vomiting blood", "hematemesis",
            "black stool", "melena", "blood in stool", "rectal bleeding", "diarrhea", "chronic diarrhea",
            "watery stool", "severe constipation", "bowel obstruction", "irritable bowel syndrome", "ibs",
            "inflammatory bowel disease", "ibd", "crohn's disease", "ulcerative colitis", "liver pain",
            "fatty liver", "jaundice", "yellow eyes and skin", "high bilirubin", "sgpt high", "sgot high",
            "elevated liver enzymes", "cirrhosis", "hepatitis", "gallbladder stones", "gallstones",
            "cholecystitis", "pancreatitis", "loss of appetite", "difficulty swallowing", "dysphagia"
        ],
        "description": "Evaluation of digestive system, stomach, intestines, liver, gallbladder, and pancreas."
    },

    # --------------------------------------------------------------------------
    # 3. Cardiology (Heart, Cardiovascular, Coronary Care)
    # --------------------------------------------------------------------------
    {
        "department": "Cardiology",
        "primary_symptom": "Cardiovascular / Cardiac Symptom",
        "severity": "Emergency",
        "keywords": [
            "heart attack", "heartattack", "cardiac arrest", "chest pain", "chest tightness",
            "chest pressure", "crushing chest pain", "pain radiating to left arm", "angina",
            "angina pectoris", "palpitation", "palpitations", "racing heart", "irregular heartbeat",
            "arrhythmia", "tachycardia", "bradycardia", "high blood pressure", "hypertension",
            "severe hypertension", "bp spike", "coronary artery disease", "heart failure",
            "shortness of breath on exertion", "orthopnea", "swollen ankles heart", "cardiac murmur",
            "ecg abnormal", "troponin positive", "valvular heart disease", "pericarditis"
        ],
        "description": "Evaluation of cardiovascular system, heart disorders, hypertension, and cardiac emergencies."
    },

    # --------------------------------------------------------------------------
    # 4. Pulmonology (Lungs, Respiratory System)
    # --------------------------------------------------------------------------
    {
        "department": "Pulmonology",
        "primary_symptom": "Respiratory / Pulmonary Disorder",
        "severity": "High",
        "keywords": [
            "asthma", "asthma attack", "wheezing", "shortness of breath", "difficulty breathing",
            "breathlessness", "cannot catch breath", "chronic cough", "dry cough for months",
            "coughing up blood", "hemoptysis", "phlegm", "productive cough", "copd",
            "emphysema", "chronic bronchitis", "pneumonia", "lung infection", "tuberculosis", "tb",
            "pleurisy", "pleural effusion", "chest congestion", "heavy chest breathing",
            "sleep apnea", "snoring and breathing stops", "pulmonary fibrosis", "bronchiectasis"
        ],
        "description": "Evaluation of lungs, bronchial passages, respiratory capacity, and chronic airway diseases."
    },

    # --------------------------------------------------------------------------
    # 5. Neurology (Brain, Nerves, Spine, Nervous System)
    # --------------------------------------------------------------------------
    {
        "department": "Neurology",
        "primary_symptom": "Neurological Disorder",
        "severity": "High",
        "keywords": [
            "migraine", "severe migraine", "throbbing headache", "cluster headache", "chronic headache",
            "dizziness", "vertigo", "spinning sensation", "loss of balance", "unsteady walking",
            "seizure", "seizures", "epileptic fit", "convulsions", "stroke", "paralysis",
            "facial droop", "arm weakness", "slurred speech", "numbness", "tingling in hands",
            "pins and needles", "neuropathy", "peripheral neuropathy", "diabetic nerve pain",
            "tremor", "hand tremors", "parkinson's", "memory loss", "confusion", "amnesia",
            "dementia", "alzheimer's", "sciatica nerve pain", "cervical radiculopathy", "multiple sclerosis"
        ],
        "description": "Evaluation of brain, spinal cord, cranial nerves, peripheral nerves, and stroke management."
    },

    # --------------------------------------------------------------------------
    # 6. Endocrinology & Diabetology (Hormones, Diabetes, Thyroid, Metabolism)
    # --------------------------------------------------------------------------
    {
        "department": "Endocrinology",
        "primary_symptom": "High Blood Sugar / Diabetes / Thyroid",
        "severity": "Medium",
        "keywords": [
            "diabetes", "type 1 diabetes", "type 2 diabetes", "high blood sugar", "hyperglycemia",
            "blood sugar", "blood sugar high", "sugar is high", "sugar high", "fasting blood sugar",
            "fasting blood sugar high", "hba1c", "hba1c high", "hba1c is high", "blood glucose spike", "low blood sugar",
            "hypoglycemia", "excessive thirst", "polydipsia", "frequent urination night", "polyuria",
            "unexplained weight loss", "unexplained weight gain", "thyroid", "tsh high", "tsh low",
            "hypothyroidism", "hyperthyroidism", "goiter", "thyroid nodule", "hormonal imbalance",
            "adrenal disorder", "cushing's syndrome", "addison's disease", "osteoporosis bone density",
            "high prolactin", "calcium metabolism", "parathyroid"
        ],
        "description": "Specialized diagnosis and management of diabetes, thyroid conditions, and hormonal imbalances."
    },

    # --------------------------------------------------------------------------
    # 7. Nephrology & Urology (Kidneys, Urinary Tract, Bladder)
    # --------------------------------------------------------------------------
    {
        "department": "Nephrology",
        "primary_symptom": "Renal / Kidney / Urinary Disorder",
        "severity": "High",
        "keywords": [
            "kidney pain", "flank pain", "back kidney area pain", "kidney stone", "renal calculi",
            "creatinine", "high creatinine", "elevated urea", "creatinine 2.5", "kidney failure", "renal impairment",
            "blood in urine", "hematuria", "burning urination", "dysuria", "urinary tract infection", "uti",
            "frequent urination", "foamy urine", "frothy urine", "protein in urine", "proteinuria",
            "decreased urine output", "oliguria", "swollen feet kidney", "edema", "dialysis consultation",
            "kidney cysts", "polycystic kidney", "prostate enlargement", "bph", "urinary incontinence"
        ],
        "description": "Diagnosis and treatment of kidney diseases, kidney stones, creatinine elevation, and urinary disorders."
    },

    # --------------------------------------------------------------------------
    # 8. Dermatology (Skin, Hair, Nails)
    # --------------------------------------------------------------------------
    {
        "department": "Dermatology",
        "primary_symptom": "Dermatological / Skin Condition",
        "severity": "Low",
        "keywords": [
            "rash", "skin rash", "itchy skin", "itching", "pruritus", "hives", "urticaria",
            "eczema", "atopic dermatitis", "psoriasis", "silvery scales on skin", "acne", "severe acne",
            "pimples", "cystic acne", "skin breakout", "fungal infection", "ringworm", "athlete's foot",
            "hair loss", "alopecia", "excessive hair fall", "scalp itching", "dandruff", "mole check",
            "skin lesion", "skin discoloration", "vitiligo", "pigmentation", "melasma", "boils", "furuncle",
            "cellulitis", "skin allergy", "dry peeling skin", "blisters on skin", "nail infection"
        ],
        "description": "Evaluation of skin conditions, allergies, rashes, acne, hair, and nail problems."
    },

    # --------------------------------------------------------------------------
    # 9. Orthopedics (Bones, Joints, Muscles, Spine)
    # --------------------------------------------------------------------------
    {
        "department": "Orthopedics",
        "primary_symptom": "Musculoskeletal / Orthopedic Disorder",
        "severity": "Medium",
        "keywords": [
            "fracture", "small fracture", "hairline fracture", "bone fracture", "broken bone",
            "bone crack", "cracked bone", "bone pain", "fractured bone", "wrist fracture",
            "ankle fracture", "finger fracture", "leg fracture", "arm fracture", "toe fracture",
            "joint pain", "knee pain", "knee swelling", "knee stiffness", "difficulty walking pain",
            "back pain", "lower back ache", "lumbago", "slip disc", "herniated disc", "sciatica",
            "neck pain", "cervical spondylosis", "shoulder pain", "frozen shoulder", "rotator cuff",
            "wrist pain", "ankle pain", "sprain", "twisted ankle", "ligament tear", "acl tear",
            "meniscus tear", "arthritis", "osteoarthritis", "rheumatoid arthritis joint", "gout",
            "high uric acid pain", "swollen big toe", "osteoporosis", "hip pain", "heel pain", "plantar fasciitis"
        ],
        "description": "Diagnosis and management of bone fractures, joint arthritis, back pain, and musculoskeletal injuries."
    },

    # --------------------------------------------------------------------------
    # 10. ENT (Ear, Nose, Throat, Sinus)
    # --------------------------------------------------------------------------
    {
        "department": "ENT",
        "primary_symptom": "Ear, Nose, or Throat Disorder",
        "severity": "Low",
        "keywords": [
            "earache", "ear pain", "ear discharge", "fluid in ear", "blocked ear", "ear fullness",
            "tinnitus", "ringing in ear", "hearing loss", "partial deafness", "ear wax blockage",
            "sore throat", "throat pain", "pain swallowing", "tonsillitis", "enlarged tonsils",
            "hoarse voice", "laryngitis", "voice loss", "sinus", "sinusitis", "facial sinus pain",
            "nasal congestion", "blocked nose", "runny nose", "deviated nasal septum", "dns",
            "nosebleed", "epistaxis", "foreign body in ear", "loss of smell", "anosmia", "adenoids"
        ],
        "description": "Specialized clinical care for ear, nose, sinus, throat, voice, and hearing conditions."
    },

    # --------------------------------------------------------------------------
    # 11. Ophthalmology (Eyes, Vision)
    # --------------------------------------------------------------------------
    {
        "department": "Ophthalmology",
        "primary_symptom": "Eye / Vision Disorder",
        "severity": "Medium",
        "keywords": [
            "eye pain", "red eye", "pink eye", "conjunctivitis", "blurry vision", "blurred vision",
            "vision loss", "sudden vision drop", "double vision", "diplopia", "watery eyes",
            "dry eyes", "burning eyes", "stye", "swollen eyelid", "foreign object in eye",
            "sensitivity to light", "photophobia", "flashes of light", "floaters in vision",
            "cataract", "cloudy vision", "glaucoma", "high eye pressure", "spectacles check",
            "refractive error", "myopia", "astigmatism", "diabetic retinopathy screening"
        ],
        "description": "Comprehensive vision testing, eye disease diagnosis, cataract, and glaucoma care."
    },

    # --------------------------------------------------------------------------
    # 12. Dental (Teeth, Gums, Oral Cavity)
    # --------------------------------------------------------------------------
    {
        "department": "Dental",
        "primary_symptom": "Dental / Oral Condition",
        "severity": "Low",
        "keywords": [
            "toothache", "tooth pain", "severe tooth pain", "teeth sensitivity", "sensitive teeth to cold",
            "cavity", "tooth decay", "caries", "bleeding gums", "gingivitis", "swollen gums", "gum boil",
            "periodontitis", "wisdom tooth pain", "impacted wisdom tooth", "broken tooth", "chipped tooth",
            "mouth ulcer", "canker sore", "bad breath", "halitosis", "jaw pain chewing", "tmj pain",
            "root canal consultation", "dental crown", "teeth cleaning", "tartar removal", "dental implant"
        ],
        "description": "Dental diagnosis, tooth cavity treatments, root canal therapy, and gum health."
    },

    # --------------------------------------------------------------------------
    # 13. Gynecology & Obstetrics (Women's Health, Pregnancy)
    # --------------------------------------------------------------------------
    {
        "department": "Gynecology",
        "primary_symptom": "Gynecological / Menstrual Condition",
        "severity": "Medium",
        "keywords": [
            "periods", "period", "my periods", "have periods", "period pain", "missed period",
            "missed periods", "delayed period", "delayed periods", "heavy periods", "period blood",
            "irregular periods", "menstrual irregularities", "heavy menstrual bleeding", "menstrual",
            "menses", "spotting", "menorrhagia", "severe period cramps", "period cramps", "menstrual cramps",
            "dysmenorrhea", "pelvic pain", "pregnancy", "pregnant", "positive pregnancy test", "prenatal checkup",
            "morning sickness", "pcos", "pcod", "ovarian cyst", "uterine fibroids", "vaginal discharge",
            "vaginal itching", "yeast infection", "post-menopausal bleeding", "hot flashes", "menopause symptoms",
            "endometriosis", "fertility consultation", "conception advice", "pap smear screening", "breast lump screening"
        ],
        "description": "Comprehensive women's healthcare, obstetric pregnancy care, PCOS, and reproductive medicine."
    },

    # --------------------------------------------------------------------------
    # 14. Psychiatry & Mental Health (Behavioral Health, Mood)
    # --------------------------------------------------------------------------
    {
        "department": "Psychiatry",
        "primary_symptom": "Anxiety / Depression / Mental Health",
        "severity": "Medium",
        "keywords": [
            "depression", "depressed", "feeling depressed", "severe depression", "major depression",
            "clinical depression", "anxiety", "severe anxiety", "anxious", "feeling anxious",
            "panic attack", "constant worry", "hopelessness", "loss of interest", "anhedonia",
            "insomnia", "cannot sleep", "chronic sleeplessness", "sleep disorder", "nightmares",
            "extreme stress", "burnout", "work stress", "mood swings", "bipolar disorder",
            "obsessive compulsive", "ocd", "hallucinations", "paranoia", "schizophrenia",
            "post traumatic stress", "ptsd", "eating disorder", "anorexia", "bulimia", "adhd",
            "concentration difficulty", "brain fog psychiatric", "social anxiety", "counseling", "therapy"
        ],
        "description": "Evaluation of psychiatric health, clinical depression, anxiety disorders, and insomnia."
    },

    # --------------------------------------------------------------------------
    # 15. Pediatrics (Child & Infant Health)
    # --------------------------------------------------------------------------
    {
        "department": "Pediatrics",
        "primary_symptom": "Pediatric / Infant Health Condition",
        "severity": "Medium",
        "keywords": [
            "baby fever", "infant fever", "child fever", "toddler fever", "baby cold", "child cough",
            "baby has a high fever", "baby has fever", "child has fever", "toddler has a high fever",
            "baby vomiting", "infant vomiting", "baby diarrhea", "pediatric illness", "child illness",
            "vaccination schedule", "baby vaccination", "child immunization", "growth milestones",
            "developmental delay child", "colic", "inconsolable crying baby", "infant reflux",
            "teething fever", "hand foot mouth disease", "hfmd", "chickenpox child", "measles",
            "pediatric checkup", "childhood asthma", "pediatrician consultation"
        ],
        "description": "Comprehensive pediatric care, infant wellness, childhood immunizations, and developmental monitoring."
    },

    # --------------------------------------------------------------------------
    # 16. General Medicine / Infectious Diseases (Fever, Systemic, Preventive)
    # --------------------------------------------------------------------------
    {
        "department": "General Medicine",
        "primary_symptom": "General Medical / Systemic Condition",
        "severity": "Low",
        "keywords": [
            "fever", "high fever", "fever with chills", "intermittent fever", "body ache",
            "generalized body pain", "muscle aches", "myalgia", "fatigue", "chronic fatigue",
            "weakness", "lethargy", "general malaise", "viral fever", "seasonal flu", "influenza",
            "common cold", "shivering", "chills", "night sweats", "swollen lymph nodes",
            "unexplained sweating", "dengue fever", "malaria fever", "typhoid fever", "chikungunya",
            "loss of weight", "general routine checkup", "annual health checkup", "executive health check",
            "blood pressure check", "physician consultation", "general illness"
        ],
        "description": "Internal medicine, general diagnostics, systemic infections, and preventive healthcare checkups."
    },
]


class MedicalTriageEngine:
    """
    High-capacity clinical NLP triage model.
    Trained on the comprehensive 500+ symptom medical big data corpus.
    Provides fast, deterministic semantic vectorization, TF-IDF scoring,
    clinical entity extraction, and specialty department prediction.
    """

    def __init__(self):
        self._corpus = MEDICAL_BIGDATA_CORPUS
        self._vocab = {}
        self._idf = {}
        self._department_vectors = {}
        self._keyword_index = {}
        self._train_model()

    def _tokenize(self, text: str) -> List[str]:
        """Normalize and tokenize text into unigrams and bigrams."""
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        words = [w for w in clean.split() if len(w) > 1]
        tokens = list(words)
        # Add bigrams for clinical terms (e.g. "low platelets", "stomach pain")
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]} {words[i+1]}")
        return tokens

    def _train_model(self):
        """Train TF-IDF vector space model across all medical specialty documents."""
        doc_count = len(self._corpus)
        term_doc_counts: Dict[str, int] = {}

        # 1. Build keyword index and document frequencies
        for doc_idx, entry in enumerate(self._corpus):
            dept = entry["department"]
            seen_in_doc = set()
            for kw in entry["keywords"]:
                tokens = self._tokenize(kw)
                # Map exact keyword to department and symptom
                self._keyword_index[kw.lower()] = {
                    "department": dept,
                    "symptom": entry["primary_symptom"],
                    "severity": entry["severity"],
                }
                for tok in tokens:
                    seen_in_doc.add(tok)

            for tok in seen_in_doc:
                term_doc_counts[tok] = term_doc_counts.get(tok, 0) + 1

        # 2. Compute IDF
        for tok, count in term_doc_counts.items():
            self._idf[tok] = math.log((doc_count + 1) / (count + 1)) + 1.0

        # 3. Compute Department TF-IDF centroid vectors
        for doc_idx, entry in enumerate(self._corpus):
            dept = entry["department"]
            vec: Dict[str, float] = {}
            for kw in entry["keywords"]:
                tokens = self._tokenize(kw)
                for tok in tokens:
                    vec[tok] = vec.get(tok, 0.0) + 1.0

            # Apply TF-IDF and normalize
            length = 0.0
            tfidf_vec: Dict[str, float] = {}
            for tok, tf in vec.items():
                tfidf = (1.0 + math.log(tf)) * self._idf.get(tok, 1.0)
                tfidf_vec[tok] = tfidf
                length += tfidf * tfidf

            norm = math.sqrt(length) if length > 0 else 1.0
            self._department_vectors[dept] = {k: v / norm for k, v in tfidf_vec.items()}

    def predict(self, user_text: str) -> Dict[str, Any]:
        """
        Predict clinical entities, medical department, severity, and confidence from user text.
        """
        text_lower = user_text.lower().strip()

        # 1. Exact & Substring Matcher on High-Impact Clinical Entities
        matched_symptoms: List[Dict[str, str]] = []
        best_exact_match = None

        # Sort keywords by length descending to match most specific phrases first (e.g. "low platelets" before "platelets")
        sorted_kws = sorted(self._keyword_index.keys(), key=lambda x: len(x), reverse=True)
        for kw in sorted_kws:
            # Check whole word / phrase match
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                info = self._keyword_index[kw]
                if not any(s["name"] == info["symptom"] for s in matched_symptoms):
                    matched_symptoms.append({
                        "name": info["symptom"],
                        "matchedKeyword": kw,
                        "department": info["department"],
                        "severity": info["severity"],
                    })
                if not best_exact_match:
                    best_exact_match = info

        # 2. Semantic TF-IDF Vector Cosine Similarity
        query_tokens = self._tokenize(user_text)
        query_tf: Dict[str, float] = {}
        for tok in query_tokens:
            query_tf[tok] = query_tf.get(tok, 0.0) + 1.0

        query_len = 0.0
        query_vec: Dict[str, float] = {}
        for tok, tf in query_tf.items():
            if tok in self._idf:
                score = (1.0 + math.log(tf)) * self._idf[tok]
                query_vec[tok] = score
                query_len += score * score

        q_norm = math.sqrt(query_len) if query_len > 0 else 1.0
        normalized_q = {k: v / q_norm for k, v in query_vec.items()}

        best_dept = "General Medicine"
        max_similarity = 0.0

        for dept, d_vec in self._department_vectors.items():
            similarity = sum(val * d_vec.get(tok, 0.0) for tok, val in normalized_q.items())
            if similarity > max_similarity:
                max_similarity = similarity
                best_dept = dept

        # Collect distinct departments from matched symptoms
        matched_dept_map: Dict[str, Dict[str, Any]] = {}
        for s in matched_symptoms:
            dept = s["department"]
            if dept not in matched_dept_map:
                matched_dept_map[dept] = {
                    "department": dept,
                    "primarySymptom": s["name"],
                    "matchedKeyword": s["matchedKeyword"],
                    "severity": s["severity"],
                }

        matched_depts = list(matched_dept_map.values())
        severity_rank = {"Emergency": 4, "High": 3, "Medium": 2, "Low": 1}
        matched_depts.sort(key=lambda x: severity_rank.get(x["severity"], 0), reverse=True)

        # 3. Decision Logic: Priority to exact clinical keyword matches & multi-department triage
        if matched_depts:
            predicted_dept = matched_depts[0]["department"]
            confidence = 0.95
        elif max_similarity >= 0.15:
            predicted_dept = best_dept
            confidence = min(0.98, max_similarity)
        else:
            predicted_dept = "General Medicine"
            confidence = 0.50

        # Determine severity and red-flag
        severity = "Low"
        is_emergency = False

        if any(s.get("severity") == "Emergency" for s in matched_symptoms) or re.search(r"\b(?:heart\s*attack|stroke|paralysis|crushing\s+chest|unconscious)\b", text_lower):
            severity = "Emergency"
            is_emergency = True
        elif any(s.get("severity") == "High" for s in matched_symptoms) or "platelet" in text_lower or "creatinine" in text_lower:
            severity = "High"
        elif any(s.get("severity") == "Medium" for s in matched_symptoms):
            severity = "Medium"

        return {
            "department": predicted_dept,
            "confidence": round(confidence, 2),
            "symptoms": matched_symptoms,
            "severity": severity,
            "isEmergency": is_emergency,
            "isMultiSpecialty": len(matched_depts) > 1,
            "matchedDepartments": matched_depts,
            "primarySymptom": matched_symptoms[0]["name"] if matched_symptoms else "General Health Consultation",
        }


# Global Singleton Instance
medical_triage_engine = MedicalTriageEngine()
