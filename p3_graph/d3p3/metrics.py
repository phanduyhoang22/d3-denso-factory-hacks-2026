"""Chỉ số đánh giá E1 / E2 / E3 (dùng chung cho runner)."""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import spearmanr

from .ontology import IMPACT_LAYERS

NAN = float("nan")


def _prf(pred: set, truth: set):
    tp = len(pred & truth)
    p = tp / len(pred) if pred else NAN
    r = tp / len(truth) if truth else NAN
    f = (2 * p * r / (p + r)) if (pred and truth and (p + r) > 0) else (0.0 if truth else NAN)
    return p, r, f


def e1_metrics(trace: dict, forward_truth: dict, ks=(5, 10)) -> list[tuple[str, str, float]]:
    """Trả về [(layer, metric, value)]. layer='all' là gộp các tầng."""
    out = []
    all_pred, all_truth = set(), set()
    for t in IMPACT_LAYERS:
        pred, truth = set(trace["by_layer"][t]), set(forward_truth[t])
        all_pred |= pred
        all_truth |= truth
        if not truth and not pred:
            continue
        p, r, f = _prf(pred, truth)
        out += [(t, "precision", p), (t, "recall", r), (t, "f1", f)]
    p, r, f = _prf(all_pred, all_truth)
    out += [("all", "precision", p), ("all", "recall", r), ("all", "f1", f)]
    ranked = [a["node_id"] for a in trace["affected"]]
    for k in ks:
        top = set(ranked[:k])
        out.append(("all", f"precision@{k}", len(top & all_truth) / k))
        out.append(("all", f"recall@{k}", len(top & all_truth) / len(all_truth) if all_truth else NAN))
    if all_truth:
        R = len(all_truth)
        out.append(("all", "r_precision", len(set(ranked[:R]) & all_truth) / R))
    out.append(("all", "n_pred", float(len(all_pred))))
    out.append(("all", "n_truth", float(len(all_truth))))
    return out


def e2_metrics(scores: dict, true_impact: dict, universe: list[str], k: int = 5):
    """Spearman giữa điểm hệ thống và mức ảnh hưởng thật trên `universe`; Top-k precision."""
    if len(universe) < 3:
        return [("all", "spearman", NAN), ("all", f"top{k}_precision", NAN)]
    s = np.array([scores.get(n, 0.0) for n in universe])
    t = np.array([true_impact.get(n, 0.0) for n in universe])
    rho = spearmanr(s, t).statistic if (s.std() > 0 and t.std() > 0) else NAN
    kk = min(k, len(universe))
    top_t = set(np.array(universe)[np.argsort(-t, kind="stable")[:kk]])
    order = sorted(universe, key=lambda n: (-scores.get(n, 0.0), n))
    top_s = set(order[:kk]) if s.max() > 0 else set()
    return [("all", "spearman", float(rho) if not (isinstance(rho, float) and math.isnan(rho)) else NAN),
            ("all", f"top{k}_precision", len(top_s & top_t) / kk)]


def e3_metrics(ranking: list[str], root: str, ks=(1, 3)):
    return [("all", f"top{k}_acc", float(root in ranking[:k])) for k in ks]
