"""Ground truth (mục 15.2 / 18.4).

`true_impact` là BẢN THAM CHIẾU để bộ sinh kịch bản chạy được (P3.4 phụ thuộc P2.5).
P2 có thể thay thế bằng hàm của mình miễn giữ chữ ký:
    true_impact(graph_full, root, severity) -> {node_id: mức ảnh hưởng thật}
"""
from __future__ import annotations

import networkx as nx

from . import sim_params as SP
from .ontology import IMPACT_LAYERS
from .propagation import propagate


def true_impact(graph_full: nx.DiGraph, root: str, severity: float = 1.0) -> dict[str, float]:
    """Lan truyền theo trọng số THẬT của đồ thị đầy đủ (có cả WIP buffer ẩn)."""
    impact, *_ = propagate(graph_full, root, severity)
    return {k: round(v, 6) for k, v in impact.items()}


def forward_truth_from_impact(graph_full: nx.DiGraph, impact: dict[str, float],
                              threshold: float = SP.IMPACT_THRESHOLD) -> dict[str, list[str]]:
    """Tập đối tượng bị ảnh hưởng thật theo tầng (impact >= threshold), xếp giảm dần."""
    out = {t: [] for t in IMPACT_LAYERS}
    for n, v in sorted(impact.items(), key=lambda kv: -kv[1]):
        t = graph_full.nodes[n]["type"]
        if t in out and v >= threshold:
            out[t].append(n)
    return out
