#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D3 - P2: THÍ NGHIỆM E1-E4 (mục 15, 17 Part 3/5, 18 của tài liệu D3)
===================================================================
    python p2_experiments.py --csv ai4i2020.csv --out p2_outputs --seeds 30

Phần này bổ sung cho p2_impact_trace.py những gì tài liệu yêu cầu mà bản trước còn thiếu:
  * generate_graph(seed, size)  : đồ thị nhà máy nhiều máy, 3 quy mô, sinh ĐỘC LẬP với sự cố (18.2)
  * true_impact()               : ground truth tác động, mô hình dòng chảy KHÁC công thức của hệ thống (18.4)
  * observed_graph()            : đồ thị hệ thống được nhìn thấy: trọng số/đệm có nhiễu, xóa 0/10/25/50% cạnh (E4)
  * E1 truy vết xuôi            : precision/recall theo tầng vs baseline "cảnh báo cục bộ"
  * E2 điểm rủi ro              : Spearman, top-k vs baseline "chỉ theo số bước"
  * E3 truy vết ngược           : Top-1/Top-3/MRR của MÁY GỐC khi có confounder 0/25/50%
                                  vs baseline "điểm bất thường cao nhất" và "xảy ra gần nhất"
  * E4                          : lặp E1-E3 khi xóa cạnh
  * results.csv (seed, cấu hình, chỉ số), tóm tắt mean +- std, biểu đồ, báo cáo trung thực.

Tín hiệu máy là DÒNG THẬT của AI4I 2020 (tập test); bộ phát hiện là Isolation Forest fit trên train,
ngưỡng cố định theo recall 90% trên validation (18.2). Cấu trúc đồ thị và mọi tham số vận hành là MÔ PHỎNG.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

import p2_impact_trace as P

# =============================================================================
# CẤU HÌNH THÍ NGHIỆM (mọi tham số tự đặt nằm ở đây, ghi vào báo cáo)
# =============================================================================
EXP = {
    "n_units": 10000,
    "sizes": {                       # số công đoạn mỗi tầng, số sản phẩm, số đơn/sản phẩm
        "small":  dict(stages=[2, 2, 2],          products=3, orders_per_product=4),
        "medium": dict(stages=[3, 4, 4, 3],       products=5, orders_per_product=5),
        "large":  dict(stages=[4, 6, 6, 6, 4],    products=8, orders_per_product=6),
    },
    "confounder_pcts": [0, 25, 50],  # % máy KHÔNG thuộc tổ tiên của kết quả xấu bị bật bất thường
    "delete_pcts": [0, 10, 25, 50],  # % cạnh dòng chảy bị xóa khỏi đồ thị hệ thống nhìn thấy
    "w_range": (0.70, 1.00),         # trọng số phụ thuộc thật
    "buf_range": (0.0, 12.0),        # đệm thật (phút)
    "raw_buf_range": (20.0, 90.0),
    "p_substitute": 0.5,
    "substitute_share": 0.30,
    "w_noise_sd": 0.15,              # nhiễu log-chuẩn trên trọng số hệ thống nhìn thấy
    "buf_noise_sd": 0.30,            # nhiễu log-chuẩn trên đệm hệ thống nhìn thấy
    "downtime_noise_sd": 0.35,       # thời gian dừng thật lệch so với giá trị kỳ vọng theo kiểu lỗi
    "tau_true_h": (12.0, 48.0),      # hằng số bù trễ thật (hệ thống giả định 24 h)
    "impact_thr": 0.05,              # ngưỡng coi là "bị ảnh hưởng"
    "lookback_h": 72.0,
    "reach_floor": 0.5,              # lambda: score = pct * (lam + (1-lam) * reach). Đặt trước, không tinh chỉnh
    "reach_floor_sweep": [0.0, 0.25, 0.5, 0.75],
    "split": (0.5, 0.2, 0.3),        # train / validation / test cho tầng phát hiện
    "target_recall": 0.90,
    "data_seed": 0,
    # --- tần suất lỗi lịch sử theo máy (P1.5) ---
    "hist_rate_median": 4.0,         # số sự cố / 1000 đơn vị, trung vị giữa các máy (giả định)
    "hist_rate_sd": 0.7,             # độ lệch chuẩn log của tỷ lệ giữa các máy (giả định)
    "hist_units": 20000,             # độ dài lịch sử quan sát được, TÁCH BIỆT với giai đoạn kịch bản
    "hist_gamma_sweep": [0.25, 0.5, 1.0],  # số mũ hệ số lịch sử; 0 = không dùng (cột e3_sys). 0.5 và 1.0 đặt trước; 0.25 THÊM SAU khi thấy kết quả
    "root_sampling": "uniform",      # uniform | proportional (máy gốc ~ tỷ lệ lỗi thật)
    "secom_downtime_min": 45.0,      # GIẢ ĐỊNH: SECOM không có kiểu lỗi/thời gian dừng; dùng hằng số cố định
}
LAYER_TYPES = ["process", "part", "product", "order"]


# =============================================================================
# 1. TẦNG PHÁT HIỆN (thật, từ AI4I): Isolation Forest, ngưỡng cố định recall 90% trên validation
# =============================================================================
class Detector:
    domain = "ai4i"
    name = "AI4I 2020"
    FEATS = list(P.SENSORS.values())

    def describe(self) -> str:
        return (f"Isolation Forest fit trên train AI4I (50%), ngưỡng cố định recall {int(EXP['target_recall']*100)}% trên validation (20%). "
                f"Bộ đặc trưng chọn theo validation: {self.feature_set} (tỷ lệ báo sai validation {self.candidate_val_far}). "
                f"Trên test (30%): recall thực {self.test_recall:.3f}, tỷ lệ báo sai {self.test_false_alarm:.3f}. "
                "RNF bị loại (không phát hiện được theo thiết kế).")
    CANDIDATES = {
        "raw": FEATS + ["_tcode"],
        "physical": ["_dT", "_power", "_strain", "Tool wear [min]", "Rotational speed [rpm]"],
    }

    @staticmethod
    def _derive(d: pd.DataFrame) -> pd.DataFrame:
        d = d.copy()
        d["_tcode"] = d["Type"].map({"L": 0, "M": 1, "H": 2})
        d["_dT"] = d["Process temperature [K]"] - d["Air temperature [K]"]
        d["_power"] = d["Torque [Nm]"] * d["Rotational speed [rpm]"] * 2.0 * np.pi / 60.0
        d["_strain"] = d["Tool wear [min]"] * d["Torque [Nm]"]
        return d

    def __init__(self, df: pd.DataFrame, exp: dict = EXP):
        """Đặc trưng suy ra CHỈ từ 5 cảm biến (không dùng nhãn). Bộ đặc trưng được chọn theo tỷ lệ báo sai
        trên VALIDATION ở recall cố định 90%, không nhìn tập test."""
        from sklearn.ensemble import IsolationForest
        from sklearn.model_selection import train_test_split
        seed = exp["data_seed"]
        d = self._derive(df)
        tr, rest = train_test_split(d, train_size=exp["split"][0], stratify=d["Machine failure"], random_state=seed)
        va, te = train_test_split(rest, train_size=exp["split"][1] / (exp["split"][1] + exp["split"][2]),
                                  stratify=rest["Machine failure"], random_state=seed)
        self.train, self.val, self.test = tr, va, te
        det_modes = list(P.MODES)[:4]
        vfail = va[va[det_modes].sum(axis=1) > 0]                     # RNF không phát hiện được (18.1) -> loại
        vnorm = va[va["Machine failure"] == 0]
        best = None
        self.candidate_val_far = {}
        for name, cols in self.CANDIDATES.items():
            m = IsolationForest(n_estimators=200, random_state=seed).fit(tr[cols])
            thr = float(np.quantile(-m.score_samples(vfail[cols]), 1.0 - exp["target_recall"]))
            far = float((-m.score_samples(vnorm[cols]) >= thr).mean())
            self.candidate_val_far[name] = round(far, 4)
            if best is None or far < best[0]:
                best = (far, name, cols, m, thr)
        _, self.feature_set, self.cols, self.model, self.thr_raw = best
        self._ecdf = np.sort(-self.model.score_samples(tr[self.cols]))
        self.thr_pct = float(np.searchsorted(self._ecdf, self.thr_raw) / len(self._ecdf))
        det_te = self.pct(te) >= self.thr_pct
        fm = (te[det_modes].sum(axis=1) > 0).to_numpy()
        self.test_recall = float(det_te[fm].mean())
        self.test_false_alarm = float(det_te[(te["Machine failure"] == 0).to_numpy()].mean())
        self.fail_pool = te[fm].reset_index(drop=True)
        self.norm_pool = te[te["Machine failure"] == 0].reset_index(drop=True)

    def pct(self, rows: pd.DataFrame) -> np.ndarray:
        a = -self.model.score_samples(rows[self.cols])
        return np.searchsorted(self._ecdf, a) / len(self._ecdf)


def build_cause_graph(train: pd.DataFrame, cfg: dict) -> nx.DiGraph:
    """Đồ thị nguyên nhân tối thiểu cho rank_causes, prior/độ lệch chuẩn CHỈ tính từ train."""
    Gc = nx.DiGraph()
    Gc.graph["cfg"] = cfg
    for s, col in P.SENSORS.items():
        Gc.add_node(s, type="sensor", column=col, sd=float(train[col].std()))
    cnt = {m: int(train[m].sum()) + 1 for m in P.MODES}
    tot = sum(cnt.values())
    Gc.add_node("M", type="machine")
    for m, name in P.MODES.items():
        Gc.add_node(f"FM_{m}", type="failure_mode", code=m, name=name, prior=cnt[m] / tot, count=cnt[m])
        for s in P.MODE_SENSORS[m]:
            Gc.add_edge(s, f"FM_{m}")
        Gc.add_edge(f"FM_{m}", "M")
    return Gc


# =============================================================================
# 2. BỘ SINH ĐỒ THỊ NHÀ MÁY (độc lập với sự cố)
# =============================================================================
def _cfg_for_graph() -> dict:
    cfg = copy.deepcopy(P.CFG)
    cfg["substitute_share"] = EXP["substitute_share"]
    return cfg


def generate_graph(seed: int, size: str, exp: dict = EXP) -> nx.DiGraph:
    """Đồ thị đầy đủ (ground truth cấu trúc). KHÔNG đọc bất kỳ nhãn lỗi nào: cấu trúc, trọng số, đệm,
    đơn hàng đều quyết định trước, sự cố gán sau (nguyên tắc 18.2)."""
    sp = exp["sizes"][size]
    rng = np.random.default_rng([seed, list(exp["sizes"]).index(size), 1])
    cfg = _cfg_for_graph()
    G = nx.DiGraph()
    wlo, whi = exp["w_range"]
    blo, bhi = exp["buf_range"]

    def flow(u, v, rel, w, buf, kind):
        G.add_edge(u, v, rel=rel, flow=True, w=float(w), buffer_min=float(buf), stock_kind=kind)

    def node(n, typ, layer="logic", **kw):
        G.add_node(n, type=typ, layer=layer, name=kw.pop("name", n), **kw)

    stages = sp["stages"]
    procs, parts = [], []
    for k, n_p in enumerate(stages, start=1):
        procs.append([f"P{k}_{i + 1}" for i in range(n_p)])
        parts.append([f"A{k}_{i + 1}" for i in range(n_p)])
    machines, subs = [], []
    for k, row in enumerate(procs):
        for i, p in enumerate(row):
            node(p, "process", name=f"Công đoạn {p}")
            node(parts[k][i], "part", name=f"Chi tiết {parts[k][i]}")
            m = f"M{k + 1}{i + 1:02d}"
            node(m, "machine", name=f"Máy {m}")
            machines.append(m)
            flow(m, p, "performs", 1.0, 0.0, None)
            flow(p, parts[k][i], "produces", rng.uniform(wlo, whi), rng.uniform(blo, bhi), "wip")
            if rng.random() < exp["p_substitute"]:
                sm = f"S{k + 1}{i + 1:02d}"
                node(sm, "machine", name=f"Máy dự phòng {sm}")
                subs.append(sm)
                G.add_edge(sm, p, rel="can_perform", capacity_share=exp["substitute_share"])
    for i, p in enumerate(procs[0]):                      # nguyên liệu thô vào tầng 1
        r = f"R{i + 1}"
        node(r, "part", name=f"Phôi {r}")
        flow(r, p, "consumed_by", 1.0, rng.uniform(*exp["raw_buf_range"]), "raw_material")
    for k in range(len(stages) - 1):                      # linh kiện tầng k -> công đoạn tầng k+1
        nxt = procs[k + 1]
        links = set()
        for j, p in enumerate(nxt):                       # mỗi công đoạn có >= 1 đầu vào
            links.add((int(rng.integers(len(parts[k]))), j))
        for i in range(len(parts[k])):                    # mỗi linh kiện dùng cho >= 1 công đoạn
            if not any(a == i for a, _ in links):
                links.add((i, int(rng.integers(len(nxt)))))
        for i in range(len(parts[k])):
            for j in range(len(nxt)):
                if (i, j) not in links and rng.random() < 0.25:
                    links.add((i, j))
        for i, j in sorted(links):
            flow(parts[k][i], nxt[j], "consumed_by", rng.uniform(wlo, whi), rng.uniform(blo, bhi), "wip")
    last = parts[-1]
    prods = [f"PRD_{j + 1}" for j in range(sp["products"])]
    for pr in prods:
        node(pr, "product", name=f"Sản phẩm {pr}")
    links = set()
    for j in range(len(prods)):
        for i in rng.choice(len(last), size=min(len(last), int(rng.integers(1, 4))), replace=False):
            links.add((int(i), j))
    for i in range(len(last)):
        if not any(a == i for a, _ in links):
            links.add((i, int(rng.integers(len(prods)))))
    for i, j in sorted(links):
        flow(last[i], prods[j], "consumed_by", rng.uniform(wlo, whi), rng.uniform(blo, bhi), "finished_goods")

    # lớp nghiệp vụ: đơn hàng và phân bổ đơn vị sản phẩm theo thời gian
    n = exp["n_units"]
    unit_prod = rng.integers(len(prods), size=n)
    order_of = {}
    for j, pr in enumerate(prods):
        udis = np.flatnonzero(unit_prod == j) + 1
        for k, chunk in enumerate(np.array_split(udis, sp["orders_per_product"]), start=1):
            if len(chunk) == 0:
                continue
            oid = f"ORD_{pr[4:]}_{k:02d}"
            first, last_u = int(chunk[0]), int(chunk[-1])
            lo, hi = cfg["slack_range_min"]
            slack = int(min(max(rng.exponential(cfg["slack_mean_min"]), lo), hi))
            node(oid, "order", layer="business", product=pr, qty=int(len(chunk)),
                 priority=int(rng.choice([1, 2, 3], p=cfg["priority_p"])), customer=f"KH{int(rng.integers(1, 6))}",
                 first_udi=first, last_udi=last_u, first_min=P.t_min(cfg, first),
                 last_min=P.t_min(cfg, last_u) + cfg["takt_min"], slack_min=float(slack))
            G.nodes[oid]["due_min"] = G.nodes[oid]["last_min"] + slack
            flow(pr, oid, "requested", 1.0, 0.0, None)
            for u in chunk:
                order_of[int(u)] = oid
    for nn, d in G.nodes(data=True):
        dept = P.DEPT_OF_TYPE.get(d["type"])
        if dept:
            d["owner_dept"] = dept
    # lịch sử sự cố theo máy: tỷ lệ thật (ẩn) -> số sự cố đếm được trong một giai đoạn lịch sử riêng.
    # Rút SAU cấu trúc nên không đổi cấu trúc đồ thị; không phụ thuộc kịch bản sự cố (18.2).
    for m in machines + subs:
        rate = exp["hist_rate_median"] * math.exp(rng.normal(0, exp["hist_rate_sd"]))
        G.nodes[m]["true_fail_per_1000"] = float(rate)
        G.nodes[m]["hist_count"] = int(rng.poisson(rate * exp["hist_units"] / 1000.0))
    _refresh_flow(G)
    G.graph.update(order_of=order_of, cfg=cfg, machines=machines, substitutes=subs, hist_units=exp["hist_units"])
    return G


def _refresh_flow(G: nx.DiGraph) -> None:
    F = nx.DiGraph()
    F.add_nodes_from(G.nodes(data=True))
    F.add_edges_from((u, v, d) for u, v, d in G.edges(data=True) if d.get("flow"))
    G.graph["flow"] = F


def observed_graph(G: nx.DiGraph, delete_pct: int, seed: int, size: str, exp: dict = EXP) -> nx.DiGraph:
    """Phiên bản hệ thống được nhìn thấy: trọng số/đệm là ước lượng có nhiễu; xóa ngẫu nhiên delete_pct% cạnh dòng chảy."""
    rng = np.random.default_rng([seed, list(exp["sizes"]).index(size), 3, delete_pct])
    Go = G.copy()
    Go.graph.update(order_of=G.graph["order_of"], cfg=G.graph["cfg"], machines=G.graph["machines"],
                    substitutes=G.graph["substitutes"], hist_units=G.graph["hist_units"])
    for u, v, d in list(Go.edges(data=True)):          # copy dict cạnh để không sửa đồ thị đầy đủ
        Go[u][v].update(dict(d))
    flow_edges = [(u, v) for u, v, d in Go.edges(data=True) if d.get("flow")]
    k = int(round(len(flow_edges) * delete_pct / 100.0))
    if k:
        for i in rng.choice(len(flow_edges), size=k, replace=False):
            Go.remove_edge(*flow_edges[i])
    for u, v, d in Go.edges(data=True):
        if d.get("flow") and d.get("stock_kind") is not None:
            d["w"] = float(min(1.0, d["w"] * math.exp(rng.normal(0, exp["w_noise_sd"]))))
            d["buffer_min"] = float(d["buffer_min"] * math.exp(rng.normal(0, exp["buf_noise_sd"])))
        elif d.get("flow"):
            d["w"] = float(d["w"])
    _refresh_flow(Go)
    return Go


# =============================================================================
# 3. GROUND TRUTH TÁC ĐỘNG (18.4): mô hình dòng chảy khác công thức của hệ thống
# =============================================================================
def true_impact(G: nx.DiGraph, root: str, udi: int, downtime_true: float, tau_h: float) -> dict[str, float]:
    """Mức ảnh hưởng thật của từng nút (0..1) trên đồ thị ĐẦY ĐỦ với trọng số/đệm thật.
    Khác hệ thống ở: (a) đệm TRỪ vào số phút thiếu hụt (hệ thống nhân hệ số che phủ), (b) nhiều đường vào
    gộp kiểu noisy-OR (hệ thống chọn đường tốt nhất), (c) thời gian dừng và hằng số bù trễ là giá trị thật."""
    cfg = G.graph["cfg"]
    F = G.graph["flow"]
    share = 0.0
    for v in F.successors(root):
        for m in G.predecessors(v):
            if G[m][v].get("rel") == "can_perform":
                share += G[m][v]["capacity_share"]
    d_eff = downtime_true * (1.0 - min(1.0, share))
    out = {n: 0.0 for n in F}
    if d_eff <= 0:
        return out
    lost = {root: d_eff}
    inc = P.t_min(cfg, udi)
    for u in nx.topological_sort(F):
        if u == root or F.in_degree(u) == 0:
            continue
        keep = 1.0
        for p in F.predecessors(u):
            if p in lost and lost[p] > 0:
                e = F[p][u]
                via = e["w"] * max(0.0, lost[p] - e.get("buffer_min", 0.0))
                keep *= (1.0 - min(1.0, via / d_eff))
        frac = 1.0 - keep
        if frac > 0:
            lost[u] = frac * d_eff
    for n, mins in lost.items():
        if n == root:
            continue
        t = G.nodes[n]["type"]
        if t == "order":
            o = G.nodes[n]
            if o["last_min"] <= inc:
                continue
            hours = (o["last_min"] - inc) / 60.0
            delay = mins * math.exp(-hours / tau_h)
            out[n] = min(1.0, delay / max(o["slack_min"], 1.0)) * cfg["prio_factor"][o["priority"]]
        elif t in ("process", "part", "product"):
            out[n] = mins / d_eff
    return out


# =============================================================================
# 4. HỆ THỐNG (dùng lại P.rank_causes + P.trace_forward) VÀ BASELINE
# =============================================================================
def estimate_effect(det, Gc, row: pd.Series, cfg: dict, exp: dict = EXP) -> tuple[float, float]:
    """Thời gian dừng và mức nghiêm trọng hệ thống ƯỚC LƯỢNG cho sự cố (không dùng nhãn).
    AI4I: từ xếp hạng nguyên nhân. SECOM không có kiểu lỗi: thời gian dừng giả định cố định, mức nghiêm trọng = điểm bất thường."""
    if getattr(det, "domain", "ai4i") == "secom":
        pct = float(det.pct(pd.DataFrame([row]))[0])
        return float(exp["secom_downtime_min"]), float(np.clip(pct, 0.3, 1.0))
    return P.expected_effect(P.rank_causes(Gc, row, machine="M"), cfg)


def system_forward(Go: nx.DiGraph, Gc, row: pd.Series, root: str, udi: int, thr=None, effect=None, det=None) -> dict:
    cfg = Go.graph["cfg"]
    d_hat, s_hat = effect if effect is not None else estimate_effect(det, Gc, row, cfg)
    return P.trace_forward(Go, root, udi, s_hat, d_hat, thr=thr)


def baseline_e3(pct: dict, flagged: set, times: dict, mode: str) -> dict:
    """Baseline E3 (18.5), không dùng đồ thị. mode='anomaly': xếp theo điểm bất thường cao nhất.
    mode='recent': máy bị cảnh báo xếp trước, trong đó máy xảy ra gần nhất về thời gian xếp đầu (times: phút trước kết quả xấu, âm)."""
    if mode == "anomaly":
        return dict(pct)
    if mode == "recent":
        return {m: (1e3 if m in flagged else 0.0) + times[m] / 1e4 + pct[m] * 1e-6 for m in pct}
    raise ValueError("mode phải là 'anomaly' hoặc 'recent'")


def _by_type(G, ids):
    out = {t: set() for t in LAYER_TYPES}
    for n in ids:
        t = G.nodes[n]["type"]
        if t in out:
            out[t].add(n)
    return out


def e1_metrics(G, truth: dict, flagged: set, thr: float) -> dict:
    T = _by_type(G, [n for n, v in truth.items() if v >= thr and G.nodes[n]["type"] in LAYER_TYPES])
    S = _by_type(G, flagged)
    tp = sum(len(T[t] & S[t]) for t in LAYER_TYPES)
    ns, nt = sum(len(S[t]) for t in LAYER_TYPES), sum(len(T[t]) for t in LAYER_TYPES)
    prec = tp / ns if ns else 0.0
    rec = tp / nt if nt else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    out = dict(P=prec, R=rec, F1=f1)
    for t in LAYER_TYPES:
        out[f"R_{t}"] = len(T[t] & S[t]) / len(T[t]) if T[t] else float("nan")
    return out


def _spearman(a: pd.Series, b: pd.Series) -> float:
    if len(a) < 3 or a.nunique() < 2 or b.nunique() < 2:
        return float("nan")
    return float(a.corr(b, method="spearman"))


def _topk_prec(sys_score: dict, truth: dict, ids: list, k: int) -> float:
    if k <= 0:
        return float("nan")
    ids = sorted(ids)
    ts = set(sorted(ids, key=lambda n: -truth[n])[:k])
    ss = set(sorted(ids, key=lambda n: -sys_score[n])[:k])
    return len(ts & ss) / k


def e2_metrics(G, truth, sys_score: dict, base_score: dict, root: str) -> dict:
    desc = [n for n in nx.descendants(G.graph["flow"], root) if G.nodes[n]["type"] in LAYER_TYPES]
    t = pd.Series({n: truth[n] for n in desc})
    out = dict(n_desc=len(desc))
    for name, sc in (("sys", sys_score), ("base", base_score)):
        out[f"{name}_spearman"] = _spearman(t, pd.Series({n: sc.get(n, 0.0) for n in desc}))
        orders = [n for n in desc if G.nodes[n]["type"] == "order"]
        k = min(3, sum(1 for n in orders if truth[n] > 0))
        out[f"{name}_top3_orders"] = _topk_prec({n: sc.get(n, 0.0) for n in orders}, truth, orders, k)
    return out


def best_reach(Go: nx.DiGraph, target: str) -> dict:
    """Tích trọng số lớn nhất từ mỗi nút tới `target` trên đồ thị hệ thống nhìn thấy (0 nếu không tới được)."""
    F = Go.graph["flow"]
    best = {n: 0.0 for n in F}
    best[target] = 1.0
    for u in reversed(list(nx.topological_sort(F))):
        for v in F.successors(u):
            best[u] = max(best[u], F[u][v]["w"] * best[v])
    return best


def ancestor_machines(G: nx.DiGraph, target: str) -> set:
    F = G.graph["flow"]
    anc = nx.ancestors(F, target)
    ms = {n for n in anc if G.nodes[n]["type"] == "machine"}
    for s in G.graph["substitutes"]:                     # máy dự phòng tính là tổ tiên nếu công đoạn của nó là tổ tiên
        if any(v in anc for v in G.successors(s)):
            ms.add(s)
    return ms


def _primary_machines(Go: nx.DiGraph) -> set:
    """Máy nằm trên dòng chảy vật liệu. Đồ thị của thí nghiệm có sẵn danh sách; đồ thị của pipeline chính
    (p2_impact_trace.build_graph) thì suy ra từ nút loại 'machine' có cạnh dòng chảy đi ra."""
    if "machines" in Go.graph:
        return set(Go.graph["machines"])
    F = Go.graph["flow"]
    return {n for n, d in Go.nodes(data=True) if d.get("type") == "machine" and n in F and F.out_degree(n) > 0}


def machine_scores(Go: nx.DiGraph, outcome: str, pct: dict, lam: float = EXP["reach_floor"], gamma: float = 0.0,
                   reach: dict | None = None) -> dict:
    """Điểm nguyên nhân của từng máy: pct_bất_thường × (λ + (1-λ)·reach) × hệ_số_lịch_sử^γ.
    reach = tích trọng số lớn nhất từ máy tới kết quả xấu trên đồ thị hệ thống nhìn thấy (0 nếu không nối được).
    hệ_số_lịch_sử = (số sự cố lịch sử của máy + 1) / (trung bình + 1), chặn [0.25, 4]; γ = 0 là không dùng lịch sử."""
    prim = _primary_machines(Go)
    reach = best_reach(Go, outcome) if reach is None else reach
    machines = list(pct)
    counts = {m: Go.nodes[m].get("hist_count", 0) for m in machines}
    mean_c = float(np.mean(list(counts.values()))) if counts else 0.0
    out = {}
    for m in machines:
        r = reach.get(m, 0.0) if m in prim else 0.0
        sc = pct[m] * (lam + (1.0 - lam) * r)
        if gamma:
            sc *= float(np.clip((counts[m] + 1.0) / (mean_c + 1.0), 0.25, 4.0)) ** gamma
        out[m] = sc
    return out


def backward_trace(Go: nx.DiGraph, outcome: str, anomaly_pct: dict, topk: int = 5, lam: float = EXP["reach_floor"],
                   gamma: float = 0.0) -> list[dict]:
    """HÀM TRUY VẾT NGƯỢC DÙNG CHUNG (P1.5): xếp hạng máy là nguyên nhân gốc có khả năng nhất của một kết quả xấu
    (đơn hàng trễ/lỗi hoặc bất kỳ nút hạ nguồn nào).

    Đầu vào : `Go` đồ thị hệ thống nhìn thấy (có thể thiếu cạnh); `outcome` mã nút kết quả xấu;
              `anomaly_pct` {mã máy: điểm bất thường 0..1} từ bộ phát hiện (P1); `gamma` > 0 để dùng tần suất lỗi lịch sử.
    Đầu ra  : Top-k [{rank, machine, score, anomaly, reach, hist_factor, path}], giảm dần theo score.
              `score` là điểm tương đối để xếp hạng, KHÔNG phải xác suất; `path` là đường phụ thuộc tốt nhất trong đồ thị.
    Chỉ nói "nguyên nhân có khả năng", không khẳng định quan hệ nhân quả."""
    if outcome not in Go.graph["flow"]:
        raise ValueError(f"Nút kết quả '{outcome}' không thuộc đồ thị dòng chảy")
    unknown = [m for m in anomaly_pct if m not in Go]
    if unknown:
        raise ValueError(f"Máy không có trong đồ thị: {unknown}")
    reach = best_reach(Go, outcome)
    sc = machine_scores(Go, outcome, anomaly_pct, lam, gamma, reach)
    counts = [Go.nodes[m].get("hist_count", 0) for m in anomaly_pct]
    mean_c = float(np.mean(counts)) if counts else 0.0
    F = Go.graph["flow"]

    def best_path(m):
        if reach.get(m, 0.0) <= 0.0:
            return []
        path, cur = [m], m
        while cur != outcome:
            cur = max(F.successors(cur), key=lambda v: F[path[-1]][v]["w"] * reach[v])
            path.append(cur)
        return path

    ranked = sorted(sc, key=lambda m: (-sc[m], m))[:topk]
    return [dict(rank=i + 1, machine=m, score=round(sc[m], 4), anomaly=round(float(anomaly_pct[m]), 4),
                 reach=round(reach.get(m, 0.0), 4),
                 hist_factor=round(float(np.clip((Go.nodes[m].get("hist_count", 0) + 1.0) / (mean_c + 1.0), 0.25, 4.0)), 3),
                 path=best_path(m)) for i, m in enumerate(ranked)]


def rank_credit(scores: dict, root: str, ks=(1, 3)) -> dict:
    s = np.array(list(scores.values()), dtype=float)
    sr = scores[root]
    higher, tied = int((s > sr + 1e-12).sum()), int((np.abs(s - sr) <= 1e-12).sum())
    out = {f"top{k}": float(np.clip((k - higher) / tied, 0.0, 1.0)) for k in ks}
    out["mrr"] = float(np.mean([1.0 / (higher + j + 1) for j in range(tied)]))
    return out


# =============================================================================
# 5. CHẠY THÍ NGHIỆM
# =============================================================================
def run_seed_size(seed: int, size: str, det: Detector, Gc: nx.DiGraph, exp: dict = EXP) -> list[dict]:
    si = list(exp["sizes"]).index(size)
    G = generate_graph(seed, size, exp)
    cfg = G.graph["cfg"]
    rng = np.random.default_rng([seed, si, 7])
    prim = [m for m in G.graph["machines"]]
    all_m = prim + list(G.graph["substitutes"])
    thr = exp["impact_thr"]

    # --- chọn máy gốc, dòng lỗi thật, thời gian dừng thật; lặp tới khi có đơn hàng bị ảnh hưởng ---
    for _ in range(50):
        if exp.get("root_sampling", "uniform") == "proportional":
            w = np.array([G.nodes[m]["true_fail_per_1000"] for m in prim])
            root = prim[int(rng.choice(len(prim), p=w / w.sum()))]
        else:
            root = prim[int(rng.integers(len(prim)))]
        udi = int(rng.integers(1, int(exp["n_units"] * 0.8)))
        frow = det.fail_pool.iloc[int(rng.integers(len(det.fail_pool)))]
        if getattr(det, "domain", "ai4i") == "secom":
            d_base = exp["secom_downtime_min"]
        else:
            d_base = max(cfg["downtime_min"][m] for m in [m for m in list(P.MODES)[:4] if frow[m] == 1])
        d_true = d_base * math.exp(rng.normal(0, exp["downtime_noise_sd"]))
        tau = float(rng.uniform(*exp["tau_true_h"]))
        truth = true_impact(G, root, udi, d_true, tau)
        orders = [n for n in truth if G.nodes[n]["type"] == "order"]
        if orders and max(truth[n] for n in orders) >= thr:
            break
    else:
        return []
    outcome = max(orders, key=lambda n: (truth[n], n))
    anc = ancestor_machines(G, outcome)
    non_anc = sorted(set(all_m) - anc)
    perm = [non_anc[i] for i in rng.permutation(len(non_anc))]
    conf_rows = {m: det.fail_pool.iloc[int(rng.integers(len(det.fail_pool)))] for m in perm}
    norm_rows = {m: det.norm_pool.iloc[int(rng.integers(len(det.norm_pool)))] for m in all_m}
    times = {m: float(rng.uniform(-exp["lookback_h"] * 60, -5.0)) for m in all_m}   # phút trước kết quả xấu

    effect = estimate_effect(det, Gc, frow, cfg, exp)
    base = dict(domain=getattr(det, "domain", "ai4i"), root_sampling=exp.get("root_sampling", "uniform"), seed=seed, size=size, n_nodes=G.number_of_nodes(), n_machines=len(all_m), root=root,
                outcome=outcome, n_ancestor_machines=len(anc), downtime_true=round(d_true, 1))
    rows = []
    obs_cache = {}
    for dp in exp["delete_pcts"]:
        Go = observed_graph(G, dp, seed, size, exp)
        t0 = time.perf_counter()
        try:
            fwd = system_forward(Go, Gc, frow, root, udi, effect=effect)                    # thr mặc định (E1)
            fwd0 = system_forward(Go, Gc, frow, root, udi, thr=0.0, effect=effect)         # toàn bộ điểm (E2)
            ms = (time.perf_counter() - t0) * 1000
            sys_flag = {a["id"] for a in fwd["affected"]}
            sys_risk = {a["id"]: a["risk"] for a in fwd0["affected"]}
        except ValueError:
            sys_flag, sys_risk, ms = set(), {}, float("nan")
        Fo = Go.graph["flow"]
        adj = {v for v in Fo.successors(root)} if root in Fo else set()      # baseline E1: chỉ công đoạn liền kề
        hops = nx.single_source_shortest_path_length(Fo, root) if root in Fo else {}
        base_risk = {n: 1.0 / h for n, h in hops.items() if h > 0}           # baseline E2: chỉ số bước
        e1s, e1b = e1_metrics(G, truth, sys_flag, thr), e1_metrics(G, truth, adj, thr)
        e2 = e2_metrics(G, truth, sys_risk, base_risk, root)
        obs_cache[dp] = (Go, e1s, e1b, e2, ms)

    for cp in exp["confounder_pcts"]:
        n_conf = int(math.ceil(len(non_anc) * cp / 100.0)) if cp else 0
        conf = set(perm[:n_conf])
        mrows = {m: (conf_rows[m] if m in conf else norm_rows[m]) for m in all_m}
        mrows[root] = frow
        pct_ = det.pct(pd.DataFrame([mrows[m] for m in all_m]))
        pct = dict(zip(all_m, pct_))
        flagged = {m for m in all_m if pct[m] >= det.thr_pct}
        naive_a = rank_credit(baseline_e3(pct, flagged, times, "anomaly"), root)
        naive_t = rank_credit(baseline_e3(pct, flagged, times, "recent"), root)
        for dp in exp["delete_pcts"]:
            Go, e1s, e1b, e2, ms = obs_cache[dp]
            reach = best_reach(Go, outcome)
            rec = dict(base, confounder_pct=cp, delete_pct=dp, n_confounders=n_conf,
                       n_flagged=len(flagged), root_flagged=bool(root in flagged), runtime_ms=round(ms, 2))
            for k, v in e1s.items():
                rec[f"e1_sys_{k}"] = v
            for k, v in e1b.items():
                rec[f"e1_base_{k}"] = v
            rec.update(e2_sys_spearman=e2["sys_spearman"], e2_base_spearman=e2["base_spearman"],
                       e2_sys_top3=e2["sys_top3_orders"], e2_base_top3=e2["base_top3_orders"], e2_n_desc=e2["n_desc"])
            for lam in exp["reach_floor_sweep"]:
                sc = machine_scores(Go, outcome, pct, lam, 0.0, reach)
                rc = rank_credit(sc, root)
                key = "e3_sys" if lam == exp["reach_floor"] else f"e3_sys_lam{lam}"
                rec[f"{key}_top1"], rec[f"{key}_top3"], rec[f"{key}_mrr"] = rc["top1"], rc["top3"], rc["mrr"]
            for gm in exp["hist_gamma_sweep"]:
                rc = rank_credit(machine_scores(Go, outcome, pct, exp["reach_floor"], gm, reach), root)
                rec[f"e3_hist_g{gm}_top1"], rec[f"e3_hist_g{gm}_top3"], rec[f"e3_hist_g{gm}_mrr"] = rc["top1"], rc["top3"], rc["mrr"]
            rc = rank_credit({m: pct[m] * float(np.clip((G.nodes[m]["hist_count"] + 1.0) /
                              (np.mean([G.nodes[x]["hist_count"] for x in all_m]) + 1.0), 0.25, 4.0)) for m in all_m}, root)
            rec["e3_naive_anomaly_hist_top1"], rec["e3_naive_anomaly_hist_top3"], rec["e3_naive_anomaly_hist_mrr"] = rc["top1"], rc["top3"], rc["mrr"]
            for nm, rc in (("e3_naive_anomaly", naive_a), ("e3_naive_recent", naive_t)):
                rec[f"{nm}_top1"], rec[f"{nm}_top3"], rec[f"{nm}_mrr"] = rc["top1"], rc["top3"], rc["mrr"]
            rows.append(rec)
    return rows


def run_all(df: pd.DataFrame | None, seeds: int = 30, exp: dict = EXP, progress: bool = True, det=None) -> tuple[pd.DataFrame, object]:
    """df: dữ liệu AI4I (bỏ qua nếu truyền `det`). `det`: bộ phát hiện bất kỳ có giao diện như Detector (vd. SECOMDetector)."""
    det = det if det is not None else Detector(df, exp)
    Gc = build_cause_graph(det.train, _cfg_for_graph()) if getattr(det, "domain", "ai4i") == "ai4i" else None
    rows = []
    for s in range(seeds):
        for size in exp["sizes"]:
            rows += run_seed_size(s, size, det, Gc, exp)
        if progress and (s + 1) % 5 == 0:
            print(f"  seed {s + 1}/{seeds}")
    return pd.DataFrame(rows), det


# =============================================================================
# 6. TỔNG HỢP, BIỂU ĐỒ, BÁO CÁO TRUNG THỰC (mục 15.4-15.5)
# =============================================================================
E1_COLS = ["P", "R", "F1", "R_process", "R_part", "R_product", "R_order"]


def _ms(x: pd.Series) -> str:
    x = x.dropna()
    return "n/a" if x.empty else f"{x.mean():.3f} ± {x.std(ddof=1) if len(x) > 1 else 0:.3f}"


def paired_diff(res: pd.DataFrame, a: str, b: str, by: list[str]) -> pd.DataFrame:
    """Hiệu a - b ghép cặp theo (seed, size) rồi lấy trung bình trên các nhóm `by`: mean, 95% CI, tỷ lệ seed thắng."""
    g = res.groupby(by + ["seed", "size"])[[a, b]].mean().reset_index()
    g["d"] = g[a] - g[b]
    out = g.groupby(by)["d"].agg(mean="mean", sd="std", n="count",
                                 win=lambda x: float((x > 1e-9).mean()), loss=lambda x: float((x < -1e-9).mean()))
    out["ci95"] = 1.96 * out["sd"] / np.sqrt(out["n"])
    return out.reset_index()


def summarize(res: pd.DataFrame) -> pd.DataFrame:
    metrics = [c for c in res.columns if c.startswith(("e1_", "e2_", "e3_")) and not c.endswith("n_desc")]
    g = res.groupby(["size", "confounder_pct", "delete_pct"])[metrics]
    m, s = g.mean(), g.std(ddof=1)
    out = m.add_suffix("__mean").join(s.add_suffix("__std")).reset_index()
    out.insert(3, "n_scenarios", g.size().values)
    return out


def make_chart(res: pd.DataFrame, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    d = res.groupby("delete_pct")
    x = sorted(res["delete_pct"].unique())

    def line(a, cols, labels, title, ylab):
        for c, lb in zip(cols, labels):
            m = d[c].mean().reindex(x)
            e = d[c].std().reindex(x) / np.sqrt(d[c].count().reindex(x))
            a.errorbar(x, m, yerr=1.96 * e, marker="o", capsize=3, label=lb)
        a.set_xlabel("% cạnh bị xóa khỏi đồ thị"); a.set_ylabel(ylab); a.set_title(title)
        a.set_xticks(x); a.grid(alpha=.3); a.legend(fontsize=8)
    line(ax[0], ["e1_sys_R", "e1_base_R"], ["Truy vết xuôi", "Cảnh báo cục bộ"], "E1/E4 – Recall đối tượng bị ảnh hưởng", "Recall")
    line(ax[1], ["e2_sys_spearman", "e2_base_spearman"], ["Điểm rủi ro", "Chỉ số bước"], "E2/E4 – Spearman với mức ảnh hưởng thật", "Spearman")
    sub = res[res["confounder_pct"] == 50]
    d3 = sub.groupby("delete_pct")
    for c, lb in (("e3_sys_top1", "Truy vết ngược (đồ thị)"), ("e3_naive_anomaly_top1", "Điểm bất thường cao nhất"),
                  ("e3_naive_recent_top1", "Gần nhất về thời gian")):
        m = d3[c].mean().reindex(x); e = d3[c].std().reindex(x) / np.sqrt(d3[c].count().reindex(x))
        ax[2].errorbar(x, m, yerr=1.96 * e, marker="o", capsize=3, label=lb)
    ax[2].set_xlabel("% cạnh bị xóa khỏi đồ thị"); ax[2].set_ylabel("Top-1"); ax[2].set_xticks(x)
    ax[2].set_title("E3/E4 – Top-1 máy gốc (confounder 50%)"); ax[2].grid(alpha=.3); ax[2].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    return True


def build_report(res: pd.DataFrame, det: Detector, seeds: int) -> str:
    L = []
    L += ["# D3 – P2: kết quả thí nghiệm E1–E4 (" + det.name + ")", "",
          f"{seeds} seed × 3 quy mô × 3 mức confounder × 4 mức xóa cạnh = {len(res)} dòng trong `p2_results.csv`. "
          "Số liệu là mean ± std qua seed (E1/E2 không phụ thuộc confounder nên lặp lại qua 3 mức confounder, không đổi mean/std).", "",
          "## Điều kiện thí nghiệm (đọc trước khi trích số)", "",
          f"- Phát hiện: {det.describe()}",
          f"- Mọi sự cố là dòng lỗi THẬT của {det.name} (tập test); cấu trúc đồ thị, trọng số, đệm, đơn hàng là MÔ PHỎNG, sinh độc lập với sự cố.",
          "- Ground truth tác động dùng mô hình dòng chảy khác công thức của hệ thống (đệm trừ phút, gộp noisy-OR, thời gian dừng và hằng số bù trễ thật). "
          "Hệ thống chỉ thấy đồ thị với trọng số/đệm có nhiễu và bị xóa cạnh.",
          "- Confounder chỉ được đặt ở máy KHÔNG nằm trong tổ tiên của kết quả xấu (đúng thiết kế 18.3). Vì cạnh chỉ bị xóa chứ không thêm cạnh sai, "
          "đồ thị không bao giờ nối nhầm confounder vào kết quả xấu: E3 ở mức xóa 0% gần như dễ theo cấu trúc, phần có giá trị là E4.",
          f"- Điểm truy vết ngược = pct_bất_thường × (λ + (1−λ)·reach), λ = {EXP['reach_floor']} đặt TRƯỚC khi chạy; bảng độ nhạy λ ở cuối chỉ để tham khảo.",
          "- Kết quả theo quy mô đồ thị mô phỏng tự đặt; chưa chứng minh trên dữ liệu DENSO.", ""]

    def table(rows, hdr):
        t = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
        t += ["| " + " | ".join(r) + " |" for r in rows]
        return t + [""]

    L += ["## E1 – Truy vết xuôi (pooled 4 tầng) theo % cạnh bị xóa (E4)", ""]
    rows = []
    for dp, g in res.groupby("delete_pct"):
        rows.append([f"{dp}%", _ms(g["e1_sys_P"]), _ms(g["e1_sys_R"]), _ms(g["e1_sys_F1"]),
                     _ms(g["e1_base_P"]), _ms(g["e1_base_R"]), _ms(g["e1_base_F1"])])
    L += table(rows, ["Xóa cạnh", "Hệ thống P", "Hệ thống R", "Hệ thống F1", "Cục bộ P", "Cục bộ R", "Cục bộ F1"])
    L += ["Recall theo tầng (hệ thống), theo % cạnh bị xóa:", ""]
    rows = [[f"{dp}%"] + [_ms(g[f"e1_sys_R_{t}"]) for t in LAYER_TYPES] for dp, g in res.groupby("delete_pct")]
    L += table(rows, ["Xóa cạnh", "Công đoạn", "Linh kiện", "Sản phẩm", "Đơn hàng"])
    L += ["Theo quy mô đồ thị (Recall hệ thống, ở 0% / 25% / 50% xóa):", ""]
    rows = []
    for sz in EXP["sizes"]:
        g = res[res["size"] == sz]
        rows.append([sz] + [_ms(g[g["delete_pct"] == d]["e1_sys_R"]) for d in (0, 25, 50)])
    L += table(rows, ["Quy mô", "0%", "25%", "50%"])

    L += ["## E2 – Điểm rủi ro vs mức ảnh hưởng thật", ""]
    rows = []
    for dp, g in res.groupby("delete_pct"):
        rows.append([f"{dp}%", _ms(g["e2_sys_spearman"]), _ms(g["e2_base_spearman"]),
                     _ms(g["e2_sys_top3"]), _ms(g["e2_base_top3"])])
    L += table(rows, ["Xóa cạnh", "Spearman hệ thống", "Spearman chỉ-số-bước", "Top-3 đơn hệ thống", "Top-3 đơn chỉ-số-bước"])

    L += ["## E3 – Truy vết ngược: Top-1 của máy gốc theo confounder × xóa cạnh", ""]
    rows = []
    for (cp, dp), g in res.groupby(["confounder_pct", "delete_pct"]):
        rows.append([f"{cp}%", f"{dp}%", _ms(g["e3_sys_top1"]), _ms(g["e3_sys_top3"]),
                     _ms(g["e3_naive_anomaly_top1"]), _ms(g["e3_naive_recent_top1"])])
    L += table(rows, ["Confounder", "Xóa cạnh", "Top-1 hệ thống", "Top-3 hệ thống", "Top-1 baseline bất thường", "Top-1 baseline gần nhất"])
    L += ["Top-1 của baseline 'bất thường cao nhất' bị chặn trên bởi việc bộ phát hiện có chấm điểm máy gốc cao nhất hay không "
          f"(máy gốc bị phát hiện trong {res.drop_duplicates(['seed','size','confounder_pct'])['root_flagged'].mean():.1%} kịch bản).", ""]

    L += ["## Kiểm tra tiêu chí thành công (15.5): hệ thống có vượt baseline khi thiếu cạnh?", "",
          "Hiệu hệ thống − baseline, ghép cặp theo (seed, quy mô), kèm khoảng tin cậy 95% và tỷ lệ seed thắng/thua.", ""]
    pairs = [("E1 Recall", "e1_sys_R", "e1_base_R", ["delete_pct"]),
             ("E2 Spearman", "e2_sys_spearman", "e2_base_spearman", ["delete_pct"]),
             ("E2 Top-3 đơn", "e2_sys_top3", "e2_base_top3", ["delete_pct"])]
    rows = []
    for nm, a, b, by in pairs:
        pdff = paired_diff(res, a, b, by)
        for r in pdff.itertuples():
            rows.append([nm, f"{r.delete_pct}%", f"{r.mean:+.3f} ± {r.ci95:.3f}", f"{r.win:.0%}", f"{r.loss:.0%}"])
    L += table(rows, ["Chỉ số", "Xóa cạnh", "Hiệu (hệ thống − baseline)", "% seed thắng", "% seed thua"])
    rows = []
    for nm, b in (("E3 vs bất thường cao nhất", "e3_naive_anomaly_top1"), ("E3 vs gần nhất", "e3_naive_recent_top1")):
        pdff = paired_diff(res[res["confounder_pct"] > 0], "e3_sys_top1", b, ["confounder_pct", "delete_pct"])
        for r in pdff.itertuples():
            rows.append([nm, f"{r.confounder_pct}%", f"{r.delete_pct}%", f"{r.mean:+.3f} ± {r.ci95:.3f}", f"{r.win:.0%}", f"{r.loss:.0%}"])
    L += table(rows, ["So sánh", "Confounder", "Xóa cạnh", "Hiệu Top-1", "% seed thắng", "% seed thua"])

    # kết luận tự động, trung thực: nêu cả mức tuyệt đối vì "vượt baseline" không đồng nghĩa "dùng được"
    verdicts = []
    for nm, a_, b_ in (("E1 Recall", "e1_sys_R", "e1_base_R"), ("E2 Spearman", "e2_sys_spearman", "e2_base_spearman")):
        for dp in (0, 25, 50):
            sub = res[res["delete_pct"] == dp]
            r = paired_diff(sub, a_, b_, ["delete_pct"]).iloc[0]
            sig = r["mean"] - r["ci95"] > 0
            verdicts.append(f"- {nm} ở {dp}% xóa cạnh: hệ thống {sub[a_].mean():.3f} vs baseline {sub[b_].mean():.3f} "
                            f"(hiệu {r['mean']:+.3f}, CI95 ±{r['ci95']:.3f}) -> "
                            + ("vượt baseline có ý nghĩa thống kê." if sig else "KHÔNG vượt baseline có ý nghĩa thống kê."))
    for b_, nm in (("e3_naive_anomaly_top1", "bất thường cao nhất"), ("e3_naive_recent_top1", "gần nhất")):
        for dp in (0, 25, 50):
            sub = res[(res["delete_pct"] == dp) & (res["confounder_pct"] == 50)]
            r = paired_diff(sub, "e3_sys_top1", b_, ["delete_pct"]).iloc[0]
            sig = r["mean"] - r["ci95"] > 0
            verdicts.append(f"- E3 (confounder 50%) ở {dp}% xóa cạnh vs baseline {nm}: hệ thống {sub['e3_sys_top1'].mean():.3f} "
                            f"vs {sub[b_].mean():.3f} (hiệu {r['mean']:+.3f}, CI95 ±{r['ci95']:.3f}) -> "
                            + ("vượt baseline có ý nghĩa thống kê." if sig else "KHÔNG vượt baseline có ý nghĩa thống kê."))
    L += ["## Kết luận", ""] + verdicts + [""]
    d0 = res[res["delete_pct"] == 0]["e1_sys_R"].mean()
    d50 = res[res["delete_pct"] == 50]["e1_sys_R"].mean()
    L += [f"Recall truy vết xuôi giảm từ {d0:.3f} (đồ thị đủ) xuống {d50:.3f} (thiếu 50% cạnh). "
          "Nếu dữ liệu DENSO thiếu nhiều quan hệ phụ thuộc, đây là mức suy giảm cần kỳ vọng; không nên trình bày số ở 0% như hiệu năng thực tế. "
          "Precision được tính bằng 0 khi hệ thống không cảnh báo đối tượng nào (ví dụ cạnh máy -> công đoạn bị xóa), nên std của P ở mức xóa cao rất lớn.", ""]

    L += ["## Độ nhạy của λ trong truy vết ngược (tham khảo, KHÔNG dùng để chọn lại λ)", ""]
    rows = []
    for dp, g in res[res["confounder_pct"] == 50].groupby("delete_pct"):
        rows.append([f"{dp}%"] + [_ms(g["e3_sys_top1" if lam == EXP["reach_floor"] else f"e3_sys_lam{lam}_top1"])
                                 for lam in EXP["reach_floor_sweep"]] + [_ms(g["e3_naive_anomaly_top1"])])
    L += table(rows, ["Xóa cạnh"] + [f"λ={l}" for l in EXP["reach_floor_sweep"]] + ["baseline bất thường"])
    L += ["## Thời gian chạy (đóng góp cho E6, chỉ phần truy vết + chấm điểm)", "",
          f"Median {res['runtime_ms'].median():.2f} ms, p95 {res['runtime_ms'].quantile(.95):.2f} ms mỗi sự cố "
          "(ước tính thủ công của kỹ sư vẫn cần phỏng vấn, xem việc P2.8 trong tài liệu).", ""]
    return "\n".join(L)


def build_history_section(res_all: pd.DataFrame) -> str:
    """Giá trị của tần suất lỗi lịch sử theo máy (P1.5). Hai chế độ chọn máy gốc:
    uniform = máy gốc chọn ngẫu nhiên đều (lịch sử KHÔNG mang thông tin, kiểm tra xem dùng lịch sử có làm hại không);
    proportional = máy gốc chọn tỷ lệ với tỷ lệ lỗi thật của máy (lịch sử có thông tin; đây là GIẢ ĐỊNH của mô phỏng)."""
    L = ["## Tần suất lỗi lịch sử theo máy (P1.5): có giúp truy vết ngược không?", "",
         "Hệ số lịch sử = (số sự cố lịch sử + 1)/(trung bình + 1), chặn [0,25; 4], lũy thừa γ. Lịch sử là một giai đoạn đếm riêng "
         f"({EXP['hist_units']} đơn vị) tách khỏi kịch bản, có nhiễu đếm Poisson. Confounder 50%. Các số mean ± std, Top-1 máy gốc.", ""]
    hdr = ["Chế độ máy gốc", "Xóa cạnh", "Bất thường", "Bất thường × lịch sử", "Đồ thị (γ=0)"] + \
          [f"Đồ thị + lịch sử γ={g}" + (" (thêm sau)" if g == 0.25 else "") for g in EXP["hist_gamma_sweep"]]
    L += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for (rs, dp), g in res_all[res_all["confounder_pct"] == 50].groupby(["root_sampling", "delete_pct"]):
        cells = [rs, f"{dp}%", _ms(g["e3_naive_anomaly_top1"]), _ms(g["e3_naive_anomaly_hist_top1"]), _ms(g["e3_sys_top1"])]
        cells += [_ms(g[f"e3_hist_g{gm}_top1"]) for gm in EXP["hist_gamma_sweep"]]
        L.append("| " + " | ".join(cells) + " |")
    L += ["", "Hiệu ghép cặp (đồ thị + lịch sử) − (đồ thị γ=0), Top-1, confounder 50%:", "",
          "| Chế độ máy gốc | γ | Xóa cạnh | Hiệu | % seed thắng | % seed thua |", "|---|---|---|---|---|---|"]
    for rs, g in res_all[res_all["confounder_pct"] == 50].groupby("root_sampling"):
        for gm in EXP["hist_gamma_sweep"]:
            for r in paired_diff(g, f"e3_hist_g{gm}_top1", "e3_sys_top1", ["delete_pct"]).itertuples():
                L.append(f"| {rs} | {gm} | {r.delete_pct}% | {r.mean:+.3f} ± {r.ci95:.3f} | {r.win:.0%} | {r.loss:.0%} |")
    L += ["", "Cách đọc: ở chế độ uniform lịch sử không có thông tin thật, nên kết quả cho thấy dùng nó có làm hại hay không. "
          "Ở chế độ proportional, lợi ích là hệ quả của giả định 'máy hay lỗi thì lỗi nhiều hơn', không phải bằng chứng trên dữ liệu DENSO. "
          "γ = 0,5 và 1,0 đặt trước; γ = 0,25 thêm sau khi thấy kết quả nên chỉ mang tính thăm dò; cần số liệu bảo trì thật của DENSO để biết lịch sử có đáng tin hay không.",
          "**Kết luận:** trong thiết lập này, nhân trực tiếp hệ số lịch sử vào điểm không cải thiện Top-1: nó làm giảm rõ ở chế độ uniform và "
          "không khác biệt có ý nghĩa (hoặc giảm) ở chế độ proportional, kể cả khi lịch sử có thông tin. Lý do khả dĩ: hệ số dao động tới 16 lần "
          "(0,25 đến 4) nên át tín hiệu đồ thị và điểm bất thường vốn chưa được hiệu chỉnh thành xác suất. Vì vậy `backward_trace()` mặc định "
          "`gamma = 0` (không dùng lịch sử); tham số vẫn có để thử khi có dữ liệu bảo trì thật hoặc khi có cách kết hợp có hiệu chỉnh (ví dụ prior Bayes).", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="D3-P2: thí nghiệm E1-E4")
    ap.add_argument("--csv", default="ai4i2020.csv")
    ap.add_argument("--out", default="p2_outputs")
    ap.add_argument("--seeds", type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    df = P.load_data(a.csv)
    t0 = time.time()
    res_u, det = run_all(df, a.seeds)                                            # chế độ chính: máy gốc ngẫu nhiên đều
    res_p, _ = run_all(df, a.seeds, {**EXP, "root_sampling": "proportional"})    # chế độ phụ: lịch sử có thông tin
    res_all = pd.concat([res_u, res_p], ignore_index=True)
    res = res_u
    res_all.to_csv(out / "p2_results.csv", index=False)
    pd.concat([summarize(res_u).assign(root_sampling="uniform"),
               summarize(res_p).assign(root_sampling="proportional")]).to_csv(out / "p2_summary.csv", index=False)
    (out / "p2_experiments_report.md").write_text(
        build_report(res, det, a.seeds) + "\n" + build_history_section(res_all), encoding="utf-8")
    ok = make_chart(res, out / "p2_experiments_E4.png")
    (out / "p2_experiments_config.json").write_text(json.dumps(P.clean(EXP), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Xong {len(res_all)} dòng trong {time.time() - t0:.1f}s -> {out.resolve()}" + ("" if ok else " (không có matplotlib: bỏ biểu đồ)"))
    print(f"Bộ phát hiện: recall test {det.test_recall:.3f}, báo sai {det.test_false_alarm:.3f}, ngưỡng pct {det.thr_pct:.3f}")


if __name__ == "__main__":
    main()
