"""Tổng hợp results_p3.csv → bảng markdown (mean ± std qua 30 seed) + hình cho báo cáo/slide."""
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
FIG = os.path.join(RES, "figures")
os.makedirs(FIG, exist_ok=True)
d = pd.read_csv(os.path.join(RES, "results_p3.csv"))
sens = pd.read_csv(os.path.join(RES, "edge_type_sensitivity.csv"))

DOM = {"ai4i": "AI4I (nhánh A – Máy)", "secom": "SECOM (nhánh B – Công đoạn)"}
LAYER_VN = {"process": "Công đoạn", "component": "Linh kiện", "product": "Sản phẩm", "order": "Đơn hàng", "all": "Gộp"}
DROPS = [0.0, 0.1, 0.25, 0.5]


def ms(x):
    x = x.dropna()
    return "—" if len(x) == 0 else f"{x.mean():.2f} ± {x.std():.2f}"


def table(df, index, cols="edge_drop", fmt=ms):
    t = df.groupby(index + [cols]).value.agg(fmt).unstack(cols)
    if cols == "edge_drop":
        t.columns = [f"thiếu {int(c*100)}%" if c else "đầy đủ" for c in t.columns]
    return t


out = []
w = out.append
w("# Kết quả P3 – E1 (truy vết xuôi) và E4 (đồ thị thiếu cạnh)\n")
w(f"Số kịch bản: {d.scenario_id.nunique()} · seed: {d.seed.nunique()} · domain: {', '.join(d.domain.unique())} · "
  f"quy mô: {', '.join(d['size'].unique())}. Giá trị = trung bình ± độ lệch chuẩn qua seed (và qua 3 quy mô nếu không ghi rõ).\n")

# ---------------- E1 ở đồ thị đầy đủ, theo tầng
w("## E1 – Truy vết xuôi vs. cảnh báo cục bộ (đồ thị đầy đủ)\n")
e1 = d[(d.experiment == "E1") & (d.edge_drop == 0)]
for dom in ("ai4i", "secom"):
    x = e1[(e1.domain == dom) & e1.metric.isin(["precision", "recall", "f1"])]
    t = x.groupby(["layer", "method", "metric"]).value.agg(ms).unstack("metric")[["precision", "recall", "f1"]]
    t = t.reindex([(l, m) for l in ["process", "component", "product", "order", "all"]
                   for m in ["forward_trace", "baseline_local"] if (l, m) in t.index])
    t.index = [f"{LAYER_VN[l]} · {'truy vết xuôi' if m == 'forward_trace' else 'baseline cục bộ'}" for l, m in t.index]
    w(f"### {DOM[dom]}\n")
    w(t.to_markdown() + "\n")
x = e1[(e1.method == "forward_trace") & e1.metric.isin(["precision@5", "recall@10", "r_precision", "runtime_ms"])]
t = x.groupby(["domain", "size", "metric"]).value.agg(ms).unstack("metric")
w("### Theo quy mô đồ thị (truy vết xuôi, đồ thị đầy đủ)\n")
w(t.to_markdown() + "\n")
x = e1[(e1.method == "forward_trace") & (e1.domain == "ai4i") & (e1.layer == "all") & e1.metric.isin(["recall", "precision", "n_truth"])]
t = x.groupby(["root_mode", "metric"]).value.agg(ms).unstack("metric")
t["số kịch bản"] = x[x.metric == "recall"].groupby("root_mode").size()
w("### Theo chế độ lỗi AI4I của sự cố gốc (đồ thị đầy đủ)\n")
w("Chế độ lỗi chỉ đổi mức nghiêm trọng đầu vào (sim_params.SEVERITY_BY_MODE); RNF/TWF nhẹ hơn nên vùng ảnh hưởng nhỏ hơn.\n")
w(t.to_markdown() + "\n")

# ---------------- E4
w("## E4 – Đồ thị thiếu cạnh (xóa ngẫu nhiên 10/25/50% cạnh lan truyền)\n")
w("Tập cạnh bị xóa lồng nhau theo seed (10% ⊂ 25% ⊂ 50%) nên so sánh là theo cặp.\n")
for dom in ("ai4i", "secom"):
    w(f"### {DOM[dom]}\n")
    x = d[(d.domain == dom) & (d.experiment == "E1") & (d.layer == "all") & d.metric.isin(["recall", "precision", "f1"])]
    w("**E1 – gộp các tầng**\n")
    w(table(x, ["method", "metric"]).to_markdown() + "\n")
    x = d[(d.domain == dom) & (d.experiment == "E1") & (d.method == "forward_trace") & (d.layer != "all") & (d.metric == "recall")]
    w("**E1 – recall theo tầng (truy vết xuôi)**\n")
    t = table(x, ["layer"])
    t = t.reindex(["process", "component", "product", "order"])
    t.index = [LAYER_VN[i] for i in t.index]
    w(t.to_markdown() + "\n")
    x = d[(d.domain == dom) & (d.experiment == "E2")]
    w("**E2 – xếp hạng rủi ro (bản tham chiếu, chờ risk_score của P4)**\n")
    w(table(x, ["method", "metric"]).to_markdown() + "\n")
    x = d[(d.domain == dom) & (d.experiment == "E3") & (d.metric == "top1_acc")]
    w("**E3 – Top-1 truy vết ngược theo tỷ lệ confounder (bản tham chiếu, chờ backward_trace của P1)**\n")
    w(table(x, ["method", "confounder_ratio"], fmt=lambda v: f"{v.mean():.2f}").to_markdown() + "\n")

# ---------------- mức suy giảm tương đối
w("## Mức suy giảm so với đồ thị đầy đủ (truy vết xuôi, trung bình 2 domain × 3 quy mô)\n")
rows = []
for (exp, meth, layer, metric) in [("E1", "forward_trace", "all", "recall"), ("E1", "forward_trace", "order", "recall"),
                                   ("E1", "forward_trace", "all", "f1"), ("E2", "risk_ref(est_impact)", "all", "spearman")]:
    x = d[(d.experiment == exp) & (d.method == meth) & (d.layer == layer) & (d.metric == metric)]
    m = x.groupby("edge_drop").value.mean()
    rows.append({"chỉ số": f"{exp} {metric} ({LAYER_VN[layer]})", **{f"thiếu {int(k*100)}%" if k else "đầy đủ":
                 f"{m[k]:.2f} ({(m[k]/m[0]-1)*100:+.0f}%)" if k else f"{m[k]:.2f}" for k in DROPS}})
x = d[(d.experiment == "E3") & (d.method == "backward_ref(graph+hist)") & (d.metric == "top1_acc") & (d.confounder_ratio == 0.5)]
m = x.groupby("edge_drop").value.mean()
rows.append({"chỉ số": "E3 top-1 (confounder 50%)", **{f"thiếu {int(k*100)}%" if k else "đầy đủ":
             f"{m[k]:.2f} ({(m[k]/m[0]-1)*100:+.0f}%)" if k else f"{m[k]:.2f}" for k in DROPS}})
w(pd.DataFrame(rows).set_index("chỉ số").to_markdown() + "\n")

# ---------------- độ nhạy theo loại cạnh
w("## Phụ lục – Thiếu 25% cạnh của từng loại quan hệ (quy mô medium, 30 seed)\n")
x = sens[(sens.metric == "recall") & sens.layer.isin(["all", "order"])]
t = x.groupby(["dropped_type", "domain", "layer"]).value.mean().unstack(["domain", "layer"]).round(2)
t.columns = [f"{DOM[a].split(' ')[0]} · recall {LAYER_VN[b]}" for a, b in t.columns]
w(t.to_markdown() + "\n")
open(os.path.join(RES, "summary_p3.md"), "w", encoding="utf-8").write("\n".join(out))

# ================= hình =================
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlecolor": INK, "axes.spines.top": False, "axes.spines.right": False})


def place_end_labels(ax, items, gap=0.065):
    """items: [(x, y, text)] – giãn nhãn cuối đường để không chồng nhau."""
    items = sorted(items, key=lambda t: t[1])
    ys = [y for _, y, _ in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    for (x, y, txt), yl in zip(items, ys):
        ax.annotate(txt, (x, y), xytext=(x + 2.5, yl), textcoords="data", va="center", fontsize=9, color=INK2)


def series(x):
    g = x.groupby("edge_drop").value
    m, s, n = g.mean(), g.std(), g.count()
    return m.index.values * 100, m.values, 1.96 * s.values / np.sqrt(n.values)


panels = [
    ("E1 · recall gộp các tầng", ("E1", "all", "recall"), ("forward_trace", "baseline_local"), None),
    ("E1 · recall tầng Đơn hàng", ("E1", "order", "recall"), ("forward_trace", "baseline_local"), None),
    ("E2 · Spearman với mức ảnh hưởng thật", ("E2", "all", "spearman"), ("risk_ref(est_impact)", "baseline_hops"), None),
    ("E3 · Top-1 nguyên nhân (confounder 50%)", ("E3", "all", "top1_acc"), ("backward_ref(graph+hist)", "baseline_max_anomaly"), 0.5),
]
labels = {"forward_trace": "Truy vết xuôi", "baseline_local": "Baseline cục bộ", "risk_ref(est_impact)": "Điểm rủi ro (tham chiếu)",
          "baseline_hops": "Baseline số bước", "backward_ref(graph+hist)": "Truy ngược (tham chiếu)",
          "baseline_max_anomaly": "Baseline điểm bất thường"}
fig, axes = plt.subplots(2, 4, figsize=(15, 6.6), sharey=True)
for r, dom in enumerate(("ai4i", "secom")):
    for c, (title, (exp, layer, metric), meths, conf) in enumerate(panels):
        ax = axes[r, c]
        ends = []
        for meth, col in zip(meths, (BLUE, ORANGE)):
            x = d[(d.domain == dom) & (d.experiment == exp) & (d.layer == layer) & (d.metric == metric) & (d.method == meth)]
            if conf is not None:
                x = x[x.confounder_ratio == conf]
            xs, m, ci = series(x)
            ax.fill_between(xs, m - ci, m + ci, color=col, alpha=0.12, linewidth=0)
            ax.plot(xs, m, color=col, lw=2, marker="o", ms=5, label=labels[meth])
            ends.append((xs[-1], m[-1], f"{m[-1]:.2f}"))
        place_end_labels(ax, ends)
        ax.set_xticks([0, 10, 25, 50])
        ax.set_ylim(0, 1.05)
        ax.set_xlim(-3, 60)
        ax.grid(axis="y", color=GRID, lw=0.8)
        if r == 0:
            ax.set_title(title, fontsize=10.5, loc="left")
        if r == 1:
            ax.set_xlabel("% cạnh bị xóa")
        if c == 0:
            ax.set_ylabel(DOM[dom].split(" (")[0], fontsize=11, color=INK)
        ax.legend(frameon=False, fontsize=8, loc="lower left")
fig.suptitle("E4 – Hiệu năng khi đồ thị thiếu cạnh (trung bình 30 seed × 3 quy mô, dải = KTC 95%)",
             x=0.01, ha="left", fontsize=12, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "e4_degradation.png"), dpi=160)

# hình theo tầng
fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
LCOL = {"process": "#2a78d6", "component": "#1baf7a", "product": "#6250d6", "order": "#eb6834"}
for ax, dom in zip(axes, ("ai4i", "secom")):
    ends = []
    for layer in ["process", "component", "product", "order"]:
        x = d[(d.domain == dom) & (d.experiment == "E1") & (d.method == "forward_trace") & (d.layer == layer) & (d.metric == "recall")]
        xs, m, _ = series(x)
        ax.plot(xs, m, color=LCOL[layer], lw=2, marker="o", ms=5, label=LAYER_VN[layer])
        ends.append((xs[-1], m[-1], LAYER_VN[layer]))
    place_end_labels(ax, ends, gap=0.055)
    ax.set_title(DOM[dom], loc="left", fontsize=10.5)
    ax.set_xticks([0, 10, 25, 50]); ax.set_xlim(-3, 68); ax.set_ylim(0, 1.05)
    ax.set_xlabel("% cạnh bị xóa"); ax.grid(axis="y", color=GRID, lw=0.8)
    ax.legend(frameon=False, fontsize=8, loc="lower left")
axes[0].set_ylabel("Recall truy vết xuôi")
fig.suptitle("Tầng càng xa nguồn lỗi càng mất nhiều khi thiếu cạnh", x=0.01, ha="left", fontsize=12, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "e4_recall_by_layer.png"), dpi=160)
print("ok →", RES)
