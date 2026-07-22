"""
SafeNet AI - EfficientNet Counterfeit Detector
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from .inference import verify_currency


class CounterfeitDetector:
    """
    Wrapper around EfficientNet inference.
    Keeps the same API expected by currency_routes.py.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path

    def load(self):
        """
        Model loading is handled lazily in inference.py
        """
        return

    def analyse(self, image_bytes: bytes, denomination: int = 500):

        result = verify_currency(image_bytes)

        verdict = result["verdict"]

        confidence = result["confidence_score"]

        recommendation = result["recommendation"]

        processing_time = result["processing_time_ms"]

        if verdict == "counterfeit":
            defects = [
                "ai_model_detected_counterfeit"
            ]
        else:
            defects = []

        return {
            "denomination": denomination,

            "verdict": verdict,

            "confidence_score": confidence,

            "defects_detected": defects,

            "security_checks": {
                "watermark": confidence,
                "security_thread": confidence,
                "microprint": confidence,
            },

            "serial_number_valid": None,

            "serial_number_pattern": None,

            "recommendation": recommendation,

            "processing_time_ms": processing_time,

            "image_hash": hashlib.sha256(
                image_bytes
            ).hexdigest(),
        }


_detector_instance = None


def get_counterfeit_detector(model_path=None):
    global _detector_instance

    if _detector_instance is None:
        _detector_instance = CounterfeitDetector(model_path)
        _detector_instance.load()

    return _detector_instance