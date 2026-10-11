# -*- coding: utf-8 -*-
"""Kiểm thử phần SECOM. Chạy:  SECOM_DIR=secom pytest -q test_p2_secom.py   (bỏ qua nếu không có file SECOM)"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import p2_experiments as E  # noqa: E402
import p2_impact_trace as P  # noqa: E402
import p2_schema as S  # noqa: E402
import p2_secom as SC  # noqa: E402

D = Path(os.environ.get("SECOM_DIR", HERE / "secom"))
HAVE = (D / "secom.data").exists() and (D / "secom_labels.data").exists()
needs = pytest.mark.skipif(not HAVE, reason="Không tìm thấy secom/secom.data")


@pytest.fixture(scope="module")
def raw():
    return SC.load_secom(str(D / "secom.data"), str(D / "secom_labels.data"))


@pytest.fixture(scope="module")
def det(raw):
    return SC.SECOMDetector(*raw)


@needs
def test_facts_counted_from_file(raw):
    X, y, t = raw
    f = SC.data_facts(X, y, t)
    assert (f["rows"], f["features"], f["fails"]) == (1567, 590, 104)             # đếm trực tiếp, khớp mô tả UCI
    assert f["fails"] + f["passes"] == f["rows"]
    assert t.is_monotonic_increasing
    assert sum(v["rows"] for v in f["splits"].values()) == f["rows"]
    assert sum(v["fails"] for v in f["splits"].values()) == f["fails"]


@needs
def test_chronological_split_no_overlap_no_shuffle(det):
    assert det.t["train"].max() <= det.t["val"].min() <= det.t["val"].max() <= det.t["test"].min()


@needs
def test_preprocessing_fit_on_train_only(raw, det):
    X, y, t = raw
    cols = [c for c in X.columns if det.train[c].isna().mean() <= 0.4]
    assert det.prep.keep_cols == cols                                             # lọc cột chỉ dựa trên train
    med = det.train[cols].median()
    assert np.allclose(det.prep.imp.statistics_, med.to_numpy(), equal_nan=True)    # trung vị lấy từ train
    assert det.prep.n_pca < det.prep.n_after_var < 590
    assert det.prep.transform(det.X["test"]).shape == (len(det.X["test"]), det.prep.n_pca)


@needs
def test_threshold_from_validation_and_test_pools(det):
    vp = det.y["val"].to_numpy() == 1
    assert (det.pct(det.X["val"])[vp] >= det.thr_pct - 1e-9).mean() >= 0.89        # recall validation ~ 90%
    assert (det.fail_pool["_label"] == 1).all() and (det.norm_pool["_label"] == 0).all()
    assert det.fail_pool["_time"].min() >= det.t["val"].max()                       # kịch bản chỉ lấy dòng test


@needs
def test_e0_table_shape_and_no_smote(det):
    tab = SC.e0_table(det, n_boot=50)
    assert len(tab) == 3 and {"precision", "recall", "pr_auc", "roc_auc", "false_alarm_rate"} <= set(tab.columns)
    assert ((tab["recall_lo"] <= tab["recall"]) | tab["recall"].isna()).all()
    assert det.lr.class_weight == "balanced"                                         # class weight, không SMOTE
    assert "SMOTE" not in open(HERE / "p2_secom.py", encoding="utf-8").read().replace("không dùng SMOTE", "").replace("KHÔNG dùng SMOTE", "")


@needs
def test_incidents_valid_and_labels_hidden(det):
    incs = SC.build_incidents(det)
    assert incs and SC.validate_incidents(incs) == len(incs)
    for r in incs:
        assert not ({"TWF", "HDF", "PWF", "OSF", "RNF", "label", "Machine failure"} & set(r))   # nhãn chỉ nằm trong eval_only
        assert r["dataset"] == "SECOM" and r["timestamp_is_synthetic"] is False
        assert 0 <= r["anomaly_score"] <= 1 and r["incident_id"].startswith("INC_SECOM_")
    assert len({r["incident_id"] for r in incs}) == len(incs)


def test_true_impact_hand_check():
    """Kiểm tra tay trên đồ thị nhỏ M -> P -> A -> PRD -> ORD (P2.5)."""
    cfg = P.CFG
    G = nx.DiGraph()
    inc = P.t_min(cfg, 1)
    for n, d in dict(M=dict(type="machine"), P=dict(type="process"), A=dict(type="part"), PRD=dict(type="product"),
                     O=dict(type="order", last_min=inc + 600.0, slack_min=60.0, priority=2)).items():
        G.add_node(n, layer="logic", **d)
    for u, v, w, b in (("M", "P", 1.0, 0.0), ("P", "A", 0.8, 10.0), ("A", "PRD", 0.5, 0.0), ("PRD", "O", 1.0, 0.0)):
        G.add_edge(u, v, flow=True, w=w, buffer_min=b)
    E._refresh_flow(G)
    G.graph["cfg"] = cfg
    t = E.true_impact(G, "M", 1, 100.0, 24.0)
    # thiếu hụt (phút): P=100, A=0.8*(100-10)=72, PRD=0.5*72=36, ORD=36
    assert t["P"] == pytest.approx(1.0) and t["A"] == pytest.approx(0.72) and t["PRD"] == pytest.approx(0.36)
    delay = 36 * math.exp(-10 / 24)
    assert t["O"] == pytest.approx(min(1, delay / 60) * cfg["prio_factor"][2])
    assert t["M"] == 0.0


def test_baseline_e3_modes():
    pct = {"a": 0.9, "b": 0.5, "c": 0.7}
    assert E.baseline_e3(pct, {"a", "c"}, {"a": -100, "b": -5, "c": -10}, "anomaly") == pct
    r = E.baseline_e3(pct, {"a", "c"}, {"a": -100, "b": -5, "c": -10}, "recent")
    assert max(r, key=r.get) == "c" and r["b"] < r["a"]                              # gần nhất trong các máy bị cảnh báo
    with pytest.raises(ValueError):
        E.baseline_e3(pct, set(), {}, "x")


@needs
def test_secom_runs_through_experiment_pipeline_and_backward_trace(det):
    res, d2 = E.run_all(None, seeds=3, det=det, progress=False)
    assert set(res["domain"]) == {"secom"} and len(res) > 0
    assert res["e3_sys_top1"].between(0, 1).all() and res["e1_sys_R"].dropna().between(0, 1).all()
    ex = SC.example_scenario(det, seed=1)
    assert len(ex["backward_trace_top5"]) == 5 and ex["backward_truth"] not in ex["confounders"]
    res2, _ = E.run_all(None, seeds=3, det=det, progress=False)
    assert res.drop(columns="runtime_ms").equals(res2.drop(columns="runtime_ms"))     # tái lập theo seed
