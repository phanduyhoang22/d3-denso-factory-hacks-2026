"""risk.py – P4.2/P4.3: mock forward trace, risk_score(), baseline_e2(), e2_metrics().
Schema bảng forward (đề xuất, P3 cần xuất đúng dạng này):
  level   : process | component | product | order
  obj_id  : mã đối tượng
  hops    : số bước từ node sự cố trên đồ thị
  product_id : (chỉ với order) sản phẩm chứa đơn
  dep     : phần tuyến sản phẩm nằm sau/tại bước lỗi (product, order); 1 cho tầng khác
  n_products : (chỉ với component) số sản phẩm bị ảnh hưởng dùng linh kiện này
"""
import numpy as np, pandas as pd

PARAMS = dict(w=0.9, a=0.6, b=0.4, horizon=90, t0="2026-11-01",
              prio={"Cao": 1.0, "Trung bình": 0.5, "Thấp": 0.1})

def mock_forward(node_id, routing, orders, branch="A"):
    """Truy vết xuôi tạm (P3 sẽ thay). A: node là máy; B: node là công đoạn."""
    key, proc = ("machine_id", "process") if branch == "A" else ("process_id", "process_id")
    off = dict(process=1, component=2, product=3, order=4) if branch == "A" else dict(component=1, product=2, order=3)
    s = routing[routing[key] == node_id]
    n_steps = routing.groupby("product_id").step.max()
    s = s.assign(dep=(s.product_id.map(n_steps) - s.step + 1) / s.product_id.map(n_steps))
    parts = []
    if branch == "A":
        parts.append(pd.DataFrame(dict(level="process", obj_id=[s[proc].iloc[0]], hops=off["process"], dep=1.0)))
    comp = s.groupby("component_id").product_id.nunique()
    parts.append(pd.DataFrame(dict(level="component", obj_id=comp.index, hops=off["component"], dep=1.0, n_products=comp.values)))
    parts.append(pd.DataFrame(dict(level="product", obj_id=s.product_id.values, hops=off["product"], dep=s.dep.values)))
    o = orders[orders.product_id.isin(s.product_id)].merge(s[["product_id", "dep"]], on="product_id")
    parts.append(pd.DataFrame(dict(level="order", obj_id=o.order_id.values, product_id=o.product_id.values, hops=off["order"], dep=o.dep.values)))
    return pd.concat(parts, ignore_index=True)

def risk_score(fwd, orders, p=PARAMS):
    """risk = w^hops * dep * (a + b*c). c: độ quan trọng [0,1]."""
    t0 = pd.Timestamp(p["t0"])
    od = orders.set_index("order_id")
    urg = 1 - ((pd.to_datetime(od.due_date) - t0).dt.days / p["horizon"]).clip(0, 1)
    pri = od.priority.map(p["prio"])
    qn = (od.qty - 10) / 490
    c_order = (0.5 * urg + 0.3 * pri + 0.2 * qn).rename("c")          # độ quan trọng của đơn
    f = fwd.copy()
    f["c"] = np.nan
    is_o = f.level == "order"
    f.loc[is_o, "c"] = f.loc[is_o, "obj_id"].map(c_order).values
    c_prod = f[is_o].groupby("product_id").c.mean()                    # sản phẩm = TB các đơn của nó
    f.loc[f.level == "product", "c"] = f.loc[f.level == "product", "obj_id"].map(c_prod).values
    f.loc[f.level == "process", "c"] = c_order.loc[f[is_o].obj_id].mean()
    comp = f.level == "component"
    f.loc[comp, "c"] = (f.loc[comp, "n_products"] / f.loc[comp, "n_products"].max()).values
    f["risk"] = p["w"] ** f.hops * f.dep * (p["a"] + p["b"] * f.c)
    return f.sort_values(["level", "risk"], ascending=[True, False]).reset_index(drop=True)

def baseline_e2(fwd):
    """Baseline E2: chỉ phụ thuộc số bước (không trọng số, không độ quan trọng)."""
    f = fwd.copy(); f["risk"] = 1 / (1 + f.hops); return f

def e2_metrics(scored, true_impact, level="order", k=100):
    """true_impact: Series index=obj_id (từ P2). Trả Spearman và Top-k precision."""
    from scipy.stats import spearmanr
    s = scored[scored.level == level].set_index("obj_id").risk
    t = true_impact.reindex(s.index).dropna(); s = s.reindex(t.index)
    return dict(spearman=spearmanr(s, t)[0], topk=len(set(s.nlargest(k).index) & set(t.nlargest(k).index)) / k)

LEVEL_VI = {"process": "Công đoạn", "component": "Linh kiện", "product": "Sản phẩm", "order": "Đơn hàng"}

def risk_table(scored, orders, p=PARAMS, top=None):
    """Bảng đúng dạng mục 7: Đối tượng | Loại | Điểm rủi ro | Lý do. top=k: chỉ giữ k dòng đầu mỗi tầng."""
    t0 = pd.Timestamp(p["t0"]); od = orders.set_index("order_id")
    n_ord = scored[scored.level == "order"].groupby("product_id").size()
    hi = orders[orders.priority == "Cao"].groupby("product_id").size()
    def reason(r):
        parts = []
        if r.level == "order":
            o = od.loc[r.obj_id]; days = (pd.Timestamp(o.due_date) - t0).days
            parts.append(("hạn giao gần (còn %d ngày)" % days if days > 0 else "đến hạn ngay") if days <= 30 else "hạn giao còn %d ngày" % days)
            if o.priority == "Cao": parts.append("ưu tiên Cao")
            if o.qty >= 400: parts.append("số lượng lớn (%d)" % o.qty)
        elif r.level == "product":
            parts.append("%d đơn hàng bị ảnh hưởng, %d đơn ưu tiên Cao" % (n_ord.get(r.obj_id, 0), hi.get(r.obj_id, 0)))
        elif r.level == "component":
            parts.append("dùng cho %d sản phẩm bị ảnh hưởng" % r.n_products)
        else:
            parts.append("công đoạn của máy lỗi, phụ thuộc trực tiếp")
        if r.level in ("product", "order") and r.dep < 1:
            parts.append("bước lỗi nằm trước %d%% tuyến sản xuất" % round(r.dep * 100))
        parts.append("cách nguồn lỗi %d bước" % r.hops)
        return "; ".join(parts)
    d = scored.sort_values("risk", ascending=False)
    if top: d = d.groupby("level", sort=False).head(top)
    d = d.sort_values(["level", "risk"], ascending=[True, False])
    return pd.DataFrame({"Đối tượng": d.obj_id.values, "Loại": d.level.map(LEVEL_VI).values,
                         "Điểm rủi ro": d.risk.round(2).values, "Lý do": [reason(r) for r in d.itertuples()]})