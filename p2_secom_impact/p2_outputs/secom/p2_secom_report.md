# D3 – P2: kết quả thí nghiệm E1–E4 (SECOM)

30 seed × 3 quy mô × 3 mức confounder × 4 mức xóa cạnh = 1080 dòng trong `p2_results.csv`. Số liệu là mean ± std qua seed (E1/E2 không phụ thuộc confounder nên lặp lại qua 3 mức confounder, không đổi mean/std).

## Điều kiện thí nghiệm (đọc trước khi trích số)

- Phát hiện: SECOM chia THEO THỜI GIAN 60/20/20 (train 940 dòng/76 fail; validation 313/11; test 314/17). Tiền xử lý fit trên train: 562 cột sau lọc thiếu, 440 sau lọc hằng số, PCA 121 thành phần. Mô hình sinh sự cố: Isolation Forest trên PCA, ngưỡng cố định recall 90% trên validation (chỉ 11 fail nên ngưỡng không ổn định). Trên test: recall thực 0.941, tỷ lệ báo sai 0.933. Timestamp trong kịch bản đồ thị là timestamp giả theo kịch bản (các dòng SECOM được gắn vào máy khác nhau nên không chung một dòng thời gian). SECOM không có kiểu lỗi và thời gian dừng: dùng hằng số giả định 45 phút, mức nghiêm trọng = điểm bất thường.
- Mọi sự cố là dòng lỗi THẬT của SECOM (tập test); cấu trúc đồ thị, trọng số, đệm, đơn hàng là MÔ PHỎNG, sinh độc lập với sự cố.
- Ground truth tác động dùng mô hình dòng chảy khác công thức của hệ thống (đệm trừ phút, gộp noisy-OR, thời gian dừng và hằng số bù trễ thật). Hệ thống chỉ thấy đồ thị với trọng số/đệm có nhiễu và bị xóa cạnh.
- Confounder chỉ được đặt ở máy KHÔNG nằm trong tổ tiên của kết quả xấu (đúng thiết kế 18.3). Vì cạnh chỉ bị xóa chứ không thêm cạnh sai, đồ thị không bao giờ nối nhầm confounder vào kết quả xấu: E3 ở mức xóa 0% gần như dễ theo cấu trúc, phần có giá trị là E4.
- Điểm truy vết ngược = pct_bất_thường × (λ + (1−λ)·reach), λ = 0.5 đặt TRƯỚC khi chạy; bảng độ nhạy λ ở cuối chỉ để tham khảo.
- Kết quả theo quy mô đồ thị mô phỏng tự đặt; chưa chứng minh trên dữ liệu DENSO.

## E1 – Truy vết xuôi (pooled 4 tầng) theo % cạnh bị xóa (E4)

| Xóa cạnh | Hệ thống P | Hệ thống R | Hệ thống F1 | Cục bộ P | Cục bộ R | Cục bộ F1 |
|---|---|---|---|---|---|---|
| 0% | 0.988 ± 0.049 | 0.815 ± 0.163 | 0.883 ± 0.112 | 1.000 ± 0.000 | 0.122 ± 0.050 | 0.214 ± 0.080 |
| 10% | 0.932 ± 0.232 | 0.618 ± 0.289 | 0.708 ± 0.278 | 0.944 ± 0.229 | 0.114 ± 0.056 | 0.201 ± 0.092 |
| 25% | 0.717 ± 0.446 | 0.339 ± 0.313 | 0.424 ± 0.349 | 0.722 ± 0.449 | 0.091 ± 0.071 | 0.159 ± 0.120 |
| 50% | 0.522 ± 0.500 | 0.138 ± 0.210 | 0.196 ± 0.257 | 0.522 ± 0.500 | 0.060 ± 0.068 | 0.105 ± 0.117 |

Recall theo tầng (hệ thống), theo % cạnh bị xóa:

| Xóa cạnh | Công đoạn | Linh kiện | Sản phẩm | Đơn hàng |
|---|---|---|---|---|
| 0% | 0.992 ± 0.060 | 0.961 ± 0.117 | 0.871 ± 0.270 | 0.314 ± 0.424 |
| 10% | 0.878 ± 0.286 | 0.795 ± 0.364 | 0.612 ± 0.407 | 0.167 ± 0.348 |
| 25% | 0.605 ± 0.438 | 0.463 ± 0.464 | 0.315 ± 0.391 | 0.039 ± 0.166 |
| 50% | 0.383 ± 0.433 | 0.177 ± 0.348 | 0.076 ± 0.212 | 0.031 ± 0.159 |

Theo quy mô đồ thị (Recall hệ thống, ở 0% / 25% / 50% xóa):

| Quy mô | 0% | 25% | 50% |
|---|---|---|---|
| small | 0.841 ± 0.123 | 0.474 ± 0.332 | 0.218 ± 0.279 |
| medium | 0.860 ± 0.150 | 0.290 ± 0.292 | 0.132 ± 0.186 |
| large | 0.744 ± 0.187 | 0.253 ± 0.268 | 0.064 ± 0.091 |

## E2 – Điểm rủi ro vs mức ảnh hưởng thật

| Xóa cạnh | Spearman hệ thống | Spearman chỉ-số-bước | Top-3 đơn hệ thống | Top-3 đơn chỉ-số-bước |
|---|---|---|---|---|
| 0% | 0.941 ± 0.071 | 0.790 ± 0.069 | 0.796 ± 0.237 | 0.215 ± 0.240 |
| 10% | 0.790 ± 0.192 | 0.602 ± 0.179 | 0.593 ± 0.333 | 0.215 ± 0.230 |
| 25% | 0.631 ± 0.199 | 0.499 ± 0.153 | 0.307 ± 0.287 | 0.181 ± 0.218 |
| 50% | 0.472 ± 0.195 | 0.437 ± 0.162 | 0.237 ± 0.255 | 0.222 ± 0.244 |

## E3 – Truy vết ngược: Top-1 của máy gốc theo confounder × xóa cạnh

| Confounder | Xóa cạnh | Top-1 hệ thống | Top-3 hệ thống | Top-1 baseline bất thường | Top-1 baseline gần nhất |
|---|---|---|---|---|---|
| 0% | 0% | 0.233 ± 0.425 | 0.389 ± 0.490 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 0% | 10% | 0.144 ± 0.354 | 0.333 ± 0.474 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 0% | 25% | 0.100 ± 0.302 | 0.233 ± 0.425 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 0% | 50% | 0.056 ± 0.230 | 0.139 ± 0.344 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 25% | 0% | 0.233 ± 0.425 | 0.389 ± 0.490 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 25% | 10% | 0.144 ± 0.354 | 0.333 ± 0.474 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 25% | 25% | 0.100 ± 0.302 | 0.233 ± 0.425 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 25% | 50% | 0.056 ± 0.230 | 0.139 ± 0.344 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 50% | 0% | 0.233 ± 0.425 | 0.389 ± 0.490 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 50% | 10% | 0.144 ± 0.354 | 0.333 ± 0.474 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 50% | 25% | 0.100 ± 0.302 | 0.233 ± 0.425 | 0.022 ± 0.148 | 0.044 ± 0.207 |
| 50% | 50% | 0.056 ± 0.230 | 0.139 ± 0.344 | 0.022 ± 0.148 | 0.044 ± 0.207 |

Top-1 của baseline 'bất thường cao nhất' bị chặn trên bởi việc bộ phát hiện có chấm điểm máy gốc cao nhất hay không (máy gốc bị phát hiện trong 95.6% kịch bản).

## Kiểm tra tiêu chí thành công (15.5): hệ thống có vượt baseline khi thiếu cạnh?

Hiệu hệ thống − baseline, ghép cặp theo (seed, quy mô), kèm khoảng tin cậy 95% và tỷ lệ seed thắng/thua.

| Chỉ số | Xóa cạnh | Hiệu (hệ thống − baseline) | % seed thắng | % seed thua |
|---|---|---|---|---|
| E1 Recall | 0% | +0.693 ± 0.031 | 100% | 0% |
| E1 Recall | 10% | +0.503 ± 0.054 | 87% | 0% |
| E1 Recall | 25% | +0.248 ± 0.055 | 54% | 0% |
| E1 Recall | 50% | +0.078 ± 0.034 | 26% | 0% |
| E2 Spearman | 0% | +0.151 ± 0.018 | 96% | 4% |
| E2 Spearman | 10% | +0.187 ± 0.025 | 82% | 3% |
| E2 Spearman | 25% | +0.132 ± 0.031 | 44% | 2% |
| E2 Spearman | 50% | +0.035 ± 0.021 | 13% | 1% |
| E2 Top-3 đơn | 0% | +0.581 ± 0.063 | 88% | 0% |
| E2 Top-3 đơn | 10% | +0.378 ± 0.068 | 68% | 1% |
| E2 Top-3 đơn | 25% | +0.126 ± 0.048 | 29% | 1% |
| E2 Top-3 đơn | 50% | +0.015 ± 0.014 | 4% | 0% |

| So sánh | Confounder | Xóa cạnh | Hiệu Top-1 | % seed thắng | % seed thua |
|---|---|---|---|---|---|
| E3 vs bất thường cao nhất | 25% | 0% | +0.211 ± 0.085 | 21% | 0% |
| E3 vs bất thường cao nhất | 25% | 10% | +0.122 ± 0.075 | 13% | 1% |
| E3 vs bất thường cao nhất | 25% | 25% | +0.078 ± 0.056 | 8% | 0% |
| E3 vs bất thường cao nhất | 25% | 50% | +0.033 ± 0.037 | 3% | 0% |
| E3 vs bất thường cao nhất | 50% | 0% | +0.211 ± 0.085 | 21% | 0% |
| E3 vs bất thường cao nhất | 50% | 10% | +0.122 ± 0.075 | 13% | 1% |
| E3 vs bất thường cao nhất | 50% | 25% | +0.078 ± 0.056 | 8% | 0% |
| E3 vs bất thường cao nhất | 50% | 50% | +0.033 ± 0.037 | 3% | 0% |
| E3 vs gần nhất | 25% | 0% | +0.189 ± 0.087 | 20% | 1% |
| E3 vs gần nhất | 25% | 10% | +0.100 ± 0.082 | 13% | 3% |
| E3 vs gần nhất | 25% | 25% | +0.056 ± 0.072 | 9% | 3% |
| E3 vs gần nhất | 25% | 50% | +0.011 ± 0.058 | 4% | 3% |
| E3 vs gần nhất | 50% | 0% | +0.189 ± 0.087 | 20% | 1% |
| E3 vs gần nhất | 50% | 10% | +0.100 ± 0.082 | 13% | 3% |
| E3 vs gần nhất | 50% | 25% | +0.056 ± 0.072 | 9% | 3% |
| E3 vs gần nhất | 50% | 50% | +0.011 ± 0.058 | 4% | 3% |

## Kết luận

- E1 Recall ở 0% xóa cạnh: hệ thống 0.815 vs baseline 0.122 (hiệu +0.693, CI95 ±0.031) -> vượt baseline có ý nghĩa thống kê.
- E1 Recall ở 25% xóa cạnh: hệ thống 0.339 vs baseline 0.091 (hiệu +0.248, CI95 ±0.055) -> vượt baseline có ý nghĩa thống kê.
- E1 Recall ở 50% xóa cạnh: hệ thống 0.138 vs baseline 0.060 (hiệu +0.078, CI95 ±0.034) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 0% xóa cạnh: hệ thống 0.941 vs baseline 0.790 (hiệu +0.151, CI95 ±0.018) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 25% xóa cạnh: hệ thống 0.631 vs baseline 0.499 (hiệu +0.132, CI95 ±0.031) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 50% xóa cạnh: hệ thống 0.472 vs baseline 0.437 (hiệu +0.035, CI95 ±0.021) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 0% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.233 vs 0.022 (hiệu +0.211, CI95 ±0.085) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 25% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.100 vs 0.022 (hiệu +0.078, CI95 ±0.056) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 50% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.056 vs 0.022 (hiệu +0.033, CI95 ±0.037) -> KHÔNG vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 0% xóa cạnh vs baseline gần nhất: hệ thống 0.233 vs 0.044 (hiệu +0.189, CI95 ±0.087) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 25% xóa cạnh vs baseline gần nhất: hệ thống 0.100 vs 0.044 (hiệu +0.056, CI95 ±0.072) -> KHÔNG vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 50% xóa cạnh vs baseline gần nhất: hệ thống 0.056 vs 0.044 (hiệu +0.011, CI95 ±0.058) -> KHÔNG vượt baseline có ý nghĩa thống kê.

Recall truy vết xuôi giảm từ 0.815 (đồ thị đủ) xuống 0.138 (thiếu 50% cạnh). Nếu dữ liệu DENSO thiếu nhiều quan hệ phụ thuộc, đây là mức suy giảm cần kỳ vọng; không nên trình bày số ở 0% như hiệu năng thực tế. Precision được tính bằng 0 khi hệ thống không cảnh báo đối tượng nào (ví dụ cạnh máy -> công đoạn bị xóa), nên std của P ở mức xóa cao rất lớn.

## Độ nhạy của λ trong truy vết ngược (tham khảo, KHÔNG dùng để chọn lại λ)

| Xóa cạnh | λ=0.0 | λ=0.25 | λ=0.5 | λ=0.75 | baseline bất thường |
|---|---|---|---|---|---|
| 0% | 0.233 ± 0.425 | 0.244 ± 0.432 | 0.233 ± 0.425 | 0.167 ± 0.375 | 0.022 ± 0.148 |
| 10% | 0.190 ± 0.380 | 0.178 ± 0.384 | 0.144 ± 0.354 | 0.122 ± 0.329 | 0.022 ± 0.148 |
| 25% | 0.119 ± 0.280 | 0.100 ± 0.302 | 0.100 ± 0.302 | 0.067 ± 0.251 | 0.022 ± 0.148 |
| 50% | 0.095 ± 0.201 | 0.067 ± 0.251 | 0.056 ± 0.230 | 0.033 ± 0.181 | 0.022 ± 0.148 |

## Thời gian chạy (đóng góp cho E6, chỉ phần truy vết + chấm điểm)

Median 0.91 ms, p95 2.76 ms mỗi sự cố (ước tính thủ công của kỹ sư vẫn cần phỏng vấn, xem việc P2.8 trong tài liệu).

## E0 – Phát hiện bất thường trên SECOM (tập test theo thời gian)

Ngưỡng cố định theo recall 90% trên validation. Test có 17 fail trong 314 dòng (tỷ lệ fail 5.4%, đây cũng là PR-AUC của bộ phân loại ngẫu nhiên). Trong ngoặc là khoảng tin cậy bootstrap 95%.

| Mô hình | Precision | Recall | F1 | PR-AUC | Tỷ lệ báo sai | ROC-AUC |
|---|---|---|---|---|---|---|
| Luật 3-sigma (số cảm biến vượt ±3σ) | 0.055 (0.03–0.08) | 1.000 (1.00–1.00) | 0.105 (0.06–0.15) | 0.055 (0.03–0.11) | 0.976 (0.96–0.99) | 0.481 (0.34–0.63) |
| Isolation Forest (PCA) | 0.055 (0.03–0.08) | 0.941 (0.80–1.00) | 0.103 (0.06–0.15) | 0.048 (0.03–0.10) | 0.933 (0.91–0.96) | 0.373 (0.23–0.53) |
| Hồi quy logistic có class weight (PCA) | 0.059 (0.03–0.09) | 0.824 (0.62–1.00) | 0.111 (0.06–0.17) | 0.082 (0.04–0.18) | 0.747 (0.70–0.80) | 0.589 (0.46–0.73) |

**Cách đọc:** SECOM có tín hiệu phát hiện rất yếu và test chỉ có vài chục fail. Khi PR-AUC xấp xỉ tỷ lệ fail và ROC-AUC gần 0,5 thì mô hình chưa tốt hơn đoán ngẫu nhiên một cách đáng tin; nên báo cáo đúng như vậy thay vì chọn mô hình có điểm cao nhất trên một tập test nhỏ. Class weight được dùng ở hồi quy logistic (không dùng SMOTE). Isolation Forest không có tham số class weight vì không dùng nhãn khi huấn luyện.

## Cách đọc kết quả SECOM (quan trọng)

- Điểm bất thường trung bình (phân vị train) của dòng FAIL trong tập sinh sự cố là 0.68, của dòng PASS là 0.76. Dòng fail không bất thường hơn dòng pass (dữ liệu tháng 10 lệch so với tập train tháng 7–9), nên điểm bất thường gần như không mang thông tin về máy gốc.
- Vì vậy baseline E3 (điểm bất thường cao nhất) chỉ đạt Top-1 0.022, xấp xỉ đoán ngẫu nhiên trong 23 máy. Phần hệ thống hơn baseline ở E3 chủ yếu đến từ cấu trúc đồ thị (khả năng nối tới kết quả xấu), không phải từ chất lượng phát hiện.
- E1 và E2 không phụ thuộc chất lượng bộ phát hiện (chỉ phụ thuộc đồ thị và ước lượng tác động) nên tương tự AI4I.
- SECOM được dùng đúng vai trò trong tài liệu: kiểm tra pipeline tổng quát hóa sang domain khác (590 chiều, mất cân bằng 6,6%), không phải để chứng minh phát hiện tốt. Phát hiện lỗi SECOM theo thời gian là bài toán khó; báo cáo trung thực là phát hiện chưa vượt ngẫu nhiên.
