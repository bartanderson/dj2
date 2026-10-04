# structural/check_fsms.py
"""
Structural integrity checker for dj2 FSMs.

Run from the project root:
    python -m structural.check_fsms

Or:
    python structural/check_fsms.py

This checks:
- Every JSON spec has a corresponding Python class.
- Every transition that has an 'action' must have a 'cond' (guard) if leaving 'awaiting_choice'.
- The context builder has a _get_<fsm>_context function for each FSM.
- No ghosts (context getters referencing FSMs that don't exist).
"""

import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# --- Configuration ---
# Adjust these if your dj2 structure differs.
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # Assumes dj2/structural/check_fsms.py
SPEC_DIR = PROJECT_ROOT / "config" / "fsms"
IMPL_DIR = PROJECT_ROOT / "world" / "fsm"
CONTEXT_BUILDER_PATH = PROJECT_ROOT / "world" / "context_builder.py"

# --- ANSI Colors for output ---
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def find_fsm_specs() -> Dict[str, Path]:
    """Return a dict mapping FSM name (e.g., 'Encounter') to its JSON file path."""
    specs = {}
    if not SPEC_DIR.exists():
        print(f"{RED}Error: Spec directory not found: {SPEC_DIR}{RESET}")
        return specs

    for json_path in SPEC_DIR.glob("*.json"):
        name = json_path.stem  # 'encounter' -> 'Encounter'
        # Normalize to PascalCase for class matching
        pascal_name = "".join(part.capitalize() for part in name.split("_"))
        specs[pascal_name] = json_path
    return specs


def find_fsm_implementations() -> Dict[str, Set[str]]:
    """
    Return a dict mapping FSM class names (e.g., 'EncounterFSM') 
    to the set of methods defined in that class.
    """
    implementations = {}
    if not IMPL_DIR.exists():
        print(f"{RED}Error: Implementation directory not found: {IMPL_DIR}{RESET}")
        return implementations

    for py_file in IMPL_DIR.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except SyntaxError as e:
            print(f"{YELLOW}Warning: Could not parse {py_file.name} (syntax error): {e}{RESET}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                implementations[node.name] = set()
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        implementations[node.name].add(item.name)
    return implementations


def find_context_getters() -> Dict[str, str]:
    """
    Parse context_builder.py for functions named _get_<Something>_context.
    Returns a dict mapping FSM name (e.g., 'Encounter') to the function name.
    """
    getters = {}
    if not CONTEXT_BUILDER_PATH.exists():
        print(f"{RED}Error: Context builder not found: {CONTEXT_BUILDER_PATH}{RESET}")
        return getters

    try:
        with open(CONTEXT_BUILDER_PATH, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except SyntaxError as e:
        print(f"{RED}Error parsing context_builder.py: {e}{RESET}")
        return getters

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            name = node.name
            if name.startswith("_get_") and name.endswith("_context"):
                # Extract "Encounter" from "_get_Encounter_context"
                fsm_name = name[5:-8]  # len('_get_') = 5, len('_context') = 8
                getters[fsm_name] = name
    return getters


def load_spec_data(json_path: Path) -> Tuple[Dict, List[str]]:
    """
    Loads the JSON spec and returns (full_spec, list_of_issues).
    Issues are structural problems found in the spec itself.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except json.JSONDecodeError as e:
        return {}, [f"Invalid JSON: {e}"]
    except Exception as e:
        return {}, [f"Error reading file: {e}"]

    issues = []
    events = spec.get("events", {})
    for event_name, event_def in events.items():
        transitions = event_def.get("transitions", [])
        for trans in transitions:
            from_state = trans.get("from", "")
            to_state = trans.get("to", "")
            actions = trans.get("actions", [])
            cond = trans.get("cond")

            # RULE: If a transition leaves the 'awaiting_choice' state AND has an action,
            # it MUST have a guard (cond), unless the action is explicitly unconditional.
            # We specifically target 'awaiting_choice' because it's the decision hub.
            if from_state == "awaiting_choice" and actions:
                if not cond:
                    issues.append(
                        f"Transition '{event_name}' from '{from_state}' to '{to_state}' "
                        f"has action(s) {actions} but NO guard (cond)."
                    )
    return spec, issues


def run_checks():
    print(f"{BLUE}dj2 Structural FSM Checker{RESET}")
    print("=" * 50)

    # 1. Load specs
    specs = find_fsm_specs()
    if not specs:
        print(f"{RED}No FSM specs found in {SPEC_DIR}{RESET}")
        return 1

    # 2. Load implementations
    impls = find_fsm_implementations()

    # 3. Load context getters
    getters = find_context_getters()

    # 4. Perform cross-checks
    all_ok = True
    fsm_names = list(specs.keys())

    # Keep track of referenced FSMs to detect ghosts
    referenced_fsms = set(getters.keys())
    referenced_fsms.update(fsm_names)

    for fsm_name, spec_path in specs.items():
        spec, spec_issues = load_spec_data(spec_path)
        if spec_issues:
            print(f"\n{RED}❌ {fsm_name}: Spec issues{RESET}")
            for issue in spec_issues:
                print(f"   {RED}• {issue}{RESET}")
            all_ok = False
            continue

        # Check implementation
        impl_class_name = f"{fsm_name}FSM"
        if impl_class_name not in impls:
            print(f"\n{RED}❌ {fsm_name}: Class {impl_class_name} not found in {IMPL_DIR}{RESET}")
            all_ok = False
            continue

        # Check methods (optional: warn if methods are stubs, but we leave that to Determined)
        # For now, just check if the class exists.
        print(f"\n{GREEN}✅ {fsm_name}: Class {impl_class_name} found.{RESET}")

        # Check context getter
        if fsm_name in getters:
            print(f"   {GREEN}✅ Context getter: {getters[fsm_name]} found.{RESET}")
        else:
            print(f"   {YELLOW}⚠️  Missing context getter: _get_{fsm_name}_context in context_builder.py{RESET}")
            all_ok = False

        # Check symmetry (action-guard)
        if "events" in spec:
            awaiting_events = []
            for evt_name, evt_def in spec["events"].items():
                for trans in evt_def.get("transitions", []):
                    if trans.get("from") == "awaiting_choice" and trans.get("actions"):
                        if not trans.get("cond"):
                            awaiting_events.append(evt_name)
            if awaiting_events:
                print(f"   {YELLOW}⚠️  Transitions without guards: {', '.join(awaiting_events)}{RESET}")
                all_ok = False

    # 5. Ghost detection: FSMs referenced in context builder but missing spec or impl
    print(f"\n{BLUE}Ghost Detection (Context getters without specs):{RESET}")
    ghost_found = False
    # Build case-insensitive map of spec names
    specs_lower = {k.lower(): k for k in specs.keys()}
    for fsm_name in getters:
        if fsm_name.lower() not in specs_lower:
            print(f"   {RED}🚫 GHOST: _get_{fsm_name}_context references '{fsm_name}' "
                  f"but no spec exists at {SPEC_DIR / fsm_name.lower()}.json{RESET}")
            ghost_found = True
            all_ok = False
    if not ghost_found:
        print(f"   {GREEN}No ghosts found.{RESET}")

    # 6. Summary
    print("\n" + "=" * 50)
    if all_ok:
        print(f"{GREEN}✅ All structural checks passed!{RESET}")
    else:
        print(f"{RED}❌ Some structural issues found. See above for details.{RESET}")
        print(f"{YELLOW}💡 Tip: Fix missing context getters, add guards to transitions, or scaffold missing classes.{RESET}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run_checks())