# E5/E6 – Đánh giá sơ bộ theo góc nhìn chuyên gia

> **Nguồn và giới hạn – phải ghi khi trích dẫn:** đánh giá sơ bộ theo góc nhìn của một kỹ sư sản xuất/bảo trì,
> thực hiện ngày 12/10/2026 trên output hệ thống trong `docs/E5_E6_phieu.md`. Đây **chưa phải** phiếu chấm độc lập
> của từng thành viên và **chưa phải** số liệu phỏng vấn kỹ sư DENSO; khi có hai nguồn đó thì thay thế hoặc đặt cạnh.
> Phần kiểm tra khách quan bằng dữ liệu trên toàn bộ 443 sự cố: `docs/E5_E6_tu_dong.md`.

Thang chấm: **Đ** đúng/hợp lý · **S** sai/không hợp lý · **?** chấp nhận được nhưng có điều kiện.

## E5 – Chấm 12 kịch bản

| # | Sự cố | C1 Nguyên nhân #1 | C2 Phạm vi | C3 Hành động | Lý do chính |
|---|---|---|---|---|---|
| K1 | INC_A003 · M41 · OSF | **Đ** | **?** | **Đ** | Nguyên nhân đúng dù có M21, M03 bất thường cùng lúc. Kiểm tra mòn dao × mô-men đúng bản chất OSF. Phạm vi 4.410 đơn là *mức phơi nhiễm*, chưa phải số đơn thực sự trễ |
| K2 | INC_A004 · M21 · OSF | **S** | **?** | **Đ** | Xếp M41 trên M21 (máy gốc) vì M41 bất thường cùng lúc và cùng chuỗi tới DH02628. Hành động vẫn đúng vì gắn với node báo lỗi M21 |
| K3 | INC_A077 · M29 · HDF | **Đ** | **?** | **Đ** | Đúng máy, khoảng cách điểm rõ (0,87 vs 0,49). Kiểm tra làm mát + chuyển cảnh báo Bảo trì làm mát là đúng quy trình |
| K4 | INC_A089 · M09 · HDF | **S** | **?** | **Đ** | Điểm bất thường M09 chỉ 0,57 giữa 31 cảnh báo khác → M09 xếp #2 sau M40 (0,86). Detector yếu là gốc rễ, không phải đồ thị |
| K5 | INC_A000 · M03 · PWF | **Đ** | **?** | **Đ** | Tín hiệu rõ (0,99), ít nhiễu. Chuyển cảnh báo Bảo trì điện đúng |
| K6 | INC_A005 · M35 · PWF | **Đ** | **?** | **Đ** | Đúng máy, tách biệt rõ với nhiễu |
| K7 | INC_A002 · M47 · TWF | **S** | **S** | **S** | Điểm TWF của M47 chỉ 0,47 nên M03 (0,50) vượt lên – mòn dao khó phát hiện từ cảm biến. Thay dao là việc ~10–20 phút; báo 8.408 đơn bị ảnh hưởng và đề xuất dời lịch 855 đơn là **phản ứng quá mức** |
| K8 | INC_A025 · M38 · TWF | **S** | **S** | **?** | Xếp M09 trên M38. Phạm vi quá rộng cho một lần thay dao; hành động trên M38 vẫn đúng |
| K9 | INC_A001 · M34 · PWF+OSF | **Đ** | **?** | **Đ** | Xử lý lỗi chồng tốt: hai luật kiểm tra, hai bộ phận. Có thể gộp hai cảnh báo thành một phiếu |
| K10 | INC_A039 · M24 · UNKNOWN | **S** | **?** | **S** | Điểm bất thường 0,11: tín hiệu gần như bình thường nhưng vẫn kích hoạt chuyển tải và dời lịch. Cần ngưỡng mức độ trước khi đề xuất hành động lớn |
| K11 | INC_B339 · PB04 · SECOM | **Đ** | **S** | **?** | Một lô bán dẫn fail chỉ ảnh hưởng lô đó, không phải mọi đơn tương lai qua PB04 (4.338 đơn). Thiếu hành động đầu tiên đúng chuẩn: **giữ (hold) và cách ly lô** |
| K12 | INC_B340 · PB02 · SECOM | **Đ** | **S** | **?** | Như K11 |

### Tổng hợp E5 (đánh giá sơ bộ)

| Câu | Đ | ? | S | Tỷ lệ Đ |
|---|---|---|---|---|
| C1 Nguyên nhân | 7 | 0 | 5 | 58% |
| C2 Phạm vi | 0 | 8 | 4 | 0% (8/12 chấp nhận có điều kiện) |
| C3 Hành động | 7 | 3 | 2 | 58% (83% nếu tính cả ?) |

Đối chiếu với kiểm tra dữ liệu trên 443 sự cố (`docs/E5_E6_tu_dong.md`): C1 top-1 đúng 47% (AI4I) / 95% (SECOM);
phạm vi và hành động hợp lệ về dữ liệu 100%. Mẫu 12 kịch bản cho C1 cao hơn trung bình vì có sự cố demo và SECOM. Chấm lại ngày 12/10 sau khi P1 đổi bộ phát hiện chính (Isolation Forest + đặc trưng vật lý).

### Nhận định của chuyên gia

1. **Điểm mạnh:** truy xuôi đúng về cấu trúc; hành động gắn đúng luật theo chế độ lỗi và đúng bộ phận; xử lý được lỗi
   chồng; máy dự phòng hợp lệ. Đây là phần kỹ sư dùng được ngay.
2. **Điểm yếu lớn nhất – phạm vi không có chiều thời gian.** Hệ thống liệt kê *mọi* đơn tương lai của sản phẩm làm trên
   máy lỗi (~4.400 đơn, hạn tới 90 ngày). Thực tế mức ảnh hưởng phụ thuộc **thời gian dừng** (thay dao 15 phút khác
   hỏng nguồn 4 giờ) và **đệm WIP**. Cần lọc theo `thời gian dừng ước tính × tốc độ sản xuất` và cửa sổ hạn giao
   gần (P2 đã có mô hình `downtime_min`, `buffer` – nên đưa vào pipeline tích hợp).
3. **Hành động phải tỷ lệ với mức nghiêm trọng.** K7, K10: tín hiệu nhẹ vẫn sinh "dời lịch hàng trăm đơn".
   Đề xuất: chỉ đề xuất chuyển tải/dời lịch khi mức độ ≥ trung bình hoặc thời gian dừng ước tính > đệm.
4. **Truy ngược thua khi nhiều cảnh báo trùng thời điểm** (K2, K4, K8, K10) **và với lỗi mòn dao** (K7: TWF khó thấy trên cảm biến). Gốc rễ: detector báo sai nhiều và
   timestamp giả dồn về cùng thời điểm. Đề xuất: ưu tiên cảnh báo xảy ra **trước** kết quả xấu theo thứ tự thời gian,
   và cộng điểm khi chế độ lỗi phù hợp với triệu chứng của kết quả xấu.
5. **SECOM:** thêm hành động chuẩn "hold & cách ly lô" ở vị trí #1; phạm vi nên là sản phẩm của **lô** đó.

## E6 – Thời gian điều tra: ước tính của chuyên gia

> Ước tính có lập luận theo quy trình điển hình ở nhà máy có MES/ERP tách rời; **chưa kiểm chứng bằng phỏng vấn**.
> Trình bày dạng khoảng, không phải một con số.

Quy trình thủ công khi một máy báo lỗi (khối lượng dữ liệu lấy từ `docs/E5_E6_tu_dong.md`):

| Bước | Việc kỹ sư làm | Ước tính |
|---|---|---|
| 1 | Xác nhận cảnh báo, xem trend cảm biến trên SCADA/HMI | 5–15 phút |
| 2 | Tra MES: máy đang chạy lệnh nào, sản phẩm nào dùng máy này (~180 sản phẩm) | 10–20 phút |
| 3 | Xuất danh sách lệnh/sản phẩm, đối chiếu ERP để ra đơn hàng (~4.400 đơn), lọc theo hạn giao | 20–45 phút |
| 4 | Xếp ưu tiên đơn, gọi Kế hoạch / Kinh doanh xác nhận | 15–30 phút |
| **A** | **Xác định phạm vi ảnh hưởng (1–4)** | **50–110 phút** |
| 5 | Khi có nhiều cảnh báo cùng lúc: rà lịch sử bảo trì, so sánh từng máy, loại trừ | 30–120 phút |
| **B** | **Xác định nguyên nhân khả dĩ (1 + 5)** | **35–135 phút** |

So với pipeline (đo được, `results/`): trung vị **0,24–0,48 giây** mỗi sự cố, P95 < 1 giây.

| | Thủ công (ước tính chuyên gia) | Pipeline (đo) | Tỷ lệ |
|---|---|---|---|
| Xác định phạm vi | 50–110 phút | < 1 giây | nhanh hơn ~3.000–13.000 lần |
| Thời gian ra quyết định ban đầu (A + B song song) | ~1–2 giờ | < 1 giây + thời gian kỹ sư đọc kết quả (~5–10 phút) | rút ngắn **~85–95%** thời gian tới quyết định |

Cách trình bày khuyến nghị: dùng con số **"rút ngắn ~85–95% thời gian tới quyết định ban đầu"** (đã tính thời gian
kỹ sư đọc và xác nhận kết quả), không dùng tỷ lệ hàng nghìn lần vì nó bỏ qua phần việc của con người.
Ghi chú nguồn: "ước tính theo quy trình điển hình, chưa phỏng vấn kỹ sư DENSO".
