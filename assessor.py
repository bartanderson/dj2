from tools.analysis.oracle.db_oracle import DBOracle


oracle = DBOracle("C_Users_bartl_dev_dj2_tools_analysis_engine.db")

# snapshot graph (RAW STRUCTURE LAYER)
graph = oracle.get_snapshot_graph()

print("number of graph edges:", len(graph.edges))
print("first edge:", graph.edges[0])

# semantic layer (INTERPRETED VIEW)
semantic = oracle.get_semantic_edges()
print("first semantic edge", semantic[0])

# oracle queries (TRAVERSAL ENGINE)
print("neighbors:", oracle.neighbors("re.sub"))
print("surface:", oracle.surface("resolve_analysis_db_path", 1))
print("influence:", oracle.influence("resolve_analysis_db_path", 1))

# semantic projection
print("semantic edges:", semantic[:1])