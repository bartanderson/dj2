# tools/analysis/tests/fixtures/sample_project/runtime_case.py

from tools.analysis.context.build_context_bundle import build_context_bundle
import tools.analysis.context.build_context_bundle as ctx


def handler():
    x = build_context_bundle
    y = ctx.build_context_bundle
    return x, y