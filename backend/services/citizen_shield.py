"""
SafeNet AI – CitizenShield Service
-------------------------------------
Multilingual fraud risk assessment for citizens via WhatsApp/IVR.
Uses LLM (OpenAI GPT-4o-mini) with RAG over scam knowledge base.
Falls back to rule-based detection when LLM is unavailable.
"""
from __future__ import annotations

import json
import re
import time
from typing import Dict, List, Optional, Tuple

from backend.core.config import get_settings
from backend.models.scam.classifier import ScamPatternMatcher

settings = get_settings()

# ── Language Support ──────────────────────────────────────────────

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "pa": "Punjabi",
    "or": "Odia",
    "as": "Assamese",
}

# Localised responses for key verdicts
VERDICT_MESSAGES = {
    "scam": {
        "en": "⚠️ HIGH RISK: This appears to be a SCAM. Do NOT share any money, OTP, or personal details. Call 1930 immediately.",
        "hi": "⚠️ उच्च जोखिम: यह एक धोखाधड़ी प्रतीत होती है। कोई पैसा, OTP, या व्यक्तिगत जानकारी साझा न करें। तुरंत 1930 पर कॉल करें।",
        "ta": "⚠️ அதிக ஆபத்து: இது ஒரு மோசடி. பணம், OTP அல்லது தனிப்பட்ட தகவல்களை பகிர வேண்டாம். உடனே 1930 அழைக்கவும்.",
        "te": "⚠️ అధిక ప్రమాదం: ఇది మోసం. డబ్బు, OTP లేదా వ్యక్తిగత వివరాలు పంచుకోకండి. వెంటనే 1930 కి కాల్ చేయండి.",
        "kn": "⚠️ ಹೆಚ್ಚಿನ ಅಪಾಯ: ಇದು ಮೋಸ. ಹಣ, OTP ಅಥವಾ ವ್ಯಕ್ತಿಗತ ವಿವರಗಳನ್ನು ಹಂಚಿಕೊಳ್ಳಬೇಡಿ. ತಕ್ಷಣ 1930 ಗೆ ಕರೆ ಮಾಡಿ.",
        "ml": "⚠️ ഉയർന്ന അപകടം: ഇത് ഒരു തട്ടിപ്പ്. പണം, OTP അല്ലെങ്കിൽ വ്യക്തിഗത വിവരങ്ങൾ പങ്കിടരുത്. ഉടൻ 1930 ൽ വിളിക്കുക.",
        "mr": "⚠️ उच्च धोका: हे एक घोटाळे आहे. पैसे, OTP किंवा वैयक्तिक माहिती सामायिक करू नका. ताबडतोब 1930 वर कॉल करा.",
    },
    "safe": {
        "en": "✅ This appears safe. Standard precautions apply: never share OTP or passwords with anyone.",
        "hi": "✅ यह सुरक्षित प्रतीत होता है। मानक सावधानियाँ लागू होती हैं: कभी भी OTP या पासवर्ड साझा न करें।",
        "ta": "✅ இது பாதுகாப்பானது. எப்போதும் OTP அல்லது கடவுச்சொல் யாரிடமும் பகிர வேண்டாம்.",
        "te": "✅ ఇది సురక్షితంగా కనిపిస్తుంది. OTP లేదా పాస్‌వర్డ్‌లు ఎవరితోనూ పంచుకోకండి.",
    },
    "suspicious": {
        "en": "⚡ SUSPICIOUS: Proceed with caution. Verify the caller's identity independently before sharing anything.",
        "hi": "⚡ संदिग्ध: सावधानी से आगे बढ़ें। कुछ भी साझा करने से पहले कॉलर की पहचान स्वतंत्र रूप से सत्यापित करें।",
        "ta": "⚡ சந்தேகம்: எச்சரிக்கையாக இருங்கள். எதையும் பகிர்வதற்கு முன் அழைப்பாளரின் அடையாளத்தை சரிபார்க்கவும்.",
    },
}

# ── System Prompt for CitizenShield LLM ───────────────────────────

CITIZEN_SHIELD_SYSTEM = """You are CitizenShield, an AI fraud detection assistant for Indian citizens.
Your job is to assess whether a situation described by the user is a scam, suspicious, or safe.

CRITICAL RULES:
1. ALWAYS output a JSON object with these exact keys:
   - risk_level: one of "scam" | "high_risk" | "suspicious" | "safe"
   - confidence: float 0.0-1.0
   - explanation: clear explanation in the user's language (max 100 words)
   - recommended_actions: list of 2-4 specific action strings
   - scam_type: most likely scam type or null

2. Never ask the user to share personal details, OTP, bank details, or Aadhaar.
3. Always recommend calling 1930 (MHA cybercrime helpline) for high-risk situations.
4. Be direct and clear. Avoid technical jargon.
5. Respond in the same language as the user's message.
6. Common Indian scam patterns to detect:
   - Digital arrest: CBI/ED/Police threatening arrest via video call
   - KYC fraud: Bank/Telecom asking to update KYC via OTP
   - Lottery/Prize: Unsolicited prize announcement
   - Loan fraud: Advance fee / processing fee for a loan
   - Investment: Guaranteed high returns
   - Romance: Online relationship leading to money request
   - Job: Fake job offer asking for registration fee

OUTPUT ONLY the JSON object. No markdown, no preamble."""


class ScamKnowledgeBase:
    """
    Simple in-memory knowledge base with scam FAQ.
    In production, replace with Qdrant RAG.
    """

    FAQS = [
        {
            "keywords": ["cbi", "ed", "arrest", "warrant", "court"],
            "answer": "CBI, ED, and Police NEVER arrest people via phone or video calls. This is a 'Digital Arrest' scam. Hang up immediately.",
            "risk": "scam",
        },
        {
            "keywords": ["otp", "one time password", "kyc", "aadhaar link"],
            "answer": "Banks and telecom companies NEVER ask for OTP over phone. This is a KYC fraud. Do not share.",
            "risk": "scam",
        },
        {
            "keywords": ["won", "prize", "lottery", "congratulations", "selected"],
            "answer": "Unsolicited prize wins are almost always scams. You cannot win a lottery you did not enter.",
            "risk": "scam",
        },
        {
            "keywords": ["processing fee", "advance", "loan", "approved"],
            "answer": "Legitimate lenders never charge processing fees upfront before disbursing a loan.",
            "risk": "scam",
        },
        {
            "keywords": ["double", "triple", "guaranteed return", "crypto profit"],
            "answer": "No investment guarantees returns. This is an investment scam. Contact SEBI at 1800-266-7575.",
            "risk": "scam",
        },
    ]

    def lookup(self, text: str) -> Optional[Dict]:
        text_lower = text.lower()
        for faq in self.FAQS:
            if any(kw in text_lower for kw in faq["keywords"]):
                return faq
        return None


class LanguageDetector:
    """Simple language detection fallback."""

    HINDI_CHARS = re.compile(r"[\u0900-\u097F]")
    TAMIL_CHARS = re.compile(r"[\u0B80-\u0BFF]")
    TELUGU_CHARS = re.compile(r"[\u0C00-\u0C7F]")
    KANNADA_CHARS = re.compile(r"[\u0C80-\u0CFF]")
    MALAYALAM_CHARS = re.compile(r"[\u0D00-\u0D7F]")
    BENGALI_CHARS = re.compile(r"[\u0980-\u09FF]")
    GUJARATI_CHARS = re.compile(r"[\u0A80-\u0AFF]")

    def detect(self, text: str) -> str:
        if self.HINDI_CHARS.search(text):
            return "hi"
        if self.TAMIL_CHARS.search(text):
            return "ta"
        if self.TELUGU_CHARS.search(text):
            return "te"
        if self.KANNADA_CHARS.search(text):
            return "kn"
        if self.MALAYALAM_CHARS.search(text):
            return "ml"
        if self.BENGALI_CHARS.search(text):
            return "bn"
        if self.GUJARATI_CHARS.search(text):
            return "gu"
        return "en"


class CitizenShieldService:
    """
    Main CitizenShield service.
    Provides fraud risk assessment for citizen-facing channels.
    """

    def __init__(self):
        self._pattern_matcher = ScamPatternMatcher()
        self._knowledge_base = ScamKnowledgeBase()
        self._lang_detector = LanguageDetector()
        self._openai_client = None

    def _init_openai(self):
        if self._openai_client is None and settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            except ImportError:
                pass

    def _rule_based_assess(self, message: str, language: str) -> Dict:
        """Fast rule-based assessment when LLM unavailable."""
        descriptions, weights, scam_type = self._pattern_matcher.match(message)
        faq_hit = self._knowledge_base.lookup(message)

        if faq_hit:
            risk = faq_hit["risk"]
            explanation = faq_hit["answer"]
            confidence = 0.90
        elif weights:
            avg_weight = sum(weights) / len(weights)
            if avg_weight >= 0.75:
                risk = "scam"
                confidence = min(avg_weight + 0.1, 0.95)
            elif avg_weight >= 0.50:
                risk = "suspicious"
                confidence = avg_weight
            else:
                risk = "suspicious"
                confidence = 0.45
            explanation = f"Detected patterns: {'; '.join(descriptions[:2])}"
        else:
            risk = "safe"
            confidence = 0.70
            explanation = "No known scam patterns detected. Exercise standard caution."

        risk_level = risk if risk != "scam" else "scam"

        # Localised verdict message
        verdict_msgs = VERDICT_MESSAGES.get(risk, VERDICT_MESSAGES["safe"])
        localised = verdict_msgs.get(language, verdict_msgs.get("en", ""))

        return {
            "risk_level": risk_level,
            "confidence": confidence,
            "explanation": localised or explanation,
            "recommended_actions": self._get_actions(risk_level, scam_type),
            "scam_type": scam_type if scam_type != "unknown" else None,
        }

    def _get_actions(self, risk_level: str, scam_type: str) -> List[str]:
        base_actions = {
            "scam": [
                "Do NOT transfer any money",
                "Do NOT share OTP, Aadhaar, or bank details",
                "Hang up / end the conversation immediately",
                "Call cybercrime helpline: 1930",
                "File complaint at cybercrime.gov.in",
            ],
            "high_risk": [
                "Verify caller identity independently",
                "Do NOT make any payments",
                "Call the official helpline of the organisation directly",
                "Report suspicion at cybercrime.gov.in",
            ],
            "suspicious": [
                "Verify the request through official channels",
                "Do not act under time pressure",
                "Consult a trusted family member before proceeding",
            ],
            "safe": [
                "Never share OTP with anyone",
                "Keep your bank details private",
            ],
        }
        return base_actions.get(risk_level, base_actions["safe"])

    async def assess(
        self,
        message: str,
        language: Optional[str] = None,
        phone_number: Optional[str] = None,
        context_type: str = "call",
    ) -> Dict:
        """
        Main assessment entry point.

        Args:
            message: Citizen's description of the suspicious call/message
            language: ISO 639-1 code or None (auto-detect)
            phone_number: Optional citizen phone for record-keeping
            context_type: call | sms | payment | job_offer | other

        Returns:
            Dict matching CitizenAssessResponse schema
        """
        t_start = time.perf_counter()

        # Auto-detect language if not specified
        if not language or language not in SUPPORTED_LANGUAGES:
            language = self._lang_detector.detect(message)

        # Try LLM path
        result = None
        if settings.openai_api_key:
            result = await self._llm_assess(message, language, context_type)

        # Fallback to rule-based
        if result is None:
            result = self._rule_based_assess(message, language)

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        return {
            "risk_level": result["risk_level"],
            "confidence": result["confidence"],
            "explanation": result["explanation"],
            "recommended_actions": result.get("recommended_actions", []),
            "report_url": "https://cybercrime.gov.in" if result["risk_level"] in ("scam", "high_risk") else None,
            "helpline_number": "1930",
            "response_language": language,
            "processing_time_ms": elapsed_ms,
        }

    async def _llm_assess(
        self, message: str, language: str, context_type: str
    ) -> Optional[Dict]:
        """Call OpenAI GPT-4o-mini for assessment."""
        self._init_openai()
        if not self._openai_client:
            return None

        try:
            user_prompt = f"Context type: {context_type}\nUser message: {message}"
            response = await self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CITIZEN_SHIELD_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            return {
                "risk_level": parsed.get("risk_level", "suspicious"),
                "confidence": float(parsed.get("confidence", 0.7)),
                "explanation": parsed.get("explanation", ""),
                "recommended_actions": parsed.get("recommended_actions", []),
                "scam_type": parsed.get("scam_type"),
            }
        except Exception as e:
            print(f"[CitizenShield] LLM error: {e}")
            return None


# ── Module-level singleton ────────────────────────────────────────
_service: Optional[CitizenShieldService] = None


def get_citizen_shield() -> CitizenShieldService:
    global _service
    if _service is None:
        _service = CitizenShieldService()
    return _service
