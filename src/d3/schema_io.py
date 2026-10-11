"""Kiểm tra dữ liệu theo schema đã đóng băng ở Part 0 (mốc C1)."""
import json
from functools import lru_cache

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from . import SCHEMA_DIR

SCHEMAS = {
    "incident": "incident.schema.json",
    "graph": "graph.schema.json",
    "trace_output": "trace_output.schema.json",
}


@lru_cache(maxsize=None)
def _registry():
    resources = []
    for fname in SCHEMAS.values():
        schema = json.loads((SCHEMA_DIR / fname).read_text(encoding="utf-8"))
        resources.append((fname, Resource.from_contents(schema)))
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(kind):
    schema = json.loads((SCHEMA_DIR / SCHEMAS[kind]).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=_registry())


def errors(kind, obj):
    """Trả về danh sách lỗi (chuỗi). Rỗng = hợp lệ."""
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}"
            for e in validator(kind).iter_errors(obj)]


def validate(kind, obj):
    errs = errors(kind, obj)
    if errs:
        raise ValueError(f"{kind} không hợp lệ:\n  " + "\n  ".join(errs[:20]))


def validate_file(path):
    """Đoán loại schema theo tên file: incidents_*.json, graph*.json, scenario*.json / trace*.json."""
    name = path.name.lower()
    data = json.loads(path.read_text(encoding="utf-8"))
    if name.startswith("incident"):
        items = data if isinstance(data, list) else [data]
        return [f"[{i}] {e}" for i, x in enumerate(items) for e in errors("incident", x)]
    if name.startswith("graph"):
        return errors("graph", data)
    if name.startswith(("scenario", "trace")):
        return errors("trace_output", data)
    raise ValueError(f"Không đoán được schema cho {path.name}")
