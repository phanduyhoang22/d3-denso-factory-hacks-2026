"""Bản GIẢ (mock) của các module P1–P4, đúng interface trong contracts.py.

Chạy trên dữ liệu nhà máy của nhóm (data/factory/, từ file zip). Ai có module thật thì registry tự thay.
KHÔNG dùng kết quả từ mock cho báo cáo — runner ghi cột `impl` để phân biệt mock/real.
"""
import networkx as nx


# ---------------------------------------------------------------- P3: bộ sinh kịch bản
def true_impact(G, root):
    """Mức ảnh hưởng thật = max tích trọng số trên mọi đường từ root (mục 18.4). Tính trên graph_full."""
    impact = {root: 1.0}
    for n in nx.topological_sort(G):
        if n not in impact:
            continue
        for v in G.successors(n):
            impact[v] = max(impact.get(v, 0.0), impact[n] * G[n][v]["weight"])
    impact.pop(root)
    return impact


def _drop_edges(G, rate, rng):
    H = G.copy()
    H.graph["meta"] = {**G.graph["meta"], "view": "observed", "edge_drop_rate": rate}
    droppable = [(u, v) for u, v, d in H.edges(data=True) if d["relation"] != "monitors"]
    H.remove_edges_from(rng.sample(droppable, k=int(round(rate * len(droppable)))))
    return H


def generate_scenario(seed, config):
    """Một sự cố thật làm sự cố gốc (xem factory.real_scenario)."""
    from .factory import real_scenario
    return real_scenario(seed, config)


# ---------------------------------------------------------------- P3: truy vết xuôi
def forward_trace(G, incident):
    root = incident["node_id"]
    if root not in G:
        return []
    paths = nx.single_source_shortest_path(G, root)
    return [{"node_id": n, "type": G.nodes[n]["type"], "depth": len(p) - 1, "path": p}
            for n, p in sorted(paths.items(), key=lambda kv: len(kv[1])) if n != root]


# ---------------------------------------------------------------- P4: chấm rủi ro
def _path_weight(G, path):
    w = 1.0
    for u, v in zip(path, path[1:]):
        w *= G[u][v]["weight"]
    return w


def risk_score(G, forward, incident):
    """risk = tích trọng số đường đi × điểm bất thường × hệ số nghiệp vụ (0–1) theo loại node.

    process: 1.0 · part: 0.7 + 0.3·khan hiếm · product: 0.4 + 0.6·(qty / qty lớn nhất bị ảnh hưởng)
    order: 0.3 + 0.4·priority + 0.3·urgency, urgency = max(0, 1 − hạn giao / 30 ngày)
    """
    qty_max = max((G.nodes[f["node_id"]].get("qty_total", 0) for f in forward
                   if f["type"] == "product"), default=0) or 1
    rows = []
    for f in forward:
        n, a = f["node_id"], G.nodes[f["node_id"]]
        base = _path_weight(G, f["path"]) * incident["anomaly_score"]
        t = a["type"]
        if t == "part":
            if "spare_inventory" in a or "n_suppliers" in a:
                scarce = a.get("spare_inventory", 9) < 2 or a.get("n_suppliers", 9) <= 1
                factor, reason = (1.0, "Ít nguồn thay thế, tồn kho thấp") if scarce else (0.7, "Có tồn kho/nguồn thay thế")
            else:
                factor, reason = 0.85, "Chưa có dữ liệu tồn kho"
        elif t == "product":
            if "qty_total" in a:
                factor = 0.4 + 0.6 * a["qty_total"] / qty_max
                reason = f"{a.get('n_orders', 0)} đơn, {a['qty_total']:,} sp đang đặt"
            else:
                factor, reason = 0.75, "Phụ thuộc linh kiện bị ảnh hưởng"
        elif t == "order":
            due = a.get("due_in_days", 30)
            urgency = max(0.0, 1 - due / 30)
            factor = 0.3 + 0.4 * a.get("priority", 0.5) + 0.3 * urgency
            reason = f"Ưu tiên {a.get('priority_label') or a.get('priority')}, hạn {due} ngày"
        else:
            factor = 1.0
            reason = "Phụ thuộc trực tiếp" if f["depth"] == 1 else f"Cách {f['depth']} bước"
        rows.append({"node_id": n, "type": t, "risk_score": round(min(base * factor, 1.0), 3), "reason": reason})
    return sorted(rows, key=lambda r: (-r["risk_score"], r["node_id"]))


# ---------------------------------------------------------------- P1: truy vết ngược
def backward_trace(G, incidents, bad_outcome_node, k=3):
    if bad_outcome_node in G:
        ancestors = nx.ancestors(G, bad_outcome_node)
        cands = [i for i in incidents if i["node_id"] in ancestors] or incidents
    else:
        cands = incidents
    scored = []
    for inc in cands:
        try:
            path = nx.shortest_path(G, inc["node_id"], bad_outcome_node)
            w = _path_weight(G, path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            w = 0.1
        scored.append((inc["anomaly_score"] * w, inc))
    total = sum(s for s, _ in scored) or 1.0
    scored.sort(key=lambda t: -t[0])
    return [{"rank": r + 1, "node_id": inc["node_id"], "cause": f"{inc['node_id']}: {inc['suspected_cause_group']}",
             "score": round(s / total, 3), "evidence": [f"{inc['incident_id']} ({inc['anomaly_type']}, "
                                                       f"điểm {inc['anomaly_score']})"]}
            for r, (s, inc) in enumerate(scored[:k])]


# ---------------------------------------------------------------- P4: đề xuất hành động
def recommend(G, incident, risk, backward):
    actions = []

    def add(dept, text, target, rule):
        actions.append({"priority": len(actions) + 1, "department": dept, "action": text,
                        "target_node": target, "kb_rule_id": rule, "adoption_rate": None})

    top = backward[0]["node_id"] if backward else incident["node_id"]
    add("maintenance", f"Kiểm tra {top}: {incident.get('suspected_cause_group') or 'nguồn lỗi khả dĩ nhất'}",
        top, "R_INSPECT")
    alts = G.nodes[incident["node_id"]].get("alt_machines", []) if incident["node_id"] in G else []
    if alts:
        add("production", f"Chuyển một phần tải từ {incident['node_id']} sang máy dự phòng "
                          f"{', '.join(alts[:3])}", alts[0], "R_SHIFT_LOAD")
    elif G.nodes.get(incident["node_id"], {}).get("type") == "process":
        add("quality", f"Cách ly và kiểm tra lại các lô vừa qua công đoạn {incident['node_id']}",
            incident["node_id"], "R_QUARANTINE")

    # Gộp theo bộ phận để danh sách không dài hàng nghìn dòng: nêu tối đa 3 đối tượng rủi ro cao nhất
    def top(t, cond=lambda r: True):
        return [r for r in risk if r["type"] == t and r["risk_score"] >= 0.5 and cond(r)]

    def names(rs):
        return ", ".join(r["node_id"] for r in rs[:3]) + (f" và {len(rs) - 3} khác" if len(rs) > 3 else "")

    parts = top("part")
    stocked = [r for r in parts if G.nodes[r["node_id"]].get("spare_inventory", 0) > 0]
    if stocked:
        add("warehouse", "Xuất tồn kho dự phòng " + ", ".join(
            f"{r['node_id']} (còn {G.nodes[r['node_id']]['spare_inventory']} ngày)" for r in stocked[:3]),
            stocked[0]["node_id"], "R_USE_STOCK")
    elif parts:
        add("warehouse", f"Kiểm kê tồn kho linh kiện bị ảnh hưởng: {names(parts)}", parts[0]["node_id"], "R_CHECK_STOCK")
    products = top("product")
    if products:
        add("planning", f"Xếp lại lịch sản xuất {names(products)}", products[0]["node_id"], "R_RESCHEDULE")
    orders = top("order", lambda r: G.nodes[r["node_id"]].get("due_in_days", 99) <= 14)
    if orders:
        o = G.nodes[orders[0]["node_id"]]
        add("sales", f"Báo khách hàng nguy cơ trễ {len(orders)} đơn hạn ≤ 14 ngày, gấp nhất "
                     f"{orders[0]['node_id']} (hạn {o.get('due_in_days')} ngày)",
            orders[0]["node_id"], "R_NOTIFY")
    return actions


# ---------------------------------------------------------------- Baseline (mục 18.5)
def baseline_e1(G, incident):
    """Cảnh báo cục bộ: chỉ máy + công đoạn liền kề."""
    n = incident["node_id"]
    return {v for v in G.successors(n)} if n in G else set()


def baseline_e2(G, forward, incident):
    """Rủi ro chỉ theo số bước."""
    return sorted(({"node_id": f["node_id"], "risk_score": 1.0 / f["depth"]} for f in forward),
                  key=lambda r: -r["risk_score"])


def baseline_e3(incidents, k=3):
    """Chọn máy có điểm bất thường cao nhất, không dùng đồ thị."""
    return [i["node_id"] for i in sorted(incidents, key=lambda i: -i["anomaly_score"])[:k]]
