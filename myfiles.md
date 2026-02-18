(dj2) C:\Users\bartl\dev\dj2>dir tools\ /ad /b
ai_assistant
analysis
architecture
bridge
coverage_analyzer
future -- files I saved from old code with ideas/examples for stuff I want to do - also todos in code
nativeclaw
reporter
scanner
utils
workflow
__pycache__

(dj2) C:\Users\bartl\dev\dj2>for /d %i in (tools\*) do @echo %i && if exist %i\*.py dir %i\*.py /b
tools\ai_assistant
context_builder.py -- hmm says - BridgeAgent for building context - Simplified version
editing_commands.py - Flexible editing commands - Direct operations only (no backup)
Simplified version without backup functionality -- but don't know that we ever got these working with ai
four_layer.py -- deep coverage maybe - Four-layer analysis - Uses your ast_analyzer as the engine
Patched from Original V2: fixed imports and paths
__init__.py
tools\analysis
agent.py Multi‑turn ReAct agent for test generation.
Supports --one-shot mode to stop after first tool call.
arch_recon.py - Architecture Reconnaissance + Scout + Recon + Ask + Context + Consult + Test
ast_analyzer.py - Core AST analysis engine for the project.
clean_and_repopulate.py - Clean and repopulate dependent tables after a scout scan.Run this after arch_recon.py --scout to fix duplicates and ensure data consistency. -- may be discarded if not needed
context_assembler.py - Intent-driven file discovery using discovered categories
db_operations.py -- part of arch_recon.py
db_queries.py -- part of arch_recon.py
discover_categories.py - Discover hierarchical categories from code identifiers. Links to violations/TODOs to find blockers
dump_context.py - Dump the full context that would be sent to the AI for test generation. Improved import resolution: searches the files table for likely matches.
embedding_model.py - all-MiniLM-L6-v2 to embed_text normalized for cosine similarity and cosine_similarity (both normalized)
extractors.py module name (dotted) from path, extracts (imports, dict key access, method params, constructor params)
generate_test.pyGenerate a test for a given intent using full context:
- Target file source
- Sources of its direct imports (resolved via full module paths)
- External packages noted
- Architectural rules (AI Contract, Development Playbook)

guardrails.py - Real guardrails implementation using your existing AST analyzer. Validates code against AI Contract rules
intent_matcher.py - _get_top_files_for_intent using embedding model functions, maybe integrate them if nothing else uses them?
phase_checker.py - Real phase compliance checker using your existing tools. Checks for phase mixing and boundary violations
populate_imports.py - Populate the imports table from all files in the files table. Run standalone: python tools/analysis/populate_imports.py or import and call populate_imports(db_path) after a scout scan.
reporters.py -- part of arch_recon.py
scanner.py -- part of arch_recon.py
test_templates.py - Manages test patterns extracted from existing high-quality tests.?
test_tools.py - Tools for test generation, to be used with agent.py. Exports TOOLS and HANDLERS.
utils.py module_to_file_path split_identifier classify_role should_ignore - used by dump_context and generate_test
__init__.py
tools\architecture
enhanced_architect.py - Enhanced Living Architect, analyzes project
__init__.py
tools\bridge
bridge_controller.py - Bridge Controller - Updated to use React bridge for file upload capability
deepseek_bridge_react.py - DeepSeek Bridge - React-aware version using unified core. Maintains exact same interface for backward compatibility. Unsure what there is to be backward compatible with so there may be something to remove if true
unified_core.py - Unified bridge core - Internal implementation used by compatibility wrappers, likely then bears investigation of supposed compatibility
__init__.py
tools\coverage_analyzer -- new
run.py -- new
tools\future
mcp_server.py -- do do maybe
test_server.py -- example maybe
tools\nativeclaw -- new
nativeclaw.py -- new
tools\reporter
run.py -- new
tools\scanner
run.py -- new
tools\utils
format_ai_markdown.py -- supposed to fix markdown but not really used, it was early and AI is forgiving of markdown and if I can read it, it is okish
__init__.py
tools\workflow
__init__.py
tools\__pycache__

(dj2) C:\Users\bartl\dev\dj2>
(dj2) C:\Users\bartl\dev\dj2>echo "=== ROOT PYTHON FILES ==="
"=== ROOT PYTHON FILES ==="

(dj2) C:\Users\bartl\dev\dj2>dir *.py /b
ai.py - CLI main command 
app.py - older version of one of the newer world or dungeon app.py
bidirectional_cli.py - early version of getting messages to/from deepseek on the web
check_imports.py - tiny likely not really needed
create_tables.py - original tables creation for the project, not to be confused with tables for tools
dungeon_neo_web_app.py - run by run_game.py for access to the dungeon generation/movement portion
run_analysis.py - says Run Analysis Suite - Executes all code analysis tools
Generates reports for the Project Auditor dashboard
Run this before using project_auditor_v2.py -- but I don't know if its actually up to date now
run_game.py - starts the two portions of world and dungeon flask parts
test.py - ephemeral file that gets whatever is being tested temporarily
tie.py - Test import extraction from a file without modifying the DB. -- likely outdated
tii.py - Test inserting imports for character_builder.py into the DB. -- likely outdated
world_app.py run by run_game.py for access to the main flask app for world map and character generation, world movement and other world stuff before you get to a dungeon
__init__.py -- you know, I don't really understand but is part of the project I know
(dj2) C:\Users\bartl\dev\dj2\tests> -- work in progress with generation scripts if you can do better we wack them
ref_test_character_builder.py - was a first generated test by ai or something
test_ai_dungeon_master.py ?
test_character -generated manually fixed with AI help. More fixes.py
test_character_builder.py ?
test_character_creation.py ?
test_tool_system.py ?
============
run_analysis readme - may also be out of date but we were trying to get a handle on tools/testing like now
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

