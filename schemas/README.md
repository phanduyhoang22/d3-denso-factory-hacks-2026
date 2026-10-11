# Schema D3 – bản CHỐT v1 (mốc C1, 12/10/2026)

Hợp đồng dữ liệu giữa các module của pipeline tích hợp (`src/d3/`) và dashboard. Sau bản chốt này chỉ đổi khi
cả nhóm đồng ý; mọi thay đổi ghi vào mục "Lịch sử" bên dưới.

| File | Ai xuất | Ai đọc |
|---|---|---|
| `incident.schema.json` | P1 (`p1_detection/outputs/incidents_ai4i.json`), P2 (SECOM), `src/d3/factory.py` | truy vết, dashboard |
| `graph.schema.json` | `src/d3/factory.py` (đồ thị nhà máy) | truy vết, dashboard |
| `trace_output.schema.json` | `src/d3/pipeline.py` (output 1 sự cố) | dashboard, runner |
| `examples/` | `scripts/make_examples.py` | 3 kịch bản thật (OSF, lỗi chồng, SECOM), rút gọn top 15 |

Kiểm tra: `python scripts/validate_schemas.py` (9/9 file hợp lệ tại thời điểm chốt).

## Các quyết định đã chốt

1. **Kịch bản demo mục 10 = sự cố thật `INC_A003`** (máy M41, OSF, điểm bất thường 0,975, 01/01/2026 00:30
   theo timestamp giả). Truy ngược xếp đúng M41 đứng đầu dù M21, M03 cũng bất thường cùng lúc.
   Kịch bản "M05 rung / ổ bi" trong docx **bỏ** vì AI4I không có cảm biến rung.
2. **Gán AI4I vào máy** theo `data/factory/ai4i_assigned.csv` của nhóm (chia vòng tròn 50 máy, seed 42),
   không theo Product ID (Product ID duy nhất cho mỗi dòng).
3. **Bộ phận** (`department`): `maintenance`, `production`, `quality`, `warehouse`, `planning`, `sales`.
   Mỗi hành động gắn một bộ phận → đáp ứng yêu cầu D3 "gợi ý hành động theo bộ phận".
4. **Hướng cạnh = hướng lan truyền**. Nhánh A: máy → lô linh kiện `<mã>@<máy>` → sản phẩm → đơn hàng;
   máy → công đoạn là ngữ cảnh. Nhánh B: công đoạn → linh kiện → sản phẩm → đơn hàng.
   Quan hệ: `monitors`, `performs`, `produces`, `component_of`, `fulfills`.
5. **`failure_mode`** là chuỗi `TWF|HDF|PWF|OSF|RNF|UNKNOWN|SECOM_FAIL`, nhiều chế độ nối bằng `+` (vd `PWF+OSF`);
   `null` = cảnh báo không phải lỗi thật (báo sai). Chỉ dùng để chấm, pipeline không được dựa vào nhãn này.
6. **`detector`**: `iforest` cho AI4I (điểm của P1); `label` cho SECOM (dùng nhãn thật vì phát hiện SECOM của P2
   chưa vượt ngẫu nhiên).
7. **Hàm giữa các module** cố định tên + chữ ký như `src/d3/contracts.py`.

## Schema riêng của từng part (không thay thế bản này)

P2 (`p2_secom_impact/p2_outputs/*.schema.json`) và P3 (`p3_graph/schemas/`) có schema cho bộ mô phỏng riêng của
mình (dùng cho E1–E4 có ground truth). Các schema đó phục vụ thí nghiệm nội bộ của từng part; pipeline tích hợp và
dashboard chỉ dùng 3 schema ở thư mục này.

## Lịch sử

| Ngày | Thay đổi |
|---|---|
| 04/10/2026 | Bản nháp v0 (P5) |
| 11/10/2026 | `failure_mode` nhận lỗi chồng và `UNKNOWN`; thêm `detector = "label"` (dữ liệu nhà máy của nhóm) |
| 12/10/2026 | **Chốt v1**: các quyết định 1–7 ở trên |
