# data_facts.md – Số liệu đếm trực tiếp từ file (seed = 42)

## 1. AI4I 2020 (UCI ID 601, file `ai4i2020.csv`) -> nhánh A, node Máy
- 10.000 dòng, 14 cột; không thiếu, không trùng (UDI và Product ID đều duy nhất).
- Type: L 6000 / M 2997 / H 1003.
- Sự cố = `Machine failure == 1`: **339 dòng (3,39%)**.
  - 330 dòng có >=1 chế độ lỗi xác định; 9 dòng không có chế độ nào -> gán `UNKNOWN`.
- Số dòng theo chế độ (trong 339 dòng sự cố, đếm chồng): TWF 46, HDF 115, PWF 95, OSF 98, RNF 1.
- 24 dòng lỗi chồng chế độ: PWF+OSF 11, HDF+OSF 6, HDF+PWF 3, TWF+OSF 2, TWF+RNF 1, TWF+PWF+OSF 1.
- RNF: 19 dòng có cờ RNF, 18 dòng trong đó `Machine failure = 0` -> coi là bình thường, loại RNF khỏi báo cáo theo chế độ (E0).
- 1 dòng TWF có tool wear 198 (< ngưỡng mô tả 200): giữ nguyên.
- Không có timestamp thật -> timestamp giả theo thứ tự UDI trong từng máy (`timestamp_is_fake = True`).
- Product ID là mã sản phẩm (mỗi dòng 1 ID), không phải mã máy.

## 2. SECOM (UCI ID 179, `secom.data` + `secom_labels.data`) -> nhánh B, node Công đoạn
- 1567 dòng, 590 cảm biến; nhãn: 1 = fail, -1 = pass.
- Fail: **104 dòng (6,64%)**; pass: 1463 dòng.
- Có timestamp thật (`timestamp_is_fake = False`).
- Khoảng thời gian: 19/07/2008 11:55 → 17/10/2008 06:07, đã sắp tăng dần (sự cố fail: 19/07/2008 13:17 → 15/10/2008 02:42).
- Tỷ lệ NaN trong 590 cột: 4,54% | 28 cột thiếu > 50% | số cột hằng số: 116.

## 3. Gán dữ liệu vào đồ thị
- AI4I -> 50 máy M01–M50 (chia vòng tròn, dòng lỗi chia riêng nên rải đều).
  - Số dòng/máy: 199–201; số dòng lỗi/máy: 6–7 (tổng 10.000 và 339, đã kiểm tra).
- SECOM -> 10 công đoạn PB01–PB10 (cùng cách chia): 156–158 dòng và 10–11 dòng fail mỗi node (tổng 1567 và 104, đã kiểm tra).
- Bảng sự cố chung `incidents_all.csv`: 443 sự cố (AI4I 339, SECOM 104), đã kiểm tra.

## 4. Tham số mô phỏng (không phải dữ liệu thật)
### Nhánh A (AI4I): Máy -> Công đoạn -> Linh kiện -> Sản phẩm -> Đơn hàng
- 8 công đoạn P1–P8 (5–7 máy mỗi công đoạn, tổng 50 máy).
- 2000 sản phẩm SP0001–SP2000, mỗi sản phẩm đi qua 3–6 công đoạn theo thứ tự cố định.
- Mỗi bước có 1 máy chính (`machine_id`) và 1 máy dự phòng (`backup_machine_id`): máy dự phòng cùng công đoạn, khác máy chính, chọn ngẫu nhiên.
- "Chính/dự phòng" là vai trò theo từng sản phẩm, không phải thuộc tính cố định của máy: một máy có thể là máy chính của sản phẩm này và máy dự phòng của sản phẩm khác (mỗi máy là máy chính của 129–321 sản phẩm theo lần sinh trước đó).
- Nhánh B (SECOM) không có tầng Máy nên không có máy dự phòng.
- 50.000 đơn hàng (mỗi sản phẩm >= 1 đơn, TB 25 đơn/sản phẩm, lệch kiểu Dirichlet).
### Nhánh B (SECOM): Công đoạn -> Linh kiện -> Sản phẩm -> Đơn hàng (không có tầng Máy)
- 10 công đoạn PB01–PB10.
- 500 sản phẩm SPB001–SPB500, mỗi sản phẩm đi qua 3–6 công đoạn theo thứ tự PB01 -> PB10.
- 10.000 đơn hàng (TB 20 đơn/sản phẩm, min 1, max 140).
### Giới hạn cần nêu trong báo cáo
- Cấu trúc đồ thị, quy trình, đơn hàng đều là mô phỏng; chưa chứng minh trên dữ liệu Denso thật.
- AI4I là dữ liệu tổng hợp, mỗi dòng là một lượt vận hành rời rạc, không phải chuỗi thời gian theo máy.
- Timestamp AI4I là giả định; chưa có trọng số cạnh, tồn kho dự phòng, công suất máy.
- Máy dự phòng hiện chỉ là thông tin trong dữ liệu, chưa có công suất/tải: chưa mô hình hóa việc máy dự phòng quá tải khi nhận đơn thay máy chính (hướng mở rộng).

## 5. Kiểm tra khi nối vào pipeline (P5, 11/10/2026)
- Mọi `node_id` của 339 sự cố AI4I có trong `machines.csv`; mọi `node_id` của 104 sự cố SECOM có trong `routing_b.csv`.
- Mỗi máy là máy chính của 129–321 sản phẩm; mọi sản phẩm trong routing đều có đơn hàng (cả 2 nhánh).
- Cùng một mã linh kiện được làm trên nhiều máy (320 mã, 1.963 cặp linh kiện–máy) → trong đồ thị, node linh kiện nhánh A là `<mã>@<máy>` để sự cố một máy không lan sang sản phẩm làm trên máy khác.
- 276/339 sự cố AI4I trùng timestamp giả với sự cố khác (vì timestamp giả bắt đầu từ 2026-01-01 00:00 ở mọi máy) → nhiễu đồng thời trong E3 phụ thuộc mạnh vào giả định timestamp này.
- Hạn giao tính từ ngày tham chiếu 01/11/2026 (đơn sớm nhất).
