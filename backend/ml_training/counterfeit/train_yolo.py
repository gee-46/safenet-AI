"""
SafeNet AI – YOLOv8 Counterfeit Note Detector Training
--------------------------------------------------------
Fine-tunes YOLOv8 to:
  1. Detect and localise currency notes in images
  2. Classify security feature regions for anomaly scoring

Dataset structure:
  data/counterfeit/
  ├── images/
  │   ├── train/   (genuine + counterfeit note photos)
  │   └── val/
  ├── labels/      (YOLO format: class x_c y_c w h)
  │   ├── train/
  │   └── val/
  └── dataset.yaml

Classes:
  0: note_genuine
  1: note_counterfeit
  2: watermark_region
  3: security_thread_region
  4: microprint_region
  5: serial_number_region

Usage:
    python ml_training/counterfeit/train_yolo.py \
        --data_yaml ./data/counterfeit/dataset.yaml \
        --output_dir ./ml_training/counterfeit/checkpoints \
        --epochs 50 \
        --imgsz 640
"""
from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List


def create_synthetic_dataset_yaml(output_dir: str) -> str:
    """
    Create a minimal YOLO dataset YAML pointing to synthetic data.
    In production, replace with real annotated currency images.
    """
    yaml_content = """
# SafeNet AI – Counterfeit Note Detection Dataset
path: ./data/counterfeit
train: images/train
val: images/val

nc: 6  # number of classes
names:
  0: note_genuine
  1: note_counterfeit
  2: watermark_region
  3: security_thread_region
  4: microprint_region
  5: serial_number_region

# Dataset notes:
# - Images should be 640x640 or larger
# - Include notes from multiple angles and lighting conditions
# - Include both Rs 500 and Rs 2000 denominations
# - Balance genuine vs counterfeit (ideally 50/50 after augmentation)
"""
    yaml_path = Path(output_dir) / "dataset.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    yaml_path.write_text(yaml_content.strip())
    return str(yaml_path)


def generate_synthetic_images(output_dir: str, num_images: int = 100):
    """
    Generate synthetic training images using PIL.
    Creates simple coloured rectangles simulating notes.
    In production: replace with real annotated currency images.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
    except ImportError:
        print("[YOLOTrain] PIL not available — skipping synthetic image generation")
        return

    for split in ["train", "val"]:
        img_dir = Path(output_dir) / "images" / split
        lbl_dir = Path(output_dir) / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        n = num_images if split == "train" else max(num_images // 5, 10)

        for i in range(n):
            # Create a simplified Rs 500 note representation
            w, h = 640, 320
            img = Image.new("RGB", (w, h), color=(random.randint(220, 240), random.randint(200, 220), random.randint(150, 180)))
            draw = ImageDraw.Draw(img)

            # Simulate note border
            draw.rectangle([5, 5, w-5, h-5], outline=(100, 80, 50), width=3)

            # Watermark region
            draw.ellipse([60, 60, 160, 200], fill=(230, 220, 180), outline=(180, 160, 100))
            wm_x, wm_y, wm_w, wm_h = 110/w, 130/h, 100/w, 140/h

            # Security thread (vertical line ~35% from left)
            thread_x = int(w * 0.35)
            thread_color = (50, 50, 200) if random.random() > 0.3 else (150, 150, 150)
            draw.line([(thread_x, 10), (thread_x, h-10)], fill=thread_color, width=4)
            st_x, st_y, st_w, st_h = thread_x/w, 0.5, 4/w, 0.95

            # Microprint region
            mp_region_x = int(w * 0.6)
            draw.rectangle([mp_region_x, int(h*0.45), mp_region_x+120, int(h*0.55)],
                           fill=(200, 195, 150), outline=(100, 90, 50))

            # Serial number
            sn_x = random.randint(10, 80)
            sn_y = random.randint(10, 30)
            draw.text((sn_x, sn_y), f"0AA {random.randint(100000, 999999)}", fill=(20, 20, 20))

            # Determine if counterfeit (40% chance in training)
            is_counterfeit = random.random() < 0.4
            class_id = 1 if is_counterfeit else 0

            # Add visual defects for counterfeits
            if is_counterfeit:
                # Poor quality printing (add noise)
                arr = np.array(img)
                noise = np.random.randint(-30, 30, arr.shape, dtype=np.int16)
                arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                img = Image.fromarray(arr)
                # Missing/poor thread
                draw = ImageDraw.Draw(img)
                draw.line([(thread_x, 10), (thread_x, h-10)], fill=(200, 200, 200), width=2)

            # Save image
            img_path = img_dir / f"note_{split}_{i:04d}.jpg"
            img.save(str(img_path), quality=85)

            # Save YOLO label (note bounding box)
            note_label = f"{class_id} 0.5 0.5 0.98 0.98\n"
            note_label += f"2 {wm_x:.4f} {wm_y:.4f} {wm_w:.4f} {wm_h:.4f}\n"
            note_label += f"3 {st_x:.4f} {st_y:.4f} {st_w:.4f} {st_h:.4f}\n"

            lbl_path = lbl_dir / f"note_{split}_{i:04d}.txt"
            lbl_path.write_text(note_label)

        print(f"[YOLOTrain] Generated {n} synthetic images for {split}")


def train_yolo(
    data_yaml: str,
    output_dir: str,
    model_size: str = "yolov8n",
    epochs: int = 50,
    imgsz: int = 640,
    batch_size: int = 16,
    use_synthetic: bool = False,
) -> Dict:
    """
    Train YOLOv8 on currency note dataset.

    Args:
        data_yaml: Path to YOLO dataset YAML
        output_dir: Where to save checkpoints
        model_size: yolov8n | yolov8s | yolov8m (n=nano for fast demo)
        epochs: Training epochs
        imgsz: Input image size
        batch_size: Batch size
        use_synthetic: Generate and use synthetic data
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[YOLOTrain] ultralytics not installed. Run: pip install ultralytics")
        return {}

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate synthetic data if requested
    if use_synthetic:
        print("[YOLOTrain] Generating synthetic training data...")
        synthetic_dir = "./data/counterfeit"
        generate_synthetic_images(synthetic_dir, num_images=200)
        data_yaml = create_synthetic_dataset_yaml(synthetic_dir)
        print(f"[YOLOTrain] Synthetic dataset YAML: {data_yaml}")

    if not Path(data_yaml).exists():
        print(f"[YOLOTrain] Dataset YAML not found: {data_yaml}")
        print("[YOLOTrain] Use --synthetic flag to generate demo data")
        return {}

    # Load pre-trained YOLOv8
    model_name = f"{model_size}.pt"
    print(f"[YOLOTrain] Loading pre-trained model: {model_name}")
    model = YOLO(model_name)

    # Train
    # NOTE: `project` must be an absolute path. Ultralytics nests any
    # relative project path under its own global `runs/<task>/` root
    # (from ~/.config/Ultralytics/settings.json), which silently produces
    # a save directory that does not match a manually-reconstructed path
    # like `output_path / name / weights / best.pt` below — that mismatch
    # previously caused this script to report "best.pt not found" even on
    # fully successful training runs.
    project_dir = output_path.resolve()
    print(f"[YOLOTrain] Starting training: {epochs} epochs, img size {imgsz}")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch_size,
        project=str(project_dir),
        name="safenet_counterfeit",
        exist_ok=True,
        pretrained=True,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        augment=True,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=5.0,         # Limited rotation (notes don't rotate much)
        translate=0.1,
        scale=0.3,
        flipud=0.0,          # Don't flip upside down
        fliplr=0.5,
        mosaic=0.5,
        mixup=0.1,
        save=True,
        save_period=10,
        verbose=True,
        patience=20,         # Early stopping
        device=0 if __import__("torch").cuda.is_available() else "cpu",
    )

    # Find best checkpoint — prefer asking the trainer directly rather than
    # reconstructing the path by hand, since that's the one source of truth
    # for where Ultralytics actually wrote the weights.
    import shutil
    trainer_best = getattr(getattr(model, "trainer", None), "best", None)
    candidates = [
        Path(trainer_best) if trainer_best else None,
        project_dir / "safenet_counterfeit" / "weights" / "best.pt",
        Path("runs") / "detect" / "safenet_counterfeit" / "weights" / "best.pt",
    ]
    best_pt = next((p for p in candidates if p and p.exists()), None)

    if best_pt:
        final_path = output_path / "best_yolo.pt"
        shutil.copy(str(best_pt), str(final_path))
        print(f"[YOLOTrain] ✅ Best model saved to {final_path}")
    else:
        print("[YOLOTrain] ⚠️  best.pt not found — check training output")

    # Save training summary
    summary = {
        "model": model_size,
        "epochs": epochs,
        "imgsz": imgsz,
        "data_yaml": str(data_yaml),
        "trained_at": str(__import__("datetime").datetime.utcnow()),
    }
    with open(output_path / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print("[YOLOTrain] Training complete!")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train YOLOv8 counterfeit detector")
    parser.add_argument("--data_yaml", default="./data/counterfeit/dataset.yaml")
    parser.add_argument("--output_dir", default="./ml_training/counterfeit/checkpoints")
    parser.add_argument("--model", default="yolov8n", choices=["yolov8n", "yolov8s", "yolov8m"])
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    train_yolo(
        data_yaml=args.data_yaml,
        output_dir=args.output_dir,
        model_size=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch_size=args.batch,
        use_synthetic=args.synthetic,
    )
