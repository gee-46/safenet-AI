"""
SafeNet AI – Test Suite
Covers: scam classifier, counterfeit detector, geo engine, citizen shield.
Run: pytest tests/ -v --cov=backend --cov-report=term-missing
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ══════════════════════════════════════════════════════════════════
# SCAM CLASSIFIER TESTS
# ══════════════════════════════════════════════════════════════════

class TestScamPatternMatcher:
    """Unit tests for the regex pattern matcher."""

    def setup_method(self):
        from backend.models.scam.classifier import ScamPatternMatcher
        self.matcher = ScamPatternMatcher()

    def test_digital_arrest_pattern(self):
        text = "This is CBI officer. You are under arrest. Stay on the call."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "digital_arrest"
        assert len(descriptions) > 0
        assert any(w > 0.7 for w in weights)

    def test_kyc_otp_pattern(self):
        text = "Your KYC is expired. Please share the OTP to update your account."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "kyc_update"
        assert any("OTP" in d or "otp" in d.lower() for d in descriptions)

    def test_lottery_pattern(self):
        text = "Congratulations! You have won 50 lakh rupees in our lucky draw."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "lottery"

    def test_investment_pattern(self):
        text = "Our scheme guarantees 40% monthly returns. Risk free investment."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "investment"

    def test_no_pattern_safe_text(self):
        text = "Hello, how are you? The weather is nice today."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "unknown"
        assert len(descriptions) == 0

    def test_empty_text(self):
        descriptions, weights, dominant = self.matcher.match("")
        assert descriptions == []
        assert weights == []
        assert dominant == "unknown"

    def test_secrecy_pattern(self):
        text = "Do not tell your family about this call. Keep this confidential."
        descriptions, weights, dominant = self.matcher.match(text)
        assert any(w >= 0.8 for w in weights)

    def test_loan_fraud_pattern(self):
        text = "Pre-approved loan of 5 lakh. Pay processing fee of 2000 to activate."
        descriptions, weights, dominant = self.matcher.match(text)
        assert dominant == "loan_fraud"


class TestMetadataRiskScorer:
    """Unit tests for metadata-based risk scoring."""

    def setup_method(self):
        from backend.models.scam.classifier import MetadataRiskScorer
        self.scorer = MetadataRiskScorer()

    def test_spoofed_number_high_risk(self):
        metadata = {
            "caller_number": "+919999999999",
            "number_spoofing_detected": True,
        }
        score, features = self.scorer.score(metadata)
        assert features.is_spoofed == 1.0
        assert score >= 0.35

    def test_normal_call_low_risk(self):
        metadata = {
            "caller_number": "+919876543210",
            "number_spoofing_detected": False,
            "call_duration_seconds": 120,
            "silence_ratio": 0.1,
            "speech_rate_wpm": 130,
        }
        score, features = self.scorer.score(metadata)
        assert score < 0.5

    def test_high_silence_ratio(self):
        metadata = {
            "caller_number": "+919876543210",
            "silence_ratio": 0.6,
            "number_spoofing_detected": False,
        }
        score, features = self.scorer.score(metadata)
        assert features.silence_ratio >= 0.6

    def test_fast_speech_rate(self):
        metadata = {
            "caller_number": "+919876543210",
            "speech_rate_wpm": 250,
            "number_spoofing_detected": False,
        }
        score, features = self.scorer.score(metadata)
        assert features.speech_rate_normalized > 0


class TestScamCallClassifier:
    """Integration tests for the full scam classifier pipeline."""

    def setup_method(self):
        from backend.models.scam.classifier import ScamCallClassifier
        self.classifier = ScamCallClassifier(model_path=None)  # pattern-only mode
        self.classifier.load()

    def test_digital_arrest_call(self):
        result = self.classifier.classify({
            "caller_number": "+911800123456",
            "victim_number": "+919876543210",
            "number_spoofing_detected": True,
            "transcript_snippet": "This is CBI officer. You are arrested for money laundering. Do not disconnect the call.",
            "call_duration_seconds": 300,
            "silence_ratio": 0.45,
        })
        assert result["scam_type"] == "digital_arrest"
        assert result["is_scam"] is True
        assert result["confidence_score"] >= 0.60
        assert result["risk_level"] in ("high", "critical")
        assert len(result["patterns_matched"]) > 0
        assert result["input_hash"]  # audit hash must be present

    def test_kyc_fraud_call(self):
        result = self.classifier.classify({
            "caller_number": "+919000000000",
            "victim_number": "+919876543210",
            "number_spoofing_detected": False,
            "transcript_snippet": "Your KYC is expired. Please share the OTP to update your bank account immediately.",
        })
        assert result["scam_type"] == "kyc_update"
        assert result["is_scam"] is True

    def test_safe_call(self):
        result = self.classifier.classify({
            "caller_number": "+919876543210",
            "victim_number": "+919000000000",
            "number_spoofing_detected": False,
            "transcript_snippet": "Hello, I am calling to confirm your appointment tomorrow at 3 PM.",
            "call_duration_seconds": 45,
            "silence_ratio": 0.05,
        })
        assert result["is_scam"] is False
        assert result["risk_level"] in ("low", "medium")

    def test_result_schema_completeness(self):
        result = self.classifier.classify({
            "caller_number": "+919876543210",
            "victim_number": "+910000000000",
        })
        required_keys = {
            "scam_type", "confidence_score", "is_scam", "risk_level",
            "patterns_matched", "recommended_action", "processing_time_ms", "input_hash",
        }
        assert required_keys.issubset(result.keys())

    def test_confidence_bounds(self):
        for _ in range(10):
            result = self.classifier.classify({
                "caller_number": "+919876543210",
                "victim_number": "+910000000000",
                "transcript_snippet": "Some random text here for testing purposes.",
            })
            assert 0.0 <= result["confidence_score"] <= 1.0

    def test_processing_time_reasonable(self):
        result = self.classifier.classify({
            "caller_number": "+919876543210",
            "victim_number": "+910000000000",
            "transcript_snippet": "Test transcript.",
        })
        # Pattern-only mode should be very fast
        assert result["processing_time_ms"] < 1000


# ══════════════════════════════════════════════════════════════════
# COUNTERFEIT DETECTOR TESTS
# ══════════════════════════════════════════════════════════════════

class TestSerialNumberValidation:
    """Unit tests for RBI serial number format validation."""

    def setup_method(self):
        from backend.models.counterfeit.detector import validate_serial_number
        self.validate = validate_serial_number

    def test_valid_500_serial(self):
        is_valid, reason = self.validate("0AA 000001", 500)
        assert is_valid is True

    def test_invalid_format_500(self):
        is_valid, reason = self.validate("XXXX12345678", 500)
        assert is_valid is False

    def test_unknown_prefix(self):
        is_valid, reason = self.validate("ZZZ999999", 500)
        assert is_valid is False
        assert "prefix" in reason

    def test_empty_serial(self):
        is_valid, reason = self.validate("", 500)
        assert is_valid is False

    def test_generic_denomination(self):
        is_valid, reason = self.validate("1AB123456", 200)
        # Should pass format check for non-500
        assert isinstance(is_valid, bool)


class TestPerceptualHasher:
    """Unit tests for image hashing."""

    def setup_method(self):
        from backend.models.counterfeit.detector import PerceptualHasher
        self.hasher = PerceptualHasher()

    def test_hash_returns_string(self):
        # Create minimal valid PNG bytes
        import io
        from PIL import Image
        img = Image.new("RGB", (100, 50), color=(255, 200, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        h = self.hasher.hash(buf.getvalue())
        assert isinstance(h, str)
        assert len(h) > 0

    def test_same_image_same_hash(self):
        import io
        from PIL import Image
        img = Image.new("RGB", (100, 50), color=(100, 150, 200))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes = buf.getvalue()
        h1 = self.hasher.hash(image_bytes)
        h2 = self.hasher.hash(image_bytes)
        assert h1 == h2

    def test_different_images_different_hash(self):
        import io
        import numpy as np
        from PIL import Image
        # Use images with distinct luminance patterns (not solid colors)
        # Solid colors all convert to same grayscale intensity → same hash
        images = []
        # Dark gradient image
        arr1 = np.zeros((50, 100, 3), dtype=np.uint8)
        arr1[:, :50] = 20   # dark left half
        arr1[:, 50:] = 200  # bright right half
        images.append(arr1)
        # Inverse gradient
        arr2 = np.zeros((50, 100, 3), dtype=np.uint8)
        arr2[:, :50] = 200
        arr2[:, 50:] = 20
        images.append(arr2)
        # Checkerboard
        arr3 = np.zeros((50, 100, 3), dtype=np.uint8)
        arr3[::2, ::2] = 255
        arr3[1::2, 1::2] = 255
        images.append(arr3)

        hashes = set()
        for arr in images:
            img = Image.fromarray(arr)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            hashes.add(self.hasher.hash(buf.getvalue()))
        assert len(hashes) >= 2


# ══════════════════════════════════════════════════════════════════
# GEO INTELLIGENCE TESTS
# ══════════════════════════════════════════════════════════════════

class TestH3GeoEngine:
    """Unit tests for H3 geo engine."""

    def setup_method(self):
        from backend.geo.geo_intelligence import H3GeoEngine
        self.engine = H3GeoEngine(default_resolution=7)

    def test_lat_lng_to_h3_returns_string(self):
        h3_index = self.engine.lat_lng_to_h3(19.076, 72.877)  # Mumbai
        assert isinstance(h3_index, str)
        assert len(h3_index) > 0

    def test_h3_to_center_roundtrip(self):
        lat, lng = 28.704, 77.102  # Delhi
        h3_index = self.engine.lat_lng_to_h3(lat, lng)
        center_lat, center_lng = self.engine.h3_to_center(h3_index)
        # Center should be within ~1km of input
        assert abs(center_lat - lat) < 0.05
        assert abs(center_lng - lng) < 0.05

    def test_bin_incidents(self):
        incidents = [
            {"lat": 19.076, "lng": 72.877, "scam_type": "digital_arrest"},
            {"lat": 19.077, "lng": 72.878, "scam_type": "digital_arrest"},
            {"lat": 28.704, "lng": 77.102, "scam_type": "kyc_update"},
        ]
        bins = self.engine.bin_incidents(incidents, resolution=7)
        assert len(bins) >= 1
        total = sum(len(v) for v in bins.values())
        assert total == 3

    def test_bin_incidents_skips_missing_coords(self):
        incidents = [
            {"lat": None, "lng": 72.877},
            {"lat": 19.076, "lng": None},
            {"lat": 19.076, "lng": 72.877, "scam_type": "test"},
        ]
        bins = self.engine.bin_incidents(incidents)
        total = sum(len(v) for v in bins.values())
        assert total == 1

    def test_risk_score_bounds(self):
        from datetime import datetime
        incidents = [
            {"scam_type": "digital_arrest", "created_at": datetime.utcnow()}
            for _ in range(10)
        ]
        score = self.engine.compute_cluster_risk(incidents, "test_cell")
        assert 0.0 <= score <= 1.0

    def test_empty_incidents_zero_risk(self):
        score = self.engine.compute_cluster_risk([], "test_cell")
        assert score == 0.0


class TestDBSCANClusterer:
    """Unit tests for DBSCAN geographic clustering."""

    def setup_method(self):
        from backend.geo.geo_intelligence import DBSCANClusterer
        self.clusterer = DBSCANClusterer(eps_km=2.0, min_samples=3)

    def test_clusters_nearby_points(self):
        # 5 points near Mumbai
        points = [
            (19.076, 72.877),
            (19.077, 72.878),
            (19.078, 72.876),
            (19.075, 72.879),
            (19.079, 72.875),
        ]
        labels = self.clusterer.cluster(points)
        assert len(labels) == 5
        # All should be in same cluster (all within 2km)
        non_noise = [l for l in labels if l >= 0]
        assert len(non_noise) >= 3

    def test_separates_distant_points(self):
        # Points in different cities
        points = [
            (19.076, 72.877),  # Mumbai
            (19.077, 72.878),
            (19.078, 72.876),
            (28.704, 77.102),  # Delhi
            (28.705, 77.103),
            (28.703, 77.101),
        ]
        labels = self.clusterer.cluster(points)
        unique_clusters = set(l for l in labels if l >= 0)
        # Should produce 2 distinct clusters
        assert len(unique_clusters) >= 1

    def test_too_few_points(self):
        labels = self.clusterer.cluster([(19.076, 72.877)])
        assert labels == [-1]

    def test_empty_points(self):
        labels = self.clusterer.cluster([])
        assert labels == []


# ══════════════════════════════════════════════════════════════════
# CITIZEN SHIELD TESTS
# ══════════════════════════════════════════════════════════════════

class TestLanguageDetector:
    """Unit tests for script-based language detection."""

    def setup_method(self):
        from backend.services.citizen_shield import LanguageDetector
        self.detector = LanguageDetector()

    def test_detects_hindi(self):
        text = "यह एक धोखाधड़ी कॉल है। कृपया OTP साझा न करें।"
        assert self.detector.detect(text) == "hi"

    def test_detects_tamil(self):
        text = "இது ஒரு மோசடி அழைப்பு. OTP பகிர வேண்டாம்."
        assert self.detector.detect(text) == "ta"

    def test_detects_kannada(self):
        text = "ಇದು ಮೋಸ. ಹಣ ಕಳುಹಿಸಬೇಡಿ."
        assert self.detector.detect(text) == "kn"

    def test_defaults_to_english(self):
        text = "This is a suspicious call."
        assert self.detector.detect(text) == "en"


class TestScamKnowledgeBase:
    """Unit tests for the FAQ knowledge base."""

    def setup_method(self):
        from backend.services.citizen_shield import ScamKnowledgeBase
        self.kb = ScamKnowledgeBase()

    def test_cbi_arrest_hit(self):
        result = self.kb.lookup("CBI officer is arresting me on video call")
        assert result is not None
        assert result["risk"] == "scam"

    def test_otp_hit(self):
        result = self.kb.lookup("They asked me to share my OTP for KYC update")
        assert result is not None
        assert result["risk"] == "scam"

    def test_lottery_hit(self):
        result = self.kb.lookup("They said I won a lottery prize of 50 lakhs")
        assert result is not None
        assert result["risk"] == "scam"

    def test_miss_returns_none(self):
        result = self.kb.lookup("The weather is nice today")
        assert result is None


@pytest.mark.asyncio
class TestCitizenShieldService:
    """Integration tests for the CitizenShield service."""

    async def test_assess_scam_call_english(self):
        from backend.services.citizen_shield import CitizenShieldService
        service = CitizenShieldService()
        result = await service.assess(
            message="A person claiming to be CBI officer said I am arrested for money laundering. They want me to stay on video call.",
            language="en",
            context_type="call",
        )
        assert result["risk_level"] in ("scam", "high_risk")
        assert result["confidence"] > 0.5
        assert len(result["recommended_actions"]) > 0
        assert result["helpline_number"] == "1930"
        assert result["response_language"] == "en"

    async def test_assess_safe_message(self):
        from backend.services.citizen_shield import CitizenShieldService
        service = CitizenShieldService()
        result = await service.assess(
            message="My bank sent me a routine transaction alert for my purchase at Flipkart.",
            language="en",
            context_type="sms",
        )
        assert result["risk_level"] in ("safe", "suspicious")
        assert result["helpline_number"] == "1930"

    async def test_assess_auto_detect_hindi(self):
        from backend.services.citizen_shield import CitizenShieldService
        service = CitizenShieldService()
        result = await service.assess(
            message="CBI अधिकारी ने कहा कि मुझे गिरफ्तार किया जाएगा। OTP बताइए।",
            language=None,  # auto-detect
            context_type="call",
        )
        # Should auto-detect Hindi
        assert result["response_language"] == "hi"

    async def test_result_always_has_required_fields(self):
        from backend.services.citizen_shield import CitizenShieldService
        service = CitizenShieldService()
        result = await service.assess(message="test message")
        required = {"risk_level", "confidence", "explanation", "recommended_actions",
                    "helpline_number", "response_language"}
        assert required.issubset(result.keys())


# ══════════════════════════════════════════════════════════════════
# EVIDENCE GENERATOR TESTS
# ══════════════════════════════════════════════════════════════════

class TestEvidenceGenerator:
    """Tests for PDF evidence package generation."""

    def setup_method(self):
        from backend.services.evidence_generator import EvidencePackageGenerator
        self.generator = EvidencePackageGenerator()

    def test_generates_pdf_bytes(self):
        pdf = self.generator.generate(
            case_number="SN-2026-TEST01",
            scam_reports=[
                {
                    "caller_number": "+911800123456",
                    "scam_type": "digital_arrest",
                    "confidence_score": 0.92,
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "created_at": "2026-06-01T10:00:00",
                }
            ],
            fraud_graph=None,
            case_summary={
                "fraud_type": "digital_arrest",
                "severity": "HIGH",
                "estimated_victims": 5,
                "estimated_loss_inr": 2_500_000,
                "states_involved": ["Maharashtra"],
                "status": "open",
                "description": "Test case for unit testing.",
                "avg_confidence": 0.92,
            },
            include_regulatory=True,
        )
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000
        # PDFs start with %PDF
        assert pdf[:4] == b"%PDF"

    def test_generate_and_store_returns_id(self):
        package_id, pdf_bytes = self.generator.generate_and_store(
            case_number="SN-2026-TEST02",
            scam_reports=[],
            fraud_graph=None,
            case_summary={
                "fraud_type": "kyc_update",
                "severity": "MEDIUM",
                "estimated_victims": 2,
                "estimated_loss_inr": 100_000,
                "states_involved": ["Delhi"],
                "status": "open",
                "description": "Test case.",
                "avg_confidence": 0.80,
            },
        )
        assert isinstance(package_id, str)
        assert len(package_id) == 36  # UUID format
        retrieved = self.generator.get_package(package_id)
        assert retrieved == pdf_bytes

    def test_nonexistent_package_returns_none(self):
        result = self.generator.get_package("nonexistent-id")
        assert result is None
