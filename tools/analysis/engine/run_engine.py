# tools/analysis/engine/run_engine.py

from dataclasses import dataclass
from typing import Any, Dict
import sqlite3
from pathlib import Path
from tools.analysis.ingestion.scan_project_files import scan_project_files
from tools.analysis.classification.classify_references import classify_references
from tools.analysis.graph.graph_builder import GraphBuilder
from tools.analysis.persistence.persistence_engine import persist_all
from tools.analysis.engine.db_resolver import resolve_analysis_db_path

ENABLE_FAULTS = False  # hard off for now

from pathlib import Path

_LOG_FILE = None
_LOG_ENABLED = True

def enable_log(db_path: str, enabled: bool = True):
    """
    Turns logging on/off.
    Log file is always:
        engine.db -> engine.txt
    """
    global _LOG_FILE, _LOG_ENABLED

    _LOG_ENABLED = enabled

    if not enabled:
        return

    log_path = Path(db_path).with_suffix(".txt")
    _LOG_FILE = open(log_path, "a", encoding="utf-8")

def log_dbg(*args):
    if not _LOG_ENABLED or _LOG_FILE is None:
        return

    _LOG_FILE.write(" ".join(str(a) for a in args) + "\n")

def close_log():
    global _LOG_FILE
    if _LOG_FILE:
        _LOG_FILE.close()
        _LOG_FILE = None

@dataclass
class EngineResult:
    ingestion: Any
    graph: Any
    facts: Dict[str, Any]
    # snapshot: Dict[str, Any]
    # reduced: Any | None = None

class EngineRunner:

    def run(self, corpus, project_prefixes, repo_root, connection=None, chaos_mode: bool = False):

        # ==================================================
        # PHASE 0: INGESTION
        # ==================================================
        file_analyses = list(
            scan_project_files(
                corpus.root_path,
                project_prefixes,
                repo_root,
            )
        )

        # ----------------------------
        # CHAOS MODE (controlled fault injection)
        # ----------------------------
        if chaos_mode:
            print("\n=== CHAOS MODE ACTIVE ===")

            # 1. drop half the files
            file_analyses = file_analyses[: max(1, len(file_analyses) // 2)]

            # 2. corrupt bucket metadata slightly
            for a in file_analyses:
                for r in getattr(a, "symbol_references", []):
                    r.bucket = "unknown"

        if not file_analyses:
            raise RuntimeError("Engine ingestion produced no analyses")

        processed_count = len(file_analyses)

        file_analyses = [
            classify_references(a, project_prefixes)
            for a in file_analyses
        ]

        symbol_reference_count = sum(
            len(a.symbol_references) for a in file_analyses
        )

        ingestion = {
            "file_analyses": file_analyses,
            "processed_count": processed_count,
            "symbol_reference_count": symbol_reference_count,
        }

        # # ==================================================
        # # PHASE 0.5: GLOBAL INIT (MUST EXIST BEFORE ANYTHING ELSE)
        # # ==================================================
        # validator = SystemValidator(strict=False)

        all_reports = []
        drift_signals = []
        validation_errors = []

        # ==================================================
        # PHASE 1: GRAPH BUILD (NO ANALYSIS HERE)
        # ==================================================
        builder = GraphBuilder()

        for analysis in file_analyses:
            for ref in analysis.symbol_references:
                builder.add_reference(
                    caller=ref.caller,
                    callee=ref.callee,
                    line_number=ref.line_number,
                    bucket=getattr(ref, "bucket", "unknown"),
                )

        graph = builder.build()

        if ENABLE_FAULTS:
            from tools.analysis.observability.fault_injector import (
                inject_edge_drop,
                inject_classification_drift,
            )

            graph = inject_edge_drop(graph, rate=0.1)
            file_analyses = inject_classification_drift(file_analyses, rate=0.1)

        edge_count = len(getattr(graph, "edges", []))

        # Obeservability begin
        from tools.analysis.observability.signal_contract import prune_signals
        from tools.analysis.observability.instruments import (
            ingestion_instrument,
            graph_instrument,
            classification_instrument,
        )

        signals = []

        signals += ingestion_instrument(file_analyses)
        signals += graph_instrument(graph)
        signals += classification_instrument(file_analyses)

        signals = prune_signals(signals)

        print("\n=== OBSERVABILITY SIGNALS ===")

        for s in signals:
            print(
                f"{s.stage} | {s.signal_class} | {s.name} = {s.value}"
            )
        # Obeservability end

        print("\n=== SYMBOL REFERENCE SANITY CHECK ===")

        sample = file_analyses[:3]

        for a in sample:
            print(a.file_path)
            print("  symbol_references:", len(a.symbol_references))

        print("TOTAL symbol refs:", sum(len(a.symbol_references) for a in file_analyses))
        print("EDGE COUNT:", edge_count)

        persist_all(
            connection=connection,
            file_analyses=file_analyses,
            graph=graph,
            project_prefixes=project_prefixes,
        )


if __name__ == "__main__":

    # ----------------------------
    # DB TARGETS (explicit roles)
    # ----------------------------

    print("RUNNING ENGINE TEST")
    project_prefixes = []
    repo_root = "."

    #ENGINE_DB = "tools.analysis.data.analysis.db"

    import tkinter as tk 
    from tkinter import filedialog

    root = tk.Tk()

    root.withdraw() # hide the empty window

    # select analysis target path
    selected_target = filedialog.askdirectory(initialdir=Path(__file__).parent) 
    
    corpus = type(
        "Corpus",
        (),
        {"root_path": selected_target},
    )()
 
    db_path = resolve_analysis_db_path(corpus.root_path) # path selected normalized with _ + .db
    enable_log(db_path, enabled=True)   # <- toggle here

    log_dbg("ENGINE START")
    log_dbg("Target:", corpus.root_path)
    log_dbg("DB:", db_path)
    log_dbg("LOG FILE:", str(Path(db_path).with_suffix(".txt")))
    runner = EngineRunner()

    runner.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=sqlite3.connect(db_path),
    )
    print("\nAnalysis complete.")
    print("Database:", db_path)




