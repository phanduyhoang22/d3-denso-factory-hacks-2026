"""Runner thí nghiệm E1–E4, E6 (P5.3) trên dữ liệu nhà máy của nhóm (data/factory/).

Mỗi sự cố thật (443: AI4I 339, SECOM 104) là một kịch bản; chạy với từng tỷ lệ xóa cạnh.
Nhiễu = sự cố thật khác trong cửa sổ --window-hours trước sự cố gốc (không tự tiêm).
Ghi results.csv dạng dài (một dòng = một chỉ số). E4 = các dòng có edge_drop_rate > 0 của E1–E3.
E0 (phát hiện) do P1/P2 chạy riêng rồi ghi vào cùng results.csv.

Ví dụ:
  python scripts/run_experiments.py --dataset ai4i                 # mọi sự cố AI4I × 4 mức xóa cạnh
  python scripts/run_experiments.py --dataset secom --limit 10     # chạy thử 10 sự cố đầu
"""
import argparse
import csv
import datetime as dt
import itertools
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from d3 import RESULTS_DIR, metrics  # noqa: E402
from d3.pipeline import run_scenario  # noqa: E402
from d3.factory import incidents_for  # noqa: E402
from d3.registry import resolve_all  # noqa: E402

FIELDS = ["run_id", "time", "git", "impl", "experiment", "dataset", "incident_id", "seed",
          "window_hours", "confounders", "edge_drop_rate", "method", "metric", "value"]


def git_rev():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL,
                                       cwd=Path(__file__).parent).decode().strip()
    except Exception:
        return "nogit"


def score_one(output, truth, ctx, fns):
    """Trả về list (experiment, method, metric, value)."""
    G_obs, inc = ctx["graph_observed"], ctx["incident"]
    node_type = {n: d["type"] for n, d in ctx["graph_full"].nodes(data=True)}
    rows = []

    # E1 – truy vết xuôi
    for method, pred in [("system", {f["node_id"] for f in output["forward"]}),
                         ("baseline_local", fns["baseline_e1"](G_obs, inc))]:
        p, r = metrics.set_precision_recall(pred, truth["forward_truth"])
        rows += [("E1", method, "precision", p), ("E1", method, "recall", r)]
        for layer, v in metrics.recall_by_layer(pred, truth["forward_truth"], node_type).items():
            rows.append(("E1", method, f"recall_{layer}", v))

    # E2 – điểm rủi ro so với mức ảnh hưởng thật
    for method, ranked in [("system", output["risk"]),
                           ("baseline_distance", fns["baseline_e2"](G_obs, output["forward"], inc))]:
        rows.append(("E2", method, "spearman", metrics.spearman_vs_truth(ranked, truth["true_impact"])))
        rows.append(("E2", method, "top3_precision",
                     metrics.topk_precision([r["node_id"] for r in ranked], truth["true_impact"], 3)))

    # E3 – truy vết ngược
    for method, ranked in [("system", [b["node_id"] for b in output["backward"]]),
                           ("baseline_max_score", fns["baseline_e3"](ctx["incidents"], k=3))]:
        rows.append(("E3", method, "top1_acc", metrics.topk_accuracy(ranked, truth["backward_truth"], 1)))
        rows.append(("E3", method, "top3_acc", metrics.topk_accuracy(ranked, truth["backward_truth"], 3)))

    rows.append(("E3", "system", "n_concurrent_incidents", len(ctx["incidents"]) - 1))

    # E6 – thời gian pipeline (không tính bước sinh kịch bản)
    rows.append(("E6", "system", "pipeline_ms",
                 sum(v for k, v in output["timing_ms"].items() if k != "generate")))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ai4i", choices=["ai4i", "secom"])
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N sự cố đầu (mặc định: tất cả)")
    ap.add_argument("--edge-drops", nargs="+", type=float, default=[0.0, 0.1, 0.25, 0.5])
    ap.add_argument("--window-hours", type=float, default=2.0,
                    help="sự cố khác trong cửa sổ này trước sự cố gốc = nhiễu thật")
    ap.add_argument("--confounders", default="labels", choices=["labels", "alarms"],
                    help="labels: nhiễu = sự cố thật khác; alarms (AI4I): thêm báo sai của detector P1")
    ap.add_argument("--out", default=str(RESULTS_DIR / "results.csv"))
    ap.add_argument("--mock", action="store_true", help="ép dùng mock cho mọi module")
    ap.add_argument("--no-schema-check", action="store_true")
    args = ap.parse_args()
    pool = incidents_for(args.dataset)[:args.limit]

    fns, impl = resolve_all(force_mock=args.mock)
    impl_tag = ";".join(f"{k}={v}" for k, v in impl.items())
    print("Module đang dùng:", ", ".join(f"{k}={v}" for k, v in impl.items()))
    if "mock" in impl.values():
        print("ℹ Dùng bản trong mock.py cho:", ", ".join(k for k, v in impl.items() if v == "mock"),
              "(generate_scenario/forward_trace = đọc và duyệt đồ thị nhà máy, xem README).")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists()
    run_id, now, rev = uuid.uuid4().hex[:8], dt.datetime.now().isoformat(timespec="seconds"), git_rev()

    grid = list(itertools.product(range(len(pool)), args.edge_drops))
    n_rows, failures = 0, []
    with out.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        for seed, drop in grid:
            config = {"dataset": args.dataset, "incident_id": pool[seed]["incident_id"],
                      "edge_drop_rate": drop, "window_hours": args.window_hours,
                      "confounders": args.confounders}
            try:
                output, truth, ctx = run_scenario(seed, config, fns, check_schema=not args.no_schema_check)
            except Exception as e:  # ghi lại và chạy tiếp, cuối cùng báo tổng
                failures.append((config, seed, repr(e)))
                continue
            for exp, method, metric, value in score_one(output, truth, ctx, fns):
                w.writerow({"run_id": run_id, "time": now, "git": rev, "impl": impl_tag, "experiment": exp,
                            "dataset": args.dataset, "incident_id": config["incident_id"], "seed": seed,
                            "window_hours": args.window_hours, "confounders": args.confounders,
                            "edge_drop_rate": drop, "method": method, "metric": metric,
                            "value": round(float(value), 6)})
                n_rows += 1

    print(f"Đã chạy {len(grid) - len(failures)}/{len(grid)} kịch bản, ghi {n_rows} dòng vào {out} (run_id={run_id})")
    for config, seed, err in failures[:10]:
        print(f"  LỖI seed={seed} {config}: {err}")
    summarize(out, run_id)
    return 1 if failures else 0


def summarize(path, run_id):
    df = pd.read_csv(path)
    df = df[(df.run_id == run_id) & df.metric.isin(["recall", "spearman", "top1_acc", "pipeline_ms"])]
    if df.empty:
        return
    tab = (df.groupby(["experiment", "metric", "method", "edge_drop_rate"]).value
             .agg(lambda s: f"{s.mean():.3f} ± {s.std():.3f}").unstack("edge_drop_rate"))
    print("\nTóm tắt (mean ± std theo tỷ lệ xóa cạnh):")
    print(tab.to_string())


if __name__ == "__main__":
    sys.exit(main())
