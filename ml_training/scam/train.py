"""
SafeNet AI – Scam Classifier Fine-Tuning
-----------------------------------------
Fine-tunes DistilBERT on a scam transcript dataset.

Dataset format (CSV):
  text,label
  "Your account has been blocked. Share OTP to update KYC.",kyc_update
  "You have been arrested by CBI. Stay on the call.",digital_arrest
  ...

Labels: digital_arrest | loan_fraud | lottery | kyc_update |
        impersonation | investment | romance | tech_support | unknown

Usage:
    python ml_training/scam/train.py \
        --data_path ./data/scam_corpus.csv \
        --output_dir ./ml_training/scam/checkpoints \
        --epochs 5 \
        --batch_size 16
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd


LABEL2ID = {
    "unknown": 0,
    "digital_arrest": 1,
    "loan_fraud": 2,
    "lottery": 3,
    "kyc_update": 4,
    "impersonation": 5,
    "investment": 6,
    "romance": 7,
    "tech_support": 8,
}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}
NUM_LABELS = len(LABEL2ID)


def generate_synthetic_data(n_samples: int = 2000) -> pd.DataFrame:
    """
    Generate synthetic training data when no real corpus available.
    In production, replace with real labelled scam transcripts.
    """
    templates = {
        "digital_arrest": [
            "This is CBI officer calling. You are under arrest for money laundering. Do not disconnect.",
            "Your Aadhaar has been linked to a drug trafficking case. Stay on the video call.",
            "ED has issued a warrant in your name. You must verify your identity on this video call.",
            "You are accused of sending obscene content online. This is cybercrime police speaking.",
            "Your SIM card is being used for illegal activities. CBI is monitoring you. Do not inform family.",
            "You have violated NDPS act. We will arrest you unless you cooperate immediately.",
            "Customs has seized a package in your name with illegal drugs. Pay the fine immediately.",
        ],
        "kyc_update": [
            "Your bank account will be blocked in 2 hours. Please share OTP to complete KYC update.",
            "TRAI has received a complaint against your mobile number. Share OTP to avoid disconnection.",
            "Your Aadhaar is not linked to your bank account. Share the OTP we just sent.",
            "Dear customer, your PAN card KYC is expired. Update now by sharing the verification code.",
            "This is SBI customer care. Your net banking will be suspended. Enter OTP to prevent this.",
            "Your UPI ID has been flagged for suspicious activity. Share OTP to unlock your account.",
        ],
        "loan_fraud": [
            "Congratulations! You are pre-approved for a loan of 5 lakhs. Pay processing fee of 2000 rupees.",
            "Your loan of 10 lakhs is approved. Transfer the registration fee to activate disbursement.",
            "Special loan offer at 0% interest. Just pay the one-time documentation fee of 1500 rupees.",
            "Instant loan without CIBIL check. Advance fee of 3000 to be paid before disbursement.",
        ],
        "lottery": [
            "Congratulations! You have won 50 lakh rupees in the KBC lucky draw. Claim your prize now.",
            "You are the lucky winner of our Diwali contest. Pay the GST amount to receive your prize.",
            "Your mobile number has won 1 crore rupees. Send us your bank details to transfer the amount.",
            "You have been selected in Google India lucky draw. Pay courier charges to receive the check.",
        ],
        "investment": [
            "Join our exclusive stock tips WhatsApp group. Guaranteed 30% monthly returns.",
            "Invest in our crypto scheme. We guarantee to double your money in 30 days.",
            "Our SEBI-registered scheme gives 40% annual returns. Limited slots available.",
            "Join our trading academy. Our members make 50 thousand per day with guaranteed signals.",
        ],
        "impersonation": [
            "This is PM Office calling. You have been selected for a government scheme. Share Aadhaar.",
            "I am calling from Microsoft. Your computer has a virus. Install this software immediately.",
            "Amazon customer service here. Your order has a problem. Share your account password.",
            "This is IRCTC helpline. Your ticket booking has failed. Refund will be processed after OTP.",
        ],
        "unknown": [
            "Hello, how are you today?",
            "Is this the correct number for Mr. Sharma?",
            "I am calling to follow up on your insurance policy renewal.",
            "This is a reminder about your EMI payment due tomorrow.",
            "Your order has been dispatched and will arrive within 2 days.",
        ],
    }

    rows = []
    for label, texts in templates.items():
        # Generate variations
        for text in texts:
            rows.append({"text": text, "label": label})
            # Add noise variants
            rows.append({"text": text + " Please cooperate fully.", "label": label})
            rows.append({"text": "Hello. " + text, "label": label})

    # Upsample to n_samples
    df = pd.DataFrame(rows)
    if len(df) < n_samples:
        df = df.sample(n=n_samples, replace=True, random_state=42).reset_index(drop=True)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


def compute_metrics(eval_pred):
    """Compute precision, recall, F1 for multi-class classification."""
    from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, predictions),
        "f1_macro": f1_score(labels, predictions, average="macro", zero_division=0),
        "precision_macro": precision_score(labels, predictions, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, predictions, average="macro", zero_division=0),
    }


def train(
    data_path: str,
    output_dir: str,
    model_name: str = "distilbert-base-multilingual-cased",
    epochs: int = 5,
    batch_size: int = 16,
    max_length: int = 256,
    learning_rate: float = 2e-5,
    use_synthetic: bool = False,
):
    """Main training function."""
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        DataCollatorWithPadding,
    )
    from datasets import Dataset

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[Training] Model: {model_name}")
    print(f"[Training] Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    # ── Load Data ───────────────────────────────────────────────
    if use_synthetic or not Path(data_path).exists():
        print("[Training] Using synthetic training data (for demo)")
        df = generate_synthetic_data(2000)
    else:
        df = pd.read_csv(data_path)
        required = {"text", "label"}
        if not required.issubset(df.columns):
            raise ValueError(f"CSV must have columns: {required}")
        print(f"[Training] Loaded {len(df)} samples from {data_path}")

    # Validate labels
    df = df[df["label"].isin(LABEL2ID.keys())].copy()
    df["label_id"] = df["label"].map(LABEL2ID)

    # Train/val split
    from sklearn.model_selection import train_test_split
    train_df, val_df = train_test_split(df, test_size=0.15, stratify=df["label_id"], random_state=42)
    print(f"[Training] Train: {len(train_df)} | Val: {len(val_df)}")

    # Print class distribution
    print("[Training] Class distribution:")
    for label, count in df["label"].value_counts().items():
        print(f"  {label}: {count}")

    # ── Tokeniser ────────────────────────────────────────────────
    print(f"[Training] Loading tokeniser: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_length,
            padding=False,
        )

    train_dataset = Dataset.from_pandas(train_df[["text", "label_id"]].rename(columns={"label_id": "labels"}))
    val_dataset = Dataset.from_pandas(val_df[["text", "label_id"]].rename(columns={"label_id": "labels"}))

    train_dataset = train_dataset.map(tokenize, batched=True, remove_columns=["text"])
    val_dataset = val_dataset.map(tokenize, batched=True, remove_columns=["text"])

    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # ── Model ────────────────────────────────────────────────────
    print("[Training] Loading model...")
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    # ── Training Args ────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=str(output_path / "runs"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        weight_decay=0.01,
        warmup_ratio=0.1,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_dir=str(output_path / "logs"),
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    # ── Train ────────────────────────────────────────────────────
    print("[Training] Starting training...")
    train_result = trainer.train()

    # ── Evaluate ─────────────────────────────────────────────────
    print("[Training] Evaluating...")
    eval_metrics = trainer.evaluate()
    print(f"[Training] Eval results: {json.dumps(eval_metrics, indent=2)}")

    # ── Save ─────────────────────────────────────────────────────
    best_model_path = output_path / "best_model"
    trainer.save_model(str(best_model_path))
    tokenizer.save_pretrained(str(best_model_path))

    # Save label map
    with open(best_model_path / "label_map.json", "w") as f:
        json.dump({"label2id": LABEL2ID, "id2label": ID2LABEL}, f, indent=2)

    print(f"[Training] ✅ Model saved to {best_model_path}")
    print(f"[Training] Best F1 (macro): {eval_metrics.get('eval_f1_macro', 'N/A'):.4f}")

    return eval_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SafeNet scam call classifier")
    parser.add_argument("--data_path", default="./data/scam_corpus.csv")
    parser.add_argument("--output_dir", default="./ml_training/scam/checkpoints")
    parser.add_argument("--model_name", default="distilbert-base-multilingual-cased")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--max_length", type=int, default=256)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data for demo")
    args = parser.parse_args()

    train(
        data_path=args.data_path,
        output_dir=args.output_dir,
        model_name=args.model_name,
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_length=args.max_length,
        learning_rate=args.lr,
        use_synthetic=args.synthetic,
    )
