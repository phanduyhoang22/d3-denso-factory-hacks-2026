"""P4.4 → pipeline: gọi recommend() của P4 (p4_risk_action/recommend.py, kb.yaml) và gắn bộ phận.

recommend() của P4 trả bảng [Ưu tiên, Hành động, Căn cứ]; ở đây chỉ chuyển sang schema `actions`
(department theo loại hành động, kb_rule_id, adoption_rate từ kb.yaml). Không đổi logic của P4.
"""
import sys
from functools import lru_cache

import pandas as pd
import yaml

from . import ROOT
from .risk import tables

sys.path.insert(0, str(ROOT / "p4_risk_action"))
import recommend as p4  # noqa: E402


@lru_cache(maxsize=None)
def kb():
    return yaml.safe_load((ROOT / "p4_risk_action" / "kb.yaml").read_text(encoding="utf-8"))


def _department(text, dataset):
    t = text.lower()
    if t.startswith("kiểm tra") or t.startswith("chuyển cảnh báo"):
        return "quality" if dataset == "secom" else "maintenance"
    if t.startswith("chuyển tải"):
        return "production"
    if t.startswith("ưu tiên giữ tiến độ"):
        return "planning"
    if "dời lịch" in t:
        return "sales"
    return "planning"


def recommend(G, incident, risk, backward):
    branch = "A" if incident["dataset"] == "ai4i" else "B"
    routing, orders, _, _ = tables(branch)
    scored = pd.DataFrame([{"level": "order", "obj_id": r["node_id"], "risk": r["risk_score"]}
                           for r in risk if r["type"] == "order"], columns=["level", "obj_id", "risk"])
    mode = incident.get("failure_mode") or "UNKNOWN"
    mode = "+".join(m if m in kb() else "UNKNOWN" for m in mode.split("+"))
    inc = {"node_id": incident["node_id"], "failure_mode": mode,
           "dataset": "AI4I" if branch == "A" else "SECOM"}
    tab = p4.recommend(inc, routing, orders, kb(), scored=scored)
    rules = mode.split("+")
    out = []
    for i, r in enumerate(tab.itertuples(index=False)):
        rule = rules[i] if i < len(rules) and r[1].startswith("Kiểm tra") else None
        ar = p4.adoption_rate(kb()[rule]) if rule else None
        out.append({"priority": int(r[0]), "department": _department(r[1], incident["dataset"]),
                    "action": f"{r[1]} — {r[2]}", "target_node": incident["node_id"],
                    "kb_rule_id": rule, "adoption_rate": ar})
    return out
