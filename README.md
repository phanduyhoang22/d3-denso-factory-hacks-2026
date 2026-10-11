# D3 – Hệ thống phát hiện sự cố và truy vết tác động trong chuỗi sản xuất

DENSO Factory Hacks 2026 · Bài toán D3 · Luồng: **Phát hiện → Truy vết → Đánh giá → Ưu tiên → Hành động**

Tài liệu ý tưởng: `docs/D3_He_thong_phat_hien_su_co_va_truy_vet_tac_dong.docx` · Tổng hợp kết quả: `docs/KET_QUA_TONG_HOP.md` · Schema đã chốt + kịch bản demo: `schemas/README.md` · Phiếu E5/E6: `docs/E5_E6_phieu.md`

## Cấu trúc theo phân công

| Thư mục | Người | Nội dung |
|---|---|---|
| `data/factory/` | cả nhóm | Dữ liệu nhà máy: 443 sự cố thật (AI4I 339, SECOM 104) gán vào 50 máy / 10 công đoạn; routing, 60.000 đơn hàng (mô phỏng); `raw/` AI4I + SECOM gốc; `src/` code sinh dữ liệu |
| `p1_detection/` | P1 – Việt | Phát hiện AI4I (luật, Isolation Forest, Autoencoder), E0, bản ghi sự cố `incidents_ai4i.json` |
| `p2_secom_impact/` | P2 – Thành | Phát hiện SECOM + E0, `true_impact`, truy vết tác động, E1–E4 (đồ thị P2), phiếu phỏng vấn E5/E6 |
| `p3_graph/` | P3 – Tình | Ontology, bộ sinh kịch bản, truy vết xuôi, E1/E4 (đồ thị P3), 17 test |
| `p4_risk_action/` | P4 – Trang | Kế hoạch thí nghiệm, công thức rủi ro, `recommend()` + `kb.yaml`, `aggregate.py` |
| `src/d3/`, `app/`, `scripts/`, `schemas/` | P5 – Phan Hoàng | Schema, pipeline tích hợp trên dữ liệu nhà máy, runner, dashboard |
| `results/` | P5 | Kết quả chạy pipeline tích hợp (E1–E3, E6) trên 443 sự cố thật |
| `docs/` | | Tổng hợp kết quả, dàn ý slide, theo dõi việc, đề bài |

Pipeline tích hợp (`src/d3/`) dùng **module thật** của từng người:

| Bước | Hàm | Nguồn |
|---|---|---|
| Phát hiện | điểm bất thường AI4I | P1 – `p1_detection/outputs/p1_ai4i_scores.csv` (Isolation Forest) |
| Đồ thị + kịch bản | `generate_scenario` | P5 – `src/d3/factory.py` đọc `data/factory/` |
| Truy vết xuôi | `forward_trace` | duyệt đồ thị nhà máy (`src/d3/mock.py`)* |
| Điểm rủi ro | `risk_score`, `baseline_e2` | P4 – `p4_risk_action/risk.py` qua `src/d3/risk.py` |
| Truy vết ngược | `backward_trace`, `baseline_e3` | P1 – `src/d3/backward.py` (cùng công thức với P2) |
| Hành động | `recommend` | P4 – `p4_risk_action/recommend.py` + `kb.yaml` qua `src/d3/action.py` |

\* `forward_trace` của P3 chạy trên ontology riêng của P3 (có `feeds`, `used_in`, noisy-OR), không cùng cấu trúc với dữ liệu nhà máy, nên pipeline tích hợp duyệt đồ thị trực tiếp.

## Cài đặt

```bash
pip install -r requirements.txt
python scripts/prepare_team_data.py      # tạo p3_graph/data/raw/ từ data/factory/raw (cho code P3)
```
Trên Windows đặt `PYTHONUTF8=1` (test CLI của P2 đọc output UTF-8).

## Chạy

```bash
streamlit run app/dashboard.py                                  # dashboard: chọn 1 trong 443 sự cố thật
python p1_detection/p1_ai4i.py                                  # P1: E0 AI4I + incidents_ai4i.json
python scripts/run_experiments.py --dataset ai4i --out results/run_ai4i.csv
python scripts/run_experiments.py --dataset ai4i --confounders alarms --out results/run_ai4i_alarms.csv
python scripts/run_experiments.py --dataset secom --out results/run_secom.csv
python scripts/validate_schemas.py                              # kiểm tra JSON theo schema

# Code từng người (chạy trong thư mục tương ứng)
cd p2_secom_impact && python p2_experiments.py --csv ../data/factory/raw/ai4i/ai4i2020.csv --out p2_outputs --seeds 30
cd p2_secom_impact && python p2_secom.py --data ../data/factory/raw/secom/secom.data --labels ../data/factory/raw/secom/secom_labels.data --out p2_outputs/secom --seeds 30
cd p3_graph && python scripts/run_experiments_p3.py --seeds 30 && python scripts/summarize_p3.py
```

Test: `cd p3_graph && python -m pytest -q tests` (17) · `cd p2_secom_impact && AI4I_CSV=../data/factory/raw/ai4i/ai4i2020.csv SECOM_DIR=../data/factory/raw/secom python -m pytest -q` (71).

## Ghép / thay module

`src/d3/contracts.py` liệt kê tên hàm, module, owner, chữ ký. Đặt hàm vào đúng module là registry tự dùng; runner
ghi cột `impl` (`real`/`mock`) cho mỗi dòng kết quả. Dashboard hiện module nào đang chạy ở thanh bên.

## Giả định cần nêu khi báo cáo

- Đồ thị nhà máy, routing, đơn hàng, ưu tiên, hạn giao là **mô phỏng**; chỉ tín hiệu và nhãn lỗi AI4I/SECOM là thật.
- AI4I là dữ liệu tổng hợp, timestamp giả (mọi máy bắt đầu 01/01/2026 00:00, 10 phút/dòng).
- Đồ thị nhà máy chưa có trọng số cạnh (= 1), nên **E2 trên pipeline tích hợp chưa đo được** (Spearman = NaN);
  E2 có số liệu trên đồ thị mô phỏng của P2 và P3.
- SECOM trong pipeline tích hợp dùng nhãn thật (`detector = "label"`); phát hiện SECOM của P2 chưa vượt ngẫu nhiên.
- Chỉ nói "nguyên nhân **khả dĩ**", không khẳng định nhân quả.

## Checklist chống sai số (mục 18.2)

- [x] Đồ thị sinh **độc lập với lỗi** (P3, P2, `data/factory/src`).
- [x] SECOM chia theo thời gian, AI4I chia phân tầng (P1, P2, P3).
- [x] Scaler, PCA, ngưỡng chỉ fit trên train; ngưỡng cố định recall 90% trên validation.
- [x] Pipeline chỉ nhìn `graph_observed`; thứ tự sự cố được xáo theo seed (tránh lộ đáp án khi bằng điểm).
- [x] Không SMOTE, không sinh dòng lỗi giả; RNF loại khỏi đánh giá theo chế độ.
