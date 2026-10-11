# D3 – Phần 2 (Truy vết tác động): giao diện cho P1, P3 và dashboard

## Chạy
```
pip install -r requirements.txt
python p2_impact_trace.py --csv ai4i2020.csv --out p2_outputs            # đầy đủ, khoảng 12 giây
python p2_impact_trace.py --csv ai4i2020.csv --out p2_outputs --fast     # bỏ random forest và quét độ nhạy, khoảng 2 giây
python p2_impact_trace.py --csv ai4i2020.csv --out p2_outputs --incidents sự_cố_từ_P1.json
python p2_experiments.py --csv ai4i2020.csv --out p2_outputs --seeds 30   # thí nghiệm E1-E4, khoảng 10 giây
python p2_secom.py --data secom/secom.data --labels secom/secom_labels.data --out p2_outputs/secom --seeds 30   # SECOM, khoảng 25 giây
AI4I_CSV=ai4i2020.csv SECOM_DIR=secom pytest -q test_p2.py test_p2_experiments.py test_p2_secom.py         # 71 test (39 + 23 + 9), khoảng 45 giây
```
Các file `p2_impact_trace.py`, `p2_schema.py`, `p2_experiments.py` phải nằm cùng thư mục.

## Dành cho P1 (phát hiện): đầu vào
Gửi một **danh sách JSON** các sự cố theo định dạng mục 5.3 của tài liệu D3
(schema: `p2_incident_record.schema.json`, ví dụ: `p2_example_incidents_from_P1.json`).

| Trường | Ý nghĩa | Ghi chú |
|---|---|---|
| `incident_id`, `machine_id` | Mã sự cố, mã máy | Bắt buộc |
| `time` hoặc `udi` | Thời điểm sự cố | `time` dạng `DD/MM/YYYY HH:MM` hoặc `YYYY-MM-DD HH:MM`, P2 tự đổi sang `udi`. Có cả hai thì `udi` được ưu tiên. Dòng thời gian dữ liệu hiện chạy từ 01/10/2026 06:00 (giả định takt 1 phút/sản phẩm), mốc ngoài khoảng này báo lỗi |
| `anomaly_type` | Loại bất thường | Văn bản tự do, chỉ lưu lại để hiển thị |
| `level` | Cao / Trung bình / Thấp | Quy đổi 0,9 / 0,6 / 0,3. Nếu có `severity` (số) thì dùng `severity` |
| `anomaly_score` | Điểm bất thường 0–1 | Lưu lại để hiển thị |
| `suspected_cause_group` | Nhóm nguyên nhân nghi ngờ | Khớp mã (TWF/HDF/PWF/OSF/RNF) hoặc tên tiếng Việt thì nhân điểm nguyên nhân đó (gợi ý, bằng chứng cảm biến vẫn quyết định). Không khớp (ví dụ "Ổ bi / lệch trục") thì ghi vào `trigger.details.hints_ignored`, không gây lỗi |
| `sensors`, `type` | 5 giá trị cảm biến và biến thể L/M/H | **Không bắt buộc**: nếu thiếu, P2 đọc từ tầng dữ liệu theo `udi` |
| `downtime_min` | Thời gian dừng ước lượng | Bắt buộc với máy chưa có mô hình nguyên nhân (mọi máy trừ M05) |

Nếu có cả `udi` và `time` thì hai giá trị phải khớp nhau (lệch tối đa 1 sản phẩm), nếu không báo lỗi.

**Không gửi nhãn lỗi** (TWF/HDF/PWF/OSF/RNF dạng cột 0/1). Dữ liệu sai sẽ báo `ValueError` kèm thông báo cụ thể.

**Xử lý lô:** một bản ghi hỏng không làm dừng cả lô. Bản ghi tốt vẫn ra `p2_report_<incident_id>.json`;
bản ghi lỗi được ghi vào `p2_errors.json` (số thứ tự, mã sự cố, loại lỗi, thông báo) và chương trình kết thúc với mã thoát 2.
`incident_id` được làm sạch khi đặt tên file (không thể ghi ra ngoài thư mục kết quả).

## Dành cho P3 (hành động, dashboard): đầu ra
Mọi tình huống dùng **một hình dạng duy nhất** theo `p2_impact_report.schema.json`:

| Khóa | Dùng để |
|---|---|
| `trigger` | Sự kiện gây ra: loại, nút nguồn, thời gian, bộ phận phụ trách. `details.history` có tần suất sự cố lịch sử của máy (số sự cố trên 1000 sản phẩm) và nguyên nhân phổ biến nhất |
| `causes` | Nguyên nhân xếp hạng. `score` là điểm tương đối, không phải xác suất đã hiệu chỉnh |
| `effect` | Thời gian dừng, thời gian dừng hiệu dụng (sau khi trừ máy dự phòng), mức nghiêm trọng và nguồn của nó |
| `affected` | Đối tượng bị ảnh hưởng, giảm dần theo `risk`, có `path`, `reason`, `owner_dept`, `cum_buffer_min` |
| `by_department` | Nhóm sẵn theo bộ phận (Bảo trì, Sản xuất, Kho & Logistics, Chất lượng, Kế hoạch sản xuất), **gồm cả bộ phận của nút nguồn** (`role: "source"`, ví dụ Bảo trì với sự cố máy) và các đối tượng bị ảnh hưởng (`role: "affected"`). Nút nguồn cũng là đối tượng bị ảnh hưởng thì `role: "source+affected"` (tình huống S2). `count` = số mục trong `items`. Chỉ liệt kê bộ phận có việc, nên có thể ít hơn 5 |
| `substitutes` | Máy dự phòng và tỷ lệ tải gánh được |
| `buffers` | Tồn kho/đệm nằm trên đường lan truyền, đơn vị là phút sản xuất, kèm loại (`raw_material`, `wip`, `finished_goods`): dùng cho hành động "dùng tồn kho dự phòng" |
| `direct_lots` | Lô có sản phẩm bị trễ trực tiếp |
| `contributing_incidents` | Với truy vết ngược từ đơn hàng: các sự cố đóng góp vào lỗi/trễ |
| `assumptions` | Các giả định giả lập, nên hiển thị trên dashboard |

Lưu ý khi đọc:
- Đơn hàng có thêm `delay_min`, `slack_min`, `miss_deadline`, `due`, `time_to_impact_min`.
- `risk` có thể là `null` ở tình huống truy vết ngược từ đơn hàng (dùng `defect_rate`).
- `selection` cho biết sự cố được chọn là trường hợp xấu nhất hay trung vị trong 339 sự cố.
- Điểm rủi ro **chưa** dùng tần suất sự cố lịch sử (chỉ cung cấp trong `history` để hiển thị).
- Khóa `eval_only` chỉ phục vụ đánh giá nội bộ, **không dùng**.

## Dành cho dashboard: đồ thị
`p2_graph_view_<tình huống>.json` (schema: `p2_graph_view.schema.json`), kèm `p2_graph_view_static.json` (chưa có rủi ro).
- `nodes[]`: `id`, `name`, `type`, `layer`, `owner_dept`, `risk` (null nếu không bị ảnh hưởng), `band` (`high` ≥ 0,5; `medium` ≥ 0,25; `low` > 0), `is_source`.
- `edges[]`: `source`, `target`, `rel`, `buffer_min`, `on_path` (true nếu nằm trên đường lan truyền, nên tô đậm).
- Chỉ gồm cảm biến, kiểu lỗi, máy, công đoạn, linh kiện, sản phẩm và các đơn hàng bị ảnh hưởng để hình gọn. Đồ thị đầy đủ nằm ở `p2_graph_nodes.csv` / `p2_graph_edges.csv` (nhập Neo4j được).

## Cách đọc `p2_metrics.json` (quan trọng khi thuyết trình)
- `notes`: ghi chú diễn giải, nên đọc trước.
- `backward`: **kiểm tra đường ống**, không phải độ chính xác ngoài thực tế (luật bằng chứng trùng luật sinh nhãn của AI4I). Có `n_by_mode`, `confusion`, `per_class`, macro-F1. RNF gần như không có mẫu.
- `ml_baseline`: đối chứng random forest. Bài test thiếu HDF cho thấy luật **không** hơn random forest khi nguyên nhân chưa từng xuất hiện (prior gần 0 triệt tiêu bằng chứng). `rule_prior_smoothing_sweep` là thăm dò làm sau khi thấy kết quả, chưa phải tham số đã chốt.
- `forward.wiring_check_*`: chỉ chứng minh đồ thị nối đúng, không phải độ chính xác dự báo.
- `forward_sensitivity`: tỷ lệ sự cố gây trễ hạn thay đổi mạnh theo giả định (dư thời gian giao hàng, tốc độ bù trễ, tỷ lệ tải máy dự phòng). Không trích một con số đơn lẻ.
- `hint_sensitivity`: gợi ý sai của P1 làm Top-1 giảm bao nhiêu theo hệ số `hint_boost`.

## Ba tình huống mẫu
- `p2_scenario_S1_machine_incident_worst.json`, `..._S1b_..._median.json`: sự cố máy M05.
- `p2_scenario_S2_order_backward.json`: đơn hàng có nhiều sản phẩm lỗi (truy vết ngược).
- `p2_scenario_S3_material_delay.json`: nhà cung cấp phôi A11 giao trễ 180 phút.

## Giả định cần xác nhận với DENSO
Đơn hàng, hạn giao, ưu tiên, vùng đệm, thời gian dừng theo từng loại lỗi, máy dự phòng M07
(gánh 30% tải), cơ cấu bộ phận phụ trách và takt 1 phút/sản phẩm đều là giả lập.
Tất cả nằm ở `CFG` và các hằng số đầu `p2_impact_trace.py`.
Dataset AI4I không có cảm biến rung nên kịch bản "ổ bi xuống cấp" trong tài liệu D3 không tái hiện được;
nguyên nhân hiện có là TWF, HDF, PWF, OSF, RNF.


## Thí nghiệm E1–E4 (`p2_experiments.py`)
Bổ sung phần tài liệu D3 mục 15, 17 (Part 3, Part 5) và 18 yêu cầu mà bản trước chưa có. Lệnh: `python p2_experiments.py --csv ai4i2020.csv --out p2_outputs --seeds 30`.

| Mã | Câu hỏi | Hệ thống | Baseline | Ground truth |
|---|---|---|---|---|
| E1 | Truy vết xuôi đúng phạm vi? | `trace_forward` trên đồ thị nhìn thấy | Chỉ báo công đoạn liền kề | Tập nút có mức ảnh hưởng thật ≥ 0,05, theo 4 tầng |
| E2 | Điểm rủi ro xếp đúng ưu tiên? | Điểm rủi ro `trace_forward` | Điểm = 1/số bước | `true_impact()` (mô hình dòng chảy khác công thức hệ thống) |
| E3 | Truy vết ngược tìm đúng máy gốc khi có nhiễu 0/25/50%? | pct_bất_thường × (λ + (1−λ)·reach) | Bất thường cao nhất; gần nhất theo thời gian | Máy gốc đã gán sự cố |
| E4 | Đồ thị thiếu 10/25/50% cạnh thì sao? | Lặp E1–E3 | Đồ thị đủ | như trên |

Thành phần mới: `generate_graph(seed, size)` (3 quy mô, sinh độc lập với sự cố), `observed_graph()` (trọng số/đệm có nhiễu, xóa cạnh),
`true_impact()` (ground truth), `Detector` (Isolation Forest, ngưỡng cố định recall 90% trên validation, bộ đặc trưng chọn theo validation),
`run_all()` (30 seed × 3 quy mô × 3 confounder × 4 mức xóa cạnh).

Đầu ra: `p2_results.csv` (mỗi dòng có seed, cấu hình và cột `root_sampling`), `p2_summary.csv` (mean/std), `p2_experiments_report.md` (bảng + kết luận tự sinh, trung thực), `p2_experiments_E4.png`, `p2_experiments_config.json`.

Cần nêu khi báo cáo:
- E1/E2 không phụ thuộc confounder nên được lặp lại qua 3 mức confounder (mean/std không đổi).
- Confounder chỉ đặt ở máy không thuộc tổ tiên của kết quả xấu và đồ thị chỉ bị xóa cạnh (không thêm cạnh sai), nên E3 ở 0% xóa cạnh dễ theo cấu trúc; phần đáng tin là xu hướng khi xóa cạnh.
- λ = 0,5 đặt trước khi chạy; bảng quét λ chỉ để tham khảo.
- Bộ phát hiện đã tối ưu sơ bộ (thêm đặc trưng vật lý) nhưng vẫn báo sai ~21% ở recall ~87% trên test; đây là P1, nếu P1 có detector tốt hơn thì thay `Detector`.
- Kết quả dựa trên đồ thị và tham số mô phỏng, chưa phải dữ liệu DENSO.

## Trạng thái P2 so với tài liệu D3
Xong: đồ thị 2 lớp, truy vết xuôi, truy vết ngược (nguyên nhân + từ đơn hàng), điểm rủi ro, 3 tình huống, giao diện JSON/schema cho P1/P3, đồ thị cho dashboard, E1–E4 với 30 seed, test.
Ngoài phạm vi P2 (thuộc P1/P3/P5): phát hiện chính thức, bảng gợi ý hành động và knowledge base, dashboard, E5 (chấm tay), E6 (phỏng vấn kỹ sư), slide.
Chưa có (mục 19, mở rộng): DTW, nhiều sự cố cùng lúc, tối ưu hóa hành động, SECOM.

## Hàm truy vết ngược dùng chung: `backward_trace()` (P1.5)
```python
import p2_experiments as E
top = E.backward_trace(graph_observed, outcome="ORD_1_03", anomaly_pct={"M101": 0.93, "M203": 0.40, ...}, topk=5)
# -> [{"rank":1,"machine":"M101","score":0.71,"anomaly":0.93,"reach":0.62,"hist_factor":1.1,"path":["M101","P1_1",...,"ORD_1_03"]}, ...]
```
- Đầu vào: đồ thị hệ thống nhìn thấy (có thể thiếu cạnh), nút kết quả xấu, điểm bất thường 0..1 của từng máy do P1 cung cấp.
- Điểm = pct_bất_thường × (λ + (1−λ)·reach) × hệ_số_lịch_sử^γ. Mặc định λ = 0,5, γ = 0 (không dùng lịch sử).
- `score` là điểm tương đối để xếp hạng, không phải xác suất; `path` là đường phụ thuộc tốt nhất trong đồ thị. Chỉ nói "nguyên nhân có khả năng".
- Máy không nối được tới kết quả (cạnh bị thiếu) vẫn được xếp theo điểm bất thường, nên suy giảm êm về baseline thay vì loại bỏ.

**Tần suất lỗi lịch sử theo máy:** mỗi máy có `hist_count` (số sự cố đếm được trong 20000 đơn vị lịch sử, tách khỏi kịch bản, có nhiễu Poisson).
Thử nghiệm cho thấy nhân trực tiếp hệ số này vào điểm không giúp Top-1 (làm giảm ở chế độ máy gốc ngẫu nhiên đều; không khác biệt có ý nghĩa ở chế độ tỷ lệ theo tần suất),
nên mặc định tắt. Xem mục "Tần suất lỗi lịch sử" cuối `p2_experiments_report.md`. Muốn dùng cần dữ liệu bảo trì thật của DENSO.


## Phần SECOM (`p2_secom.py`, việc P2.1–P2.7 và P2.9)
Chạy: `python p2_secom.py --data secom/secom.data --labels secom/secom_labels.data --out p2_outputs/secom --seeds 30`. Đầu ra trong `p2_outputs/secom/`:

| Việc | File | Nội dung |
|---|---|---|
| P2.1 | `data_facts_secom.md` | Số liệu đếm trực tiếp: 1567 dòng, 590 cảm biến, 104 fail (6,64%), timestamp thật 19/07–17/10/2008, bảng chia train/val/test |
| P2.2 | `secom_preprocess.joblib` | Tiền xử lý lưu được (bỏ cột thiếu >40%, bỏ hằng số, điền trung vị, chuẩn hóa, PCA 90% phương sai = 121 thành phần), chỉ fit trên train, chia 60/20/20 theo thời gian |
| P2.3 | `p2_secom_e0.csv`, `p2_secom_E0.png` | E0: luật 3-sigma, Isolation Forest, hồi quy logistic có class weight (không SMOTE), ngưỡng cố định recall 90% trên validation, CI bootstrap |
| P2.4 | `incidents_secom.json` | 293 bản ghi sự cố hợp lệ theo `INCIDENT_RECORD_SCHEMA`, `timestamp_is_synthetic = false`, nhãn thật chỉ nằm trong `eval_only` |
| P2.5 | `test_p2_secom.py::test_true_impact_hand_check` | `true_impact()` đã có; kiểm tra tay trên đồ thị 5 nút |
| P2.6 | `p2_secom_scenario_example.json`, `baseline_e3()` | 1 kịch bản SECOM chạy qua `backward_trace()` |
| P2.7 | `p2_results_secom.csv`, `p2_summary_secom.csv`, `p2_secom_report.md`, `p2_secom_E4.png` | E1–E4, 30 seed, cùng khung với AI4I (cột `domain = secom`) |
| P2.8 | `p2_phieu_phong_van_E6_E5.md` | Phiếu phỏng vấn kỹ sư và phiếu chấm E5 (việc của con người) |

Điểm cần nêu thẳng khi báo cáo SECOM:
- **Phát hiện SECOM chưa vượt ngẫu nhiên.** Chia theo thời gian, ROC-AUC của cả ba mô hình nằm trong khoảng 0,37–0,59 và khoảng tin cậy chứa 0,5. Test chỉ có 17 fail và validation 11 fail nên ngưỡng recall 90% không ổn định (gần như cảnh báo mọi dòng, báo sai ~93%).
- **Nguyên nhân khả dĩ:** dữ liệu tháng 10 lệch so với train tháng 7–9. Điểm bất thường của dòng fail trong tập sinh sự cố không cao hơn dòng pass.
- **Hệ quả cho E3:** baseline "bất thường cao nhất" xấp xỉ đoán ngẫu nhiên; phần hệ thống hơn baseline chủ yếu do cấu trúc đồ thị. E1 và E2 không phụ thuộc chất lượng phát hiện.
- **Giả định riêng của SECOM:** không có kiểu lỗi và thời gian dừng, dùng hằng số 45 phút (`EXP["secom_downtime_min"]`) và mức nghiêm trọng = điểm bất thường. Mỗi dòng SECOM test được gắn vào một máy của đồ thị mô phỏng (tương đương gắn vào công đoạn vì cạnh máy → công đoạn có trọng số 1, đệm 0).
- **Nguồn file:** `secom/` lấy từ bản sao trên GitHub (aimwts/ai_semicon-Data-Analysis) của dữ liệu UCI ID 179 (CC BY 4.0), đã đối chiếu số dòng, số cột, số fail và khoảng thời gian với mô tả UCI. Nên tải lại từ UCI để chắc chắn trước khi nộp.
