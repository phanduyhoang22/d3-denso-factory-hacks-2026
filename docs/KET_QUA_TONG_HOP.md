# D3 – Tổng hợp kết quả và trạng thái (12/10/2026)

Gom kết quả của 5 part. Số liệu lấy trực tiếp từ file output ghi ở mỗi mục; mean ± std qua seed/sự cố.
Đồ thị, routing, đơn hàng, trọng số đều là **mô phỏng**; chỉ tín hiệu và nhãn lỗi AI4I/SECOM là thật.

## 1. Trạng thái công việc

| Part | Người | Trạng thái | Ghi chú |
|---|---|---|---|
| P1 Phát hiện AI4I + truy vết ngược | Việt | ✅ (P5 bổ sung) | Thư mục trống trong `al.zip`; đã làm đủ P1.1–P1.7 (`p1_detection/README.md`); bộ chính = Isolation Forest + vật lý |
| P2 Phát hiện SECOM + ground truth | Thành | ✅ | 71/71 test đạt |
| P3 Đồ thị + kịch bản + truy vết xuôi | Tình | ✅ | 17/17 test; **đã chạy lại** với SECOM đúng ngày (mục 6) |
| P4 Rủi ro + hành động + báo cáo | Trang | ✅ (P5 bổ sung 4.3, 4.6) | 4.3 = `src/d3/risk.py`, `src/d3/action.py`; 4.6 = file này |
| P5 Nền tảng + tích hợp + dashboard | Phan Hoàng | ✅ | Còn: chốt schema với nhóm, slide, nộp bài |

**Đã chốt (12/10/2026):**
- Schema v1 + kịch bản demo `INC_A003` (M41, OSF): `schemas/README.md`.
- Luật `p4_risk_action/kb.yaml` (P1.7): HDF 115/115, PWF 95/95, OSF 98/98 khớp dữ liệu; TWF sửa thành ~200–250 phút
  (thực tế 198–253). `action`/`team` vẫn cần kỹ sư DENSO xác nhận.

**E5/E6 (12/10/2026):**
- Kiểm tra bằng dữ liệu trên 443 sự cố: `docs/E5_E6_tu_dong.md` – nguyên nhân #1 đúng 47% (AI4I) / 95% (SECOM),
  top-3 88% / 100%; phạm vi và hành động hợp lệ về dữ liệu 100%.
- Đánh giá sơ bộ theo góc nhìn chuyên gia, 12 kịch bản: `docs/E5_E6_chuyen_gia.md` – C1 58% Đ, C2 0% Đ (8/12 có
  điều kiện: phạm vi thiếu chiều thời gian), C3 58% Đ (83% tính cả có điều kiện). E6 ước tính: rút ngắn ~85–95% thời
  gian tới quyết định ban đầu (thủ công ~1–2 giờ vs pipeline < 1 giây).
- Khi trích dẫn phải ghi nguồn "đánh giá sơ bộ, chưa phỏng vấn kỹ sư DENSO". Nếu nhóm chấm thật
  (`docs/E5_E6_phieu.md`) hoặc phỏng vấn được kỹ sư thì thay bằng số đó.

**Còn lại:** P1 (Việt) đọc lại phần P5 viết thay; slide; nộp bài.

## 2. E0 – Phát hiện bất thường

**AI4I** (`p1_detection/outputs/p1_ai4i_report.md`) – test 2.000 dòng / 68 lỗi, ngưỡng recall 90% trên validation:

| Bộ phát hiện | Precision | Recall | F1 | PR-AUC | Tỷ lệ báo sai |
|---|---|---|---|---|---|
| Luật mô tả dataset (cận trên) | 0.307 | 0.971 | 0.466 | 0.358 | 0.077 |
| Isolation Forest (5 cảm biến) | 0.070 | 0.912 | 0.131 | 0.145 | 0.424 |
| **Isolation Forest + đặc trưng vật lý (bộ chính)** | 0.079 | 0.926 | 0.146 | 0.272 | 0.378 |
| Autoencoder | 0.046 | 0.971 | 0.087 | 0.275 | 0.713 |

- Luật HDF/PWF/OSF trùng luật sinh nhãn nên không báo sai; toàn bộ báo sai của luật đến từ TWF (`tool wear ≥ 200`).
- Bộ chính chọn theo tỷ lệ báo sai thấp nhất trên **validation** (0.374 so với 0.420 của bản 5 cảm biến). Vẫn báo sai ~38%:
  794 cảnh báo trên test, chỉ 63 là lỗi thật.

**SECOM** (`p2_secom_impact/p2_outputs/secom/p2_secom_e0.csv`) – test 314 dòng / 17 fail, chia theo thời gian:

| Bộ phát hiện | Precision | Recall | Tỷ lệ báo sai | ROC-AUC |
|---|---|---|---|---|
| Luật 3-sigma | 0.055 | 1.000 | 0.976 | 0.48 |
| Isolation Forest (PCA) | 0.055 | 0.941 | 0.933 | 0.37 |
| Hồi quy logistic (class weight) | 0.059 | 0.824 | 0.747 | 0.59 |

→ **Phát hiện SECOM chưa vượt ngẫu nhiên** (ROC-AUC 0.37–0.59, khoảng tin cậy chứa 0.5).

## 3. E1–E4 trên đồ thị mô phỏng có ground truth (P2, P3)

Hai bộ mô phỏng độc lập, cùng thiết kế mục 15 (30 seed × 3 quy mô × 3 confounder × 4 mức xóa cạnh).

| Chỉ số | Nguồn | Đầy đủ | Thiếu 10% | Thiếu 25% | Thiếu 50% |
|---|---|---|---|---|---|
| E1 recall (gộp tầng) – hệ thống | P3 (2 domain) | 0.94 | 0.77 | 0.50 | 0.22 |
| E1 recall – baseline cục bộ | P3 | 0.12 | – | – | – |
| E1 recall **đơn hàng** – hệ thống | P3 | 0.90 | 0.67 | 0.34 | 0.08 |
| E1 recall – hệ thống / baseline | P2 (AI4I) | 0.816 / 0.105 | 0.597 / 0.100 | 0.332 / 0.082 | 0.121 / 0.050 |
| E2 Spearman – hệ thống / số bước | P2 (AI4I) | 0.946 / 0.795 | 0.791 / 0.617 | 0.586 / 0.460 | 0.458 / 0.422 |
| E3 Top-1 (confounder 25%) – hệ thống / bất thường cao nhất | P2 (AI4I) | 0.656 / 0.467 | 0.522 / 0.467 | 0.489 / 0.467 | 0.456 / 0.467 |

Nguồn: `p3_graph/results/summary_p3.md`, `p2_secom_impact/p2_outputs/p2_experiments_report.md`.

## 4. Pipeline tích hợp trên dữ liệu nhà máy (P5)

443 sự cố thật × 4 mức xóa cạnh; module thật: điểm bất thường P1, rủi ro + hành động P4, truy vết ngược P1.
File: `results/run_ai4i.csv`, `run_ai4i_alarms.csv`, `run_secom.csv`.

| Chỉ số | AI4I (nhiễu = sự cố thật) | AI4I (+ báo sai của detector) | SECOM |
|---|---|---|---|
| Số sự cố đồng thời trung bình (cửa sổ 2h) | 33 | 277 | 0.3 |
| E1 recall, đồ thị đầy đủ → thiếu 25% → thiếu 50% | 1.00 → 0.43 → 0.14 | như cột trái | 1.00 → 0.44 → 0.14 |
| E3 Top-1 hệ thống / bất thường cao nhất (đầy đủ) | **0.469 / 0.041** | **0.242 / 0.027** | 0.952 / 0.875 |
| E3 Top-3 hệ thống / bất thường cao nhất (đầy đủ) | 0.882 / 0.150 | 0.614 / 0.086 | 1.000 / 1.000 |
| E3 Top-1 hệ thống khi thiếu 50% cạnh | 0.118 | 0.080 | 0.865 |
| E6 thời gian pipeline (trung vị) | ~0.5 s/sự cố | ~0.5 s | ~0.3 s |

Đọc kết quả:
- **E1 = 1.00 khi đồ thị đầy đủ là vòng lặp** (đáp án = tập hậu duệ trong cùng đồ thị); chỉ đường suy giảm ở E4 có ý nghĩa.
  Thiếu 25% cạnh → chỉ còn ~43% đối tượng bị ảnh hưởng được tìm thấy.
- **E3 AI4I**: đồ thị giúp rõ rệt so với chọn điểm cao nhất (0.47 vs 0.04 top-1; 0.88 vs 0.15 top-3), nhưng top-1
  còn thấp vì nhiều sự cố cùng lúc nằm trên **cùng chuỗi sản xuất** của đơn hàng (timestamp giả dồn về 01/01 00:00).
  Thêm báo sai của detector thì top-1 còn 0.24 (0.17 với bộ 5 cảm biến) → chất lượng phát hiện là nút thắt của truy vết ngược.
- **E3 SECOM** gần như không có nhiễu (timestamp thật ít trùng) nên chênh lệch với baseline không nói lên nhiều.
- **E2 chưa đo được** trên dữ liệu nhà máy: chưa có trọng số cạnh / mức ảnh hưởng thật → Spearman NaN. Số E2 dùng mục 3.

## 5. Kết luận trung thực (mục 15.5)

1. Truy vết xuôi vượt baseline cục bộ ở mọi mức thiếu cạnh, nhưng **sụp mạnh khi thiếu 25–50% cạnh**, và lỗi là
   *bỏ sót im lặng* (precision vẫn cao) – rủi ro lớn nhất khi áp vào dữ liệu Denso.
2. Điểm rủi ro (P2) xếp hạng tốt hơn baseline số bước tới 25% thiếu cạnh; ở 50% gần như ngang nhau.
3. Truy vết ngược hơn baseline trên đồ thị đầy đủ, **không hơn** khi thiếu 50% cạnh (P2, P3); trên dữ liệu nhà máy,
   detector báo sai nhiều làm top-1 giảm từ 0.47 xuống 0.24.
4. Theo P3, cần ưu tiên thu thập đủ **BOM**, **đơn hàng ↔ sản phẩm**, **routing công đoạn → linh kiện**.

## 6. Vấn đề phát hiện khi tích hợp (đã xử lý)

| Vấn đề | Ảnh hưởng | Xử lý |
|---|---|---|
| Bản SECOM P3 dùng có ngày bị đảo (08/01–10/12/2008 thay vì 19/07–17/10/2008) | Chia "theo thời gian" sai thứ tự | `scripts/prepare_team_data.py` tạo CSV từ dữ liệu gốc; chạy lại P3: E1/E2 không đổi, E3 SECOM baseline 0.67 → 0.72, hệ thống 1.00/0.75 (0%/50%) gần như giữ nguyên |
| Sự cố gốc luôn đứng đầu danh sách | Baseline E3 "đoán đúng" khi bằng điểm | Pipeline xáo thứ tự theo seed |
| Cùng mã linh kiện làm trên nhiều máy | Lan truyền sai sang sản phẩm của máy khác | Node linh kiện `<mã>@<máy>` |
| Test CLI của P2 lỗi trên Windows | Đọc output bằng cp1252 | Chạy với `PYTHONUTF8=1` (71/71 đạt) |
