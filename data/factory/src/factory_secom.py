# Nhánh B (SECOM): Công đoạn PB01–PB10 -> Linh kiện -> Sản phẩm -> Đơn hàng (không có tầng Máy)
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

SEED, N_PROC, N_PRODUCTS, N_ORDERS = 42, 10, 500, 10000
OUT = Path("out_b"); OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)
PROC = [f"PB{i:02d}" for i in range(1, N_PROC + 1)]      # trùng node_id đã gán dòng SECOM

# ---- Quy trình: mỗi sản phẩm đi qua 3–6 công đoạn, giữ thứ tự PB01 -> PB10 ----
rows = []
for k in range(N_PRODUCTS):
    pid = f"SPB{k+1:03d}"
    steps = sorted(rng.choice(N_PROC, size=rng.integers(3, 7), replace=False))
    for s, p in enumerate(steps, 1):
        rows.append(dict(product_id=pid, step=s, process_id=PROC[p],
                         component_id=f"CB{p+1:02d}{rng.integers(1, 31):02d}"))   # 30 loại linh kiện/công đoạn
routing = pd.DataFrame(rows)

# ---- Đơn hàng: mỗi sản phẩm >= 1 đơn, phần còn lại chia lệch kiểu Dirichlet ----
counts = rng.multinomial(N_ORDERS - N_PRODUCTS, rng.dirichlet(np.full(N_PRODUCTS, 1.0))) + 1
orders = pd.DataFrame({"product_id": np.repeat([f"SPB{k+1:03d}" for k in range(N_PRODUCTS)], counts)})
orders = orders.sample(frac=1, random_state=SEED).reset_index(drop=True)
orders.insert(0, "order_id", [f"DHB{i+1:05d}" for i in range(N_ORDERS)])
orders["qty"] = rng.integers(10, 501, N_ORDERS)
orders["priority"] = rng.choice(["Cao", "Trung bình", "Thấp"], N_ORDERS, p=[.15, .55, .30])
orders["due_date"] = pd.Timestamp("2026-11-01") + pd.to_timedelta(rng.integers(0, 90, N_ORDERS), unit="D")

routing.to_csv(OUT / "routing_b.csv", index=False)
orders.to_csv(OUT / "orders_b.csv", index=False)

def draw_route(product_id):
    r = routing[routing.product_id == product_id].sort_values("step")
    n_ord = (orders.product_id == product_id).sum()
    fig, ax = plt.subplots(figsize=(2.6 * len(r) + 3.2, 3.6)); ax.axis("off")
    for i, (_, s) in enumerate(r.iterrows()):
        x = i * 2.6
        ax.add_patch(plt.Rectangle((x, 1.2), 2, 1, fc="#fef3c7", ec="#b45309", lw=1.5))
        ax.text(x + 1, 1.7, s.process_id, ha="center", va="center", fontsize=11, weight="bold")
        ax.text(x + 1, 2.55, f"Linh kiện {s.component_id}", ha="center", fontsize=8.5, color="#475569")
        ax.annotate("", xy=(x + 2.55, 1.7), xytext=(x + 2, 1.7), arrowprops=dict(arrowstyle="->", lw=1.5))
    x = len(r) * 2.6
    ax.add_patch(plt.Rectangle((x + .05, 1.2), 2.2, 1, fc="#dcfce7", ec="#15803d", lw=1.5))
    ax.text(x + 1.15, 1.9, product_id, ha="center", fontsize=10, weight="bold")
    ax.text(x + 1.15, 1.5, f"{n_ord} đơn hàng", ha="center", fontsize=9)
    ax.set_xlim(-.3, x + 2.5); ax.set_ylim(0.6, 3.0)
    ax.set_title(f"Nhánh B – quy trình {product_id}: Công đoạn → Linh kiện → Sản phẩm → Đơn hàng", fontsize=11)
    fig.savefig(OUT / f"route_{product_id}.png", dpi=130, bbox_inches="tight"); plt.close(fig)

for p in ["SPB001", "SPB002", "SPB003"]:
    draw_route(p)

print("Công đoạn:", N_PROC, "| sản phẩm:", routing.product_id.nunique(), "| đơn:", len(orders),
      "| đơn/SP min/TB/max:", counts.min(), round(counts.mean(), 1), counts.max())
print("Số bước/SP:\n", routing.groupby("product_id").size().value_counts().sort_index())
print("Thứ tự đúng:", all(g.process_id.map(PROC.index).is_monotonic_increasing for _, g in routing.groupby("product_id")))
print("Mỗi công đoạn có SP đi qua:", routing.groupby("process_id").product_id.nunique().min(), "–",
      routing.groupby("process_id").product_id.nunique().max())