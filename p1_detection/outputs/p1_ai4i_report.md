# P1 – Phát hiện bất thường AI4I 2020 (E0)

Dữ liệu `data/factory/ai4i_assigned.csv`: 10,000 dòng, 339 lỗi máy. Chia phân tầng 60/20/20 (seed 42): test 2,000 dòng / 68 lỗi, train 6,000 dòng / 203 lỗi, val 2,000 dòng / 68 lỗi.
RNF: 18 dòng có cờ RNF nhưng `Machine failure = 0` → coi là bình thường; 9 dòng lỗi không có chế độ → `UNKNOWN`.

Ngưỡng: Isolation Forest và Autoencoder cố định **recall 90% trên validation**, áp nguyên lên test. Luật dùng ngưỡng của mô tả dataset.

## E0 trên test

| Bộ phát hiện | Precision | Recall | F1 | PR-AUC | Tỷ lệ báo sai |
|---|---|---|---|---|---|
| Luật mô tả dataset (cận trên*) | 0.307 | 0.971 | 0.466 | 0.358 | 0.077 |
| Isolation Forest (5 cảm biến) | 0.070 | 0.912 | 0.131 | 0.145 | 0.424 |
| Isolation Forest (+ đặc trưng vật lý) | 0.079 | 0.926 | 0.146 | 0.272 | 0.378 |
| Autoencoder | 0.046 | 0.971 | 0.087 | 0.275 | 0.713 |

## Recall theo chế độ lỗi (test)

| Chế độ | n | Luật | IF 5 cảm biến | IF + vật lý | Autoencoder |
|---|---|---|---|---|---|
| HDF | 29 | 1.00 | 0.86 | 0.93 | 1.00 |
| OSF | 16 | 1.00 | 1.00 | 1.00 | 1.00 |
| PWF | 13 | 1.00 | 1.00 | 1.00 | 1.00 |
| TWF | 10 | 0.90 | 0.90 | 0.80 | 0.80 |
| UNKNOWN | 2 | 0.50 | 0.50 | 0.50 | 1.00 |

**Bộ chính: Isolation Forest (+ đặc trưng vật lý)**, chọn vì tỷ lệ báo sai thấp nhất trên **validation** (Isolation Forest (5 cảm biến) 0.420, Isolation Forest (+ đặc trưng vật lý) 0.374, Autoencoder 0.701); test không dùng để chọn.

Bản ghi sự cố (`incidents_ai4i.json`): 794 cảnh báo của bộ chính trên test, trong đó 63 là lỗi thật, còn lại là **báo sai**.

## Cần nêu thẳng khi báo cáo

- *Luật HDF/PWF/OSF dùng đúng công thức đã sinh nhãn AI4I nên không báo sai lần nào (cận trên, không phải năng lực kỳ vọng ở nhà máy thật). Toàn bộ báo sai của luật đến từ TWF: dao hỏng ngẫu nhiên trong khoảng ~200–250 phút, nên ngưỡng `tool wear ≥ 200` bắt cả 678/9.661 dòng bình thường (toàn bộ dữ liệu).
- Bộ chính (Isolation Forest (+ đặc trưng vật lý)) đạt recall 0.93 nhưng báo sai 38% dòng bình thường: chỉ 63/794 cảnh báo trên test là lỗi thật. Đây là nhiễu thật cho truy vết ngược; P2 báo cáo bộ tương tự còn ~21% báo sai nhờ chọn bộ đặc trưng trên validation, nên còn dư địa cải thiện.
- Số mẫu lỗi trên test mỗi chế độ chỉ vài chục (TWF, UNKNOWN rất ít) → recall theo chế độ dao động mạnh; nên gộp hoặc báo kèm n.
- AI4I là dữ liệu tổng hợp, mỗi dòng là một lượt vận hành rời rạc; timestamp là giả.
- Mô hình không giám sát chỉ học dòng bình thường của train; ngưỡng chọn trên validation, không chỉnh theo test.
