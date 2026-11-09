# test_ability_roundtrip.py
# Smoke tests for the dj2 6-ability redesign.
# Run from repo root:  python test_ability_roundtrip.py
# Exit codes: 0 = all passed, 1 = any failed.

import sys
import traceback

PASS = "PASS"
FAIL = "FAIL"

_results = []  # (name, status, detail)


def check(name, fn):
    """Run fn(); record PASS/FAIL."""
    try:
        fn()
        status, detail = PASS, ""
    except Exception:
        status, detail = FAIL, traceback.format_exc()

    if status == PASS:
        print(f"[{PASS}] {name}")
    else:
        print(f"[{FAIL}] {name}")
        print(detail)

    _results.append((name, status, detail))


# ---------------------------------------------------------------------------
# Character tests
# ---------------------------------------------------------------------------

def _make_char():
    from world.character import Character
    return Character(
        name="t", race="Human", classs="Warrior",
        abilities={"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
    )


def test_character_roundtrip():
    from world.character import Character
    c = _make_char()
    d = c.to_dict()
    c2 = Character.from_dict(d)
    assert c2.abilities == c.abilities, (
        f"roundtrip mismatch: {c2.abilities!r} != {c.abilities!r}"
    )


def test_character_has_six_abilities():
    from world.dm_chat_handler import ABILITY_KEYS
    c = _make_char()
    assert set(c.abilities.keys()) == set(ABILITY_KEYS), (
        f"expected keys {ABILITY_KEYS}, got {sorted(c.abilities.keys())}"
    )


# ---------------------------------------------------------------------------
# dm_chat_handler tests
# ---------------------------------------------------------------------------

def _stub_handler():
    from world.dm_chat_handler import DMChatHandler

    class _Stub:
        pass

    return DMChatHandler(_Stub())


def test_handler_imports():
    # Importing the module is itself the check: catches missing constants, bad refs.
    import world.dm_chat_handler  # noqa: F401


def test_handler_constants():
    from world.dm_chat_handler import (
        ABILITY_KEYS, ABILITY_ALIASES, ABILITY_MIN, ABILITY_MAX,
    )
    assert ABILITY_KEYS == ("STR", "DEX", "CON", "INT", "WIS", "CHA"), ABILITY_KEYS
    for k in ("str", "dex", "con", "int", "wis", "cha"):
        assert k in ABILITY_ALIASES, f"missing lowercase alias {k!r}"
    for k in ("brawn", "finesse", "wits", "will"):
        assert k in ABILITY_ALIASES, f"missing legacy alias {k!r}"
    assert ABILITY_MIN < ABILITY_MAX, (ABILITY_MIN, ABILITY_MAX)


def test_update_applies_and_aliases():
    h = _stub_handler()
    c = _make_char()
    ok, errs = h._update_character_from_ai(c, {"STR": 15, "wisdom": 12})
    assert ok, f"update failed: {errs}"
    assert c.abilities["STR"] == 15, c.abilities
    assert c.abilities["WIS"] == 12, c.abilities  # "wisdom" -> "WIS" alias path
    assert c.max_hp >= 1, c.max_hp
    assert c.max_sp >= 0, c.max_sp


def test_update_rejects_out_of_range():
    h = _stub_handler()
    c = _make_char()
    ok, errs = h._update_character_from_ai(c, {"STR": 99})
    assert not ok, "expected rejection for out-of-range STR"
    assert any("STR" in e for e in errs), errs


def test_update_rejects_non_numeric():
    h = _stub_handler()
    c = _make_char()
    ok, errs = h._update_character_from_ai(c, {"DEX": "high"})
    assert not ok, "expected rejection for non-numeric DEX"
    assert any("DEX" in e for e in errs), errs


def test_rules_question_topic_match():
    from world import dnd_data
    h = _stub_handler()
    target = dnd_data.get_class_list()[0]
    assert h._is_rules_question(f"tell me about {target}") is True, (
        f"'{target}' should match a rules topic"
    )


def test_rules_question_spellbook():
    h = _stub_handler()
    # "spell" must not substring-match inside "spellbook"
    assert h._is_rules_question("tell me about my spellbook") is False, (
        "spellbook must not trigger the 'spell' substring match"
    )


def test_rules_question_non_question():
    from world import dnd_data
    h = _stub_handler()
    target = dnd_data.get_class_list()[0]
    assert h._is_rules_question(f"I attack the {target}") is False, (
        "non-question statements must be rejected before topic matching"
    )


# ---------------------------------------------------------------------------
# narrative_system tests
# ---------------------------------------------------------------------------

def test_narrative_imports():
    import world.narrative_system  # noqa: F401


def test_narrative_parse_aliases():
    from world.narrative_system import NarrativeSystem
    parsed = NarrativeSystem._parse_ability_assignments(
        "STR 15, dex 14, Con 13, int 12, wis 10, cha 8"
    )
    assert parsed == {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8}, parsed


def test_narrative_parse_full_names():
    from world.narrative_system import NarrativeSystem
    parsed = NarrativeSystem._parse_ability_assignments(
        "Strength 15, Dexterity 14, Constitution 13, Intelligence 12, Wisdom 10, Charisma 8"
    )
    assert parsed == {"STR": 15, "DEX": 14, "CON": 13, "INT": 12, "WIS": 10, "CHA": 8}, parsed

def test_full_creation_flow():
    from world.narrative_system import NarrativeSystem
    from world import dnd_data

    captured = []

    class StubCharacterManager:
        def add_character(self, character):
            captured.append(character)

    class StubWorldState:
        narrative_framework = {}
        character_manager = StubCharacterManager()

    ns = NarrativeSystem(StubWorldState(), ai_system=None)
    state = None

    def turn(msg):
        nonlocal state
        result = ns.guide_character_creation("player-1", msg, state)
        state = result["new_state"]
        return result

    turn("Bob")
    assert state is not None and state['phase'] == 'attribute_method', (
        f"expected attribute_method, got {state['phase'] if state else None}"
    )

    turn("standard")
    assert state['phase'] == 'attribute_assignment', f"got {state['phase']}"

    turn("STR 15, DEX 14, CON 13, INT 12, WIS 10, CHA 8")
    assert state['phase'] == 'race_selection', f"got {state['phase']}"

    turn(dnd_data.get_race_list()[0])

    if state is not None and state['phase'] == 'racial_choice':
        spec = state['pending_race'].choice_spec()
        count = spec.get('count', 1)
        turn(", ".join(spec['from'][:count]))

    assert state['phase'] == 'class_selection', f"got {state['phase']}"
    turn(dnd_data.get_class_list()[0])
    assert state['phase'] == 'background_selection', f"got {state['phase']}"

    turn("Sage")
    assert state['phase'] == 'skill_selection', f"got {state['phase']}"

    skills = [s.name for s in dnd_data.Skill.all()][:3]
    turn(", ".join(skills))
    assert state['phase'] == 'personality_development', f"got {state['phase']}"

    turn("brave")
    turn("justice")
    turn("family")
    turn("pride")
    assert state['phase'] == 'name_input', f"got {state['phase']}"

    turn("Bob")
    assert state is None, "state should be None after finalization"
    assert len(captured) == 1, f"expected 1 character, got {len(captured)}"

    char = captured[0]
    assert char.name == "Bob", char.name
    assert set(char.abilities.keys()) == {"STR", "DEX", "CON", "INT", "WIS", "CHA"}
    print(f"  created: {char.name} | {char.race} | {char.classs.name if char.classs else '?'}")

# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main():
    print("dj2 ability redesign - smoke tests")
    print("-" * 44)

    check("character abilities roundtrip (to_dict/from_dict)", test_character_roundtrip)
    check("character has the 6 new abilities", test_character_has_six_abilities)
    check("world.dm_chat_handler imports cleanly", test_handler_imports)
    check("module constants (KEYS/ALIASES/MIN/MAX)", test_handler_constants)
    check("_update_character_from_ai applies STR + 'wisdom' alias", test_update_applies_and_aliases)
    check("_update_character_from_ai rejects out-of-range", test_update_rejects_out_of_range)
    check("_update_character_from_ai rejects non-numeric", test_update_rejects_non_numeric)

    print("-" * 44)
    check("_is_rules_question: topic match", test_rules_question_topic_match)
    check("_is_rules_question: spellbook not false-positive", test_rules_question_spellbook)
    check("_is_rules_question: non-question rejected", test_rules_question_non_question)

    print("-" * 44)
    check("narrative_system imports", test_narrative_imports)
    check("narrative_system.parse handles aliases", test_narrative_parse_aliases)
    check("narrative_system.parse handles full names", test_narrative_parse_full_names)
    check("full character creation flow end-to-end", test_full_creation_flow)

    fails = [r for r in _results if r[1] == FAIL]
    total = len(_results)
    print("-" * 44)
    print(f"{total - len(fails)}/{total} passed")
    if fails:
        print("FAILURES:")
        for name, _, _ in fails:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())