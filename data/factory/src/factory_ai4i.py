import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

SEED, N_MACHINES, N_PRODUCTS, N_ORDERS = 42, 50, 2000, 50000
OUT = Path("out"); OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)

# ---- 1. Máy -> Công đoạn (8 công đoạn, thứ tự cố định trong nhà máy) ----
PROC = ["P1 Cắt", "P2 Tiện", "P3 Phay", "P4 Hàn", "P5 Sơn/Xử lý bề mặt",
        "P6 Lắp ráp", "P7 Kiểm tra QC", "P8 Đóng gói"]
sizes = [6, 7, 7, 6, 6, 7, 6, 5]                      # tổng = 50
machines = pd.DataFrame({
    "machine_id": [f"M{i:02d}" for i in range(1, N_MACHINES + 1)],
    "process": np.repeat(PROC, sizes)})
pool = machines.groupby("process")["machine_id"].apply(list).to_dict()

# ---- 2. Sản phẩm: route = dãy công đoạn (giữ thứ tự), mỗi bước 1 máy chính + 1 máy dự phòng cùng công đoạn ----
rows = []
for k in range(N_PRODUCTS):
    pid = f"SP{k+1:04d}"
    n_steps = rng.integers(3, 7)                                   # 3–6 công đoạn
    mid = rng.choice(range(1, 7), size=n_steps - 2, replace=False)  # công đoạn giữa
    steps = [0, *sorted(mid), 7] if rng.random() < .5 else sorted(rng.choice(8, n_steps, replace=False))
    steps = sorted(set(steps))
    for s, p in enumerate(steps, 1):
        main, backup = rng.choice(pool[PROC[p]], size=2, replace=False)   # backup: cùng công đoạn, khác máy chính
        rows.append(dict(product_id=pid, step=s, process=PROC[p],
                         machine_id=main, backup_machine_id=backup,
                         component_id=f"C{p+1}{rng.integers(1, 41):02d}"))   # 40 loại linh kiện/công đoạn
routing = pd.DataFrame(rows)

# ---- 3. 50.000 đơn hàng chia vào 2.000 sản phẩm (mỗi sản phẩm >= 1 đơn, phần còn lại lệch kiểu Dirichlet) ----
w = rng.dirichlet(np.full(N_PRODUCTS, 1.0))
extra = rng.multinomial(N_ORDERS - N_PRODUCTS, w)
counts = extra + 1
orders = pd.DataFrame({"product_id": np.repeat([f"SP{k+1:04d}" for k in range(N_PRODUCTS)], counts)})
orders = orders.sample(frac=1, random_state=SEED).reset_index(drop=True)
orders.insert(0, "order_id", [f"DH{i+1:05d}" for i in range(N_ORDERS)])
orders["qty"] = rng.integers(10, 501, N_ORDERS)
orders["priority"] = rng.choice(["Cao", "Trung bình", "Thấp"], N_ORDERS, p=[.15, .55, .30])
orders["due_date"] = pd.Timestamp("2026-11-01") + pd.to_timedelta(rng.integers(0, 90, N_ORDERS), unit="D")

machines.to_csv(OUT / "machines.csv", index=False)
routing.to_csv(OUT / "routing.csv", index=False)
orders.to_csv(OUT / "orders.csv", index=False)

# ---- 4. Vẽ quy trình chạy của 1 sản phẩm ----
def draw_route(product_id, save=True):
    r = routing[routing.product_id == product_id].sort_values("step")
    n_ord = (orders.product_id == product_id).sum()
    fig, ax = plt.subplots(figsize=(2.6 * len(r) + 3.2, 4.2)); ax.axis("off")
    for i, (_, s) in enumerate(r.iterrows()):
        x = i * 2.6
        ax.add_patch(plt.Rectangle((x, 1.4), 2, 1, fc="#dbeafe", ec="#1d4ed8", lw=1.5))
        ax.text(x + 1, 1.9, s.process, ha="center", va="center", fontsize=10, weight="bold")
        ax.text(x + 1, 0.85, f"{s.machine_id} (chính)", ha="center", fontsize=10, color="#166534", weight="bold")
        ax.text(x + 1, 0.4, f"{s.backup_machine_id} (dự phòng)", ha="center", fontsize=9, color="#92400e")
        ax.text(x + 1, 2.75, f"Linh kiện {s.component_id}", ha="center", fontsize=8.5, color="#475569")
        if i < len(r) - 1:
            ax.annotate("", xy=(x + 2.55, 1.9), xytext=(x + 2, 1.9), arrowprops=dict(arrowstyle="->", lw=1.5))
    x = len(r) * 2.6
    ax.annotate("", xy=(x + .05, 1.9), xytext=(x - .6, 1.9), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.add_patch(plt.Rectangle((x + .05, 1.4), 2.2, 1, fc="#dcfce7", ec="#15803d", lw=1.5))
    ax.text(x + 1.15, 2.1, product_id, ha="center", fontsize=10, weight="bold")
    ax.text(x + 1.15, 1.7, f"{n_ord} đơn hàng", ha="center", fontsize=9)
    ax.set_xlim(-.3, x + 2.5); ax.set_ylim(0, 3.2)
    ax.set_title(f"Quy trình sản xuất {product_id}: Máy → Công đoạn → Linh kiện → Sản phẩm → Đơn hàng", fontsize=11)
    if save: fig.savefig(OUT / f"route_{product_id}.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

for p in ["SP0001", "SP0002", "SP0003"]:
    draw_route(p)

# ---- Kiểm tra ----
print("Máy:", len(machines), "| công đoạn:", machines.process.nunique())
print("Sản phẩm:", routing.product_id.nunique(), "| đơn:", len(orders), "| đơn/sản phẩm min/TB/max:",
      counts.min(), round(counts.mean(), 1), counts.max())
print("Số bước/sản phẩm:\n", routing.groupby("product_id").size().value_counts().sort_index())
print("Thứ tự công đoạn đúng:", all(g.process.map(PROC.index).is_monotonic_increasing
      for _, g in routing.sort_values(["product_id","step"]).groupby("product_id")))
print("Máy dự phòng khác máy chính:", (routing.machine_id != routing.backup_machine_id).all())
mp = machines.set_index("machine_id").process
print("Máy dự phòng cùng công đoạn:", (routing.backup_machine_id.map(mp) == routing.process).all())