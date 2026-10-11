"""Hợp đồng interface giữa các module (Part 0). Đóng băng cùng schema ở mốc C1.

Mỗi người viết hàm THẬT của mình vào đúng module + tên hàm dưới đây, cùng chữ ký.
Registry sẽ tự dùng bản thật nếu tìm thấy, nếu không thì dùng bản mock (d3/mock.py).

Kiểu dữ liệu:
  G           networkx.DiGraph, node attr theo graph.schema.json (type, department, ...),
              edge attr: relation, weight. Chuyển JSON qua d3.graph_io.
  incident    dict theo incident.schema.json
  forward     list[dict] theo trace_output.schema.json#/properties/forward
  risk        list[dict] theo .../risk     (sắp giảm dần)
  backward    list[dict] theo .../backward (rank 1..k)
  actions     list[dict] theo .../actions

Tên hàm          Module thật       Owner  Chữ ký
---------------  ----------------  -----  ------------------------------------------------------------
generate_scenario d3.scenario      P3     (seed:int, config:dict) -> dict với các khóa:
                                            graph_full, graph_observed, incidents, root_incident,
                                            bad_outcome_node, forward_truth:set, backward_truth:str,
                                            true_impact:dict[node_id, float]
forward_trace     d3.tracing       P3     (G, incident) -> forward
backward_trace    d3.backward      P1     (G, incidents, bad_outcome_node, k=3) -> backward
risk_score        d3.risk          P4     (G, forward, incident) -> risk
recommend         d3.action        P4     (G, incident, risk, backward) -> actions
baseline_e1       d3.tracing       P3     (G, incident) -> set[node_id]
baseline_e2       d3.risk          P4     (G, forward, incident) -> list[{node_id, risk_score}]
baseline_e3       d3.backward      P2     (incidents, k=3) -> list[node_id]

Quy tắc:
  - Pipeline chỉ được nhìn graph_observed + incidents (không đọc is_confounder, true_impact, *_truth).
  - Mọi hàm ngẫu nhiên nhận seed/rng từ ngoài, không dùng random toàn cục.
"""

CONTRACTS = {
    "generate_scenario": "d3.scenario",
    "forward_trace": "d3.tracing",
    "backward_trace": "d3.backward",
    "risk_score": "d3.risk",
    "recommend": "d3.action",
    "baseline_e1": "d3.tracing",
    "baseline_e2": "d3.risk",
    "baseline_e3": "d3.backward",
}
