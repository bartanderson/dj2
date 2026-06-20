# tools/analysis/agent/local_agent.py
#
# Local conversational agent backed by Ollama (llama3.2:3b).
# DESIGN.md section 8.
#
# Usage:
#   python tools/analysis/agent/local_agent.py world_corpus.db
#   python tools/analysis/agent/local_agent.py world_corpus.db --verbose
#
# Type 'quit', 'exit', or 'q' to end the session.
# Type 'clear' to reset conversation history.
# Type 'tools' to list available tools.

from __future__ import annotations

import argparse
import json
import sys

import requests

from tools.analysis.oracle.db_oracle import DBOracle
from tools.analysis.assessor.assessor import Assessor
from tools.analysis.agent.agent_tools import dispatch, TOOLS
from tools.analysis.agent.agent_prompt import (
    build_messages, parse_tool_call, format_observation,
)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT = 30
MAX_TOOL_TURNS = 8  # max tool calls per user question before forcing an answer


# ------------------------------------------------------------------
# Ollama call
# ------------------------------------------------------------------

def _call_ollama(messages: list[dict], verbose: bool = False) -> str:
    """Call Ollama chat endpoint. Returns the model's response text."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1},  # low temp for deterministic tool calls
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        resp.raise_for_status()
        text = resp.json()["message"]["content"].strip()
        if verbose:
            print(f"\n[model raw]\n{text}\n[/model raw]", flush=True)
        return text
    except requests.exceptions.ConnectionError:
        return "ERROR: Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "ERROR: Ollama timed out. The model may be loading - try again."
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


# ------------------------------------------------------------------
# Single question/answer cycle (ReAct loop)
# ------------------------------------------------------------------

def _answer(
    user_input: str,
    history: list[dict],
    oracle: DBOracle,
    assessor: Assessor,
    verbose: bool = False,
) -> tuple[str, list[dict]]:
    """
    Run the ReAct loop for one user question.
    Returns (final_answer, updated_history).
    History is extended in place with all turns (user, tool calls, observations,
    final assistant response) so follow-up questions have full context.
    """
    # Working copy of messages for this question's tool chain
    messages = build_messages(history, user_input)
    tool_turns = 0

    while tool_turns < MAX_TOOL_TURNS:
        response = _call_ollama(messages, verbose=verbose)

        if response.startswith("ERROR:"):
            return response, history

        tool_name, args = parse_tool_call(response)

        if tool_name is None:
            # Model is giving a final answer - no tool call in response
            history.append({"role": "user",    "content": user_input})
            history.append({"role": "assistant","content": response})
            return response, history

        # Model wants to call a tool
        if verbose:
            print(f"  [tool] {tool_name}({json.dumps(args)})", flush=True)

        tool_result = dispatch(tool_name, args, oracle, assessor)

        if verbose:
            print(f"  [result] {tool_result[:200]}", flush=True)

        # Feed result back as the next message and loop
        observation = format_observation(tool_name, tool_result)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user",      "content": observation})
        tool_turns += 1

    # Hit the tool limit - ask for a final answer with what we have
    messages.append({
        "role": "user",
        "content": "You have used enough tools. Please give your final answer now based on what you have found.",
    })
    response = _call_ollama(messages, verbose=verbose)

    history.append({"role": "user",    "content": user_input})
    history.append({"role": "assistant","content": response})
    return response, history


# ------------------------------------------------------------------
# Main loop
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
    print(f"\nType your question. 'tools' to list tools. 'clear' to reset. 'quit' to exit.\n")

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

        if user_input.lower() == "tools":
            print("\nAvailable tools:")
            for name in TOOLS:
                print(f"  {name}")
            print()
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
    parser.add_argument(
        "db_path",
        help="Path to corpus DB (e.g. world_corpus.db)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show raw model output and tool calls",
    )
    args = parser.parse_args()
    run(args.db_path, verbose=args.verbose)
