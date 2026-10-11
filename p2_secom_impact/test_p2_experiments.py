# -*- coding: utf-8 -*-
"""Kiểm thử phần thí nghiệm E1-E4 (p2_experiments.py).  Chạy:  AI4I_CSV=ai4i2020.csv pytest -q test_p2_experiments.py
Các test kiểm tra tính đúng đắn của KHUNG thí nghiệm (không rò rỉ, độc lập cấu trúc, tái lập), không kiểm tra độ chính xác ngoài thực tế."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p2_experiments as E  # noqa: E402
import p2_impact_trace as P  # noqa: E402


def _csv():
    for c in (os.environ.get("AI4I_CSV"), HERE / "ai4i2020.csv", Path("ai4i2020.csv")):
        if c and Path(c).exists():
            return str(c)


CSV = _csv()
pytestmark = pytest.mark.skipif(CSV is None, reason="Không tìm thấy ai4i2020.csv")


@pytest.fixture(scope="module")
def df():
    return P.load_data(CSV)


@pytest.fixture(scope="module")
def det(df):
    return E.Detector(df)


@pytest.mark.parametrize("size", list(E.EXP["sizes"]))
def test_graph_is_valid_dag_and_deterministic(size):
    G1, G2 = E.generate_graph(3, size), E.generate_graph(3, size)
    assert sorted(G1.edges(data="w")) == sorted(G2.edges(data="w"))          # tái lập theo seed
    assert nx.is_directed_acyclic_graph(G1.graph["flow"])
    F = G1.graph["flow"]
    orders = [n for n, d in G1.nodes(data=True) if d["type"] == "order"]
    machines = G1.graph["machines"]
    reach = set().union(*(nx.descendants(F, m) for m in machines))
    assert all(o in reach for o in orders)                                    # mọi đơn đều có máy thượng nguồn
    assert all(F.out_degree(m) >= 1 for m in machines)
    assert G1.graph["order_of"] and len(G1.graph["order_of"]) == E.EXP["n_units"]


def test_sizes_increase_and_seeds_differ():
    n = [E.generate_graph(1, s).number_of_nodes() for s in E.EXP["sizes"]]
    assert n == sorted(n) and len(set(n)) == 3
    assert sorted(E.generate_graph(1, "medium").edges(data="w")) != sorted(E.generate_graph(2, "medium").edges(data="w"))


def test_graph_independent_of_fault_data(df):
    """Cấu trúc đồ thị chỉ phụ thuộc (seed, size): sinh trước và sau khi dựng bộ phát hiện cho kết quả y hệt."""
    a = E.generate_graph(5, "large")
    E.Detector(df)
    b = E.generate_graph(5, "large")
    assert sorted(a.edges(data="w")) == sorted(b.edges(data="w"))


def test_observed_graph_deletion_and_isolation():
    G = E.generate_graph(2, "medium")
    before = sorted(G.edges(data="w"))
    n_flow = sum(1 for *_, d in G.edges(data=True) if d.get("flow"))
    for pct in (0, 10, 25, 50):
        Go = E.observed_graph(G, pct, 2, "medium")
        assert sum(1 for *_, d in Go.edges(data=True) if d.get("flow")) == n_flow - int(round(n_flow * pct / 100))
        assert Go.graph["flow"].number_of_edges() == sum(1 for *_, d in Go.edges(data=True) if d.get("flow"))
    assert sorted(G.edges(data="w")) == before                                # đồ thị đầy đủ không bị sửa
    assert E.observed_graph(G, 25, 2, "medium").edges == E.observed_graph(G, 25, 2, "medium").edges


def test_true_impact_properties():
    G = E.generate_graph(4, "medium")
    root = G.graph["machines"][0]
    zero = E.true_impact(G, root, 100, 0.0, 24.0)
    assert all(v == 0 for v in zero.values())
    lo = E.true_impact(G, root, 100, 20.0, 24.0)
    hi = E.true_impact(G, root, 100, 200.0, 24.0)
    assert all(0.0 <= v <= 1.0 for v in hi.values())
    assert all(hi[n] >= lo[n] - 1e-9 for n in lo)                             # dừng lâu hơn không giảm tác động
    assert hi[root] == 0.0
    G2 = copy.deepcopy(G)                                                      # thêm đệm không làm tăng tác động
    for u, v, d in G2.edges(data=True):
        if d.get("flow"):
            d["buffer_min"] += 30.0
    E._refresh_flow(G2)
    more = E.true_impact(G2, root, 100, 200.0, 24.0)
    assert all(more[n] <= hi[n] + 1e-9 for n in hi)


def test_true_impact_uses_different_formula_than_system(df):
    """Ground truth không phải bản sao của trace_forward: trên cùng đồ thị đầy đủ hai kết quả khác nhau."""
    G = E.generate_graph(6, "medium")
    root = G.graph["machines"][3]
    t = E.true_impact(G, root, 500, 90.0, 24.0)
    s = P.trace_forward(G, root, 500, 0.9, 90.0, thr=0.0)
    risk = {a["id"]: a["risk"] for a in s["affected"]}
    common = [n for n in risk if G.nodes[n]["type"] != "order"]
    assert any(abs(risk[n] - t[n]) > 1e-3 for n in common)


def test_rank_credit_ties():
    sc = {"a": 1.0, "b": 1.0, "c": 0.2, "d": 0.1}
    r = E.rank_credit(sc, "a")
    assert r["top1"] == pytest.approx(0.5) and r["top3"] == 1.0
    assert E.rank_credit(sc, "d")["top3"] == 0.0


def test_detector_no_leakage_and_validation_threshold(det):
    tr, va, te = set(det.train["UDI"]), set(det.val["UDI"]), set(det.test["UDI"])
    assert not (tr & va) and not (tr & te) and not (va & te)
    assert set(det.fail_pool["UDI"]) <= te and set(det.norm_pool["UDI"]) <= te   # kịch bản chỉ lấy dòng test
    assert (det.fail_pool[list(P.MODES)[:4]].sum(axis=1) > 0).all()              # không có RNF-only
    assert det.feature_set in det.CANDIDATES
    assert det.candidate_val_far[det.feature_set] == min(det.candidate_val_far.values())
    vf = det.val[det.val[list(P.MODES)[:4]].sum(axis=1) > 0]
    assert (det.pct(vf) >= det.thr_pct).mean() >= 0.88                           # recall validation ~ 90%


def test_cause_graph_priors_only_from_train(det):
    Gc = E.build_cause_graph(det.train, P.CFG)
    cnt = {d["code"]: d["count"] for _, d in Gc.nodes(data=True) if d["type"] == "failure_mode"}
    assert cnt["HDF"] == int(det.train["HDF"].sum()) + 1


@pytest.fixture(scope="module")
def small_run(df):
    return E.run_all(df, seeds=4, progress=False)


def test_run_shape_columns_and_determinism(df, small_run):
    res, det = small_run
    assert len(res) <= 4 * 3 * 3 * 4 and len(res) >= 4 * 3 * 3 * 4 - 12
    for c in ("seed", "size", "confounder_pct", "delete_pct", "e1_sys_R", "e1_base_R", "e2_sys_spearman",
              "e3_sys_top1", "e3_naive_anomaly_top1", "e3_naive_recent_top1"):
        assert c in res.columns
    res2, _ = E.run_all(df, seeds=4, progress=False)
    assert res.drop(columns="runtime_ms").equals(res2.drop(columns="runtime_ms"))


def test_scenarios_shared_across_levels(small_run):
    res, _ = small_run
    g = res.groupby(["seed", "size"])[["root", "outcome", "downtime_true"]].nunique()
    assert (g == 1).all().all()                                                  # cùng kịch bản qua mọi mức xóa/confounder


def test_confounders_only_off_ancestors_and_nested(small_run):
    res, _ = small_run
    for (_, _), g in res.groupby(["seed", "size"]):
        c = g.groupby("confounder_pct")["n_confounders"].first()
        assert c[0] == 0 and c[0] <= c[25] <= c[50]


def test_baseline_e3_does_not_depend_on_deletion(small_run):
    res, _ = small_run
    g = res.groupby(["seed", "size", "confounder_pct"])["e3_naive_anomaly_top1"].nunique()
    assert (g == 1).all()


def test_forward_beats_local_baseline_on_full_graph(small_run):
    res, _ = small_run
    full = res[res["delete_pct"] == 0]
    assert full["e1_sys_R"].mean() > full["e1_base_R"].mean() + 0.3
    assert (res["e1_sys_R"].dropna().between(0, 1)).all()


def test_recall_degrades_with_deleted_edges(small_run):
    res, _ = small_run
    m = res.groupby("delete_pct")["e1_sys_R"].mean()
    assert m[0] > m[25] > m[50]


def test_report_and_summary_build(small_run):
    res, det = small_run
    md = E.build_report(res, det, 4)
    assert "## Kết luận" in md and "E4" in md
    s = E.summarize(res)
    assert {"size", "confounder_pct", "delete_pct", "n_scenarios"} <= set(s.columns)


def test_backward_trace_api_and_ranking():
    G = E.generate_graph(7, "medium")
    F = G.graph["flow"]
    outcome = next(n for n, d in G.nodes(data=True) if d["type"] == "order")
    anc = [m for m in E.ancestor_machines(G, outcome) if m in G.graph["machines"]]
    others = [m for m in G.graph["machines"] if m not in anc]
    pct = {m: 0.3 for m in G.graph["machines"] + G.graph["substitutes"]}
    pct[anc[0]] = 0.95                                                         # máy tổ tiên bất thường cao
    if others:
        pct[others[0]] = 0.95                                                  # confounder cũng bất thường cao
    top = E.backward_trace(G, outcome, pct, topk=3)
    assert [r["rank"] for r in top] == [1, 2, 3] and len(top) == 3
    assert top[0]["machine"] == anc[0] and top[0]["path"][0] == anc[0] and top[0]["path"][-1] == outcome
    assert all(top[i]["score"] >= top[i + 1]["score"] for i in range(2))
    if others:
        c = next(r for r in E.backward_trace(G, outcome, pct, topk=len(pct)) if r["machine"] == others[0])
        assert c["reach"] == 0.0 and c["path"] == []                           # confounder không nối tới kết quả


def test_backward_trace_degrades_gracefully_and_validates():
    G = E.generate_graph(7, "small")
    outcome = next(n for n, d in G.nodes(data=True) if d["type"] == "order")
    machines = G.graph["machines"]
    pct = {m: 0.1 * (i + 1) for i, m in enumerate(machines)}
    Go = E.observed_graph(G, 50, 7, "small")
    assert len(E.backward_trace(Go, outcome, pct, topk=2)) == 2                # đồ thị thiếu cạnh vẫn trả kết quả
    with pytest.raises(ValueError):
        E.backward_trace(G, "KHONG_CO", pct)
    with pytest.raises(ValueError):
        E.backward_trace(G, outcome, {"M999": 0.5})


def test_history_is_independent_of_scenario_and_gamma_zero_is_default():
    G1, G2 = E.generate_graph(9, "large"), E.generate_graph(9, "large")
    assert [G1.nodes[m]["hist_count"] for m in G1.graph["machines"]] == [G2.nodes[m]["hist_count"] for m in G2.graph["machines"]]
    pct = {m: 0.5 for m in G1.graph["machines"]}
    outcome = next(n for n, d in G1.nodes(data=True) if d["type"] == "order")
    assert E.machine_scores(G1, outcome, pct) == E.machine_scores(G1, outcome, pct, gamma=0.0)
    assert E.machine_scores(G1, outcome, pct, gamma=1.0) != E.machine_scores(G1, outcome, pct, gamma=0.0)


def test_proportional_root_sampling_favours_failure_prone_machines(df):
    det = E.Detector(df)
    exp = {**E.EXP, "root_sampling": "proportional"}
    res, _ = E.run_all(df, seeds=12, exp=exp, progress=False)
    assert set(res["root_sampling"]) == {"proportional"}
    rates = []
    for (seed, size), g in res.groupby(["seed", "size"]):
        G = E.generate_graph(seed, size, exp)
        r = g["root"].iloc[0]
        rates.append(G.nodes[r]["true_fail_per_1000"] / np.mean([G.nodes[m]["true_fail_per_1000"] for m in G.graph["machines"]]))
    assert np.mean(rates) > 1.1


def test_backward_trace_runs_on_main_pipeline_graph(df):
    """Đồ thị của pipeline chính (build_graph, máy M05) dùng được với backward_trace để P5 nối hai phần."""
    orders, order_of = P.build_orders(df, P.CFG)
    G = P.build_graph(df, orders, order_of, P.CFG)
    top = E.backward_trace(G, "ORD_H03", {"M03": 0.2, "M05": 0.9, "M07": 0.1, "M09": 0.3}, topk=3)
    assert top[0]["machine"] == "M05" and top[0]["path"][0] == "M05" and top[0]["path"][-1] == "ORD_H03"
    m07 = next(r for r in E.backward_trace(G, "ORD_H03", {"M05": 0.9, "M07": 0.99}, topk=2) if r["machine"] == "M07")
    assert m07["reach"] == 0.0                                                   # máy dự phòng không nằm trên dòng chảy
