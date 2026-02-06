# Dev Playbook - Quick Reference

## Phase × Stage Matrix
- **INPUT**: Mechanics → Events → Narrative
- **PROCESSING**: Validation → Interpretation → Planning  
- **OUTPUT**: State Changes → Event Emit → Response

## Critical Patterns
1. **AI→GameEngine→WorldState** (NEVER AI→WorldState directly)
2. **Session owns mutable state** (GameEngine manages it)
3. **Events decouple systems** (fire-and-forget)

## Windows Rules
- CMD: backslashes (`tools\script.py`)
- NO multiline `python -c` (use .py files)
- Single-line only for simple commands

## Tool Patterns
Before: AI→WorldState.update()  # VIOLATION
After:  AI→GameEngine.request()→validated→WorldState  # CORRECT
Copy

## Common Commands
```bash
# Check violations
python ai.py violations .

# Build context  
python scripts/context_manager.py --query "..." --send

# Quick AI analyze
python scripts/ai_workflow.py local-analyze --topic "..."
File Structure
Session: state, history
GameEngine: validation, execution
WorldState: read-only views
Tools: one job each
