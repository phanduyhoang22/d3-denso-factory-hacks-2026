"""P1.5 – Truy vết ngược dùng chung 2 nhánh + baseline E3 (P2).

Điểm = điểm_bất_thường × (λ + (1−λ)·reach), λ = 0,5 (đặt TRƯỚC khi chạy, cùng công thức với
p2_experiments.backward_trace để hai nhánh thống nhất).
  reach = tích trọng số trên đường mạnh nhất từ node ứng viên tới kết quả xấu trong đồ thị NHÌN THẤY;
          0 nếu không nối được (cạnh bị thiếu) → ứng viên vẫn được xếp theo điểm bất thường (suy giảm êm).
Chỉ nói "nguyên nhân khả dĩ"; `score` là điểm tương đối, không phải xác suất.
"""
import networkx as nx

LAMBDA = 0.5


def _reach(G, src, dst):
    if src not in G or dst not in G:
        return 0.0
    try:
        path = nx.shortest_path(G, src, dst)
    except nx.NetworkXNoPath:
        return 0.0
    w = 1.0
    for u, v in zip(path, path[1:]):
        w *= G[u][v].get("weight", 1.0)
    return w


def backward_trace(G, incidents, bad_outcome_node, k=3):
    best = {}
    for inc in incidents:  # mỗi node giữ cảnh báo có điểm cao nhất
        n = inc["node_id"]
        if n and (n not in best or inc["anomaly_score"] > best[n]["anomaly_score"]):
            best[n] = inc
    scored = []
    for n, inc in best.items():
        reach = _reach(G, n, bad_outcome_node) if bad_outcome_node else 0.0
        score = inc["anomaly_score"] * (LAMBDA + (1 - LAMBDA) * reach)
        scored.append((score, reach, n, inc))
    scored.sort(key=lambda t: (-t[0], t[2]))
    return [{"rank": i + 1, "node_id": n,
             "cause": f"{n}: {inc.get('suspected_cause_group') or inc.get('anomaly_type')}",
             "score": round(s, 4),
             "evidence": [f"{inc['incident_id']} · {inc['anomaly_type']} · điểm bất thường {inc['anomaly_score']:.2f}",
                          "nối được tới kết quả xấu trên đồ thị" if reach > 0 else "không nối được tới kết quả xấu"]}
            for i, (s, reach, n, inc) in enumerate(scored[:k])]


def baseline_e3(incidents, k=3):
    """Baseline E3: node có điểm bất thường cao nhất, không dùng đồ thị."""
    order = sorted(incidents, key=lambda i: (-i["anomaly_score"], i["node_id"] or ""))
    return list(dict.fromkeys(i["node_id"] for i in order))[:k]
