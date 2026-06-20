# tools/analysis/agent/agent_prompt.py
#
# System prompt and tool call protocol for the local conversational agent.
# Model: llama3.2:3b via Ollama.
#
# Design constraints (DESIGN.md section 8):
# - Model is small: keep system prompt short, tool descriptions one line each.
# - One tool call per response turn - model reasons briefly, calls one tool,
#   gets the result, decides next step.
# - Model must not guess - if it doesn't know, it calls a tool.
# - Model stores non-obvious findings with store_finding before answering.

TOOL_PROTOCOL = """\
To call a tool, output exactly this format (nothing else on those lines):
TOOL: tool_name
ARGS: {"key": "value"}

Wait for the result before calling another tool. One tool call per response.
If you have enough information to answer, do not call a tool - just answer.
"""

TOOL_DESCRIPTIONS = """\
Available tools:

DISCOVERY - find what exists in the codebase:
  search_symbols   {"query": str}        Find functions/classes by name pattern (up to 20)
  search_files     {"query": str}        Find files by path pattern
  list_callers     {"symbol": str}       Who calls this function directly
  list_callees     {"symbol": str}       What this function calls
  symbols_in_file  {"file_path": str}    All functions/classes defined in a file
  files_in_directory {"path": str}       List files in a directory (e.g. "world")

UNDERSTANDING - what does it mean:
  describe_file    {"file_path": str}    AI summary of what a file does
  symbol_intent    {"symbol": str}       Docstring/stated purpose of a function or class
  symbol_brief     {"symbol": str}       Full impact brief: callers + impact zone

KNOWLEDGE - what do we know, what should we remember:
  get_findings     {"symbol": str}       Stored facts about a symbol from past sessions
  store_finding    {"symbol": str, "kind": str, "content": str}
                                         Save a derived finding for future sessions.
                                         kinds: file_purpose / strategy_decision /
                                                query_finding / design_note / known_issue
  ask_truth_layer  {"question": str}     Structured query: system-wide structural questions
"""

SYSTEM_PROMPT = f"""\
You are a codebase analysis assistant for a Python dungeon-master game project.
You have access to a structural analysis database that knows the call graph,
file contents, and stored findings for the game codebase.

Your job: answer questions about the codebase factually using your tools.
Do not guess or invent information. If you are unsure, call a tool to find out.
When a question requires multiple pieces of information, decompose it: call one
tool at a time, read the result, then decide what to call next.

{TOOL_DESCRIPTIONS}
{TOOL_PROTOCOL}
Rules:
- Always call a tool when you need information you don't have yet.
- If a tool returns no results, say so explicitly rather than guessing.
- If you derive a non-obvious finding (took 2+ tool calls to reach), call
  store_finding before giving your final answer so it is available next session.
- Stale findings (marked [STALE]) should be verified with other tools before trusting.
- Keep answers concise and grounded in what the tools actually returned.
- If asked about a broad area (e.g. "the encounter system"), start with
  search_symbols or files_in_directory to get oriented before going deeper.
"""


def build_messages(history: list[dict], user_input: str) -> list[dict]:
    """
    Build the Ollama message list from conversation history + new user input.
    history is a list of {role, content} dicts (assistant/user turns).
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_input})
    return messages


def parse_tool_call(text: str) -> tuple[str, dict] | tuple[None, None]:
    """
    Parse a TOOL/ARGS block from model output. Tolerant of common small-model
    formatting drift:
      - case-insensitive TOOL/ARGS labels
      - extra whitespace or blank lines between label and value
      - args on same line as ARGS:
      - JSON wrapped in markdown backticks
      - single quotes instead of double quotes
      - tool name with or without trailing colon
      - missing braces on single-key args

    Returns (tool_name, args_dict) or (None, None) if no tool call found.
    """
    import json
    import re

    # Normalise: collapse \r, strip markdown code fences around JSON
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"```(?:json)?\s*", "", text)

    # Find TOOL label (case-insensitive), optional colon, whitespace, then name
    tool_match = re.search(
        r"(?i)tool:?\s*([a-z_][a-z0-9_]*)",
        text,
    )
    if not tool_match:
        return None, None

    tool_name = tool_match.group(1).strip().lower()

    # Find ARGS label anywhere after the TOOL label
    after_tool = text[tool_match.end():]
    args_match = re.search(
        r"(?i)args:?\s*(\{.*?\})",
        after_tool,
        re.DOTALL,
    )

    if not args_match:
        # No args block found - return tool with empty args (some tools need none)
        return tool_name, {}

    args_str = args_match.group(1).strip()

    # Normalise single quotes -> double quotes for JSON parsing
    args_str = re.sub(r"'([^']*)'", lambda m: '"' + m.group(1).replace('"', '\\"') + '"', args_str)

    try:
        args = json.loads(args_str)
        return tool_name, args
    except json.JSONDecodeError:
        pass

    # Recovery pass: extract all "key": "value" pairs individually
    pairs = re.findall(r'"([^"]+)"\s*:\s*"([^"]*)"', args_str)
    if pairs:
        return tool_name, dict(pairs)

    # Last resort: treat whole args_str content as a single "query" value
    # (handles model outputting ARGS: {"encounter"} without a key)
    bare = args_str.strip("{}\"' ")
    if bare:
        return tool_name, {"query": bare}

    return tool_name, {}


def format_observation(tool_name: str, result: str) -> str:
    """Wrap a tool result as an observation message for the next model turn."""
    return f"[Tool result: {tool_name}]\n{result}"
