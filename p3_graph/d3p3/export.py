"""P3.8 – Xuất node/cạnh JSON cho dashboard (P5), có đánh dấu vùng ảnh hưởng."""
from __future__ import annotations

import json

import networkx as nx

from .ontology import SENSOR


def graph_to_json(G: nx.DiGraph, trace: dict | None = None, include_sensors: bool = False,
                  truth_impact: dict | None = None) -> dict:
    est = {a["node_id"]: a for a in (trace or {}).get("affected", [])}
    path_edges = set()
    for a in est.values():
        if a.get("above_threshold"):
            p = a["path"]
            path_edges.update(zip(p[:-1], p[1:]))
    nodes = []
    for n, d in G.nodes(data=True):
        if d["type"] == SENSOR and not include_sensors:
            continue
        rec = {k: v for k, v in d.items() if k not in ("data",)}
        if "data" in d:
            rec["data_summary"] = {"dataset": d["data"]["dataset"], "n_train": len(d["data"]["train_rows"]),
                                   "n_test": len(d["data"]["test_rows"])}
        if trace:
            rec["is_root"] = n == trace["root"]
            a = est.get(n)
            rec["affected"] = bool(a and a["above_threshold"])
            rec["est_impact"] = a["est_impact"] if a else 0.0
            rec["hops"] = a["hops"] if a else None
        if truth_impact is not None:
            rec["true_impact"] = truth_impact.get(n, 0.0)
        nodes.append(rec)
    keep = {r["id"] for r in nodes}
    edges = [{"source": u, "target": v, "type": d["type"], "weight": d["weight"],
              "on_impact_path": (u, v) in path_edges}
             for u, v, d in G.edges(data=True) if u in keep and v in keep]
    return {"graph": {k: v for k, v in G.graph.items()}, "nodes": nodes, "edges": edges,
            "root": (trace or {}).get("root")}


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
