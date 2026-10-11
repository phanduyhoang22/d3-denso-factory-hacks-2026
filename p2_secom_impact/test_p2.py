# -*- coding: utf-8 -*-
"""
Bộ kiểm thử P2 (D3). Chạy:   pytest -q test_p2.py
Cần file dữ liệu: đặt ai4i2020.csv cạnh file này hoặc đặt biến môi trường AI4I_CSV=/đường/dẫn/ai4i2020.csv
(không có thì các test bị bỏ qua).

LƯU Ý ĐỌC KẾT QUẢ: nhiều test kiểm tra tính nhất quán/đường ống (đồ thị nối đúng, hợp đồng schema, tính an toàn
của đầu vào). Chúng KHÔNG chứng minh độ chính xác dự báo ngoài thực tế (lớp nghiệp vụ là giả lập).
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import p2_impact_trace as P  # noqa: E402
import p2_schema as S        # noqa: E402


def _find_csv():
    for c in (os.environ.get("AI4I_CSV"), HERE / "ai4i2020.csv", Path("ai4i2020.csv")):
        if c and Path(c).exists():
            return str(c)
    return None


CSV = _find_csv()
pytestmark = pytest.mark.skipif(CSV is None, reason="Không tìm thấy ai4i2020.csv (đặt AI4I_CSV)")


def run_cli(*args):
    return subprocess.run([sys.executable, str(HERE / "p2_impact_trace.py"), "--csv", CSV, *args],
                          capture_output=True, text=True)


def build(cfg=None):
    cfg = copy.deepcopy(cfg or P.CFG)
    df = P.load_data(CSV)
    dfi = df.set_index("UDI", drop=False)
    orders, order_of = P.build_orders(df, cfg)
    return df, dfi, P.build_graph(df, orders, order_of, cfg)


@pytest.fixture(scope="module")
def world():
    df, dfi, G = build()
    return df, dfi, G


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("p2_out")
    r = run_cli("--out", str(d), "--fast")
    assert r.returncode == 0, r.stderr[-500:]
    return d


def load(d, name):
    return json.loads((Path(d) / name).read_text(encoding="utf-8"))


SCEN = ["S1_machine_incident_worst", "S1b_machine_incident_median", "S2_order_backward", "S3_material_delay"]


# ------------------------------------------------------------------ truy vết xuôi
def test_substitute_reduces_delay_and_effective_downtime(world):
    _, _, G = world
    a = P.trace_forward(G, "M05", 3351, 0.87, 73.0, use_substitute=True)
    b = P.trace_forward(G, "M05", 3351, 0.87, 73.0, use_substitute=False)
    da = {r["id"]: r["delay_min"] for r in a["_all_orders"]}
    db = {r["id"]: r["delay_min"] for r in b["_all_orders"]}
    assert all(da[k] <= db[k] for k in da) and any(da[k] < db[k] for k in da)
    assert a["effective_downtime_min"] == pytest.approx(73.0 * 0.7, abs=0.05)
    assert b["effective_downtime_min"] == 73.0
    assert sum(r["miss_deadline"] for r in a["_all_orders"]) <= sum(r["miss_deadline"] for r in b["_all_orders"])
    assert a["substitutes"][0]["machine_id"] == "M07"


@pytest.mark.parametrize("src", ["M07", "S_AIR", "FM_HDF", "KHONG_TON_TAI"])
def test_forward_rejects_non_flow_source(world, src):
    with pytest.raises(ValueError):
        P.trace_forward(world[2], src, 100, 0.8, 45.0)


@pytest.mark.parametrize("args", [("M05", 999999, 0.8, 45.0), ("M05", 100, 1.5, 45.0), ("M05", 100, 0.8, -1.0)])
def test_forward_rejects_bad_numbers(world, args):
    with pytest.raises(ValueError):
        P.trace_forward(world[2], *args)


def test_zero_downtime_has_no_impact(world):
    assert P.trace_forward(world[2], "M05", 500, 0.9, 0.0)["affected"] == []


def test_invariants_risk_and_deadlines(world):
    _, dfi, G = world
    for udi in dfi.index[dfi["Machine failure"] == 1][:80]:
        rep = P.analyze_incident(G, dfi, int(udi))
        sev = rep["effect"]["severity"]
        t_inc = P.t_min(G.graph["cfg"], int(udi))
        for a in rep["affected"]:
            assert 0 <= a["risk"] <= sev + 1e-9
            if a["type"] == "order":
                assert a["miss_deadline"] == (a["delay_min"] > a["slack_min"])
                assert G.nodes[a["id"]]["last_min"] > t_inc          # đơn đã xong trước sự cố không xuất hiện


def test_more_buffer_never_increases_risk():
    _, dfi, G1 = build()
    cfg2 = copy.deepcopy(P.CFG)
    cfg2["buf_a13_p03"] += 20.0
    _, _, G2 = build(cfg2)
    r1 = {a["id"]: a["risk"] for a in P.trace_forward(G1, "M05", 3351, 0.87, 73.0, thr=0.0)["affected"]}
    r2 = {a["id"]: a["risk"] for a in P.trace_forward(G2, "M05", 3351, 0.87, 73.0, thr=0.0)["affected"]}
    assert all(r2.get(k, 0) <= v + 1e-9 for k, v in r1.items())
    assert any(r2.get(k, 0) < v for k, v in r1.items())


def test_self_check_and_determinism(world):
    df, _, _ = world
    o1, m1 = P.build_orders(df, P.CFG)
    o2, m2 = P.build_orders(df, P.CFG)
    assert o1.equals(o2) and m1 == m2


# ------------------------------------------------------------------ cấu hình một nguồn (finding 9)
def test_config_copy_is_respected():
    cfg2 = copy.deepcopy(P.CFG)
    cfg2.update(takt_min=2.0, t0="2026-11-01 06:00", hint_boost=50.0)
    df, dfi, G2 = build(cfg2)
    _, _, G1 = build()
    assert P.t_min(cfg2, 11) == 20.0
    assert P.iso(cfg2, 0) == "2026-11-01 06:00"
    row = dfi.loc[2076]
    s2 = {c["cause"]: c["score"] for c in P.rank_causes(G2, row, hints={"RNF"})}
    s1 = {c["cause"]: c["score"] for c in P.rank_causes(G1, row, hints={"RNF"})}
    assert s2["RNF"] > s1["RNF"]
    assert P.udi_from_time(G2, P.iso(cfg2, P.t_min(cfg2, 777))) == 777         # quy đổi hai chiều nhất quán
    rep = P.analyze_incident(G2, dfi, 2076)
    assert rep["trigger"]["time"] == P.iso(cfg2, P.t_min(cfg2, 2076))


# ------------------------------------------------------------------ bản ghi theo mục 5.3
def doc_ts(G, udi):
    cfg = G.graph["cfg"]
    return (pd.Timestamp(cfg["t0"]) + pd.Timedelta(minutes=P.t_min(cfg, udi))).strftime("%d/%m/%Y %H:%M")


def test_time_conversion(world):
    G = world[2]
    assert P.udi_from_time(G, doc_ts(G, 2076)) == 2076
    assert P.udi_from_time(G, P.iso(G.graph["cfg"], P.t_min(G.graph["cfg"], 2076))) == 2076
    with pytest.raises(ValueError, match="ngoài dòng thời gian"):
        P.udi_from_time(G, "15/09/2026 10:32")                 # ví dụ trong tài liệu D3, trước mốc dữ liệu
    with pytest.raises(ValueError, match="Không đọc được"):
        P.udi_from_time(G, "hôm qua lúc 3 giờ")


def test_doc_format_record_runs_and_matches_full_record(world):
    _, dfi, G = world
    doc = dict(incident_id="X1", time=doc_ts(G, 2076), machine_id="M05", anomaly_type="Mô-men xoắn bất thường",
               level="Cao", anomaly_score=0.93)
    r = P.analyze_record(G, doc, dfi=dfi)
    assert r["trigger"]["udi"] == 2076 and r["effect"]["severity"] == 0.9 and r["effect"]["severity_source"] == "P1"
    assert r["causes"] == P.analyze_incident(G, dfi, 2076)["causes"]
    with pytest.raises(ValueError):
        P.analyze_record(G, doc)                              # không có dfi và không có sensors


def test_level_mapping_and_numeric_precedence(world):
    _, dfi, G = world
    base = dict(incident_id="X", time=doc_ts(G, 2076), machine_id="M05")
    sev = [P.analyze_record(G, {**base, "level": lv}, dfi=dfi)["effect"]["severity"]
           for lv in ("Cao", "Trung bình", "Thấp")]
    assert sev == [0.9, 0.6, 0.3]
    assert P.analyze_record(G, {**base, "level": "Cao", "severity": 0.77}, dfi=dfi)["effect"]["severity"] == 0.77
    with pytest.raises(ValueError, match="level"):
        P.analyze_record(G, {**base, "level": "Khẩn cấp"}, dfi=dfi)


def test_hints(world):
    _, dfi, G = world
    base = dict(incident_id="X", time=doc_ts(G, 2076), machine_id="M05")
    plain = P.analyze_record(G, base, dfi=dfi)
    h = P.analyze_record(G, {**base, "suspected_cause_group": "Lỗi ngẫu nhiên"}, dfi=dfi)
    score = lambda rep, c: next(x["score"] for x in rep["causes"] if x["cause"] == c)
    assert score(h, "RNF") > score(plain, "RNF")
    assert h["causes"][0]["cause"] == plain["causes"][0]["cause"]            # gợi ý yếu không đảo bằng chứng mạnh
    assert sum(c["score"] for c in h["causes"]) == pytest.approx(1.0, abs=0.01)
    d = P.analyze_record(G, {**base, "suspected_cause_group": ["TWF", "Ổ bi / lệch trục"]}, dfi=dfi)["trigger"]["details"]
    assert d["hints_applied"] == ["TWF"] and d["hints_ignored"] == ["Ổ bi / lệch trục"]


def test_udi_time_conflict(world):
    _, dfi, G = world
    base = dict(incident_id="X", machine_id="M05")
    with pytest.raises(ValueError, match="mâu thuẫn"):
        P.analyze_record(G, {**base, "udi": 100, "time": doc_ts(G, 2000)}, dfi=dfi)
    ok = P.analyze_record(G, {**base, "udi": 2000, "time": doc_ts(G, 2000)}, dfi=dfi)
    assert ok["trigger"]["udi"] == 2000
    P.analyze_record(G, {**base, "udi": 2000, "time": doc_ts(G, 2001)}, dfi=dfi)   # lệch 1 chu kỳ: chấp nhận


def test_record_validation_errors(world):
    _, dfi, G = world
    good = P.record_from_row(dfi.loc[3351])
    bad = [({**good, "udi": True}, "udi"), ({k: v for k, v in good.items() if k != "sensors"}, "sensors"),
           ({**good, "type": "X"}, "type"), ({**good, "severity": 2}, "severity"),
           ({**good, "machine_id": "M03"}, "downtime"), ({**good, "machine_id": "ZZ"}, "machine_id"),
           ("không phải dict", "JSON object")]
    for rec, key in bad:
        with pytest.raises(ValueError, match=key):
            P.analyze_record(G, rec)
    r = P.analyze_record(G, {"incident_id": "M", "udi": 500, "machine_id": "M03", "downtime_min": 30, "severity": 0.6})
    assert r["causes"] == [] and r["effect"]["severity_source"] == "P1"


def test_no_label_leakage(world):
    _, dfi, G = world
    rec = P.record_from_row(dfi.loc[3351])
    assert not any(m in rec for m in P.MODES)
    rep = P.clean(P.analyze_record(G, rec))
    assert "label_modes" not in json.dumps(rep)
    inc = P.clean(P.analyze_incident(G, dfi, 3351))
    assert "label_modes" in inc["eval_only"] and "label_modes" not in json.dumps({k: v for k, v in inc.items() if k != "eval_only"})


def test_load_data_validation_survives_python_O(tmp_path, world):
    df = world[0].copy()
    df.loc[1, "UDI"] = df.loc[0, "UDI"]
    bad = tmp_path / "bad.csv"
    df.to_csv(bad, index=False)
    r = subprocess.run([sys.executable, "-O", "-c",
                        f"import sys;sys.path.insert(0,r'{HERE}');import p2_impact_trace as P;P.load_data(r'{bad}')"],
                       capture_output=True, text=True)
    assert "ValueError" in r.stderr


# ------------------------------------------------------------------ xử lý lô (finding 12)
def test_batch_isolates_bad_records(world, tmp_path):
    _, dfi, G = world
    good = [P.record_from_row(dfi.loc[2076]), P.record_from_row(dfi.loc[3351])]
    good[0]["incident_id"], good[1]["incident_id"] = "A", "C"
    f = tmp_path / "mixed.json"
    f.write_text(json.dumps([good[0], {"incident_id": "B", "machine_id": "M05"}, good[1]]), encoding="utf-8")
    res = P.process_incident_file(G, dfi, str(f), tmp_path)
    assert (res["n_total"], res["n_ok"]) == (3, 2) and len(res["errors"]) == 1
    assert res["errors"][0]["incident_id"] == "B" and "udi" in res["errors"][0]["error"]
    assert (tmp_path / "p2_report_A.json").exists() and (tmp_path / "p2_report_C.json").exists()
    assert json.loads((tmp_path / "p2_errors.json").read_text(encoding="utf-8"))[0]["index"] == 1


def test_batch_rejects_non_list_and_bad_json(world, tmp_path):
    _, dfi, G = world
    f = tmp_path / "d.json"
    f.write_text(json.dumps({"incident_id": "A"}), encoding="utf-8")
    res = P.process_incident_file(G, dfi, str(f), tmp_path)
    assert res["n_ok"] == 0 and "DANH SÁCH" in res["errors"][0]["error"]
    f.write_text("{không phải json", encoding="utf-8")
    assert P.process_incident_file(G, dfi, str(f), tmp_path)["errors"][0]["error_type"] == "JSONDecodeError"
    res = P.process_incident_file(G, dfi, str(tmp_path / "khong_co.json"), tmp_path)
    assert res["errors"][0]["error_type"] == "FileNotFoundError"


def test_batch_filenames_are_safe(world, tmp_path):
    _, dfi, G = world
    out = tmp_path / "out"
    out.mkdir()
    r1, r2, r3 = (P.record_from_row(dfi.loc[2076]) for _ in range(3))
    r1["incident_id"], r2["incident_id"], r3["incident_id"] = "../../evil", "dup", "dup"
    f = tmp_path / "x.json"
    f.write_text(json.dumps([r1, r2, r3]), encoding="utf-8")
    res = P.process_incident_file(G, dfi, str(f), out)
    assert res["n_ok"] == 3
    names = sorted(p.name for p in out.glob("p2_report_*.json"))
    assert names == ["p2_report_dup.json", "p2_report_dup_2.json", "p2_report_evil.json"]
    assert not (tmp_path / "evil.json").exists() and not list(tmp_path.glob("p2_report_*"))


def test_cli_batch_exit_code_and_other_outputs(world, tmp_path):
    _, dfi, _ = world
    f = tmp_path / "mixed.json"
    ok = P.record_from_row(dfi.loc[2076])
    f.write_text(json.dumps([ok, {"incident_id": "BAD", "machine_id": "M05"}]), encoding="utf-8")
    r = run_cli("--out", str(tmp_path / "o"), "--fast", "--incidents", str(f))
    assert r.returncode == 2
    assert (tmp_path / "o" / "p2_metrics.json").exists() and (tmp_path / "o" / "p2_errors.json").exists()
    assert (tmp_path / "o" / "p2_report_INC_02076.json").exists()


def test_cli_accepts_example_file_from_P1(tmp_path):
    ex = tmp_path / "ex.json"
    first = run_cli("--out", str(tmp_path / "a"), "--fast")
    assert first.returncode == 0
    ex.write_text((tmp_path / "a" / "p2_example_incidents_from_P1.json").read_text(encoding="utf-8"), encoding="utf-8")
    r = run_cli("--out", str(tmp_path / "b"), "--fast", "--incidents", str(ex))
    assert r.returncode == 0 and "4/4" in r.stdout


# ------------------------------------------------------------------ báo cáo & schema
def test_reports_valid_and_consistent(out_dir):
    reps = [load(out_dir, f"p2_scenario_{n}.json") for n in SCEN]
    for r in reps:
        assert S.validate(r, S.IMPACT_REPORT_SCHEMA)
        assert all(a["owner_dept"] for a in r["affected"])
        for dep, g in r["by_department"].items():
            assert g["count"] == len(g["items"])
    keys = {tuple(sorted(set(r) - {"eval_only"})) for r in reps}
    assert len(keys) == 1
    assert reps[0]["selection"].startswith("worst_case_of_") and reps[1]["selection"].startswith("median_of_")


def test_by_department_includes_source(out_dir):
    s1 = load(out_dir, "p2_scenario_S1_machine_incident_worst.json")
    assert s1["trigger"]["owner_dept"] == "Bảo trì"
    g = s1["by_department"]["Bảo trì"]
    assert g["roles"] == ["source"] and g["items"][0]["id"] == "M05" and g["items"][0]["risk"] == s1["effect"]["severity"]
    s2 = load(out_dir, "p2_scenario_S2_order_backward.json")                   # nguồn cũng là đối tượng bị ảnh hưởng
    roles = {it["role"] for g in s2["by_department"].values() for it in g["items"]}
    assert roles == {"source+affected"}
    assert sum(g["count"] for g in s2["by_department"].values()) == 1          # không đếm trùng


def test_data_for_p3(out_dir):
    s1 = load(out_dir, "p2_scenario_S1_machine_incident_worst.json")
    assert all("cum_buffer_min" in a for a in s1["affected"])
    assert s1["buffers"] and {b["kind"] for b in s1["buffers"]} <= {"raw_material", "wip", "finished_goods"}
    assert all(b["buffer_min"] > 0 for b in s1["buffers"])
    h = s1["trigger"]["details"]["history"]
    assert 0 < h["machine_failures_per_1000_units"] < 100 and 0 < h["top_cause_historical_share"] <= 1
    s3 = load(out_dir, "p2_scenario_S3_material_delay.json")
    assert s3["affected"] and any(b["kind"] == "raw_material" for b in s3["buffers"])


def test_schema_catches_broken_reports(out_dir):
    r = load(out_dir, "p2_scenario_S1_machine_incident_worst.json")
    for mutate in (lambda x: x.pop("affected"), lambda x: x.pop("buffers"),
                   lambda x: x["affected"][0].__setitem__("risk", 1.7)):
        broken = copy.deepcopy(r)
        mutate(broken)
        with pytest.raises(S.ValidationError):
            S.validate(broken, S.IMPACT_REPORT_SCHEMA)


def test_example_incidents_match_schema_and_doc_format(out_dir):
    ex = load(out_dir, "p2_example_incidents_from_P1.json")
    assert all(S.validate(e, S.INCIDENT_RECORD_SCHEMA) for e in ex)
    assert "sensors" not in ex[0] and "udi" not in ex[0] and "time" in ex[0]


def test_graph_views(out_dir):
    gv = load(out_dir, "p2_graph_view_S1_machine_incident_worst.json")
    assert S.validate(gv, S.GRAPH_VIEW_SCHEMA)
    ids = {n["id"] for n in gv["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in gv["edges"])
    assert [n["id"] for n in gv["nodes"] if n["is_source"]] == ["M05"]
    assert not any(n["type"] in ("lot", "department") for n in gv["nodes"])
    s1 = load(out_dir, "p2_scenario_S1_machine_incident_worst.json")
    assert {n["id"] for n in gv["nodes"] if n["type"] == "order"} == {a["id"] for a in s1["affected"] if a["type"] == "order"}
    assert all((n["band"] is None) == (n["risk"] is None) for n in gv["nodes"])
    assert any(e["on_path"] for e in gv["edges"])
    st = load(out_dir, "p2_graph_view_static.json")
    assert all(n["risk"] is None for n in st["nodes"])
    s2g = load(out_dir, "p2_graph_view_S2_order_backward.json")
    assert any(n["is_source"] and n["type"] == "order" for n in s2g["nodes"])


def test_deterministic_outputs(out_dir, tmp_path):
    r = run_cli("--out", str(tmp_path), "--fast")
    assert r.returncode == 0
    for n in SCEN:
        assert (out_dir / f"p2_scenario_{n}.json").read_bytes() == (tmp_path / f"p2_scenario_{n}.json").read_bytes()


# ------------------------------------------------------------------ số liệu đánh giá
def test_metrics_file_content(out_dir):
    m = load(out_dir, "p2_metrics.json")
    assert "KIỂM TRA ĐƯỜNG ỐNG" in m["notes"]["backward"]
    allf = [r for r in m["backward"] if r["subset"] == "all_failures" and r["method"] == "prior+evidence"
            and r["noise_sd_frac"] == 0.0][0]
    assert 0.99 <= allf["top1"] <= 1.0 and allf["n"] == 330
    assert allf["n_by_mode"]["RNF"] <= 1 and set(allf["confusion"]) == set(P.MODES)
    assert allf["macro_f1_all"] is not None
    base = [r for r in m["backward"] if r["subset"] == "all_failures" and r["method"] == "prior_only"][0]
    assert base["top1"] < 0.5
    noisy = sorted((r["noise_sd_frac"], r["top1"]) for r in m["backward"]
                   if r["subset"] == "all_failures" and r["method"] == "prior+evidence")
    assert all(a[1] >= b[1] - 0.01 for a, b in zip(noisy, noisy[1:]))             # nhiễu tăng thì Top-1 không tăng
    f = m["forward"]
    assert f["wiring_check_precision"] == 1.0 and f["wiring_check_recall"] == 1.0 and "consistency_precision" not in f
    assert m["ml_baseline"] == {"skipped": "--fast"}


def test_hint_sensitivity(world):
    _, dfi, G = world
    rows = {r["hint_boost"]: r for r in P.evaluate_hint_sensitivity(G, dfi, boosts=(1.0, 2.0, 5.0))}
    assert rows[1.0]["top1_wrong_hint"] == rows[1.0]["top1_none_hint"]              # hệ số 1 = không có tác dụng
    assert rows[2.0]["top1_correct_hint"] >= rows[2.0]["top1_none_hint"]
    assert rows[5.0]["top1_wrong_hint"] <= rows[2.0]["top1_wrong_hint"] <= rows[1.0]["top1_wrong_hint"]


def test_ml_baseline_is_fair_and_leak_free(world):
    pytest.importorskip("sklearn")
    _, dfi, G = world
    mlb = P.evaluate_ml_baseline(G, dfi)
    d = mlb["drift_without_hdf"]
    assert d["train_hdf"] == 0 and d["test_hdf"] > 100                              # huấn luyện không thấy HDF
    assert mlb["cv5"]["rule_prior_plus_evidence"] >= 0.99
    assert d["prior_only"] < d["rule_prior_plus_evidence"]
    sweep = d["rule_prior_smoothing_sweep"]
    assert sweep[0]["prior_smoothing"] == 0.0 and sweep[0]["drift_top1"] == d["rule_prior_plus_evidence"]
    assert sweep[-1]["drift_top1"] > sweep[0]["drift_top1"]                         # làm trơn giúp khi gặp nguyên nhân lạ
    assert sweep[-1]["in_distribution_top1"] < sweep[0]["in_distribution_top1"]     # nhưng có cái giá


def test_forward_sensitivity_directions(world):
    df, dfi, _ = world
    res = P.forward_sensitivity(df, dfi, P.CFG, {"slack_mean_min": [60, 360, 1440], "recovery_tau_h": [6, 24, 96],
                                                 "substitute_share": [0.0, 0.3, 0.5]})
    pct = lambda k: [r["pct_incidents_with_missed_deadline"] for r in res[k]]
    assert pct("slack_mean_min") == sorted(pct("slack_mean_min"), reverse=True)     # nhiều thời gian dư -> ít trễ hạn
    assert pct("recovery_tau_h") == sorted(pct("recovery_tau_h"))                   # bù chậm hơn -> nhiều trễ hạn hơn
    assert pct("substitute_share") == sorted(pct("substitute_share"), reverse=True)


def test_leave_one_out_priors(world):
    _, dfi, G = world
    row = dfi[dfi["HDF"] == 1].iloc[0]
    loo = P.loo_priors(G, row)
    full = {d["code"]: d["prior"] for _, d in G.nodes(data=True) if d["type"] == "failure_mode"}
    assert sum(loo.values()) == pytest.approx(1.0) and loo["HDF"] < full["HDF"]


def test_runtime_per_incident_is_small(world):
    import time
    _, dfi, G = world
    t = time.perf_counter()
    for udi in dfi.index[dfi["Machine failure"] == 1][:50]:
        P.analyze_incident(G, dfi, int(udi))
    assert (time.perf_counter() - t) / 50 < 0.05
