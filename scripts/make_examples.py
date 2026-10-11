"""Sinh file mẫu cho mỗi schema từ dữ liệu nhà máy thật (Part 0: ≥ 3 bản ghi mẫu).

  python scripts/make_examples.py

Output đầy đủ của một sự cố có hàng nghìn đơn hàng, nên file mẫu được RÚT GỌN: chỉ giữ
TOP_N đối tượng rủi ro cao nhất (vẫn hợp lệ schema). Đồ thị mẫu là đồ thị con quanh các đối tượng đó.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from d3 import RESULTS_DIR, ROOT, SCHEMA_DIR, graph_io  # noqa: E402
from d3.factory import incidents_for  # noqa: E402
from d3.pipeline import run_scenario  # noqa: E402
from d3.schema_io import validate  # noqa: E402

TOP_N = 15
CASES = [  # (dataset, chỉ số sự cố) — đủ loại: OSF ở AI4I, lỗi chồng, SECOM
    ("ai4i", next(i for i, x in enumerate(incidents_for("ai4i")) if x["failure_mode"] == "OSF")),
    ("ai4i", next(i for i, x in enumerate(incidents_for("ai4i")) if "+" in x["failure_mode"])),
    ("secom", 0),
]


def dump(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  ghi", path.relative_to(ROOT))


def shrink(out, G):
    risk = out["risk"][:TOP_N]
    keep = {r["node_id"] for r in risk}
    fwd = [f for f in out["forward"] if f["node_id"] in keep]
    out = {**out, "risk": risk, "forward": fwd}
    nodes = {n for f in fwd for n in f["path"]} | {b["node_id"] for b in out["backward"]}
    return out, graph_io.to_json(G.subgraph(nodes).copy())


def main():
    ex = SCHEMA_DIR / "examples"
    for old in ex.glob("*.json"):
        old.unlink()
    for ds in ("ai4i", "secom"):
        dump(list(incidents_for(ds)), RESULTS_DIR / f"incidents_{ds}.json")
    incidents = []
    for k, (ds, idx) in enumerate(CASES):
        out, _, ctx = run_scenario(idx, {"dataset": ds}, check_schema=False)
        out, graph = shrink(out, ctx["graph_observed"])
        validate("trace_output", out)
        validate("graph", graph)
        dump(out, ex / f"scenario_{k}.example.json")
        dump(graph, ex / f"graph_{k}.example.json")
        incidents.append(out["incident"])
    dump(incidents, ex / "incidents.example.json")


if __name__ == "__main__":
    main()
