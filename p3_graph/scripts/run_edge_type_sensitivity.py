"""Phụ lục E4: thiếu 25% cạnh của TỪNG loại quan hệ thì truy vết xuôi giảm bao nhiêu?
Giúp ưu tiên loại dữ liệu cần ghi nhận khi triển khai trên dữ liệu thật."""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from d3p3.data import load_domain
from d3p3.forward import forward_trace
from d3p3.metrics import e1_metrics
from d3p3.ontology import PROPAGATION_EDGES
from d3p3.scenario import generate_scenario

data = {d: load_domain(d) for d in ("ai4i", "secom")}
rows = []
for domain in ("ai4i", "secom"):
    for t in [None] + PROPAGATION_EDGES:
        for seed in range(30):
            cfg = {"domain": domain, "size": "medium", "edge_drop": 0.25 if t else 0.0,
                   "drop_types": [t] if t else None}
            sc = generate_scenario(seed, cfg, data)
            bt = sc["backward_truth"]
            tr = forward_trace(sc["graph_observed"], bt["root_node"], bt["severity_score"])
            for layer, metric, v in e1_metrics(tr, sc["forward_truth"]):
                rows.append(dict(domain=domain, dropped_type=t or "none (đầy đủ)", seed=seed,
                                 layer=layer, metric=metric, value=v))
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "edge_type_sensitivity.csv")
pd.DataFrame(rows).to_csv(out, index=False)
print("→", out)
