# tools/analysis/context/build_context_packet.py

from tools.analysis.query.query_file_analysis import fetch_complete_file_analysis
from tools.analysis.context.context_packet import ContextPacket


def build_context_packet(connection, file_path: str) -> ContextPacket:
    analysis = fetch_complete_file_analysis(connection, file_path)

    if analysis is None:
        return None

    return ContextPacket(
        file_path=file_path,
        summary=analysis["file"],

        key_functions=[f["name"] for f in analysis["functions"]],
        key_classes=[c["name"] for c in analysis["classes"]],

        dependencies=[i["module"] for i in analysis["imports"]],

        referenced_symbols=[
            r["callee"] for r in analysis["symbol_references"]
        ],
    )