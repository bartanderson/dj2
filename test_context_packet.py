from tools.analysis.persistence.persist_file_analysis import create_database
from tools.analysis.context.build_context_packet import build_context_packet

db = create_database("tools/analysis/data/analysis.db")

packet = build_context_packet(
    db,
    "C:/Users/bartl/dev/dj2/tools/analysis/run_analysis_pipeline.py"
)

print(packet)