"""Đồ thị tri thức + kịch bản sự cố từ dữ liệu nhà máy của nhóm (data/factory/).

Nguồn (xem data/factory/data_facts_team.md):
  incidents_all.csv     443 sự cố THẬT (AI4I 339, SECOM 104), đã gán node
  machines.csv          50 máy M01–M50 → 8 công đoạn P1–P8           (nhánh A, mô phỏng)
  routing.csv           2000 SP, mỗi bước: công đoạn, máy chính, máy dự phòng, linh kiện
  orders.csv            50.000 đơn hàng (qty, priority, due_date)
  routing_b.csv         500 SP nhánh B: công đoạn PB01–PB10 → linh kiện
  orders_b.csv          10.000 đơn hàng nhánh B

Thiết kế đồ thị:
  Nhánh A: Máy ─performs→ Công đoạn (ngữ cảnh)
           Máy ─produces→ Lô linh kiện "<component>@<máy>" ─component_of→ Sản phẩm ─fulfills→ Đơn hàng
     Linh kiện được tách theo máy chính, vì cùng mã linh kiện có thể làm trên nhiều máy:
     nếu nối Công đoạn→Linh kiện thì một máy hỏng sẽ "lan" sang sản phẩm làm trên máy khác.
  Nhánh B: Công đoạn ─produces→ Linh kiện ─component_of→ Sản phẩm ─fulfills→ Đơn hàng (không có tầng Máy).

Giả định (THAM SỐ MÔ PHỎNG, ghi trong báo cáo):
  - Trọng số cạnh = 1.0 (dữ liệu chưa có mức phụ thuộc).
  - priority: Cao 0.9 / Trung bình 0.6 / Thấp 0.3.  due_in_days tính từ AS_OF.
  - AI4I: anomaly_score = điểm bộ phát hiện chính của P1 (cột score_main) (p1_detection/outputs/p1_ai4i_scores.csv), detector "iforest".
    SECOM: anomaly_score = 1.0, detector = "label" (P2 chia SECOM theo thời gian, chỉ chấm test; chưa ánh xạ vào đây).
"""
from functools import lru_cache

import networkx as nx
import pandas as pd

from . import DATA_DIR, ROOT

FACTORY_DIR = DATA_DIR / "factory"
AS_OF = pd.Timestamp("2026-11-01")  # ngày tham chiếu tính hạn giao (đơn sớm nhất có hạn 2026-11-01)
PRIORITY = {"Cao": 0.9, "Trung bình": 0.6, "Thấp": 0.3}

MODE_INFO = {  # failure_mode → (loại bất thường, nhóm nguyên nhân nghi ngờ, mức độ)
    "TWF": ("Mòn dao", "Dao mòn quá hạn (tool wear ~200–250 phút)", "medium"),
    "HDF": ("Tản nhiệt kém", "Làm mát kém: chênh nhiệt < 8,6 K và tốc độ quay < 1380 rpm", "high"),
    "PWF": ("Lỗi công suất", "Công suất ngoài dải 3500–9000 W", "high"),
    "OSF": ("Quá tải mô-men", "Mòn dao × mô-men vượt ngưỡng theo loại máy", "high"),
    "RNF": ("Lỗi ngẫu nhiên", None, "low"),
    "UNKNOWN": ("Lỗi máy không rõ chế độ", None, "medium"),
    "SECOM_FAIL": ("Lô bán dẫn không đạt QC", "Bất thường trong 590 thông số quy trình", "high"),
}


def _read(name):
    path = FACTORY_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Thiếu {path}. Giải nén dữ liệu nhóm vào data/factory/ (xem README).")
    return pd.read_csv(path)


# ---------------------------------------------------------------- sự cố
P1_SCORES = ROOT / "p1_detection" / "outputs" / "p1_ai4i_scores.csv"


@lru_cache(maxsize=None)
def p1_scores():
    """Điểm Isolation Forest của P1 cho mọi dòng AI4I (index = UDI); None nếu chưa chạy P1."""
    if not P1_SCORES.exists():
        return None
    return pd.read_csv(P1_SCORES).set_index("UDI")


@lru_cache(maxsize=None)
def load_incidents():
    """443 sự cố thật → list[dict] theo incident.schema.json, sắp theo dataset rồi thời gian."""
    df = _read("incidents_all.csv")
    out = []
    for i, r in df.iterrows():
        dataset = r["dataset"].lower()
        modes = r["failure_mode"].split("+")
        main = next((m for m in ("OSF", "PWF", "HDF", "TWF") if m in modes), modes[0])  # chế độ nặng nhất
        a_type, cause, sev = MODE_INFO.get(main, MODE_INFO["UNKNOWN"])
        if len(modes) > 1:
            a_type += " (+" + ", ".join(m for m in modes if m != main) + ")"
        out.append({
            "incident_id": f"INC_{'A' if dataset == 'ai4i' else 'B'}{i:03d}",
            "timestamp": pd.Timestamp(r["timestamp"]).isoformat(),
            "timestamp_is_synthetic": bool(r["timestamp_is_fake"]),
            "dataset": dataset,
            "node_id": r["node_id"],
            "source_row": int(r["source_row"]),
            "anomaly_type": a_type,
            "failure_mode": r["failure_mode"],
            "severity": sev,
            "anomaly_score": _score(dataset, int(r["source_row"])),
            "detector": "iforest" if dataset == "ai4i" and p1_scores() is not None else "label",
            "suspected_cause_group": cause,
            "split": "test",
        })
    return tuple(out)


def _score(dataset, row):
    sc = p1_scores()
    if dataset != "ai4i" or sc is None:
        return 1.0
    return float(sc.at[row, "score_main"])


@lru_cache(maxsize=None)
def p1_alarms():
    """Cảnh báo Isolation Forest của P1 trên dòng KHÔNG lỗi (báo sai) → dùng làm nhiễu thật cho E3."""
    sc = p1_scores()
    if sc is None:
        return ()
    fa = sc[sc.alarm_main & (sc.machine_failure == 0)]
    return tuple({"incident_id": f"INC_FA{udi:05d}", "timestamp": pd.Timestamp(r.timestamp).isoformat(),
                  "timestamp_is_synthetic": True, "dataset": "ai4i", "node_id": r.machine_id,
                  "source_row": int(udi), "anomaly_type": "Bất thường cảm biến (báo sai)", "failure_mode": None,
                  "severity": "low", "anomaly_score": float(r.score_main), "detector": "iforest",
                  "suspected_cause_group": None, "split": r.split} for udi, r in fa.iterrows())


# ---------------------------------------------------------------- đồ thị
def _add_orders(G, orders):
    for o in orders.itertuples(index=False):
        G.add_node(o.order_id, type="order", label=f"{o.order_id} · {o.qty} sp", department="sales",
                   priority=PRIORITY.get(o.priority, 0.5), priority_label=o.priority, qty=int(o.qty),
                   due_in_days=int((pd.Timestamp(o.due_date) - AS_OF).days), due_date=o.due_date)
        G.add_edge(o.product_id, o.order_id, relation="fulfills", weight=1.0)


def _add_products(G, routing, orders, prefix_label):
    n_orders = orders.groupby("product_id").size()
    qty = orders.groupby("product_id").qty.sum()
    for p in routing.product_id.unique():
        G.add_node(p, type="product", label=prefix_label + p, department="planning",
                   n_orders=int(n_orders.get(p, 0)), qty_total=int(qty.get(p, 0)))


@lru_cache(maxsize=None)
def build_graph(branch):
    """branch 'A' (AI4I) hoặc 'B' (SECOM) → networkx.DiGraph theo graph.schema.json."""
    G = nx.DiGraph()
    G.graph["meta"] = {"seed": 42, "size": "large", "view": "full", "edge_drop_rate": 0.0,
                       "generator": f"factory.build_graph@v1/{branch}"}
    if branch == "A":
        machines, routing, orders = _read("machines.csv"), _read("routing.csv"), _read("orders.csv")
        alts = routing.groupby("machine_id").backup_machine_id.agg(lambda s: sorted(set(s)))
        ai4i = _read("ai4i_assigned.csv").groupby("machine_id").agg(type=("Type", lambda s: s.mode()[0]),
                                                                    rows=("UDI", list))
        for m in machines.itertuples(index=False):
            pid = m.process.split()[0]
            G.add_node(pid, type="process", label=m.process, department="production", branch="A")
            G.add_node(m.machine_id, type="machine", label=f"Máy {m.machine_id}", department="maintenance",
                       branch="A", machine_type=ai4i.type.get(m.machine_id),
                       alt_machines=alts.get(m.machine_id, []), process=pid,
                       data_rows=[int(x) for x in ai4i.rows.get(m.machine_id, [])])
            G.add_edge(m.machine_id, pid, relation="performs", weight=1.0)
        _add_products(G, routing, orders, "Sản phẩm ")
        for r in routing.itertuples(index=False):
            part = f"{r.component_id}@{r.machine_id}"
            if part not in G:
                G.add_node(part, type="part", label=f"Linh kiện {r.component_id} (máy {r.machine_id})",
                           department="warehouse", component_id=r.component_id, process=r.process.split()[0])
                G.add_edge(r.machine_id, part, relation="produces", weight=1.0)
            G.add_edge(part, r.product_id, relation="component_of", weight=1.0)
        _add_orders(G, orders)
    elif branch == "B":
        routing, orders = _read("routing_b.csv"), _read("orders_b.csv")
        for p in sorted(routing.process_id.unique()):
            G.add_node(p, type="process", label=f"Công đoạn {p}", department="production", branch="B")
        _add_products(G, routing, orders, "Sản phẩm ")
        for r in routing.itertuples(index=False):
            if r.component_id not in G:
                G.add_node(r.component_id, type="part", label=f"Linh kiện {r.component_id}",
                           department="warehouse", process=r.process_id)
                G.add_edge(r.process_id, r.component_id, relation="produces", weight=1.0)
            G.add_edge(r.component_id, r.product_id, relation="component_of", weight=1.0)
        _add_orders(G, orders)
    else:
        raise ValueError(branch)
    return G


# ---------------------------------------------------------------- kịch bản
def incidents_for(dataset):
    return [i for i in load_incidents() if i["dataset"] == dataset]


def real_scenario(seed, config):
    """Kịch bản trên dữ liệu thật. seed chọn sự cố gốc (seed % số sự cố), hoặc config['incident_id'].

    Nhiễu (confounder) KHÔNG tự tiêm: là các sự cố thật khác xảy ra trong cửa sổ thời gian
    config['window_hours'] (mặc định 2h) trước sự cố gốc, cùng nhánh.
    config['confounders'] = "alarms" (chỉ AI4I): thêm cả cảnh báo SAI của detector P1 trong cửa sổ đó.
    """
    from .mock import _drop_edges, true_impact  # dùng chung với bộ sinh mock
    import random

    dataset = config.get("dataset", "ai4i")
    pool = incidents_for(dataset)
    root = next((i for i in pool if i["incident_id"] == config.get("incident_id")), None) or pool[seed % len(pool)]
    G = build_graph("A" if dataset == "ai4i" else "B")

    t0 = pd.Timestamp(root["timestamp"])
    win = pd.Timedelta(hours=config.get("window_hours", 2))
    others = [dict(i, is_confounder=True) for i in pool
              if i is not root and i["node_id"] != root["node_id"]
              and t0 - win <= pd.Timestamp(i["timestamp"]) <= t0]
    if config.get("confounders") == "alarms" and dataset == "ai4i":  # + báo sai của detector P1
        others += [dict(i, is_confounder=True) for i in p1_alarms()
                   if i["node_id"] != root["node_id"] and t0 - win <= pd.Timestamp(i["timestamp"]) <= t0]
    incidents = [dict(root, is_confounder=False)] + others

    impact = true_impact(G, root["node_id"])
    orders = [n for n in impact if G.nodes[n]["type"] == "order"]
    # kết quả xấu = đơn bị ảnh hưởng gấp nhất (ưu tiên cao, hạn sớm)
    bad = min(orders, key=lambda n: (-G.nodes[n]["priority"], G.nodes[n]["due_in_days"], n)) if orders else None
    return {
        "graph_full": G,
        "graph_observed": _drop_edges(G, config.get("edge_drop_rate", 0.0), random.Random(seed))
        if config.get("edge_drop_rate") else G,
        "incidents": incidents,
        "root_incident": incidents[0],
        "bad_outcome_node": bad,
        "forward_truth": set(impact),
        "backward_truth": root["node_id"],
        "true_impact": impact,
    }
