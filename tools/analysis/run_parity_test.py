from tools.analysis.engine.core.engine_run import EngineRunner
from tools.analysis.engine.core.ingestion import EngineIngestion
from tools.analysis.engine.core.graph import EngineGraphBuilder
from tools.analysis.engine.core.facts import EngineFacts
from tools.analysis.engine.core.snapshot import EngineSnapshotBuilder

from tools.analysis.engine.parity import ParityChecker

# ⚠️ IMPORTANT:
# You must replace this import with your REAL pipeline entrypoint
# based on EngineRunner.run(...) logic you already have.
from tools.analysis.engine.core.engine_run import EngineRunner as PipelineRunner


def run_engine(corpus, project_prefixes, repo_root, connection=None):
    engine = EngineRunner(
        ingestion=EngineIngestion(),
        graph=EngineGraph(),
        facts=EngineFacts(),
        snapshot_builder=EngineSnapshotBuilder(),
    )

    return engine.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=connection,
    )


def run_pipeline(corpus, project_prefixes, repo_root, connection=None):
    pipeline = PipelineRunner(
        ingestion=EngineIngestion(),
        graph=EngineGraph(),
        facts=EngineFacts(),
        snapshot_builder=EngineSnapshotBuilder(),
    )

    return pipeline.run(
        corpus=corpus,
        project_prefixes=project_prefixes,
        repo_root=repo_root,
        connection=connection,
    )


def main():
    # ----------------------------------------
    # YOU MUST PROVIDE THESE
    # ----------------------------------------
    corpus = None  # <-- replace with real corpus loader
    project_prefixes = []
    repo_root = "."
    connection = None

    # ----------------------------------------
    # RUN BOTH SYSTEMS
    # ----------------------------------------
    engine_result = run_engine(corpus, project_prefixes, repo_root, connection)
    pipeline_result = run_pipeline(corpus, project_prefixes, repo_root, connection)

    # ----------------------------------------
    # PARITY CHECK
    # ----------------------------------------
    checker = ParityChecker()
    result = checker.compare(engine_result, pipeline_result)

    # ----------------------------------------
    # OUTPUT
    # ----------------------------------------
    print("\n=== PARITY RESULT ===")
    print("MATCH:", result.match)

    if not result.match:
        print("\n=== DIFFERENCES ===")
        for diff in result.differences:
            print(diff)


if __name__ == "__main__":
    main()