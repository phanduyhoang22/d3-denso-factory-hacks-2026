# D3 – P2: kết quả thí nghiệm E1–E4 (AI4I 2020)

30 seed × 3 quy mô × 3 mức confounder × 4 mức xóa cạnh = 1080 dòng trong `p2_results.csv`. Số liệu là mean ± std qua seed (E1/E2 không phụ thuộc confounder nên lặp lại qua 3 mức confounder, không đổi mean/std).

## Điều kiện thí nghiệm (đọc trước khi trích số)

- Phát hiện: Isolation Forest fit trên train AI4I (50%), ngưỡng cố định recall 90% trên validation (20%). Bộ đặc trưng chọn theo validation: physical (tỷ lệ báo sai validation {'raw': 0.4653, 'physical': 0.2195}). Trên test (30%): recall thực 0.869, tỷ lệ báo sai 0.215. RNF bị loại (không phát hiện được theo thiết kế).
- Mọi sự cố là dòng lỗi THẬT của AI4I 2020 (tập test); cấu trúc đồ thị, trọng số, đệm, đơn hàng là MÔ PHỎNG, sinh độc lập với sự cố.
- Ground truth tác động dùng mô hình dòng chảy khác công thức của hệ thống (đệm trừ phút, gộp noisy-OR, thời gian dừng và hằng số bù trễ thật). Hệ thống chỉ thấy đồ thị với trọng số/đệm có nhiễu và bị xóa cạnh.
- Confounder chỉ được đặt ở máy KHÔNG nằm trong tổ tiên của kết quả xấu (đúng thiết kế 18.3). Vì cạnh chỉ bị xóa chứ không thêm cạnh sai, đồ thị không bao giờ nối nhầm confounder vào kết quả xấu: E3 ở mức xóa 0% gần như dễ theo cấu trúc, phần có giá trị là E4.
- Điểm truy vết ngược = pct_bất_thường × (λ + (1−λ)·reach), λ = 0.5 đặt TRƯỚC khi chạy; bảng độ nhạy λ ở cuối chỉ để tham khảo.
- Kết quả theo quy mô đồ thị mô phỏng tự đặt; chưa chứng minh trên dữ liệu DENSO.

## E1 – Truy vết xuôi (pooled 4 tầng) theo % cạnh bị xóa (E4)

| Xóa cạnh | Hệ thống P | Hệ thống R | Hệ thống F1 | Cục bộ P | Cục bộ R | Cục bộ F1 |
|---|---|---|---|---|---|---|
| 0% | 0.985 ± 0.049 | 0.816 ± 0.142 | 0.884 ± 0.088 | 1.000 ± 0.000 | 0.105 ± 0.052 | 0.186 ± 0.084 |
| 10% | 0.911 ± 0.268 | 0.597 ± 0.297 | 0.688 ± 0.297 | 0.922 ± 0.268 | 0.100 ± 0.057 | 0.178 ± 0.095 |
| 25% | 0.795 ± 0.399 | 0.332 ± 0.289 | 0.427 ± 0.326 | 0.800 ± 0.401 | 0.082 ± 0.062 | 0.146 ± 0.105 |
| 50% | 0.500 ± 0.501 | 0.121 ± 0.206 | 0.170 ± 0.250 | 0.500 ± 0.501 | 0.050 ± 0.064 | 0.089 ± 0.109 |

Recall theo tầng (hệ thống), theo % cạnh bị xóa:

| Xóa cạnh | Công đoạn | Linh kiện | Sản phẩm | Đơn hàng |
|---|---|---|---|---|
| 0% | 0.996 ± 0.020 | 0.981 ± 0.066 | 0.893 ± 0.271 | 0.319 ± 0.408 |
| 10% | 0.843 ± 0.318 | 0.775 ± 0.374 | 0.635 ± 0.405 | 0.167 ± 0.315 |
| 25% | 0.602 ± 0.408 | 0.452 ± 0.440 | 0.306 ± 0.381 | 0.069 ± 0.203 |
| 50% | 0.308 ± 0.395 | 0.146 ± 0.316 | 0.079 ± 0.228 | 0.034 ± 0.160 |

Theo quy mô đồ thị (Recall hệ thống, ở 0% / 25% / 50% xóa):

| Quy mô | 0% | 25% | 50% |
|---|---|---|---|
| small | 0.822 ± 0.116 | 0.416 ± 0.313 | 0.198 ± 0.251 |
| medium | 0.849 ± 0.145 | 0.314 ± 0.278 | 0.102 ± 0.210 |
| large | 0.777 ± 0.154 | 0.264 ± 0.255 | 0.062 ± 0.109 |

## E2 – Điểm rủi ro vs mức ảnh hưởng thật

| Xóa cạnh | Spearman hệ thống | Spearman chỉ-số-bước | Top-3 đơn hệ thống | Top-3 đơn chỉ-số-bước |
|---|---|---|---|---|
| 0% | 0.946 ± 0.066 | 0.795 ± 0.081 | 0.793 ± 0.266 | 0.215 ± 0.240 |
| 10% | 0.791 ± 0.199 | 0.617 ± 0.176 | 0.559 ± 0.341 | 0.200 ± 0.232 |
| 25% | 0.586 ± 0.212 | 0.460 ± 0.170 | 0.300 ± 0.286 | 0.185 ± 0.229 |
| 50% | 0.458 ± 0.205 | 0.422 ± 0.166 | 0.226 ± 0.243 | 0.211 ± 0.231 |

## E3 – Truy vết ngược: Top-1 của máy gốc theo confounder × xóa cạnh

| Confounder | Xóa cạnh | Top-1 hệ thống | Top-3 hệ thống | Top-1 baseline bất thường | Top-1 baseline gần nhất |
|---|---|---|---|---|---|
| 0% | 0% | 0.656 ± 0.478 | 0.900 ± 0.302 | 0.589 ± 0.495 | 0.267 ± 0.445 |
| 0% | 10% | 0.567 ± 0.498 | 0.800 ± 0.402 | 0.589 ± 0.495 | 0.267 ± 0.445 |
| 0% | 25% | 0.544 ± 0.501 | 0.878 ± 0.329 | 0.589 ± 0.495 | 0.267 ± 0.445 |
| 0% | 50% | 0.567 ± 0.498 | 0.889 ± 0.316 | 0.589 ± 0.495 | 0.267 ± 0.445 |
| 25% | 0% | 0.656 ± 0.478 | 0.900 ± 0.302 | 0.467 ± 0.502 | 0.233 ± 0.425 |
| 25% | 10% | 0.522 ± 0.502 | 0.800 ± 0.402 | 0.467 ± 0.502 | 0.233 ± 0.425 |
| 25% | 25% | 0.489 ± 0.503 | 0.867 ± 0.342 | 0.467 ± 0.502 | 0.233 ± 0.425 |
| 25% | 50% | 0.456 ± 0.501 | 0.856 ± 0.354 | 0.467 ± 0.502 | 0.233 ± 0.425 |
| 50% | 0% | 0.656 ± 0.478 | 0.900 ± 0.302 | 0.433 ± 0.498 | 0.233 ± 0.425 |
| 50% | 10% | 0.511 ± 0.503 | 0.789 ± 0.410 | 0.433 ± 0.498 | 0.233 ± 0.425 |
| 50% | 25% | 0.467 ± 0.502 | 0.822 ± 0.384 | 0.433 ± 0.498 | 0.233 ± 0.425 |
| 50% | 50% | 0.422 ± 0.497 | 0.833 ± 0.375 | 0.433 ± 0.498 | 0.233 ± 0.425 |

Top-1 của baseline 'bất thường cao nhất' bị chặn trên bởi việc bộ phát hiện có chấm điểm máy gốc cao nhất hay không (máy gốc bị phát hiện trong 95.6% kịch bản).

## Kiểm tra tiêu chí thành công (15.5): hệ thống có vượt baseline khi thiếu cạnh?

Hiệu hệ thống − baseline, ghép cặp theo (seed, quy mô), kèm khoảng tin cậy 95% và tỷ lệ seed thắng/thua.

| Chỉ số | Xóa cạnh | Hiệu (hệ thống − baseline) | % seed thắng | % seed thua |
|---|---|---|---|---|
| E1 Recall | 0% | +0.711 ± 0.028 | 100% | 0% |
| E1 Recall | 10% | +0.497 ± 0.057 | 83% | 0% |
| E1 Recall | 25% | +0.249 ± 0.053 | 58% | 0% |
| E1 Recall | 50% | +0.070 ± 0.034 | 22% | 0% |
| E2 Spearman | 0% | +0.151 ± 0.017 | 93% | 7% |
| E2 Spearman | 10% | +0.174 ± 0.024 | 79% | 1% |
| E2 Spearman | 25% | +0.126 ± 0.029 | 48% | 2% |
| E2 Spearman | 50% | +0.036 ± 0.022 | 12% | 0% |
| E2 Top-3 đơn | 0% | +0.578 ± 0.063 | 89% | 0% |
| E2 Top-3 đơn | 10% | +0.359 ± 0.061 | 67% | 0% |
| E2 Top-3 đơn | 25% | +0.115 ± 0.045 | 26% | 0% |
| E2 Top-3 đơn | 50% | +0.015 ± 0.014 | 4% | 0% |

| So sánh | Confounder | Xóa cạnh | Hiệu Top-1 | % seed thắng | % seed thua |
|---|---|---|---|---|---|
| E3 vs bất thường cao nhất | 25% | 0% | +0.189 ± 0.111 | 26% | 7% |
| E3 vs bất thường cao nhất | 25% | 10% | +0.056 ± 0.121 | 20% | 14% |
| E3 vs bất thường cao nhất | 25% | 25% | +0.022 ± 0.093 | 11% | 9% |
| E3 vs bất thường cao nhất | 25% | 50% | -0.011 ± 0.022 | 0% | 1% |
| E3 vs bất thường cao nhất | 50% | 0% | +0.222 ± 0.111 | 28% | 6% |
| E3 vs bất thường cao nhất | 50% | 10% | +0.078 ± 0.121 | 21% | 13% |
| E3 vs bất thường cao nhất | 50% | 25% | +0.033 ± 0.090 | 11% | 8% |
| E3 vs bất thường cao nhất | 50% | 50% | -0.011 ± 0.022 | 0% | 1% |
| E3 vs gần nhất | 25% | 0% | +0.422 ± 0.124 | 48% | 6% |
| E3 vs gần nhất | 25% | 10% | +0.289 ± 0.125 | 37% | 8% |
| E3 vs gần nhất | 25% | 25% | +0.256 ± 0.118 | 32% | 7% |
| E3 vs gần nhất | 25% | 50% | +0.222 ± 0.111 | 28% | 6% |
| E3 vs gần nhất | 50% | 0% | +0.422 ± 0.124 | 48% | 6% |
| E3 vs gần nhất | 50% | 10% | +0.278 ± 0.124 | 36% | 8% |
| E3 vs gần nhất | 50% | 25% | +0.233 ± 0.116 | 30% | 7% |
| E3 vs gần nhất | 50% | 50% | +0.189 ± 0.107 | 24% | 6% |

## Kết luận

- E1 Recall ở 0% xóa cạnh: hệ thống 0.816 vs baseline 0.105 (hiệu +0.711, CI95 ±0.028) -> vượt baseline có ý nghĩa thống kê.
- E1 Recall ở 25% xóa cạnh: hệ thống 0.332 vs baseline 0.082 (hiệu +0.249, CI95 ±0.053) -> vượt baseline có ý nghĩa thống kê.
- E1 Recall ở 50% xóa cạnh: hệ thống 0.121 vs baseline 0.050 (hiệu +0.070, CI95 ±0.034) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 0% xóa cạnh: hệ thống 0.946 vs baseline 0.795 (hiệu +0.151, CI95 ±0.017) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 25% xóa cạnh: hệ thống 0.586 vs baseline 0.460 (hiệu +0.126, CI95 ±0.029) -> vượt baseline có ý nghĩa thống kê.
- E2 Spearman ở 50% xóa cạnh: hệ thống 0.458 vs baseline 0.422 (hiệu +0.036, CI95 ±0.022) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 0% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.656 vs 0.433 (hiệu +0.222, CI95 ±0.111) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 25% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.467 vs 0.433 (hiệu +0.033, CI95 ±0.090) -> KHÔNG vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 50% xóa cạnh vs baseline bất thường cao nhất: hệ thống 0.422 vs 0.433 (hiệu -0.011, CI95 ±0.022) -> KHÔNG vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 0% xóa cạnh vs baseline gần nhất: hệ thống 0.656 vs 0.233 (hiệu +0.422, CI95 ±0.124) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 25% xóa cạnh vs baseline gần nhất: hệ thống 0.467 vs 0.233 (hiệu +0.233, CI95 ±0.116) -> vượt baseline có ý nghĩa thống kê.
- E3 (confounder 50%) ở 50% xóa cạnh vs baseline gần nhất: hệ thống 0.422 vs 0.233 (hiệu +0.189, CI95 ±0.107) -> vượt baseline có ý nghĩa thống kê.

Recall truy vết xuôi giảm từ 0.816 (đồ thị đủ) xuống 0.121 (thiếu 50% cạnh). Nếu dữ liệu DENSO thiếu nhiều quan hệ phụ thuộc, đây là mức suy giảm cần kỳ vọng; không nên trình bày số ở 0% như hiệu năng thực tế. Precision được tính bằng 0 khi hệ thống không cảnh báo đối tượng nào (ví dụ cạnh máy -> công đoạn bị xóa), nên std của P ở mức xóa cao rất lớn.

## Độ nhạy của λ trong truy vết ngược (tham khảo, KHÔNG dùng để chọn lại λ)

| Xóa cạnh | λ=0.0 | λ=0.25 | λ=0.5 | λ=0.75 | baseline bất thường |
|---|---|---|---|---|---|
| 0% | 0.533 ± 0.502 | 0.611 ± 0.490 | 0.656 ± 0.478 | 0.733 ± 0.445 | 0.433 ± 0.498 |
| 10% | 0.411 ± 0.484 | 0.467 ± 0.502 | 0.511 ± 0.503 | 0.589 ± 0.495 | 0.433 ± 0.498 |
| 25% | 0.197 ± 0.363 | 0.400 ± 0.493 | 0.467 ± 0.502 | 0.511 ± 0.503 | 0.433 ± 0.498 |
| 50% | 0.096 ± 0.201 | 0.389 ± 0.490 | 0.422 ± 0.497 | 0.422 ± 0.497 | 0.433 ± 0.498 |

## Thời gian chạy (đóng góp cho E6, chỉ phần truy vết + chấm điểm)

Median 0.89 ms, p95 2.93 ms mỗi sự cố (ước tính thủ công của kỹ sư vẫn cần phỏng vấn, xem việc P2.8 trong tài liệu).

## Tần suất lỗi lịch sử theo máy (P1.5): có giúp truy vết ngược không?

Hệ số lịch sử = (số sự cố lịch sử + 1)/(trung bình + 1), chặn [0,25; 4], lũy thừa γ. Lịch sử là một giai đoạn đếm riêng (20000 đơn vị) tách khỏi kịch bản, có nhiễu đếm Poisson. Confounder 50%. Các số mean ± std, Top-1 máy gốc.

| Chế độ máy gốc | Xóa cạnh | Bất thường | Bất thường × lịch sử | Đồ thị (γ=0) | Đồ thị + lịch sử γ=0.25 (thêm sau) | Đồ thị + lịch sử γ=0.5 | Đồ thị + lịch sử γ=1.0 |
|---|---|---|---|---|---|---|---|
| proportional | 0% | 0.500 ± 0.503 | 0.311 ± 0.466 | 0.644 ± 0.481 | 0.678 ± 0.470 | 0.533 ± 0.502 | 0.378 ± 0.488 |
| proportional | 10% | 0.500 ± 0.503 | 0.311 ± 0.466 | 0.567 ± 0.498 | 0.533 ± 0.502 | 0.478 ± 0.502 | 0.356 ± 0.481 |
| proportional | 25% | 0.500 ± 0.503 | 0.311 ± 0.466 | 0.433 ± 0.498 | 0.478 ± 0.502 | 0.456 ± 0.501 | 0.356 ± 0.481 |
| proportional | 50% | 0.500 ± 0.503 | 0.311 ± 0.466 | 0.511 ± 0.503 | 0.478 ± 0.502 | 0.433 ± 0.498 | 0.322 ± 0.470 |
| uniform | 0% | 0.433 ± 0.498 | 0.133 ± 0.342 | 0.656 ± 0.478 | 0.444 ± 0.500 | 0.256 ± 0.439 | 0.167 ± 0.375 |
| uniform | 10% | 0.433 ± 0.498 | 0.133 ± 0.342 | 0.511 ± 0.503 | 0.400 ± 0.493 | 0.267 ± 0.445 | 0.156 ± 0.364 |
| uniform | 25% | 0.433 ± 0.498 | 0.133 ± 0.342 | 0.467 ± 0.502 | 0.267 ± 0.445 | 0.178 ± 0.384 | 0.144 ± 0.354 |
| uniform | 50% | 0.433 ± 0.498 | 0.133 ± 0.342 | 0.422 ± 0.497 | 0.222 ± 0.418 | 0.167 ± 0.375 | 0.133 ± 0.342 |

Hiệu ghép cặp (đồ thị + lịch sử) − (đồ thị γ=0), Top-1, confounder 50%:

| Chế độ máy gốc | γ | Xóa cạnh | Hiệu | % seed thắng | % seed thua |
|---|---|---|---|---|---|
| proportional | 0.25 | 0% | +0.033 ± 0.109 | 16% | 12% |
| proportional | 0.25 | 10% | -0.033 ± 0.100 | 10% | 13% |
| proportional | 0.25 | 25% | +0.044 ± 0.116 | 18% | 13% |
| proportional | 0.25 | 50% | -0.033 ± 0.114 | 13% | 17% |
| proportional | 0.5 | 0% | -0.111 ± 0.129 | 14% | 26% |
| proportional | 0.5 | 10% | -0.089 ± 0.119 | 12% | 21% |
| proportional | 0.5 | 25% | +0.022 ± 0.131 | 21% | 19% |
| proportional | 0.5 | 50% | -0.078 ± 0.117 | 12% | 20% |
| proportional | 1.0 | 0% | -0.267 ± 0.131 | 10% | 37% |
| proportional | 1.0 | 10% | -0.211 ± 0.126 | 10% | 31% |
| proportional | 1.0 | 25% | -0.078 ± 0.132 | 17% | 24% |
| proportional | 1.0 | 50% | -0.189 ± 0.127 | 11% | 30% |
| uniform | 0.25 | 0% | -0.211 ± 0.100 | 3% | 24% |
| uniform | 0.25 | 10% | -0.111 ± 0.100 | 7% | 18% |
| uniform | 0.25 | 25% | -0.200 ± 0.099 | 3% | 23% |
| uniform | 0.25 | 50% | -0.200 ± 0.104 | 4% | 24% |
| uniform | 0.5 | 0% | -0.400 ± 0.111 | 2% | 42% |
| uniform | 0.5 | 10% | -0.244 ± 0.113 | 6% | 30% |
| uniform | 0.5 | 25% | -0.289 ± 0.113 | 4% | 33% |
| uniform | 0.5 | 50% | -0.256 ± 0.114 | 6% | 31% |
| uniform | 1.0 | 0% | -0.489 ± 0.108 | 1% | 50% |
| uniform | 1.0 | 10% | -0.356 ± 0.109 | 2% | 38% |
| uniform | 1.0 | 25% | -0.322 ± 0.115 | 4% | 37% |
| uniform | 1.0 | 50% | -0.289 ± 0.117 | 6% | 34% |

Cách đọc: ở chế độ uniform lịch sử không có thông tin thật, nên kết quả cho thấy dùng nó có làm hại hay không. Ở chế độ proportional, lợi ích là hệ quả của giả định 'máy hay lỗi thì lỗi nhiều hơn', không phải bằng chứng trên dữ liệu DENSO. γ = 0,5 và 1,0 đặt trước; γ = 0,25 thêm sau khi thấy kết quả nên chỉ mang tính thăm dò; cần số liệu bảo trì thật của DENSO để biết lịch sử có đáng tin hay không.
**Kết luận:** trong thiết lập này, nhân trực tiếp hệ số lịch sử vào điểm không cải thiện Top-1: nó làm giảm rõ ở chế độ uniform và không khác biệt có ý nghĩa (hoặc giảm) ở chế độ proportional, kể cả khi lịch sử có thông tin. Lý do khả dĩ: hệ số dao động tới 16 lần (0,25 đến 4) nên át tín hiệu đồ thị và điểm bất thường vốn chưa được hiệu chỉnh thành xác suất. Vì vậy `backward_trace()` mặc định `gamma = 0` (không dùng lịch sử); tham số vẫn có để thử khi có dữ liệu bảo trì thật hoặc khi có cách kết hợp có hiệu chỉnh (ví dụ prior Bayes).
