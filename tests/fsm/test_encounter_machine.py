import pytest
from world.fsm.encounter_machine import EncounterMachine

@pytest.fixture
def encounter_data():
    return {"description": "Goblin attack!", "flee_dc": 15, "parley_dc": 12}

def test_initial_state(mock_world, encounter_data):
    fsm = EncounterMachine(encounter_data, mock_world)
    assert fsm.current_state.id == "awaiting_choice"
    # (Add a get_prompt method to EncounterMachine for proper testing)
    # For now, just check state
    assert fsm.awaiting_choice.is_active

def test_flee_success(mock_world, encounter_data):
    mock_world.flee_success = True
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.flee()
    assert fsm.current_state.id == "completed"
    # Optionally check mock_world.last_encounter

def test_flee_failure(mock_world, encounter_data):
    mock_world.flee_success = False
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.flee()
    # Expect remaining in awaiting_choice (since flee_failure transitions back)
    assert fsm.current_state.id == "awaiting_choice"

def test_parley_success(mock_world, encounter_data):
    mock_world.parley_success = True
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.parley()
    assert fsm.current_state.id == "awaiting_choice"   # parley_success goes back to choices

def test_parley_failure_leads_to_fight(mock_world, encounter_data):
    mock_world.parley_success = False
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.parley()
    # parley_failure leads to resolving_fight, which automatically resolves to completed
    assert fsm.current_state.id == "completed"

def test_fight(mock_world, encounter_data):
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.fight()
    assert fsm.current_state.id == "completed"