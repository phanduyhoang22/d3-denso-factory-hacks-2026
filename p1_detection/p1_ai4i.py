"""P1 – Phát hiện bất thường AI4I 2020 (P1.1–P1.4) và E0.

  python p1_detection/p1_ai4i.py            # ~20 giây, ghi p1_detection/outputs/

Dữ liệu: data/factory/ai4i_assigned.csv (AI4I 2020 đã gán vào máy M01–M50, timestamp giả theo máy).

Quy tắc chống sai số (mục 18.2) được tuân thủ:
  * Chia ngẫu nhiên PHÂN TẦNG theo nhãn: train 60% / val 20% / test 20%, seed 42.
  * Scaler, mô hình, chuẩn hóa điểm và ngưỡng CHỈ fit trên train (mô hình chỉ học dòng bình thường của train).
  * Ngưỡng cố định: recall 90% trên validation, rồi áp nguyên lên test.
  * Không SMOTE, không sinh dòng lỗi giả. RNF loại khỏi đánh giá theo chế độ (lỗi ngẫu nhiên, không phụ thuộc tín hiệu).

Ba bộ phát hiện (E0):
  rule         luật ngưỡng theo MÔ TẢ DATASET (TWF/HDF/PWF/OSF). Đây là đúng luật đã SINH nhãn AI4I,
               nên kết quả là CẬN TRÊN, không phải năng lực thật ngoài nhà máy.
  iforest      Isolation Forest không giám sát trên 5 cảm biến thô.
  iforest_phys Isolation Forest trên 5 cảm biến + 3 đặc trưng vật lý (chênh nhiệt, công suất, mòn dao × mô-men),
               cùng hướng với Detector của P2.
  autoencoder  MLP tự mã hóa (5→3→5) học tái tạo dòng bình thường; điểm = sai số tái tạo.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "factory" / "ai4i_assigned.csv"
OUT = Path(__file__).resolve().parent / "outputs"
SEED, TARGET_RECALL = 42, 0.90
FEATURES = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
MODES = ["TWF", "HDF", "PWF", "OSF", "RNF"]
OSF_LIMIT = {"L": 11000, "M": 12000, "H": 13000}
MODE_VI = {"TWF": "Mòn dao", "HDF": "Tản nhiệt kém", "PWF": "Lỗi công suất", "OSF": "Quá tải mô-men",
           "RNF": "Lỗi ngẫu nhiên", "UNKNOWN": "Lỗi máy không rõ chế độ"}
CAUSE_VI = {"TWF": "Dao mòn quá hạn (tool wear ~200–250 phút)",
            "HDF": "Làm mát kém: chênh nhiệt < 8,6 K và tốc độ quay < 1380 rpm",
            "PWF": "Công suất ngoài dải 3500–9000 W",
            "OSF": "Mòn dao × mô-men vượt ngưỡng theo loại máy"}


# ---------------------------------------------------------------- dữ liệu
def load():
    df = pd.read_csv(DATA)
    df["mode"] = df[MODES].apply(lambda r: "+".join(m for m in MODES if r[m]) or "", axis=1)
    df.loc[(df["Machine failure"] == 1) & (df["mode"] == ""), "mode"] = "UNKNOWN"
    df.loc[df["Machine failure"] == 0, "mode"] = ""  # 18 dòng RNF có Machine failure = 0 → bình thường
    y = df["Machine failure"].values
    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=0.2, stratify=y, random_state=SEED)
    fit, val = train_test_split(tr, test_size=0.25, stratify=y[tr], random_state=SEED)
    split = np.empty(len(df), dtype=object)
    split[fit], split[val], split[te] = "train", "val", "test"
    df["split"] = split
    return df


# ---------------------------------------------------------------- bộ phát hiện
def rule_flags(df):
    """Trả về DataFrame cờ theo từng chế độ (luật mô tả dataset)."""
    wear, torque, rpm = df["Tool wear [min]"], df["Torque [Nm]"], df["Rotational speed [rpm]"]
    dT = df["Process temperature [K]"] - df["Air temperature [K]"]
    power = torque * rpm * 2 * np.pi / 60
    return pd.DataFrame({
        "TWF": wear >= 200,
        "HDF": (dT < 8.6) & (rpm < 1380),
        "PWF": (power < 3500) | (power > 9000),
        "OSF": wear * torque > df["Type"].map(OSF_LIMIT),
    })


def rule_score(df):
    """Điểm luật 0–1: mức vượt ngưỡng lớn nhất trong 4 luật (1 = vượt rõ)."""
    wear, torque, rpm = df["Tool wear [min]"], df["Torque [Nm]"], df["Rotational speed [rpm]"]
    dT = df["Process temperature [K]"] - df["Air temperature [K]"]
    power = torque * rpm * 2 * np.pi / 60
    s = np.column_stack([
        wear / 200,
        np.minimum(8.6 / dT.clip(lower=0.1), 1380 / rpm),
        np.maximum(3500 / power.clip(lower=1), power / 9000),
        wear * torque / df["Type"].map(OSF_LIMIT),
    ])
    return np.clip(s.max(axis=1) / 2, 0, 1)  # 0.5 = đúng ngưỡng


def physical(df):
    """5 cảm biến + 3 đặc trưng vật lý suy ra từ chúng (không dùng nhãn)."""
    X = df[FEATURES].copy()
    X["dT"] = df["Process temperature [K]"] - df["Air temperature [K]"]
    X["power"] = df["Torque [Nm]"] * df["Rotational speed [rpm]"] * 2 * np.pi / 60
    X["strain"] = df["Tool wear [min]"] * df["Torque [Nm]"]
    return X.values.astype(float)


def _iforest(X, normal_fit):
    sc = StandardScaler().fit(X[normal_fit])
    Xs = sc.transform(X)
    iso = IsolationForest(n_estimators=300, random_state=SEED).fit(Xs[normal_fit])
    return -iso.score_samples(Xs), Xs


def fit_scores(df):
    """Trả về dict model → điểm thô (cao = bất thường hơn). Chỉ fit trên dòng bình thường của train."""
    normal_fit = (df.split == "train").values & (df["Machine failure"] == 0).values
    raw_if, Xs = _iforest(df[FEATURES].values.astype(float), normal_fit)
    phys_if, _ = _iforest(physical(df), normal_fit)
    ae = MLPRegressor(hidden_layer_sizes=(3,), activation="tanh", max_iter=2000, random_state=SEED)
    ae.fit(Xs[normal_fit], Xs[normal_fit])
    return {
        "rule": rule_score(df),
        "iforest": raw_if,
        "iforest_phys": phys_if,
        "autoencoder": ((ae.predict(Xs) - Xs) ** 2).mean(axis=1),
    }


def to_unit(raw, train_mask):
    """Chuẩn hóa về [0,1] theo phân vị so với điểm train (fit trên train)."""
    ref = np.sort(raw[train_mask])
    return np.searchsorted(ref, raw, side="right") / len(ref)


def threshold_at_recall(score, y, recall=TARGET_RECALL):
    pos = np.sort(score[y == 1])
    return float(pos[int(np.floor((1 - recall) * len(pos)))])


# ---------------------------------------------------------------- E0
def e0_rows(df, score, thr, model):
    rows = []
    for split in ("val", "test"):
        d = df[df.split == split]
        s, y = score[d.index], d["Machine failure"].values.astype(bool)
        pred = s >= thr
        tp, fp, fn = int((pred & y).sum()), int((pred & ~y).sum()), int((~pred & y).sum())
        p = tp / max(1, tp + fp)
        r = tp / max(1, tp + fn)
        base = dict(experiment="E0", dataset="ai4i", method=model, split=split, threshold=round(thr, 4))
        rows += [dict(base, failure_mode="ALL", metric=m, value=v, n_pos=int(y.sum())) for m, v in [
            ("precision", p), ("recall", r), ("f1", 2 * p * r / max(1e-9, p + r)),
            ("pr_auc", average_precision_score(y, s)), ("false_alarm_rate", fp / max(1, int((~y).sum())))]]
        for m in ["TWF", "HDF", "PWF", "OSF", "UNKNOWN"]:  # recall theo chế độ (RNF loại)
            mask = d["mode"].str.contains(m).values
            if mask.sum():
                rows.append(dict(base, failure_mode=m, metric="recall", value=(pred & mask).sum() / mask.sum(),
                                 n_pos=int(mask.sum())))
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    train = (df.split == "train").values
    val = (df.split == "val").values
    y = df["Machine failure"].values

    # P1.1 data facts
    facts = {
        "n_rows": len(df), "n_fail": int(y.sum()),
        "split_counts": df.groupby("split")["Machine failure"].agg(["size", "sum"]).to_dict("index"),
        "mode_counts_fail_only": {m: int(df.loc[y == 1, m].sum()) for m in MODES},
        "rnf_flag_but_no_failure": int(((df.RNF == 1) & (y == 0)).sum()),
        "fail_without_mode": int((df["mode"] == "UNKNOWN").sum()),
    }

    scores, thresholds, e0 = {}, {}, []
    for name, raw in fit_scores(df).items():
        s = to_unit(raw, train) if name != "rule" else raw
        thr = 0.5 if name == "rule" else threshold_at_recall(s[val], y[val])  # luật: ngưỡng mô tả dataset
        scores[name], thresholds[name] = s, thr
        e0 += e0_rows(df, s, thr, name)
    e0 = pd.DataFrame(e0).round(4)
    e0.to_csv(OUT / "p1_ai4i_e0.csv", index=False)

    # P1.2 rule flags → chế độ nghi ngờ (dùng làm suspected_cause_group cho bản ghi sự cố)
    flags = rule_flags(df)
    sc_tab = pd.DataFrame({"UDI": df.UDI, "machine_id": df.machine_id, "split": df.split,
                           "timestamp": df.timestamp_fake, "machine_failure": y, "failure_mode": df["mode"]})
    for k, s in scores.items():
        sc_tab[f"score_{k}"] = np.round(s, 4)
        sc_tab[f"alarm_{k}"] = s >= thresholds[k]
    sc_tab["suspected_mode"] = flags.apply(lambda r: "+".join(m for m in flags.columns if r[m]), axis=1)
    sc_tab.to_csv(OUT / "p1_ai4i_scores.csv", index=False)

    # P1.4 bản ghi sự cố chuẩn hóa (mục 5.3) = cảnh báo của Isolation Forest trên TEST (gồm cả báo sai)
    # Chọn bộ chính: bộ học máy (không phải luật sinh nhãn) có tỷ lệ báo sai thấp nhất trên VALIDATION
    val_fa = e0[(e0.split == "val") & (e0.failure_mode == "ALL") & (e0.metric == "false_alarm_rate")]         .set_index("method").value
    MAIN = val_fa.drop("rule").idxmin()
    sc_tab["score_main"], sc_tab["alarm_main"] = sc_tab[f"score_{MAIN}"], sc_tab[f"alarm_{MAIN}"]
    sc_tab.to_csv(OUT / "p1_ai4i_scores.csv", index=False)
    alarms = sc_tab[(sc_tab.split == "test") & sc_tab[f"alarm_{MAIN}"]]
    recs = []
    for r in alarms.itertuples(index=False):
        sus = r.suspected_mode.split("+")[0] if r.suspected_mode else None
        s = float(getattr(r, f"score_{MAIN}"))
        recs.append({
            "incident_id": f"INC_P1_{r.UDI:05d}", "timestamp": pd.Timestamp(r.timestamp).isoformat(),
            "timestamp_is_synthetic": True, "dataset": "ai4i", "node_id": r.machine_id,
            "source_row": int(r.UDI),
            "anomaly_type": MODE_VI.get(sus, "Bất thường cảm biến"),
            "failure_mode": r.failure_mode or None,  # nhãn thật (chỉ để chấm), None = báo sai
            "severity": "high" if s >= 0.99 else "medium" if s >= 0.97 else "low",
            "anomaly_score": round(s, 4), "detector": "iforest" if MAIN.startswith("iforest") else MAIN,
            "suspected_cause_group": CAUSE_VI.get(sus), "split": "test",
        })
    (OUT / "incidents_ai4i.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding="utf-8")

    meta = {"facts": facts, "thresholds": thresholds, "main_detector": MAIN,
            "selection": "tỷ lệ báo sai thấp nhất trên validation (không dùng test, không xét luật)",
            "val_false_alarm_rate": val_fa.round(4).to_dict(),
            "n_alarms_test": len(recs), "n_true_alarms_test": int(sum(r["failure_mode"] is not None for r in recs))}
    (OUT / "p1_ai4i_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str),
                                           encoding="utf-8")
    write_report(e0, meta)
    print((OUT / "p1_ai4i_report.md").read_text(encoding="utf-8"))


def write_report(e0, meta):
    t = e0[(e0.split == "test") & (e0.failure_mode == "ALL")].pivot(index="method", columns="metric", values="value")
    m = e0[(e0.split == "test") & (e0.failure_mode != "ALL")].pivot(index="failure_mode", columns="method",
                                                                    values="value")
    n = e0[(e0.split == "test") & (e0.failure_mode != "ALL")].groupby("failure_mode").n_pos.first()
    f = meta["facts"]
    lines = [
        "# P1 – Phát hiện bất thường AI4I 2020 (E0)", "",
        f"Dữ liệu `data/factory/ai4i_assigned.csv`: {f['n_rows']:,} dòng, {f['n_fail']} lỗi máy. "
        "Chia phân tầng 60/20/20 (seed 42): " + ", ".join(
            f"{k} {v['size']:,} dòng / {v['sum']} lỗi" for k, v in f["split_counts"].items()) + ".",
        f"RNF: {f['rnf_flag_but_no_failure']} dòng có cờ RNF nhưng `Machine failure = 0` → coi là bình thường; "
        f"{f['fail_without_mode']} dòng lỗi không có chế độ → `UNKNOWN`.", "",
        "Ngưỡng: Isolation Forest và Autoencoder cố định **recall 90% trên validation**, áp nguyên lên test. "
        "Luật dùng ngưỡng của mô tả dataset.", "",
        "## E0 trên test", "",
        "| Bộ phát hiện | Precision | Recall | F1 | PR-AUC | Tỷ lệ báo sai |", "|---|---|---|---|---|---|",
    ]
    names = {"rule": "Luật mô tả dataset (cận trên*)", "iforest": "Isolation Forest (5 cảm biến)",
             "iforest_phys": "Isolation Forest (+ đặc trưng vật lý)", "autoencoder": "Autoencoder"}
    for k in ["rule", "iforest", "iforest_phys", "autoencoder"]:
        r = t.loc[k]
        lines.append(f"| {names[k]} | {r.precision:.3f} | {r.recall:.3f} | {r.f1:.3f} | {r.pr_auc:.3f} | "
                     f"{r.false_alarm_rate:.3f} |")
    lines += ["", "## Recall theo chế độ lỗi (test)", "",
              "| Chế độ | n | Luật | IF 5 cảm biến | IF + vật lý | Autoencoder |", "|---|---|---|---|---|---|"]
    for mode in m.index:
        r = m.loc[mode]
        lines.append(f"| {mode} | {n[mode]} | {r['rule']:.2f} | {r['iforest']:.2f} | {r['iforest_phys']:.2f} | "
                     f"{r['autoencoder']:.2f} |")
    fa = ", ".join(f"{names[k]} {v:.3f}" for k, v in meta["val_false_alarm_rate"].items() if k != "rule")
    lines += ["", f"**Bộ chính: {names[meta['main_detector']]}**, chọn vì tỷ lệ báo sai thấp nhất trên **validation** "
              f"({fa}); test không dùng để chọn.",
              "", f"Bản ghi sự cố (`incidents_ai4i.json`): {meta['n_alarms_test']} cảnh báo của bộ chính "
              f"trên test, trong đó {meta['n_true_alarms_test']} là lỗi thật, còn lại là **báo sai**.", "",
              "## Cần nêu thẳng khi báo cáo", "",
              "- *Luật HDF/PWF/OSF dùng đúng công thức đã sinh nhãn AI4I nên không báo sai lần nào (cận trên, "
              "không phải năng lực kỳ vọng ở nhà máy thật). Toàn bộ báo sai của luật đến từ TWF: dao hỏng "
              "ngẫu nhiên trong khoảng ~200–250 phút, nên ngưỡng `tool wear ≥ 200` bắt cả 678/9.661 dòng "
              "bình thường (toàn bộ dữ liệu).",
              f"- Bộ chính ({names[meta['main_detector']]}) đạt recall {t.loc[meta['main_detector']].recall:.2f} "
              f"nhưng báo sai {t.loc[meta['main_detector']].false_alarm_rate:.0%} dòng bình thường: chỉ "
              f"{meta['n_true_alarms_test']}/{meta['n_alarms_test']} cảnh báo trên test là lỗi thật. Đây là nhiễu "
              "thật cho truy vết ngược; P2 báo cáo bộ tương tự còn ~21% báo sai nhờ chọn bộ đặc trưng trên "
              "validation, nên còn dư địa cải thiện.",
              "- Số mẫu lỗi trên test mỗi chế độ chỉ vài chục (TWF, UNKNOWN rất ít) → recall theo chế độ dao động "
              "mạnh; nên gộp hoặc báo kèm n.",
              "- AI4I là dữ liệu tổng hợp, mỗi dòng là một lượt vận hành rời rạc; timestamp là giả.",
              "- Mô hình không giám sát chỉ học dòng bình thường của train; ngưỡng chọn trên validation, "
              "không chỉnh theo test."]
    (OUT / "p1_ai4i_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
