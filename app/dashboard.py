"""Dashboard demo D3 (P5, Part 4). Chạy:  streamlit run app/dashboard.py

Chỉ dùng dữ liệu nhà máy của nhóm (data/factory/). Bố cục theo kịch bản trình diễn mục 10:
  Bước 1 Phát hiện → Bước 2 Truy vết xuôi → Bước 3 Đánh giá rủi ro → Bước 4 Truy vết ngược → Bước 5 Hành động
"""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d3 import RESULTS_DIR  # noqa: E402
from d3.factory import incidents_for  # noqa: E402
from d3.pipeline import run_scenario  # noqa: E402
from d3.registry import resolve_all  # noqa: E402

DEPT_VI = {"maintenance": "Bảo trì", "production": "Sản xuất", "quality": "Chất lượng",
           "warehouse": "Kho", "planning": "Kế hoạch", "sales": "Kinh doanh"}
TYPE_VI = {"sensor": "Cảm biến", "machine": "Máy", "process": "Công đoạn", "part": "Linh kiện",
           "product": "Sản phẩm", "order": "Đơn hàng"}
LAYER_ORDER = ["sensor", "machine", "process", "part", "product", "order"]
DEMO_INCIDENT = "INC_A003"  # kịch bản trình diễn mục 10, chốt ở schemas/README.md
SEVERITY_VI = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}

st.set_page_config(page_title="D3 – Truy vết tác động sự cố", page_icon="🏭", layout="wide")


# ---------------------------------------------------------------- dữ liệu (data/factory/)
@st.cache_resource(show_spinner="Đang dựng đồ thị nhà máy và truy vết…", max_entries=32)
def run_real(dataset, incident_id, index, drop, window, confounders):
    fns, impl = resolve_all()
    out, _, ctx = run_scenario(index, {"dataset": dataset, "incident_id": incident_id, "edge_drop_rate": drop,
                                       "window_hours": window, "confounders": confounders}, fns, check_schema=False)
    return out, ctx["graph_observed"], impl


def incident_label(i):
    return f"{i['incident_id']} · {i['node_id']} · {i['failure_mode']} · {i['timestamp'][:16].replace('T', ' ')}"


with st.sidebar:
    st.header("Sự cố")
    ds = st.radio("Nhánh", ["ai4i", "secom"], horizontal=True,
                  format_func={"ai4i": "A · AI4I (máy)", "secom": "B · SECOM (công đoạn)"}.get)
    pool = incidents_for(ds)
    modes = sorted({i["failure_mode"] for i in pool})
    pick_modes = st.multiselect("Lọc chế độ lỗi", modes, default=[])
    shown = [i for i in pool if not pick_modes or i["failure_mode"] in pick_modes]
    demo = next((k for k, i in enumerate(shown) if i["incident_id"] == DEMO_INCIDENT), 0)
    inc_sel = st.selectbox(f"Sự cố thật ({len(shown)}/{len(pool)})", shown, index=demo, format_func=incident_label,
                           help=f"Mặc định: {DEMO_INCIDENT} = kịch bản demo đã chốt (schemas/README.md)")
    window = st.select_slider("Cửa sổ sự cố đồng thời (giờ)", [0.5, 1.0, 2.0, 4.0, 8.0], 2.0,
                              help="Sự cố khác xảy ra trong khoảng này trước sự cố gốc = ứng viên nguyên nhân")
    conf = "labels"
    if ds == "ai4i":
        conf = "alarms" if st.checkbox("Tính cả cảnh báo sai của detector P1", value=False,
                                       help="Isolation Forest báo sai ~42% dòng bình thường → nhiều ứng viên nguyên nhân hơn")             else "labels"
    drop = st.select_slider("Tỷ lệ cạnh bị thiếu (E4)", [0.0, 0.1, 0.25, 0.5], 0.0)
    top_k = st.slider("Số đơn hàng vẽ trên đồ thị", 3, 25, 8)
    scenario, G, impl = run_real(ds, inc_sel["incident_id"], pool.index(inc_sel), drop, window, conf)
    show_all = False
    st.caption("Module: " + " · ".join(f"{k} {'✅' if v == 'real' else '(mock)'}" for k, v in impl.items()
                                         if not k.startswith("baseline")))

BIG = len(scenario["forward"]) > 40
fwd_by_node = {f["node_id"]: f for f in scenario["forward"]}
inc = scenario["incident"]
risk_by_node = {r["node_id"]: r for r in scenario["risk"]}
fwd_nodes = {f["node_id"] for f in scenario["forward"]}
fwd_edges = {(u, v) for f in scenario["forward"] for u, v in zip(f["path"], f["path"][1:])}
cause_nodes = {b["node_id"] for b in scenario["backward"]}

# ---------------------------------------------------------------- tiêu đề
st.title("🏭 Phát hiện sự cố & truy vết tác động trong chuỗi sản xuất")
st.caption("Chuyện gì đã xảy ra? · Những gì sẽ bị ảnh hưởng? · Tại sao? · Nên xử lý việc gì trước?   "
           f"— kịch bản `{scenario['scenario_id']}`")

# ---------------------------------------------------------------- Bước 1
st.subheader("Bước 1 – Phát hiện")
c = st.columns(5)
c[0].metric("Sự cố", inc["incident_id"])
c[1].metric("Vị trí", inc["node_id"] or "—")
c[2].metric("Loại bất thường", inc["anomaly_type"], inc.get("failure_mode") or None, delta_color="off")
c[3].metric("Điểm bất thường", f"{inc['anomaly_score']:.2f}")
c[4].metric("Mức độ", SEVERITY_VI[inc["severity"]])
st.caption(f"Thời điểm {inc['timestamp']}{' (giả định theo thứ tự dòng)' if inc['timestamp_is_synthetic'] else ''}"
           f" · nguồn {inc['dataset']} dòng {inc['source_row']} · bộ phát hiện {inc['detector']}"
           f" · nhóm nguyên nhân nghi ngờ: {inc.get('suspected_cause_group') or '—'}")


# ---------------------------------------------------------------- Bước 2
def risk_color(score):
    # vàng nhạt → đỏ cam theo điểm rủi ro
    r, g, b = 255, int(235 - 150 * score), int(200 - 170 * score)
    return f"#{r:02x}{max(g, 0):02x}{max(b, 0):02x}"


def big_keep():
    """Đồ thị lớn: sự cố + công đoạn của nó + nguyên nhân khả dĩ + đường tới top-K đơn rủi ro cao nhất."""
    keep = {inc["node_id"]} | cause_nodes
    keep |= {v for v in G.successors(inc["node_id"]) if G.nodes[v]["type"] == "process"}
    orders = [r["node_id"] for r in scenario["risk"] if r["type"] == "order"][:top_k]
    for n in orders:
        keep |= set(fwd_by_node[n]["path"])
    return keep


def to_dot():
    if BIG:
        keep = big_keep()
    else:
        keep = set(G.nodes) if show_all else fwd_nodes | {inc["node_id"]} | cause_nodes | \
            {p for n in fwd_nodes | {inc["node_id"]} for p in G.predecessors(n) if G.nodes[p]["type"] == "sensor"}
    lines = ['digraph G {', 'rankdir=LR; nodesep=0.25; ranksep=0.6; bgcolor="transparent";',
             'node [shape=box style="rounded,filled" fontname="Helvetica" fontsize=11 color="#888888"];',
             'edge [color="#bbbbbb" arrowsize=0.6];']
    for layer in LAYER_ORDER:
        ids = [n for n in keep if G.nodes[n]["type"] == layer]
        if ids:
            lines.append("{rank=same; " + " ".join(f'"{n}";' for n in sorted(ids)) + "}")
    for n in keep:
        a = G.nodes[n]
        label = f"{n}\\n{a.get('label', '')}" if a.get("label") and a.get("label") != n else n
        fill, extra = "#f2f2f2", ""
        if n == inc["node_id"]:
            fill, extra = "#d62728", ' fontcolor="white" penwidth=2 color="#7f0000"'
        elif n in risk_by_node:
            fill = risk_color(risk_by_node[n]["risk_score"])
            label += f"\\nrủi ro {risk_by_node[n]['risk_score']:.2f}"
        elif n in cause_nodes:
            fill, extra = "#ffe680", ' style="rounded,filled,dashed"'
        lines.append(f'"{n}" [label="{label}" fillcolor="{fill}"{extra}];')
    for u, v, d in G.out_edges(keep, data=True):
        if v in keep:
            style = ' color="#d62728" penwidth=2.2' if (u, v) in fwd_edges else ""
            lines.append(f'"{u}" -> "{v}" [tooltip="{d["relation"]} w={d["weight"]}"{style}];')
    lines.append("}")
    return "\n".join(lines)


st.subheader("Bước 2 – Truy vết xuôi: phạm vi ảnh hưởng")
if BIG:
    by_type = pd.Series([f["type"] for f in scenario["forward"]]).value_counts()
    orders = [G.nodes[f["node_id"]] for f in scenario["forward"] if f["type"] == "order"]
    c = st.columns(6)
    c[0].metric("Linh kiện", f"{by_type.get('part', 0):,}")
    c[1].metric("Sản phẩm", f"{by_type.get('product', 0):,}")
    c[2].metric("Đơn hàng", f"{by_type.get('order', 0):,}")
    c[3].metric("Số lượng đặt", f"{sum(o.get('qty', 0) for o in orders):,}")
    c[4].metric("Đơn ưu tiên Cao", f"{sum(o.get('priority_label') == 'Cao' for o in orders):,}")
    c[5].metric("Đơn hạn ≤ 14 ngày", f"{sum(o.get('due_in_days', 99) <= 14 for o in orders):,}")
    top_orders = [r["node_id"] for r in scenario["risk"] if r["type"] == "order"][:3]
    st.markdown("Đường lan truyền tới 3 đơn rủi ro cao nhất:  \n" +
                "  \n".join(f"**{' → '.join(fwd_by_node[n]['path'])}**" for n in top_orders))
else:
    paths = sorted({" → ".join(f["path"]) for f in scenario["forward"]
                    if not any(set(f["path"]) < set(g["path"]) for g in scenario["forward"])})
    if paths:
        st.markdown("  \n".join(f"**{p}**" for p in paths))
if not scenario["forward"]:
    st.info("Không tìm thấy đối tượng phía sau (đồ thị có thể thiếu cạnh).")
st.graphviz_chart(to_dot(), width="stretch")
if BIG:
    st.caption(f"Đồ thị chỉ vẽ đường tới {top_k} đơn rủi ro cao nhất "
               f"(trên tổng {len(scenario['forward']):,} đối tượng bị ảnh hưởng).")
st.caption("🟥 nơi xảy ra sự cố · 🟧 đối tượng bị ảnh hưởng (màu đậm = rủi ro cao) · "
           "🟨 máy bất thường khác (ứng viên nguyên nhân) · mũi tên đỏ = đường lan truyền")

# ---------------------------------------------------------------- Bước 3 & 4
left, right = st.columns([3, 2])
with left:
    st.subheader("Bước 3 – Đánh giá rủi ro tác động")
    if scenario["risk"]:
        df = pd.DataFrame(scenario["risk"])
        if BIG:
            types = st.multiselect("Loại đối tượng", list(TYPE_VI), default=["part", "product", "order"],
                                   format_func=TYPE_VI.get)
            df = df[df["type"].isin(types)].head(100)
            st.caption(f"Top {len(df)} theo điểm rủi ro")
        df["type"] = df["type"].map(TYPE_VI)
        st.dataframe(df.rename(columns={"node_id": "Đối tượng", "type": "Loại", "risk_score": "Điểm rủi ro",
                                        "reason": "Lý do"}),
                     hide_index=True, width="stretch",
                     column_config={"Điểm rủi ro": st.column_config.ProgressColumn(
                         min_value=0, max_value=1, format="%.2f")})
with right:
    st.subheader("Bước 4 – Truy vết ngược: nguyên nhân khả dĩ")
    st.caption(f"Xuất phát từ kết quả xấu: **{scenario.get('bad_outcome_node') or '—'}**")
    if scenario["backward"]:
        df = pd.DataFrame(scenario["backward"])
        df["evidence"] = df.get("evidence", pd.Series([[]] * len(df))).map(lambda e: "; ".join(e or []))
        df = df[["rank", "cause", "score", "evidence"]]
        st.dataframe(df.rename(columns={"rank": "#", "cause": "Nguyên nhân nghi ngờ", "score": "Điểm",
                                        "evidence": "Bằng chứng"}),
                     hide_index=True, width="stretch",
                     column_config={"Điểm": st.column_config.ProgressColumn(min_value=0, max_value=1,
                                                                             format="%.2f")})
    st.caption("Xếp hạng nguyên nhân *khả dĩ*, không khẳng định quan hệ nhân quả.")

# ---------------------------------------------------------------- Bước 5
st.subheader("Bước 5 – Hành động ưu tiên theo bộ phận")
fb_path = RESULTS_DIR / "feedback.jsonl"
for a in sorted(scenario["actions"], key=lambda a: a["priority"]):
    col_a, col_b, col_c = st.columns([1, 7, 2])
    col_a.markdown(f"**#{a['priority']}**")
    col_b.markdown(f"**{DEPT_VI[a['department']]}** — {a['action']}"
                   + (f"  \n<small>luật {a['kb_rule_id']}"
                      + (f" · tỷ lệ chấp nhận {a['adoption_rate']:.0%}" if a.get("adoption_rate") is not None else "")
                      + "</small>" if a.get("kb_rule_id") else ""), unsafe_allow_html=True)
    ok, no = col_c.columns(2)
    for btn, verdict in ((ok, "accept"), (no, "reject")):
        if btn.button("👍" if verdict == "accept" else "👎", key=f"{verdict}_{a['priority']}",
                      help="Kỹ sư phản hồi (mục 19, việc 4)"):
            with fb_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"time": dt.datetime.now().isoformat(timespec="seconds"),
                                    "scenario_id": scenario["scenario_id"], "kb_rule_id": a.get("kb_rule_id"),
                                    "action": a["action"], "verdict": verdict}, ensure_ascii=False) + "\n")
            st.toast("Đã ghi phản hồi")

# ---------------------------------------------------------------- E6
if scenario.get("timing_ms"):
    t = scenario["timing_ms"]
    total = sum(v for k, v in t.items() if k != "generate")
    st.divider()
    st.caption(f"⏱ Pipeline phát hiện → truy vết → chấm điểm → đề xuất: **{total:.1f} ms** "
               f"({', '.join(f'{k} {v:.1f}' for k, v in t.items() if k != 'generate')})")
