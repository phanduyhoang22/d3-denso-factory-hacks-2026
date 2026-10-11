"""P3.2 – Sinh cấu trúc đồ thị nhà máy ĐỘC LẬP với lỗi.

`generate_graph(seed, size)` chỉ dùng RNG của riêng nó: cấu trúc, trọng số, tồn kho,
ưu tiên… được quyết định xong TRƯỚC KHI có bất kỳ thông tin nào về máy nào sẽ lỗi.
Không hàm nào ở đây nhận dữ liệu lỗi làm đầu vào.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from . import sim_params as SP
from .ontology import (BRANCH_A, BRANCH_B, COMPONENT, FEEDS, FULFILLS, LAYER, MACHINE,
                       MONITORS, OPERATES_IN, ORDER, PROCESS, PRODUCES, PRODUCT, SENSOR,
                       SHARED, USED_IN)


def _rint(rng, lo_hi):
    lo, hi = lo_hi
    return int(rng.integers(lo, hi + 1))


def _runif(rng, lo_hi):
    return float(rng.uniform(*lo_hi))


def _add_node(G, nid, ntype, branch, **attrs):
    G.add_node(nid, id=nid, type=ntype, layer=LAYER[ntype], branch=branch, **attrs)


def _add_edge(G, u, v, etype, weight):
    G.add_edge(u, v, type=etype, weight=float(round(weight, 4)))


def component_buffer(stock_cover_days: float, lead_time_days: float) -> float:
    """Phần cú sốc mà tồn kho dự phòng hấp thụ (0..BUFFER_CAP). Dùng chung cho truth & trace."""
    if stock_cover_days <= 0:
        return 0.0
    return float(min(SP.BUFFER_CAP, stock_cover_days / (stock_cover_days + lead_time_days)))


def generate_graph(seed: int, size: str = "medium") -> nx.DiGraph:
    """Sinh đồ thị nhà máy. size ∈ {'small','medium','large'}."""
    if size not in SP.SIZES:
        raise ValueError(f"size phải thuộc {list(SP.SIZES)}")
    cfg = SP.SIZES[size]
    rng = np.random.default_rng(np.random.SeedSequence([seed, 101]))
    G = nx.DiGraph(name=f"factory_{size}_seed{seed}", seed=seed, size=size)

    counters = {MACHINE: 0, PROCESS: 0, COMPONENT: 0}

    def next_id(kind, prefix):
        counters[kind] += 1
        return f"{prefix}{counters[kind]:02d}"

    # ---- lines, công đoạn, máy, cảm biến ----------------------------------
    lines = [(BRANCH_A, f"LA{i+1}", cfg["procs_a"]) for i in range(cfg["lines_a"])] + \
            [(BRANCH_B, f"LB{i+1}", cfg["procs_b"]) for i in range(cfg["lines_b"])]
    types = list(SP.MACHINE_TYPE_MIX)
    probs = list(SP.MACHINE_TYPE_MIX.values())
    for branch, line, n_proc in lines:
        procs = []
        for k in range(n_proc):
            p = next_id(PROCESS, "P")
            _add_node(G, p, PROCESS, branch, line=line, step=k + 1,
                      wip_buffer_true=round(_runif(rng, SP.WIP_BUFFER), 3))
            procs.append(p)
            if branch == BRANCH_B:  # SECOM: cảm biến gom nhóm gắn thẳng vào công đoạn
                for g in range(SP.SECOM_SENSOR_GROUPS):
                    s = f"S_{p}_g{g+1}"
                    _add_node(G, s, SENSOR, branch, measures=f"secom_group_{g+1}")
                    _add_edge(G, s, p, MONITORS, 1.0)
        # feeds giữa các công đoạn liên tiếp
        for a, b in zip(procs[:-1], procs[1:]):
            if rng.random() < SP.P_FEED:
                _add_edge(G, a, b, FEEDS, _runif(rng, SP.FEED_WEIGHT))
        # máy
        line_machines = []
        for i, p in enumerate(procs):
            k = _rint(rng, SP.MACHINES_PER_PROCESS_A if branch == BRANCH_A else SP.MACHINES_PER_PROCESS_B)
            ms = []
            for _ in range(k):
                m = next_id(MACHINE, "M")
                _add_node(G, m, MACHINE, branch, line=line,
                          machine_type=str(rng.choice(types, p=probs)),
                          spare_capacity=round(_runif(rng, SP.SPARE_CAPACITY), 3))
                if branch == BRANCH_A:
                    for s_name in SP.AI4I_SENSORS:
                        s = f"S_{m}_{s_name}"
                        _add_node(G, s, SENSOR, branch, measures=s_name)
                        _add_edge(G, s, m, MONITORS, 1.0)
                ms.append(m)
            line_machines.append((p, ms))
        # máy dùng chung với công đoạn kế tiếp
        for i, (p, ms) in enumerate(line_machines[:-1]):
            for m in ms:
                if rng.random() < SP.P_SHARED_MACHINE:
                    line_machines[i + 1][1].append(m)
        for p, ms in line_machines:
            shares = rng.dirichlet(np.ones(len(ms)) * 2.0)
            for m, w in zip(ms, shares):
                _add_edge(G, m, p, OPERATES_IN, w)

    # ---- máy thay thế: cùng line, cùng machine_type --------------------------
    machines = [n for n, d in G.nodes(data=True) if d["type"] == MACHINE]
    for m in machines:
        d = G.nodes[m]
        G.nodes[m]["alt_machines"] = [o for o in machines if o != m and G.nodes[o]["line"] == d["line"]
                                      and G.nodes[o]["machine_type"] == d["machine_type"]]

    # ---- linh kiện ----------------------------------------------------------
    processes = [n for n, d in G.nodes(data=True) if d["type"] == PROCESS]
    components = []
    for p in processes:
        for _ in range(_rint(rng, SP.COMPONENTS_PER_PROCESS)):
            a = next_id(COMPONENT, "A")
            usage = _rint(rng, SP.DAILY_USAGE)
            cover = round(_runif(rng, SP.STOCK_COVER_DAYS), 2)
            _add_node(G, a, COMPONENT, SHARED,
                      daily_usage=usage, safety_stock=int(round(cover * usage)),
                      lead_time_days=_rint(rng, SP.LEAD_TIME_DAYS),
                      n_alt_sources=_rint(rng, SP.N_ALT_SOURCES))
            _add_edge(G, p, a, PRODUCES, _runif(rng, SP.PRODUCE_WEIGHT))
            if rng.random() < SP.P_DUAL_SOURCE:
                other = [q for q in processes if q != p]
                q = str(rng.choice(other))
                _add_edge(G, q, a, PRODUCES, _runif(rng, SP.PRODUCE_WEIGHT) * 0.5)
            components.append(a)

    # ---- sản phẩm: mỗi SP thuộc 1 "họ" gắn với 1 line (line nhà) -------------
    line_names = [ln for _, ln, _ in lines]
    comp_line = {a: G.nodes[next(iter(G.predecessors(a)))]["line"] for a in components}
    for a in components:
        G.nodes[a]["line"] = comp_line[a]
    products = []
    for i in range(cfg["n_products"]):
        x = f"X{i+1}"
        home = line_names[i % len(line_names)]
        _add_node(G, x, PRODUCT, SHARED, family_line=home)
        products.append(x)
        home_comps = [a for a in components if comp_line[a] == home]
        k = min(_rint(rng, SP.COMPONENTS_PER_PRODUCT), len(components))
        chosen = set()
        while len(chosen) < k:
            pool = home_comps if (home_comps and rng.random() < SP.P_HOME_LINE_COMPONENT) else components
            chosen.add(str(rng.choice(pool)))
        for a in sorted(chosen):
            _add_edge(G, a, x, USED_IN, _runif(rng, SP.USED_IN_WEIGHT))
    # mọi linh kiện phải dùng ở ít nhất 1 sản phẩm (ưu tiên SP cùng họ)
    for a in components:
        if G.out_degree(a) == 0:
            fam = [x for x in products if G.nodes[x]["family_line"] == comp_line[a]] or products
            _add_edge(G, a, str(rng.choice(fam)), USED_IN, _runif(rng, SP.USED_IN_WEIGHT))

    # ---- đơn hàng -----------------------------------------------------------
    pr_levels, pr_probs = list(SP.ORDER_PRIORITY), list(SP.ORDER_PRIORITY.values())
    for j in range(cfg["n_orders"]):
        o = f"O{j+1:02d}" if cfg["n_orders"] < 100 else f"O{j+1:03d}"
        _add_node(G, o, ORDER, SHARED, priority=int(rng.choice(pr_levels, p=pr_probs)),
                  due_in_days=_rint(rng, SP.DUE_IN_DAYS), quantity=_rint(rng, SP.ORDER_QTY))
        k = min(_rint(rng, SP.PRODUCTS_PER_ORDER), len(products))
        first = str(rng.choice(products))
        chosen = [first]
        fam = [x for x in products if G.nodes[x]["family_line"] == G.nodes[first]["family_line"]]
        while len(chosen) < k:
            pool = fam if rng.random() < SP.P_SAME_FAMILY_ORDER else products
            cand = [x for x in pool if x not in chosen] or [x for x in products if x not in chosen]
            chosen.append(str(rng.choice(cand)))
        shares = rng.dirichlet(np.ones(k) * 2.0) if k > 1 else np.array([1.0])
        for x, w in zip(chosen, shares):
            _add_edge(G, x, o, FULFILLS, max(w, 0.05))

    assert nx.is_directed_acyclic_graph(G), "đồ thị phải là DAG"
    return G


# --------------------------------------------------------------------------- demo
def demo_graph() -> nx.DiGraph:
    """Đồ thị cố định cho kịch bản trình diễn mục 10: M05 → P02 → A13 → X1 → O43/O58.

    M07 chạy song song ở P02 và là máy thay thế của M05; A13 có tồn kho dự phòng thấp.
    """
    G = nx.DiGraph(name="factory_demo", seed=None, size="demo")
    procs = {"P01": 1, "P02": 2, "P03": 3, "P04": 4}
    for p, step in procs.items():
        _add_node(G, p, PROCESS, BRANCH_A, line="LA1", step=step, wip_buffer_true=0.0)
    mach = {  # máy: (công đoạn, tỷ trọng tải, loại)
        "M01": ("P01", 0.5, "L"), "M02": ("P01", 0.5, "L"),
        "M05": ("P02", 0.6, "M"), "M07": ("P02", 0.4, "M"),
        "M03": ("P03", 0.7, "L"), "M04": ("P03", 0.3, "H"),
        "M06": ("P04", 0.5, "L"), "M08": ("P04", 0.5, "L"),
    }
    for m, (p, w, t) in mach.items():
        _add_node(G, m, MACHINE, BRANCH_A, line="LA1", machine_type=t, spare_capacity=0.35 if m == "M07" else 0.1)
        for s_name in SP.AI4I_SENSORS:
            s = f"S_{m}_{s_name}"
            _add_node(G, s, SENSOR, BRANCH_A, measures=s_name)
            _add_edge(G, s, m, MONITORS, 1.0)
        _add_edge(G, m, p, OPERATES_IN, w)
    for m in mach:
        t = G.nodes[m]["machine_type"]
        G.nodes[m]["alt_machines"] = [o for o in mach if o != m and G.nodes[o]["machine_type"] == t]
    _add_edge(G, "P01", "P03", FEEDS, 0.5)
    comps = {  # linh kiện: (công đoạn, w, daily_usage, stock_cover_days, lead_time, n_alt)
        "A10": ("P01", 0.9, 200, 4.0, 5, 2), "A11": ("P01", 0.8, 150, 3.0, 5, 1),
        "A12": ("P03", 0.9, 300, 5.0, 7, 2), "A13": ("P02", 0.95, 400, 1.0, 7, 0),
        "A14": ("P04", 0.85, 100, 2.0, 4, 1), "A15": ("P04", 0.7, 120, 6.0, 4, 3),
    }
    for a, (p, w, u, cover, lt, alt) in comps.items():
        _add_node(G, a, COMPONENT, SHARED, daily_usage=u, safety_stock=int(cover * u),
                  lead_time_days=lt, n_alt_sources=alt)
        _add_edge(G, p, a, PRODUCES, w)
    for x in ["X1", "X2", "X3"]:
        _add_node(G, x, PRODUCT, SHARED)
    for a, x, w in [("A13", "X1", 0.9), ("A10", "X2", 0.8), ("A11", "X2", 0.5), ("A12", "X3", 0.9),
                    ("A14", "X3", 0.6), ("A15", "X2", 0.4)]:
        _add_edge(G, a, x, USED_IN, w)
    orders = {"O41": ("X2", 2, 20), "O42": ("X3", 1, 25), "O43": ("X1", 3, 3), "O44": ("X2", 2, 12),
              "O50": ("X3", 2, 9), "O58": ("X1", 2, 6), "O60": ("X2", 1, 28)}
    for o, (x, pr, due) in orders.items():
        _add_node(G, o, ORDER, SHARED, priority=pr, due_in_days=due, quantity=1000)
    for o, (x, _, _) in orders.items():
        _add_edge(G, x, o, FULFILLS, {"O43": 0.8, "O58": 0.6}.get(o, 0.7))
    _add_edge(G, "X3", "O41", FULFILLS, 0.3)
    return G


def graph_summary(G: nx.DiGraph) -> dict:
    from collections import Counter
    return {"nodes": dict(Counter(d["type"] for _, d in G.nodes(data=True))),
            "edges": dict(Counter(d["type"] for _, _, d in G.edges(data=True))),
            "n_nodes": G.number_of_nodes(), "n_edges": G.number_of_edges()}
