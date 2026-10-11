# Ontology & schema đồ thị – D3 (P3.1)

Nguồn sự thật trong code: `d3p3/ontology.py`. JSON Schema: `schemas/graph.schema.json`.

## Chuỗi phụ thuộc

```
Cảm biến ──monitors──▶ Máy ──operates_in──▶ Công đoạn ──produces──▶ Linh kiện ──used_in──▶ Sản phẩm ──fulfills──▶ Đơn hàng
                                             │  ▲
                                             └feeds┘ (công đoạn trước → công đoạn sau trong cùng line)
```

Mọi cạnh hướng **thượng nguồn → hạ nguồn**. Truy vết xuôi đi theo chiều cạnh, truy vết ngược đi ngược chiều. Đồ thị luôn là DAG (có test).

## Loại node

| type | Tiếng Việt | layer | ID mẫu | Nhánh | Thuộc tính chính |
|---|---|---|---|---|---|
| `sensor` | Cảm biến | 0 | `S_M05_torque`, `S_P13_g1` | A / B | `measures` |
| `machine` | Máy | 1 | `M05` | A (AI4I) / B | `line`, `machine_type` (L/M/H), `spare_capacity`, `alt_machines`, `data_source`, `hist_fail_rate` |
| `process` | Công đoạn | 2 | `P02` | A / B (SECOM) | `line`, `step`, `wip_buffer_true` (ẩn), `data_source`, `hist_fail_rate` |
| `component` | Linh kiện | 3 | `A13` | shared | `line`, `daily_usage`, `safety_stock`, `lead_time_days`, `n_alt_sources` |
| `product` | Sản phẩm | 4 | `X1` | shared | `family_line` |
| `order` | Đơn hàng | 5 | `O43` | shared | `priority` (1–3), `due_in_days`, `quantity` |

**Nhánh dữ liệu (mục 16.2):**

- Nhánh A: node **Máy** gắn bản ghi **AI4I 2020** (5 cảm biến/máy). Sự cố AI4I phát sinh tại Máy.
- Nhánh B: node **Công đoạn** gắn bản ghi **SECOM** (590 cảm biến gom thành 3 node nhóm/công đoạn). Sự cố SECOM phát sinh tại Công đoạn.
- Linh kiện / Sản phẩm / Đơn hàng dùng chung cho cả hai nhánh.

## Loại cạnh và ý nghĩa trọng số (0 < w ≤ 1)

| type | Từ → Tới | Ý nghĩa `weight` |
|---|---|---|
| `monitors` | Sensor → Machine/Process | luôn 1 (quan hệ quan sát, không lan truyền) |
| `operates_in` | Machine → Process | tỷ trọng tải của máy trong công đoạn (tổng theo công đoạn = 1) |
| `feeds` | Process → Process | mức phụ thuộc của công đoạn sau vào công đoạn trước |
| `produces` | Process → Component | tỷ trọng linh kiện do công đoạn này làm ra (nguồn thứ 2 có trọng số thấp hơn) |
| `used_in` | Component → Product | mức trọng yếu của linh kiện trong sản phẩm (BOM) |
| `fulfills` | Product → Order | tỷ trọng sản phẩm trong đơn hàng |

Cạnh lan truyền: `operates_in, feeds, produces, used_in, fulfills`. "Máy thay thế" là **thuộc tính** (`alt_machines`) chứ không phải cạnh, để không làm sai lan truyền; P4 dùng nó cho đề xuất "chuyển tải sang M07".

## Mô hình lan truyền (dùng cho cả ground truth và truy vết xuôi)

```
impact(v) = (1 − buffer(v)) · [1 − Π_{u ∈ cha(v)} (1 − impact(u) · w(u,v))]
impact(gốc) = severity của sự cố
buffer(Linh kiện) = min(0.7, cover / (cover + lead_time)),  cover = safety_stock / daily_usage (ngày)
buffer(Công đoạn) = wip_buffer_true  (chỉ có ở graph_full)
```

Đối tượng được coi là **bị ảnh hưởng** nếu `impact ≥ 0.10`.

Khác biệt giữa **ground truth** (`true_impact` trên `graph_full`) và **hệ thống** (`forward_trace` trên `graph_observed`):

| | graph_full (đáp án) | graph_observed (hệ thống thấy) |
|---|---|---|
| Trọng số cạnh | thật | × nhiễu log-normal σ = 0.25 |
| Tồn kho dự phòng | thật | × nhiễu log-normal σ = 0.20 |
| Bộ đệm WIP của công đoạn | có | **không biết** (coi = 0) |
| Cạnh | đủ | thiếu 0/10/25/50% (E4) |

Nhờ vậy E1/E2 không tự chấm bằng chính công thức của mình trên cùng dữ liệu (mục 18.4).

## Quy ước ID và đầu ra

- ID ổn định theo seed: cùng `(seed, size)` → cùng đồ thị (có test).
- Đồ thị demo mục 10 (`demo_graph()`): cố định, cho đúng chuỗi `M05 → P02 → A13 → X1 → O43 / O58`; M07 là máy thay thế cùng công đoạn P02; A13 có tồn kho dự phòng thấp (1 ngày, lead time 7 ngày, 0 nguồn thay thế).
- Xuất cho dashboard: `export.graph_to_json(G, trace)` – node-link, có `is_root`, `affected`, `est_impact`, `hops`, `on_impact_path`.
