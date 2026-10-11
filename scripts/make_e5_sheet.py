"""Sinh phiếu chấm E5 (12 sự cố thật, đủ loại lỗi) + phiếu E6 → docs/E5_E6_phieu.md

  python scripts/make_e5_sheet.py

Mỗi kịch bản in sẵn output của hệ thống; người chấm chỉ điền Đúng / Sai / Không chắc.
Không tự chấm thay: E5 là đánh giá của con người (mục 15.3).
"""
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d3.factory import incidents_for  # noqa: E402
from d3.pipeline import run_scenario  # noqa: E402

DEPT_VI = {"maintenance": "Bảo trì", "production": "Sản xuất", "quality": "Chất lượng",
           "warehouse": "Kho", "planning": "Kế hoạch", "sales": "Kinh doanh"}
TYPE_VI = {"process": "công đoạn", "part": "linh kiện", "product": "sản phẩm", "order": "đơn hàng"}
GRADERS = ["P1 Việt", "P2 Thành", "P3 Tình", "P4 Trang", "P5 Phan Hoàng"]


def pick():
    """12 sự cố: kịch bản demo + mỗi chế độ AI4I 1–2 sự cố + lỗi chồng + UNKNOWN + 3 SECOM. Cố định, không ngẫu nhiên."""
    a, b = incidents_for("ai4i"), incidents_for("secom")
    out = [next(i for i in a if i["incident_id"] == "INC_A003")]
    for mode, n in [("OSF", 1), ("HDF", 2), ("PWF", 2), ("TWF", 2)]:
        out += [i for i in a if i["failure_mode"] == mode and i not in out][:n]
    out.append(next(i for i in a if "+" in i["failure_mode"]))
    out.append(next(i for i in a if i["failure_mode"] == "UNKNOWN"))
    return [("ai4i", i) for i in out] + [("secom", i) for i in b[:3:]][:3]


def main():
    cases = pick()[:12]
    lines = ["# Phiếu E5 (chấm khuyến nghị) và E6 (thời gian điều tra)", "",
             "Sinh tự động bởi `scripts/make_e5_sheet.py` từ pipeline tích hợp (module thật P1, P4) trên sự cố thật.",
             "**Mỗi người chấm độc lập**, không xem phiếu của người khác trước khi chấm xong. Điền `Đ` (đúng), "
             "`S` (sai) hoặc `?` (không chắc) vào 3 câu cho mỗi kịch bản:", "",
             "- **C1** Nguyên nhân xếp đầu có hợp lý không?",
             "- **C2** Phạm vi ảnh hưởng (số linh kiện / sản phẩm / đơn) có hợp lý không?",
             "- **C3** Hành động đề xuất có hợp lý **và làm được** không?", ""]
    for k, (ds, inc) in enumerate(cases, 1):
        out, _, ctx = run_scenario(0, {"dataset": ds, "incident_id": inc["incident_id"]}, check_schema=False)
        cnt = Counter(f["type"] for f in out["forward"])
        scope = ", ".join(f"{cnt[t]:,} {TYPE_VI[t]}" for t in ("process", "part", "product", "order") if cnt.get(t))
        lines += [f"## K{k}. {inc['incident_id']} · {inc['node_id']} · {inc['failure_mode']} "
                  f"({inc['anomaly_type']})", "",
                  f"- Điểm bất thường {inc['anomaly_score']:.2f}; {len(ctx['incidents']) - 1} sự cố khác cùng lúc "
                  f"(cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **{out['bad_outcome_node']}**.",
                  "- Nguyên nhân khả dĩ: " + "; ".join(f"#{b['rank']} {b['node_id']} ({b['score']:.2f})"
                                                       for b in out["backward"]),
                  f"- Phạm vi ảnh hưởng: {scope}.",
                  "- Rủi ro cao nhất: " + "; ".join(f"{r['node_id']} {r['risk_score']:.2f}"
                                                   for r in out["risk"][:5]),
                  "- Hành động:"]
        lines += [f"  {a['priority']}. [{DEPT_VI[a['department']]}] {a['action']}" for a in out["actions"]]
        lines.append("")
    lines += ["## Bảng chấm", "", "| Kịch bản | " + " | ".join(f"{g} C1/C2/C3" for g in GRADERS) + " | Ghi chú |",
              "|---" * (len(GRADERS) + 2) + "|"]
    lines += [f"| K{k} {inc['incident_id']} | " + " | ".join(" / / " for _ in GRADERS) + " | |"
              for k, (_, inc) in enumerate(cases, 1)]
    lines += ["", "Tổng hợp E5 (điền sau khi chấm): với mỗi câu C1–C3, tỷ lệ `Đ` = số ô Đ / số ô đã chấm (bỏ `?`); "
              "mức đồng thuận = tỷ lệ kịch bản mà mọi người cùng một đáp án. Cần ít nhất 2 người chấm.", ""]

    # E6: thời gian đo của pipeline (từ results/), thời gian thủ công để trống
    e6 = []
    for f, name in [("run_ai4i.csv", "AI4I"), ("run_secom.csv", "SECOM")]:
        p = ROOT / "results" / f
        if p.exists():
            d = pd.read_csv(p)
            v = d[(d.metric == "pipeline_ms") & (d.edge_drop_rate == 0)].value
            e6.append(f"| {name} | {len(v)} | {v.median():.0f} ms | {v.quantile(.95):.0f} ms |")
    lines += ["# E6 – Thời gian điều tra", "",
              "Thời gian pipeline đo được (phát hiện → truy xuôi → chấm rủi ro → truy ngược → đề xuất; không tính "
              "bước dựng đồ thị):", "", "| Nhánh | Số sự cố | Trung vị | P95 |", "|---|---|---|---|", *e6, "",
              "Thời gian điều tra thủ công (điền từ phỏng vấn, phiếu câu hỏi ở "
              "`p2_secom_impact/p2_phieu_phong_van_E6_E5.md`, mục A):", "",
              "| Kỹ sư (tên, vai trò, ngày) | Xác định đối tượng bị ảnh hưởng (phút) | Xác định nguyên nhân (phút) |",
              "|---|---|---|", "| | | |", "| | | |", "",
              "Kết luận E6 = thời gian thủ công / thời gian pipeline. **Không điền số ước đoán**: chỉ dùng số từ phỏng vấn "
              "và ghi rõ nguồn."]
    out_path = ROOT / "docs" / "E5_E6_phieu.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("ghi", out_path.relative_to(ROOT), "-", len(cases), "kịch bản")


if __name__ == "__main__":
    main()
