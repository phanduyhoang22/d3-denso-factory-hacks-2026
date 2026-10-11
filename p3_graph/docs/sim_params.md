# Tham số mô phỏng – P3.2 (mục 18.1: bắt buộc ghi rõ là tự sinh)

> AI4I 2020 và SECOM chỉ có **tín hiệu cảm biến + nhãn lỗi**. Mọi thứ trong file này – cấu trúc đồ thị, trọng số phụ thuộc, tồn kho dự phòng, ưu tiên và hạn giao đơn hàng, máy thay thế, mức nghiêm trọng – là **giả định minh họa do nhóm tự sinh**, không phải dữ liệu Denso. Nguồn sự thật trong code: `d3p3/sim_params.py`.

## Quy mô đồ thị

| size | Line A × công đoạn | Line B × công đoạn | Sản phẩm | Đơn hàng | Node (seed 1) | Cạnh (seed 1) |
|---|---|---|---|---|---|---|
| small | 2 × 3 | 2 × 3 | 6 | 15 | 152 | 190 |
| medium | 3 × 4 | 2 × 4 | 12 | 40 | 257 | 334 |
| large | 5 × 5 | 3 × 5 | 28 | 100 | 647 | 848 |

Số máy, linh kiện… thay đổi theo seed (medium seed 1: 30 máy, 20 công đoạn, 36 linh kiện).

## Cấu trúc

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| Máy / công đoạn (nhánh A) | 1–3 | tỷ trọng tải ~ Dirichlet(2) |
| Máy / công đoạn (nhánh B) | 1–2 | không gắn dữ liệu, chỉ để đủ ontology |
| Máy dùng chung với công đoạn kế tiếp | 15% | |
| Cạnh `feeds` giữa 2 công đoạn liên tiếp | 60%, w ∈ [0.3, 0.7] | |
| Linh kiện / công đoạn | 1–3, w ∈ [0.6, 1.0] | |
| Linh kiện có nguồn thứ 2 | 20%, w × 0.5 | |
| Linh kiện / sản phẩm | 2–5, w ∈ [0.3, 1.0] | 80% từ line "nhà" của sản phẩm |
| Sản phẩm / đơn hàng | 1–3, tỷ trọng ~ Dirichlet(2), tối thiểu 0.05 | 70% cùng họ sản phẩm |
| Loại máy L/M/H | 60/30/10% | khớp tỷ lệ cột Type của AI4I |
| Cảm biến | 5/máy (AI4I), 3 nhóm/công đoạn (SECOM) | |

Họ sản phẩm (product family) được thêm sau bản thử đầu tiên: khi linh kiện được chọn ngẫu nhiên toàn nhà máy, gần như mọi máy đều là tổ tiên của mọi đơn hàng → không còn máy nào đủ điều kiện làm confounder (yêu cầu 18.3). Gắn sản phẩm với line nhà vừa thực tế hơn vừa giữ được thiết kế nhiễu.

## Thuộc tính vận hành

| Tham số | Giá trị |
|---|---|
| Công suất dư của máy | U(0, 0.5) |
| Bộ đệm WIP công đoạn (ẩn với hệ thống) | U(0, 0.2) |
| Mức dùng linh kiện / ngày | 50–500 |
| Số ngày tồn kho dự phòng | U(0, 6) |
| Lead time | 2–14 ngày |
| Số nguồn thay thế | 0–3 |
| Tồn kho hấp thụ tối đa | 70% cú sốc |
| Ưu tiên đơn hàng 1/2/3 | 20/50/30% |
| Hạn giao | 1–30 ngày |
| Số lượng đơn | 100–5000 |

## Mức nghiêm trọng theo chế độ lỗi (đầu vào lan truyền)

| PWF | HDF | OSF | SECOM fail | UNK | TWF | RNF |
|---|---|---|---|---|---|---|
| 1.0 | 0.9 | 0.8 | 0.8 | 0.7 | 0.6 | 0.5 |

Nhãn: ≥ 0.85 "Cao", ≥ 0.65 "Trung bình", còn lại "Thấp".

## Ground truth, quan sát, nhiễu

| Tham số | Giá trị |
|---|---|
| Ngưỡng "bị ảnh hưởng thật" | true_impact ≥ 0.10 |
| Nhiễu trọng số cạnh hệ thống thấy | log-normal σ = 0.25, cắt về [0.01, 1] |
| Nhiễu tồn kho hệ thống thấy | log-normal σ = 0.20 |
| Tỷ lệ xóa cạnh (E4) | 0 / 10 / 25 / 50% cạnh lan truyền, lồng nhau theo seed |
| Tỷ lệ confounder | 0 / 25 / 50% số node nguồn **không phải tổ tiên** của kết quả xấu |

## Dòng thời gian kịch bản (timestamp GIẢ)

| Mốc | Giá trị |
|---|---|
| Gốc thời gian | 2026-09-15 08:00 + (seed mod 365) ngày |
| Sự cố gốc | +U(0, 2) giờ |
| Kết quả xấu | sự cố gốc + U(2, 6) giờ |
| Confounder | đều trong [gốc − 3h, kết quả xấu − 10 phút] → có thể xảy ra sau gốc (làm baseline "gần nhất" sai) |

AI4I không có thời gian thật: dùng thứ tự dòng (`pseudo_time_min = UDI`) và timeline kịch bản; mọi bản ghi sự cố có `timestamp_is_synthetic = true`. SECOM có thời gian thật (giữ trong dữ liệu gốc, dùng để chia train/test), nhưng thời điểm trong kịch bản vẫn là giả.

## Chia dữ liệu (chung cho cả nhóm, seed 2020)

| | AI4I | SECOM |
|---|---|---|
| Cách chia | ngẫu nhiên, phân tầng theo `Machine failure` | theo thời gian, không xáo trộn |
| train / val / test | 5250 / 1750 / 3000 | 823 / 274 / 470 |
| Số lỗi train / val / test | 178 / 59 / 102 | 72 / 18 / 14 |

Sự cố gốc và confounder lấy từ **test**; `hist_fail_rate` của node chỉ tính từ **train**.

## Luồng seed

Mỗi bước có luồng RNG riêng `SeedSequence([seed, tag])`: đồ thị 101, gán dữ liệu 202, gốc 303, kết quả xấu & thời gian 404, confounder 505, quan sát/xóa cạnh 606, cảnh báo sai nền 707. Vì vậy đổi confounder hay tỷ lệ xóa cạnh **không** đổi đồ thị, gốc hay nhiễu trọng số.
