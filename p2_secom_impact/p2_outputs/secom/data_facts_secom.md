# data_facts – SECOM (đếm trực tiếp từ file)

Nguồn file: secom.data, secom_labels.data (UCI ID 179). Mọi số dưới đây được đếm lại bởi `p2_secom.py`, không lấy từ mô tả.

| Mục | Giá trị |
|---|---|
| Số dòng | 1567 |
| Số cảm biến | 590 |
| Dòng fail (nhãn 1) | 104 (6.64%) |
| Dòng pass (nhãn −1) | 1463 |
| Khoảng thời gian (timestamp THẬT) | 2008-07-19 11:55:00 đến 2008-10-17 06:07:00 |
| Timestamp trùng nhau | 33 |
| Tỷ lệ ô thiếu | 4.54% |
| Cột thiếu > 40% | 32 |
| Cột hằng số | 116 |
| Dòng có ít nhất 1 ô thiếu | 100% |

Chia train/validation/test theo thời gian (không xáo trộn):

| Tập | Dòng | Fail | Từ | Đến |
|---|---|---|---|---|
| train | 940 | 76 | 2008-07-19 11:55:00 | 2008-09-20 05:34:00 |
| val | 313 | 11 | 2008-09-20 06:08:00 | 2008-10-02 19:25:00 |
| test | 314 | 17 | 2008-10-02 20:54:00 | 2008-10-17 06:07:00 |

Tiền xử lý (chỉ fit trên train):

- Bỏ cột thiếu > 40% (tính trên train): còn 562 cột.
- Bỏ cột hằng số trên train: còn 440 cột.
- PCA giữ 90% phương sai: **121 thành phần** (từ 590 chiều).

Lưu ý: số fail ở validation và test rất ít, nên chỉ số E0 trên SECOM dao động mạnh; báo cáo kèm khoảng tin cậy bootstrap.
