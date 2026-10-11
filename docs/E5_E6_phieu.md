# Phiếu E5 (chấm khuyến nghị) và E6 (thời gian điều tra)

Sinh tự động bởi `scripts/make_e5_sheet.py` từ pipeline tích hợp (module thật P1, P4) trên sự cố thật.
**Mỗi người chấm độc lập**, không xem phiếu của người khác trước khi chấm xong. Điền `Đ` (đúng), `S` (sai) hoặc `?` (không chắc) vào 3 câu cho mỗi kịch bản:

- **C1** Nguyên nhân xếp đầu có hợp lý không?
- **C2** Phạm vi ảnh hưởng (số linh kiện / sản phẩm / đơn) có hợp lý không?
- **C3** Hành động đề xuất có hợp lý **và làm được** không?

## K1. INC_A003 · M41 · OSF (Quá tải mô-men)

- Điểm bất thường 0.98; 6 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH02628**.
- Nguyên nhân khả dĩ: #1 M41 (0.98); #2 M21 (0.91); #3 M03 (0.50)
- Phạm vi ảnh hưởng: 1 công đoạn, 40 linh kiện, 182 sản phẩm, 4,410 đơn hàng.
- Rủi ro cao nhất: C718@M41 0.81; C705@M41 0.78; C703@M41 0.75; P7 0.72; C702@M41 0.71
- Hành động:
  1. [Bảo trì] Kiểm tra M41: Giảm tải, kiểm tra tool wear và mô-men — OSF: Quá tải (tool wear x mô-men vượt ngưỡng L/M/H)
  2. [Bảo trì] Chuyển cảnh báo tới: Kỹ thuật quy trình — sự cố OSF tại M41
  3. [Sản xuất] Chuyển tải sang M40 — nhận ít đơn nhất (682 đơn); tránh M45 (1028 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH19803, DH06515, DH00535, DH10409, DH31565 — điểm 0.43–0.41; 4/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 401 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 98250 sản phẩm; giải phóng năng lực cho đơn gấp

## K2. INC_A004 · M21 · OSF (Quá tải mô-men)

- Điểm bất thường 0.91; 6 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH02628**.
- Nguyên nhân khả dĩ: #1 M41 (0.98); #2 M21 (0.91); #3 M03 (0.50)
- Phạm vi ảnh hưởng: 1 công đoạn, 39 linh kiện, 151 sản phẩm, 4,274 đơn hàng.
- Rủi ro cao nhất: C440@M21 0.81; C414@M21 0.74; P4 0.72; C411@M21 0.70; C419@M21 0.70
- Hành động:
  1. [Bảo trì] Kiểm tra M21: Giảm tải, kiểm tra tool wear và mô-men — OSF: Quá tải (tool wear x mô-men vượt ngưỡng L/M/H)
  2. [Bảo trì] Chuyển cảnh báo tới: Kỹ thuật quy trình — sự cố OSF tại M21
  3. [Sản xuất] Chuyển tải sang M22 — nhận ít đơn nhất (635 đơn); tránh M26 (1174 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH39127, DH37600, DH24558, DH49295, DH37331 — điểm 0.62–0.59; 3/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 414 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 106721 sản phẩm; giải phóng năng lực cho đơn gấp

## K3. INC_A077 · M29 · HDF (Tản nhiệt kém)

- Điểm bất thường 0.97; 9 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH14042**.
- Nguyên nhân khả dĩ: #1 M29 (0.97); #2 M36 (0.50); #3 M21 (0.49)
- Phạm vi ảnh hưởng: 1 công đoạn, 38 linh kiện, 161 sản phẩm, 3,957 đơn hàng.
- Rủi ro cao nhất: C536@M29 0.81; C506@M29 0.77; C511@M29 0.77; C530@M29 0.77; C517@M29 0.73
- Hành động:
  1. [Bảo trì] Kiểm tra M29: Kiểm tra hệ thống làm mát, tăng tốc độ quay — HDF: Tản nhiệt kém (chênh nhiệt <8.6K, tốc độ <1380 rpm)
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì làm mát — sự cố HDF tại M29
  3. [Sản xuất] Chuyển tải sang M30 — nhận ít đơn nhất (567 đơn); tránh M31 (1095 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH14531, DH22373, DH28603, DH46661, DH45465 — điểm 0.63–0.61; 3/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 369 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 96914 sản phẩm; giải phóng năng lực cho đơn gấp

## K4. INC_A089 · M09 · HDF (Tản nhiệt kém)

- Điểm bất thường 0.57; 31 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH00634**.
- Nguyên nhân khả dĩ: #1 M40 (0.86); #2 M09 (0.57); #3 M05 (0.50)
- Phạm vi ảnh hưởng: 1 công đoạn, 38 linh kiện, 137 sản phẩm, 2,998 đơn hàng.
- Rủi ro cao nhất: C202@M09 0.81; C219@M09 0.81; C227@M09 0.81; C204@M09 0.76; C207@M09 0.76
- Hành động:
  1. [Bảo trì] Kiểm tra M09: Kiểm tra hệ thống làm mát, tăng tốc độ quay — HDF: Tản nhiệt kém (chênh nhiệt <8.6K, tốc độ <1380 rpm)
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì làm mát — sự cố HDF tại M09
  3. [Sản xuất] Chuyển tải sang M12 — nhận ít đơn nhất (358 đơn); tránh M08 (825 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH49536, DH49333, DH04604, DH45361, DH37728 — điểm 0.65–0.64; 5/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 334 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 84099 sản phẩm; giải phóng năng lực cho đơn gấp

## K5. INC_A000 · M03 · PWF (Lỗi công suất)

- Điểm bất thường 0.99; 1 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH08376**.
- Nguyên nhân khả dĩ: #1 M03 (0.99); #2 M47 (0.23)
- Phạm vi ảnh hưởng: 1 công đoạn, 39 linh kiện, 277 sản phẩm, 6,467 đơn hàng.
- Rủi ro cao nhất: C101@M03 0.81; C126@M03 0.78; C125@M03 0.76; C135@M03 0.76; C102@M03 0.73
- Hành động:
  1. [Bảo trì] Kiểm tra M03: Kiểm tra nguồn điện, mô-men và tốc độ — PWF: Công suất ngoài 3500-9000 W
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì điện — sự cố PWF tại M03
  3. [Sản xuất] Chuyển tải sang M02 — nhận ít đơn nhất (1051 đơn); tránh M04 (1577 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH14042, DH02855, DH27664, DH02610, DH18493 — điểm 0.65–0.65; 5/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 680 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 173452 sản phẩm; giải phóng năng lực cho đơn gấp

## K6. INC_A005 · M35 · PWF (Lỗi công suất)

- Điểm bất thường 0.93; 6 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH01307**.
- Nguyên nhân khả dĩ: #1 M35 (0.93); #2 M03 (0.50); #3 M41 (0.49)
- Phạm vi ảnh hưởng: 1 công đoạn, 40 linh kiện, 142 sản phẩm, 3,485 đơn hàng.
- Rủi ro cao nhất: C604@M35 0.81; C625@M35 0.81; C602@M35 0.76; C610@M35 0.76; C626@M35 0.76
- Hành động:
  1. [Bảo trì] Kiểm tra M35: Kiểm tra nguồn điện, mô-men và tốc độ — PWF: Công suất ngoài 3500-9000 W
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì điện — sự cố PWF tại M35
  3. [Sản xuất] Chuyển tải sang M38 — nhận ít đơn nhất (432 đơn); tránh M39 (711 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH49295, DH06540, DH18237, DH22826, DH48975 — điểm 0.45–0.43; 3/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 322 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 84631 sản phẩm; giải phóng năng lực cho đơn gấp

## K7. INC_A002 · M47 · TWF (Mòn dao)

- Điểm bất thường 0.47; 1 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH01307**.
- Nguyên nhân khả dĩ: #1 M03 (0.50); #2 M47 (0.47)
- Phạm vi ảnh hưởng: 1 công đoạn, 40 linh kiện, 321 sản phẩm, 8,408 đơn hàng.
- Rủi ro cao nhất: C806@M47 0.81; C838@M47 0.81; C814@M47 0.79; C819@M47 0.79; C805@M47 0.76
- Hành động:
  1. [Bảo trì] Kiểm tra M47: Thay dao / kiểm tra tool wear — TWF: Dao mòn (tool wear ~200-250 phút)
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì cơ khí — sự cố TWF tại M47
  3. [Sản xuất] Chuyển tải sang M48 — nhận ít đơn nhất (1989 đơn); tránh M50 (2345 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH10235, DH19812, DH48975, DH28968, DH32339 — điểm 0.22–0.21; 5/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 855 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 214890 sản phẩm; giải phóng năng lực cho đơn gấp

## K8. INC_A025 · M38 · TWF (Mòn dao)

- Điểm bất thường 0.69; 13 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH01588**.
- Nguyên nhân khả dĩ: #1 M09 (0.95); #2 M38 (0.69); #3 M34 (0.50)
- Phạm vi ảnh hưởng: 1 công đoạn, 40 linh kiện, 152 sản phẩm, 3,668 đơn hàng.
- Rủi ro cao nhất: C627@M38 0.81; C635@M38 0.81; C602@M38 0.76; C609@M38 0.76; C614@M38 0.76
- Hành động:
  1. [Bảo trì] Kiểm tra M38: Thay dao / kiểm tra tool wear — TWF: Dao mòn (tool wear ~200-250 phút)
  2. [Bảo trì] Chuyển cảnh báo tới: Bảo trì cơ khí — sự cố TWF tại M38
  3. [Sản xuất] Chuyển tải sang M39 — nhận ít đơn nhất (365 đơn); tránh M34 (784 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH36911, DH14935, DH05166, DH03502, DH42541 — điểm 0.64–0.60; 4/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 366 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 94605 sản phẩm; giải phóng năng lực cho đơn gấp

## K9. INC_A001 · M34 · PWF+OSF (Quá tải mô-men (+PWF))

- Điểm bất thường 0.97; 2 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH12434**.
- Nguyên nhân khả dĩ: #1 M34 (0.97); #2 M03 (0.50); #3 M47 (0.23)
- Phạm vi ảnh hưởng: 1 công đoạn, 38 linh kiện, 144 sản phẩm, 4,195 đơn hàng.
- Rủi ro cao nhất: C628@M34 0.81; P6 0.72; C618@M34 0.68; C605@M34 0.65; C616@M34 0.65
- Hành động:
  1. [Bảo trì] Kiểm tra M34: Kiểm tra nguồn điện, mô-men và tốc độ — PWF: Công suất ngoài 3500-9000 W
  2. [Bảo trì] Kiểm tra M34: Giảm tải, kiểm tra tool wear và mô-men — OSF: Quá tải (tool wear x mô-men vượt ngưỡng L/M/H)
  3. [Bảo trì] Chuyển cảnh báo tới: Bảo trì điện — sự cố PWF+OSF tại M34
  4. [Bảo trì] Chuyển cảnh báo tới: Kỹ thuật quy trình — sự cố PWF+OSF tại M34
  5. [Sản xuất] Chuyển tải sang M36 — nhận ít đơn nhất (487 đơn); tránh M39 (847 đơn). Chưa mô hình hóa công suất máy dự phòng
  6. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH12041, DH19728, DH13262, DH35378, DH35902 — điểm 0.46–0.45; 2/5 đơn ưu tiên Cao
  7. [Kinh doanh] Cân nhắc dời lịch 397 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 97826 sản phẩm; giải phóng năng lực cho đơn gấp

## K10. INC_A039 · M24 · UNKNOWN (Lỗi máy không rõ chế độ)

- Điểm bất thường 0.15; 18 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DH01812**.
- Nguyên nhân khả dĩ: #1 M06 (0.99); #2 M34 (0.50); #3 M14 (0.50)
- Phạm vi ảnh hưởng: 1 công đoạn, 40 linh kiện, 154 sản phẩm, 4,544 đơn hàng.
- Rủi ro cao nhất: C419@M24 0.81; C406@M24 0.73; C410@M24 0.73; C428@M24 0.73; C437@M24 0.73
- Hành động:
  1. [Bảo trì] Kiểm tra M24: Kỹ sư kiểm tra thủ công — UNKNOWN: Không rõ chế độ lỗi (gồm RNF)
  2. [Bảo trì] Chuyển cảnh báo tới: Kỹ sư chuyên trách — sự cố UNKNOWN tại M24
  3. [Sản xuất] Chuyển tải sang M23 — nhận ít đơn nhất (616 đơn); tránh M26 (1215 đơn). Chưa mô hình hóa công suất máy dự phòng
  4. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DH28705, DH40043, DH18395, DH03215, DH12456 — điểm 0.64–0.60; 3/5 đơn ưu tiên Cao
  5. [Kinh doanh] Cân nhắc dời lịch 431 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 105792 sản phẩm; giải phóng năng lực cho đơn gấp

## K11. INC_B339 · PB04 · SECOM_FAIL (Lô bán dẫn không đạt QC)

- Điểm bất thường 1.00; 0 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DHB02223**.
- Nguyên nhân khả dĩ: #1 PB04 (1.00)
- Phạm vi ảnh hưởng: 30 linh kiện, 212 sản phẩm, 4,338 đơn hàng.
- Rủi ro cao nhất: CB0410 0.90; CB0411 0.90; CB0430 0.87; CB0420 0.84; CB0428 0.82
- Hành động:
  1. [Chất lượng] Kiểm tra PB04: Rà soát cảm biến lệch nhiều nhất tại công đoạn này — SECOM_FAIL: Lô SECOM fail, không có chế độ lỗi
  2. [Chất lượng] Chuyển cảnh báo tới: Kỹ thuật quy trình — sự cố SECOM_FAIL tại PB04
  3. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DHB01585, DHB01584, DHB04097, DHB07326, DHB09359 — điểm 0.72–0.69; 5/5 đơn ưu tiên Cao
  4. [Kinh doanh] Cân nhắc dời lịch 469 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 118868 sản phẩm; giải phóng năng lực cho đơn gấp

## K12. INC_B340 · PB02 · SECOM_FAIL (Lô bán dẫn không đạt QC)

- Điểm bất thường 1.00; 0 sự cố khác cùng lúc (cửa sổ 2 giờ). Kết quả xấu dùng để truy ngược: **DHB06033**.
- Nguyên nhân khả dĩ: #1 PB02 (1.00)
- Phạm vi ảnh hưởng: 30 linh kiện, 223 sản phẩm, 4,418 đơn hàng.
- Rủi ro cao nhất: CB0228 0.90; CB0205 0.84; CB0214 0.84; CB0215 0.82; CB0216 0.82
- Hành động:
  1. [Chất lượng] Kiểm tra PB02: Rà soát cảm biến lệch nhiều nhất tại công đoạn này — SECOM_FAIL: Lô SECOM fail, không có chế độ lỗi
  2. [Chất lượng] Chuyển cảnh báo tới: Kỹ thuật quy trình — sự cố SECOM_FAIL tại PB02
  3. [Kế hoạch] Ưu tiên giữ tiến độ 5 đơn rủi ro cao nhất: DHB06863, DHB08328, DHB05757, DHB05196, DHB04982 — điểm 0.72–0.72; 5/5 đơn ưu tiên Cao
  4. [Kinh doanh] Cân nhắc dời lịch 474 đơn ưu tiên Thấp có hạn giao ≥ 60 ngày — tổng 121600 sản phẩm; giải phóng năng lực cho đơn gấp

## Bảng chấm

| Kịch bản | P1 Việt C1/C2/C3 | P2 Thành C1/C2/C3 | P3 Tình C1/C2/C3 | P4 Trang C1/C2/C3 | P5 Phan Hoàng C1/C2/C3 | Ghi chú |
|---|---|---|---|---|---|---|
| K1 INC_A003 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K2 INC_A004 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K3 INC_A077 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K4 INC_A089 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K5 INC_A000 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K6 INC_A005 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K7 INC_A002 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K8 INC_A025 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K9 INC_A001 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K10 INC_A039 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K11 INC_B339 |  / /  |  / /  |  / /  |  / /  |  / /  | |
| K12 INC_B340 |  / /  |  / /  |  / /  |  / /  |  / /  | |

Tổng hợp E5 (điền sau khi chấm): với mỗi câu C1–C3, tỷ lệ `Đ` = số ô Đ / số ô đã chấm (bỏ `?`); mức đồng thuận = tỷ lệ kịch bản mà mọi người cùng một đáp án. Cần ít nhất 2 người chấm.

# E6 – Thời gian điều tra

Thời gian pipeline đo được (phát hiện → truy xuôi → chấm rủi ro → truy ngược → đề xuất; không tính bước dựng đồ thị):

| Nhánh | Số sự cố | Trung vị | P95 |
|---|---|---|---|
| AI4I | 339 | 293 ms | 625 ms |
| SECOM | 104 | 341 ms | 465 ms |

Thời gian điều tra thủ công (điền từ phỏng vấn, phiếu câu hỏi ở `p2_secom_impact/p2_phieu_phong_van_E6_E5.md`, mục A):

| Kỹ sư (tên, vai trò, ngày) | Xác định đối tượng bị ảnh hưởng (phút) | Xác định nguyên nhân (phút) |
|---|---|---|
| | | |
| | | |

Kết luận E6 = thời gian thủ công / thời gian pipeline. **Không điền số ước đoán**: chỉ dùng số từ phỏng vấn và ghi rõ nguồn.
