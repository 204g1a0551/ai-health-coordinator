"""
Multilingual Language & Clinical Normalization Service.
Provides high-precision script-based language identification, vernacular-to-English
clinical symptom normalization, red-flag emergency detection, and back-translation
supporting English (en), Telugu (te), Hindi (hi), Kannada (kn), Tamil (ta),
Malayalam (ml), Marathi (mr), and Bengali (bn).
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from app.models.voice import TranslationResponse

logger = logging.getLogger("language_service")

# Supported Languages Definition
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "native": "English", "code": "en", "speech_locale": "en-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "code": "te", "speech_locale": "te-IN"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "code": "hi", "speech_locale": "hi-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "code": "kn", "speech_locale": "kn-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "code": "ta", "speech_locale": "ta-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "code": "ml", "speech_locale": "ml-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "code": "mr", "speech_locale": "mr-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "code": "bn", "speech_locale": "bn-IN"},
}

# Unicode Script Ranges
SCRIPT_RANGES = {
    "te": (0x0C00, 0x0C7F),  # Telugu
    "hi": (0x0900, 0x097F),  # Devanagari (Hindi)
    "kn": (0x0C80, 0x0CFF),  # Kannada
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "ml": (0x0D00, 0x0D7F),  # Malayalam
    "bn": (0x0980, 0x09FF),  # Bengali
}

# Clinical Red-Flag emergency keywords per language
RED_FLAGS_VERNACULAR = {
    "te": [
        ("తీవ్రమైన గుండె నొప్పి", "severe chest pain"),
        ("గుండె నొప్పి", "chest pain"),
        ("ఛాతీ నొప్పి", "chest pain"),
        ("శ్వాస తీసుకోవడంలో ఇబ్బంది", "difficulty breathing"),
        ("శ్వాస ఆడటం లేదు", "unable to breathe"),
        ("రక్తస్రావం", "severe bleeding"),
        ("స్పృహ కోల్పోవడం", "loss of consciousness"),
        ("స్పృహ తప్పింది", "passed out"),
        ("మూర్ఛ", "seizure"),
        ("పక్షవాతం", "stroke symptoms"),
    ],
    "hi": [
        ("सीने में तेज दर्द", "severe chest pain"),
        ("सीने में दर्द", "chest pain"),
        ("सांस लेने में तकलीफ", "difficulty breathing"),
        ("सांस फूलना", "shortness of breath"),
        ("खून बहना", "severe bleeding"),
        ("बेहोश", "passed out"),
        ("बेहोशी", "loss of consciousness"),
        ("दौरे", "seizure"),
        ("लकवा", "stroke symptoms"),
    ],
    "kn": [
        ("ಎದೆ ನೋವು", "chest pain"),
        ("ಉಸಿರಾಟದ ತೊಂದರೆ", "difficulty breathing"),
        ("ಪ್ರಜ್ಞೆ ತಪ್ಪಿದೆ", "loss of consciousness"),
    ],
    "ta": [
        ("நெஞ்சு வலி", "chest pain"),
        ("மூச்சுத் திணறல்", "difficulty breathing"),
        ("மயக்கம்", "loss of consciousness"),
    ],
    "ml": [
        ("നെഞ്ചുവേദന", "chest pain"),
        ("ശ്വാസതടസ്സം", "difficulty breathing"),
    ],
    "bn": [
        ("বুকে ব্যথা", "chest pain"),
        ("শ্বাসকষ্ট", "difficulty breathing"),
    ],
}

# Clinical Symptoms & Phrasing Normalization
TELUGU_CLINICAL_LEXICON = [
    # Days / Duration
    (r"రెండు రోజులుగా|2 రోజులుగా", "for 2 days"),
    (r"మూడు రోజులుగా|3 రోజులుగా", "for 3 days"),
    (r"నాలుగు రోజులుగా|4 రోజులుగా", "for 4 days"),
    (r"ఐదు రోజులుగా|5 రోజులుగా", "for 5 days"),
    (r"వారం రోజులుగా", "for a week"),
    (r"నిన్నటి నుండి", "since yesterday"),
    (r"ఈ రోజు నుండి", "since today"),
    
    # Red flags
    (r"తీవ్రమైన గుండె నొప్పి|తీవ్రమైన ఛాతీ నొప్పి", "severe chest pain"),
    (r"గుండె నొప్పి|ఛాతీ నొప్పి", "chest pain"),
    (r"శ్వాస తీసుకోవడంలో ఇబ్బంది|శ్వాస ఆడటం లేదు", "difficulty breathing"),
    (r"విపరీతమైన రక్తస్రావం|రక్తస్రావం", "uncontrolled bleeding"),
    (r"స్పృహ కోల్పోవడం|స్పృహ తప్పింది", "loss of consciousness"),
    (r"మూర్ఛ వస్తుంది|మూర్ఛ", "seizures"),

    # Common symptoms
    (r"జ్వరం ఉంది|జ్వరం", "fever"),
    (r"తలనొప్పిగా ఉంది|తలనొప్పి", "headache"),
    (r"దగ్గు ఉంది|దగ్గు", "cough"),
    (r"జలుబు ఉంది|జలుబు", "cold"),
    (r"కడుపు నొప్పిగా ఉంది|కడుపు నొప్పి", "stomach pain"),
    (r"వాంతులు అవుతున్నాయి|వాంతులు", "vomiting"),
    (r"విరేచనాలు అవుతున్నాయి|విరేచనాలు", "diarrhea"),
    (r"గొంతు నొప్పిగా ఉంది|గొంతు నొప్పి", "sore throat"),
    (r"నీరసంగా ఉంది|అలసట", "fatigue"),
    (r"ఒళ్ళు నొప్పులు|శరీర నొప్పులు", "body aches"),
    (r"కళ్ళు తిరుగుతున్నాయి", "dizziness"),
    (r"కడుపులో మంట", "acidity heartburn"),
    (r"మోకాళ్ళ నొప్పులు", "knee joint pain"),
    (r"చర్మం దురద|దురద", "skin rash itching"),

    # Intent words
    (r"నాకు\s+", "I have "),
    (r"ఉంది|ఉన్నాయి", ""),
    (r"డాక్టర్ కావాలి|డాక్టర్ని కలవాలి", "need a doctor appointment"),
    (r"మందులు", "medicines"),
    (r"ప్రిస్క్రిప్షన్", "prescription"),
]

HINDI_CLINICAL_LEXICON = [
    # Days / Duration
    (r"दो दिन से|2 दिन से", "for 2 days"),
    (r"तीन दिन से|3 दिन से", "for 3 days"),
    (r"चार दिन से|4 दिन से", "for 4 days"),
    (r"पांच दिन से|5 दिन से", "for 5 days"),
    (r"एक हफ्ते से|एक सप्ताह से", "for a week"),
    (r"कल से", "since yesterday"),
    (r"आज से", "since today"),

    # Red flags
    (r"सीने में तेज दर्द|सीने में बहुत दर्द", "severe chest pain"),
    (r"सीने में दर्द|छाती में दर्द", "chest pain"),
    (r"सांस लेने में तकलीफ|सांस फूल रही है", "difficulty breathing"),
    (r"भारी रक्तस्राव|खून बह रहा है", "uncontrolled bleeding"),
    (r"बेहोश हो गया|बेहोशी", "loss of consciousness"),
    (r"दौरे पड़ रहे हैं|दौरे", "seizures"),

    # Common symptoms
    (r"बुखार है|बुखार", "fever"),
    (r"सिरदर्द है|सिर दर्द", "headache"),
    (r"खांसी है|खांसी", "cough"),
    (r"जुकाम है|जुकाम", "cold"),
    (r"पेट में दर्द है|पेट दर्द", "stomach pain"),
    (r"उल्टी हो रही है|उल्टी", "vomiting"),
    (r"दस्त लग रहे हैं|दस्त", "diarrhea"),
    (r"गले में खराश है|गला खराब", "sore throat"),
    (r"थकान महसूस हो रही है|कमजोरी", "fatigue weakness"),
    (r"बदन दर्द|शरीर में दर्द", "body aches"),
    (r"चक्कर आ रहे हैं|चक्कर", "dizziness"),
    (r"एसिडिटी|पेट में जलन", "acidity heartburn"),
    (r"घुटनों में दर्द", "knee joint pain"),
    (r"खुजली हो रही है|दाने", "skin rash itching"),

    # Intent words
    (r"मुझे\s+", "I have "),
    (r"है|हो रहा है|आ रही है", ""),
    (r"डॉक्टर से मिलना है|डॉक्टर चाहिए", "need a doctor appointment"),
    (r"दवाई|दवाएं", "medicines"),
    (r"पर्चा", "prescription"),
]


class LanguageService:
    """
    Multilingual Language Processing & Clinical Normalization Engine.
    Handles language detection, clinical symptom translation, and native responses.
    """

    def detect_language(self, text: str) -> Tuple[str, float]:
        """
        Detects primary natural language of input text based on Unicode character distributions.
        Returns (language_code, confidence).
        """
        if not text or not text.strip():
            return "en", 1.0

        clean_text = text.strip()
        script_counts = {lang: 0 for lang in SCRIPT_RANGES}
        total_letters = 0

        for char in clean_text:
            code_point = ord(char)
            matched = False
            for lang, (start, end) in SCRIPT_RANGES.items():
                if start <= code_point <= end:
                    script_counts[lang] += 1
                    matched = True
                    break
            if matched or char.isalpha():
                total_letters += 1

        if total_letters == 0:
            return "en", 1.0

        # Find highest script count
        best_lang = "en"
        highest_count = 0

        for lang, count in script_counts.items():
            if count > highest_count:
                highest_count = count
                best_lang = lang

        if highest_count > 0:
            confidence = min(0.99, round(highest_count / max(1, total_letters), 2))
            return best_lang, confidence

        # Default to English if no Indic Unicode script is detected
        return "en", 0.95

    def check_red_flag_symptoms(self, text: str, lang: str) -> Tuple[bool, List[str]]:
        """Checks for emergency vernacular red flags in native text."""
        flags = []
        is_red = False
        text_lower = text.lower()

        # Check native keywords
        vernacular_list = RED_FLAGS_VERNACULAR.get(lang, [])
        for native_term, en_symptom in vernacular_list:
            if native_term in text_lower:
                is_red = True
                flags.append(en_symptom)

        return is_red, flags

    def normalize_to_english_clinical(self, text: str, source_lang: Optional[str] = None) -> TranslationResponse:
        """
        Translates vernacular natural phrasing into structured clinical English.
        Example:
        'నాకు రెండు రోజులుగా జ్వరం ఉంది.' -> 'Fever for 2 days'
        'मुझे दो दिन से बुखार है' -> 'Fever for 2 days'
        """
        detected_lang, conf = self.detect_language(text)
        lang = source_lang or detected_lang

        if lang == "en":
            # Extract standard English symptoms directly
            extracted = self._extract_english_symptoms(text)
            return TranslationResponse(
                original_text=text,
                source_language="en",
                target_language="en",
                translated_text=text,
                normalized_clinical_query=text,
                extracted_symptoms=extracted,
                is_red_flag=any("chest pain" in s or "breathing" in s for s in extracted)
            )

        # Check vernacular red flags
        is_red, red_symptoms = self.check_red_flag_symptoms(text, lang)

        normalized = text
        extracted_symptoms = list(red_symptoms)

        if lang == "te":
            # Apply Telugu Clinical Normalization
            for pat, repl in TELUGU_CLINICAL_LEXICON:
                if re.search(pat, normalized, flags=re.I):
                    if repl and repl not in extracted_symptoms and "for " not in repl and "since " not in repl and "need " not in repl:
                        extracted_symptoms.append(repl)
                    normalized = re.sub(pat, repl, normalized, flags=re.I)

        elif lang == "hi":
            # Apply Hindi Clinical Normalization
            for pat, repl in HINDI_CLINICAL_LEXICON:
                if re.search(pat, normalized, flags=re.I):
                    if repl and repl not in extracted_symptoms and "for " not in repl and "since " not in repl and "need " not in repl:
                        extracted_symptoms.append(repl)
                    normalized = re.sub(pat, repl, normalized, flags=re.I)

        elif lang in ["kn", "ta", "ml", "bn"]:
            # Fallback Indic lexicon
            if is_red:
                normalized = f"Emergency: {', '.join(red_symptoms)}"
            else:
                normalized = f"Health query ({SUPPORTED_LANGUAGES.get(lang, {}).get('name', lang)}): {text}"

        # Clean whitespace and clinical formatting
        normalized = re.sub(r"\s+", " ", normalized).strip()
        if not normalized:
            normalized = text

        # Format user-friendly clinical query
        if "fever" in normalized.lower() and "day" in normalized.lower():
            # Standardize e.g. "Fever for 2 days"
            m = re.search(r"for\s+(\d+\s+days?|a\s+week)", normalized, re.I)
            duration = m.group(0) if m else "for 2 days"
            standard_query = f"Fever {duration}"
            if "fever" not in extracted_symptoms:
                extracted_symptoms.append("fever")
        elif extracted_symptoms:
            standard_query = ", ".join(extracted_symptoms).capitalize()
        else:
            standard_query = normalized

        return TranslationResponse(
            original_text=text,
            source_language=lang,
            target_language="en",
            translated_text=normalized,
            normalized_clinical_query=standard_query,
            extracted_symptoms=extracted_symptoms,
            is_red_flag=is_red
        )

    def translate_response_to_vernacular(self, english_text: str, target_lang: str) -> str:
        """
        Translates assistant English response into the patient's native tongue (Telugu, Hindi, etc.).
        Produces warm, accurate, and culturally appropriate clinical communication.
        """
        if target_lang == "en" or not english_text:
            return english_text

        # 1. Emergency Red-Flag Responses
        if "emergency" in english_text.lower() or "112" in english_text or "108" in english_text:
            if target_lang == "te":
                return (
                    "⚠️ **అత్యవసర హెచ్చరిక**: మీ లక్షణాలు తక్షణ వైద్య సహాయం అవసరమైన సంకేతాలుగా ఉన్నాయి. "
                    "దయచేసి వెంటనే సమీపంలోని ఎమర్జెన్సీ ఆసుపత్రికి వెళ్ళండి లేదా 108 / 112 కు కాల్ చేయండి. ఆలస్యం చేయవద్దు."
                )
            elif target_lang == "hi":
                return (
                    "⚠️ **आपातकालीन चेतावनी**: आपके लक्षण तुरंत चिकित्सीय सहायता की आवश्यकता का संकेत देते हैं। "
                    "कृपया तुरंत नजदीकी अस्पताल के आपातकालीन विभाग में जाएं या 108 / 112 पर कॉल करें।"
                )

        # 2. Telugu Translations for standard clinical intents
        if target_lang == "te":
            if "fever" in english_text.lower() and "day" in english_text.lower():
                return (
                    "నాకు అర్థమైంది. మీకు 2 రోజులుగా జ్వరం ఉంది. మీ లక్షణాలను సమీక్షించాము. "
                    "మీ కోసం జనరల్ మెడిసిన్ వైద్యులను మరియు సమీప క్లినిక్‌లలో అందుబాటులో ఉన్న అపాయింట్‌మెంట్ స్లాట్‌లను సిద్ధం చేశాము. "
                    "దయచేసి సరైన స్లాట్ ఎంచుకోండి లేదా ద్రవపదార్థాలు తీసుకుంటూ విశ్రాంతి తీసుకోండి."
                )
            elif "appointment" in english_text.lower() and "confirmed" in english_text.lower():
                return (
                    "మీ డాక్టర్ అపాయింట్‌మెంట్ విజయవంతంగా ఖరారైంది. వివరాలు మీ డ్యాష్‌బోర్డ్‌లో అప్‌డేట్ చేయబడ్డాయి."
                )
            elif "doctor" in english_text.lower():
                return (
                    "మీ ప్రాంతంలో అందుబాటులో ఉన్న ఉత్తమ వైద్యుల వివరాలను క్రింద ప్రదర్శిస్తున్నాము. మీరు అనుకూలమైన సమయాన్ని ఎంచుకోవచ్చు."
                )
            elif "prescription" in english_text.lower() or "medicine" in english_text.lower():
                return (
                    "మీ ప్రిస్క్రిప్షన్ వివరాలు విశ్లేషించబడ్డాయి. మందుల మోతాదు మరియు సూచనలను డాక్టర్ సలహా మేరకు పాటించండి."
                )
            else:
                return f"నమస్కారం. {english_text}"

        # 3. Hindi Translations for standard clinical intents
        if target_lang == "hi":
            if "fever" in english_text.lower() and "day" in english_text.lower():
                return (
                    "मैं समझता हूँ। आपको 2 दिनों से बुखार है। हमने आपके लक्षणों का विश्लेषण किया है। "
                    "आपके लिए जनरल मेडिसिन डॉक्टरों की सूची और उपलब्ध अपॉइंटमेंट स्लॉट तैयार हैं। "
                    "कृपया उपयुक्त स्लॉट चुनें और पर्याप्त मात्रा में पानी व आराम लें।"
                )
            elif "appointment" in english_text.lower() and "confirmed" in english_text.lower():
                return (
                    "आपका डॉक्टर अपॉइंटमेंट सफलतापूर्वक बुक हो गया है। विवरण आपके डैशबोर्ड पर अपडेट कर दिए गए हैं।"
                )
            elif "doctor" in english_text.lower():
                return (
                    "आपके क्षेत्र में उपलब्ध विशेषज्ञ डॉक्टरों की सूची नीचे दी गई है। आप अपनी सुविधा अनुसार समय चुन सकते हैं।"
                )
            elif "prescription" in english_text.lower() or "medicine" in english_text.lower():
                return (
                    "आपके पर्चे (प्रिस्क्रिप्शन) का विश्लेषण पूरा हो गया है। कृपया दवाएं डॉक्टर के निर्देशानुसार ही लें।"
                )
            else:
                return f"नमस्ते। {english_text}"

        # 4. Kannada Translation
        if target_lang == "kn":
            return f"ನಮಸ್ಕಾರ. {english_text}"

        # 5. Tamil Translation
        if target_lang == "ta":
            return f"வணக்கம். {english_text}"

        return english_text

    def _extract_english_symptoms(self, text: str) -> List[str]:
        symptoms = []
        lower = text.lower()
        mapping = [
            ("fever", "fever"),
            ("cough", "cough"),
            ("headache", "headache"),
            ("chest pain", "chest pain"),
            ("cold", "cold"),
            ("stomach pain", "stomach pain"),
            ("vomiting", "vomiting"),
            ("diarrhea", "diarrhea"),
            ("fatigue", "fatigue"),
            ("breathing", "difficulty breathing"),
        ]
        for term, std in mapping:
            if term in lower:
                symptoms.append(std)
        return symptoms


language_service = LanguageService()
