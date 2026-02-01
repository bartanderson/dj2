# AI Context System - Complete Usage Guide

## Directory Structure Overview

C:\Users\bartl\dev\dj2\
├── ai_context\                     # SYSTEM FILES (you maintain)
│   ├── ai_contract.md
│   ├── development_playbook.md
│   ├── tool_index.json
│   ├── status_manifest.json
│   └── session\                    # GENERATED (auto-created)
│       ├── context_for_ai.txt      # Output for DeepSeek
│       ├── current_session.json    # Session state
│       ├── last_analysis.json      # AI response analysis
│       └── tool_output_*.txt       # Tool execution results
├── scripts\                        # EXECUTABLES (existing venv scripts)
│   ├── context_manager.py          # [OK] Works
│   ├── ai_workflow.py              # [OK] Works
│   ├── tool_discovery.py           # [OK] Works
│   └── start_ai_session.bat        # [OK] Works
└── archive\Docs-old\               # HISTORICAL (original 13 files)

Important: The scripts now look for system files in ai_context/, not root.
Extraction Methods: Old vs New
Method A: Extracting from Archive (Historical Data)
If you need to reference the original 13 documentation files (now in archive/Docs-old/):
```cmd
:: Extract specific section from old SYSTEM_OWNERSHIP.md
python scripts\context_manager.py --query "boundary rules from archive" --source archive

:: Or manually reference for DeepSeek context:
type archive\Docs-old\SYSTEM_OWNERSHIP.md | findstr "AI BOUNDARY"
type archive\Docs-old\PHASE_AUDIT.md | findstr "Active Violations"
Note: The new system maintains current_context.md in ai_context/ which already extracts the 
```

Method B: Current System Data (Primary Method)
Quick Context Generation (Most Common):
```cmd
cd C:\Users\bartl\dev\dj2
scripts\activate.bat

:: Generate context for DeepSeek (copy-paste)
python scripts\context_manager.py --query "WorldState to CampaignState refactor" --target deepseek
:: Then open context_for_ai.txt and paste into DeepSeek web

:: Generate for Local Ollama (direct pipe)
python scripts\context_manager.py --query "Phase violations in DMChatHandler" --target ollama --output session.txt
type session.txt | ollama run llama3.2:3b
```

Method C: Workflow Orchestration (Full Sessions)
Start Tracked Session:
```cmd
python scripts\ai_workflow.py start --topic "CampaignState rename architecture"
:: Generates: current_session.json, context_for_ai.txt
:: Session state tracks: topic, violations, tool status, history
```
Continue Previous Session:
```cmd
python scripts\context_manager.py --query "Continue previous session" --target ollama
:: Checks current_session.json for context continuity
```

Tool Usage Reference
Discover Available Tools
```cmd
:: List all working tools
python scripts\tool_discovery.py

:: Search for specific capability
python scripts\tool_discovery.py violations

:: Get help on specific tool
python scripts\tool_discovery.py --help four_layer
```

Key Tool Matrix
Context Manager [Command]     python scripts\context_manager.py --query "X" --target deepseek
                [Output]      ai_context\session\context_for_ai.txt
                [Use]         Starting any analysis session

Violations      [Command]     python ai.py violations .
                [Output]      Terminal text
                [Use]         Quick phase compliance check

Four Layer      [Command]     python tools\ai_assistant\four_layer.py "topic"
                [Output]      JSON/Analysis
                [Use]         Deep architectural investigation

Search          [Command]     python ai.py search "term" --limit 5
                [Output]      File list
                [When to use] Finding specific code locations

Start Workflow  [Command]     python scripts\ai_workflow.py start --topic "X"
                [Output]      Session files
                [When to use] Multi-step refactoring planning

Extracting Specific Data Types
1. Current Violations (Active Only)
```cmd
:: Automatic (included in context_manager output)
:: OR manual:
python ai.py violations . > ai_context\current_violations.txt
type ai_context\current_violations.txt
```
2. Recent Accomplishments (Auto-extracted)
```cmd
:: Extracts last 30 days from ACCOMPLISHMENTS.md in archive
:: Included automatically in context_manager --target deepseek output
```
3. Tool Status (Auto-extracted)
```cmd
:: Reads ai_context\tool_index.json
:: Shows: Working ✅, Needs Test ⚠️, Broken ❌
python scripts\tool_discovery.py
```
4. Code Snippets (Targeted)
```cmd
:: Extract only class/function matching query (not whole files)
python scripts\context_manager.py --query "class WorldState" --code-only --output code.txt
```
5. Historical Patterns (Archive Mining)
```cmd
:: Search old documentation/implementations
python ai.py archive-search "character creation" --limit 5
```

Data Flow Architecture
Input Sources
 1. ai_context/ai_contract.md - Immutable rules, always loaded
 2. ai_context/tool_index.json - Available capabilities registry
 3. ai_context/current_context.md - Auto-generated current state
 4. archive/Docs-old/ - Historical reference (manual only)
 5. Live code - Extracted via context_manager.py on demand

 Processing Pipeline
	User Query → context_manager.py
	    ↓
	[Extract Documentation: `ai_context/*.md`]
	[Extract Code: ai.py search + four_layer.py]
	[Check System Status: violations, todos]
	    ↓
	Format for Target (DeepSeek=verbose, Ollama=concise)
	    ↓
	Output: context_for_ai.txt
	    ↓
	[DeepSeek Web] OR [Ollama Local]
	    ↓
	AI Response → ai_workflow.py analyze (validation)
	    ↓
	Tool Execution (if suggested) → context updated

Common Workflows

Workflow 1: Analyze New Component
```cmd
:: 1. Get context
python scripts\context_manager.py --query "Analyze PuzzleSystem integration" --target deepseek

:: 2. Paste to DeepSeek, get response
:: 3. Validate response
python scripts\ai_workflow.py analyze --response-file deepseek_response.txt
```

Workflow 2: Fix Phase Violations
```cmd
:: 1. Check current violations (auto-included in context)
:: 2. Start targeted session
python scripts\ai_workflow.py start --topic "Fix DMChatHandler line 293"


:: 3. After AI suggests fix, validate before applying
python ai.py violations . > pre_fix.txt
:: [Apply fix]
python ai.py violations . > post_fix.txt
fc pre_fix.txt post_fix.txt
```

Workflow 3: Archive Old Patterns
```cmd
:: When you need to reference old implementations
python ai.py archive-index  # Index archive/Docs-old if not indexed
python ai.py archive-search "how we did character creation before"
:: Copy relevant excerpt to context when needed
```

Troubleshooting
"File not found: ai_contract.md"
Cause: Running from wrong directory or files not moved to ai_context/
Fix:
```cmd
cd C:\Users\bartl\dev\dj2
dir ai_context\ai_contract.md
:: If missing, move it there from root
```

"No tools found"
Cause: tool_index.json missing or empty
Fix: Check ai_context\tool_index.json exists (see template below)
"Context too large for Ollama"
Fix: Use truncation flags
```cmd
python scripts\context_manager.py --query "topic" --target ollama --max-tokens 2000
```

Need Historical Context from Original Docs
Option A: Direct file access
```cmd
type "archive\Docs-old\PHASE_AUDIT.md" | findstr "January 24"
```

Option B: Search archived index (if indexed)
```cmd
python ai.py archive-search "PHASE_VIOLATION markers" --limit 5
```

Maintenance

Updating System Status
Edit ai_context\status_manifest.json manually or generate via:
```cmd
python scripts\ai_workflow.py status-update
```

Adding New Tools to Registry
Edit ai_context\tool_index.json:
```JSON
{
  "category_name": {
    "new_tool": {
      "tested": true,
      "description": "What it does",
      "windows_cmd": "python scripts\\tool.py"
    }
  }
}
```

Archiving Current Work
When current_context.md becomes obsolete:
```cmd
move ai_context\current_context.md archive\Sessions\context_2026-01-31.md
```

Exit/Backup Strategy
Before major changes:
Git commit current state
Archive current session:
```cmd
xcopy ai_context\*.md archive\Backup\
copy current_session.json archive\Backup\
```

After this, you can safely experiment with context extraction.