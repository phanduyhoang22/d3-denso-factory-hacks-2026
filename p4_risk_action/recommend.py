"""recommend.py – P4.4. recommend(inc, routing, orders, kb, scored=None) -> DataFrame [Ưu tiên, Hành động, Căn cứ].
Không dùng tồn kho (dữ liệu không có; ghi rõ là hạn chế trong báo cáo).
inc: dict(node_id, failure_mode, dataset). scored: bảng từ risk_score(); None thì tự tính bằng mock_forward."""
import pandas as pd
from risk import mock_forward, risk_score, PARAMS

def adoption_rate(rule):
    return rule["n_accepted"] / rule["n_shown"] if rule["n_shown"] else None

def recommend(inc, routing, orders, kb, scored=None, top=5, p=PARAMS):
    br = "A" if inc["dataset"] == "AI4I" else "B"
    if scored is None:
        scored = risk_score(mock_forward(inc["node_id"], routing, orders, br), orders, p)
    acts, node = [], inc["node_id"]
    rules = [kb.get(m, kb["UNKNOWN"]) for m in inc["failure_mode"].split("+")]   # lỗi chồng "PWF+OSF" -> 2 luật
    # 1) kiểm tra nguyên nhân + báo bộ phận kỹ thuật
    for m, r in zip(inc["failure_mode"].split("+"), rules):
        ar = adoption_rate(r)
        acts.append((f"Kiểm tra {node}: {r['action']}", f"{m}: {r['cause']}" + (f"; tỷ lệ chấp nhận {ar:.0%}" if ar is not None else "")))
    for t in dict.fromkeys(r["team"] for r in rules):
        acts.append((f"Chuyển cảnh báo tới: {t}", f"sự cố {inc['failure_mode']} tại {node}"))
    # 2) chuyển tải sang máy dự phòng (chỉ nhánh A có máy)
    if br == "A":
        s = routing[routing.machine_id == node]
        d = (orders[orders.product_id.isin(s.product_id)].merge(s[["product_id", "backup_machine_id"]], on="product_id")
             .groupby("backup_machine_id").size().sort_values())
        acts.append((f"Chuyển tải sang {d.index[0]}", f"nhận ít đơn nhất ({d.iloc[0]} đơn); tránh {d.index[-1]} ({d.iloc[-1]} đơn). Chưa mô hình hóa công suất máy dự phòng"))
    # 3) ưu tiên giữ tiến độ các đơn rủi ro cao nhất
    o = scored[scored.level == "order"].nlargest(top, "risk")
    od = orders.set_index("order_id")
    acts.append((f"Ưu tiên giữ tiến độ {len(o)} đơn rủi ro cao nhất: " + ", ".join(o.obj_id),
                 f"điểm {o.risk.max():.2f}–{o.risk.min():.2f}; {int((od.loc[o.obj_id].priority == 'Cao').sum())}/{len(o)} đơn ưu tiên Cao"))
    # 4) dời lịch các đơn ưu tiên Thấp, hạn giao xa (giải phóng năng lực)
    ao = od.loc[scored[scored.level == "order"].obj_id]
    days = (pd.to_datetime(ao.due_date) - pd.Timestamp(p["t0"])).dt.days
    late = ao[(ao.priority == "Thấp") & (days >= 60)]
    if len(late):
        acts.append((f"Cân nhắc dời lịch {len(late)} đơn ưu tiên Thấp có hạn giao ≥ 60 ngày", f"tổng {int(late.qty.sum())} sản phẩm; giải phóng năng lực cho đơn gấp"))
    return pd.DataFrame([(i + 1, a, b) for i, (a, b) in enumerate(acts)], columns=["Ưu tiên", "Hành động", "Căn cứ"])