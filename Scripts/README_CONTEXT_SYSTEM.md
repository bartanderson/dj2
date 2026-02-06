\# Unified Context Extraction System - DJ2



\## Overview

A production-ready system to extract ONLY relevant code and documentation for AI analysis, replacing manual copy-paste.



\## Quick Start



\### 1. For DeepSeek Web (Copy-Paste):

```cmd

python scripts\context_manager.py --query "How to refactor WorldState?" --target deepseek'

Then open context_for_ai.txt and paste into DeepSeek.

2. For Local Ollama:
cmd
python scripts\context_manager.py --query "Phase violations in DMChatHandler" --target ollama --output session.txt
type session.txt | ollama run llama3.2:3b
```
3. Quick Tool Discovery:
```cmd
python scripts\tool_discovery.py violations
python scripts\tool_discovery.py --help four_layer
```
Complete Workflow
Step 1: Start Session
```cmd
python scripts\ai_workflow.py start --topic "WorldState to CampaignState refactor"
```
Step 2: Get Context (Copy from context_for_ai.txt)
System boundaries from SYSTEM_OWNERSHIP.md

Phase rules from ENGINE_LOOP.md

Current violations from PHASE_AUDIT.md

ONLY relevant code snippets (not entire files)

Tool availability status

Step 3: AI Responds with Analysis
AI might suggest: "Use the four_layer tool to analyze dependencies"

Step 4: Execute Tool
```cmd
python scripts\ai_workflow.py execute --tool four_layer
```
Then provide the output back to AI.

Step 5: Validate Suggestions
```cmd
python scripts\ai_workflow.py analyze --response-file ai_suggestion.txt
```
Key Features
Smart Extraction: Uses ai.py search + four_layer.py to find ONLY relevant code

Token Budgeting: Automatically trims to ~4000 tokens

Multiple Targets: Optimized for DeepSeek (verbose) or Ollama (concise)

Fallback Strategies: If Whoosh fails, uses filesystem search

Tool Integration: One-command access to all analysis tools

File Structure

scripts/
├── context_manager.py      # MAIN unified extractor
├── tool_discovery.py       # Quick tool reference
├── ai_workflow.py         # Complete workflow orchestrator
└── start_ai_session.bat   # Windows batch starter
Common Examples
Extract code-only context:
```cmd
python scripts\context_manager.py --query "GameEngine initialization" --code-only
```
Get JSON for programmatic use:
```cmd
python scripts\context_manager.py --query "Current state" --target json
```
Quick violation check:
```cmd
python ai.py violations . > violations.txt
python scripts\context_manager.py --query "fix these violations" --no-code
```
Integration with Existing Tools
The system automatically detects and uses:

ai.py for searching

Whoosh index for fast lookup

four_layer.py for deep analysis

AST analyzer for violation detection

Troubleshooting
Problem: "No code found"
Solution: Try different strategy:

```cmd
python scripts\context_manager.py --query "your query" --verbose
```
Problem: Context too large
Solution: Limit tokens:

```cmd
python scripts\context_manager.py --query "your query" --max-tokens 2000
```
Problem: Need specific tool
Solution: Discover tools:

```cmd
python scripts\tool_discovery.py extract
python scripts\tool_discovery.py --help context_manager
```
Pro Tips
Start sessions: Always use ai_workflow.py start to track context

Save outputs: Tool outputs are saved for AI context

Validate: Always run violations . after AI suggestions

Use dry-run: For editing commands, use --dry-run first

Support
Run: python scripts\context_manager.py --help

Check: python scripts\tool_discovery.py

Validate: python ai.py bridge-status

text

## **Key Advantages of This System:**

1. **No Holes**: Complete workflow from query → extraction → AI → validation
2. **Universal**: Works for DeepSeek web AND local Ollama
3. **Production-Ready**: Error handling, fallbacks, token management
4. **Constructive**: Guides next steps, suggests tools
5. **Cohesive**: All components work together
6. **Parameterized**: Flexible for any query or target
7. **Useful**: Actually solves the manual copy-paste problem

## **To Install:**

```cmd
cd C:\Users\bartl\dev\dj2
mkdir scripts  # if not exists
# Copy all 5 files above into scripts\
python scripts\context_manager.py --query "test" --target deepseek
```
This gives you a complete, bulletproof system where you can:

Ask any question about your codebase

Get ONLY relevant context (not everything)

Have clear next steps

Execute tools as needed

Validate AI suggestions

The system automatically handles the extraction complexity while giving you a simple interface.

