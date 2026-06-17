# tools/analysis/tests/regression/run_all.py
#
# Single entrypoint for the whole tools/analysis test suite. Run from
# anywhere (no need to set PYTHONPATH yourself - this script does it):
#
#   python tools\analysis\tests\regression\run_all.py
#
# What it does:
#   1. Auto-discovers every tests/regression/test_*.py module (the plain
#      assert-based "python3 file.py" style suites) and calls every
#      test_* function in each one directly.
#   2. Auto-discovers every truth/tests/test_*.py module and runs it via
#      pytest (these use fixtures/parametrize, not the function-list
#      convention above, so they need pytest's runner).
#   3. Prints one final PASS/FAIL summary across everything.
#
# Auto-discovery means this file does NOT need to be hand-edited every
# time a new test_*.py file is added under either directory - drop a new
# test_*.py in tests/regression/ or truth/tests/ and it's picked up on
# the next run automatically. Only touch this file if the *discovery
# rule itself* needs to change (e.g. a third test directory shows up).
#
# Also suppresses the noisy torch.distributed.elastic "redirects not
# supported on Windows" warning - see the logging.getLogger() call below.
# NOTE: PYTHONWARNINGS=ignore does NOT do this (confirmed 2026-06-17) -
# that warning is emitted via logging.warning(), not warnings.warn(), so
# the `warnings`-module env var has no effect on it. Raising the specific
# logger's level is the only thing that actually works.

import importlib
import logging
import sys
import traceback
from pathlib import Path

logging.getLogger("torch.distributed.elastic.multiprocessing.redirects").setLevel(logging.ERROR)

THIS_FILE = Path(__file__).resolve()
REGRESSION_DIR = THIS_FILE.parent                     # .../tools/analysis/tests/regression
ANALYSIS_DIR = REGRESSION_DIR.parents[1]               # .../tools/analysis
REPO_ROOT = REGRESSION_DIR.parents[3]                  # .../dj2

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRUTH_TESTS_DIR = ANALYSIS_DIR / "truth" / "tests"


def _module_name_for(path: Path) -> str:
    """Turn an absolute file path under REPO_ROOT into a dotted import path."""
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    return ".".join(rel.parts)


def _discover_regression_modules():
    if not REGRESSION_DIR.exists():
        return []
    found = sorted(REGRESSION_DIR.glob("test_*.py"))
    # don't try to import this file as a test module if it ever matches the glob
    return [_module_name_for(p) for p in found if p.resolve() != THIS_FILE]


def _discover_pytest_targets():
    if not TRUTH_TESTS_DIR.exists():
        return []
    return [str(p) for p in sorted(TRUTH_TESTS_DIR.glob("test_*.py"))]


def _run_module(module_name: str) -> tuple[int, int]:
    print(f"\n=== {module_name} ===")
    try:
        module = importlib.import_module(module_name)
    except Exception:
        print(f"FAIL: could not import {module_name}")
        traceback.print_exc()
        return 0, 1

    test_fns = [
        getattr(module, name) for name in dir(module)
        if name.startswith("test_") and callable(getattr(module, name))
    ]

    if not test_fns:
        print(f"(no test_* functions found in {module_name})")
        return 0, 0

    passed = 0
    failed = 0
    for fn in test_fns:
        try:
            fn()
            print(f"PASS: {fn.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL: {fn.__name__}")
            traceback.print_exc()
            failed += 1
    return passed, failed


def main():
    regression_modules = _discover_regression_modules()
    pytest_targets = _discover_pytest_targets()

    total_passed = 0
    total_failed = 0

    for module_name in regression_modules:
        passed, failed = _run_module(module_name)
        total_passed += passed
        total_failed += failed

    pytest_exit_code = 0
    if pytest_targets:
        try:
            import pytest
            print(f"\n=== pytest: {', '.join(pytest_targets)} ===")
            pytest_exit_code = pytest.main(["-q", *pytest_targets])
        except ImportError:
            print(
                "\npytest not installed - skipping "
                f"{', '.join(pytest_targets)} (pip install pytest to include it)"
            )

    print("\n" + "=" * 60)
    print(f"REGRESSION MODULES DISCOVERED: {len(regression_modules)}")
    print(f"REGRESSION TESTS: {total_passed} passed, {total_failed} failed")
    print(f"PYTEST TARGETS DISCOVERED: {len(pytest_targets)}")
    print(f"PYTEST RESULT: {'OK' if pytest_exit_code == 0 else 'FAILURES (see above)'}")
    print("=" * 60)

    if total_failed or pytest_exit_code:
        sys.exit(1)


if __name__ == "__main__":
    main()
