# P1 – Phát hiện bất thường AI4I + Truy vết ngược

```bash
python p1_detection/p1_ai4i.py      # ~15 giây → p1_detection/outputs/
```

## Trạng thái các việc P1 (mục 17.4)

| ID | Việc | Trạng thái | Output |
|---|---|---|---|
| P1.1 | Đếm dòng lỗi theo chế độ | ✅ | `outputs/p1_ai4i_meta.json` (`facts`); `data/factory/data_facts.md` |
| P1.2 | EDA + luật | ✅ | `rule_flags()`, `rule_score()`; luật HDF/PWF/OSF khớp 100% nhãn, TWF báo sai nhiều (xem báo cáo) |
| P1.3 | Phát hiện bằng ML, ngưỡng recall 90% trên validation | ✅ | Isolation Forest (5 cảm biến), Isolation Forest (+ vật lý), Autoencoder; `outputs/p1_ai4i_e0.csv` |
| P1.4 | Bản ghi sự cố chuẩn hóa | ✅ | `outputs/incidents_ai4i.json` (cảnh báo của bộ chính trên test, hợp lệ `schemas/incident.schema.json`) |
| P1.5 | Truy vết ngược dùng chung 2 domain | ✅ | `src/d3/backward.py` (cùng công thức với `p2_experiments.backward_trace`) |
| P1.6 | Chạy E0–E3 trên AI4I | ✅ | E0: báo cáo này. E1–E3: pipeline trên 339 sự cố thật (`results/run_ai4i*.csv`) + mô phỏng 30 seed của P2/P3 |
| P1.7 | Luật hành động theo chế độ lỗi; E5 | ✅ | `p4_risk_action/kb.yaml` đã đối chiếu dữ liệu; E5: `docs/E5_E6_tu_dong.md`, `docs/E5_E6_chuyen_gia.md` |
| P1.8 | Slide phần Phát hiện | ⏳ | chờ làm slide |

## Quyết định

- **Bộ phát hiện chính** = bộ học máy có tỷ lệ báo sai thấp nhất trên **validation** (hiện là Isolation Forest +
  đặc trưng vật lý). Chọn tự động trong code (`main_detector` trong `p1_ai4i_meta.json`); test không dùng để chọn.
  Luật bị loại khỏi lựa chọn vì trùng luật sinh nhãn AI4I.
- Pipeline tích hợp đọc điểm của bộ chính qua cột `score_main` / `alarm_main` trong `outputs/p1_ai4i_scores.csv`.

## Output

| File | Nội dung |
|---|---|
| `p1_ai4i_report.md` | Bảng E0 (test), recall theo chế độ lỗi, các hạn chế phải nêu |
| `p1_ai4i_e0.csv` | E0 dạng dài (val + test, mọi bộ phát hiện, theo chế độ) |
| `p1_ai4i_scores.csv` | Điểm + cờ cảnh báo của mọi bộ cho 10.000 dòng, chế độ nghi ngờ theo luật |
| `incidents_ai4i.json` | Bản ghi sự cố mục 5.3 (gồm cả báo sai, `failure_mode = null`) |
| `p1_ai4i_meta.json` | Số liệu đếm, ngưỡng, bộ chính, tỷ lệ báo sai validation |
