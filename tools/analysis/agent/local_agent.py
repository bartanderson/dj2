# tools/analysis/agent/local_agent.py
#
# Local conversational agent backed by Ollama (llama3.2:3b).
# Three-phase pipeline (DESIGN.md section 8):
#   Phase 1 DECOMPOSE - AI lists what it needs (NEED: lines)
#   Phase 2 RESOLVE   - deterministic pattern router runs tool calls
#   Phase 3 ASSEMBLE  - AI reads facts and writes plain English answer
#
# Usage:
#   python tools/analysis/agent/local_agent.py world_corpus.db
#   python tools/analysis/agent/local_agent.py world_corpus.db --verbose
#
# Type 'quit', 'exit', or 'q' to end the session.
# Type 'clear' to reset conversation history.

from __future__ import annotations

import argparse
import sys

import requests

from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor
from tools.analysis.agent.agent_resolver import (
    parse_needs, resolve_and_expand, facts_to_text, ground_question,
    detect_heuristic,
)
from tools.analysis.agent.knowledge_status import coverage_summary, suggest_followups

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 60


# ------------------------------------------------------------------
# Phase 1 prompt - DECOMPOSE
# ------------------------------------------------------------------

_DECOMPOSE_SYSTEM = """\
You are a code analysis assistant. Your job is to list what information
you need to answer a question about a game codebase. Do NOT answer the
question yet. Just list your needs.

Output exactly one NEED: line per piece of information needed.
Use only these patterns (copy exactly):
  NEED: files in <directory>
  NEED: files matching <substring>
  NEED: symbols named <name>
  NEED: symbols in <file.py>
  NEED: what calls <symbol>
  NEED: callees of <symbol>
  NEED: what does <file.py> do
  NEED: intent of <symbol>
  NEED: findings for <symbol>
  NEED: brief for <symbol>

Extract all symbol and file names explicitly from the question.
Output only NEED: lines, nothing else."""


def _decompose_prompt(
    question: str,
    history: list[dict],
    grounding: str = "",
) -> list[dict]:
    messages = [{"role": "system", "content": _DECOMPOSE_SYSTEM}]
    for turn in history[-6:]:  # last 3 Q/A pairs
        messages.append({"role": turn["role"], "content": turn["content"]})
    user_content = question
    if grounding:
        user_content = f"{question}\n\n{grounding}"
    messages.append({"role": "user", "content": user_content})
    return messages


# ------------------------------------------------------------------
# Phase 3 prompt - ASSEMBLE
# ------------------------------------------------------------------

_ASSEMBLE_SYSTEM = """\
You are a code analysis assistant. Answer the question using ONLY
the facts provided below. Be concise and direct. If the facts do not
contain enough information to answer, say so."""


def _assemble_prompt(question: str, facts_text: str, history: list[dict]) -> list[dict]:
    messages = [{"role": "system", "content": _ASSEMBLE_SYSTEM}]
    for turn in history[-6:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    content = f"Question: {question}\n\nFacts retrieved from the codebase:\n{facts_text}"
    messages.append({"role": "user", "content": content})
    return messages


# ------------------------------------------------------------------
# Ollama call
# ------------------------------------------------------------------

def _call_ollama(messages: list[dict], verbose: bool = False, label: str = "") -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1},
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        if verbose and label:
            print(f"\n[{label}]\n{text}\n[/{label}]", flush=True)
        return text
    except requests.exceptions.ConnectionError:
        return "ERROR: Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "ERROR: Ollama timed out. The model may be loading - try again."
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ------------------------------------------------------------------
# Single question/answer cycle (three-phase)
# ------------------------------------------------------------------

def _answer(
    user_input: str,
    history: list[dict],
    oracle: DBOracle,
    assessor: Assessor,
    verbose: bool = False,
) -> tuple[str, list[dict]]:
    """
    Run three-phase pipeline for one user question.
    Returns (final_answer, updated_history).
    History is a list of {role, content} dicts (user/assistant pairs),
    extended in place with the (question, answer) pair.
    """
    # Phase 0: GROUND
    grounding = ground_question(user_input, oracle, assessor)
    if verbose and grounding:
        print(f"\n[phase0-ground]\n{grounding}\n[/phase0-ground]", flush=True)

    # Phase 1: DECOMPOSE - try named heuristic first, fall back to Ollama
    needs = detect_heuristic(user_input)
    if needs:
        if verbose:
            print(f"\n[heuristic matched] {needs}", flush=True)
    else:
        decompose_msgs = _decompose_prompt(user_input, history, grounding=grounding)
        needs_text = _call_ollama(decompose_msgs, verbose=verbose, label="phase1-decompose")
        if needs_text.startswith("ERROR:"):
            return needs_text, history
        needs = parse_needs(needs_text)

    if verbose:
        print(f"\n[needs parsed] {needs}", flush=True)

    # Phase 2: RESOLVE
    facts = []
    if needs:
        facts = resolve_and_expand(needs, oracle, assessor)
        if verbose:
            for f in facts:
                print(f"  [tool={f['tool']} args={f['args']}] {f['result'][:120]}", flush=True)
        facts_text = facts_to_text(facts)
    else:
        facts_text = "(no structured needs identified - answering from general knowledge)"

    # Phase 3: ASSEMBLE
    assemble_msgs = _assemble_prompt(user_input, facts_text, history)
    answer = _call_ollama(assemble_msgs, verbose=verbose, label="phase3-assemble")

    # Phase 4: SUGGEST
    suggestions = suggest_followups(facts, oracle, assessor)
    if suggestions:
        answer = answer + "\n\n" + suggestions

    history.append({"role": "user",      "content": user_input})
    history.append({"role": "assistant", "content": answer})
    return answer, history


# ------------------------------------------------------------------
# Main REPL
# ------------------------------------------------------------------

def run(db_path: str, verbose: bool = False) -> None:
    print(f"\nLoading corpus: {db_path}")
    try:
        oracle = DBOracle(db_path)
        assessor = Assessor(oracle)
    except Exception as e:
        print(f"ERROR loading corpus: {e}")
        sys.exit(1)

    root = oracle.get_project_root() or db_path
    print(f"Project root:   {root}")
    print(f"Model:          {OLLAMA_MODEL}")
    print(f"\n{coverage_summary(oracle, assessor)}")
    print(f"\nType your question. 'clear' to reset. 'quit' to exit.")
    print(f"Special: 'what do you know?' | 'what haven't you explored?' | 'discover'")
    print(f"Workflow: 'what's next' | 'reprioritize' | 'add to backlog: <item>' | 'reorder as 3,1,2'\n")

    history: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        if user_input.lower() == "clear":
            history = []
            print("[conversation history cleared]\n")
            continue

        if user_input.lower() in ("what do you know?", "what do you know"):
            print(f"\n{coverage_summary(oracle, assessor)}\n")
            continue

        if user_input.lower() in ("what haven't you explored?", "what havent you explored?",
                                   "what haven't you explored", "unexplored"):
            from tools.analysis.agent.knowledge_status import coverage_report
            r = coverage_report(oracle, assessor)
            unknown = r["unknown_files"]
            if unknown:
                print(f"\nUnexplored files ({len(unknown)} of {r['total_files']}):")
                for f in unknown:
                    print(f"  {f}")
            else:
                print("\nAll files have been surveyed.")
            print()
            continue

        if user_input.lower() == "discover":
            from tools.analysis.agent.discovery_agent import run as discover_run
            discover_run(db_path, limit=5, verbose=True)
            print(f"\n{coverage_summary(oracle, assessor)}\n")
            continue

        if user_input.lower() in ("reprioritize", "suggest priorities", "suggest order"):
            status = assessor.workflow_status()
            if status == "No active workflow items.":
                print(f"\n{status}\n")
                continue
            msgs = [
                {"role": "system", "content":
                    "You are a project planning assistant. Given a list of workflow items, "
                    "suggest a priority ordering with brief reasoning for each position. "
                    "End with: 'To apply this order, type: reorder as <id>,<id>,...'"},
                {"role": "user", "content":
                    f"Here are the current workflow items:\n\n{status}\n\n"
                    "Suggest a priority order for the active backlog/next_up items, "
                    "considering dependencies and logical sequencing."},
            ]
            suggestion = _call_ollama(msgs, verbose=verbose, label="reprioritize")
            print(f"\nAgent: {suggestion}\n")
            continue

        print("\nThinking...", flush=True)
        answer, history = _answer(user_input, history, oracle, assessor, verbose=verbose)
        print(f"\nAgent: {answer}\n")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Local codebase analysis agent backed by Ollama."
    )
    parser.add_argument("db_path", help="Path to corpus DB (e.g. world_corpus.db)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show phase outputs and tool calls")
    args = parser.parse_args()
    run(args.db_path, verbose=args.verbose)
