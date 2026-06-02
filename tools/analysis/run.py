# tools\analysis\run.py
"""
Self‑contained runner that derives database name from the source path.
Usage: python run.py <path_to_analyze>
Example: python run.py tools.old/analysis
  -> creates tools_analysis.db in current directory
"""

import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python run.py <path>")
        sys.exit(1)

    src_path = Path(sys.argv[1]).resolve()
    if not src_path.exists():
        print(f"Error: path not found: {src_path}")
        sys.exit(1)

    # Derive database name: replace slashes/backslashes with underscores
    db_name = str(src_path).replace('/', '_').replace('\\', '_') + ".db"

    print(f"Analyzing: {src_path}")
    print(f"Database:  {db_name}")

    # Run the pipeline
    cmd = [
        sys.executable,
        "tools/analysis/run_analysis_pipeline.py",
        str(src_path),
        "--database", db_name,
    ]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    main()