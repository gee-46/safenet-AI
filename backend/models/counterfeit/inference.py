"""
EfficientNet-B0 Inference
SafeNet AI Counterfeit Detection
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


# -----------------------------------------------------
# Configuration
# -----------------------------------------------------

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MODEL_PATH = (
    Path(__file__).parent / "best_counterfeit_model.pth"
)

CLASS_NAMES = [
    "fake",
    "real",
]


# -----------------------------------------------------
# Image Transform
# -----------------------------------------------------

transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225],
        ),
    ]
)


# -----------------------------------------------------
# Load Model
# -----------------------------------------------------

_model = None


def load_model():
    global _model

    if _model is not None:
        return _model

    model = models.efficientnet_b0(weights=None)

    num_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_features, 2)

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
        )

    state_dict = torch.load(
        MODEL_PATH,
        map_location=DEVICE,
    )

    model.load_state_dict(state_dict)

    model.to(DEVICE)
    model.eval()

    _model = model

    print(f"✓ Counterfeit model loaded ({DEVICE})")

    return _model


# -----------------------------------------------------
# Preprocess
# -----------------------------------------------------

def preprocess_image(image_bytes: bytes):

    image = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    tensor = transform(image)

    tensor = tensor.unsqueeze(0)

    tensor = tensor.to(DEVICE)

    return tensor


# -----------------------------------------------------
# Prediction
# -----------------------------------------------------

@torch.no_grad()
def predict(image_bytes: bytes):

    model = load_model()

    tensor = preprocess_image(image_bytes)

    start = time.perf_counter()

    outputs = model(tensor)

    probabilities = torch.softmax(outputs, dim=1)

    confidence, predicted = torch.max(
        probabilities,
        dim=1,
    )

    elapsed = int(
        (time.perf_counter() - start) * 1000
    )

    predicted_class = CLASS_NAMES[
        predicted.item()
    ]

    confidence = float(confidence.item())

    return {
        "prediction": predicted_class,
        "confidence": confidence,
        "processing_time_ms": elapsed,
    }


# -----------------------------------------------------
# Public Function
# -----------------------------------------------------

def verify_currency(image_bytes: bytes):

    result = predict(image_bytes)

    prediction = result["prediction"]

    confidence = round(
        result["confidence"],
        4,
    )

    if prediction == "fake":

        verdict = "counterfeit"

        recommendation = (
            "Suspected counterfeit. "
            "Do not accept the note."
        )

    else:

        verdict = "genuine"

        recommendation = (
            "The note appears genuine."
        )

    return {
        "verdict": verdict,
        "confidence_score": confidence,
        "recommendation": recommendation,
        "processing_time_ms": result["processing_time_ms"],
    }