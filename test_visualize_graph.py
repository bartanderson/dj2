from tools.analysis.graph.build_dependency_graph import build_dependency_graph
from tools.analysis.graph.visualize_dependency_graph import visualize_dependency_graph

from tools.analysis.query.query_file_analysis import fetch_complete_file_analysis
from tools.analysis.persistence.persist_file_analysis import create_database

db = create_database("tools/analysis/data/analysis.db")
cursor = db.cursor()

cursor.execute("SELECT file_path FROM files")
files = [r[0] for r in cursor.fetchall()]

file_analyses = []
for f in files:
    file_analyses.append(fetch_complete_file_analysis(db, f))

edges = build_dependency_graph(file_analyses)

visualize_dependency_graph(edges)