@echo off
chcp 65001 > nul
cd /d "C:\Users\bartl\dev\dj2"

echo ========================================
echo DUNGEON JOURNEY 2 - AI SESSION STARTER
echo ========================================

:: Check for existing session in ai_context/session/
if exist "ai_context\session\current_session.json" (
    echo Found existing session. Loading...
    python scripts\ai_workflow.py continue
) else (
    :: Start new session
    echo Starting new AI session...
    
    :: Get user query
    set /p "QUERY=What would you like to work on? "
    
    :: Build initial context
    echo Building context for: %QUERY%
    python scripts\ai_workflow.py start --topic "%QUERY%"
    
    echo.
    echo ========================================
    echo Context saved to: ai_context\session\context_for_ai.txt
    echo ========================================
    echo.
    echo To use with DeepSeek:
    echo   1. Open ai_context\session\context_for_ai.txt
    echo   2. Copy contents
    echo   3. Paste into DeepSeek chat
    echo.
    echo To use with local Ollama:
    echo   type ai_context\session\context_for_ai.txt ^| ollama run llama3.2:3b
)

pause