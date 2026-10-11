"""Lan truyền tác động trên DAG (noisy-OR có trọng số + bộ đệm).

impact(v) = (1 - buffer(v)) · [1 - Π_{u ∈ cha(v)} (1 - impact(u) · w(u, v))]

* buffer(Linh kiện) = tồn kho dự phòng hấp thụ (component_buffer).
* buffer(Công đoạn) = wip_buffer_true – CHỈ có trong graph_full (hệ thống không biết).

Cùng một hàm được dùng cho:
* true_impact()  – trên graph_full (trọng số thật, đủ cạnh, có WIP buffer)
* forward_trace() – trên graph_observed (trọng số nhiễu, thiếu cạnh, không có WIP buffer)
Sự khác biệt giữa 2 đồ thị chính là thứ E1/E2/E4 đo.
"""
from __future__ import annotations

from collections import deque

import networkx as nx

from .graph import component_buffer
from .ontology import COMPONENT, PROCESS, PROPAGATION_EDGES


def propagation_view(G: nx.DiGraph) -> nx.DiGraph:
    return nx.subgraph_view(G, filter_edge=lambda u, v: G.edges[u, v]["type"] in PROPAGATION_EDGES)


def node_buffer(G: nx.DiGraph, v: str) -> float:
    d = G.nodes[v]
    if d["type"] == COMPONENT:
        usage = max(1, d.get("daily_usage", 1))
        return component_buffer(d.get("safety_stock", 0) / usage, d.get("lead_time_days", 1))
    if d["type"] == PROCESS:
        return float(d.get("wip_buffer_true", 0.0))
    return 0.0


def propagate(G: nx.DiGraph, root: str, severity: float = 1.0, max_hops: int | None = None):
    """Trả về (impact, strength, parent, hops) cho mọi hậu duệ của root.

    impact:   mức ảnh hưởng ước lượng (0..1)
    strength: tích trọng số lớn nhất theo 1 đường đi (để chọn đường đi tiêu biểu)
    parent:   cha trên đường đi mạnh nhất
    hops:     số bước ngắn nhất từ root
    """
    P = propagation_view(G)
    if root not in P:
        return {}, {}, {}, {}
    # BFS để lấy hops và tập hậu duệ (có giới hạn bước nếu cần)
    hops = {root: 0}
    dq = deque([root])
    while dq:
        u = dq.popleft()
        if max_hops is not None and hops[u] >= max_hops:
            continue
        for v in P.successors(u):
            if v not in hops:
                hops[v] = hops[u] + 1
                dq.append(v)
    reach = set(hops)
    sub = P.subgraph(reach)
    impact = {root: float(severity)}
    strength = {root: 1.0}
    parent = {root: None}
    for v in nx.topological_sort(sub):
        if v == root:
            continue
        keep = 1.0
        best, best_u = 0.0, None
        for u in sub.predecessors(v):
            if u not in impact:
                continue
            w = G.edges[u, v]["weight"]
            keep *= 1.0 - impact[u] * w
            s = strength[u] * w
            if s > best:
                best, best_u = s, u
        if best_u is None:
            continue
        impact[v] = (1.0 - node_buffer(G, v)) * (1.0 - keep)
        strength[v], parent[v] = best, best_u
    del impact[root], strength[root], parent[root]
    hops.pop(root)
    hops = {k: v for k, v in hops.items() if k in impact}
    return impact, strength, parent, hops


def path_to(parent: dict, root: str, v: str) -> list[str]:
    path = [v]
    while path[-1] != root:
        p = parent.get(path[-1])
        if p is None:
            path.append(root)
            break
        path.append(p)
    return path[::-1]
