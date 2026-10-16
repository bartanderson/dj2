"""
Unit tests for the barter FSM (config/fsms/barter.json).

Walks every declared transition through the GenericFSM runner and checks
the events emitted through the EventLog.
"""
from pathlib import Path
from unittest.mock import Mock

from world.event_log import EventLog
from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins


FSM_PATH = str(Path(__file__).resolve().parents[2] / "config" / "fsms" / "barter.json")


class StubEngine:
    """Minimal engine stand-in. _execute_barter is a mock; event_log is real."""

    def __init__(self):
        self.event_log = EventLog()
        self._execute_barter = Mock()


def _build_fsm(engine, shortage=3, give_value=10, receive_value=13):
    guard_reg = {
        'need_more_gold': builtins.need_more_gold,
    }
    action_reg = {
        'add_gold': builtins.add_gold,
        'execute_barter': builtins.execute_barter,
    }
    context = {
        'give_item': 'shortsword',
        'receive_item': 'healing potion',
        'give_value': give_value,
        'receive_value': receive_value,
        'shortage': shortage,
        'character': None,
        'merchant': None,
        'give_item_obj': None,
        'receive_item_obj': None,
        'engine': engine,
        'session_id': 'test_session',
        '_guard_registry': guard_reg,
        '_action_registry': action_reg,
    }
    return GenericFSM(FSM_PATH, context)


def _send_quiet(fsm, event, **kwargs):
    """send_event that swallows guard-block exceptions."""
    try:
        fsm.send_event(event, kwargs or None)
    except Exception:
        pass


def _types(engine):
    return [e.type for e in engine.event_log.get_all_events()]


def test_offer_below_shortage_transitions_to_countering():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('offer', {'value': 2})
    assert fsm.state == 'countering'


def test_offer_below_shortage_emits_resource_changed():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('offer', {'value': 2})
    assert 'state.resource.changed' in _types(engine)
    ev = engine.event_log.get_events('state.resource.changed')[0]
    assert ev.data['session_id'] == 'test_session'
    assert ev.data['resource'] == 'gold'
    assert ev.data['delta'] == 2


def test_offer_below_shortage_decrements_shortage():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('offer', {'value': 2})
    assert fsm.context['shortage'] == 1
    assert fsm.context['offered_extra'] == 2


def test_offer_at_or_above_shortage_does_not_transition():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    _send_quiet(fsm, 'offer', value=3)
    assert fsm.state == 'awaiting'
    assert 'state.resource.changed' not in _types(engine)


def test_confirm_emits_trade_completed():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'interaction.trade.completed' in _types(engine)


def test_confirm_calls_engine_execute_barter():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('confirm')
    assert engine._execute_barter.called


def test_full_barter_flow():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('offer', {'value': 2})
    assert fsm.state == 'countering'
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    types = _types(engine)
    assert 'state.resource.changed' in types
    assert 'interaction.trade.completed' in types


def test_cancel_completes_without_trade_events():
    engine = StubEngine()
    fsm = _build_fsm(engine, shortage=3)
    fsm.send_event('cancel')
    assert fsm.state == 'completed'
    assert 'interaction.trade.completed' not in _types(engine)