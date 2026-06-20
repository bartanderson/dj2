# tools/analysis/agent/agent_resolver.py
#
# Phase 2 of the three-phase agent pipeline (DESIGN.md section 8).
# Maps NEED lines produced by Phase 1 to tool calls, executes them,
# and returns a flat fact set. Pure Python, no AI calls - independently
# testable.

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.analysis.oracle.db_oracle import DBOracle
    from tools.analysis.assessor.assessor import Assessor

from tools.analysis.agent.agent_tools import dispatch


# ------------------------------------------------------------------
# Phase 0: GROUND
# Extract keywords from the question, run broad searches, return
# a summary of what actually exists in the corpus. This is injected
# into the Phase 1 prompt so the model selects from real names
# rather than inventing plausible-sounding ones.
# ------------------------------------------------------------------

_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must",
    "what", "how", "where", "when", "why", "which", "who", "whom",
    "this", "that", "these", "those", "it", "its",
    "of", "in", "on", "at", "to", "for", "by", "with", "about",
    "from", "into", "through", "during", "before", "after",
    "and", "or", "but", "not", "so", "yet", "both", "either",
    "currently", "handled", "status", "tell", "me", "show", "find",
    "get", "give", "list", "describe", "explain", "there", "their",
    "they", "them", "we", "our", "my", "your", "any", "all", "each",
    "more", "most", "other", "some", "such", "no", "nor", "only",
    "own", "same", "than", "too", "very", "just", "also", "now",
    "system", "code", "codebase", "file", "files", "function",
    "functions", "class", "classes", "module", "modules",
})


def _extract_keywords(question: str) -> list[str]:
    """
    Extract search-worthy keywords from a natural language question.
    Returns words ordered longest-first (longer = more specific).
    """
    words = re.findall(r"[a-zA-Z_]\w*", question)
    seen: set[str] = set()
    keywords = []
    for w in words:
        low = w.lower()
        if low not in _STOPWORDS and len(low) >= 3 and low not in seen:
            seen.add(low)
            keywords.append(w)
    # Longer words are more specific - sort descending by length, keep top 5
    keywords.sort(key=len, reverse=True)
    return keywords[:5]


def ground_question(question: str, oracle: "DBOracle", assessor: "Assessor") -> str:
    """
    Phase 0: broad keyword search against the corpus.
    Returns a short grounding block (text) for injection into the Phase 1 prompt.
    Empty string if nothing found.
    """
    keywords = _extract_keywords(question)
    if not keywords:
        return ""

    found_symbols: dict[str, str] = {}   # name -> file_short
    found_files: list[str] = []
    seen_files: set[str] = set()

    for kw in keywords:
        # Search symbols
        try:
            rows = oracle.find_symbols(kw, limit=10)
            for r in rows:
                if r["name"] not in found_symbols:
                    file_short = r["file_path"].replace("\\", "/").split("/")[-1]
                    found_symbols[r["name"]] = file_short
        except Exception:
            pass

        # Search files
        try:
            rows = oracle.find_files(pattern=kw)
            root = oracle.get_project_root().replace("\\", "/")
            for r in rows:
                fp = r["file_path"].replace("\\", "/")
                if root and fp.startswith(root + "/"):
                    fp = fp[len(root) + 1:]
                if fp not in seen_files:
                    seen_files.add(fp)
                    found_files.append(fp)
        except Exception:
            pass

    if not found_symbols and not found_files:
        return ""

    lines = ["Corpus search results (use these actual names in your NEED: lines):"]
    if found_symbols:
        sym_list = ", ".join(
            f"{n} (in {f})" for n, f in list(found_symbols.items())[:10]
        )
        lines.append(f"  Symbols found: {sym_list}")
    if found_files:
        lines.append(f"  Files found: {', '.join(found_files[:8])}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Pattern table: (regex, tool_name, arg_key, group_index)
# Patterns are tried in order; first match wins for each NEED line.
# ------------------------------------------------------------------

_PATTERNS = [
    # "files in <dir>"
    (re.compile(r"files?\s+in\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "files_in_directory", "path", 1),

    # "files matching <query>" / "files named <query>"
    (re.compile(r"files?\s+(?:matching|named)\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "search_files", "query", 1),

    # "symbols named <name>" / "symbol named <name>"
    (re.compile(r"symbols?\s+named\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "search_symbols", "query", 1),

    # "symbols in <file>" / "symbols in <file>.py"
    (re.compile(r"symbols?\s+in\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "symbols_in_file", "file_path", 1),

    # "what calls <symbol>" / "callers of <symbol>"
    (re.compile(r"(?:what\s+calls|callers?\s+of)\s+['\"]?(\S+?)['\"]?\s*$", re.I),
     "list_callers", "symbol", 1),

    # "what <symbol> calls" / "callees of <symbol>"
    (re.compile(r"(?:what\s+\S+\s+calls|callees?\s+of)\s+['\"]?(\S+?)['\"]?\s*$", re.I),
     "list_callees", "symbol", 1),

    # "what does <file>.py do" / "describe <file>"
    (re.compile(r"(?:what\s+does\s+['\"]?(.+?\.py)['\"]?\s+do|describe\s+(?:file\s+)?['\"]?(.+?\.py)['\"]?)\s*$", re.I),
     "describe_file", "file_path", None),  # group_index=None: handle multi-group below

    # "intent of <symbol>" / "purpose of <symbol>"
    (re.compile(r"(?:intent|purpose)\s+of\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "symbol_intent", "symbol", 1),

    # "findings for <symbol>" / "known findings for <symbol>"
    (re.compile(r"(?:known\s+)?findings?\s+for\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "get_findings", "symbol", 1),

    # "brief for <symbol>"
    (re.compile(r"brief\s+for\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "symbol_brief", "symbol", 1),

    # "search <query>" / "find <query>" - fallback to search_symbols
    (re.compile(r"(?:search|find)\s+['\"]?([^'\"]+?)['\"]?\s*$", re.I),
     "search_symbols", "query", 1),
]


def parse_needs(model_output: str) -> list[str]:
    """
    Extract NEED lines from Phase 1 model output.
    Accepts 'NEED: ...' or '- NEED: ...' or '* NEED: ...' forms.
    Returns list of need strings (stripped, lowercased).
    """
    needs = []
    for line in model_output.splitlines():
        line = line.strip()
        m = re.match(r"[-*]?\s*NEED:\s*(.+)", line, re.I)
        if m:
            needs.append(m.group(1).strip())
    return needs


def resolve_need(need: str) -> tuple[str, dict] | None:
    """
    Map a single NEED string to (tool_name, args_dict).
    Returns None if no pattern matches.
    """
    for pattern, tool_name, arg_key, group_idx in _PATTERNS:
        m = pattern.search(need)
        if m:
            if group_idx is None:
                # multi-group: pick first non-None group
                value = next((g for g in m.groups() if g is not None), "").strip()
            else:
                value = m.group(group_idx).strip()
            if value:
                # Strip glob characters - the DB uses substring matching, not glob
                if tool_name in ("search_files", "search_symbols"):
                    value = value.replace("*", "").replace("?", "").strip()
                if value:
                    return tool_name, {arg_key: value}
    return None


def resolve_all(
    needs: list[str],
    oracle: "DBOracle",
    assessor: "Assessor",
) -> list[dict]:
    """
    Resolve and execute all NEEDs. Returns list of fact dicts:
      { "need": str, "tool": str, "args": dict, "result": str }
    Unmatched NEEDs are included with tool="unmatched" and result="".
    Duplicate (tool, args) pairs are deduplicated - each unique call runs once.
    """
    facts = []
    seen: set[tuple] = set()

    for need in needs:
        resolved = resolve_need(need)
        if resolved is None:
            facts.append({"need": need, "tool": "unmatched", "args": {}, "result": ""})
            continue

        tool_name, args = resolved
        dedup_key = (tool_name, tuple(sorted(args.items())))
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        result = dispatch(tool_name, args, oracle, assessor)
        facts.append({"need": need, "tool": tool_name, "args": args, "result": result})

    return facts


# ------------------------------------------------------------------
# Phase 2b: auto-expansion
# Extract leads from Phase 2 results and run follow-up tool calls.
# All pure Python - no AI call needed.
# ------------------------------------------------------------------

_SYM_LINE = re.compile(r"^\s+(\w+)\s+\(\w+\)\s+in\s+\S+\s+line\s+\d+")
_FILE_LINE = re.compile(r"^\s+(\S+\.py)\s+\(\d+\s+lines\)")
_SIF_LINE  = re.compile(r"^\s+line\s+\d+:\s+(?:function|class)\s+(\w+)")

_MAX_EXPAND = 5  # max symbols or files to follow up per result

# Generic boilerplate names not worth expanding - they appear everywhere
# and produce noisy, question-irrelevant results.
_EXPANSION_NOISE = frozenset({
    "__init__", "__str__", "__repr__", "__eq__", "__hash__", "__len__",
    "__iter__", "__next__", "__contains__", "__getitem__", "__setitem__",
    "__delitem__", "__enter__", "__exit__", "__call__", "__del__",
    "to_dict", "from_dict", "to_json", "from_json", "serialize",
    "deserialize", "update", "get", "set", "reset", "clear",
})


def _symbols_from_result(result: str) -> list[str]:
    """Extract symbol names from search_symbols or symbols_in_file output.
    Filters out generic boilerplate names that add noise to expansion."""
    names = []
    for line in result.splitlines():
        m = _SYM_LINE.match(line) or _SIF_LINE.match(line)
        if m:
            name = m.group(1)
            if name not in _EXPANSION_NOISE and not name.startswith("__"):
                names.append(name)
        if len(names) >= _MAX_EXPAND:
            break
    return names


def _files_from_result(result: str) -> list[str]:
    """Extract .py file paths from files_in_directory or search_files output."""
    paths = []
    for line in result.splitlines():
        m = _FILE_LINE.match(line)
        if m:
            paths.append(m.group(1))
        if len(paths) >= _MAX_EXPAND:
            break
    return paths


def _run_expansion(
    tool_name: str,
    args: dict,
    result: str,
    seen: set[tuple],
    oracle: "DBOracle",
    assessor: "Assessor",
) -> list[dict]:
    """
    Given one Phase 2 result, produce follow-up facts (Phase 2b).
    Expansion rules:
      search_symbols / symbols_in_file -> list_callers + symbol_intent per symbol
      files_in_directory / search_files -> symbols_in_file per file
      list_callers                      -> symbol_intent per caller name
    """
    expansions = []

    if tool_name in ("search_symbols", "symbols_in_file", "list_callers"):
        for sym in _symbols_from_result(result):
            for follow_tool, follow_args in [
                ("list_callers",  {"symbol": sym}),
                ("symbol_intent", {"symbol": sym}),
            ]:
                key = (follow_tool, tuple(sorted(follow_args.items())))
                if key in seen:
                    continue
                seen.add(key)
                r = dispatch(follow_tool, follow_args, oracle, assessor)
                expansions.append({
                    "need": f"[auto] {follow_tool}({sym})",
                    "tool": follow_tool,
                    "args": follow_args,
                    "result": r,
                })

    return expansions


def expand_facts(
    facts: list[dict],
    oracle: "DBOracle",
    assessor: "Assessor",
    seen: set[tuple],
) -> list[dict]:
    """
    Phase 2b: run one round of follow-up tool calls based on Phase 2 results.
    Returns new fact dicts to append (does not mutate `facts`).
    `seen` is the dedup set from resolve_all, passed in and extended in place.
    """
    new_facts = []
    for f in facts:
        if f["tool"] == "unmatched" or not f["result"]:
            continue
        new_facts.extend(_run_expansion(f["tool"], f["args"], f["result"], seen, oracle, assessor))
    return new_facts


def resolve_and_expand(
    needs: list[str],
    oracle: "DBOracle",
    assessor: "Assessor",
) -> list[dict]:
    """
    Phase 2 + Phase 2b combined entry point.
    Returns all facts (Phase 2 results + auto-expansion follow-ups).
    """
    seen: set[tuple] = set()

    # Phase 2 - primary resolution
    facts = []
    for need in needs:
        resolved = resolve_need(need)
        if resolved is None:
            facts.append({"need": need, "tool": "unmatched", "args": {}, "result": ""})
            continue
        tool_name, args = resolved
        key = (tool_name, tuple(sorted(args.items())))
        if key in seen:
            continue
        seen.add(key)
        result = dispatch(tool_name, args, oracle, assessor)
        facts.append({"need": need, "tool": tool_name, "args": args, "result": result})

    # Phase 2b - auto-expansion
    facts.extend(expand_facts(facts, oracle, assessor, seen))

    return facts


def facts_to_text(facts: list[dict]) -> str:
    """
    Format fact set as readable text block for Phase 3 prompt.
    Skips unmatched and empty results.
    """
    sections = []
    for f in facts:
        if f["tool"] == "unmatched" or not f["result"]:
            continue
        sections.append(f["result"])
    return "\n\n".join(sections) if sections else "(no facts retrieved)"
