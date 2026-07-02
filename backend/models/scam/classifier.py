"""
SafeNet AI – Scam Call Classifier
--------------------------------------
Multi-signal classifier combining:
  1. Call metadata features (rule-based + statistical)
  2. Transcript NLP (DistilBERT fine-tuned on scam corpus)
  3. Audio feature patterns (if Whisper transcript available)

Outputs: ScamType + confidence score + matched patterns
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Lazy imports – heavy libs only loaded when model actually used
_torch = None
_transformers = None


def _lazy_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


def _lazy_transformers():
    global _transformers
    if _transformers is None:
        import transformers
        _transformers = transformers
    return _transformers


# ── Scam Script Pattern Library ───────────────────────────────────
# Each pattern carries: regex, scam_type, weight (0-1), description

SCAM_PATTERNS: List[Dict] = [
    # Digital Arrest
    {
        "pattern": r"\b(cbi|ed|customs|cybercrime|police|court)\b",
        "scam_type": "digital_arrest",
        "weight": 0.55,
        "description": "Government authority impersonation",
    },
    {
        "pattern": r"\b(cbi|ed|customs|cybercrime|police|court)\b.{0,60}\b(arrest|arrested|warrant|case|detained|notice|summon)\b",
        "scam_type": "digital_arrest",
        "weight": 0.85,
        "description": "Authority impersonation with legal threat",
    },
    {
        "pattern": r"\b(arrest|arrested|warrant|detained)\b.{0,40}\b(cbi|police|court|ed|customs)\b",
        "scam_type": "digital_arrest",
        "weight": 0.85,
        "description": "Legal threat with authority mention",
    },
    {
        "pattern": r"\b(under arrest|you are arrested|being arrested|face arrest)\b",
        "scam_type": "digital_arrest",
        "weight": 0.90,
        "description": "Direct arrest threat",
    },
    {
        "pattern": r"\b(do not.{0,10}(tell|inform|contact)|keep.{0,10}secret|disconnect.{0,10}call|do not disconnect)\b",
        "scam_type": "digital_arrest",
        "weight": 0.90,
        "description": "Secrecy / isolation instruction",
    },
    {
        "pattern": r"\b(stay on.{0,10}call|do not.{0,10}hang up|remain on.{0,10}line)\b",
        "scam_type": "digital_arrest",
        "weight": 0.85,
        "description": "Stay on call instruction",
    },
    {
        "pattern": r"\b(video.{0,10}call|screen.{0,10}share|whatsapp.{0,10}video)\b.{0,50}\b(verify|identity|document)\b",
        "scam_type": "digital_arrest",
        "weight": 0.75,
        "description": "Video call identity verification pressure",
    },
    {
        "pattern": r"\b(money.{0,10}launder|terror.{0,10}financ|hawala|drug.{0,10}money)\b",
        "scam_type": "digital_arrest",
        "weight": 0.80,
        "description": "Serious crime accusation",
    },
    # KYC Fraud
    {
        "pattern": r"\b(kyc|know.your.customer)\b",
        "scam_type": "kyc_update",
        "weight": 0.50,
        "description": "KYC mention",
    },
    {
        "pattern": r"\b(kyc|know.your.customer)\b.{0,30}\b(expir|update|verify|block|suspend|complet)\b",
        "scam_type": "kyc_update",
        "weight": 0.82,
        "description": "Fake KYC update urgency",
    },
    {
        "pattern": r"\b(otp|one.time.password|one-time.password)\b",
        "scam_type": "kyc_update",
        "weight": 0.88,
        "description": "OTP solicitation (never legitimate)",
    },
    {
        "pattern": r"\b(share.{0,10}otp|send.{0,10}otp|give.{0,10}otp|tell.{0,10}otp|enter.{0,10}otp)\b",
        "scam_type": "kyc_update",
        "weight": 0.95,
        "description": "Explicit OTP request",
    },
    {
        "pattern": r"\b(aadhaar.{0,20}(link|update|block|verify)|pan.{0,10}(link|update|expir|block))\b",
        "scam_type": "kyc_update",
        "weight": 0.80,
        "description": "Aadhaar/PAN update pressure",
    },
    # Loan Fraud
    {
        "pattern": r"\b(pre.?approved.{0,20}loan|instant.{0,10}loan|processing.{0,10}fee|advance.{0,10}payment)\b",
        "scam_type": "loan_fraud",
        "weight": 0.78,
        "description": "Advance fee loan scam",
    },
    # Investment Fraud
    {
        "pattern": "(guarantee[sd]? .{0,20}(return|profit|earning|income))",
        "scam_type": "investment",
        "weight": 0.82,
        "description": "Guaranteed returns promise",
    },
    {
        "pattern": "(double|triple).{0,15}(money|investment|amount|income)",
        "scam_type": "investment",
        "weight": 0.80,
        "description": "Money doubling scheme",
    },
    {
        "pattern": "risk.{0,8}free.{0,20}(invest|return|profit|earn)",
        "scam_type": "investment",
        "weight": 0.80,
        "description": "Risk-free investment claim",
    },
    {
        "pattern": "(crypto|bitcoin|forex).{0,20}(profit|return|earn|invest|guaranteed)",
        "scam_type": "investment",
        "weight": 0.75,
        "description": "Crypto investment fraud",
    },
    {
        "pattern": "[0-9]{2,3}%.{0,20}(monthly|weekly|daily|annual).{0,10}return",
        "scam_type": "investment",
        "weight": 0.85,
        "description": "Unrealistic percentage return promise",
    },
    # Lottery
    {
        "pattern": r"\b(won.{0,20}(prize|lottery|lucky draw|crore|lakh)|claim.{0,20}reward)\b",
        "scam_type": "lottery",
        "weight": 0.85,
        "description": "Unsolicited prize / lottery win",
    },
    # Generic pressure tactics
    {
        "pattern": r"\b(immediately|urgent|expire.{0,10}today|last.{0,5}chance|act.{0,10}now|within.{0,10}hour)\b",
        "scam_type": "unknown",
        "weight": 0.45,
        "description": "High-pressure urgency language",
    },
]

# ── Number Spoofing Signatures ────────────────────────────────────
SPOOFED_PREFIXES = {
    "+91000", "+91999999", "00911800",  # known spoofed patterns
}

GOVT_NUMBER_PATTERNS = [
    r"^1800\d{6,8}$",   # Toll-free (often spoofed)
    r"^14[0-9]{3}$",    # Govt short codes (often spoofed)
]


@dataclass
class ScamFeatures:
    """Extracted feature vector before model inference."""
    # Metadata features
    is_spoofed: float = 0.0
    looks_govt_number: float = 0.0
    call_duration_normalized: float = 0.0
    silence_ratio: float = 0.0
    speech_rate_normalized: float = 0.0
    # Text features
    patterns_matched: List[str] = field(default_factory=list)
    pattern_weights: List[float] = field(default_factory=list)
    dominant_scam_type: str = "unknown"
    keyword_density: float = 0.0
    # Derived
    metadata_risk_score: float = 0.0


class ScamPatternMatcher:
    """Fast regex-based pattern matcher. Zero ML dependencies."""

    def __init__(self):
        self._compiled = [
            {
                **p,
                "_re": re.compile(p["pattern"], re.IGNORECASE | re.DOTALL),
            }
            for p in SCAM_PATTERNS
        ]

    def match(self, text: str) -> Tuple[List[str], List[float], str]:
        """
        Returns (matched_descriptions, weights, dominant_type).
        """
        if not text:
            return [], [], "unknown"

        descriptions, weights, types = [], [], []
        for pat in self._compiled:
            if pat["_re"].search(text):
                descriptions.append(pat["description"])
                weights.append(pat["weight"])
                types.append(pat["scam_type"])

        dominant = "unknown"
        if types:
            # Most frequent non-unknown type wins
            type_counts: Dict[str, float] = {}
            for t, w in zip(types, weights):
                if t != "unknown":
                    type_counts[t] = type_counts.get(t, 0) + w
            if type_counts:
                dominant = max(type_counts, key=type_counts.get)

        return descriptions, weights, dominant


class MetadataRiskScorer:
    """
    Rule-based risk scorer on call metadata.
    Returns a 0-1 risk score without any ML.
    """

    def score(self, metadata: Dict) -> Tuple[float, ScamFeatures]:
        feats = ScamFeatures()

        # Spoofing check
        caller = metadata.get("caller_number", "")
        for prefix in SPOOFED_PREFIXES:
            if caller.startswith(prefix):
                feats.is_spoofed = 1.0
                break
        if not feats.is_spoofed:
            for pat in GOVT_NUMBER_PATTERNS:
                if re.match(pat, caller.lstrip("+")):
                    feats.looks_govt_number = 0.6
                    break

        # Explicit spoofing flag from telecom
        if metadata.get("number_spoofing_detected"):
            feats.is_spoofed = 1.0

        # Call duration: very short or very long calls are suspicious
        duration = metadata.get("call_duration_seconds", 0) or 0
        if duration > 0:
            # Scam calls cluster at 60-600s
            if 60 <= duration <= 600:
                feats.call_duration_normalized = 0.7
            elif duration < 20:
                feats.call_duration_normalized = 0.5  # hang-up after answer
            else:
                feats.call_duration_normalized = 0.3

        # Silence ratio: digital arrest scams have long silent "processing" gaps
        silence = metadata.get("silence_ratio", 0) or 0
        if silence > 0.4:
            feats.silence_ratio = min(silence, 1.0)

        # Speech rate: scripted reads are faster than normal conversation
        wpm = metadata.get("speech_rate_wpm", 0) or 0
        if wpm > 180:
            feats.speech_rate_normalized = min((wpm - 180) / 120, 1.0)

        # Composite metadata risk
        feats.metadata_risk_score = (
            feats.is_spoofed * 0.40
            + feats.looks_govt_number * 0.15
            + feats.call_duration_normalized * 0.20
            + feats.silence_ratio * 0.15
            + feats.speech_rate_normalized * 0.10
        )

        return feats.metadata_risk_score, feats


class NLPScamClassifier:
    """
    DistilBERT-based NLP classifier fine-tuned on scam transcripts.
    Falls back to pattern-matching when model is not loaded.
    """

    # Label mapping from training
    LABEL2SCAM = {
        0: "unknown",
        1: "digital_arrest",
        2: "loan_fraud",
        3: "lottery",
        4: "kyc_update",
        5: "impersonation",
        6: "investment",
        7: "romance",
        8: "tech_support",
    }

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._tokenizer = None
        self._model_path = model_path
        self._pattern_matcher = ScamPatternMatcher()

    def load(self):
        """Lazy-load model to avoid startup overhead."""
        if self._model is not None:
            return
        path = Path(self._model_path) if self._model_path else None
        if path and path.exists():
            try:
                tf = _lazy_transformers()
                self._tokenizer = tf.AutoTokenizer.from_pretrained(str(path))
                self._model = tf.AutoModelForSequenceClassification.from_pretrained(str(path))
                self._model.eval()
                print(f"[ScamClassifier] Loaded fine-tuned model from {path}")
            except Exception as e:
                print(f"[ScamClassifier] Model load failed ({e}), using pattern fallback")
        else:
            print("[ScamClassifier] No model path / file, using pattern-only mode")

    def _nlp_predict(self, text: str) -> Tuple[str, float]:
        """Run transformer inference. Returns (label, confidence)."""
        torch = _lazy_torch()
        inputs = self._tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=True,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1).squeeze()
            confidence, label_idx = torch.max(probs, dim=-1)
        label = self.LABEL2SCAM.get(label_idx.item(), "unknown")
        return label, confidence.item()

    def predict(self, transcript: str, metadata: Dict) -> Tuple[str, float]:
        """
        Returns (scam_type, nlp_confidence).
        Uses transformer if available, else pattern matching.
        """
        if not transcript:
            return "unknown", 0.0

        # Pattern matching always runs (fast, interpretable)
        descriptions, weights, dominant = self._pattern_matcher.match(transcript)

        if self._model is not None:
            try:
                label, conf = self._nlp_predict(transcript)
                # Blend: 70% NLP model, 30% pattern score
                pattern_score = min(sum(weights) / max(len(weights), 1), 1.0) if weights else 0.0
                blended_conf = 0.70 * conf + 0.30 * pattern_score
                # If NLP says unknown but patterns are strong, use pattern dominant
                if label == "unknown" and dominant != "unknown" and pattern_score > 0.6:
                    label = dominant
                return label, blended_conf
            except Exception as e:
                print(f"[NLPClassifier] Inference error: {e}")

        # Fallback: pattern-only score
        if not weights:
            return "unknown", 0.05
        score = min(sum(weights) / len(weights) + 0.1 * len(weights), 1.0)
        return dominant, score


class ScamCallClassifier:
    """
    Main entry point: fuses metadata risk + NLP to produce final verdict.
    Fully self-contained, no external dependencies at import time.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._metadata_scorer = MetadataRiskScorer()
        self._nlp_classifier = NLPScamClassifier(model_path)
        self._pattern_matcher = ScamPatternMatcher()
        self._loaded = False

    def load(self):
        if not self._loaded:
            self._nlp_classifier.load()
            self._loaded = True

    def _compute_final_score(
        self,
        metadata_score: float,
        nlp_score: float,
        pattern_weights: List[float],
    ) -> float:
        """
        Weighted ensemble. Metadata alone can't flag a scam above 0.6.
        NLP + patterns together can reach 1.0.
        """
        pattern_bonus = min(0.15 * len(pattern_weights), 0.30)
        raw = (
            0.35 * metadata_score
            + 0.50 * nlp_score
            + pattern_bonus
        )
        # Apply calibration sigmoid to avoid over-confidence
        import math
        calibrated = 1 / (1 + math.exp(-8 * (raw - 0.5)))
        return round(min(calibrated, 0.99), 4)

    def _risk_level(self, score: float) -> str:
        if score >= 0.85:
            return "critical"
        if score >= 0.72:
            return "high"
        if score >= 0.50:
            return "medium"
        return "low"

    def _recommended_action(self, scam_type: str, risk: str) -> str:
        actions = {
            "digital_arrest": "Hang up immediately. Govt agencies NEVER arrest via phone/video.",
            "kyc_update": "Do NOT share OTP or Aadhaar. Your bank will NEVER call for OTP.",
            "loan_fraud": "Legitimate lenders NEVER charge processing fees upfront.",
            "investment": "No investment is guaranteed. Consult SEBI-registered advisors.",
            "lottery": "You cannot win a lottery you did not enter.",
            "impersonation": "Verify the caller's identity independently before sharing anything.",
            "unknown": "Be cautious. Disconnect and call the official helpline directly.",
        }
        base = actions.get(scam_type, actions["unknown"])
        if risk in ("critical", "high"):
            return f"⚠️ HIGH RISK: {base} Report to 1930."
        return base

    def classify(self, call_data: Dict) -> Dict:
        """
        Main classification pipeline.

        Args:
            call_data: Dict with keys matching CallMetadataIn schema

        Returns:
            Dict with scam_type, confidence, patterns, risk_level, etc.
        """
        t_start = time.perf_counter()

        # 1. Metadata risk scoring
        meta_score, features = self._metadata_scorer.score(call_data)

        # 2. Pattern matching on transcript
        transcript = call_data.get("transcript_snippet", "") or ""
        descriptions, weights, pattern_dominant = self._pattern_matcher.match(transcript)
        features.patterns_matched = descriptions
        features.pattern_weights = weights
        features.dominant_scam_type = pattern_dominant

        # 3. NLP classification
        nlp_type, nlp_score = self._nlp_classifier.predict(transcript, call_data)

        # 4. Resolve final scam type
        #    NLP wins if confident; pattern dominant breaks tie
        if nlp_score > 0.60 and nlp_type != "unknown":
            final_type = nlp_type
        elif pattern_dominant != "unknown":
            final_type = pattern_dominant
        else:
            final_type = "unknown"

        # 5. Final confidence score
        confidence = self._compute_final_score(meta_score, nlp_score, weights)
        risk = self._risk_level(confidence)

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        return {
            "scam_type": final_type,
            "confidence_score": confidence,
            "is_scam": confidence >= 0.72,
            "risk_level": risk,
            "patterns_matched": descriptions,
            "metadata_risk_score": round(meta_score, 4),
            "nlp_score": round(nlp_score, 4),
            "recommended_action": self._recommended_action(final_type, risk),
            "processing_time_ms": elapsed_ms,
            "model_version": "1.0.0-pattern-nlp-ensemble",
            # Audit fields
            "input_hash": hashlib.sha256(
                json.dumps(call_data, default=str, sort_keys=True).encode()
            ).hexdigest(),
        }


# ── Module-level singleton ────────────────────────────────────────
_classifier_instance: Optional[ScamCallClassifier] = None


def get_scam_classifier(model_path: Optional[str] = None) -> ScamCallClassifier:
    """Return the module-level singleton (loaded once at startup)."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = ScamCallClassifier(model_path)
        _classifier_instance.load()
    return _classifier_instance
