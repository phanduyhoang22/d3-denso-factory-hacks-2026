"""aggregate.py – P4.5: gom results.csv -> bảng mean ± std (+ CI 95%) và biểu đồ.
Chạy: python aggregate.py results.csv   (ghi tables/*.csv và figs/*.png)
Chấp nhận mọi experiment (E0–E4) nếu header đúng khuôn; hiện vẽ biểu đồ cho E2."""
import sys, os, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

SRC = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
os.makedirs("tables", exist_ok=True); os.makedirs("figs", exist_ok=True)
r = pd.read_csv(SRC)

def mode_group(m):                      # gộp chế độ lỗi: số mẫu từng tổ hợp quá ít (mục 18.1)
    if m in ("TWF", "HDF", "PWF", "OSF", "UNKNOWN", "SECOM_FAIL"): return m
    return "Chồng chế độ" if "+" in m else m
r["mode_group"] = r.failure_mode.map(mode_group)

def agg(df, by):
    g = df.groupby(by).value.agg(["mean", "std", "count"]).reset_index()
    g["ci95"] = 1.96 * g["std"] / np.sqrt(g["count"]); return g.round(3)

# --- bảng ---
agg(r, ["experiment", "domain", "metric", "edge_drop_rate", "method"]).to_csv("tables/by_edge_drop.csv", index=False)
agg(r[r.edge_drop_rate == 0], ["experiment", "domain", "metric", "mode_group", "method"]).to_csv("tables/by_failure_mode.csv", index=False)
agg(r, ["experiment", "domain", "metric", "confounder_rate", "method"]).to_csv("tables/by_confounder.csv", index=False)

# --- biểu đồ (E2) ---
BG, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
COL = {"risk_score": "#2a78d6", "naive_hops": "#eb6834"}; LAB = {"risk_score": "risk_score", "naive_hops": "Baseline (số bước)"}
plt.rcParams.update({"font.size": 10, "axes.facecolor": BG, "figure.facecolor": BG, "text.color": INK,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED})
def style(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=.8); ax.set_axisbelow(True)

e2 = r[r.experiment == "E2"]
if len(e2):
    # Hình 1: E4 – top-k theo tỷ lệ cạnh bị xóa
    panels = [("topk_order", "Top-50 đơn hàng"), ("topk_product", "Top-20 sản phẩm")]
    fig, axs = plt.subplots(2, 2, figsize=(9, 6.2), sharex=True)
    for i, dom in enumerate(["AI4I", "SECOM"]):
        for j, (met, title) in enumerate(panels):
            ax = axs[i, j]; style(ax)
            for m in ["risk_score", "naive_hops"]:
                g = agg(e2[(e2.domain == dom) & (e2.metric == met) & (e2.method == m)], ["edge_drop_rate"])
                x = g.edge_drop_rate * 100
                ax.errorbar(x, g["mean"], yerr=g["std"], color=COL[m], lw=2, marker="o", ms=6, capsize=3, mfc=BG, mew=2, label=LAB[m])
            ax.set_title(f"{dom} – {title}", loc="left", fontsize=10, color=INK)
            ax.set_ylim(0, 0.7); ax.set_xticks([0, 10, 25, 50])
            if i == 1: ax.set_xlabel("Tỷ lệ cạnh bị xóa (%)")
            if j == 0: ax.set_ylabel("Precision@k")
    axs[0, 0].legend(frameon=False, loc="upper right")
    fig.suptitle("E2/E4 – Điểm rủi ro so với baseline khi đồ thị thiếu cạnh (mean ± std, 30 seed)", x=.01, ha="left", fontsize=11)
    fig.tight_layout(); fig.savefig("figs/fig_e4_topk.png", dpi=150); plt.close(fig)

    # Hình 2: theo chế độ lỗi (không xóa cạnh), AI4I
    d = agg(e2[(e2.domain == "AI4I") & (e2.metric == "topk_order") & (e2.edge_drop_rate == 0)], ["mode_group", "method"])
    order = [m for m in ["TWF", "HDF", "PWF", "OSF", "Chồng chế độ", "UNKNOWN"] if m in set(d.mode_group)]
    fig, ax = plt.subplots(figsize=(8, 4)); style(ax); w = .36
    for k, m in enumerate(["risk_score", "naive_hops"]):
        s = d[d.method == m].set_index("mode_group").reindex(order)
        ax.bar(np.arange(len(order)) + (k - .5) * (w + .02), s["mean"], w, yerr=s["ci95"], color=COL[m], capsize=3, label=LAB[m])
    ax.set_xticks(range(len(order))); ax.set_xticklabels([f"{m}\n(n={int(d[(d.mode_group==m)&(d.method=='risk_score')]['count'].iloc[0])})" for m in order])
    ax.set_ylabel("Top-50 precision (đơn hàng)"); ax.legend(frameon=False)
    ax.set_title("AI4I – Top-50 theo chế độ lỗi (mean, khoảng tin cậy 95%)", loc="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig("figs/fig_e2_by_mode.png", dpi=150); plt.close(fig)

t = pd.read_csv("tables/by_failure_mode.csv"); print(t[(t.metric == "topk_order")].to_string(index=False))
print(pd.read_csv("tables/by_edge_drop.csv").query("metric=='topk_order'").to_string(index=False))