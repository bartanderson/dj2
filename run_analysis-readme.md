📁 run_analysis.py

🕐 When to Run It:
First Time Setup:

# 1. Install dependencies (if not already)
```cmd
pip install coverage radon
```

# 2. Run full analysis (takes 2-5 minutes)
python run_analysis.py
Regular Workflow:
When	What to Run	Why
Start of day	python run_analysis.py --quick	Get fresh metrics for planning
After major changes	python run_analysis.py	Full analysis to see impact
Before refactoring	python run_analysis.py	Baseline for comparison
Weekly	python run_analysis.py	Track progress over time
Common Scenarios:

# Quick check - just coverage (~30 seconds)
python run_analysis.py --quick

# Full analysis - coverage + complexity (~2-5 minutes)
python run_analysis.py

# Check if tools are installed
python run_analysis.py --check

# Clean old reports
python run_analysis.py --clean

# Force re-run even if reports exist
python run_analysis.py --force
📊 How It Works:
Runs your tests with coverage run run_game.py

Generates coverage report as JSON

Analyzes code complexity with radon

Creates manifest with metadata

Outputs reports to reports/ directory

🎯 Integration with Your Workflow:

# Your complete workflow:
1. python run_analysis.py          # Generate metrics
2. python project_auditor.py       # See dashboard
3. python ai.py                    # Work on top priority
4. git commit                      # Commit changes
5. Repeat 1-4                      # Track improvement
⏱️ Expected Runtime:
Analysis Type	Time	What It Does
Quick	30-60s	Just coverage on run_game.py
Full	2-5min	Coverage + complexity of all directories
First Run	3-6min	May be slower if wily runs
🔧 If It Fails:
Common issues and fixes:


# If coverage fails - check your run_game.py
python run_game.py  # Should run without errors

# If radon fails - install it
pip install radon

# If memory error - reduce directories
python -m radon cc core/ dungeon_neo/ -a -j > reports/source_complexity.json

# If timeout - increase timeout in run_analysis.py
# Change timeout=300 to timeout=600
📈 The Payoff:
After running this, you'll have:

reports/coverage.json - Shows exactly what code is tested

reports/source_complexity.json - Shows which files are complex

Data for your dashboard - Real metrics for decision making

🚀 Your Next Step:

# 1. Save the file as run_analysis.py
# 2. Run it once to generate baseline metrics
python run_analysis.py

# 3. Then see your complete dashboard
python project_auditor.py
This creates a complete feedback loop: Run analysis → See dashboard → Fix issues → Re-run analysis → See improvement.

Want me to create a simpler version if this seems too complex? Or shall we run it and see what your actual metrics look like?

