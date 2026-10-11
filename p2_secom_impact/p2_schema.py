# -*- coding: utf-8 -*-
"""
Hợp đồng giao diện của P2 (D3). Đây là "nguồn sự thật" cho P1 (đầu vào) và P3 (đầu ra).

  * INCIDENT_RECORD_SCHEMA : bản ghi sự cố P1 gửi cho P2
  * IMPACT_REPORT_SCHEMA   : báo cáo P2 trả cho P3 (mọi tình huống dùng chung 1 hình dạng)

Quy ước:
  - risk: số trong [0, 1]; null khi tình huống truy vết ngược (đơn hàng) không có điểm rủi ro.
  - Thời gian là chuỗi 'YYYY-MM-DD HH:MM' (giả định takt 1 phút/sản phẩm, xem assumptions).
  - Khóa 'eval_only' chỉ phục vụ đánh giá nội bộ, P3 không dùng.
"""
from __future__ import annotations

import json
from pathlib import Path

try:
    from jsonschema import ValidationError
except ImportError:                                  # chưa cài jsonschema: dùng lớp rỗng để except vẫn hợp lệ
    class ValidationError(Exception):
        pass

SENSOR_COLUMNS = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]",
                  "Torque [Nm]", "Tool wear [min]"]
_NUM_OR_NULL = {"type": ["number", "null"]}
_STR_OR_NULL = {"type": ["string", "null"]}

INCIDENT_RECORD_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "P2 IncidentRecord (đầu vào từ P1)",
    "description": ("Một sự cố do P1 phát hiện, theo định dạng mục 5.3 của tài liệu D3 "
                    "(mã sự cố, thời gian, mã máy, loại bất thường, mức độ, điểm bất thường, nhóm nguyên nhân nghi ngờ). "
                    "Cần 'udi' HOẶC 'time'. Với máy có mô hình nguyên nhân (M05), nếu thiếu 'sensors'/'type' thì P2 tự đọc "
                    "từ tầng dữ liệu theo udi. Với máy khác cần 'downtime_min' và 'severity' (hoặc 'level') do P1 ước lượng."),
    "type": "object",
    "required": ["incident_id", "machine_id"],
    "anyOf": [{"required": ["udi"]}, {"required": ["time"]}],
    "properties": {
        "incident_id": {"type": "string"},
        "udi": {"type": "integer", "minimum": 1,
                "description": "Số thứ tự sản phẩm đang gia công khi sự cố xảy ra (liên kết với đơn hàng). Ưu tiên hơn 'time'."},
        "time": {"type": "string", "examples": ["02/10/2026 17:27", "2026-10-02 17:27"],
                 "description": "Thời điểm sự cố. Dùng khi chưa có udi; P2 quy đổi sang udi theo takt giả định."},
        "machine_id": {"type": "string", "examples": ["M05"]},
        "anomaly_type": {"type": "string", "description": "Loại bất thường (văn bản tự do), chỉ lưu lại để hiển thị."},
        "level": {"type": "string", "description": "Mức độ: Cao / Trung bình / Thấp. Quy đổi 0.9 / 0.6 / 0.3 nếu không có 'severity'."},
        "suspected_cause_group": {
            "oneOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}],
            "description": ("Nhóm nguyên nhân P1 nghi ngờ. Khớp mã (TWF/HDF/PWF/OSF/RNF) hoặc tên tiếng Việt thì nhân điểm "
                            "nguyên nhân đó; không khớp thì ghi vào trigger.details.hints_ignored.")},
        "type": {"enum": ["L", "M", "H"], "description": "Biến thể sản phẩm."},
        "product_id": {"type": "string"},
        "sensors": {
            "type": "object",
            "required": SENSOR_COLUMNS,
            "properties": {c: {"type": "number"} for c in SENSOR_COLUMNS},
            "description": "Giá trị cảm biến tại thời điểm sự cố, khóa là tên cột AI4I.",
        },
        "anomaly_score": {"type": "number", "minimum": 0, "maximum": 1},
        "severity": {"type": "number", "minimum": 0, "maximum": 1,
                     "description": "Nếu có thì ưu tiên hơn mức nghiêm trọng P2 tự suy ra từ nguyên nhân."},
        "downtime_min": {"type": "number", "minimum": 0},
        # trường bổ sung của Part 0 (tài liệu D3, mục 17.3): truy nguồn dữ liệu và cờ timestamp giả định
        "node_id": {"type": "string", "description": "Mã nút trong đồ thị mà sự cố gắn vào (thường trùng machine_id)."},
        "dataset": {"type": "string", "examples": ["AI4I2020", "SECOM"], "description": "Nguồn dữ liệu của sự cố."},
        "timestamp_is_synthetic": {"type": "boolean",
                                   "description": "true nếu 'time' là timestamp giả định theo thứ tự dòng (AI4I không có thời gian thật)."},
    },
    "additionalProperties": True,
}

_AFFECTED_ITEM = {
    "type": "object",
    "required": ["id", "name", "type", "layer", "owner_dept", "risk", "path", "reason"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "type": {"enum": ["process", "part", "product", "order"]},
        "layer": {"enum": ["logic", "business"]},
        "owner_dept": _STR_OR_NULL,
        "risk": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "path": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
        # chỉ có ở đơn hàng:
        "reach": {"type": "number"}, "delay_min": {"type": "number"}, "slack_min": {"type": "number"},
        "miss_deadline": {"type": "boolean"}, "priority": {"type": "integer"}, "product": {"type": "string"},
        "qty": {"type": "integer"}, "customer": {"type": "string"}, "due": {"type": "string"},
        "time_to_impact_min": {"type": "number"}, "direct_units": {"type": "integer"},
        "cum_buffer_min": {"type": "number", "description": "Đệm tích lũy (phút sản xuất) dọc đường đi tới đối tượng."},
        "defect_rate": {"type": "number"},
    },
    "additionalProperties": True,
}

IMPACT_REPORT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "P2 ImpactReport (đầu ra cho P3)",
    "type": "object",
    "required": ["schema_version", "scenario", "trigger", "causes", "effect", "affected",
                 "by_department", "substitutes", "buffers", "direct_lots", "contributing_incidents", "assumptions"],
    "properties": {
        "schema_version": {"const": "p2.impact_report.v1"},
        "scenario": {"enum": ["machine_incident", "order_backward", "material_delay"]},
        "selection": _STR_OR_NULL,
        "trigger": {
            "type": "object",
            "required": ["type", "id", "source_node", "time"],
            "properties": {
                "type": {"enum": ["machine_incident", "defective_order", "supplier_delay"]},
                "id": {"type": "string"}, "source_node": {"type": "string"},
                "owner_dept": _STR_OR_NULL, "time": {"type": "string"},
                "details": {"type": "object"},
            },
        },
        "causes": {
            "type": "array",
            "items": {"type": "object", "required": ["cause", "name", "score"],
                      "properties": {"cause": {"type": "string"}, "name": {"type": "string"},
                                     "score": {"type": "number", "minimum": 0, "maximum": 1},
                                     "prior": _NUM_OR_NULL, "evidence": _NUM_OR_NULL}},
            "description": "Xếp hạng giảm dần theo score (điểm tương đối, không phải xác suất đã hiệu chỉnh).",
        },
        "effect": {
            "type": "object",
            "required": ["downtime_min", "effective_downtime_min", "severity", "severity_source"],
            "properties": {"downtime_min": _NUM_OR_NULL, "effective_downtime_min": _NUM_OR_NULL,
                           "severity": _NUM_OR_NULL,
                           "severity_source": {"enum": ["cause_mixture", "P1", "assumed", None]}},
        },
        "affected": {"type": "array", "items": _AFFECTED_ITEM,
                     "description": "Sắp xếp giảm dần theo risk (truy vết xuôi)."},
        "by_department": {
            "type": "object",
            "description": ("Nhóm 'affected' VÀ nút nguồn theo bộ phận để P3 lập bảng hành động. "
                            "Mục của nút nguồn có role='source' (hoặc 'source+affected'). count = số mục trong items."),
            "additionalProperties": {
                "type": "object", "required": ["count", "max_risk", "items", "roles"],
                "properties": {"count": {"type": "integer"}, "max_risk": {"type": "number"},
                               "roles": {"type": "array", "items": {"enum": ["affected", "source", "source+affected"]}},
                               "items": {"type": "array", "items": {
                                   "type": "object", "required": ["id", "type", "risk", "role"],
                                   "properties": {"id": {"type": "string"}, "type": {"type": "string"},
                                                  "risk": _NUM_OR_NULL,
                                                  "role": {"enum": ["affected", "source", "source+affected"]}}}}},
            },
        },
        "substitutes": {"type": "array", "items": {
            "type": "object", "required": ["machine_id", "process", "capacity_share"],
            "properties": {"machine_id": {"type": "string"}, "name": {"type": "string"},
                           "process": {"type": "string"}, "capacity_share": {"type": "number"}}}},
        "buffers": {"type": "array", "description": "Tồn kho/đệm nằm trên đường lan truyền (đơn vị: phút sản xuất).",
                    "items": {"type": "object", "required": ["src", "dst", "buffer_min"],
                              "properties": {"src": {"type": "string"}, "dst": {"type": "string"},
                                             "buffer_min": {"type": "number"},
                                             "kind": {"enum": ["raw_material", "wip", "finished_goods", None]}}}},
        "direct_lots": {"type": "array", "items": {
            "type": "object", "required": ["lot", "units_delayed"],
            "properties": {"lot": {"type": "string"}, "units_delayed": {"type": "integer"}}}},
        "contributing_incidents": {"type": "array", "items": {"type": "object"}},
        "assumptions": {"type": "object", "required": ["business_layer", "note"]},
        "eval_only": {"type": "object"},
    },
}


GRAPH_VIEW_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "P2 GraphView (đồ thị rút gọn cho dashboard)",
    "type": "object",
    "required": ["schema_version", "nodes", "edges"],
    "properties": {
        "schema_version": {"const": "p2.graph_view.v1"},
        "scenario": _STR_OR_NULL,
        "nodes": {"type": "array", "items": {
            "type": "object", "required": ["id", "name", "type", "layer", "risk", "band", "is_source"],
            "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "type": {"type": "string"},
                           "layer": {"enum": ["logic", "business"]}, "owner_dept": _STR_OR_NULL,
                           "risk": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                           "band": {"enum": ["high", "medium", "low", None]}, "is_source": {"type": "boolean"}}}},
        "edges": {"type": "array", "items": {
            "type": "object", "required": ["source", "target", "rel", "on_path"],
            "properties": {"source": {"type": "string"}, "target": {"type": "string"}, "rel": {"type": "string"},
                           "buffer_min": _NUM_OR_NULL, "on_path": {"type": "boolean"}}}},
        "legend": {"type": "object"},
    },
}


def validate(instance: dict, schema: dict) -> bool | None:
    """Kiểm tra theo schema. Trả None nếu chưa cài thư viện 'jsonschema' (pip install jsonschema)."""
    try:
        import jsonschema
    except ImportError:
        return None
    jsonschema.validate(instance, schema)
    return True


def write_schemas(out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, sch in [("p2_incident_record.schema.json", INCIDENT_RECORD_SCHEMA),
                      ("p2_impact_report.schema.json", IMPACT_REPORT_SCHEMA),
                      ("p2_graph_view.schema.json", GRAPH_VIEW_SCHEMA)]:
        (out / name).write_text(json.dumps(sch, ensure_ascii=False, indent=2), encoding="utf-8")
