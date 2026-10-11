"""P3.7 – Chạy E1 (truy vết xuôi) và E4 (lặp E1–E3 khi xóa 0/10/25/50% cạnh), cả 2 domain.

Ghi results/results_p3.csv dạng dài (mỗi dòng 1 chỉ số) để P4/P5 gộp vào results.csv chung.
E2/E3 ở đây dùng bản tham chiếu (d3p3/reference.py) – sẽ chạy lại khi có hàm của P4/P1.

python scripts/run_experiments_p3.py --seeds 30
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import networkx as nx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from d3p3 import sim_params as SP  # noqa: E402
from d3p3.data import load_domain  # noqa: E402
from d3p3.forward import baseline_e1, forward_trace  # noqa: E402
from d3p3.metrics import e1_metrics, e2_metrics, e3_metrics  # noqa: E402
from d3p3.ontology import IMPACT_LAYERS  # noqa: E402
from d3p3.propagation import propagation_view  # noqa: E402
from d3p3.reference import (backward_trace_ref, baseline_e2, baseline_e3_anomaly,  # noqa: E402
                            baseline_e3_recent, risk_score_ref)
from d3p3.scenario import generate_scenario  # noqa: E402


def run(seeds, domains, sizes, confs, drops, out_csv):
    data = {d: load_domain(d) for d in ("ai4i", "secom")}
    rows = []
    t0 = time.time()
    n_sc = 0
    for domain in domains:
        for size in sizes:
            for seed in seeds:
                for drop in drops:
                    for conf in confs:
                        sc = generate_scenario(seed, {"domain": domain, "size": size,
                                                      "confounder_ratio": conf, "edge_drop": drop}, data)
                        n_sc += 1
                        bt = sc["backward_truth"]
                        root, Go, Gf = bt["root_node"], sc["graph_observed"], sc["graph_full"]
                        base = dict(domain=domain, size=size, seed=seed, confounder_ratio=conf, edge_drop=drop,
                                    root_node=root, root_mode=bt["failure_mode"], scenario_id=sc["scenario_id"],
                                    n_confounders=len(sc["confounder_nodes"]))

                        def add(exp, method, mets):
                            for layer, metric, val in mets:
                                rows.append({**base, "experiment": exp, "method": method,
                                             "layer": layer, "metric": metric, "value": val})

                        if conf == confs[0]:  # E1/E2 không phụ thuộc confounder → tính 1 lần
                            t_s = time.perf_counter()
                            tr = forward_trace(Go, root, bt["severity_score"])
                            dt_ms = (time.perf_counter() - t_s) * 1000
                            add("E1", "forward_trace", e1_metrics(tr, sc["forward_truth"]) + [("all", "runtime_ms", dt_ms)])
                            add("E1", "baseline_local", e1_metrics(baseline_e1(Go, root), sc["forward_truth"]))
                            universe = sorted(n for n in nx.descendants(propagation_view(Gf), root)
                                              if Gf.nodes[n]["type"] in IMPACT_LAYERS)
                            add("E2", "risk_ref(est_impact)", e2_metrics(risk_score_ref(tr), sc["true_impact"], universe))
                            add("E2", "baseline_hops", e2_metrics(baseline_e2(Go, root), sc["true_impact"], universe))
                        rk = [r["node_id"] for r in backward_trace_ref(Go, sc["incidents"], sc["bad_outcome"])]
                        add("E3", "backward_ref(graph+hist)", e3_metrics(rk, root))
                        add("E3", "baseline_max_anomaly", e3_metrics(baseline_e3_anomaly(sc["incidents"], sc["bad_outcome"]), root))
                        add("E3", "baseline_most_recent", e3_metrics(baseline_e3_recent(sc["incidents"], sc["bad_outcome"]), root))
            print(f"  {domain}/{size}: xong ({n_sc} kịch bản, {time.time()-t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    df["experiment_group"] = df["edge_drop"].map(lambda d: "E4" if d > 0 else "base")
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Đã ghi {len(df)} dòng, {n_sc} kịch bản → {out_csv} ({time.time()-t0:.0f}s)")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=30)
    ap.add_argument("--seed-start", type=int, default=0)
    ap.add_argument("--domains", nargs="+", default=["ai4i", "secom"])
    ap.add_argument("--sizes", nargs="+", default=["small", "medium", "large"])
    ap.add_argument("--confs", nargs="+", type=float, default=SP.CONFOUNDER_RATES)
    ap.add_argument("--drops", nargs="+", type=float, default=SP.EDGE_DROP_RATES)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                  "results", "results_p3.csv"))
    a = ap.parse_args()
    run(range(a.seed_start, a.seed_start + a.seeds), a.domains, a.sizes, a.confs, a.drops, a.out)
