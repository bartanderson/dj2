"""
Test that buy, sell, and barter FSMs build with the registries defined
in world/adjudication_engine.py.

Because importing AdjudicationEngine pulls in psycopg2 (Postgres driver),
this test parses the source file with the ast module to extract the
guard_registry and action_registry dicts from each TransactionConfig.
"""
import ast
from pathlib import Path

from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins

DJ2_ROOT = Path(__file__).resolve().parents[2]
ENGINE_SRC = DJ2_ROOT / "world" / "adjudication_engine.py"
FSM_DIR = DJ2_ROOT / "config" / "fsms"


def _extract_registries(source: str) -> dict:
    """Parse adjudication_engine.py and return {name: (guard_reg, action_reg)}."""
    tree = ast.parse(source)
    registries = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match TransactionConfig(name='buy', guard_registry={...}, action_registry={...})
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == "TransactionConfig"):
            continue
        name = None
        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                name = kw.value.value
        if name not in ("buy", "sell", "barter"):
            continue
        guard_reg = _ast_dict_to_python(node, "guard_registry")
        action_reg = _ast_dict_to_python(node, "action_registry")
        if guard_reg is not None and action_reg is not None:
            registries[name] = (guard_reg, action_reg)
    return registries


def _ast_dict_to_python(call_node: ast.Call, kwarg_name: str) -> dict:
    """Extract a dict literal from a keyword argument on a Call node."""
    for kw in call_node.keywords:
        if kw.arg == kwarg_name and isinstance(kw.value, ast.Dict):
            return _ast_dict_to_py(kw.value)
    return None


def _ast_dict_to_py(d: ast.Dict) -> dict:
    """Convert an ast.Dict node to a plain dict with string keys and function references."""
    result = {}
    for key_node, value_node in zip(d.keys, d.values):
        if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
            return None  # only support string-keyed dicts
        key = key_node.value
        # Map builtin function names to actual functions
        val = _resolve_builtin_ref(value_node)
        result[key] = val
    return result


def _resolve_builtin_ref(node: ast.expr):
    """Resolve a.b to builtins.b."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        if node.value.id == "builtins":
            fn_name = node.attr
            if hasattr(builtins, fn_name):
                return getattr(builtins, fn_name)
    # Handle dotted chain like builtins.some_func
    return None


# ---------------------------------------------------------------------------
# Build registries from source
# ---------------------------------------------------------------------------
_REGISTRIES = _extract_registries(ENGINE_SRC.read_text())


def _make_context(engine, extra=None):
    ctx = {
        "engine": engine,
        "character": type("Char", (), {"name": "char"})(),
        "merchant": type("Merchant", (), {"id": "m1", "name": "Merchant"})(),
        "session_id": "test",
        "item": type("Item", (), {"name": "potion"})(),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _build_from_registries(json_path, guard_reg, action_reg):
    ctx = _make_context(None)
    ctx["_guard_registry"] = guard_reg
    ctx["_action_registry"] = action_reg
    return GenericFSM(str(json_path), ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_buy_fsm_builds():
    """Buy FSM builds with the registries from AdjudicationEngine.buy_config."""
    assert "buy" in _REGISTRIES, "buy_config not found in source"
    guard_reg, action_reg = _REGISTRIES["buy"]
    fsm = _build_from_registries(FSM_DIR / "buy.json", guard_reg, action_reg)
    assert fsm.state == "awaiting"
    prompt = fsm.get_prompt()
    assert isinstance(prompt, str) and len(prompt) > 0


def test_sell_fsm_builds():
    """Sell FSM builds with the registries from AdjudicationEngine.sell_config."""
    assert "sell" in _REGISTRIES, "sell_config not found in source"
    guard_reg, action_reg = _REGISTRIES["sell"]
    fsm = _build_from_registries(FSM_DIR / "sell.json", guard_reg, action_reg)
    assert fsm.state == "awaiting"


def test_barter_fsm_builds():
    """Barter FSM builds with the registries from AdjudicationEngine.barter_config."""
    assert "barter" in _REGISTRIES, "barter_config not found in source"
    guard_reg, action_reg = _REGISTRIES["barter"]
    ctx = _make_context(None)
    ctx["give_item"] = "old sword"
    ctx["receive_item"] = "new shield"
    ctx["give_value"] = 50
    ctx["receive_value"] = 100
    ctx["shortage"] = 50
    ctx["_guard_registry"] = guard_reg
    ctx["_action_registry"] = action_reg
    fsm = GenericFSM(str(FSM_DIR / "barter.json"), ctx)
    assert fsm.state == "awaiting"
