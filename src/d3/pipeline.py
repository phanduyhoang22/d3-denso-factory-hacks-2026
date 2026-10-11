"""Nối các module: detect → forward → risk → backward → action (mục 16.1).

run_scenario() chạy MỘT kịch bản và trả về:
  output  — dict theo trace_output.schema.json (cho dashboard)
  truth   — ground truth của kịch bản (chỉ runner dùng để chấm)
  ctx     — graph_observed, incidents, ... (cho baseline)
"""
import random
import time

from .registry import resolve_all
from .schema_io import validate


def run_scenario(seed, config, fns=None, check_schema=True):
    if fns is None:
        fns, _ = resolve_all()
    t = {}

    t0 = time.perf_counter()
    sc = fns["generate_scenario"](seed, config)
    t["generate"] = time.perf_counter() - t0

    G = sc["graph_observed"]  # pipeline KHÔNG được nhìn graph_full
    incidents = [{k: v for k, v in i.items() if k != "is_confounder"} for i in sc["incidents"]]
    # Xáo thứ tự: bộ sinh luôn đặt sự cố gốc đầu danh sách → khi bằng điểm, thứ tự sẽ làm lộ đáp án
    random.Random(seed).shuffle(incidents)
    incident = next(i for i in incidents if i["incident_id"] == sc["root_incident"]["incident_id"])

    t0 = time.perf_counter()
    forward = fns["forward_trace"](G, incident)
    t["forward"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    risk = fns["risk_score"](G, forward, incident)
    t["risk"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    backward = fns["backward_trace"](G, incidents, sc["bad_outcome_node"], k=3)
    t["backward"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    actions = fns["recommend"](G, incident, risk, backward)
    t["action"] = time.perf_counter() - t0

    output = {
        "scenario_id": f"{incident['incident_id']}_d{config.get('edge_drop_rate', 0)}",
        "seed": seed,
        "dataset": incident["dataset"],
        "config": config,
        "incident": incident,
        "bad_outcome_node": sc["bad_outcome_node"],
        "forward": forward,
        "risk": risk,
        "backward": backward,
        "actions": actions,
        "timing_ms": {k: round(v * 1000, 3) for k, v in t.items()},
    }
    if check_schema:
        validate("trace_output", output)
    truth = {k: sc[k] for k in ("forward_truth", "backward_truth", "true_impact")}
    ctx = {"graph_full": sc["graph_full"], "graph_observed": G, "incidents": incidents, "incident": incident}
    return output, truth, ctx
