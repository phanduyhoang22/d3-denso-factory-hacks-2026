"""E5/E6 tự động theo tiêu chí KHÁCH QUAN (không thay thế chấm của người / phỏng vấn kỹ sư).

  python scripts/auto_e5_e6.py           # ghi docs/E5_E6_tu_dong.md

E5 – mỗi sự cố thật (443) được kiểm 3 câu bằng dữ liệu, không bằng ý kiến:
  C1 nguyên nhân: máy/công đoạn xếp #1 có đúng là nơi xảy ra sự cố gốc không (và có trong top-3 không)
  C2 phạm vi:     tập sản phẩm/đơn hàng hệ thống báo có KHỚP với tập đếm lại độc lập từ routing.csv/orders.csv không
  C3 hành động:   (a) có hành động kiểm tra đúng node lỗi theo luật kb.yaml của đúng chế độ lỗi
                  (b) máy dự phòng đề xuất cùng công đoạn và khác máy lỗi (theo routing)
                  (c) 5 đơn "ưu tiên giữ tiến độ" đều thuộc tập đơn bị ảnh hưởng
E6 – khối lượng tra cứu thủ công (số dòng phải dò qua các bảng) và thời gian pipeline đo được.
     KHÔNG có số phút thủ công: chỉ phỏng vấn kỹ sư mới cho được con số đó.
"""
import re
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d3.factory import _read, incidents_for  # noqa: E402
from d3.pipeline import run_scenario  # noqa: E402
from d3.registry import resolve_all  # noqa: E402


def independent_scope(ds, node, routing, orders):
    """Đếm lại phạm vi trực tiếp từ CSV, không qua đồ thị."""
    key = "machine_id" if ds == "ai4i" else "process_id"
    prods = set(routing.loc[routing[key] == node, "product_id"])
    ords = set(orders.loc[orders.product_id.isin(prods), "order_id"])
    return prods, ords


def main():
    fns, _ = resolve_all()
    data = {"ai4i": (_read("routing.csv"), _read("orders.csv"), _read("machines.csv")),
            "secom": (_read("routing_b.csv"), _read("orders_b.csv"), None)}
    rows = []
    for ds in ("ai4i", "secom"):
        routing, orders, machines = data[ds]
        proc_of = dict(zip(machines.machine_id, machines.process.str.split().str[0])) if machines is not None else {}
        for idx, inc in enumerate(incidents_for(ds)):
            t0 = time.perf_counter()
            out, truth, _ = run_scenario(idx, {"dataset": ds, "incident_id": inc["incident_id"]}, fns,
                                         check_schema=False)
            node = inc["node_id"]
            ranked = [b["node_id"] for b in out["backward"]]
            # C2
            prods, ords = independent_scope(ds, node, routing, orders)
            f_prods = {f["node_id"] for f in out["forward"] if f["type"] == "product"}
            f_ords = {f["node_id"] for f in out["forward"] if f["type"] == "order"}
            # C3
            acts = [a["action"] for a in out["actions"]]
            check = any(a.startswith(f"Kiểm tra {node}") for a in acts)
            m = next((re.match(r"Chuyển tải sang (\S+)", a) for a in acts if a.startswith("Chuyển tải")), None)
            backup_ok = True if ds == "secom" else bool(m) and m.group(1) != node and \
                proc_of.get(m.group(1)) == proc_of.get(node)
            pr = next((a for a in acts if a.startswith("Ưu tiên giữ tiến độ")), "")
            top_orders = re.findall(r"DHB?\d+", pr.split("—")[0])
            orders_ok = bool(top_orders) and set(top_orders) <= f_ords
            rows.append(dict(dataset=ds, incident_id=inc["incident_id"], node=node, mode=inc["failure_mode"],
                             c1_top1=ranked[:1] == [node], c1_top3=node in ranked,
                             c2_products=f_prods == prods, c2_orders=f_ords == ords,
                             c3_check=check, c3_backup=backup_ok, c3_orders=orders_ok,
                             n_products=len(prods), n_orders=len(ords),
                             pipeline_ms=sum(v for k, v in out["timing_ms"].items() if k != "generate"),
                             wall_ms=(time.perf_counter() - t0) * 1000))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "results" / "e5_tu_dong.csv", index=False)
    write(df, data)


def write(df, data):
    pct = lambda s: f"{s.mean():.1%} ({int(s.sum())}/{len(s)})"  # noqa: E731
    L = ["# E5/E6 chấm tự động theo tiêu chí khách quan", "",
         "Sinh bởi `scripts/auto_e5_e6.py` trên **toàn bộ 443 sự cố thật**, đồ thị đầy đủ. Chi tiết từng sự cố: "
         "`results/e5_tu_dong.csv`.", "",
         "> Đây là kiểm tra **bằng dữ liệu**, không thay thế E5 do người chấm (`docs/E5_E6_phieu.md`) và không có "
         "số phút điều tra thủ công (cần phỏng vấn kỹ sư). Nó trả lời: hệ thống có làm *đúng điều nó tuyên bố* không.", "",
         "## E5 – kết quả", "", "| Câu | Tiêu chí kiểm | AI4I (339) | SECOM (104) |", "|---|---|---|---|"]
    a, b = df[df.dataset == "ai4i"], df[df.dataset == "secom"]
    for col, text in [("c1_top1", "C1 · nguyên nhân #1 đúng nơi xảy ra sự cố"),
                      ("c1_top3", "C1 · nơi xảy ra sự cố nằm trong top-3"),
                      ("c2_products", "C2 · tập sản phẩm khớp đếm độc lập từ CSV"),
                      ("c2_orders", "C2 · tập đơn hàng khớp đếm độc lập từ CSV"),
                      ("c3_check", "C3 · có hành động kiểm tra đúng node theo luật kb.yaml"),
                      ("c3_backup", "C3 · máy dự phòng cùng công đoạn, khác máy lỗi"),
                      ("c3_orders", "C3 · 5 đơn ưu tiên đều thuộc tập bị ảnh hưởng")]:
        L.append(f"| {col.split('_')[0].upper()} | {text} | {pct(a[col])} | "
                 f"{pct(b[col]) if col != 'c3_backup' else 'không áp dụng (không có tầng máy)'} |")
    miss = a[~a.c1_top1]
    L += ["", "Nhận xét:",
          f"- C1 sai ở {len(miss)} sự cố AI4I: hệ thống xếp một máy khác (cũng đang bất thường cùng lúc, cùng chuỗi "
          "tới đơn hàng) lên trên máy gốc. Đây là lỗi thật của truy vết ngược khi nhiều sự cố trùng thời điểm "
          "(timestamp giả dồn về 01/01 00:00), khớp với E3 trong `docs/KET_QUA_TONG_HOP.md`.",
          "- C2 kiểm tính đúng của dựng đồ thị + truy xuôi so với dữ liệu gốc; không chứng minh độ chính xác ngoài thực tế.",
          "- C3 chỉ kiểm hành động **hợp lệ về dữ liệu**; có *hợp lý về nghiệp vụ* hay không vẫn cần người chấm.", "",
          "## E6 – khối lượng tra cứu thủ công vs. pipeline", ""]
    ra, oa, ma = data["ai4i"]
    rb, ob, _ = data["secom"]
    L += ["Để tự xác định phạm vi ảnh hưởng của một sự cố, kỹ sư phải dò ít nhất các bảng sau (đếm từ dữ liệu):", "",
          "| Nhánh | Bảng phải dò | Số dòng phải dò | Phạm vi trung bình phải liệt kê | Pipeline (trung vị / P95) |",
          "|---|---|---|---|---|",
          f"| AI4I | máy → routing → đơn hàng | {len(ma) + len(ra) + len(oa):,} | {a.n_products.mean():.0f} sản phẩm, "
          f"{a.n_orders.mean():,.0f} đơn | {a.pipeline_ms.median():.0f} ms / {a.pipeline_ms.quantile(.95):.0f} ms |",
          f"| SECOM | routing → đơn hàng | {len(rb) + len(ob):,} | {b.n_products.mean():.0f} sản phẩm, "
          f"{b.n_orders.mean():,.0f} đơn | {b.pipeline_ms.median():.0f} ms / {b.pipeline_ms.quantile(.95):.0f} ms |", "",
          "Số phút điều tra thủ công: **chưa có** – cần phỏng vấn kỹ sư (`docs/E5_E6_phieu.md`, mục E6). "
          "Khi có số, E6 = phút thủ công ÷ thời gian pipeline ở bảng trên."]
    (ROOT / "docs" / "E5_E6_tu_dong.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
