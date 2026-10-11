"""Kiểm tra file JSON theo schema. Mặc định kiểm tra schemas/examples/ và results/*.json.

  python scripts/validate_schemas.py                         # mặc định
  python scripts/validate_schemas.py results/incidents_ai4i.json

Quy ước tên file: incidents_*.json | graph*.json | scenario*.json / trace*.json
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from d3.schema_io import validate_file  # noqa: E402


def main(paths):
    files = [Path(p) for p in paths] or sorted((ROOT / "schemas" / "examples").glob("*.json")) + \
        sorted((ROOT / "results").glob("*.json"))
    bad = 0
    for p in files:
        try:
            errs = validate_file(p)
        except ValueError as e:
            print(f"SKIP {p.name}: {e}")
            continue
        print(("OK  " if not errs else "FAIL"), p.name)
        for e in errs[:10]:
            print("     ", e)
        bad += bool(errs)
    print(f"\n{len(files) - bad}/{len(files)} file hợp lệ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
