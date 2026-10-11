"""Chuyển đổi networkx.DiGraph <-> JSON theo graph.schema.json."""
import networkx as nx

DEPARTMENT_BY_TYPE = {
    "sensor": "maintenance",
    "machine": "maintenance",
    "process": "production",
    "part": "warehouse",
    "product": "planning",
    "order": "sales",
}


def to_json(G, **meta):
    m = {"seed": 0, "size": "small", "view": "full", "edge_drop_rate": 0.0}
    m.update(G.graph.get("meta", {}))
    m.update(meta)
    nodes = [{"id": n, **attrs} for n, attrs in G.nodes(data=True)]
    edges = [{"source": u, "target": v, "relation": d["relation"], "weight": round(float(d["weight"]), 4)}
             for u, v, d in G.edges(data=True)]
    return {"meta": m, "nodes": nodes, "edges": edges}


def from_json(data):
    G = nx.DiGraph()
    G.graph["meta"] = dict(data["meta"])
    for n in data["nodes"]:
        attrs = {k: v for k, v in n.items() if k != "id"}
        G.add_node(n["id"], **attrs)
    for e in data["edges"]:
        G.add_edge(e["source"], e["target"], relation=e["relation"], weight=e["weight"])
    return G
