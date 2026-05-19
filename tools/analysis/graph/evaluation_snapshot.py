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
    failure_events=None,
):
    failure_events = failure_events or []
    failure_breakdown = defaultdict(int)
    unknown_examples = []
    for event in failure_events:
        if not isinstance(event, dict):
            continue

        bucket = event.get("bucket", "unknown")
        failure_breakdown[bucket] += 1

        # keep only a few samples (avoid log explosion)
        if len(unknown_examples) < 10:
            unknown_examples.append(event)
                
    node_degree = defaultdict(int)

    for edge in graph.edges:
        node_degree[edge.caller] += 1
        node_degree[edge.callee] += 1

    ranked_nodes = []

    for node, degree in node_degree.items():

        role = node_semantic_tag(node)

        structural_score = degree

        ranked_nodes.append(
            (node, degree, structural_score, role)
        )

    top_nodes = sorted(ranked_nodes, key=lambda x: -x[2])[:10]

    high_fanout = [
        (n, d, s, r)
        for n, d, s, r in top_nodes
        if s > 3
    ]

    failure_breakdown = defaultdict(int)

    for event in failure_events:
        if not event:
            continue

        if isinstance(event, dict):
            bucket = event.get("bucket", "classification_gap")
        else:
            bucket = str(event)

        failure_breakdown[bucket] += 1

    return {
        "file_count": getattr(analysis, "file_count", None),
        "edge_count": len(graph.edges),

        "bucket_summary": dict(bucket_counts),

        "graph_insights": {
            "top_nodes_by_degree": top_nodes,
        },

        "structural_signals": {
            "high_fanout_nodes": high_fanout,
        },

        # NEW STRUCTURED FAILURE VIEW
        "failure_breakdown": dict(failure_breakdown),
        "unknown_samples": unknown_examples,
    }