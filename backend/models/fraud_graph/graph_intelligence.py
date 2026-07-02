"""
SafeNet AI – Fraud Graph Intelligence
---------------------------------------
Graph-based fraud network analysis using Neo4j as the persistent store
and a GNN (Graph Neural Network) for risk scoring.

Two modes:
  1. Rule-based (no GNN): Heuristic risk scores on graph topology
  2. GNN mode: Node embeddings via trained GraphSAGE model

Graph schema:
  Nodes: PhoneNumber | BankAccount | Device | IPAddress | Person | Organisation
  Edges: CALLED | TRANSFERRED_TO | SHARES_DEVICE | MULE_LINK | ASSOCIATED_WITH
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Lazy imports
_neo4j = None
_torch = None
_pyg = None


def _lazy_neo4j():
    global _neo4j
    if _neo4j is None:
        from neo4j import AsyncGraphDatabase
        _neo4j = AsyncGraphDatabase
    return _neo4j


def _lazy_torch():
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


# ── Graph Schema Constants ────────────────────────────────────────

NODE_TYPES = {
    "phone_number": "PhoneNumber",
    "bank_account": "BankAccount",
    "device": "Device",
    "ip_address": "IPAddress",
    "person": "Person",
    "organisation": "Organisation",
}

EDGE_TYPES = [
    "CALLED",
    "TRANSFERRED_TO",
    "SHARES_DEVICE",
    "MULE_LINK",
    "ASSOCIATED_WITH",
    "CONTROLS",
]

# Risk multipliers for edge types
EDGE_RISK_WEIGHTS = {
    "CALLED": 0.3,
    "TRANSFERRED_TO": 0.7,
    "SHARES_DEVICE": 0.5,
    "MULE_LINK": 0.9,
    "ASSOCIATED_WITH": 0.4,
    "CONTROLS": 0.8,
}


# ── Cypher Query Templates ────────────────────────────────────────

CYPHER_UPSERT_NODE = """
MERGE (n:{label} {{id: $id}})
ON CREATE SET n += $props, n.created_at = datetime()
ON MATCH SET n += $props, n.updated_at = datetime()
RETURN n
"""

CYPHER_UPSERT_EDGE = """
MATCH (a {{id: $source_id}})
MATCH (b {{id: $target_id}})
MERGE (a)-[r:{rel_type}]->(b)
ON CREATE SET r += $props, r.created_at = datetime()
ON MATCH SET r += $props, r.updated_at = datetime()
RETURN r
"""

CYPHER_GET_SUBGRAPH = """
MATCH path = (start {{id: $entity_id}})-[*1..{depth}]-(connected)
WITH nodes(path) AS ns, relationships(path) AS rs
UNWIND ns AS n
WITH COLLECT(DISTINCT n) AS all_nodes, rs
UNWIND rs AS r
RETURN all_nodes,
       COLLECT(DISTINCT {{
           source: startNode(r).id,
           target: endNode(r).id,
           type: type(r),
           props: properties(r)
       }}) AS all_edges
LIMIT 1
"""

CYPHER_FRAUD_SCORE = """
MATCH (n {{id: $entity_id}})
OPTIONAL MATCH (n)-[:CALLED|TRANSFERRED_TO*1..2]-(linked)
WHERE linked.fraud_count > 0
WITH n, COUNT(DISTINCT linked) AS fraud_neighbors
RETURN 
    n.fraud_count AS fraud_count,
    n.report_count AS report_count,
    fraud_neighbors,
    n.risk_score AS stored_risk_score
"""

CYPHER_CONNECTED_CASES = """
MATCH (n {{id: $entity_id}})-[*1..3]-(case:FraudCase)
RETURN COLLECT(DISTINCT case.case_number) AS case_numbers
LIMIT 20
"""

CYPHER_STATES_INVOLVED = """
MATCH (n {{id: $entity_id}})-[*1..2]-(related)
WHERE related.state IS NOT NULL
RETURN COLLECT(DISTINCT related.state) AS states
"""

CYPHER_INCREMENT_FRAUD = """
MATCH (n {{id: $entity_id}})
SET n.fraud_count = COALESCE(n.fraud_count, 0) + 1,
    n.risk_score = $risk_score,
    n.last_seen = datetime()
"""


# ── Heuristic Risk Scorer (no GNN required) ───────────────────────

class HeuristicRiskScorer:
    """
    Computes fraud risk score from graph topology features.
    No ML model required — works purely from Neo4j query results.
    """

    def score(
        self,
        fraud_count: int,
        report_count: int,
        fraud_neighbors: int,
        stored_score: Optional[float],
    ) -> float:
        """Returns a 0-1 risk score."""
        # Stored score if recently computed by GNN
        if stored_score is not None and stored_score > 0:
            return stored_score

        # Heuristic scoring
        base = 0.0

        # Direct fraud involvement
        if fraud_count >= 5:
            base += 0.60
        elif fraud_count >= 2:
            base += 0.40
        elif fraud_count >= 1:
            base += 0.20

        # Complaint volume
        if report_count >= 10:
            base += 0.25
        elif report_count >= 3:
            base += 0.15

        # Network contamination (friends of fraudsters)
        if fraud_neighbors >= 5:
            base += 0.20
        elif fraud_neighbors >= 2:
            base += 0.10

        return round(min(base, 0.99), 4)


# ── GNN Risk Scorer (optional, requires trained model) ────────────

class GNNRiskScorer:
    """
    GraphSAGE-based node risk scorer.
    Falls back to HeuristicRiskScorer if model not available.
    """

    def __init__(self, model_path: Optional[str] = None):
        self._model = None
        self._model_path = model_path
        self._fallback = HeuristicRiskScorer()

    def load(self):
        if not self._model_path:
            return
        try:
            from pathlib import Path
            import torch
            path = Path(self._model_path)
            if path.exists():
                self._model = torch.load(str(path), map_location="cpu")
                self._model.eval()
                print(f"[GNNScorer] Model loaded from {path}")
        except Exception as e:
            print(f"[GNNScorer] Load failed ({e}), using heuristic fallback")

    def score_from_features(self, node_features: List[float]) -> float:
        """Score a single node from its feature vector."""
        if self._model is None:
            return 0.0
        torch = _lazy_torch()
        try:
            x = torch.tensor([node_features], dtype=torch.float32)
            with torch.no_grad():
                out = self._model(x)
                prob = torch.sigmoid(out).item()
            return round(prob, 4)
        except Exception as e:
            print(f"[GNNScorer] Inference error: {e}")
            return 0.0


# ── Neo4j Graph Manager ───────────────────────────────────────────

class FraudGraphManager:
    """
    Manages all Neo4j interactions for the fraud graph.
    Provides async methods for CRUD + traversal + risk scoring.
    """

    def __init__(self, uri: str, user: str, password: str, gnn_model_path: Optional[str] = None):
        self._uri = uri
        self._user = user
        self._password = password
        self._driver = None
        self._gnn = GNNRiskScorer(gnn_model_path)
        self._heuristic = HeuristicRiskScorer()

    async def connect(self):
        try:
            driver_cls = _lazy_neo4j()
            self._driver = driver_cls.driver(
                self._uri,
                auth=(self._user, self._password),
            )
            # Verify connectivity
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            self._gnn.load()
            print("[FraudGraph] Neo4j connected")
        except Exception as e:
            print(f"[FraudGraph] Neo4j connection failed: {e}. Using mock mode.")
            self._driver = None

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def _run(self, query: str, **params) -> List[Dict]:
        """Execute a Cypher query and return list of record dicts."""
        if not self._driver:
            return []
        async with self._driver.session() as session:
            result = await session.run(query, **params)
            return [dict(record) async for record in result]

    async def upsert_entity(
        self,
        entity_id: str,
        entity_type: str,
        props: Dict[str, Any],
    ) -> bool:
        """Create or update a node in the fraud graph."""
        label = NODE_TYPES.get(entity_type, "Entity")
        try:
            await self._run(
                CYPHER_UPSERT_NODE.format(label=label),
                id=entity_id,
                props=props,
            )
            return True
        except Exception as e:
            print(f"[FraudGraph] upsert_entity error: {e}")
            return False

    async def upsert_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        props: Optional[Dict] = None,
    ) -> bool:
        """Create or update an edge."""
        if rel_type not in EDGE_TYPES:
            return False
        try:
            await self._run(
                CYPHER_UPSERT_EDGE.format(rel_type=rel_type),
                source_id=source_id,
                target_id=target_id,
                props=props or {},
            )
            return True
        except Exception as e:
            print(f"[FraudGraph] upsert_relationship error: {e}")
            return False

    async def get_subgraph(
        self,
        entity_id: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Returns (nodes, edges) for the subgraph around an entity.
        """
        try:
            records = await self._run(
                CYPHER_GET_SUBGRAPH.format(depth=depth),
                entity_id=entity_id,
            )
            if not records:
                return [], []

            row = records[0]
            raw_nodes = row.get("all_nodes", [])
            raw_edges = row.get("all_edges", [])

            # Limit nodes
            raw_nodes = raw_nodes[:max_nodes]

            nodes = []
            for n in raw_nodes:
                props = dict(n) if hasattr(n, "items") else n
                nodes.append({
                    "id": props.get("id", ""),
                    "type": _infer_type(props),
                    "label": props.get("label", props.get("id", "")),
                    "risk_score": props.get("risk_score", 0.0),
                    "fraud_count": props.get("fraud_count", 0),
                    "first_seen": str(props.get("created_at", "")),
                    "last_seen": str(props.get("updated_at", "")),
                    "attributes": {k: v for k, v in props.items()
                                   if k not in ("id", "label", "risk_score", "fraud_count")},
                })

            edges = []
            for e in raw_edges:
                edges.append({
                    "source": e.get("source", ""),
                    "target": e.get("target", ""),
                    "relationship": e.get("type", ""),
                    "weight": EDGE_RISK_WEIGHTS.get(e.get("type", ""), 0.3),
                    "transaction_count": e.get("props", {}).get("transaction_count"),
                    "total_amount_inr": e.get("props", {}).get("total_amount_inr"),
                })

            return nodes, edges

        except Exception as e:
            print(f"[FraudGraph] get_subgraph error: {e}")
            return [], []

    async def get_risk_score(self, entity_id: str) -> float:
        """Compute or retrieve risk score for an entity."""
        try:
            records = await self._run(CYPHER_FRAUD_SCORE, entity_id=entity_id)
            if not records:
                return 0.0
            row = records[0]
            score = self._heuristic.score(
                fraud_count=row.get("fraud_count") or 0,
                report_count=row.get("report_count") or 0,
                fraud_neighbors=row.get("fraud_neighbors") or 0,
                stored_score=row.get("stored_risk_score"),
            )
            return score
        except Exception as e:
            print(f"[FraudGraph] get_risk_score error: {e}")
            return 0.0

    async def get_connected_cases(self, entity_id: str) -> List[str]:
        try:
            records = await self._run(CYPHER_CONNECTED_CASES, entity_id=entity_id)
            if records:
                return records[0].get("case_numbers", [])
            return []
        except Exception:
            return []

    async def get_states_involved(self, entity_id: str) -> List[str]:
        try:
            records = await self._run(CYPHER_STATES_INVOLVED, entity_id=entity_id)
            if records:
                return records[0].get("states", [])
            return []
        except Exception:
            return []

    async def register_fraud_event(
        self,
        entity_id: str,
        entity_type: str,
        scam_type: str,
        confidence: float,
        location: Optional[Dict] = None,
    ) -> None:
        """
        Called when a scam is confirmed. Updates entity risk score
        and links it into the fraud network.
        """
        # Upsert entity with updated fraud info
        props = {
            "label": entity_id,
            "scam_type": scam_type,
            "last_fraud_confidence": confidence,
        }
        if location:
            props["lat"] = location.get("lat")
            props["lng"] = location.get("lng")
            props["state"] = location.get("state")

        await self.upsert_entity(entity_id, entity_type, props)

        # Increment fraud count + recompute risk score
        new_score = await self.get_risk_score(entity_id)
        await self._run(
            CYPHER_INCREMENT_FRAUD,
            entity_id=entity_id,
            risk_score=new_score,
        )

    async def full_query(
        self,
        entity_id: str,
        entity_type: str,
        depth: int = 2,
        max_nodes: int = 50,
    ) -> Dict:
        """
        Complete fraud graph analysis for an entity.
        Returns data matching FraudGraphResponse schema.
        """
        t_start = time.perf_counter()

        nodes, edges = await self.get_subgraph(entity_id, depth, max_nodes)
        risk_score = await self.get_risk_score(entity_id)
        cases = await self.get_connected_cases(entity_id)
        states = await self.get_states_involved(entity_id)

        # Recommended action based on risk
        if risk_score >= 0.80:
            action = "⚠️ CRITICAL: Immediately block entity. Generate evidence package and file FIR."
        elif risk_score >= 0.60:
            action = "HIGH RISK: Flag for investigation. Monitor transactions and linked accounts."
        elif risk_score >= 0.40:
            action = "MEDIUM: Add to watchlist. Correlate with upcoming complaints."
        else:
            action = "LOW: No immediate action. Continue monitoring."

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "risk_score": risk_score,
            "fraud_network_size": len(nodes),
            "nodes": nodes,
            "edges": edges,
            "connected_cases": cases,
            "states_involved": states,
            "recommended_action": action,
            "processing_time_ms": elapsed_ms,
        }


def _infer_type(props: Dict) -> str:
    """Infer node type from property keys."""
    if "phone" in str(props.get("id", "")).lower() or re.match(r"^\+?\d{10,}", str(props.get("id", ""))):
        return "phone_number"
    if "ACC" in str(props.get("id", "")).upper():
        return "bank_account"
    return "person"


import re  # noqa: E402 (needed for _infer_type)


# ── Module-level singleton ────────────────────────────────────────
_graph_manager: Optional[FraudGraphManager] = None


def get_fraud_graph_manager(
    uri: str = "bolt://localhost:7687",
    user: str = "neo4j",
    password: str = "neo4j_pass",
    gnn_model_path: Optional[str] = None,
) -> FraudGraphManager:
    global _graph_manager
    if _graph_manager is None:
        _graph_manager = FraudGraphManager(uri, user, password, gnn_model_path)
    return _graph_manager
