"""P3.3 – Gán dữ liệu thật vào node: Máy (nhánh A) ↔ AI4I 2020, Công đoạn (nhánh B) ↔ SECOM.

Gọi SAU generate_graph(): cấu trúc đã cố định, việc gán chỉ quyết định node nào
"sở hữu" dòng dữ liệu nào. Các dòng được chia rời nhau giữa các node.
* AI4I: gán theo machine_type (L/M/H khớp cột Type) → mỗi máy có lịch sử train + test riêng.
* SECOM: chia theo thứ tự thời gian, xen kẽ (round-robin) → mỗi công đoạn có chuỗi theo thời gian.
* hist_fail_rate chỉ tính trên phần train (quy tắc 18.2).
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from .data import DomainData
from .ontology import BRANCH_A, BRANCH_B, DOMAIN_AI4I, DOMAIN_SECOM, MACHINE, PROCESS


def _set_data(G, n, dataset, rows_df, train_ids, test_ids):
    tr = rows_df.loc[train_ids]
    G.nodes[n]["data"] = {
        "dataset": dataset,
        "train_rows": [int(i) for i in train_ids],
        "test_rows": [int(i) for i in test_ids],
    }
    k, n_tr = int(tr.is_fail.sum()), len(tr)
    G.nodes[n]["hist_fail_count"] = k
    G.nodes[n]["hist_n"] = n_tr
    # làm trơn Laplace để node ít dữ liệu không ra 0 tuyệt đối
    G.nodes[n]["hist_fail_rate"] = round((k + 1) / (n_tr + 2), 5)


def assign_data(G: nx.DiGraph, ai4i: DomainData | None, secom: DomainData | None, seed: int) -> nx.DiGraph:
    """Gán bản ghi vào node, trả về chính G (đã thêm thuộc tính `data`, `hist_fail_rate`)."""
    rng = np.random.default_rng(np.random.SeedSequence([seed, 202]))

    if ai4i is not None:
        rows = ai4i.rows.set_index(np.arange(len(ai4i.rows)))  # chỉ số vị trí
        machines = [n for n, d in G.nodes(data=True) if d["type"] == MACHINE and d["branch"] == BRANCH_A]
        for t in ("L", "M", "H"):
            ms = [m for m in machines if G.nodes[m]["machine_type"] == t]
            if not ms:
                continue
            parts = {}
            for split in ("train", "test"):
                ids = rows.index[(rows.type == t) & (rows.split == split)].to_numpy().copy()
                rng.shuffle(ids)
                parts[split] = np.array_split(ids, len(ms))
            for i, m in enumerate(ms):
                _set_data(G, m, DOMAIN_AI4I, rows, parts["train"][i], parts["test"][i])
                G.nodes[m]["data_source"] = DOMAIN_AI4I

    if secom is not None:
        rows = secom.rows.set_index(np.arange(len(secom.rows)))  # đã sắp theo thời gian
        procs = [n for n, d in G.nodes(data=True) if d["type"] == PROCESS and d["branch"] == BRANCH_B]
        if procs:
            offset = int(rng.integers(len(procs)))
            for split in ("train", "test"):
                ids = rows.index[rows.split == split].to_numpy()
                buckets = {p: ids[(np.arange(len(ids)) + offset) % len(procs) == i] for i, p in enumerate(procs)}
                for p in procs:
                    G.nodes[p].setdefault("_tmp", {})[split] = buckets[p]
            for p in procs:
                tmp = G.nodes[p].pop("_tmp")
                _set_data(G, p, DOMAIN_SECOM, rows, tmp["train"], tmp["test"])
                G.nodes[p]["data_source"] = DOMAIN_SECOM
    return G


def source_nodes(G: nx.DiGraph, domain: str) -> list[str]:
    """Các node mang dữ liệu thật của domain (ứng viên làm nguồn sự cố)."""
    return [n for n, d in G.nodes(data=True) if d.get("data_source") == domain]
