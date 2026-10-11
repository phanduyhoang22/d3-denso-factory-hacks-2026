"""Nạp AI4I 2020 / SECOM, chia train/val/test đúng quy tắc 18.2 và chấm điểm bất thường.

Detector ở đây là BẢN MOCK (Isolation Forest đơn giản) để bộ sinh kịch bản chạy được
end-to-end trước khi có model của P1/P2. Muốn dùng model thật: truyền `score_fn`
vào `load_domain()` hoặc ghi đè cột `anomaly_score`.

Quy tắc chống sai số được tôn trọng:
* AI4I chia ngẫu nhiên phân tầng theo nhãn; SECOM chia theo thời gian (không xáo trộn).
* Scaler / PCA / Isolation Forest / ngưỡng chỉ fit trên phần train.
* Ngưỡng cố định: recall 90% trên validation.
* Tần suất lỗi lịch sử (hist_fail_rate) chỉ dùng phần train (xem assign.py).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from . import sim_params as SP
from .ontology import DOMAIN_AI4I, DOMAIN_SECOM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATHS = {
    DOMAIN_AI4I: os.path.join(ROOT, "data", "raw", "ai4i2020.csv"),
    DOMAIN_SECOM: os.path.join(ROOT, "data", "raw", "uci-secom.csv"),
}
AI4I_FEATURES = ["Air temperature [K]", "Process temperature [K]",
                 "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
MODE_PRIORITY = ["PWF", "HDF", "OSF", "TWF", "RNF"]  # chọn mode nặng nhất nếu nhiều cờ
TARGET_RECALL = 0.90


@dataclass
class DomainData:
    domain: str
    rows: pd.DataFrame            # row_id, split, is_fail, mode, anomaly_score, detected, (type)
    threshold: float
    meta: dict = field(default_factory=dict)

    def pool(self, split: str, fail: bool | None = None, **eq) -> pd.DataFrame:
        r = self.rows[self.rows.split == split]
        if fail is not None:
            r = r[r.is_fail == fail]
        for k, v in eq.items():
            r = r[r[k] == v]
        return r


# --------------------------------------------------------------------------- helpers
def _normalize(raw_train: np.ndarray, raw: np.ndarray) -> np.ndarray:
    """Đưa điểm thô về [0,1] bằng phân vị so với điểm train (fit trên train)."""
    ref = np.sort(raw_train)
    return np.searchsorted(ref, raw, side="right") / len(ref)


def _threshold_at_recall(scores_val: np.ndarray, y_val: np.ndarray, recall=TARGET_RECALL):
    pos = np.sort(scores_val[y_val == 1])
    if len(pos) == 0:
        return 1.0
    k = int(np.floor((1 - recall) * len(pos)))
    return float(pos[k])


def _detector_meta(rows, thr):
    v = rows[rows.split == "val"]
    t = rows[rows.split == "test"]
    out = {"threshold": thr}
    for name, d in (("val", v), ("test", t)):
        y, s = d.is_fail.values, d.anomaly_score.values >= thr
        tp, fp = int((s & y).sum()), int((s & ~y).sum())
        out[f"{name}_recall"] = tp / max(1, int(y.sum()))
        out[f"{name}_precision"] = tp / max(1, tp + fp)
        out[f"{name}_false_alarm_rate"] = fp / max(1, int((~y).sum()))
    return out


# --------------------------------------------------------------------------- AI4I
def load_ai4i(path: str | None = None, seed: int = SP.DATA_SPLIT_SEED) -> DomainData:
    df = pd.read_csv(path or DEFAULT_PATHS[DOMAIN_AI4I], encoding="utf-8-sig")
    is_fail = df["Machine failure"].values.astype(bool)

    def mode_of(r):
        for m in MODE_PRIORITY:
            if r[m] == 1:
                return m
        return "UNK"

    mode = np.where(is_fail, df.apply(mode_of, axis=1), "NONE")
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=SP.TEST_FRACTION, stratify=is_fail, random_state=seed)
    fit, val = train_test_split(tr, test_size=0.25, stratify=is_fail[tr], random_state=seed)
    split = np.empty(len(df), dtype=object)
    split[fit], split[val], split[te] = "train", "val", "test"

    X = df[AI4I_FEATURES].values.astype(float)
    normal_fit = fit[~is_fail[fit]]
    sc = StandardScaler().fit(X[normal_fit])
    iso = IsolationForest(n_estimators=300, random_state=seed).fit(sc.transform(X[normal_fit]))
    raw = -iso.score_samples(sc.transform(X))
    score = _normalize(raw[fit], raw)

    rows = pd.DataFrame({
        "row_id": df["UDI"].values, "product_id": df["Product ID"].values,
        "type": df["Type"].values, "split": split, "is_fail": is_fail,
        "mode": mode, "anomaly_score": score,
    })
    # Timestamp GIẢ theo thứ tự dòng (AI4I không có thời gian thật) – mục 18.2
    rows["pseudo_time_min"] = rows["row_id"].astype(int)
    thr = _threshold_at_recall(score[val], is_fail[val])
    rows["detected"] = rows.anomaly_score >= thr
    meta = _detector_meta(rows, thr)
    meta.update(n_rows=len(df), n_fail=int(is_fail.sum()),
                mode_counts={m: int(df[m].sum()) for m in ["TWF", "HDF", "PWF", "OSF", "RNF"]},
                detector="MOCK IsolationForest(5 features) – thay bằng model P1")
    return DomainData(DOMAIN_AI4I, rows, thr, meta)


# --------------------------------------------------------------------------- SECOM
def load_secom(path: str | None = None, seed: int = SP.DATA_SPLIT_SEED, n_pca: int = 20) -> DomainData:
    df = pd.read_csv(path or DEFAULT_PATHS[DOMAIN_SECOM])
    df = df.assign(Time=pd.to_datetime(df["Time"])).copy()
    df = df.sort_values("Time", kind="stable").reset_index(drop=False).rename(columns={"index": "orig_index"})
    is_fail = (df["Pass/Fail"].values == 1)
    n = len(df)
    n_train_all = int(round(n * (1 - SP.TEST_FRACTION)))
    n_fit = int(round(n_train_all * 0.75))
    split = np.array(["train"] * n_fit + ["val"] * (n_train_all - n_fit) + ["test"] * (n - n_train_all), dtype=object)

    feat_cols = [c for c in df.columns if c not in ("Time", "Pass/Fail", "orig_index")]
    X = df[feat_cols].values.astype(float)
    fit = np.where(split == "train")[0]
    keep = np.isnan(X[fit]).mean(axis=0) <= 0.5
    X = X[:, keep]
    imp = SimpleImputer(strategy="median").fit(X[fit])
    Xi = imp.transform(X)
    var_ok = Xi[fit].std(axis=0) > 1e-8
    Xi = Xi[:, var_ok]
    sc = StandardScaler().fit(Xi[fit])
    Xs = np.clip(sc.transform(Xi), -10, 10)
    pca = PCA(n_components=n_pca, random_state=seed).fit(Xs[fit])
    Z = pca.transform(Xs)
    normal_fit = fit[~is_fail[fit]]
    iso = IsolationForest(n_estimators=300, random_state=seed).fit(Z[normal_fit])
    raw = -iso.score_samples(Z)
    score = _normalize(raw[fit], raw)

    rows = pd.DataFrame({
        "row_id": df["orig_index"].values, "time": df["Time"].values, "split": split,
        "is_fail": is_fail, "mode": np.where(is_fail, "SECOM_FAIL", "NONE"), "anomaly_score": score,
    })
    val = split == "val"
    thr = _threshold_at_recall(score[val], is_fail[val])
    rows["detected"] = rows.anomaly_score >= thr
    meta = _detector_meta(rows, thr)
    meta.update(n_rows=n, n_fail=int(is_fail.sum()), n_features_raw=len(feat_cols),
                n_features_kept=int(var_ok.sum()), n_pca=n_pca,
                pca_var_explained=float(pca.explained_variance_ratio_.sum()),
                time_range=[str(df.Time.min()), str(df.Time.max())],
                detector="MOCK IsolationForest(PCA-20) – thay bằng model P2")
    return DomainData(DOMAIN_SECOM, rows, thr, meta)


_CACHE: dict = {}


def load_domain(domain: str, path: str | None = None) -> DomainData:
    key = (domain, path)
    if key not in _CACHE:
        _CACHE[key] = load_ai4i(path) if domain == DOMAIN_AI4I else load_secom(path)
    return _CACHE[key]
