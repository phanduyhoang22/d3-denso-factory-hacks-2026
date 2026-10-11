# D3 – P3: Đồ thị tri thức, Bộ sinh kịch bản, Truy vết xuôi

Phần P3 của dự án D3 (Hệ thống phát hiện sự cố và truy vết tác động). Báo cáo đầy đủ: [`docs/P3_report.md`](docs/P3_report.md).

## Cấu trúc

```
d3p3/
  ontology.py      loại node/cạnh, nhánh A (AI4I) / B (SECOM)
  sim_params.py    MỌI tham số mô phỏng (xem docs/sim_params.md)
  data.py          nạp + chia train/val/test + detector MOCK
  graph.py         generate_graph(seed, size), demo_graph()
  assign.py        assign_data()
  propagation.py   lan truyền noisy-OR dùng chung
  truth.py         true_impact() (tham chiếu cho P2)
  scenario.py      generate_scenario(), inject_confounders(), observe_graph()
  forward.py       forward_trace(), baseline_e1()
  reference.py     bản tham chiếu E2/E3 (thay bằng hàm của P4/P1)
  metrics.py       chỉ số E1/E2/E3
  export.py        graph_to_json() cho dashboard
scripts/           run_experiments_p3.py, run_edge_type_sensitivity.py, summarize_p3.py, make_samples.py
schemas/           graph / incident / forward_trace / scenario .schema.json + samples/
tests/test_p3.py   17 test (quy tắc chống sai số 18.2, ví dụ M05, …)
results/           results_p3.csv, edge_type_sensitivity.csv, summary_p3.md, figures/
docs/              ontology.md, sim_params.md, P3_report.md
```

## Dùng nhanh

```python
from d3p3.scenario import generate_scenario
from d3p3.forward import forward_trace, format_trace

sc = generate_scenario(seed=7, config={"domain": "ai4i", "size": "medium",
                                       "confounder_ratio": 0.25, "edge_drop": 0.25})
bt = sc["backward_truth"]
tr = forward_trace(sc["graph_observed"], bt["root_node"], bt["severity_score"])
print(format_trace(tr))
```

## Dữ liệu

Đặt file vào `data/raw/`:
- `ai4i2020.csv` – AI4I 2020 Predictive Maintenance (UCI 601 / Kaggle stephanmatzka), CC BY 4.0
- `uci-secom.csv` – SECOM (UCI 179), dạng CSV gộp có cột `Time`, `Pass/Fail`

Đường dẫn khác: `load_ai4i(path)` / `load_secom(path)`.
