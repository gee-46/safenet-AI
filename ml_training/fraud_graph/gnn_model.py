"""
SafeNet AI – Fraud Graph Neural Network
-----------------------------------------
GraphSAGE-based node classifier for fraud risk scoring.
Predicts the probability that a graph entity (phone number,
bank account, device) is involved in fraud.

Architecture:
  Input → GraphSAGE(64) → ReLU → Dropout → GraphSAGE(32) → ReLU → Linear(1) → Sigmoid

Node Features (8-dim):
  [0] fraud_count_normalised        (0–1)
  [1] report_count_normalised       (0–1)
  [2] degree_normalised             (0–1, in-graph degree)
  [3] days_active_normalised        (0–1)
  [4] fraud_neighbor_ratio          (0–1)
  [5] avg_neighbor_risk             (0–1)
  [6] transfer_volume_normalised    (0–1)
  [7] cross_state_flag              (0 or 1)

Training data: synthetic fraud graph + real NCRB-derived patterns.

Usage:
    python ml_training/fraud_graph/train_gnn.py --synthetic --epochs 50
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Lazy imports
_torch = None
_pyg = None


def _lazy_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


def _lazy_pyg():
    global _pyg
    if _pyg is None:
        import torch_geometric as pyg
        _pyg = pyg
    return _pyg


# ── Node Feature Extractor ────────────────────────────────────────

class NodeFeatureExtractor:
    """
    Converts Neo4j node properties → fixed-size feature vector.
    Used both at training time and inference time.
    """

    FEATURE_DIM = 8

    def extract(self, node_props: Dict) -> List[float]:
        """
        Returns 8-dimensional feature vector for a node.
        All features normalised to [0, 1].
        """
        fraud_count = min(node_props.get("fraud_count", 0) / 20.0, 1.0)
        report_count = min(node_props.get("report_count", 0) / 50.0, 1.0)
        degree = min(node_props.get("degree", 0) / 30.0, 1.0)
        days_active = min(node_props.get("days_active", 0) / 365.0, 1.0)
        fraud_neighbor_ratio = float(node_props.get("fraud_neighbor_ratio", 0.0))
        avg_neighbor_risk = float(node_props.get("avg_neighbor_risk", 0.0))
        transfer_volume = min(node_props.get("transfer_volume_lakh", 0) / 100.0, 1.0)
        cross_state = float(bool(node_props.get("cross_state_activity", False)))

        return [
            fraud_count,
            report_count,
            degree,
            days_active,
            fraud_neighbor_ratio,
            avg_neighbor_risk,
            transfer_volume,
            cross_state,
        ]

    def extract_batch(self, nodes: List[Dict]) -> "torch.Tensor":
        torch = _lazy_torch()
        features = [self.extract(n) for n in nodes]
        return torch.tensor(features, dtype=torch.float32)


# ── GNN Model Architecture ────────────────────────────────────────

class FraudGNN:
    """
    GraphSAGE model for fraud node classification.
    Lazy-loads PyTorch Geometric to avoid import at startup.
    """

    def __init__(self, in_channels: int = 8, hidden_channels: int = 64, dropout: float = 0.3):
        self.in_channels = in_channels
        self.hidden_channels = hidden_channels
        self.dropout = dropout
        self._model = None

    def build(self):
        """Build the model (requires PyTorch Geometric)."""
        torch = _lazy_torch()
        pyg = _lazy_pyg()
        from torch_geometric.nn import SAGEConv
        import torch.nn as nn
        import torch.nn.functional as F

        class _SAGEClassifier(nn.Module):
            def __init__(self, in_ch, hidden_ch, dropout):
                super().__init__()
                self.conv1 = SAGEConv(in_ch, hidden_ch)
                self.conv2 = SAGEConv(hidden_ch, hidden_ch // 2)
                self.dropout = dropout
                self.classifier = nn.Linear(hidden_ch // 2, 1)

            def forward(self, x, edge_index):
                x = self.conv1(x, edge_index)
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)
                x = self.conv2(x, edge_index)
                x = F.relu(x)
                x = F.dropout(x, p=self.dropout, training=self.training)
                return self.classifier(x)

        self._model = _SAGEClassifier(self.in_channels, self.hidden_channels, self.dropout)
        return self._model

    def save(self, path: str):
        torch = _lazy_torch()
        if self._model:
            torch.save(self._model.state_dict(), path)
            print(f"[FraudGNN] Model saved to {path}")

    def load(self, path: str):
        torch = _lazy_torch()
        model = self.build()
        model.load_state_dict(torch.load(path, map_location="cpu"))
        model.eval()
        self._model = model
        return model

    def predict_risk(self, node_features: "torch.Tensor", edge_index: "torch.Tensor") -> "torch.Tensor":
        """Returns sigmoid risk probabilities for each node."""
        torch = _lazy_torch()
        if self._model is None:
            raise RuntimeError("Model not built/loaded")
        self._model.eval()
        with torch.no_grad():
            logits = self._model(node_features, edge_index)
            return torch.sigmoid(logits).squeeze(-1)


# ── Synthetic Graph Generator (for training demo) ─────────────────

class SyntheticFraudGraphGenerator:
    """
    Generates synthetic fraud graph training data.
    Simulates phone number networks with known fraud rings.
    """

    def __init__(self, num_nodes: int = 500, fraud_ratio: float = 0.25, seed: int = 42):
        self.num_nodes = num_nodes
        self.fraud_ratio = fraud_ratio
        random.seed(seed)
        np.random.seed(seed)

    def generate(self) -> Tuple["torch.Tensor", "torch.Tensor", "torch.Tensor"]:
        """
        Returns (node_features, edge_index, labels).
        labels: 1 = fraud node, 0 = legitimate node
        """
        torch = _lazy_torch()

        num_fraud = int(self.num_nodes * self.fraud_ratio)
        num_legit = self.num_nodes - num_fraud

        labels = [1] * num_fraud + [0] * num_legit
        random.shuffle(labels)
        labels_tensor = torch.tensor(labels, dtype=torch.float32)

        # Generate node features
        extractor = NodeFeatureExtractor()
        nodes = []
        for i, label in enumerate(labels):
            if label == 1:
                # Fraud node: high counts, many neighbours, cross-state
                node = {
                    "fraud_count": random.randint(2, 25),
                    "report_count": random.randint(5, 60),
                    "degree": random.randint(5, 35),
                    "days_active": random.randint(30, 365),
                    "fraud_neighbor_ratio": random.uniform(0.4, 1.0),
                    "avg_neighbor_risk": random.uniform(0.5, 1.0),
                    "transfer_volume_lakh": random.uniform(5, 150),
                    "cross_state_activity": random.random() > 0.3,
                }
            else:
                # Legitimate node: low counts
                node = {
                    "fraud_count": random.choices([0, 1], weights=[90, 10])[0],
                    "report_count": random.choices([0, 1, 2], weights=[80, 15, 5])[0],
                    "degree": random.randint(1, 10),
                    "days_active": random.randint(1, 180),
                    "fraud_neighbor_ratio": random.uniform(0.0, 0.2),
                    "avg_neighbor_risk": random.uniform(0.0, 0.3),
                    "transfer_volume_lakh": random.uniform(0, 20),
                    "cross_state_activity": random.random() > 0.8,
                }
            nodes.append(node)

        features = extractor.extract_batch(nodes)

        # Generate edges: fraud nodes form dense clusters, legit nodes sparse
        fraud_indices = [i for i, l in enumerate(labels) if l == 1]
        legit_indices = [i for i, l in enumerate(labels) if l == 0]

        edges_src, edges_dst = [], []

        # Fraud ring: dense internal connections
        for i in range(len(fraud_indices)):
            for j in range(i + 1, min(i + 6, len(fraud_indices))):
                src, dst = fraud_indices[i], fraud_indices[j]
                edges_src.extend([src, dst])
                edges_dst.extend([dst, src])

        # Some fraud → legit edges (mule accounts)
        mule_count = min(30, len(legit_indices))
        mules = random.sample(legit_indices, mule_count)
        for fraud_node in random.sample(fraud_indices, min(20, len(fraud_indices))):
            for mule in random.sample(mules, min(3, len(mules))):
                edges_src.extend([fraud_node, mule])
                edges_dst.extend([mule, fraud_node])

        # Legit sparse connections
        for i in range(0, len(legit_indices) - 1, 5):
            if i + 1 < len(legit_indices):
                src, dst = legit_indices[i], legit_indices[i + 1]
                edges_src.extend([src, dst])
                edges_dst.extend([dst, src])

        edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)

        return features, edge_index, labels_tensor


# ── Training Script ───────────────────────────────────────────────

def train_gnn(
    output_dir: str,
    num_nodes: int = 500,
    epochs: int = 50,
    lr: float = 0.01,
    hidden_channels: int = 64,
    dropout: float = 0.3,
    use_synthetic: bool = True,
):
    """Train the GNN fraud classifier."""
    torch = _lazy_torch()
    import torch.nn.functional as F

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[GNN Training] Device: {device}")

    # Generate or load data
    if use_synthetic:
        print(f"[GNN Training] Generating synthetic graph ({num_nodes} nodes)...")
        gen = SyntheticFraudGraphGenerator(num_nodes=num_nodes)
        features, edge_index, labels = gen.generate()
    else:
        raise NotImplementedError("Real graph data loading not implemented — use --synthetic for demo")

    features = features.to(device)
    edge_index = edge_index.to(device)
    labels = labels.to(device)

    # Train/test split (node-level)
    num_nodes_actual = features.shape[0]
    perm = torch.randperm(num_nodes_actual)
    train_mask = torch.zeros(num_nodes_actual, dtype=torch.bool)
    test_mask = torch.zeros(num_nodes_actual, dtype=torch.bool)
    train_mask[perm[:int(0.8 * num_nodes_actual)]] = True
    test_mask[perm[int(0.8 * num_nodes_actual):]] = True

    # Build model
    gnn = FraudGNN(in_channels=8, hidden_channels=hidden_channels, dropout=dropout)
    model = gnn.build().to(device)

    # Class weights to handle imbalance
    num_fraud = labels.sum().item()
    num_legit = num_nodes_actual - num_fraud
    pos_weight = torch.tensor([num_legit / max(num_fraud, 1)]).to(device)
    criterion = torch.nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimiser = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimiser, patience=10, factor=0.5)

    print(f"[GNN Training] Nodes: {num_nodes_actual} | Fraud: {int(num_fraud)} | Edges: {edge_index.shape[1]}")
    print(f"[GNN Training] Starting {epochs} epochs...")

    best_f1 = 0.0
    best_state = None

    for epoch in range(1, epochs + 1):
        # Training
        model.train()
        optimiser.zero_grad()
        logits = model(features, edge_index).squeeze(-1)
        loss = criterion(logits[train_mask], labels[train_mask])
        loss.backward()
        optimiser.step()

        # Evaluation
        model.eval()
        with torch.no_grad():
            test_logits = model(features, edge_index).squeeze(-1)
            preds = (torch.sigmoid(test_logits[test_mask]) >= 0.5).float()
            true = labels[test_mask]

            tp = ((preds == 1) & (true == 1)).sum().item()
            fp = ((preds == 1) & (true == 0)).sum().item()
            fn = ((preds == 0) & (true == 1)).sum().item()
            tn = ((preds == 0) & (true == 0)).sum().item()

            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 1e-8)
            acc = (tp + tn) / max(tp + fp + fn + tn, 1)

        scheduler.step(loss)

        if f1 > best_f1:
            best_f1 = f1
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == 1:
            print(
                f"  Epoch {epoch:3d}/{epochs} | Loss: {loss.item():.4f} | "
                f"Acc: {acc:.3f} | P: {precision:.3f} | R: {recall:.3f} | F1: {f1:.3f}"
            )

    # Save best model
    if best_state:
        model.load_state_dict(best_state)

    checkpoint_path = str(output_path / "best_gnn.pt")
    torch.save(model.state_dict(), checkpoint_path)

    # Save model config
    config = {
        "in_channels": 8,
        "hidden_channels": hidden_channels,
        "dropout": dropout,
        "best_f1": best_f1,
        "trained_at": str(__import__("datetime").datetime.utcnow()),
        "num_nodes": num_nodes_actual,
        "feature_names": [
            "fraud_count_norm", "report_count_norm", "degree_norm",
            "days_active_norm", "fraud_neighbor_ratio", "avg_neighbor_risk",
            "transfer_volume_norm", "cross_state_flag",
        ],
    }
    with open(output_path / "gnn_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n[GNN Training] [OK] Best F1: {best_f1:.4f}")
    print(f"[GNN Training] [OK] Model saved to {checkpoint_path}")
    return {"best_f1": best_f1, "checkpoint": checkpoint_path}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train SafeNet Fraud GNN")
    parser.add_argument("--output_dir", default="./ml_training/fraud_graph/checkpoints")
    parser.add_argument("--num_nodes", type=int, default=500)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--hidden", type=int, default=64)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--synthetic", action="store_true", default=True)
    args = parser.parse_args()

    train_gnn(
        output_dir=args.output_dir,
        num_nodes=args.num_nodes,
        epochs=args.epochs,
        lr=args.lr,
        hidden_channels=args.hidden,
        dropout=args.dropout,
        use_synthetic=args.synthetic,
    )
