import pytest
from world.character import (
    Character, ability_modifier, proficiency_bonus_for_level, ABILITIES,
)
from world import dnd_data


def test_modifier_table():
    assert ability_modifier(3) == -4
    assert ability_modifier(10) == 0
    assert ability_modifier(11) == 0
    assert ability_modifier(12) == 1
    assert ability_modifier(18) == 4


def test_proficiency_by_level():
    assert proficiency_bonus_for_level(1) == 2
    assert proficiency_bonus_for_level(4) == 2
    assert proficiency_bonus_for_level(5) == 3
    assert proficiency_bonus_for_level(20) == 6


def test_race_apply_choices_human():
    race = dnd_data.Race.get("Human")
    bonuses = race.apply_choices(["STR", "CON"])
    assert bonuses == {"STR": 1, "CON": 1}
    with pytest.raises(ValueError):
        race.apply_choices(["STR", "STR"])  # duplicates not counted at different slots
    with pytest.raises(ValueError):
        race.apply_choices(["STR"])  # wrong count


def test_race_apply_choices_dwarf():
    race = dnd_data.Race.get("Dwarf")
    bonuses = race.apply_choices(["STR"])
    assert bonuses == {"CON": 2, "STR": 1}
    with pytest.raises(ValueError):
        race.apply_choices(["DEX"])  # DEX not permitted


def test_race_apply_choices_troll_static():
    race = dnd_data.Race.get("Troll-Blooded")
    bonuses = race.apply_choices([])
    assert bonuses == {"CON": 2, "STR": 1}
    with pytest.raises(ValueError):
        race.apply_choices(["STR"])  # race has no choice


def test_character_construction_and_derived():
    char = Character(
        name="Test", race="Human", classs="Warrior", level=1,
        abilities={"STR": 16, "DEX": 13, "CON": 14, "INT": 10, "WIS": 12, "CHA": 8},
        save_proficiencies=["STR", "CON"],
    )
    assert char.modifier("STR") == 3
    assert char.max_hp == 6 + 2*1 + 2*2   # = 12
    assert char.defense == 10 + 1          # DEX 13 → +1
    assert char.initiative_bonus == 1      # no init proficiency for Warrior


def test_roundtrip():
    original = Character(
        name="A", race="Elf", classs="Rogue", level=3,
        abilities={"STR": 8, "DEX": 17, "CON": 12, "INT": 14, "WIS": 10, "CHA": 12},
        save_proficiencies=["DEX", "INT"],
        skill_proficiencies=["Stealth", "Sleight of Hand"],
    )
    original.add_item({"name": "Dagger", "description": "", "cost": 2})
    original.hp = original.max_hp - 3

    restored = Character.from_dict(original.to_dict())
    assert restored.abilities == original.abilities
    assert restored.hp == original.hp
    assert restored.save_proficiencies == original.save_proficiencies
    assert len(restored.inventory) == 1
    # Derived stats re-derived identically
    assert restored.max_hp == original.max_hp
    assert restored.defense == original.defense


def test_builder_applies_race_and_rejects_bad_choice():
    from world.character_builder import CharacterBuilder
    b = CharacterBuilder(ai_system=None)
    with pytest.raises(ValueError):
        b._create_character_impl("owner", {
            "name": "X", "race": "Dwarf", "class": "Warrior",
            "abilities": {"STR": 15, "DEX": 12, "CON": 13, "INT": 10, "WIS": 14, "CHA": 8},
            "racial_choice": ["DEX"],   # DEX not permitted for Dwarf
        })