"""Sinh file mẫu đúng schema cho Part 0 + file demo cho dashboard (P3.8)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from d3p3.export import graph_to_json, save_json  # noqa: E402
from d3p3.forward import format_trace, forward_trace  # noqa: E402
from d3p3.graph import demo_graph, generate_graph, graph_summary  # noqa: E402
from d3p3.scenario import generate_scenario, scenario_to_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "schemas", "samples")
os.makedirs(S, exist_ok=True)

# 1) Demo mục 10 – cho dashboard P5
G = demo_graph()
tr = forward_trace(G, "M05", severity=0.93)
save_json(graph_to_json(G, tr), os.path.join(S, "demo_M05_graph_with_impact.json"))
save_json(tr, os.path.join(S, "demo_M05_forward_trace.json"))
print(format_trace(tr))

# 2) 3 kịch bản mẫu (2 AI4I, 1 SECOM) – không kèm đồ thị để gọn
for seed, cfg in [(1, dict(domain="ai4i", size="small", confounder_ratio=0.5, edge_drop=0.1)),
                  (2, dict(domain="ai4i", size="medium", confounder_ratio=0.25, edge_drop=0.25)),
                  (3, dict(domain="secom", size="medium", confounder_ratio=0.5, edge_drop=0.0))]:
    sc = generate_scenario(seed, cfg)
    j = scenario_to_json(sc)
    j["true_impact"] = dict(sorted(j["true_impact"].items(), key=lambda kv: -kv[1])[:15])
    j["meta"]["dropped_edges"] = j["meta"]["dropped_edges"][:5] + (["…"] if len(j["meta"]["dropped_edges"]) > 5 else [])
    j["meta"]["graph_summary_full"] = graph_summary(sc["graph_full"])
    bt = sc["backward_truth"]
    trs = forward_trace(sc["graph_observed"], bt["root_node"], bt["severity_score"])
    trs["affected"] = trs["affected"][:8]
    j["forward_trace_example"] = trs
    save_json(j, os.path.join(S, f"scenario_{cfg['domain']}_seed{seed}.json"))

# 3) bản ghi sự cố mẫu (>=3) và đồ thị mẫu đầy đủ (small)
incs = []
for seed in (1, 3):
    incs += generate_scenario(seed, dict(domain="ai4i" if seed == 1 else "secom", confounder_ratio=0.5))["incidents"]
save_json(incs[:6], os.path.join(S, "incidents_sample.json"))
save_json(graph_to_json(generate_graph(1, "small"), include_sensors=True), os.path.join(S, "graph_small_seed1.json"))
print("ok →", S)
