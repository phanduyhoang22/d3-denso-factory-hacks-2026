"""Chỉ số đánh giá E1–E3 (mục 15.3). P4 rà soát định nghĩa trước mốc C5."""
from scipy.stats import spearmanr


def set_precision_recall(pred, truth):
    pred, truth = set(pred), set(truth)
    if not pred and not truth:
        return 1.0, 1.0
    tp = len(pred & truth)
    return (tp / len(pred) if pred else 0.0), (tp / len(truth) if truth else 0.0)


def recall_by_layer(pred, truth, node_type):
    """Recall tách theo tầng (process/part/product/order). node_type: dict node_id -> type."""
    out = {}
    for layer in ("process", "part", "product", "order"):
        t = {n for n in truth if node_type.get(n) == layer}
        if t:
            out[layer] = len(set(pred) & t) / len(t)
    return out


def spearman_vs_truth(ranked, true_impact):
    """ranked: list[{node_id, risk_score}]. Node thiếu trong dự đoán được tính điểm 0."""
    nodes = list(true_impact)
    if len(nodes) < 2:
        return float("nan")
    pred = {r["node_id"]: r["risk_score"] for r in ranked}
    x, y = [pred.get(n, 0.0) for n in nodes], [true_impact[n] for n in nodes]
    if len(set(x)) < 2 or len(set(y)) < 2:  # hằng số → Spearman không xác định
        return float("nan")
    rho, _ = spearmanr(x, y)
    return float(rho)


def topk_precision(ranked_ids, true_impact, k):
    true_top = set(sorted(true_impact, key=true_impact.get, reverse=True)[:k])
    pred_top = list(ranked_ids)[:k]
    return len(set(pred_top) & true_top) / k if k else 0.0


def topk_accuracy(ranked_ids, truth, k):
    return 1.0 if truth in list(ranked_ids)[:k] else 0.0
