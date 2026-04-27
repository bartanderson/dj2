from world.fsm.encounter_machine import EncounterMachine
import sys
sys.path.append('.')

class MockWorld:
    def check_flee(self, encounter):
        return True
    def check_parley(self, encounter):
        return False

def test_encounter_flow():
    print("=== Testing Encounter FSM ===")
    encounter_data = {"description": "A goblin blocks your path!"}
    mock_world = MockWorld()
    fsm = EncounterMachine(encounter_data, mock_world)

    # current_state.id gives the state name string (e.g., "awaiting_choice")
    print(f"Initial state: {fsm.current_state.id}")
    assert fsm.current_state.id == "awaiting_choice"
    print("OK: FSM is in awaiting_choice state.")

    # Player chooses to flee
    fsm.choose_flee()
    print(f"After flee: {fsm.current_state.id}")
    assert fsm.current_state.id == "completed"
    print("OK: Flee succeeded, FSM completed.")

    # Reset for next test
    fsm = EncounterMachine(encounter_data, mock_world)
    # Player tries parley
    fsm.choose_parley()
    print(f"After parley then fight: {fsm.current_state.id}")
    assert fsm.current_state.id == "completed"
    print("OK: Parley failed, fight resolved, completed.")

    # Reset for fight direct
    fsm = EncounterMachine(encounter_data, mock_world)
    fsm.choose_fight()
    print(f"After fight: {fsm.current_state.id}")
    assert fsm.current_state.id == "completed"
    print("OK: Fight resolved directly, completed.")

if __name__ == "__main__":
    test_encounter_flow()