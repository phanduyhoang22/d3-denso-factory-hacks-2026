#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D3 - P2: PHẦN SECOM (việc P2.1-P2.7, P2.9 trong tài liệu D3)
============================================================
    python p2_secom.py --data secom/secom.data --labels secom/secom_labels.data --out p2_outputs/secom --seeds 30

  P2.1  data_facts_secom.md        số liệu đếm trực tiếp từ file
  P2.2  tiền xử lý lưu được        bỏ cột thiếu >40% / hằng số, điền trung vị, chuẩn hóa, PCA (chỉ fit trên train), chia theo thời gian
  P2.3  E0 cho SECOM               Isolation Forest (cùng loại model với AI4I) + hồi quy logistic có class weight + luật 3-sigma,
                                   ngưỡng cố định recall 90% trên validation; KHÔNG dùng SMOTE
  P2.4  incidents_secom.json       bản ghi sự cố chuẩn hóa, kiểm tra theo INCIDENT_RECORD_SCHEMA
  P2.5  true_impact()              đã có trong p2_experiments.py (kiểm tra tay trong test_p2_secom.py)
  P2.6  baseline_e3() + 1 kịch bản SECOM chạy qua backward_trace()
  P2.7  E0-E3 (+E4) 30 seed trên SECOM

Việc P2.8 (phỏng vấn kỹ sư E6, chấm E5) là việc của con người: xem p2_phieu_phong_van_E6_E5.md.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

import p2_experiments as E
import p2_impact_trace as P
import p2_schema as S


# =============================================================================
# P2.1 – ĐỌC DỮ LIỆU VÀ SỐ LIỆU ĐẾM TRỰC TIẾP
# =============================================================================
def load_secom(data_path: str, labels_path: str) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    X = pd.read_csv(data_path, sep=r"\s+", header=None, na_values=["NaN"])
    lab = pd.read_csv(labels_path, sep=" ", header=None, names=["label", "time"], quotechar='"')
    if len(X) != len(lab):
        raise ValueError(f"secom.data có {len(X)} dòng nhưng secom_labels.data có {len(lab)} dòng")
    y = (lab["label"] == 1).astype(int)                       # -1 = pass, 1 = fail
    t = pd.to_datetime(lab["time"], format="%d/%m/%Y %H:%M:%S")
    if not t.is_monotonic_increasing:
        order = np.argsort(t.to_numpy(), kind="stable")
        X, y, t = X.iloc[order].reset_index(drop=True), y.iloc[order].reset_index(drop=True), t.iloc[order].reset_index(drop=True)
    X.columns = list(range(X.shape[1]))
    return X, y, t


def data_facts(X: pd.DataFrame, y: pd.Series, t: pd.Series, split=(0.6, 0.2, 0.2)) -> dict:
    n = len(y)
    cuts = [0, int(split[0] * n), int((split[0] + split[1]) * n), n]
    parts = {}
    for name, a, b in zip(("train", "val", "test"), cuts[:-1], cuts[1:]):
        parts[name] = dict(rows=b - a, fails=int(y.iloc[a:b].sum()), start=str(t.iloc[a]), end=str(t.iloc[b - 1]))
    return dict(rows=n, features=X.shape[1], fails=int(y.sum()), passes=int((1 - y).sum()), fail_rate=float(y.mean()),
                t_min=str(t.min()), t_max=str(t.max()), duplicated_timestamps=int(t.duplicated().sum()),
                nan_fraction=float(X.isna().to_numpy().mean()), cols_nan_over_40pct=int((X.isna().mean() > 0.4).sum()),
                constant_cols=int((X.nunique() <= 1).sum()), rows_with_any_nan=float(X.isna().any(axis=1).mean()),
                splits=parts)


def facts_markdown(f: dict, prep: "Prep | None" = None, src: str = "") -> str:
    L = ["# data_facts – SECOM (đếm trực tiếp từ file)", "",
         f"Nguồn file: {src or 'secom.data, secom_labels.data (UCI ID 179)'}. Mọi số dưới đây được đếm lại bởi `p2_secom.py`, không lấy từ mô tả.", "",
         "| Mục | Giá trị |", "|---|---|",
         f"| Số dòng | {f['rows']} |", f"| Số cảm biến | {f['features']} |",
         f"| Dòng fail (nhãn 1) | {f['fails']} ({f['fail_rate']:.2%}) |", f"| Dòng pass (nhãn −1) | {f['passes']} |",
         f"| Khoảng thời gian (timestamp THẬT) | {f['t_min']} đến {f['t_max']} |",
         f"| Timestamp trùng nhau | {f['duplicated_timestamps']} |",
         f"| Tỷ lệ ô thiếu | {f['nan_fraction']:.2%} |", f"| Cột thiếu > 40% | {f['cols_nan_over_40pct']} |",
         f"| Cột hằng số | {f['constant_cols']} |", f"| Dòng có ít nhất 1 ô thiếu | {f['rows_with_any_nan']:.0%} |", "",
         "Chia train/validation/test theo thời gian (không xáo trộn):", "",
         "| Tập | Dòng | Fail | Từ | Đến |", "|---|---|---|---|---|"]
    for k, v in f["splits"].items():
        L.append(f"| {k} | {v['rows']} | {v['fails']} | {v['start']} | {v['end']} |")
    if prep is not None:
        L += ["", "Tiền xử lý (chỉ fit trên train):", "",
              f"- Bỏ cột thiếu > 40% (tính trên train): còn {prep.n_after_nan} cột.",
              f"- Bỏ cột hằng số trên train: còn {prep.n_after_var} cột.",
              f"- PCA giữ 90% phương sai: **{prep.n_pca} thành phần** (từ {f['features']} chiều).", ""]
    L += ["Lưu ý: số fail ở validation và test rất ít, nên chỉ số E0 trên SECOM dao động mạnh; báo cáo kèm khoảng tin cậy bootstrap.", ""]
    return "\n".join(L)


# =============================================================================
# P2.2 – TIỀN XỬ LÝ (chỉ fit trên train)
# =============================================================================
class Prep:
    def __init__(self, nan_max: float = 0.40, var_explained: float = 0.90, seed: int = 0):
        self.nan_max, self.var_explained, self.seed = nan_max, var_explained, seed

    def fit(self, Xtr: pd.DataFrame) -> "Prep":
        from sklearn.decomposition import PCA
        from sklearn.feature_selection import VarianceThreshold
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
        self.keep_cols = [c for c in Xtr.columns if Xtr[c].isna().mean() <= self.nan_max]
        self.n_after_nan = len(self.keep_cols)
        self.imp = SimpleImputer(strategy="median").fit(Xtr[self.keep_cols])
        Xi = self.imp.transform(Xtr[self.keep_cols])
        self.vt = VarianceThreshold(1e-12).fit(Xi)
        Xv = self.vt.transform(Xi)
        self.n_after_var = Xv.shape[1]
        self.sc = StandardScaler().fit(Xv)
        self.pca = PCA(n_components=self.var_explained, svd_solver="full", random_state=self.seed).fit(self.sc.transform(Xv))
        self.n_pca = self.pca.n_components_
        return self

    def scaled(self, X: pd.DataFrame) -> np.ndarray:
        return self.sc.transform(self.vt.transform(self.imp.transform(X[self.keep_cols])))

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        return self.pca.transform(self.scaled(X))


# =============================================================================
# P2.3 – BỘ PHÁT HIỆN SECOM (cùng giao diện với E.Detector)
# =============================================================================
def _thr_recall(score_pos: np.ndarray, recall: float) -> float:
    return float(np.quantile(score_pos, 1.0 - recall))


class SECOMDetector:
    domain = "secom"
    name = "SECOM"

    def __init__(self, X: pd.DataFrame, y: pd.Series, t: pd.Series, exp: dict = E.EXP, split=(0.6, 0.2, 0.2)):
        from sklearn.ensemble import IsolationForest
        from sklearn.linear_model import LogisticRegression
        self.exp = exp
        n = len(y)
        c1, c2 = int(split[0] * n), int((split[0] + split[1]) * n)
        self.offset_test = c2                                    # chỉ số dòng gốc của dòng test đầu tiên
        sl = {"train": slice(0, c1), "val": slice(c1, c2), "test": slice(c2, n)}
        self.X = {k: X.iloc[v].reset_index(drop=True) for k, v in sl.items()}
        self.y = {k: y.iloc[v].reset_index(drop=True) for k, v in sl.items()}
        self.t = {k: t.iloc[v].reset_index(drop=True) for k, v in sl.items()}
        self.train = self.X["train"]
        self.facts = data_facts(X, y, t, split)
        self.cols = list(X.columns)
        self.prep = Prep(seed=exp["data_seed"]).fit(self.train)
        Z = {k: self.prep.transform(v) for k, v in self.X.items()}
        Zs = {k: self.prep.scaled(v) for k, v in self.X.items()}
        rs = exp["data_seed"]
        self.if_model = IsolationForest(n_estimators=200, random_state=rs).fit(Z["train"])
        self.lr = LogisticRegression(class_weight="balanced", C=0.1, max_iter=2000, random_state=rs).fit(Z["train"], self.y["train"])
        self._ecdf = np.sort(-self.if_model.score_samples(Z["train"]))
        self._z_cache = Z
        # điểm của từng mô hình trên val/test
        self.models = {
            "Luật 3-sigma (số cảm biến vượt ±3σ)": lambda X_: (np.abs(self.prep.scaled(X_)) > 3).sum(axis=1).astype(float),
            "Isolation Forest (PCA)": lambda X_: -self.if_model.score_samples(self.prep.transform(X_)),
            "Hồi quy logistic có class weight (PCA)": lambda X_: self.lr.decision_function(self.prep.transform(X_)),
        }
        self.thr = {}
        vpos = self.y["val"].to_numpy() == 1
        for name, f in self.models.items():
            sv = f(self.X["val"])
            self.thr[name] = _thr_recall(sv[vpos], exp["target_recall"])
        # mô hình dùng để sinh sự cố trong kịch bản = Isolation Forest (cùng loại với AI4I)
        a_vpos = -self.if_model.score_samples(Z["val"][vpos])
        self.thr_raw = _thr_recall(a_vpos, exp["target_recall"])
        self.thr_pct = float(np.searchsorted(self._ecdf, self.thr_raw) / len(self._ecdf))
        te_pct = self.pct(self.X["test"])
        yt = self.y["test"].to_numpy() == 1
        self.test_recall = float((te_pct[yt] >= self.thr_pct).mean()) if yt.any() else float("nan")
        self.test_false_alarm = float((te_pct[~yt] >= self.thr_pct).mean())
        pool = self.X["test"].copy()
        pool["_time"], pool["_label"] = self.t["test"].to_numpy(), self.y["test"].to_numpy()
        self.fail_pool = pool[pool["_label"] == 1].reset_index(drop=True)
        self.norm_pool = pool[pool["_label"] == 0].reset_index(drop=True)
        self.test_pct = te_pct

    def pct(self, rows: pd.DataFrame) -> np.ndarray:
        a = -self.if_model.score_samples(self.prep.transform(rows[self.cols]))
        return np.searchsorted(self._ecdf, a) / len(self._ecdf)

    def describe(self) -> str:
        f = self.facts["splits"]
        return (f"SECOM chia THEO THỜI GIAN 60/20/20 (train {f['train']['rows']} dòng/{f['train']['fails']} fail; validation {f['val']['rows']}/{f['val']['fails']}; "
                f"test {f['test']['rows']}/{f['test']['fails']}). Tiền xử lý fit trên train: {self.prep.n_after_nan} cột sau lọc thiếu, {self.prep.n_after_var} sau lọc hằng số, "
                f"PCA {self.prep.n_pca} thành phần. Mô hình sinh sự cố: Isolation Forest trên PCA, ngưỡng cố định recall {int(E.EXP['target_recall']*100)}% trên validation "
                f"(chỉ {f['val']['fails']} fail nên ngưỡng không ổn định). Trên test: recall thực {self.test_recall:.3f}, tỷ lệ báo sai {self.test_false_alarm:.3f}. "
                "Timestamp trong kịch bản đồ thị là timestamp giả theo kịch bản (các dòng SECOM được gắn vào máy khác nhau nên không chung một dòng thời gian). "
                f"SECOM không có kiểu lỗi và thời gian dừng: dùng hằng số giả định {E.EXP['secom_downtime_min']:.0f} phút, mức nghiêm trọng = điểm bất thường.")


def e0_table(det: SECOMDetector, n_boot: int = 1000, seed: int = 0) -> pd.DataFrame:
    """E0 trên test: ngưỡng cố định (recall 90% trên validation). Kèm khoảng tin cậy bootstrap vì số fail rất ít."""
    from sklearn.metrics import average_precision_score, roc_auc_score
    rng = np.random.default_rng(seed)
    yt = det.y["test"].to_numpy()
    rows = []
    for name, f in det.models.items():
        s = f(det.X["test"])
        pred = s >= det.thr[name]
        def metrics(idx):
            yy, ss, pp = yt[idx], s[idx], pred[idx]
            tp, fp, fn = int((pp & (yy == 1)).sum()), int((pp & (yy == 0)).sum()), int((~pp & (yy == 1)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else float("nan")
            f1 = 2 * prec * rec / (prec + rec) if prec + rec > 0 else 0.0
            far = fp / max(1, int((yy == 0).sum()))
            ap = average_precision_score(yy, ss) if yy.sum() else float("nan")
            auc = roc_auc_score(yy, ss) if 0 < yy.sum() < len(yy) else float("nan")
            return prec, rec, f1, ap, far, auc
        point = metrics(np.arange(len(yt)))
        boots = np.array([metrics(rng.integers(len(yt), size=len(yt))) for _ in range(n_boot)], dtype=float)
        lo, hi = np.nanpercentile(boots, 2.5, axis=0), np.nanpercentile(boots, 97.5, axis=0)
        r = dict(model=name, threshold=det.thr[name], n_test=len(yt), n_test_fail=int(yt.sum()), prevalence=float(yt.mean()))
        for k, nm in enumerate(["precision", "recall", "f1", "pr_auc", "false_alarm_rate", "roc_auc"]):
            r[nm], r[nm + "_lo"], r[nm + "_hi"] = point[k], lo[k], hi[k]
        rows.append(r)
    return pd.DataFrame(rows)


def e0_markdown(tab: pd.DataFrame) -> str:
    L = ["## E0 – Phát hiện bất thường trên SECOM (tập test theo thời gian)", "",
         f"Ngưỡng cố định theo recall {int(E.EXP['target_recall']*100)}% trên validation. Test có {int(tab['n_test_fail'].iloc[0])} fail trong {int(tab['n_test'].iloc[0])} dòng "
         f"(tỷ lệ fail {tab['prevalence'].iloc[0]:.1%}, đây cũng là PR-AUC của bộ phân loại ngẫu nhiên). Trong ngoặc là khoảng tin cậy bootstrap 95%.", "",
         "| Mô hình | Precision | Recall | F1 | PR-AUC | Tỷ lệ báo sai | ROC-AUC |", "|---|---|---|---|---|---|---|"]
    for r in tab.itertuples():
        c = lambda a: f"{getattr(r, a):.3f} ({getattr(r, a + '_lo'):.2f}–{getattr(r, a + '_hi'):.2f})"
        L.append(f"| {r.model} | {c('precision')} | {c('recall')} | {c('f1')} | {c('pr_auc')} | {c('false_alarm_rate')} | {c('roc_auc')} |")
    L += ["", "**Cách đọc:** SECOM có tín hiệu phát hiện rất yếu và test chỉ có vài chục fail. Khi PR-AUC xấp xỉ tỷ lệ fail và ROC-AUC gần 0,5 thì mô hình "
          "chưa tốt hơn đoán ngẫu nhiên một cách đáng tin; nên báo cáo đúng như vậy thay vì chọn mô hình có điểm cao nhất trên một tập test nhỏ. "
          "Class weight được dùng ở hồi quy logistic (không dùng SMOTE). Isolation Forest không có tham số class weight vì không dùng nhãn khi huấn luyện.", ""]
    return "\n".join(L)


def reading_note(det: SECOMDetector, res: pd.DataFrame) -> str:
    """Giải thích kết quả E1-E3 trên SECOM: tín hiệu phát hiện yếu thì E3 chủ yếu do đồ thị quyết định."""
    pf, pn = det.pct(det.fail_pool), det.pct(det.norm_pool)
    full = res[(res["delete_pct"] == 0) & (res["confounder_pct"] == 50)]
    return "\n".join([
        "## Cách đọc kết quả SECOM (quan trọng)", "",
        f"- Điểm bất thường trung bình (phân vị train) của dòng FAIL trong tập sinh sự cố là {pf.mean():.2f}, của dòng PASS là {pn.mean():.2f}. "
        "Dòng fail không bất thường hơn dòng pass (dữ liệu tháng 10 lệch so với tập train tháng 7–9), nên điểm bất thường gần như không mang thông tin về máy gốc.",
        f"- Vì vậy baseline E3 (điểm bất thường cao nhất) chỉ đạt Top-1 {full['e3_naive_anomaly_top1'].mean():.3f}, xấp xỉ đoán ngẫu nhiên trong {full['n_machines'].mean():.0f} máy. "
        "Phần hệ thống hơn baseline ở E3 chủ yếu đến từ cấu trúc đồ thị (khả năng nối tới kết quả xấu), không phải từ chất lượng phát hiện.",
        "- E1 và E2 không phụ thuộc chất lượng bộ phát hiện (chỉ phụ thuộc đồ thị và ước lượng tác động) nên tương tự AI4I.",
        "- SECOM được dùng đúng vai trò trong tài liệu: kiểm tra pipeline tổng quát hóa sang domain khác (590 chiều, mất cân bằng 6,6%), "
        "không phải để chứng minh phát hiện tốt. Phát hiện lỗi SECOM theo thời gian là bài toán khó; báo cáo trung thực là phát hiện chưa vượt ngẫu nhiên.", ""])


# =============================================================================
# P2.4 – BẢN GHI SỰ CỐ CHUẨN HÓA
# =============================================================================
def build_incidents(det: SECOMDetector, exp: dict = E.EXP) -> list[dict]:
    """Mỗi dòng test bị bộ phát hiện cảnh báo -> một bản ghi sự cố theo INCIDENT_RECORD_SCHEMA.
    machine_id là mã nguồn tạm 'SECOM_LINE'; nút trong đồ thị do assign_data() quyết định theo seed.
    Nhãn thật nằm trong eval_only (không dùng bởi hệ thống)."""
    te, pct = det.X["test"], det.test_pct
    z = np.abs(det.prep.scaled(te))
    out = []
    for i in np.flatnonzero(pct >= det.thr_pct):
        p = float(pct[i])
        kept = np.array(det.prep.keep_cols)[det.prep.vt.get_support()]          # cột còn lại sau lọc, theo thứ tự ma trận z
        top = kept[np.argsort(-z[i])[:3]]
        out.append(dict(
            incident_id=f"INC_SECOM_{det.offset_test + int(i) + 1:04d}",
            time=det.t["test"].iloc[i].strftime("%d/%m/%Y %H:%M"),
            machine_id="SECOM_LINE", node_id="SECOM_LINE", dataset="SECOM", timestamp_is_synthetic=False,
            anomaly_type="Bất thường đa biến (Isolation Forest trên PCA)",
            level="Cao" if p >= 0.95 else "Trung bình" if p >= 0.85 else "Thấp",
            anomaly_score=round(p, 4), severity=round(float(np.clip(p, 0.3, 1.0)), 3),
            downtime_min=float(exp["secom_downtime_min"]),
            top_features=[int(c) for c in top],
            eval_only=dict(label_fail=bool(det.y["test"].iloc[i] == 1))))
    return out


def validate_incidents(incs: list[dict]) -> int:
    n = 0
    for r in incs:
        S.validate(r, S.INCIDENT_RECORD_SCHEMA)
        n += 1
    return n


# =============================================================================
# P2.6 – MỘT KỊCH BẢN SECOM CHẠY QUA backward_trace()
# =============================================================================
def example_scenario(det: SECOMDetector, seed: int = 0, size: str = "medium", conf_pct: int = 50,
                     delete_pct: int = 25, exp: dict = E.EXP) -> dict:
    G = E.generate_graph(seed, size, exp)
    cfg = G.graph["cfg"]
    rng = np.random.default_rng([seed, list(exp["sizes"]).index(size), 7])
    prim = list(G.graph["machines"])
    all_m = prim + list(G.graph["substitutes"])
    for _ in range(50):
        root = prim[int(rng.integers(len(prim)))]
        udi = int(rng.integers(1, int(exp["n_units"] * 0.8)))
        frow = det.fail_pool.iloc[int(rng.integers(len(det.fail_pool)))]
        d_true = exp["secom_downtime_min"] * math.exp(rng.normal(0, exp["downtime_noise_sd"]))
        truth = E.true_impact(G, root, udi, d_true, float(rng.uniform(*exp["tau_true_h"])))
        orders = [n for n in truth if G.nodes[n]["type"] == "order"]
        if orders and max(truth[n] for n in orders) >= exp["impact_thr"]:
            break
    outcome = max(orders, key=lambda n: (truth[n], n))
    anc = E.ancestor_machines(G, outcome)
    non_anc = sorted(set(all_m) - anc)
    perm = [non_anc[i] for i in rng.permutation(len(non_anc))]
    conf = set(perm[:int(math.ceil(len(non_anc) * conf_pct / 100.0))])
    rows = {m: (det.fail_pool.iloc[int(rng.integers(len(det.fail_pool)))] if m in conf
                else det.norm_pool.iloc[int(rng.integers(len(det.norm_pool)))]) for m in all_m}
    rows[root] = frow
    pct = dict(zip(all_m, det.pct(pd.DataFrame([rows[m] for m in all_m]))))
    Go = E.observed_graph(G, delete_pct, seed, size, exp)
    top = E.backward_trace(Go, outcome, pct, topk=5)
    return dict(
        note="Kịch bản mẫu SECOM. Đồ thị và tham số vận hành là mô phỏng; mỗi dòng SECOM test được gắn vào một máy.",
        seed=seed, size=size, confounder_pct=conf_pct, delete_pct=delete_pct, outcome=outcome,
        backward_truth=root, true_impact_outcome=round(truth[outcome], 3),
        flagged_machines=sorted(m for m in all_m if pct[m] >= det.thr_pct), confounders=sorted(conf),
        backward_trace_top5=top,
        baseline_anomaly_top1=max(pct, key=lambda m: (pct[m], m)),
        root_rank_in_system=next((r["rank"] for r in E.backward_trace(Go, outcome, pct, topk=len(pct)) if r["machine"] == root), None))


# =============================================================================
# P2.9 – BIỂU ĐỒ
# =============================================================================
def pr_chart(det: SECOMDetector, path: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from sklearn.metrics import precision_recall_curve, average_precision_score
    except ImportError:
        return False
    yt = det.y["test"].to_numpy()
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    for name, f in det.models.items():
        s = f(det.X["test"])
        p, r, _ = precision_recall_curve(yt, s)
        ax[0].plot(r, p, label=f"{name} (AP={average_precision_score(yt, s):.2f})")
    ax[0].axhline(yt.mean(), color="gray", ls="--", label=f"ngẫu nhiên ({yt.mean():.2f})")
    ax[0].set_xlabel("Recall"); ax[0].set_ylabel("Precision"); ax[0].set_title("E0 – SECOM, đường PR trên test"); ax[0].legend(fontsize=7); ax[0].grid(alpha=.3)
    s = det.test_pct
    ax[1].hist([s[yt == 0], s[yt == 1]], bins=20, label=["pass", "fail"], color=["#8ab", "#e55"], density=True)
    ax[1].axvline(det.thr_pct, color="k", ls="--", label="ngưỡng recall 90% (validation)")
    ax[1].set_xlabel("Điểm bất thường (phân vị train)"); ax[1].set_title("Phân bố điểm Isolation Forest trên test"); ax[1].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    return True


# =============================================================================
# CHẠY TOÀN BỘ
# =============================================================================
def main():
    ap = argparse.ArgumentParser(description="D3-P2: phần SECOM")
    ap.add_argument("--data", default="secom/secom.data")
    ap.add_argument("--labels", default="secom/secom_labels.data")
    ap.add_argument("--out", default="p2_outputs/secom")
    ap.add_argument("--seeds", type=int, default=30)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    X, y, t = load_secom(a.data, a.labels)
    det = SECOMDetector(X, y, t)
    t0 = time.time()
    (out / "data_facts_secom.md").write_text(facts_markdown(det.facts, det.prep), encoding="utf-8")
    import joblib
    joblib.dump(det.prep, out / "secom_preprocess.joblib")
    tab = e0_table(det)
    tab.to_csv(out / "p2_secom_e0.csv", index=False)
    pr_chart(det, out / "p2_secom_E0.png")
    incs = build_incidents(det)
    n = validate_incidents(incs)
    (out / "incidents_secom.json").write_text(json.dumps(incs, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "p2_secom_scenario_example.json").write_text(
        json.dumps(P.clean(example_scenario(det)), ensure_ascii=False, indent=2), encoding="utf-8")
    res, _ = E.run_all(None, a.seeds, det=det)
    res.to_csv(out / "p2_results_secom.csv", index=False)
    E.summarize(res).to_csv(out / "p2_summary_secom.csv", index=False)
    (out / "p2_secom_report.md").write_text(E.build_report(res, det, a.seeds) + "\n" + e0_markdown(tab) + "\n" + reading_note(det, res), encoding="utf-8")
    E.make_chart(res, out / "p2_secom_E4.png")
    print(f"SECOM xong trong {time.time() - t0:.1f}s -> {out.resolve()}")
    print(f"  {len(incs)} sự cố hợp lệ schema ({n}); PCA {det.prep.n_pca} thành phần; recall test {det.test_recall:.3f}, báo sai {det.test_false_alarm:.3f}")


if __name__ == "__main__":
    main()
