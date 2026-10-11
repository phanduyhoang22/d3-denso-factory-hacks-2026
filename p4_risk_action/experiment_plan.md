# experiment_plan.md – Khung thí nghiệm E0–E6 (P4.1)

Quy ước chung: seed cố định (42 + chỉ số lần chạy), 30 seed mỗi domain (tối thiểu 10 nếu trễ, phải ghi rõ trong báo cáo).
Domain: `AI4I` (nhánh A, có tầng Máy) và `SECOM` (nhánh B, không có tầng Máy).

| Mã | Câu hỏi | Chỉ số | Baseline | Ai chạy | Biến thay đổi |
|---|---|---|---|---|---|
| E0 | Phát hiện bất thường tốt tới đâu? | Precision, Recall, F1, PR-AUC, tỷ lệ báo sai (theo TWF/HDF/PWF/OSF; RNF loại) | Luật ngưỡng cố định | P1 (AI4I), P2 (SECOM) | chế độ lỗi |
| E1 | Truy vết xuôi đúng phạm vi không? | Recall@k, Precision@k theo tầng (công đoạn/linh kiện/sản phẩm/đơn hàng) | Cảnh báo cục bộ (chỉ máy + công đoạn liền kề) | P3 viết baseline; P1/P2 chạy | quy mô đồ thị |
| E2 | Điểm rủi ro xếp đúng mức ưu tiên không? | Spearman với true_impact, Top-k precision | Xếp theo số bước: 1/(1+hops) | P4 viết baseline; P1/P2 chạy | quy mô đồ thị |
| E3 | Truy vết ngược đúng nguyên nhân khi có nhiễu? | Top-1 / Top-k accuracy | Máy có điểm bất thường cao nhất | P1/P2 | confounder 0/25/50% |
| E4 | Đồ thị thiếu cạnh thì tệ đến đâu? | Lặp E1–E3, đo độ suy giảm | Đồ thị đầy đủ | P3 | xóa 10/25/50% cạnh |
| E5 | Khuyến nghị hợp lý không? | Tỷ lệ chấm "đúng" trên 10–15 kịch bản (thành viên tự chấm) | Không có | cả nhóm | – |
| E6 | Nhanh hơn điều tra thủ công bao nhiêu? | Thời gian pipeline (detect→trace→score→action) | Ước tính thủ công (phỏng vấn 1–2 kỹ sư; ghi rõ nguồn con số) | P5 đo, P2 phỏng vấn | – |

## Quy tắc chấm E2 (tránh tự chấm chính mình)
- Đáp án = `true_impact` do P2 tính bằng cách lan truyền sự cố trên đồ thị ĐẦY ĐỦ, có trọng số thật.
- Hệ thống chỉ được nhìn đồ thị nhiễu/ước lượng. Không dùng công thức risk để sinh đáp án.
- Hệ số công thức risk (`risk_formula.md`) chốt TRƯỚC khi chạy; không chỉnh theo kết quả E2 trên chính seed dùng để báo cáo.

## Cách báo cáo (mục 15.4–15.5)
- Cố định recall rồi so tỷ lệ báo sai, không chỉ lấy trung bình chung.
- Báo mean ± std trên các seed, riêng theo: quy mô đồ thị, chế độ lỗi AI4I, tỷ lệ confounder, tỷ lệ cạnh bị xóa, domain.
- Nếu E1–E3 không vượt rõ baseline khi thiếu 25–50% cạnh (E4) thì ghi đúng như vậy.
- Chỉ nói "xếp hạng nguyên nhân khả dĩ", không khẳng định nhân quả.

## Hạn chế phải nêu thẳng
- AI4I là dữ liệu tổng hợp, mỗi dòng là một lượt vận hành rời rạc; timestamp AI4I là giả.
- Đồ thị, quy trình, đơn hàng đều là mô phỏng; chưa chứng minh trên dữ liệu Denso thật.
- Chưa có tồn kho, công suất máy, trọng số cạnh thật; máy dự phòng chưa mô hình hóa tải.