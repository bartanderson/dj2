"""
Unit tests for the trade FSM (config/fsms/trade.json).

Walks every declared transition through the GenericFSM runner and checks
the emitted events.
"""
from pathlib import Path
from unittest.mock import Mock

from world.event_log import EventLog
from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins


FSM_PATH = str(Path(__file__).resolve().parents[2] / "config" / "fsms" / "trade.json")


class StubMerchant:
    id = "grom"
    name = "Grom"


class StubEngine:
    def __init__(self):
        self.event_log = EventLog()
        self._execute_purchase = Mock()


def _build_fsm(engine, current_price=13):
    guard_reg = {
        'price_too_low':   builtins.price_lt,
        'price_acceptable': builtins.price_ge,
    }
    action_reg = {
        'update_price': builtins.update_price,
        'execute_buy':  builtins.execute_buy,
    }
    context = {
        'item_name': 'Healing Potion',
        'current_price': current_price,
        'price': current_price,
        'character': None,
        'merchant': StubMerchant(),
        'item': None,
        'engine': engine,
        'session_id': 'test_session',
        '_guard_registry': guard_reg,
        '_action_registry': action_reg,
    }
    return GenericFSM(FSM_PATH, context)


def _send_quiet(fsm, event, **kwargs):
    try:
        fsm.send_event(event, kwargs or None)
    except Exception:
        pass


def _types(engine):
    return [e.type for e in engine.event_log.get_all_events()]


def test_offer_below_price_transitions_to_countering():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 10})
    assert fsm.state == 'countering'
    assert fsm.context['price'] == 10


def test_offer_below_price_does_not_emit_completed():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 10})
    assert 'interaction.trade.completed' not in _types(engine)


def test_offer_at_price_completes():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 13})
    assert fsm.state == 'completed'


def test_offer_above_price_completes():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 20})
    assert fsm.state == 'completed'


def test_offer_at_price_emits_completed():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 13})
    assert 'interaction.trade.completed' in _types(engine)
    ev = engine.event_log.get_events('interaction.trade.completed')[0]
    assert ev.data['session_id'] == 'test_session'
    assert ev.data['merchant_id'] == 'grom'


def test_offer_at_price_calls_engine_execute_purchase():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('offer', {'value': 13})
    assert engine._execute_purchase.called


def test_confirm_from_awaiting_completes_and_emits():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'interaction.trade.completed' in _types(engine)


def test_cancel_completes_without_emit():
    engine = StubEngine()
    fsm = _build_fsm(engine, current_price=13)
    fsm.send_event('cancel')
    assert fsm.state == 'completed'
    assert 'interaction.trade.completed' not in _types(engine)