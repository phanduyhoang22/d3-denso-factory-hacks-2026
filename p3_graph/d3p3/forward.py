"""P3.5 – Truy vết xuôi & P3.6 – Baseline E1.

forward_trace(graph_observed, root, severity) -> dict theo schema schemas/forward_trace.schema.json
"""
from __future__ import annotations

import networkx as nx

from . import sim_params as SP
from .ontology import FEEDS, IMPACT_LAYERS, MACHINE, OPERATES_IN, PROCESS, VN_NAME
from .propagation import path_to, propagate


def forward_trace(G: nx.DiGraph, root: str, severity: float = 1.0,
                  threshold: float = SP.IMPACT_THRESHOLD, max_hops: int | None = None) -> dict:
    """Đi xuôi theo cạnh phụ thuộc từ node sự cố (Máy hoặc Công đoạn).

    Trả về mọi đối tượng hạ nguồn kèm mức ảnh hưởng ước lượng, số bước và đường đi
    mạnh nhất; `by_layer` chỉ giữ đối tượng có est_impact >= threshold.
    """
    impact, strength, parent, hops = propagate(G, root, severity, max_hops)
    affected = []
    for n, v in sorted(impact.items(), key=lambda kv: (-kv[1], kv[0])):
        t = G.nodes[n]["type"]
        if t not in IMPACT_LAYERS:
            continue
        affected.append({
            "node_id": n, "type": t, "type_vn": VN_NAME[t],
            "est_impact": round(v, 4), "hops": hops[n],
            "path": path_to(parent, root, n), "path_strength": round(strength[n], 4),
            "above_threshold": v >= threshold,
        })
    by_layer = {t: [a["node_id"] for a in affected if a["type"] == t and a["above_threshold"]]
                for t in IMPACT_LAYERS}
    order_paths = [" → ".join(a["path"]) for a in affected if a["type"] == "order" and a["above_threshold"]]
    return {
        "method": "forward_trace",
        "root": root, "root_type": G.nodes[root]["type"] if root in G else None,
        "severity": severity, "threshold": threshold,
        "affected": affected, "by_layer": by_layer, "order_paths": order_paths,
    }


def baseline_e1(G: nx.DiGraph, root: str) -> dict:
    """Cảnh báo cục bộ: chỉ báo công đoạn liền kề của node lỗi, không đi tiếp (mục 18.5)."""
    nbrs = []
    if root in G:
        etype = OPERATES_IN if G.nodes[root]["type"] == MACHINE else FEEDS
        nbrs = sorted(v for v in G.successors(root) if G.edges[root, v]["type"] == etype
                      and G.nodes[v]["type"] == PROCESS)
    affected = [{"node_id": v, "type": PROCESS, "type_vn": VN_NAME[PROCESS], "est_impact": 1.0, "hops": 1,
                 "path": [root, v], "path_strength": 1.0, "above_threshold": True} for v in nbrs]
    by_layer = {t: [] for t in IMPACT_LAYERS}
    by_layer[PROCESS] = nbrs
    return {"method": "baseline_e1_local", "root": root, "severity": None, "threshold": None,
            "affected": affected, "by_layer": by_layer, "order_paths": []}


def format_trace(tr: dict, top: int = 15) -> str:
    """In gọn kết quả truy vết (dùng cho demo / log)."""
    lines = [f"Truy vết xuôi từ {tr['root']} (severity={tr['severity']}, ngưỡng={tr['threshold']})"]
    for t in IMPACT_LAYERS:
        ids = tr["by_layer"][t]
        lines.append(f"  {VN_NAME[t]:<10}: {', '.join(ids) if ids else '—'}")
    lines.append("  Đường đi tới đơn hàng:")
    for p in tr["order_paths"][:top]:
        lines.append(f"    {p}")
    return "\n".join(lines)
