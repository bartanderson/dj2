"""
Unit tests for the encounter FSM (config/fsms/encounter.json).

Walks every declared transition through the GenericFSM runner, including
both guard paths, and asserts the events emitted through the EventLog.
"""
from pathlib import Path

from world.event_log import EventLog
from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins


FSM_PATH = str(Path(__file__).resolve().parents[2] / "config" / "fsms" / "encounter.json")


class StubEngine:
    """Minimal engine stand-in: EventLog + guard hooks the FSM calls."""

    def __init__(self, flee=True, parley=True, fight=True):
        self.event_log = EventLog()
        self._flee = flee
        self._parley = parley
        self._fight = fight

    def _check_flee(self, encounter_data):
        return self._flee

    def _check_parley(self, encounter_data):
        return self._parley

    def _check_fight(self, encounter_data):
        return self._fight


def _build_fsm(engine, description="A goblin attacks!"):
    guard_reg = {
        'fight_possible':  builtins.fight_possible,
        'flee_possible':   builtins.flee_possible,
        'parley_possible': builtins.parley_possible,
    }
    action_reg = {
        'begin_encounter': builtins.begin_encounter,
        'start_combat':    builtins.start_combat,
        'resolve_flee':    builtins.resolve_flee,
        'resolve_parley':  builtins.resolve_parley,
    }
    context = {
        'description': description,
        'encounter_data': {'description': description},
        'encounter_id': 'enc::test',
        'engine': engine,
        'session_id': 'test_session',
        'character': None,
        '_guard_registry': guard_reg,
        '_action_registry': action_reg,
    }
    return GenericFSM(FSM_PATH, context)


def _types(engine):
    return [e.type for e in engine.event_log.get_all_events()]


def _send_quiet(fsm, event):
    """send_event that swallows guard-block exceptions, whatever the library raises."""
    try:
        fsm.send_event(event)
    except Exception:
        pass


def test_begin_encounter_emits_started():
    engine = StubEngine()
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    assert fsm.state == 'awaiting_choice'
    assert 'encounter.started' in _types(engine)
    started = engine.event_log.get_events('encounter.started')[0]
    assert started.data['session_id'] == 'test_session'
    assert started.data['encounter_id'] == 'enc::test'
    assert 'description' in started.data


def test_flee_success_emits_updated_then_ended():
    engine = StubEngine(flee=True)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    fsm.send_event('flee')
    assert fsm.state == 'completed'
    types = _types(engine)
    assert 'encounter.updated' in types
    assert 'encounter.ended' in types
    assert types.index('encounter.updated') < types.index('encounter.ended')
    ended = engine.event_log.get_events('encounter.ended')[0]
    assert ended.data['outcome'] == 'fled'


def test_flee_blocked_by_guard():
    engine = StubEngine(flee=False)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    _send_quiet(fsm, 'flee')
    assert fsm.state == 'awaiting_choice'
    assert 'encounter.ended' not in _types(engine)


def test_parley_success_emits_updated_then_ended():
    engine = StubEngine(parley=True)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    fsm.send_event('parley')
    assert fsm.state == 'completed'
    ended = engine.event_log.get_events('encounter.ended')[0]
    assert ended.data['outcome'] == 'parleyed'


def test_parley_blocked_by_guard():
    engine = StubEngine(parley=False)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    _send_quiet(fsm, 'parley')
    assert fsm.state == 'awaiting_choice'
    assert 'encounter.ended' not in _types(engine)


def test_fight_emits_combat_initiation():
    engine = StubEngine(fight=True)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    fsm.send_event('fight')
    assert fsm.state == 'resolving_fight'
    types = _types(engine)
    assert 'combat.initiation.triggered' in types
    assert 'encounter.ended' not in types


def test_fight_blocked_by_guard():
    engine = StubEngine(fight=False)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    _send_quiet(fsm, 'fight')
    assert fsm.state == 'awaiting_choice'
    assert 'combat.initiation.triggered' not in _types(engine)


def test_combat_ended_closes_encounter():
    engine = StubEngine(fight=True)
    fsm = _build_fsm(engine)
    fsm.send_event('next')
    fsm.send_event('fight')
    fsm.send_event('combat_ended')
    assert fsm.state == 'completed'
