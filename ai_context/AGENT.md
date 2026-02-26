# Agent Tools

This document lists all tools available to the AI agent (`agent.py`). Each tool is a Python function in `agent_tools.py`. The agent uses these tools to accomplish user goals.

## Core Tools

| Tool | Arguments | Description | Example |
|------|-----------|-------------|---------|
| `search_files` | `query`, `limit=10`, `group=None` | Search for files using `ai.py search`. Returns list of file paths. | `search_files("character creation")` |
| `read_file` | `path` | Read a single file; returns its content as string. | `read_file("world/character.py")` |
| `read_files` | `file_paths` (list) | Read multiple files; returns dict `{path: content}`. | `read_files(["file1.py", "file2.py"])` |
| `deepseek_consult` | `prompt`, `file=None`, `data=None` | Send a prompt to DeepSeek (with optional file/data). Returns response string. | `deepseek_consult("Summarize this", data=contents)` |
| `write_file` | `path`, `content` | Write content to a file (creates `.bak` backup). Use with caution. | `write_file("output.txt", "analysis...")` |
| `semantic_search` | `query`, `limit=5` | Find files relevant to a natural language query using embeddings. Returns list of `{path, score}`. | `semantic_search("ability score logic")` |

## Git Tools (Optional)

| Tool | Arguments | Description | Example |
|------|-----------|-------------|---------|
| `create_branch` | `branch_name` | Create and switch to a new git branch. | `create_branch("feature/analysis")` |
| `commit_changes` | `message` | Commit all changes with a message. | `commit_changes("Added summary")` |
| `show_diff` | (none) | Show git diff of current changes. | `show_diff()` |

## Analysis Tools

| Tool | Arguments | Description | Example |
|------|-----------|-------------|---------|
| `analyze_tools` | (none) | Run `tool_analyzer` to get full analysis of tools directory. Returns dict. | `analyze_tools()` |

## Adding New Tools

1. Write the function in `agent_tools.py` with a clear docstring.
2. Add a description to `TOOL_DESCRIPTIONS` in `agent.py`.
3. Add a branch in `execute_tool` (in `agent.py`) to call it.
4. Update this document.