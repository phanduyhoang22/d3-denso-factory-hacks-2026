#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DENSO Factory Hacks 2026 - Đề D3 - PHẦN 2: TRUY VẾT TÁC ĐỘNG
=============================================================
Chạy trên dataset AI4I 2020 (ai4i2020.csv):

    python p2_impact_trace.py --csv ai4i2020.csv --out p2_outputs

Ý tưởng
-------
* Đồ thị 2 lớp (networkx):
    - Lớp LOGIC     : Sensor, FailureMode, Machine, Process, Part, Product, Lot
    - Lớp NGHIỆP VỤ : Order (đơn hàng: số lượng, hạn giao, ưu tiên)
    - Cầu nối       : Lot -> Order (allocated_to), Product -> Order (requested)
* Truy vết NGƯỢC: xếp hạng nguyên nhân từ bằng chứng cảm biến (chỉ dùng dữ liệu
  tại/trước thời điểm sự cố) + tần suất lịch sử (prior tính trên 70% đầu chuỗi).
* Truy vết XUÔI : lan truyền Máy -> Công đoạn -> Linh kiện -> Sản phẩm -> Đơn hàng,
  suy giảm theo độ phụ thuộc và vùng đệm (buffer), rồi chấm điểm theo độ sát hạn.

GIẢ ĐỊNH QUAN TRỌNG (không có trong dataset, xem CFG và build_orders):
  - Dataset chỉ có MỘT máy (M05); mỗi dòng = 1 sản phẩm, UDI = thứ tự sản xuất.
  - Dataset không có timestamp -> giả định takt 1 phút/sản phẩm.
  - Đơn hàng, vùng đệm, thời gian dừng máy theo từng kiểu lỗi, máy thay thế M07,
    máy/công đoạn thượng nguồn và hạ nguồn: TẤT CẢ là giả lập, cần hiệu chỉnh
    bằng dữ liệu thật của DENSO ở bootcamp.
  - Nhãn lỗi (Machine failure) đóng vai "đầu ra của P1".
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from p2_schema import (GRAPH_VIEW_SCHEMA, IMPACT_REPORT_SCHEMA, INCIDENT_RECORD_SCHEMA,
                       ValidationError, validate, write_schemas)

# =============================================================================
# CONFIG
# =============================================================================
CFG = {
    "seed": 42,
    "t0": "2026-10-01 06:00",      # mốc thời gian giả định của UDI = 1
    "takt_min": 1.0,               # phút / sản phẩm (giả định)
    "lot_size": 100,               # số sản phẩm / lô truy xuất
    "train_frac": 0.70,            # tính prior trên 70% đầu theo thời gian

    # --- lớp nghiệp vụ giả lập ---
    "orders_per_type": {"L": 20, "M": 12, "H": 8},
    "slack_range_min": (15, 2880),     # chặn dưới/trên của thời gian dư đến hạn giao
    "slack_mean_min": 360.0,           # phân phối mũ, trung bình 6 giờ (giả định)
    "priority_p": [0.5, 0.3, 0.2],     # xác suất ưu tiên 1/2/3
    "prio_factor": {1: 0.70, 2: 0.85, 3: 1.00},

    # --- đặc tính từng kiểu lỗi (giả định, cần xác nhận với DENSO) ---
    "downtime_min": {"TWF": 15, "HDF": 45, "PWF": 60, "OSF": 90, "RNF": 30},
    "severity":     {"TWF": 0.50, "HDF": 0.75, "PWF": 0.85, "OSF": 0.95, "RNF": 0.60},

    # --- tham số lan truyền ---
    "substitute_share": 0.30,      # M07 gánh được 30% tải của M05
    "recovery_tau_h": 24.0,        # trễ giảm dần theo giờ nhờ tăng ca/bù (giả định)
    "risk_thr": 0.05,              # ngưỡng hiển thị
    "evidence_eps": 0.02,          # sàn bằng chứng, tránh điểm = 0
    # --- vùng đệm theo phút sản xuất (giả định) ---
    "fg_buffer_min": {"L": 20.0, "M": 8.0, "H": 0.0},   # tồn thành phẩm theo biến thể
    "buf_p02_a13": 5.0,            # WIP giữa phay và lắp ráp
    "buf_a13_p03": 5.0,
    "buf_a11_p02": 60.0,           # tồn phôi trước máy phay
    "prior_smoothing": 0.0,        # trộn prior với phân phối đều: prior' = (1-l)*prior + l/K (0 = không làm trơn)
    "hint_boost": 2.0,             # nhân điểm nguyên nhân mà P1 nêu trong "nhóm nguyên nhân nghi ngờ"
    "level_to_severity": {"cao": 0.90, "high": 0.90, "trung bình": 0.60, "trung binh": 0.60,
                          "medium": 0.60, "thấp": 0.30, "thap": 0.30, "low": 0.30},
}

MODES = {
    "TWF": "Mòn dụng cụ",
    "HDF": "Tản nhiệt kém",
    "PWF": "Công suất bất thường",
    "OSF": "Quá tải cơ học",
    "RNF": "Lỗi ngẫu nhiên",
}
SENSORS = {
    "S_AIR": "Air temperature [K]",
    "S_PROC": "Process temperature [K]",
    "S_RPM": "Rotational speed [rpm]",
    "S_TORQUE": "Torque [Nm]",
    "S_WEAR": "Tool wear [min]",
}
MODE_SENSORS = {
    "TWF": ["S_WEAR"],
    "HDF": ["S_AIR", "S_PROC", "S_RPM"],
    "PWF": ["S_TORQUE", "S_RPM"],
    "OSF": ["S_WEAR", "S_TORQUE"],
    "RNF": [],
}
REQUIRED_COLS = ["UDI", "Product ID", "Type", *SENSORS.values(),
                 "Machine failure", *MODES.keys()]

SCHEMA_VERSION = "p2.impact_report.v1"
# Bộ phận phụ trách theo loại nút (giả định, chỉnh theo cơ cấu DENSO)
DEPT_OF_TYPE = {
    "machine": "Bảo trì",
    "process": "Sản xuất",
    "part": "Kho & Logistics",
    "product": "Chất lượng",
    "lot": "Chất lượng",
    "order": "Kế hoạch sản xuất",
}

# Vùng đệm (phút) và độ phụ thuộc w trên từng cạnh dòng chảy (giả định)


# =============================================================================
# 1. NẠP & KIỂM TRA DỮ LIỆU
# =============================================================================
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().lstrip("\ufeff") for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột: {missing}")
    df = df.sort_values("UDI").reset_index(drop=True)
    if not df["UDI"].is_unique:
        raise ValueError("Cột UDI phải duy nhất")
    if df[REQUIRED_COLS].isna().sum().sum() > 0:
        raise ValueError("Dữ liệu có giá trị thiếu ở các cột bắt buộc")
    return df


def t_min(cfg: dict, udi: int) -> float:
    """UDI -> phút kể từ t0 (giả định takt cố định)."""
    return (udi - 1) * cfg["takt_min"]


def iso(cfg: dict, minutes: float) -> str:
    return (pd.Timestamp(cfg["t0"]) + pd.Timedelta(minutes=float(minutes))).strftime("%Y-%m-%d %H:%M")


# =============================================================================
# 2. LỚP NGHIỆP VỤ GIẢ LẬP: ĐƠN HÀNG + PHÂN BỔ SẢN PHẨM -> ĐƠN
# =============================================================================
def build_orders(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(cfg["seed"])
    rows, order_of = [], {}
    for tp, n in cfg["orders_per_type"].items():
        udis = df.loc[df["Type"] == tp, "UDI"].to_numpy()
        for k, chunk in enumerate(np.array_split(udis, n), start=1):
            oid = f"ORD_{tp}{k:02d}"
            first_udi, last_udi = int(chunk[0]), int(chunk[-1])
            planned_finish = t_min(cfg, last_udi) + cfg["takt_min"]
            lo, hi = cfg["slack_range_min"]
            slack = int(min(max(rng.exponential(cfg["slack_mean_min"]), lo), hi))
            rows.append(dict(
                order_id=oid, product=tp, qty=len(chunk),
                first_udi=first_udi, last_udi=last_udi,
                first_min=t_min(cfg, first_udi), last_min=planned_finish,
                due_min=planned_finish + slack, slack_min=slack,
                priority=int(rng.choice([1, 2, 3], p=cfg["priority_p"])),
                customer=f"KH{int(rng.integers(1, 6))}",
            ))
            for u in chunk:
                order_of[int(u)] = oid
    return pd.DataFrame(rows), order_of


# =============================================================================
# 3. XÂY ĐỒ THỊ 2 LỚP
# =============================================================================
def build_graph(df: pd.DataFrame, orders: pd.DataFrame, order_of: dict, cfg: dict) -> nx.DiGraph:
    G = nx.DiGraph()
    train = df.iloc[: int(len(df) * cfg["train_frac"])]

    # --- lớp Logic: cảm biến, kiểu lỗi, máy ---
    for s, col in SENSORS.items():
        G.add_node(s, layer="logic", type="sensor", column=col, name=col, sd=float(train[col].std()))
    counts = {m: int(train[m].sum()) + 1 for m in MODES}            # Laplace +1
    tot = sum(counts.values())
    for m, name in MODES.items():
        G.add_node(f"FM_{m}", layer="logic", type="failure_mode", code=m, name=name,
                   prior=counts[m] / tot, count=counts[m])
        for s in MODE_SENSORS[m]:
            G.add_edge(s, f"FM_{m}", rel="evidence_for")
        G.add_edge(f"FM_{m}", "M05", rel="can_occur_on")
    for mid, name in [("M03", "Máy cắt phôi (thượng nguồn)"), ("M05", "Máy phay (có dữ liệu AI4I)"),
                      ("M07", "Máy phay dự phòng"), ("M09", "Máy lắp ráp/kiểm tra (hạ nguồn)")]:
        G.add_node(mid, layer="logic", type="machine", name=name)
    for s in SENSORS:
        G.add_edge(s, "M05", rel="monitors")
    G.nodes["M05"]["fail_per_1000"] = round(1000.0 * float(train["Machine failure"].sum()) / len(train), 2)

    # --- lớp Logic: công đoạn, linh kiện, sản phẩm (cạnh flow=True là dòng chảy vật liệu) ---
    for pid, name in [("P01", "Cắt phôi"), ("P02", "Phay"), ("P03", "Lắp ráp & kiểm tra")]:
        G.add_node(pid, layer="logic", type="process", name=name)
    G.add_node("A11", layer="logic", type="part", name="Phôi A11")
    G.add_node("A13", layer="logic", type="part", name="Chi tiết phay A13")
    for tp in "LMH":
        G.add_node(f"PRD_{tp}", layer="logic", type="product", name=f"Sản phẩm loại {tp}",
                   variant=tp, fg_buffer_min=cfg["fg_buffer_min"][tp])

    def flow(u, v, rel, w=1.0, buf=0.0, kind=None):
        G.add_edge(u, v, rel=rel, flow=True, w=w, buffer_min=buf, stock_kind=kind)

    flow("M03", "P01", "performs")
    flow("P01", "A11", "produces")
    flow("A11", "P02", "consumed_by", 1.0, cfg["buf_a11_p02"], "raw_material")
    flow("M05", "P02", "performs")
    flow("P02", "A13", "produces", 0.90, cfg["buf_p02_a13"], "wip")
    flow("A13", "P03", "consumed_by", 0.95, cfg["buf_a13_p03"], "wip")
    flow("M09", "P03", "performs")
    for tp in "LMH":
        flow("P03", f"PRD_{tp}", "produces", 0.90, cfg["fg_buffer_min"][tp], "finished_goods")
    G.add_edge("M07", "P02", rel="can_perform", capacity_share=cfg["substitute_share"])

    # --- lớp Nghiệp vụ: đơn hàng ---
    for o in orders.itertuples():
        G.add_node(o.order_id, layer="business", type="order", name=o.order_id,
                   product=o.product, qty=int(o.qty), priority=int(o.priority),
                   customer=o.customer, first_udi=int(o.first_udi), last_udi=int(o.last_udi),
                   first_min=float(o.first_min), last_min=float(o.last_min),
                   due_min=float(o.due_min), slack_min=float(o.slack_min))
        flow(f"PRD_{o.product}", o.order_id, "requested")

    # --- cầu nối: Lô -> Đơn ---
    lot_of = (df["UDI"] - 1) // cfg["lot_size"] + 1
    for lot in sorted(lot_of.unique()):
        lo = int(lot)
        G.add_node(f"LOT_{lo:03d}", layer="logic", type="lot", name=f"Lô {lo:03d}",
                   udi_start=(lo - 1) * cfg["lot_size"] + 1, udi_end=lo * cfg["lot_size"])
        G.add_edge("P02", f"LOT_{lo:03d}", rel="processed_in")
    alloc = Counter((int(lot_of[i]), order_of[int(u)]) for i, u in enumerate(df["UDI"]))
    for (lo, oid), n in alloc.items():
        G.add_edge(f"LOT_{lo:03d}", oid, rel="allocated_to", qty=n)

    # --- bộ phận phụ trách (thuộc lớp Nghiệp vụ) ---
    for dept in sorted(set(DEPT_OF_TYPE.values())):
        G.add_node(f"DEPT_{dept}", layer="business", type="department", name=dept)
    for n, d in list(G.nodes(data=True)):
        dept = DEPT_OF_TYPE.get(d["type"])
        if dept:
            d["owner_dept"] = dept
            G.add_edge(n, f"DEPT_{dept}", rel="owned_by")

    G.graph["flow"] = nx.DiGraph([(u, v, d) for u, v, d in G.edges(data=True) if d.get("flow")])
    G.graph["order_of"] = order_of
    G.graph["cfg"] = cfg
    return G


# =============================================================================
# 4. TRUY VẾT NGƯỢC: XẾP HẠNG NGUYÊN NHÂN
# =============================================================================
def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 50.0), -50.0)))


# Bằng chứng mềm theo luật chuyên gia (khớp tài liệu mô tả dataset AI4I 2020).
# Khi triển khai thật: thay bằng luật FMEA/kinh nghiệm kỹ sư DENSO.
def ev_twf(v, t):
    return _sig((v["S_WEAR"] - 200.0) / 8.0)

def ev_hdf(v, t):
    return _sig((8.6 - (v["S_PROC"] - v["S_AIR"])) / 0.4) * _sig((1380.0 - v["S_RPM"]) / 40.0)

def ev_pwf(v, t):
    p = v["S_TORQUE"] * v["S_RPM"] * 2.0 * math.pi / 60.0
    return max(_sig((3500.0 - p) / 150.0), _sig((p - 9000.0) / 300.0))

def ev_osf(v, t):
    thr = {"L": 11000.0, "M": 12000.0, "H": 13000.0}[t]
    return _sig((v["S_WEAR"] * v["S_TORQUE"] - thr) / 500.0)

def ev_rnf(v, t):
    return 0.05

EVIDENCE = {"TWF": ev_twf, "HDF": ev_hdf, "PWF": ev_pwf, "OSF": ev_osf, "RNF": ev_rnf}


def rank_causes(G: nx.DiGraph, row: pd.Series, machine: str = "M05",
                noise: float = 0.0, rng: np.random.Generator | None = None,
                use_evidence: bool = True, hints: set | None = None,
                priors: dict | None = None, hint_boost: float | None = None,
                prior_smoothing: float | None = None) -> list[dict]:
    """Xếp hạng nguyên nhân. Chỉ dùng giá trị cảm biến tại thời điểm sự cố.
    `hints`: tập mã nguyên nhân do P1 nghi ngờ; được nhân thêm cfg['hint_boost'] (gợi ý, không phải bằng chứng).
    `priors`: ghi đè prior theo mã (dùng cho đánh giá leave-one-out); `hint_boost`: ghi đè hệ số gợi ý."""
    cfg = G.graph["cfg"]
    boost_v = cfg["hint_boost"] if hint_boost is None else hint_boost
    lam = cfg.get("prior_smoothing", 0.0) if prior_smoothing is None else prior_smoothing
    vals = {}
    for s, d in G.nodes(data=True):
        if d["type"] == "sensor":
            x = float(row[d["column"]])
            if noise > 0 and rng is not None:
                x += rng.normal(0.0, noise * d["sd"])   # noise = tỉ lệ so với độ lệch chuẩn cảm biến
            vals[s] = x
    res = []
    for fm in G.predecessors(machine):
        d = G.nodes[fm]
        if d["type"] != "failure_mode":
            continue
        e = EVIDENCE[d["code"]](vals, row["Type"]) if use_evidence else 1.0
        boost = boost_v if hints and d["code"] in hints else 1.0
        pr = d["prior"] if priors is None else priors[d["code"]]
        pr = (1.0 - lam) * pr + lam / len(MODES)
        res.append(dict(cause=d["code"], name=d["name"], prior=pr, evidence=e,
                        raw=pr * (e + cfg["evidence_eps"]) * boost))
    z = sum(r["raw"] for r in res)
    for r in res:
        r["score"] = r["raw"] / z
        r.pop("raw")
    return sorted(res, key=lambda r: -r["score"])


def loo_priors(G: nx.DiGraph, row: pd.Series) -> dict:
    """Prior bỏ chính dòng đang đánh giá (leave-one-out) để tập 'all_failures' không bị rò nhãn."""
    c = {d["code"]: max(d["count"] - int(row[d["code"]]), 1)
         for _, d in G.nodes(data=True) if d["type"] == "failure_mode"}
    z = sum(c.values())
    return {k: v / z for k, v in c.items()}


def expected_effect(causes: list[dict], cfg: dict) -> tuple[float, float]:
    """Thời gian dừng và mức nghiêm trọng kỳ vọng theo phân bố nguyên nhân."""
    d = sum(c["score"] * cfg["downtime_min"][c["cause"]] for c in causes)
    s = sum(c["score"] * cfg["severity"][c["cause"]] for c in causes)
    return d, s


# =============================================================================
# 5. TRUY VẾT XUÔI: LAN TRUYỀN TÁC ĐỘNG
# =============================================================================
def trace_forward(G: nx.DiGraph, src: str, udi: int, sev: float, downtime: float,
                  use_substitute: bool = True, thr: float | None = None) -> dict:
    """Lan truyền từ nút nguồn `src` (máy hoặc linh kiện) tại sản phẩm thứ `udi`.

    Máy dự phòng (rel='can_perform') gánh một phần tải nên giảm THỜI GIAN DỪNG HIỆU DỤNG;
    giá trị này dùng nhất quán cho độ che phủ của đệm, độ trễ đơn hàng và cửa sổ sản phẩm trễ.
    """
    cfg = G.graph["cfg"]
    thr = cfg["risk_thr"] if thr is None else thr
    F = G.graph["flow"]
    if src not in F:
        valid = sorted(n for n in F if F.out_degree(n) > 0)
        raise ValueError(f"Nguồn '{src}' không thuộc đồ thị dòng chảy vật liệu. Nguồn hợp lệ: {valid}")
    if udi not in G.graph["order_of"]:
        raise ValueError(f"UDI {udi} nằm ngoài phạm vi dữ liệu (1..{max(G.graph['order_of'])})")
    if not 0.0 <= sev <= 1.0:
        raise ValueError(f"severity phải nằm trong [0, 1], nhận {sev}")
    if downtime < 0:
        raise ValueError(f"downtime phải >= 0, nhận {downtime}")
    inc_min = t_min(cfg, udi)

    # máy dự phòng cho công đoạn mà nguồn đang thực hiện
    subs = {}
    if G.nodes[src]["type"] == "machine":
        for v in F.successors(src):
            for m in G.predecessors(v):
                if G[m][v].get("rel") == "can_perform":
                    subs[m] = dict(machine_id=m, name=G.nodes[m]["name"], process=v,
                                   capacity_share=G[m][v]["capacity_share"])
    share = min(1.0, sum(x["capacity_share"] for x in subs.values())) if use_substitute else 0.0
    eff_down = downtime * (1.0 - share)

    state = {src: dict(risk=sev, w=1.0, buf=0.0, parent=None)}
    for u in nx.topological_sort(F):
        if u not in state:
            continue
        su = state[u]
        for v in F.successors(u):
            e = F[u][v]
            w = su["w"] * e["w"]
            buf = su["buf"] + e.get("buffer_min", 0.0)
            cover = min(1.0, buf / eff_down) if eff_down > 0 else 1.0
            r = sev * w * (1.0 - cover)
            if v not in state or r > state[v]["risk"]:
                state[v] = dict(risk=r, w=w, buf=buf, parent=u)

    def path_of(n):
        p = [n]
        while state[p[-1]]["parent"] is not None:
            p.append(state[p[-1]]["parent"])
        return p[::-1]

    # cửa sổ sản phẩm bị trễ trực tiếp (sau khi hết đệm đầu nguồn)
    first_buf = min((F[src][v].get("buffer_min", 0.0) for v in F.successors(src)), default=0.0)
    n_first = int(math.ceil(max(0.0, eff_down - first_buf) / cfg["takt_min"]))
    start = udi + int(first_buf / cfg["takt_min"])
    window = [u for u in range(start, start + n_first) if u in G.graph["order_of"]]
    direct_by_order = Counter(G.graph["order_of"][u] for u in window)
    direct_lots = Counter((u - 1) // cfg["lot_size"] + 1 for u in window)

    affected, all_orders = [], []
    for n, st in state.items():
        if n == src:
            continue
        d = G.nodes[n]
        if d["type"] in ("process", "part", "product"):
            if st["risk"] >= thr:
                affected.append(dict(
                    id=n, name=d["name"], type=d["type"], layer="logic",
                    owner_dept=d.get("owner_dept"), cum_buffer_min=round(st["buf"], 1),
                    risk=round(st["risk"], 3), path=path_of(n),
                    reason=f"Phụ thuộc {src} qua {len(path_of(n)) - 1} bước, đệm tích lũy {st['buf']:.0f} phút "
                           f"so với dừng hiệu dụng {eff_down:.0f} phút"))
        elif d["type"] == "order":
            if d["last_min"] <= inc_min:
                continue                                   # đã giao xong trước sự cố
            hours = (d["last_min"] - inc_min) / 60.0
            eff_delay = max(0.0, eff_down - st["buf"]) * math.exp(-hours / cfg["recovery_tau_h"])
            slack = d["slack_min"]
            urgency = min(1.0, eff_delay / max(slack, 1.0))      # trễ càng áp sát thời gian dư càng khẩn
            risk = st["risk"] * urgency * cfg["prio_factor"][d["priority"]]
            rec = dict(id=n, name=n, type="order", layer="business", owner_dept=d.get("owner_dept"),
                       risk=round(risk, 3), _delay_raw=eff_delay, cum_buffer_min=round(st["buf"], 1),
                       path=path_of(n), reach=round(st["risk"], 3),
                       delay_min=round(eff_delay, 1), slack_min=int(slack),
                       miss_deadline=bool(eff_delay > slack), priority=d["priority"],
                       product=d["product"], qty=d["qty"], customer=d["customer"],
                       due=iso(cfg, d["due_min"]),
                       time_to_impact_min=round(max(0.0, d["first_min"] - inc_min), 1),
                       direct_units=int(direct_by_order.get(n, 0)))
            rec["reason"] = (f"Trễ dự kiến {eff_delay:.0f} phút, dư thời gian {slack:.0f} phút, "
                             f"ưu tiên {d['priority']}"
                             + (" -> NGUY CƠ TRỄ HẠN" if rec["miss_deadline"] else ""))
            all_orders.append(rec)
            if risk >= thr:
                affected.append(rec)
    affected.sort(key=lambda r: -r["risk"])
    on_path = {n for a in affected for n in a["path"]}
    buffers = [dict(src=u, dst=v, buffer_min=e["buffer_min"], kind=e.get("stock_kind"))
               for u, v, e in F.edges(data=True)
               if e.get("buffer_min", 0) > 0 and u in on_path and v in on_path]
    return dict(source=src, buffers=buffers, incident_time=iso(cfg, inc_min), downtime_min=round(downtime, 1),
                effective_downtime_min=round(eff_down, 1), severity=round(sev, 3), affected=affected,
                direct_lots=[dict(lot=f"LOT_{l:03d}", units_delayed=n) for l, n in sorted(direct_lots.items())],
                substitutes=list(subs.values()), _all_orders=all_orders)


# =============================================================================
# 5b. GIAO DIỆN: BẢN GHI SỰ CỐ (VÀO, từ P1) VÀ ImpactReport (RA, cho P3)
# =============================================================================
_TIME_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
                 "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")


def udi_from_time(G: nx.DiGraph, text: str) -> int:
    """Đổi mốc thời gian (dạng trong tài liệu D3: '15/09/2026 10:32') sang số thứ tự sản phẩm UDI."""
    cfg = G.graph["cfg"]
    ts = None
    for f in _TIME_FORMATS:
        try:
            ts = datetime.strptime(text.strip(), f)
            break
        except ValueError:
            continue
    if ts is None:
        raise ValueError(f"Không đọc được 'time' = {text!r}. Hỗ trợ 'DD/MM/YYYY HH:MM' hoặc 'YYYY-MM-DD HH:MM'")
    minutes = (pd.Timestamp(ts) - pd.Timestamp(cfg["t0"])).total_seconds() / 60.0
    udi = int(round(minutes / cfg["takt_min"])) + 1
    if udi not in G.graph["order_of"]:
        last = max(G.graph["order_of"])
        raise ValueError(f"'time' {text} nằm ngoài dòng thời gian dữ liệu ({iso(cfg, 0)} .. {iso(cfg, t_min(cfg, last))})")
    return udi


def _parse_hints(raw) -> tuple[set, list]:
    """'Nhóm nguyên nhân nghi ngờ' của P1 -> (mã nguyên nhân P2 hiểu được, phần không khớp)."""
    if raw is None:
        return set(), []
    items = [raw] if isinstance(raw, str) else list(raw)
    by_name = {v.lower(): k for k, v in MODES.items()}
    ok, ignored = set(), []
    for it in items:
        x = str(it).strip()
        if x.upper() in MODES:
            ok.add(x.upper())
        elif x.lower() in by_name:
            ok.add(by_name[x.lower()])
        else:
            ignored.append(x)
    return ok, ignored


def prepare_record(G: nx.DiGraph, rec: dict, dfi: pd.DataFrame | None = None) -> dict:
    """Chuẩn hóa bản ghi theo định dạng mục 5.3 của tài liệu D3 về dạng chuẩn của P2:
      - 'time' (DD/MM/YYYY HH:MM) -> 'udi'
      - 'level' Cao/Trung bình/Thấp -> 'severity' (số), trừ khi P1 đã gửi 'severity'
      - thiếu 'sensors'/'type'/'product_id' -> đọc từ tầng dữ liệu `dfi` theo udi (mục 4, tầng 1)
    """
    if not isinstance(rec, dict):
        raise ValueError("Bản ghi sự cố phải là một JSON object")
    r = dict(rec)
    if r.get("time") is not None and not isinstance(r["time"], str):
        raise ValueError("'time' phải là chuỗi")
    if r.get("udi") is None:
        if r.get("time") is None:
            raise ValueError("Bản ghi cần 'udi' hoặc 'time'")
        r["udi"] = udi_from_time(G, r["time"])
    elif r.get("time") is not None and isinstance(r["udi"], int) and not isinstance(r["udi"], bool):
        u2 = udi_from_time(G, r["time"])
        if abs(u2 - r["udi"]) > 1:
            raise ValueError(f"'udi' ({r['udi']}) và 'time' ({r['time']}, tương ứng udi {u2}) mâu thuẫn nhau")
    if r.get("severity") is None and r.get("level") is not None:
        sev = G.graph["cfg"]["level_to_severity"].get(str(r["level"]).strip().lower())
        if sev is None:
            raise ValueError(f"'level' = {r['level']!r} không hợp lệ; dùng Cao / Trung bình / Thấp")
        r["severity"] = sev
    m = r.get("machine_id")
    has_fm = (m in G and G.nodes[m]["type"] == "machine"
              and any(G.nodes[p]["type"] == "failure_mode" for p in G.predecessors(m)))
    if (has_fm and dfi is not None and isinstance(r.get("udi"), int)
            and not isinstance(r["udi"], bool) and r["udi"] in dfi.index):
        row = dfi.loc[r["udi"]]
        if not r.get("sensors"):
            r["sensors"] = {c: float(row[c]) for c in SENSORS.values()}
        if r.get("type") is None:
            r["type"] = row["Type"]
        if r.get("product_id") is None:
            r["product_id"] = row["Product ID"]
    return r


def validate_record(G: nx.DiGraph, rec: dict) -> dict:
    """Kiểm tra bản ghi (đã qua prepare_record). Ném ValueError có thông báo rõ ràng."""
    if not isinstance(rec, dict):
        raise ValueError("Bản ghi sự cố phải là một JSON object")
    miss = [k for k in ("incident_id", "udi", "machine_id") if k not in rec]
    if miss:
        raise ValueError(f"Bản ghi thiếu trường bắt buộc: {miss}")
    udi = rec["udi"]
    if isinstance(udi, bool) or not isinstance(udi, int) or udi not in G.graph["order_of"]:
        raise ValueError(f"udi phải là số nguyên trong 1..{max(G.graph['order_of'])}, nhận {udi!r}")
    m = rec["machine_id"]
    if m not in G or G.nodes[m]["type"] != "machine":
        raise ValueError(f"machine_id '{m}' không phải máy trong đồ thị")
    for k in ("severity", "anomaly_score"):
        v = rec.get(k)
        if v is not None and not (isinstance(v, (int, float)) and 0.0 <= v <= 1.0):
            raise ValueError(f"{k} phải là số trong [0, 1], nhận {v!r}")
    has_fm = any(G.nodes[p]["type"] == "failure_mode" for p in G.predecessors(m))
    if has_fm:
        if rec.get("type") not in ("L", "M", "H"):
            raise ValueError("Thiếu 'type' (L/M/H) của sản phẩm (hoặc truyền dfi để P2 tự đọc từ dữ liệu)")
        sens = rec.get("sensors")
        bad = [c for c in SENSORS.values()
               if not isinstance(sens, dict) or not isinstance(sens.get(c), (int, float))
               or not math.isfinite(sens[c])]
        if bad:
            raise ValueError(f"'sensors' thiếu hoặc không phải số: {bad} (hoặc truyền dfi để P2 tự đọc)")
    else:
        for k in ("downtime_min", "severity"):
            if not isinstance(rec.get(k), (int, float)):
                raise ValueError(f"Máy {m} chưa có mô hình nguyên nhân: bản ghi phải có '{k}' hoặc 'level' (từ P1)"
                                 if k == "severity" else
                                 f"Máy {m} chưa có mô hình nguyên nhân: bản ghi phải có '{k}' (ước lượng từ P1)")
    return rec


def _by_department(G: nx.DiGraph, affected: list[dict], trigger: dict, effect: dict) -> dict:
    """Nhóm theo bộ phận, GỒM cả bộ phận của nút nguồn (role='source') để bảng hành động không thiếu
    bộ phận phải hành động đầu tiên. count = số mục trong items."""
    out: dict = {}

    def slot(dep):
        return out.setdefault(dep or "Khác", dict(count=0, max_risk=0.0, items=[], roles=[]))

    for a in affected:
        slot(a.get("owner_dept"))["items"].append(
            dict(id=a["id"], type=a["type"], risk=a.get("risk"), role="affected"))
    src = trigger["source_node"]
    existing = [it for g in out.values() for it in g["items"] if it["id"] == src]
    if existing:
        existing[0]["role"] = "source+affected"
    else:
        slot(trigger.get("owner_dept"))["items"].append(
            dict(id=src, type=G.nodes[src]["type"], risk=effect.get("severity"), role="source"))
    for g in out.values():
        g["count"] = len(g["items"])
        g["max_risk"] = max([it["risk"] for it in g["items"] if it["risk"] is not None], default=0.0)
        g["roles"] = sorted({it["role"] for it in g["items"]})
    return out


def _assumptions(cfg: dict) -> dict:
    return dict(
        business_layer="synthetic",
        takt_min=cfg["takt_min"], substitute_share=cfg["substitute_share"],
        recovery_tau_h=cfg["recovery_tau_h"], slack_mean_min=cfg["slack_mean_min"],
        priority_factor={str(k): v for k, v in cfg["prio_factor"].items()},
        downtime_min_by_cause=cfg["downtime_min"], severity_by_cause=cfg["severity"],
        note="Đơn hàng, đệm, thời gian dừng, máy dự phòng là giả lập; cần hiệu chỉnh bằng dữ liệu DENSO.")


def make_report(G, scenario: str, trigger: dict, causes: list, effect: dict, forward: dict | None = None,
                affected: list | None = None, contributing: list | None = None,
                selection: str | None = None, eval_only: dict | None = None) -> dict:
    """ImpactReport thống nhất cho mọi tình huống (schema: p2_impact_report.schema.json)."""
    aff = forward["affected"] if forward else (affected or [])
    rep = dict(schema_version=SCHEMA_VERSION, scenario=scenario, selection=selection,
               trigger=trigger, causes=causes, effect=effect, affected=aff,
               by_department=_by_department(G, aff, trigger, effect),
               substitutes=forward["substitutes"] if forward else [],
               buffers=forward["buffers"] if forward else [],
               direct_lots=forward["direct_lots"] if forward else [],
               contributing_incidents=contributing or [],
               assumptions=_assumptions(G.graph["cfg"]))
    if eval_only:
        rep["eval_only"] = eval_only
    if forward:
        rep["_all_orders"] = forward["_all_orders"]
    return rep


def analyze_record(G, rec: dict, noise: float = 0.0, rng: np.random.Generator | None = None,
                   dfi: pd.DataFrame | None = None) -> dict:
    """ĐIỂM CẮM CỦA P1: bản ghi sự cố (định dạng mục 5.3) -> truy vết ngược -> kỳ vọng -> truy vết xuôi
    -> ImpactReport. Không đọc nhãn lỗi. Nếu bản ghi không có cảm biến thì đọc từ `dfi` theo udi."""
    rec = validate_record(G, prepare_record(G, rec, dfi))
    cfg = G.graph["cfg"]
    machine, udi = rec["machine_id"], rec["udi"]
    has_fm = any(G.nodes[p]["type"] == "failure_mode" for p in G.predecessors(machine))
    hints, ignored = _parse_hints(rec.get("suspected_cause_group"))
    history = None
    if has_fm:
        row = pd.Series({**{c: float(rec["sensors"][c]) for c in SENSORS.values()}, "Type": rec["type"]})
        ranked = rank_causes(G, row, machine, noise, rng, hints=hints)
        d_hat, s_hat = expected_effect(ranked, cfg)
        sev_src = "cause_mixture"
        causes = [dict(cause=c["cause"], name=c["name"], score=round(c["score"], 3),
                       prior=round(c["prior"], 3), evidence=round(c["evidence"], 3)) for c in ranked]
        if rec.get("severity") is not None:                    # P1 chỉ định thì ưu tiên P1
            s_hat, sev_src = float(rec["severity"]), "P1"
        if "fail_per_1000" in G.nodes[machine]:
            history = dict(machine_failures_per_1000_units=G.nodes[machine]["fail_per_1000"],
                           top_cause=ranked[0]["cause"], top_cause_historical_share=round(ranked[0]["prior"], 3))
    else:
        d_hat, s_hat, sev_src, causes = float(rec["downtime_min"]), float(rec["severity"]), "P1", []
    fwd = trace_forward(G, machine, udi, s_hat, d_hat)
    trigger = dict(type="machine_incident", id=rec["incident_id"], source_node=machine, machine_id=machine,
                   owner_dept=G.nodes[machine].get("owner_dept"), time=iso(cfg, t_min(cfg, udi)), udi=udi,
                   product_id=rec.get("product_id"),
                   details=dict(anomaly_score=rec.get("anomaly_score"), anomaly_type=rec.get("anomaly_type"),
                                level=rec.get("level"), suspected_cause_group=rec.get("suspected_cause_group"),
                                hints_applied=sorted(hints), hints_ignored=ignored, history=history,
                                node_id=rec.get("node_id", machine), dataset=rec.get("dataset", "AI4I2020"),
                                timestamp_is_synthetic=bool(rec.get("timestamp_is_synthetic", True))))
    effect = dict(downtime_min=round(d_hat, 1), effective_downtime_min=fwd["effective_downtime_min"],
                  severity=round(s_hat, 3), severity_source=sev_src, _downtime_raw=d_hat)
    return make_report(G, "machine_incident", trigger, causes, effect, forward=fwd)


def graph_view(G: nx.DiGraph, report: dict | None = None) -> dict:
    """Đồ thị rút gọn cho dashboard (D3.js/Cytoscape): nút có risk và dải màu, cạnh có on_path.
    Không đưa lô, bộ phận và các đơn hàng không bị ảnh hưởng vào để hình gọn."""
    risk, on_path, src = {}, set(), None
    if report:
        src = report["trigger"]["source_node"]
        for a in report["affected"]:
            if a.get("risk") is not None:
                risk[a["id"]] = a["risk"]
            on_path |= set(zip(a["path"], a["path"][1:]))
        if report["effect"]["severity"] is not None:
            risk[src] = report["effect"]["severity"]
    show = {"sensor", "failure_mode", "machine", "process", "part", "product"}
    keep = {n for n, d in G.nodes(data=True) if d["type"] in show}
    if report:
        keep |= {a["id"] for a in report["affected"] if a["type"] == "order"} | {src}
    nodes = []
    for n in keep:
        d, r = G.nodes[n], risk.get(n)
        band = None if r is None else ("high" if r >= 0.5 else "medium" if r >= 0.25 else "low")
        nodes.append(dict(id=n, name=d["name"], type=d["type"], layer=d["layer"],
                          owner_dept=d.get("owner_dept"), risk=r, band=band, is_source=(n == src)))
    rels = {"monitors", "evidence_for", "can_occur_on", "can_perform", "performs", "produces",
            "consumed_by", "requested"}
    edges = [dict(source=u, target=v, rel=e["rel"], buffer_min=e.get("buffer_min"),
                  on_path=((u, v) in on_path))
             for u, v, e in G.edges(data=True) if u in keep and v in keep and e.get("rel") in rels]
    return dict(schema_version="p2.graph_view.v1", scenario=report["scenario"] if report else None,
                nodes=sorted(nodes, key=lambda x: x["id"]), edges=edges,
                legend=dict(band={"high": "risk >= 0.5", "medium": "risk >= 0.25", "low": "risk > 0"}))


def record_from_row(row: pd.Series, machine_id: str = "M05") -> dict:
    """Dựng IncidentRecord từ một dòng AI4I (mô phỏng đầu ra của P1; KHÔNG chứa nhãn)."""
    return dict(incident_id=f"INC_{int(row['UDI']):05d}", udi=int(row["UDI"]), machine_id=machine_id,
                product_id=row["Product ID"], type=row["Type"],
                sensors={c: float(row[c]) for c in SENSORS.values()})


def analyze_incident(G, dfi: pd.DataFrame, udi: int, noise=0.0, rng=None) -> dict:
    """Tiện ích cho đánh giá: dựng bản ghi từ dataframe rồi gọi analyze_record.
    Nhãn thật chỉ nằm trong khóa 'eval_only'."""
    if udi not in dfi.index:
        raise ValueError(f"UDI {udi} không có trong dữ liệu")
    row = dfi.loc[udi]
    rep = analyze_record(G, record_from_row(row), noise, rng)
    rep["eval_only"] = dict(label_modes=[m for m in MODES if row[m] == 1])
    return rep


def report_order_backward(G, dfi: pd.DataFrame, order_id: str) -> dict:
    """Tình huống 2: truy vết ngược từ đơn hàng có sản phẩm lỗi, đóng gói thành ImpactReport."""
    cfg = G.graph["cfg"]
    raw = trace_backward_order(G, dfi, order_id)
    o = G.nodes[order_id]
    n_def = raw["defective_units"]
    causes = [dict(cause=r["cause"], name=r["name"], score=r["share"], prior=None, evidence=None)
              for r in raw["cause_ranking"]]
    entry = dict(id=order_id, name=order_id, type="order", layer="business", owner_dept=o.get("owner_dept"),
                 risk=None, path=[], reason=f"{n_def}/{o['qty']} sản phẩm lỗi trong đơn hàng",
                 defect_rate=round(n_def / o["qty"], 3), product=o["product"], qty=o["qty"],
                 priority=o["priority"], customer=o["customer"], due=iso(cfg, o["due_min"]))
    trigger = dict(type="defective_order", id=order_id, source_node=order_id, owner_dept=o.get("owner_dept"),
                   time=raw["order"]["finish"], details=dict(order=raw["order"], defective_units=n_def,
                                                              defective_unit_details=raw["defective_unit_details"]))
    effect = dict(downtime_min=None, effective_downtime_min=None, severity=None, severity_source=None)
    return make_report(G, "order_backward", trigger, causes, effect, affected=[entry],
                       contributing=raw["top_delay_incidents"])


def report_material_delay(G, part: str, udi: int, delay_min: float, severity: float) -> dict:
    """Tình huống 3: biến động từ nhà cung cấp (linh kiện giao trễ), đóng gói thành ImpactReport."""
    cfg = G.graph["cfg"]
    fwd = trace_forward(G, part, udi, severity, delay_min)
    F = G.graph["flow"]
    buf = min(F[part][v].get("buffer_min", 0.0) for v in F.successors(part))
    trigger = dict(type="supplier_delay", id=f"SUP_{part}_{udi:05d}", source_node=part,
                   owner_dept=G.nodes[part].get("owner_dept"), time=iso(cfg, t_min(cfg, udi)), udi=udi,
                   details=dict(part=part, delay_min=delay_min, buffer_min=buf))
    effect = dict(downtime_min=delay_min, effective_downtime_min=fwd["effective_downtime_min"],
                  severity=severity, severity_source="assumed")
    return make_report(G, "material_delay", trigger, [], effect, forward=fwd)


def trace_backward_order(G, dfi: pd.DataFrame, order_id: str, lookback_h: float = 72.0) -> dict:
    """Truy vết ngược từ ĐƠN HÀNG có sản phẩm lỗi/nguy cơ trễ."""
    cfg = G.graph["cfg"]
    o = G.nodes[order_id]
    units = dfi[(dfi["Type"] == o["product"]) & (dfi["UDI"].between(o["first_udi"], o["last_udi"]))]
    failed = units[units["Machine failure"] == 1]
    agg, per_unit = Counter(), []
    for udi, row in failed.iterrows():
        cs = rank_causes(G, row)
        for c in cs:
            agg[c["cause"]] += c["score"]
        per_unit.append(dict(udi=int(udi), product_id=row["Product ID"], top_cause=cs[0]["cause"],
                             top_score=round(cs[0]["score"], 3)))
    n = max(len(failed), 1)
    ranking = [dict(cause=k, name=MODES[k], share=round(v / n, 3)) for k, v in agg.most_common()]

    # sự cố trước thời điểm đơn xong (nguyên tắc thời gian) -> đóng góp vào độ trễ
    end = o["last_min"]
    contrib = []
    past = dfi[(dfi["Machine failure"] == 1) & (dfi.index.map(lambda u: t_min(cfg, u)) < end) &
               (dfi.index.map(lambda u: t_min(cfg, u)) >= end - lookback_h * 60)]
    for udi, row in past.iterrows():
        cs = rank_causes(G, row)
        d_hat, _ = expected_effect(cs, cfg)
        h = (end - t_min(cfg, udi)) / 60.0
        contrib.append(dict(udi=int(udi), time=iso(cfg, t_min(cfg, udi)), top_cause=cs[0]["cause"],
                            expected_downtime_min=round(d_hat, 1),
                            delay_contribution_min=round(d_hat * (1.0 - cfg["substitute_share"]) * math.exp(-h / cfg["recovery_tau_h"]), 1)))
    contrib.sort(key=lambda r: -r["delay_contribution_min"])
    return dict(order=dict(id=order_id, product=o["product"], qty=o["qty"], priority=o["priority"],
                           first=iso(cfg, o["first_min"]), finish=iso(cfg, o["last_min"]), due=iso(cfg, o["due_min"])),
                defective_units=len(failed), cause_ranking=ranking,
                defective_unit_details=per_unit[:15], top_delay_incidents=contrib[:5])


# =============================================================================
# 6. ĐÁNH GIÁ & KIỂM TRA TÍNH NHẤT QUÁN
# =============================================================================
def _train_max_udi(G, dfi: pd.DataFrame) -> int:
    cut = int(len(dfi) * G.graph["cfg"]["train_frac"])
    return int(dfi["UDI"].iloc[cut - 1])


def _per_class(conf: dict) -> dict:
    """Precision/recall/F1 theo lớp từ ma trận nhầm lẫn {thật: {dự đoán: số}}; macro-F1 có/không RNF."""
    per = {}
    for c in MODES:
        tp = conf[c][c]
        n_true = sum(conf[c].values())
        n_pred = sum(conf[t][c] for t in MODES)
        pr = tp / n_pred if n_pred else None
        rc = tp / n_true if n_true else None
        f1 = (2 * pr * rc / (pr + rc) if pr and rc else 0.0) if n_true else None
        per[c] = dict(n=n_true, precision=None if pr is None else round(pr, 3),
                      recall=None if rc is None else round(rc, 3), f1=None if f1 is None else round(f1, 3))
    f_all = [v["f1"] for v in per.values() if v["f1"] is not None]
    f_x = [v["f1"] for k, v in per.items() if v["f1"] is not None and k != "RNF"]
    return dict(per_class=per,
                macro_f1_all=round(float(np.mean(f_all)), 3) if f_all else None,
                macro_f1_excl_rnf=round(float(np.mean(f_x)), 3) if f_x else None)


def evaluate_backward(G, dfi: pd.DataFrame, noise_levels=(0.0, 0.10, 0.25, 0.50), reps=5) -> list[dict]:
    """noise_levels = tỉ lệ nhiễu so với độ lệch chuẩn (tập train) của từng cảm biến.
    Hai tập con: 'last_30pct' (prior không thấy dữ liệu test) và 'all_failures'
    (dòng thuộc tập train dùng prior leave-one-out; luật bằng chứng không được học từ nhãn).
    Confusion/per_class tính từ lần lặp đầu; hit = nguyên nhân đứng đầu thuộc tập nhãn thật."""
    cfg = G.graph["cfg"]
    cut = int(len(dfi) * cfg["train_frac"])
    train_max = _train_max_udi(G, dfi)
    has_mode = (dfi["Machine failure"] == 1) & (dfi[list(MODES)].sum(axis=1) > 0)
    subsets = {"last_30pct": dfi.iloc[cut:][has_mode.iloc[cut:]], "all_failures": dfi[has_mode]}
    out = []
    for sname, test in subsets.items():
        for method in ("prior_only", "prior+evidence"):
            for sigma in noise_levels:
                if method == "prior_only" and sigma > 0:
                    continue
                top1 = top2 = mrr = n = 0.0
                conf = {t: {p: 0 for p in MODES} for t in MODES}
                for rep in range(reps if sigma > 0 else 1):
                    rng = np.random.default_rng(cfg["seed"] + rep)
                    for udi, row in test.iterrows():
                        truth = [m for m in MODES if row[m] == 1]
                        pri = loo_priors(G, row) if udi <= train_max else None
                        rk = [c["cause"] for c in rank_causes(G, row, noise=sigma, rng=rng, priors=pri,
                                                              use_evidence=(method != "prior_only"))]
                        hit_rank = min(rk.index(m) for m in truth) + 1
                        top1 += hit_rank == 1
                        top2 += hit_rank <= 2
                        mrr += 1.0 / hit_rank
                        n += 1
                        if rep == 0:
                            conf[rk[0] if rk[0] in truth else truth[0]][rk[0]] += 1
                reps_used = reps if sigma > 0 else 1
                out.append(dict(subset=sname, method=method, noise_sd_frac=sigma, n=int(n) // reps_used,
                                top1=round(top1 / n, 3), top2=round(top2 / n, 3), mrr=round(mrr / n, 3),
                                n_by_mode={m: int(test[m].sum()) for m in MODES},
                                confusion=conf, **_per_class(conf)))
    return out


def evaluate_ml_baseline(G, dfi: pd.DataFrame) -> dict:
    """Đối chứng với random forest: (a) CV 5 fold trên các sự cố có nhãn; (b) bài test dịch chuyển phân phối:
    huấn luyện KHÔNG có lỗi HDF (toàn bộ HDF nằm trong một khoảng UDI), thử trong khoảng đó."""
    try:
        import warnings
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import StratifiedKFold
    except ImportError:
        return dict(skipped="scikit-learn chưa cài (pip install scikit-learn)")
    cfg = G.graph["cfg"]
    M = list(MODES)
    f = dfi[(dfi["Machine failure"] == 1) & (dfi[M].sum(axis=1) > 0)]
    y = f[M].values.argmax(axis=1)
    air, proc, rpm, tq, wear = (SENSORS[k] for k in ("S_AIR", "S_PROC", "S_RPM", "S_TORQUE", "S_WEAR"))

    def feats(d, physical):
        X = d[list(SENSORS.values())].copy()
        X["Type"] = d["Type"].map({"L": 0, "M": 1, "H": 2})
        if physical:
            X["temp_diff"] = d[proc] - d[air]
            X["power_w"] = d[tq] * d[rpm] * 2 * np.pi / 60
            X["wear_x_torque"] = d[wear] * d[tq]
        return X

    def fit_predict(Xtr, ytr, Xte):
        rf = RandomForestClassifier(300, random_state=cfg["seed"], class_weight="balanced").fit(Xtr, ytr)
        return rf.predict(Xte)

    def hit_rate(d, pred_idx):
        return round(float(np.mean([d.iloc[i][M[p]] == 1 for i, p in enumerate(pred_idx)])), 3)

    out = dict(n_failures_with_label=int(len(f)), cv5={})
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        skf = StratifiedKFold(5, shuffle=True, random_state=cfg["seed"])
        for name, phys in (("rf_raw_sensors", False), ("rf_physical_features", True)):
            X, hits = feats(f, phys), []
            for tr, te in skf.split(X, y):
                pred = fit_predict(X.iloc[tr], y[tr], X.iloc[te])
                hits += [f.iloc[i][M[p]] == 1 for i, p in zip(te, pred)]
            out["cv5"][name] = round(float(np.mean(hits)), 3)
        train_max = _train_max_udi(G, dfi)
        out["cv5"]["rule_prior_plus_evidence"] = round(float(np.mean([
            rank_causes(G, row, priors=loo_priors(G, row) if udi <= train_max else None)[0]["cause"]
            in {m for m in M if row[m] == 1} for udi, row in f.iterrows()])), 3)

        hdf = f[f["HDF"] == 1]["UDI"]
        lo, hi = int(hdf.min()), int(hdf.max())
        in_win = f["UDI"].between(lo, hi)
        tr_d, te_d = f[~in_win], f[in_win]
        counts = {m: int(tr_d[m].sum()) + 1 for m in M}
        z = sum(counts.values())
        pri = {m: counts[m] / z for m in M}
        drift = dict(hdf_udi_window=[lo, hi], train_n=int(len(tr_d)), test_n=int(len(te_d)),
                     train_hdf=int(tr_d["HDF"].sum()), test_hdf=int(te_d["HDF"].sum()))
        ytr = tr_d[M].values.argmax(axis=1)
        for name, phys in (("rf_raw_sensors", False), ("rf_physical_features", True)):
            drift[name] = hit_rate(te_d, fit_predict(feats(tr_d, phys), ytr, feats(te_d, phys)))
        in_set = lambda row, c: c in {m for m in M if row[m] == 1}
        drift["rule_prior_plus_evidence"] = round(float(np.mean([
            in_set(row, rank_causes(G, row, priors=pri, prior_smoothing=0.0)[0]["cause"])
            for _, row in te_d.iterrows()])), 3)
        # THĂM DÒ SAU KHI THẤY KẾT QUẢ (không phải tham số đã chốt): làm trơn prior có cứu được trường hợp
        # nguyên nhân chưa từng xuất hiện không, và trả giá gì trên dữ liệu bình thường?
        drift["rule_prior_smoothing_sweep"] = [
            dict(prior_smoothing=lam,
                 drift_top1=round(float(np.mean([
                     in_set(row, rank_causes(G, row, priors=pri, prior_smoothing=lam)[0]["cause"])
                     for _, row in te_d.iterrows()])), 3),
                 in_distribution_top1=round(float(np.mean([
                     in_set(row, rank_causes(G, row, priors=loo_priors(G, row) if udi <= train_max else None,
                                             prior_smoothing=lam)[0]["cause"])
                     for udi, row in f.iterrows()])), 3))
            for lam in (0.0, 0.25, 0.5)]
        drift["prior_only"] = round(float(np.mean([
            in_set(row, rank_causes(G, row, priors=pri, use_evidence=False, prior_smoothing=0.0)[0]["cause"])
            for _, row in te_d.iterrows()])), 3)
        out["drift_without_hdf"] = drift
    return out


def evaluate_hint_sensitivity(G, dfi: pd.DataFrame, boosts=(1.0, 2.0, 5.0)) -> list[dict]:
    """Độ nhạy của hệ số gợi ý P1: Top-1 khi không gợi ý / gợi ý đúng / gợi ý sai (trung bình qua mọi nguyên nhân sai)."""
    M = list(MODES)
    f = dfi[(dfi["Machine failure"] == 1) & (dfi[M].sum(axis=1) > 0)]
    train_max = _train_max_udi(G, dfi)
    rows = []
    for b in boosts:
        acc = {"none": [], "correct": [], "wrong": []}
        for udi, row in f.iterrows():
            truth = {m for m in M if row[m] == 1}
            pri = loo_priors(G, row) if udi <= train_max else None
            top = lambda hints: rank_causes(G, row, priors=pri, hints=hints, hint_boost=b)[0]["cause"] in truth
            acc["none"].append(top(None))
            acc["correct"].append(top({sorted(truth)[0]}))
            acc["wrong"] += [top({w}) for w in M if w not in truth]
        rows.append(dict(hint_boost=b, **{f"top1_{k}_hint": round(float(np.mean(v)), 3) for k, v in acc.items()}))
    return rows


def forward_sensitivity(df: pd.DataFrame, dfi: pd.DataFrame, cfg: dict, grids: dict | None = None) -> dict:
    """Quét độ nhạy của các giả định giả lập: % sự cố gây trễ hạn và số đơn bị ảnh hưởng (trung vị)."""
    grids = grids or {"slack_mean_min": [60, 120, 360, 720, 1440],
                      "recovery_tau_h": [6, 24, 96],
                      "substitute_share": [0.0, 0.3, 0.5]}
    inc = dfi.index[dfi["Machine failure"] == 1]
    res = {}
    for key, vals in grids.items():
        rows = []
        for v in vals:
            c = {**cfg, key: v}
            orders_x, order_of_x = build_orders(df, c)
            Gx = build_graph(df, orders_x, order_of_x, c)
            miss, aff = [], []
            for udi in inc:
                r = analyze_incident(Gx, dfi, int(udi))
                od = [a for a in r["affected"] if a["type"] == "order"]
                miss.append(any(a["miss_deadline"] for a in od))
                aff.append(len(od))
            rows.append(dict(value=v, pct_incidents_with_missed_deadline=round(float(np.mean(miss)), 3),
                             orders_affected_median=float(np.median(aff))))
        res[key] = rows
    return res


METRIC_NOTES = {
    "backward": ("KIỂM TRA ĐƯỜNG ỐNG, không phải độ chính xác ngoài thực tế: luật bằng chứng trùng luật sinh nhãn "
                 "của AI4I 2020 (khớp 10000/10000 dòng). Khi huấn luyện không có HDF (ml_baseline.drift_without_hdf), "
                 "luật với prior học từ dữ liệu KHÔNG hơn random forest: prior gần 0 của nguyên nhân chưa từng thấy "
                 "triệt tiêu bằng chứng. Làm trơn prior (rule_prior_smoothing_sweep) là thăm dò làm sau khi thấy kết quả, "
                 "cần xác nhận trên dữ liệu khác trước khi dùng."),
    "priors": ("Prior lấy từ 70% đầu theo UDI. Ở tập all_failures, dòng thuộc tập train dùng prior leave-one-out; "
               "độ lệch chuẩn dùng cho nhiễu cũng chỉ tính trên tập train."),
    "rnf": "RNF có rất ít mẫu có nhãn lỗi (xem n_by_mode); không kết luận về RNF.",
    "forward": ("wiring_check chỉ chứng minh đồ thị nối đúng, KHÔNG phải độ chính xác dự báo. "
                "pct_incidents_with_missed_deadline phụ thuộc giả định (xem forward_sensitivity)."),
    "synthetic": "Đơn hàng, hạn giao, đệm, thời gian dừng, máy dự phòng là giả lập; cần hiệu chỉnh bằng dữ liệu DENSO.",
    "hint": "hint_boost là hệ số tự đặt; dataset không có gợi ý thật của P1 nên chỉ khảo sát độ nhạy.",
}


def evaluate_forward(G, dfi: pd.DataFrame) -> dict:
    """(a) Nhất quán đồ thị <-> mô phỏng lịch; (b) thống kê tác động; (c) tốc độ."""
    cfg = G.graph["cfg"]
    orders = {n: d for n, d in G.nodes(data=True) if d["type"] == "order"}
    buf_total = {tp: cfg["buf_p02_a13"] + cfg["buf_a13_p03"] + cfg["fg_buffer_min"][tp] for tp in "LMH"}
    inc = dfi[dfi["Machine failure"] == 1]
    tp_, fp_, fn_, n_aff, n_miss, times, mono_ok = 0, 0, 0, [], [], [], True
    for udi, row in inc.iterrows():
        rng = np.random.default_rng(0)
        t0 = time.perf_counter()
        res = analyze_incident(G, dfi, int(udi), 0.0, rng)
        times.append((time.perf_counter() - t0) * 1000)
        D = res["effect"]["_downtime_raw"] * (1.0 - cfg["substitute_share"])    # dừng hiệu dụng (M07 gánh 30% tải)
        engine = {r["id"] for r in res["_all_orders"] if r["_delay_raw"] > 0}
        # oracle độc lập: không dùng cạnh đồ thị, chỉ dùng loại sản phẩm + hằng số đệm
        oracle = {oid for oid, d in orders.items()
                  if d["last_min"] > t_min(cfg, int(udi)) and D - buf_total[d["product"]] > 0}
        tp_ += len(engine & oracle); fp_ += len(engine - oracle); fn_ += len(oracle - engine)
        aff = res["affected"]
        n_aff.append(sum(a["type"] == "order" for a in aff))
        n_miss.append(sum(a.get("miss_deadline", False) for a in aff))
        for a in aff:                                           # rủi ro không tăng dọc đường đi
            mono_ok &= a["risk"] <= res["effect"]["severity"] + 1e-9
    prec = tp_ / (tp_ + fp_) if tp_ + fp_ else 1.0
    rec = tp_ / (tp_ + fn_) if tp_ + fn_ else 1.0
    return dict(n_incidents=len(inc),
                wiring_check_precision=round(prec, 4), wiring_check_recall=round(rec, 4),
                risk_bounded_by_severity=bool(mono_ok),
                orders_affected_median=float(np.median(n_aff)),
                orders_affected_max=int(max(n_aff)),
                pct_incidents_with_missed_deadline=round(float(np.mean(np.array(n_miss) > 0)), 3),
                runtime_ms_median=round(float(np.median(times)), 2),
                runtime_ms_p95=round(float(np.percentile(times, 95)), 2))


def self_check(G, df, orders, order_of):
    def need(cond, msg):
        if not cond:
            raise RuntimeError(f"self_check thất bại: {msg}")
    need(nx.is_directed_acyclic_graph(G.graph["flow"]), "đồ thị dòng chảy phải là DAG")
    need(len(order_of) == len(df), "mọi sản phẩm phải thuộc đúng 1 đơn")
    need(int(orders["qty"].sum()) == len(df), "tổng qty đơn hàng phải bằng số sản phẩm")
    lot_qty = sum(d["qty"] for _, _, d in G.edges(data=True) if d.get("rel") == "allocated_to")
    need(lot_qty == len(df), "tổng phân bổ Lô->Đơn phải bằng số sản phẩm")
    need(all("owner_dept" in d for _, d in G.nodes(data=True) if d["type"] in DEPT_OF_TYPE),
         "mọi nút thuộc DEPT_OF_TYPE phải có owner_dept")


# =============================================================================
# 7. 3 TÌNH HUỐNG & XUẤT KẾT QUẢ
# =============================================================================
def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items() if not str(k).startswith("_")}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def pick_scenarios(G, dfi):
    """Trả về (UDI xấu nhất, UDI trung vị, tổng số sự cố) xếp theo (số đơn trễ hạn, tổng rủi ro đơn)."""
    scored = []
    for udi in dfi.index[dfi["Machine failure"] == 1]:
        res = analyze_incident(G, dfi, int(udi))
        od = [a for a in res["affected"] if a["type"] == "order"]
        scored.append((sum(a["miss_deadline"] for a in od), sum(a["risk"] for a in od), int(udi)))
    scored.sort()
    return scored[-1][2], scored[len(scored) // 2][2], len(scored)


def _safe_name(incident_id, index: int, seen: set) -> str:
    """Tên file an toàn từ incident_id (chặn '../', ký tự lạ, trùng tên)."""
    base = re.sub(r"[^\w.\-]", "_", str(incident_id)) if incident_id not in (None, "") else ""
    base = re.sub(r"\.{2,}", "_", base).strip("._") or f"index{index}"
    name, k = base, 1
    while name in seen:
        k += 1
        name = f"{base}_{k}"
    seen.add(name)
    return name


def process_incident_file(G, dfi: pd.DataFrame, path: str, out: Path) -> dict:
    """Xử lý lô sự cố từ P1. Lỗi của từng bản ghi được ghi vào p2_errors.json, không làm dừng cả lô."""
    errors, n_ok, seen = [], 0, set()

    def finish(n_total):
        (out / "p2_errors.json").write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
        return dict(n_total=n_total, n_ok=n_ok, errors=errors)

    try:
        recs = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:                       # json.JSONDecodeError là ValueError
        errors.append(dict(index=None, incident_id=None, error_type=type(e).__name__, error=str(e)[:300]))
        return finish(0)
    if not isinstance(recs, list):
        errors.append(dict(index=None, incident_id=None, error_type="ValueError",
                           error="File phải chứa MỘT DANH SÁCH (JSON array) các bản ghi sự cố"))
        return finish(0)
    for i, rec in enumerate(recs):
        iid = rec.get("incident_id") if isinstance(rec, dict) else None
        try:
            rep_ = clean(analyze_record(G, rec, dfi=dfi))      # lỗi nghiệp vụ -> thông báo tiếng Việt rõ ràng
            validate(rec, INCIDENT_RECORD_SCHEMA)               # rồi mới đối chiếu hợp đồng schema
            validate(rep_, IMPACT_REPORT_SCHEMA)
            (out / f"p2_report_{_safe_name(iid, i, seen)}.json").write_text(
                json.dumps(rep_, ensure_ascii=False, indent=2), encoding="utf-8")
            n_ok += 1
        except (ValueError, TypeError, KeyError, ValidationError) as e:
            errors.append(dict(index=i, incident_id=iid, error_type=type(e).__name__,
                               error=str(e).splitlines()[0][:300] if str(e) else repr(e)))
    return finish(len(recs))


def main():
    ap = argparse.ArgumentParser(description="D3-P2: truy vết tác động trên AI4I 2020")
    ap.add_argument("--csv", default="ai4i2020.csv")
    ap.add_argument("--out", default="p2_outputs")
    ap.add_argument("--fast", action="store_true",
                    help="Bỏ qua đối chứng random forest và quét độ nhạy giả định (chạy nhanh khi phát triển/kiểm thử)")
    ap.add_argument("--incidents", default=None,
                    help="File JSON: danh sách IncidentRecord từ P1 (xem p2_incident_record.schema.json)")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    df = load_data(args.csv)
    dfi = df.set_index("UDI", drop=False)
    orders, order_of = build_orders(df, CFG)
    G = build_graph(df, orders, order_of, CFG)
    self_check(G, df, orders, order_of)
    print(f"Đồ thị: {G.number_of_nodes()} nút, {G.number_of_edges()} cạnh | "
          f"{len(orders)} đơn hàng giả lập | {int(df['Machine failure'].sum())} sự cố")

    # ---- 3 tình huống (+ 1 sự cố trung vị để đối chiếu với trường hợp xấu nhất) ----
    worst, median, n_inc = pick_scenarios(G, dfi)
    s1 = analyze_incident(G, dfi, worst);  s1["selection"] = f"worst_case_of_{n_inc}"
    s1b = analyze_incident(G, dfi, median); s1b["selection"] = f"median_of_{n_inc}"
    failed_per_order = {oid: int(((dfi["Type"] == d["product"]) &
                                  dfi["UDI"].between(d["first_udi"], d["last_udi"]) &
                                  (dfi["Machine failure"] == 1)).sum())
                        for oid, d in G.nodes(data=True) if d["type"] == "order"}
    s2_order = max(failed_per_order, key=failed_per_order.get)
    s2 = report_order_backward(G, dfi, s2_order);  s2["selection"] = f"most_defective_order_{s2_order}"
    s3 = report_material_delay(G, "A11", 4000, 180.0, 0.60)
    reports = {"S1_machine_incident_worst": s1, "S1b_machine_incident_median": s1b,
               "S2_order_backward": s2, "S3_material_delay": s3}

    # ---- giao diện: schema + ví dụ đầu vào cho P1 + kiểm tra đầu ra ----
    write_schemas(out)
    def doc_time(udi):                       # định dạng thời gian như tài liệu D3 mục 5.3
        return (pd.Timestamp(CFG["t0"]) + pd.Timedelta(minutes=t_min(CFG, udi))).strftime("%d/%m/%Y %H:%M")
    full = dict(record_from_row(dfi.loc[worst]), incident_id="INC_demo_full_sensors",
                anomaly_score=0.97, severity=0.90)
    ex = [dict(incident_id="INC_demo_doc_format", time=doc_time(worst), machine_id="M05",
               anomaly_type="Mô-men xoắn bất thường", level="Cao", anomaly_score=0.93,
               suspected_cause_group="Quá tải cơ học"),
          dict(incident_id="INC_demo_unmatched_hint", time=doc_time(median), machine_id="M05",
               anomaly_type="Độ rung bất thường", level="Trung bình", anomaly_score=0.81,
               suspected_cause_group="Ổ bi / lệch trục"),
          full,
          dict(incident_id="INC_demo_other_machine", udi=1500, machine_id="M03",
               anomaly_type="Cảnh báo PLC", level="Thấp", downtime_min=20)]
    (out / "p2_example_incidents_from_P1.json").write_text(
        json.dumps(clean(ex), ensure_ascii=False, indent=2), encoding="utf-8")
    ok = True
    for name, rep_ in reports.items():
        ok = validate(clean(rep_), IMPACT_REPORT_SCHEMA)
        (out / f"p2_scenario_{name}.json").write_text(
            json.dumps(clean(rep_), ensure_ascii=False, indent=2), encoding="utf-8")
        gv = graph_view(G, clean(rep_))
        validate(gv, GRAPH_VIEW_SCHEMA)
        (out / f"p2_graph_view_{name}.json").write_text(
            json.dumps(gv, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "p2_graph_view_static.json").write_text(
        json.dumps(graph_view(G), ensure_ascii=False, indent=2), encoding="utf-8")
    print("Schema ImpactReport:", "HỢP LỆ cho cả 4 báo cáo" if ok else "bỏ qua (pip install jsonschema để kiểm tra)")

    # ---- đánh giá ----
    bwd = evaluate_backward(G, dfi)
    fwd = evaluate_forward(G, dfi)
    mlb = dict(skipped="--fast") if args.fast else evaluate_ml_baseline(G, dfi)
    hint = evaluate_hint_sensitivity(G, dfi)
    sens = dict(skipped="--fast") if args.fast else forward_sensitivity(df, dfi, CFG)
    (out / "p2_metrics.json").write_text(
        json.dumps(clean(dict(notes=METRIC_NOTES, backward=bwd, ml_baseline=mlb, hint_sensitivity=hint,
                              forward=fwd, forward_sensitivity=sens, config=CFG)),
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- xuất đồ thị & đơn hàng cho P3 / Neo4j ----
    pd.DataFrame([dict(id=n, **{k: v for k, v in d.items()}) for n, d in G.nodes(data=True)]
                 ).to_csv(out / "p2_graph_nodes.csv", index=False)
    pd.DataFrame([dict(src=u, dst=v, **d) for u, v, d in G.edges(data=True)]
                 ).to_csv(out / "p2_graph_edges.csv", index=False)
    orders.assign(due=orders["due_min"].map(lambda m: iso(CFG, m))).to_csv(out / "p2_orders_synthetic.csv", index=False)

    # ---- in tóm tắt ----
    print(f"\n=== S1 ({s1['selection']}): UDI {s1['trigger']['udi']} | {s1['trigger']['time']} | "
          f"nhãn thật: {s1['eval_only']['label_modes']}")
    for c in s1["causes"][:3]:
        print(f"   nguyên nhân {c['cause']} ({c['name']}): {c['score']}")
    e = s1["effect"]
    print(f"   dừng kỳ vọng {e['downtime_min']} phút -> hiệu dụng {e['effective_downtime_min']} phút "
          f"(M07 gánh {int(CFG['substitute_share']*100)}% tải), severity {e['severity']} ({e['severity_source']})")
    for a in [x for x in s1["affected"] if x["type"] == "order"][:5]:
        print(f"   order {a['id']:10s} [{a['owner_dept']}] risk={a['risk']:<6} {a['reason']}")
    print("   theo bộ phận:", {k: (v["count"], v["max_risk"]) for k, v in s1["by_department"].items()})
    print(f"\n=== S2: đơn {s2_order} | sản phẩm lỗi: {s2['trigger']['details']['defective_units']} | "
          f"{[(c['cause'], c['score']) for c in s2['causes'][:3]]}")
    print("\n=== S3: phôi A11 trễ 180 phút")
    for a in [x for x in s3["affected"] if x["type"] == "order"][:5]:
        print(f"   order {a['id']:10s} [{a['owner_dept']}] risk={a['risk']:<6} {a['reason']}")
    print("\n=== Đánh giá truy vết ngược (KIỂM TRA ĐƯỜNG ỐNG, xem notes trong p2_metrics.json) ===")
    for r in bwd:
        print(f"   {r['subset']:12s} {r['method']:15s} noise={r['noise_sd_frac']:<5} n={r['n']:<4} "
              f"top1={r['top1']} top2={r['top2']} mrr={r['mrr']} macroF1={r['macro_f1_all']}/{r['macro_f1_excl_rnf']}(bỏ RNF)")
    print("   n theo lớp (all_failures):", bwd[-1]["n_by_mode"])
    print("\n=== Đối chứng random forest ===")
    print("   CV 5 fold:", mlb.get("cv5", mlb))
    print("   Bài test thiếu HDF:", mlb.get("drift_without_hdf"))
    print("   Độ nhạy gợi ý P1:", hint)
    print("\n=== Đánh giá truy vết xuôi ===")
    print("  ", fwd)
    print("   Độ nhạy giả định -> % sự cố gây trễ hạn:")
    for k, rows in ({} if args.fast else sens).items():
        print(f"     {k}: " + ", ".join(f"{r['value']}->{r['pct_incidents_with_missed_deadline']}" for r in rows))
    print(f"\nĐã ghi kết quả vào: {out.resolve()}")

    # ---- chế độ P1 cắm vào: xử lý SAU CÙNG để một bản ghi hỏng không ảnh hưởng đầu ra khác ----
    if args.incidents:
        res = process_incident_file(G, dfi, args.incidents, out)
        print(f"Sự cố từ P1: {res['n_ok']}/{res['n_total']} bản ghi thành công"
              + (f"; {len(res['errors'])} lỗi, xem {out / 'p2_errors.json'}" if res["errors"] else ""))
        for e in res["errors"][:5]:
            print(f"   [{e['index']}] {e['incident_id']}: {e['error_type']}: {e['error']}")
        if res["errors"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
