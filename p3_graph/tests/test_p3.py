import networkx as nx
import numpy as np
import pytest

from d3p3 import sim_params as SP
from d3p3.data import load_domain
from d3p3.forward import baseline_e1, forward_trace
from d3p3.graph import demo_graph, generate_graph
from d3p3.ontology import (BRANCH_A, BRANCH_B, EDGE_TYPES, IMPACT_LAYERS, MACHINE, OPERATES_IN,
                           PROCESS, PROPAGATION_EDGES)
from d3p3.propagation import propagation_view
from d3p3.scenario import generate_scenario
from d3p3.truth import true_impact


@pytest.fixture(scope="module")
def data():
    return {d: load_domain(d) for d in ("ai4i", "secom")}


# ---------------------------------------------------------------- dữ liệu
def test_data_counts_match_source(data):
    a, s = data["ai4i"], data["secom"]
    assert a.meta["n_rows"] == 10000 and a.meta["n_fail"] == 339
    assert a.meta["mode_counts"] == {"TWF": 46, "HDF": 115, "PWF": 95, "OSF": 98, "RNF": 19}
    assert s.meta["n_rows"] == 1567 and s.meta["n_fail"] == 104


def test_secom_split_is_chronological(data):
    r = data["secom"].rows
    assert r.time.is_monotonic_increasing
    last_train = r[r.split != "test"].time.max()
    assert r[r.split == "test"].time.min() >= last_train


# ---------------------------------------------------------------- đồ thị
@pytest.mark.parametrize("size", ["small", "medium", "large"])
def test_graph_valid(size):
    G = generate_graph(3, size)
    assert nx.is_directed_acyclic_graph(G)
    for u, v, d in G.edges(data=True):
        src, dsts = EDGE_TYPES[d["type"]]
        assert G.nodes[u]["type"] == src and G.nodes[v]["type"] in dsts
        assert 0 < d["weight"] <= 1
    for p in (n for n, d in G.nodes(data=True) if d["type"] == PROCESS):
        shares = [G.edges[m, p]["weight"] for m in G.predecessors(p) if G.edges[m, p]["type"] == OPERATES_IN]
        assert abs(sum(shares) - 1) < 0.01


def test_graph_deterministic_and_size_ordering():
    g1, g2 = generate_graph(5, "medium"), generate_graph(5, "medium")
    assert nx.utils.graphs_equal(g1, g2)
    n = [generate_graph(5, s).number_of_nodes() for s in ("small", "medium", "large")]
    assert n[0] < n[1] < n[2]


def test_structure_independent_of_failure_config(data):
    """Quy tắc 18.2: cấu trúc không phụ thuộc domain/nhiễu/xóa cạnh."""
    cfgs = [dict(domain="ai4i"), dict(domain="secom", confounder_ratio=0.5),
            dict(domain="ai4i", edge_drop=0.5, failure_mode="HDF")]
    edges = [sorted(generate_scenario(11, c, data)["graph_full"].edges()) for c in cfgs]
    assert edges[0] == edges[1] == edges[2]


def test_assign_disjoint_and_train_only(data):
    sc = generate_scenario(2, {"domain": "ai4i"}, data)
    G = sc["graph_full"]
    seen = set()
    for n, d in G.nodes(data=True):
        if "data" not in d:
            continue
        ds = d["data"]["dataset"]
        tr, te = set(d["data"]["train_rows"]), set(d["data"]["test_rows"])
        keys = {(ds, i) for i in tr | te}
        assert not (tr & te) and not (seen & keys)
        seen |= keys
        rows = data[d["data"]["dataset"]].rows
        assert set(rows.split.iloc[list(tr)]) <= {"train"}
        assert set(rows.split.iloc[list(te)]) <= {"test"}
    assert any(d.get("data_source") == "ai4i" and d["branch"] == BRANCH_A for _, d in G.nodes(data=True))
    assert any(d.get("data_source") == "secom" and d["branch"] == BRANCH_B for _, d in G.nodes(data=True))


# ---------------------------------------------------------------- kịch bản
@pytest.mark.parametrize("domain", ["ai4i", "secom"])
def test_scenario_ground_truth(domain, data):
    for seed in range(5):
        sc = generate_scenario(seed, {"domain": domain, "confounder_ratio": 0.5, "edge_drop": 0.25}, data)
        G = sc["graph_full"]
        root = sc["backward_truth"]["root_node"]
        assert G.nodes[root]["type"] == (MACHINE if domain == "ai4i" else PROCESS)
        # bad outcome thuộc forward truth
        bad = sc["bad_outcome"]["node_id"]
        assert bad in sum(sc["forward_truth"].values(), [])
        # confounder không phải tổ tiên của kết quả xấu và không trùng gốc
        anc = nx.ancestors(propagation_view(G), bad)
        assert root in anc
        for c in sc["confounder_nodes"]:
            assert c not in anc and c != root
        # incident: id duy nhất, sắp theo thời gian, trước kết quả xấu, root có mặt
        ts = [i["timestamp"] for i in sc["incidents"]]
        assert ts == sorted(ts) and all(t < sc["bad_outcome"]["timestamp"] for t in ts)
        assert len({i["incident_id"] for i in sc["incidents"]}) == len(sc["incidents"])
        root_inc = [i for i in sc["incidents"] if i["incident_id"] == sc["backward_truth"]["root_incident_id"]][0]
        assert root_inc["node_id"] == root and root_inc["failure_mode"] != "NORMAL"
        # đồ thị quan sát: không lộ WIP buffer
        assert all("wip_buffer_true" not in d for _, d in sc["graph_observed"].nodes(data=True))


def test_edge_drop_nested_and_exact(data):
    dropped = {}
    for p in SP.EDGE_DROP_RATES:
        sc = generate_scenario(4, {"domain": "ai4i", "edge_drop": p}, data)
        dropped[p] = {tuple(e) for e in sc["meta"]["dropped_edges"]}
        assert len(dropped[p]) == round(p * sc["meta"]["n_prop_edges"])
        Go = sc["graph_observed"]
        assert all(not Go.has_edge(*e) for e in dropped[p])
    assert dropped[0.0] <= dropped[0.1] <= dropped[0.25] <= dropped[0.5]


def test_same_seed_same_root_across_configs(data):
    roots = {generate_scenario(9, {"domain": "ai4i", "confounder_ratio": c, "edge_drop": d}, data)
             ["backward_truth"]["root_node"] for c in (0, 0.5) for d in (0, 0.5)}
    assert len(roots) == 1


def test_failure_mode_filter(data):
    sc = generate_scenario(1, {"domain": "ai4i", "failure_mode": "TWF"}, data)
    assert sc["backward_truth"]["failure_mode"] == "TWF"


# ---------------------------------------------------------------- truy vết xuôi
def test_demo_example_section10():
    tr = forward_trace(demo_graph(), "M05")
    assert tr["by_layer"] == {"process": ["P02"], "component": ["A13"], "product": ["X1"], "order": ["O43", "O58"]}
    assert "M05 → P02 → A13 → X1 → O43" in tr["order_paths"]
    assert "M05 → P02 → A13 → X1 → O58" in tr["order_paths"]


def test_forward_equals_truth_on_full_graph(data):
    sc = generate_scenario(6, {"domain": "secom"}, data)
    G, root = sc["graph_full"], sc["backward_truth"]["root_node"]
    s = sc["backward_truth"]["severity_score"]
    tr = forward_trace(G, root, s)
    est = {a["node_id"]: a["est_impact"] for a in tr["affected"]}
    ti = true_impact(G, root, s)
    for n in est:
        assert abs(est[n] - ti[n]) < 1e-3


def test_baseline_e1_is_local():
    b = baseline_e1(demo_graph(), "M05")
    assert b["by_layer"]["process"] == ["P02"]
    assert all(not b["by_layer"][t] for t in IMPACT_LAYERS if t != "process")


def test_forward_trace_handles_isolated_root(data):
    sc = generate_scenario(4, {"domain": "ai4i", "edge_drop": 0.5}, data)
    Go = sc["graph_observed"].copy()
    root = sc["backward_truth"]["root_node"]
    Go.remove_edges_from(list(Go.out_edges(root)))
    tr = forward_trace(Go, root)
    assert tr["affected"] == [] and all(v == [] for v in tr["by_layer"].values())
