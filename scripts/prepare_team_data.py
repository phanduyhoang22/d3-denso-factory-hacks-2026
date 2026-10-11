"""Chuẩn bị dữ liệu cho code P2/P3 từ data/factory/raw (không cần tải thêm).

  python scripts/prepare_team_data.py

  p3_graph/data/raw/ai4i2020.csv   ← data/factory/raw/ai4i/ai4i2020.csv
  p3_graph/data/raw/uci-secom.csv  ← secom.data + secom_labels.data, dạng CSV gộp (Time, 0..589, Pass/Fail)
P2 nhận đường dẫn qua tham số (--csv, --data, --labels), xem README.
"""
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "factory" / "raw"
P3_RAW = ROOT / "p3_graph" / "data" / "raw"

P3_RAW.mkdir(parents=True, exist_ok=True)
shutil.copy(RAW / "ai4i" / "ai4i2020.csv", P3_RAW / "ai4i2020.csv")

X = pd.read_csv(RAW / "secom" / "secom.data", sep=r"\s+", header=None)
X.columns = [str(c) for c in X.columns]
y = pd.read_csv(RAW / "secom" / "secom_labels.data", sep=r"\s+", header=None, names=["Pass/Fail", "ts"])
time = pd.to_datetime(y["ts"], format="%d/%m/%Y %H:%M:%S")
out = pd.concat([pd.DataFrame({"Time": time.dt.strftime("%Y-%m-%d %H:%M:%S")}), X, y[["Pass/Fail"]]], axis=1)
out.to_csv(P3_RAW / "uci-secom.csv", index=False)
assert out["Time"].notna().all()
print(f"ghi {P3_RAW / 'ai4i2020.csv'}\nghi {P3_RAW / 'uci-secom.csv'} ({len(out)} dòng, {int((out['Pass/Fail'] == 1).sum())} fail)")
