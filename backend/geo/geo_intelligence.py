"""
SafeNet AI – Geospatial Intelligence Engine
----------------------------------------------
Provides:
  - H3 hexagonal grid indexing for crime clustering
  - DBSCAN-based incident clustering
  - Risk score computation per H3 cell
  - Patrol zone optimisation hints
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

# Lazy imports
_h3 = None
_sklearn = None


def _lazy_h3():
    global _h3
    if _h3 is None:
        import h3
        _h3 = h3
    return _h3


def _lazy_sklearn():
    global _sklearn
    if _sklearn is None:
        from sklearn.cluster import DBSCAN
        from sklearn.preprocessing import StandardScaler
        _sklearn = {"DBSCAN": DBSCAN, "StandardScaler": StandardScaler}
    return _sklearn


# ── H3 Geo Engine ─────────────────────────────────────────────────

class H3GeoEngine:
    """
    H3 hexagonal binning: groups incidents into geographic cells.
    Resolution 7 ≈ 5 km², good for city-level enforcement zones.
    Resolution 9 ≈ 0.1 km², good for block-level patrol.
    """

    RESOLUTION_AREAS = {
        4: "150 km²",
        5: "25 km²",
        6: "4 km²",
        7: "0.74 km²",
        8: "0.09 km²",
        9: "0.01 km²",
        10: "0.001 km²",
    }

    def __init__(self, default_resolution: int = 7):
        self.default_resolution = default_resolution

    def lat_lng_to_h3(self, lat: float, lng: float, resolution: Optional[int] = None) -> str:
        """Convert a coordinate to H3 cell index."""
        h3 = _lazy_h3()
        res = resolution or self.default_resolution
        # H3 v4 API
        return h3.latlng_to_cell(lat, lng, res)

    def h3_to_center(self, h3_index: str) -> Tuple[float, float]:
        """Returns (lat, lng) of H3 cell center."""
        h3 = _lazy_h3()
        # H3 v4: cell_to_latlng returns (lat, lng)
        return h3.cell_to_latlng(h3_index)

    def h3_to_boundary(self, h3_index: str) -> List[Tuple[float, float]]:
        """Returns polygon boundary vertices for a cell."""
        h3 = _lazy_h3()
        return h3.cell_to_boundary(h3_index)

    def get_neighbours(self, h3_index: str, k: int = 1) -> List[str]:
        """K-ring neighbours for patrol zone expansion."""
        h3 = _lazy_h3()
        return list(h3.grid_disk(h3_index, k))

    def bin_incidents(
        self,
        incidents: List[Dict],
        resolution: Optional[int] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Group incidents into H3 cells.
        incidents: list of dicts with 'lat', 'lng', and other fields.
        Returns: {h3_index: [incident, ...]}
        """
        bins: Dict[str, List[Dict]] = {}
        for inc in incidents:
            lat = inc.get("lat") or inc.get("location_lat")
            lng = inc.get("lng") or inc.get("location_lng")
            if lat is None or lng is None:
                continue
            try:
                cell = self.lat_lng_to_h3(float(lat), float(lng), resolution)
                bins.setdefault(cell, []).append(inc)
            except Exception:
                continue
        return bins

    def compute_cluster_risk(
        self,
        incidents: List[Dict],
        h3_index: str,
    ) -> float:
        """
        0-1 risk score for an H3 cell based on incident density + recency.
        """
        if not incidents:
            return 0.0

        count = len(incidents)
        # Recency boost: incidents in last 7 days count double
        now = datetime.utcnow()
        recency_score = 0.0
        for inc in incidents:
            ts = inc.get("created_at")
            if isinstance(ts, datetime):
                days_ago = (now - ts).days
                if days_ago <= 7:
                    recency_score += 2.0
                elif days_ago <= 30:
                    recency_score += 1.0
                else:
                    recency_score += 0.3

        # Normalise
        density_score = min(count / 20.0, 1.0)              # 20+ incidents → max density
        recency_normalised = min(recency_score / (count * 2), 1.0)

        risk = 0.6 * density_score + 0.4 * recency_normalised
        return round(min(risk, 1.0), 4)


class DBSCANClusterer:
    """
    DBSCAN-based geographic clustering for identifying hotspot zones.
    More flexible than H3 for irregularly shaped hotspots.
    """

    def __init__(self, eps_km: float = 2.0, min_samples: int = 3):
        """
        eps_km: neighbourhood radius in km (converted to radians internally)
        min_samples: minimum incidents to form a cluster
        """
        self.eps_km = eps_km
        self.min_samples = min_samples

    def cluster(self, points: List[Tuple[float, float]]) -> List[int]:
        """
        Returns cluster label for each point (-1 = noise/outlier).
        points: list of (lat, lng)
        """
        if len(points) < self.min_samples:
            return [-1] * len(points)

        sklearn = _lazy_sklearn()
        coords = np.array([[p[0], p[1]] for p in points])

        # Convert km epsilon to radians (for haversine metric)
        eps_rad = self.eps_km / 6371.0

        db = sklearn["DBSCAN"](
            eps=eps_rad,
            min_samples=self.min_samples,
            algorithm="ball_tree",
            metric="haversine",
        )
        # haversine expects lat/lng in radians
        coords_rad = np.radians(coords)
        labels = db.fit_predict(coords_rad)
        return labels.tolist()

    def get_cluster_centroids(
        self,
        points: List[Tuple[float, float]],
        labels: List[int],
    ) -> Dict[int, Tuple[float, float]]:
        """Returns centroid (lat, lng) for each cluster."""
        cluster_points: Dict[int, List[Tuple[float, float]]] = {}
        for point, label in zip(points, labels):
            if label >= 0:
                cluster_points.setdefault(label, []).append(point)

        centroids = {}
        for label, pts in cluster_points.items():
            lats = [p[0] for p in pts]
            lngs = [p[1] for p in pts]
            centroids[label] = (sum(lats) / len(lats), sum(lngs) / len(lngs))
        return centroids


# ── Main Geo Intelligence Service ─────────────────────────────────

class GeoIntelligenceService:
    """
    High-level service combining H3 + DBSCAN for the heatmap API.
    """

    def __init__(self):
        self._h3_engine = H3GeoEngine()
        self._dbscan = DBSCANClusterer()

    def _dominant_type(self, incidents: List[Dict]) -> Optional[str]:
        """Most common scam_type in a cluster."""
        type_counts: Dict[str, int] = {}
        for inc in incidents:
            t = inc.get("scam_type") or inc.get("fraud_type")
            if t:
                type_counts[t] = type_counts.get(t, 0) + 1
        if not type_counts:
            return None
        return max(type_counts, key=type_counts.get)

    def generate_heatmap(
        self,
        scam_incidents: List[Dict],
        counterfeit_incidents: List[Dict],
        resolution: int = 7,
        bbox: Optional[List[float]] = None,
        days_back: int = 30,
    ) -> Dict:
        """
        Generate H3 heatmap data.

        Args:
            scam_incidents: list of scam report dicts with lat/lng
            counterfeit_incidents: list of counterfeit report dicts with lat/lng
            resolution: H3 resolution (4-10)
            bbox: optional [min_lng, min_lat, max_lng, max_lat] filter
            days_back: only include incidents from last N days

        Returns:
            dict with 'clusters' list and metadata
        """
        t_start = time.perf_counter()

        # Filter by date
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        scam_inc = [i for i in scam_incidents if _after_cutoff(i, cutoff)]
        count_inc = [i for i in counterfeit_incidents if _after_cutoff(i, cutoff)]

        # Filter by bbox
        if bbox and len(bbox) == 4:
            min_lng, min_lat, max_lng, max_lat = bbox
            scam_inc = [i for i in scam_inc if _in_bbox(i, min_lat, max_lat, min_lng, max_lng)]
            count_inc = [i for i in count_inc if _in_bbox(i, min_lat, max_lat, min_lng, max_lng)]

        # Bin into H3
        scam_bins = self._h3_engine.bin_incidents(scam_inc, resolution)
        count_bins = self._h3_engine.bin_incidents(count_inc, resolution)

        all_cells = set(scam_bins.keys()) | set(count_bins.keys())

        clusters = []
        for cell in all_cells:
            s_incidents = scam_bins.get(cell, [])
            c_incidents = count_bins.get(cell, [])
            all_incidents = s_incidents + c_incidents

            center_lat, center_lng = self._h3_engine.h3_to_center(cell)
            risk = self._h3_engine.compute_cluster_risk(all_incidents, cell)
            city, state = _extract_city_state(all_incidents)

            clusters.append({
                "h3_index": cell,
                "center": {"lat": center_lat, "lng": center_lng},
                "city": city,
                "state": state,
                "scam_count": len(s_incidents),
                "counterfeit_count": len(c_incidents),
                "risk_score": risk,
                "dominant_fraud_type": self._dominant_type(s_incidents),
            })

        # Sort by risk score descending
        clusters.sort(key=lambda x: x["risk_score"], reverse=True)

        elapsed_ms = int((time.perf_counter() - t_start) * 1000)

        return {
            "clusters": clusters,
            "total_incidents": len(scam_inc) + len(count_inc),
            "generated_at": datetime.utcnow().isoformat(),
            "bbox_used": bbox,
            "resolution": resolution,
            "processing_time_ms": elapsed_ms,
        }

    def get_patrol_priorities(
        self, clusters: List[Dict], top_n: int = 5
    ) -> List[Dict]:
        """
        Rank cells for patrol deployment.
        Combines risk score with incident velocity.
        """
        high_risk = [c for c in clusters if c["risk_score"] >= 0.60]
        high_risk.sort(key=lambda x: x["risk_score"], reverse=True)
        priorities = []
        for i, cell in enumerate(high_risk[:top_n]):
            priorities.append({
                "priority_rank": i + 1,
                "h3_index": cell["h3_index"],
                "center": cell["center"],
                "city": cell.get("city"),
                "state": cell.get("state"),
                "risk_score": cell["risk_score"],
                "dominant_type": cell.get("dominant_fraud_type"),
                "total_incidents": cell["scam_count"] + cell["counterfeit_count"],
                "recommended_units": max(1, int(cell["risk_score"] * 4)),
            })
        return priorities


# ── Helpers ───────────────────────────────────────────────────────

def _after_cutoff(incident: Dict, cutoff: datetime) -> bool:
    ts = incident.get("created_at")
    if not ts:
        return True  # unknown date — include
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return True
    return ts.replace(tzinfo=None) >= cutoff.replace(tzinfo=None)


def _in_bbox(
    incident: Dict,
    min_lat: float, max_lat: float,
    min_lng: float, max_lng: float,
) -> bool:
    lat = incident.get("lat") or incident.get("location_lat") or 0
    lng = incident.get("lng") or incident.get("location_lng") or 0
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def _extract_city_state(incidents: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
    for inc in incidents:
        city = inc.get("city")
        state = inc.get("state")
        if city or state:
            return city, state
    return None, None


# ── Module-level singleton ────────────────────────────────────────
_geo_service: Optional[GeoIntelligenceService] = None


def get_geo_service() -> GeoIntelligenceService:
    global _geo_service
    if _geo_service is None:
        _geo_service = GeoIntelligenceService()
    return _geo_service
