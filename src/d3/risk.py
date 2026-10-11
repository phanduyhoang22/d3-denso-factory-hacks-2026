"""P4.3 – Nối risk_score() của P4 (p4_risk_action/risk.py) với output truy vết xuôi thật.

Chuyển `forward` (schema trace_output) sang bảng forward của P4 (level, obj_id, hops, dep, product_id,
n_products), gọi đúng `risk.risk_score()` của P4, rồi đổi kết quả về schema. Công thức và hệ số: xem
p4_risk_action/risk_formula.md (risk = w^hops × dep × (a + b·c)), KHÔNG chỉnh ở đây.
"""
import sys
from functools import lru_cache

import pandas as pd

from . import ROOT
from .factory import _read

sys.path.insert(0, str(ROOT / "p4_risk_action"))
import risk as p4  # noqa: E402

LEVEL = {"process": "process", "part": "component", "product": "product", "order": "order"}
HOPS = {"A": dict(process=1, component=2, product=3, order=4), "B": dict(component=1, product=2, order=3)}


@lru_cache(maxsize=None)
def tables(branch):
    """routing, orders của nhánh + số bước mỗi sản phẩm."""
    if branch == "A":
        routing, orders, key = _read("routing.csv"), _read("orders.csv"), "machine_id"
    else:
        routing, orders, key = _read("routing_b.csv"), _read("orders_b.csv"), "process_id"
    n_steps = routing.groupby("product_id").step.max()
    return routing, orders, key, n_steps


def p4_forward(G, forward, incident):
    """forward (schema) → bảng forward của P4."""
    branch = "A" if incident["dataset"] == "ai4i" else "B"
    routing, orders, key, n_steps = tables(branch)
    node = incident["node_id"]
    step = routing[routing[key] == node].groupby("product_id").step.min()
    dep = ((n_steps.reindex(step.index) - step + 1) / n_steps.reindex(step.index)).to_dict()
    hops = HOPS[branch]
    affected = {f["node_id"]: f for f in forward}
    rows = []
    for nid, f in affected.items():
        lvl = LEVEL.get(f["type"])
        if lvl is None or lvl not in hops:
            continue
        r = dict(level=lvl, node_id=nid, hops=hops[lvl], dep=1.0)
        if lvl == "component":
            r["obj_id"] = G.nodes[nid].get("component_id", nid)
            r["n_products"] = sum(1 for v in G.successors(nid) if v in affected)
        elif lvl == "product":
            r["obj_id"], r["dep"] = nid, dep.get(nid, 1.0)
        elif lvl == "order":
            prod = next(iter(G.predecessors(nid)), None)
            r.update(obj_id=nid, product_id=prod, dep=dep.get(prod, 1.0))
        else:
            r["obj_id"] = nid
        rows.append(r)
    fwd = pd.DataFrame(rows)
    if "n_products" in fwd:
        fwd["n_products"] = fwd["n_products"].fillna(0)
    return fwd, orders


def risk_score(G, forward, incident):
    fwd, orders = p4_forward(G, forward, incident)
    if fwd.empty:
        return []
    scored = p4.risk_score(fwd.drop(columns="node_id").assign(node_ref=fwd.node_id.values), orders)
    tab = p4.risk_table(scored, orders)
    why = dict(zip(zip(tab["Loại"], tab["Đối tượng"]), tab["Lý do"]))
    scored = scored.assign(reason=[why.get((p4.LEVEL_VI[lv], o), "") for lv, o in zip(scored.level, scored.obj_id)])
    inv = {v: k for k, v in LEVEL.items()}
    out = [{"node_id": r.node_ref, "type": inv[r.level], "risk_score": round(float(min(max(r.risk, 0), 1)), 4),
            "reason": r.reason} for r in scored.itertuples()]
    return sorted(out, key=lambda r: (-r["risk_score"], r["node_id"]))


def baseline_e2(G, forward, incident):
    """Baseline E2 của P4: risk = 1/(1+hops), hops theo quy ước của P4."""
    fwd, _ = p4_forward(G, forward, incident)
    return sorted(({"node_id": r.node_id, "risk_score": 1 / (1 + r.hops)} for r in fwd.itertuples()),
                  key=lambda r: -r["risk_score"])
