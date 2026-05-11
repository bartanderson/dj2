# tools/analysis/api/query_entry.py

from tools.analysis.query.query_file_analysis import fetch_complete_file_analysis
from tools.analysis.persistence.persist_file_analysis import create_database


def query_entry(db_path: str, entry_file: str):
    connection = create_database(db_path)

    result = fetch_complete_file_analysis(connection, entry_file)

    if result is None:
        return {"error": "file not found"}

    return {
        "file": result["file"],
        "function_count": len(result["functions"]),
        "class_count": len(result["classes"]),
        "import_count": len(result["imports"]),
        "mutation_count": len(result["mutations"]),
        "symbol_reference_count": len(result["symbol_references"]),
    }