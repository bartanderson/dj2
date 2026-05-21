from collections import defaultdict
from tools.analysis.graph.semantic_roles import classify_semantic_role


def structural_score(node_name: str) -> int:
    # PURE GRAPH SIGNAL ONLY
    return 0


def node_semantic_tag(node_name: str) -> str:
    if not node_name:
        return "unknown"

    lowered = node_name.lower()

    if lowered.startswith("test_"):
        return "test_code"
    if lowered == "print":
        return "runtime_noise"
    if lowered == "<module>":
        return "module_root"
    if lowered == "main":
        return "entry_point"

    if node_name[0].isupper():
        return "type_or_class"

    if "." in node_name:
        return "qualified_reference"

    return "general_symbol"


def build_evaluation_snapshot(
    analysis,
    bucket_counts,
    graph,
):
    # ----------------------------
    # DEGREE COMPUTATION
    # ----------------------------
    node_degree = defaultdict(int)

    for edge in graph.edges:
        node_degree[edge.caller] += 1
        node_degree[edge.callee] += 1

    ranked_nodes = []
    for node, degree in node_degree.items():
        role = node_semantic_tag(node)
        ranked_nodes.append((node, degree, degree, role))

    top_nodes = sorted(ranked_nodes, key=lambda x: -x[2])[:10]

    high_fanout = [
        (n, d, s, r)
        for n, d, s, r in top_nodes
        if s > 3
    ]

    # ----------------------------
    # NORMALIZE BUCKETS (LOCKED)
    # ----------------------------
    bucket_summary = {
        "project": bucket_counts.get("project", 0),
        "builtin": bucket_counts.get("builtin", 0),
        "classification_gap": bucket_counts.get("classification_gap", 0),
    }

    # enforce contract
    assert set(bucket_summary.keys()) == {
        "project",
        "builtin",
        "classification_gap",
    }

    # ----------------------------
    # SNAPSHOT OUTPUT (LOCKED CONTRACT)
    # ----------------------------
    return {
        "file_count": getattr(analysis, "file_count", None),
        "edge_count": len(graph.edges),

        "bucket_summary": bucket_summary,

        "graph_insights": {
            "top_nodes_by_degree": top_nodes,
        },

        "structural_signals": {
            "high_fanout_nodes": high_fanout,
        },

        "failure_breakdown": getattr(analysis, "failure_breakdown", {}),
        "unknown_samples": getattr(analysis, "unknown_samples", []),
    }