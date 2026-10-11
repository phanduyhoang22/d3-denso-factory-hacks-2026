# risk_formula.md – Công thức điểm rủi ro (P4.2), CHƯA TUNE

risk(v) = w^hops(v) × dep(v) × (a + b × c(v))      → trong [0,1]

| Ký hiệu | Ý nghĩa | Giá trị |
|---|---|---|
| w | trọng số mỗi cạnh trên đồ thị (chưa có dữ liệu thật → giả định đồng đều) | 0.9 |
| hops | số bước từ node sự cố. Nhánh A: công đoạn 1, linh kiện 2, sản phẩm 3, đơn hàng 4. Nhánh B: linh kiện 1, sản phẩm 2, đơn hàng 3 | – |
| dep | phần tuyến của sản phẩm nằm tại/sau bước lỗi = (n_bước − bước_lỗi + 1) / n_bước; 1 với công đoạn, linh kiện | [0,1] |
| a, b | mức nền và mức điều chỉnh theo độ quan trọng | 0.6, 0.4 |

## Độ quan trọng c(v)
- Đơn hàng: c = 0.5·urgency + 0.3·priority + 0.2·qty_norm
  - urgency = 1 − clip((due_date − t0)/90 ngày, 0, 1); t0 = 2026-11-01 (đầu cửa sổ hạn giao, tham số giả định)
  - priority: Cao 1.0, Trung bình 0.5, Thấp 0.1
  - qty_norm = (qty − 10)/490
- Sản phẩm: c = trung bình c của các đơn hàng của nó
- Linh kiện: c = số sản phẩm bị ảnh hưởng dùng nó / giá trị lớn nhất trong cùng sự cố
- Công đoạn: c = trung bình c của mọi đơn bị ảnh hưởng

## Ví dụ tính tay (đơn DH48237, sự cố M05)
dep = 1, c = 0.995 → risk = 0.9^4 × 1 × (0.6 + 0.4×0.995) = 0.6561 × 0.998 = 0.655

## Lưu ý
- Tất cả hệ số là giá trị tạm; không chỉnh theo kết quả E2 của seed dùng để báo cáo (tránh học tắt). Phân tích độ nhạy là phần mở rộng (mục 19, việc 3).
- Chưa có tồn kho nên không có thành phần "tồn kho dự phòng" như mục 7 gợi ý; chưa có tần suất sự cố lịch sử trong công thức.
- Baseline E2: risk = 1/(1+hops) (không dùng w, dep, c).