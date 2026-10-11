"""Bản THAM CHIẾU cho phần của người khác, chỉ để P3 chạy được E4 (lặp E1–E3).

* risk_score_ref      – thay bằng risk_score() của P4 (E2)
* backward_trace_ref  – thay bằng backward_trace() của P1 (E3), theo phương án dự phòng C4:
                        khoảng cách/độ mạnh đường đi trên đồ thị + tần suất lỗi lịch sử (train)
* baseline_e2         – xếp theo số bước (P4 sở hữu, viết lại ở đây cho đủ bảng E4)
* baseline_e3_*       – chọn theo điểm bất thường cao nhất / gần nhất theo thời gian (P2 sở hữu)
Giữ đúng chữ ký để runner gọi được khi đổi sang hàm thật.
"""
from __future__ import annotations

from collections import deque

import networkx as nx

from .ontology import IMPACT_LAYERS
from .propagation import propagate, propagation_view


def risk_score_ref(trace: dict) -> dict[str, float]:
    """Điểm rủi ro tạm = mức ảnh hưởng ước lượng của truy vết xuôi."""
    return {a["node_id"]: a["est_impact"] for a in trace["affected"]}


def baseline_e2(G: nx.DiGraph, root: str) -> dict[str, float]:
    """Điểm rủi ro chỉ theo số bước trên đồ thị: 1 / hops."""
    P = propagation_view(G)
    if root not in P:
        return {}
    hops = {root: 0}
    dq = deque([root])
    while dq:
        u = dq.popleft()
        for v in P.successors(u):
            if v not in hops:
                hops[v] = hops[u] + 1
                dq.append(v)
    return {n: 1.0 / h for n, h in hops.items() if h > 0 and G.nodes[n]["type"] in IMPACT_LAYERS}


def _before(incidents, t_bad):
    return [i for i in incidents if i["timestamp"] < t_bad]


def backward_trace_ref(G: nx.DiGraph, incidents: list[dict], bad_outcome: dict,
                       w_reach=0.6, w_hist=0.25, w_anom=0.15) -> list[dict]:
    """Xếp hạng node nguồn khả dĩ cho kết quả xấu. Chỉ xét sự cố xảy ra TRƯỚC kết quả xấu."""
    bad, t_bad = bad_outcome["node_id"], bad_outcome["timestamp"]
    cands = {}
    for inc in _before(incidents, t_bad):
        n = inc["node_id"]
        if n not in cands or inc["anomaly_score"] > cands[n]["anomaly_score"]:
            cands[n] = inc
    if not cands:
        return []
    hist = {n: G.nodes[n].get("hist_fail_rate", 0.0) for n in cands}
    hmax = max(hist.values()) or 1.0
    out = []
    for n, inc in cands.items():
        _, strength, _, _ = propagate(G, n, 1.0)
        reach = strength.get(bad, 0.0)
        reach_n = min(1.0, reach ** 0.25) if reach > 0 else 0.0  # nén thang để đường dài vẫn có điểm
        score = w_reach * reach_n + w_hist * hist[n] / hmax + w_anom * inc["anomaly_score"]
        out.append({"node_id": n, "incident_id": inc["incident_id"], "score": round(score, 4),
                    "reach": round(reach, 4), "hist_fail_rate": hist[n],
                    "anomaly_score": inc["anomaly_score"]})
    out.sort(key=lambda r: (-r["score"], r["node_id"]))
    return out


def baseline_e3_anomaly(incidents: list[dict], bad_outcome: dict) -> list[str]:
    c = sorted(_before(incidents, bad_outcome["timestamp"]), key=lambda i: (-i["anomaly_score"], i["node_id"]))
    return list(dict.fromkeys(i["node_id"] for i in c))


def baseline_e3_recent(incidents: list[dict], bad_outcome: dict) -> list[str]:
    c = sorted(_before(incidents, bad_outcome["timestamp"]), key=lambda i: (i["timestamp"], i["node_id"]), reverse=True)
    return list(dict.fromkeys(i["node_id"] for i in c))
