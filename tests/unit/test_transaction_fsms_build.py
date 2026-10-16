"""
Unit tests that buy, sell, and barter FSMs build successfully with
the AdjudicationEngine's registries (no InvalidDefinition errors).
"""
from pathlib import Path
from unittest.mock import Mock, MagicMock

from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins

FSM_DIR = Path(__file__).resolve().parents[2] / "config" / "fsms"


def _make_context(engine, extra=None):
    """Return a minimal context dict for a transaction FSM."""
    ctx = {
        'engine': engine,
        'character': Mock(name='char'),
        'merchant': Mock(id='merchant_1', name='Merchant'),
        'session_id': 'test_session',
        'item': Mock(name='potion'),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _build_from_config(json_path, guard_registry, action_registry):
    """Build a GenericFSM using the given registries and a minimal context."""
    ctx = _make_context(Mock())
    ctx['_guard_registry'] = guard_registry
    ctx['_action_registry'] = action_registry
    return GenericFSM(str(json_path), ctx)


def test_buy_fsm_builds():
    """Buy FSM must build with store_offer + execute_purchase."""
    engine = Mock()
    guard_reg = {
        'price_too_low': builtins.price_lt,
        'price_acceptable': builtins.price_ge,
    }
    action_reg = {
        'store_offer': builtins.store_offer,
        'execute_purchase': builtins.execute_buy,
    }
    fsm = _build_from_config(FSM_DIR / "buy.json", guard_reg, action_reg)
    assert fsm.state == 'awaiting'
    # Verify get_prompt returns a non-empty string
    prompt = fsm.get_prompt()
    assert isinstance(prompt, str) and len(prompt) > 0


def test_sell_fsm_builds():
    """Sell FSM must build with store_offer + execute_sell."""
    guard_reg = {
        'offer_too_high': builtins.offer_gt,
        'offer_acceptable': builtins.offer_le,
    }
    action_reg = {
        'store_offer': builtins.store_offer,
        'execute_sell': builtins.execute_sell,
    }
    fsm = _build_from_config(FSM_DIR / "sell.json", guard_reg, action_reg)
    assert fsm.state == 'awaiting'


def test_barter_fsm_builds():
    """Barter FSM must build with add_gold + execute_barter."""
    guard_reg = {
        'need_more_gold': builtins.need_more_gold,
        'offer_acceptable': builtins.shortage_met,
    }
    action_reg = {
        'add_gold': builtins.add_gold,
        'execute_barter': builtins.execute_barter,
    }
    ctx = _make_context(Mock())
    ctx['give_item'] = 'old sword'
    ctx['receive_item'] = 'new shield'
    ctx['give_value'] = 50
    ctx['receive_value'] = 100
    ctx['shortage'] = 50
    ctx['_guard_registry'] = guard_reg
    ctx['_action_registry'] = action_reg
    fsm = GenericFSM(str(FSM_DIR / "barter.json"), ctx)
    assert fsm.state == 'awaiting'
