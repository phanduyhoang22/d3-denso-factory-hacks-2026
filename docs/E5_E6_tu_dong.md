# E5/E6 chấm tự động theo tiêu chí khách quan

Sinh bởi `scripts/auto_e5_e6.py` trên **toàn bộ 443 sự cố thật**, đồ thị đầy đủ. Chi tiết từng sự cố: `results/e5_tu_dong.csv`.

> Đây là kiểm tra **bằng dữ liệu**, không thay thế E5 do người chấm (`docs/E5_E6_phieu.md`) và không có số phút điều tra thủ công (cần phỏng vấn kỹ sư). Nó trả lời: hệ thống có làm *đúng điều nó tuyên bố* không.

## E5 – kết quả

| Câu | Tiêu chí kiểm | AI4I (339) | SECOM (104) |
|---|---|---|---|
| C1 | C1 · nguyên nhân #1 đúng nơi xảy ra sự cố | 46.9% (159/339) | 95.2% (99/104) |
| C1 | C1 · nơi xảy ra sự cố nằm trong top-3 | 88.2% (299/339) | 100.0% (104/104) |
| C2 | C2 · tập sản phẩm khớp đếm độc lập từ CSV | 100.0% (339/339) | 100.0% (104/104) |
| C2 | C2 · tập đơn hàng khớp đếm độc lập từ CSV | 100.0% (339/339) | 100.0% (104/104) |
| C3 | C3 · có hành động kiểm tra đúng node theo luật kb.yaml | 100.0% (339/339) | 100.0% (104/104) |
| C3 | C3 · máy dự phòng cùng công đoạn, khác máy lỗi | 100.0% (339/339) | không áp dụng (không có tầng máy) |
| C3 | C3 · 5 đơn ưu tiên đều thuộc tập bị ảnh hưởng | 100.0% (339/339) | 100.0% (104/104) |

Nhận xét:
- C1 sai ở 180 sự cố AI4I: hệ thống xếp một máy khác (cũng đang bất thường cùng lúc, cùng chuỗi tới đơn hàng) lên trên máy gốc. Đây là lỗi thật của truy vết ngược khi nhiều sự cố trùng thời điểm (timestamp giả dồn về 01/01 00:00), khớp với E3 trong `docs/KET_QUA_TONG_HOP.md`.
- C2 kiểm tính đúng của dựng đồ thị + truy xuôi so với dữ liệu gốc; không chứng minh độ chính xác ngoài thực tế.
- C3 chỉ kiểm hành động **hợp lệ về dữ liệu**; có *hợp lý về nghiệp vụ* hay không vẫn cần người chấm.

## E6 – khối lượng tra cứu thủ công vs. pipeline

Để tự xác định phạm vi ảnh hưởng của một sự cố, kỹ sư phải dò ít nhất các bảng sau (đếm từ dữ liệu):

| Nhánh | Bảng phải dò | Số dòng phải dò | Phạm vi trung bình phải liệt kê | Pipeline (trung vị / P95) |
|---|---|---|---|---|
| AI4I | máy → routing → đơn hàng | 59,082 | 179 sản phẩm, 4,447 đơn | 249 ms / 441 ms |
| SECOM | routing → đơn hàng | 12,237 | 223 sản phẩm, 4,412 đơn | 239 ms / 299 ms |

Số phút điều tra thủ công: **chưa có** – cần phỏng vấn kỹ sư (`docs/E5_E6_phieu.md`, mục E6). Khi có số, E6 = phút thủ công ÷ thời gian pipeline ở bảng trên.
