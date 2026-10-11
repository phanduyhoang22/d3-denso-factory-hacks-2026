"""P3.4 – Bộ sinh kịch bản sự cố (mục 18.3), một hàm dùng chung cho mọi thí nghiệm.

Thứ tự (tham số hóa bằng seed, mỗi bước một luồng RNG riêng):
 1. generate_graph(seed, size)  – cấu trúc độc lập với lỗi
 2. assign_data()               – gắn dòng AI4I / SECOM thật vào node
 3. chọn node gốc + 1 dòng lỗi thật (backward truth)
 4. true_impact() trên graph_full → forward truth; chọn "kết quả xấu" trong vùng ảnh hưởng
 5. inject_confounders(): bật lỗi thật ở các node KHÔNG phải tổ tiên của kết quả xấu
 6. observe_graph(): nhiễu trọng số/tồn kho + xóa ngẫu nhiên edge_drop% cạnh → graph_observed

Cùng seed ⇒ cùng đồ thị, cùng gốc, cùng nhiễu; tập cạnh bị xóa lồng nhau
(10% ⊂ 25% ⊂ 50%) để E4 so sánh theo cặp.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import networkx as nx
import numpy as np

from . import sim_params as SP
from .assign import assign_data, source_nodes
from .data import DomainData, load_domain
from .graph import generate_graph
from .ontology import (CAUSE_GROUP, COMPONENT, DOMAIN_AI4I, DOMAIN_SECOM, IMPACT_LAYERS, ORDER,
                       PROCESS, PRODUCT, PROPAGATION_EDGES)
from .propagation import propagation_view
from .truth import forward_truth_from_impact, true_impact


@dataclass
class ScenarioConfig:
    domain: str = DOMAIN_AI4I               # 'ai4i' (nguồn = Máy, nhánh A) | 'secom' (nguồn = Công đoạn, nhánh B)
    size: str = "medium"                    # small | medium | large
    confounder_ratio: float = 0.0           # 0 / 0.25 / 0.5 – tỷ lệ node nguồn không liên quan bị bật lỗi
    edge_drop: float = 0.0                  # 0 / 0.1 / 0.25 / 0.5 – tỷ lệ cạnh lan truyền bị xóa (E4)
    weight_noise: float = SP.WEIGHT_NOISE_SIGMA
    stock_noise: float = SP.STOCK_NOISE_SIGMA
    failure_mode: str | None = None         # ép chế độ lỗi của gốc (TWF/HDF/PWF/OSF/RNF) – None = ngẫu nhiên
    background_fp: bool = False             # thêm cảnh báo sai của detector từ dòng bình thường
    impact_threshold: float = SP.IMPACT_THRESHOLD
    drop_types: list | None = None          # chỉ xóa cạnh thuộc các loại này (None = mọi cạnh lan truyền)


def _rng(seed, tag):
    return np.random.default_rng(np.random.SeedSequence([seed, tag]))


def severity_label(score: float) -> str:
    return "Cao" if score >= 0.85 else ("Trung bình" if score >= 0.65 else "Thấp")


def _pick_failure_row(G, node, dd: DomainData, rng, mode=None):
    """Một dòng lỗi thật (tập test) cho node: ưu tiên dòng của chính node, sau đó pool cùng loại."""
    rows = dd.rows
    own = [i for i in G.nodes[node]["data"]["test_rows"] if rows.is_fail.iat[i]]
    if mode:
        own = [i for i in own if rows["mode"].iat[i] == mode]
    if own:
        return int(rng.choice(own))
    mask = (rows.split == "test") & rows.is_fail
    if mode:
        mask &= rows["mode"] == mode
    if dd.domain == DOMAIN_AI4I and "machine_type" in G.nodes[node]:
        m2 = mask & (rows.type == G.nodes[node]["machine_type"])
        if m2.any():
            mask = m2
    pool = np.where(mask.values)[0]
    if len(pool) == 0:
        raise ValueError(f"không có dòng lỗi test cho mode={mode}")
    return int(rng.choice(pool))


def make_incident(G, node, dd: DomainData, row_pos: int, ts: datetime) -> dict:
    """Bản ghi sự cố chuẩn hóa (mục 5.3 + Part 0)."""
    r = dd.rows.iloc[row_pos]
    mode = r["mode"] if r["mode"] != "NONE" else "NORMAL"
    sev = SP.SEVERITY_BY_MODE.get(mode, 0.3)
    return {
        "incident_id": None,  # gán sau khi sắp theo thời gian
        "timestamp": ts.isoformat(timespec="minutes"),
        "timestamp_is_synthetic": True,
        "node_id": node, "node_type": G.nodes[node]["type"],
        "dataset": dd.domain, "source_row_id": int(r["row_id"]), "source_row_pos": int(row_pos),
        "failure_mode": mode,
        "anomaly_type": CAUSE_GROUP.get(mode, "Bình thường (cảnh báo sai)"),
        "severity": severity_label(sev), "severity_score": sev,
        "anomaly_score": round(float(r["anomaly_score"]), 4),
        "detected": bool(r["detected"]),
        "suspected_cause_group": CAUSE_GROUP.get(mode, "Chưa xác định"),
    }


def inject_confounders(G_full, dd: DomainData, domain, root, bad_outcome, ratio, rng, t_root, t_bad):
    """Bật lỗi thật ở round(ratio·|eligible|) node nguồn KHÔNG phải tổ tiên của kết quả xấu."""
    anc = nx.ancestors(propagation_view(G_full), bad_outcome)
    eligible = [n for n in source_nodes(G_full, domain) if n != root and n not in anc]
    k = int(round(ratio * len(eligible)))
    chosen = list(rng.choice(eligible, size=k, replace=False)) if k else []
    span = (t_bad - timedelta(minutes=10) - (t_root - timedelta(hours=SP.CONFOUNDER_WINDOW_BEFORE_ROOT_H)))
    out = []
    for n in chosen:
        pos = _pick_failure_row(G_full, n, dd, rng)
        ts = t_root - timedelta(hours=SP.CONFOUNDER_WINDOW_BEFORE_ROOT_H) + span * float(rng.random())
        out.append(make_incident(G_full, str(n), dd, pos, ts))
    return out, [str(c) for c in chosen], len(eligible)


def observe_graph(G_full: nx.DiGraph, seed: int, edge_drop: float, weight_noise: float, stock_noise: float,
                  drop_types: list | None = None):
    """Phiên bản hệ thống nhìn thấy: trọng số/tồn kho nhiễu, WIP buffer ẩn, thiếu cạnh."""
    rng = _rng(seed, 606)
    Go = G_full.copy()
    prop_edges = sorted((u, v) for u, v, d in G_full.edges(data=True) if d["type"] in PROPAGATION_EDGES)
    noise = rng.lognormal(0.0, weight_noise, size=len(prop_edges))      # rút cho MỌI cạnh trước
    order = rng.permutation(len(prop_edges))                             # thứ tự xóa cố định theo seed
    for (u, v), z in zip(prop_edges, noise):
        Go.edges[u, v]["weight"] = float(np.clip(G_full.edges[u, v]["weight"] * z, 0.01, 1.0))
    comps = sorted(n for n, d in G_full.nodes(data=True) if d["type"] == COMPONENT)
    snoise = rng.lognormal(0.0, stock_noise, size=len(comps))
    for n, z in zip(comps, snoise):
        Go.nodes[n]["safety_stock"] = int(round(G_full.nodes[n]["safety_stock"] * z))
    for n, d in Go.nodes(data=True):
        d.pop("wip_buffer_true", None)
    cand = [i for i in order if drop_types is None or G_full.edges[prop_edges[i]]["type"] in drop_types]
    n_drop = int(round(edge_drop * len(cand)))
    dropped = [prop_edges[i] for i in cand[:n_drop]]
    Go.remove_edges_from(dropped)
    Go.graph["edge_drop"] = edge_drop
    return Go, dropped


def generate_scenario(seed: int, config: ScenarioConfig | dict | None = None,
                      data: dict[str, DomainData] | None = None) -> dict:
    cfg = config if isinstance(config, ScenarioConfig) else ScenarioConfig(**(config or {}))
    data = data or {d: load_domain(d) for d in (DOMAIN_AI4I, DOMAIN_SECOM)}
    dd = data[cfg.domain]

    # 1–2. cấu trúc rồi mới gán dữ liệu
    G = generate_graph(seed, cfg.size)
    assign_data(G, data.get(DOMAIN_AI4I), data.get(DOMAIN_SECOM), seed)

    # 3–4. gốc + truth
    rng_root, rng_out = _rng(seed, 303), _rng(seed, 404)
    sources = source_nodes(G, cfg.domain)
    for _ in range(100):
        root = str(rng_root.choice(sources))
        pos = _pick_failure_row(G, root, dd, rng_root, cfg.failure_mode)
        mode = dd.rows["mode"].iat[pos]
        sev = SP.SEVERITY_BY_MODE[mode]
        impact = true_impact(G, root, sev)
        ftruth = forward_truth_from_impact(G, impact, cfg.impact_threshold)
        cands = next((ftruth[t] for t in (ORDER, PRODUCT, COMPONENT, PROCESS) if ftruth[t]), [])
        if cands:
            break
    else:
        raise RuntimeError("không tìm được gốc có vùng ảnh hưởng")
    w = np.array([impact[c] for c in cands])
    bad = str(rng_out.choice(cands, p=w / w.sum()))

    base = datetime.fromisoformat(SP.SCENARIO_BASE_TIME) + timedelta(days=seed % 365)
    t_root = base + timedelta(hours=float(rng_out.uniform(*SP.ROOT_OFFSET_H)))
    t_bad = t_root + timedelta(hours=float(rng_out.uniform(*SP.OUTCOME_LAG_H)))

    root_inc = make_incident(G, root, dd, pos, t_root)
    # 5. nhiễu gây nhầm
    conf_incs, conf_nodes, n_eligible = inject_confounders(
        G, dd, cfg.domain, root, bad, cfg.confounder_ratio, _rng(seed, 505), t_root, t_bad)
    incidents = [root_inc] + conf_incs
    if cfg.background_fp:
        rng_bg = _rng(seed, 707)
        busy = {root, *conf_nodes}
        for n in source_nodes(G, cfg.domain):
            if n in busy:
                continue
            normal = [i for i in G.nodes[n]["data"]["test_rows"] if not dd.rows.is_fail.iat[i]]
            if not normal:
                continue
            p = int(rng_bg.choice(normal))
            if dd.rows.detected.iat[p]:
                ts = t_root - timedelta(hours=3) + (t_bad - t_root + timedelta(hours=3)) * float(rng_bg.random())
                incidents.append(make_incident(G, n, dd, p, ts))
    incidents.sort(key=lambda r: (r["timestamp"], r["node_id"]))
    for k, inc in enumerate(incidents):
        inc["incident_id"] = f"INC_{seed:04d}_{k+1:03d}"
    root_id = next(i["incident_id"] for i in incidents if i is root_inc)

    # 6. đồ thị quan sát
    Go, dropped = observe_graph(G, seed, cfg.edge_drop, cfg.weight_noise, cfg.stock_noise, cfg.drop_types)

    return {
        "scenario_id": f"SCN_{cfg.domain}_{cfg.size}_s{seed}_c{int(cfg.confounder_ratio*100)}_d{int(cfg.edge_drop*100)}",
        "seed": seed, "config": asdict(cfg),
        "graph_full": G, "graph_observed": Go,
        "incidents": incidents,
        "bad_outcome": {"node_id": bad, "type": G.nodes[bad]["type"],
                        "timestamp": t_bad.isoformat(timespec="minutes"), "timestamp_is_synthetic": True},
        "forward_truth": ftruth,
        "true_impact": impact,
        "backward_truth": {"root_node": root, "root_incident_id": root_id,
                           "source_row_id": root_inc["source_row_id"], "failure_mode": mode,
                           "severity_score": sev},
        "confounder_nodes": conf_nodes,
        "meta": {"n_eligible_confounders": n_eligible, "n_incidents": len(incidents),
                 "dropped_edges": [list(e) for e in dropped],
                 "n_prop_edges": sum(1 for *_, d in G.edges(data=True) if d["type"] in PROPAGATION_EDGES)},
    }


def scenario_to_json(sc: dict, include_graphs: bool = False) -> dict:
    """Bản JSON được (bỏ đồ thị networkx; dùng export.graph_to_json nếu cần đồ thị)."""
    out = {k: v for k, v in sc.items() if k not in ("graph_full", "graph_observed")}
    if include_graphs:
        from .export import graph_to_json
        out["graph_full"] = graph_to_json(sc["graph_full"])
        out["graph_observed"] = graph_to_json(sc["graph_observed"])
    return out
