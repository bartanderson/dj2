# tools/analysis/ccss/cli.py

from pathlib import Path
from tools.analysis.ccss.scan_tests import scan_test_file
from collections import Counter


def run():
    root = Path("tools/analysis/tests")

    all_signals = []

    for file in root.rglob("test_*.py"):
        all_signals.extend(scan_test_file(file))

    for s in all_signals:
        print("\nTEST:", s.test_name)
        print("FILE:", s.file_path)
        print("CANDIDATES:", s.candidate_symbols)

    symbol_counter = Counter()

    for s in all_signals:
        symbol_counter.update(s.candidate_symbols)

    print("\n================ SUMMARY ================\n")

    print("TOTAL TESTS:", len(all_signals))
    print("UNIQUE CANDIDATE SYMBOLS:", len(symbol_counter))

    print("\n================ SYMBOL FREQUENCY ================\n")

    for symbol, count in symbol_counter.most_common():
        print(f"{symbol:<40} {count}")


if __name__ == "__main__":
    run()