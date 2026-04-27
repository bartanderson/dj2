import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from world.fsm.trade_machine import TradeMachine

class MockEngine:
    def _execute_purchase(self, character, merchant, item, price):
        print(f"✓ Executing purchase of {item.name} for {price} gp")
        return True

def test_trade_flow():
    print("=== Trade FSM Test ===")
    # Mock objects
    class Character:
        currency = 100
    class Merchant:
        pass
    class Item:
        name = "Healing Potion"
    char = Character()
    merchant = Merchant()
    item = Item()
    engine = MockEngine()

    # 1. Create FSM
    fsm = TradeMachine(13, char, merchant, item, engine)
    assert fsm.current_state.id == "awaiting"
    print(f"Initial state: {fsm.current_state.id} – Prompt: {fsm.get_prompt()}")

    # 2. Offer too low
    fsm.offer(10)
    assert fsm.current_state.id == "countering"
    print(f"After offer 10: {fsm.current_state.id} – Prompt: {fsm.get_prompt()}")

    # 3. Offer acceptable
    fsm.offer(13)
    assert fsm.current_state.id == "completed"
    print(f"After offer 13: {fsm.current_state.id} – Prompt: {fsm.get_prompt()}")

    print("✓ All transitions correct")

def test_confirm_flow():
    print("\n=== Trade FSM Confirm Test ===")
    char = Character()
    merchant = Merchant()
    item = Item()
    engine = MockEngine()
    fsm = TradeMachine(13, char, merchant, item, engine)
    # Confirm without offering? Should complete? Actually confirm is only valid after offer? In our design, confirm from awaiting would complete at current price
    # But our transitions: confirm from awaiting to completed. So it should work.
    fsm.confirm()
    assert fsm.current_state.id == "completed"
    print(f"After confirm: {fsm.current_state.id} – Prompt: {fsm.get_prompt()}")

if __name__ == "__main__":
    test_trade_flow()
    test_confirm_flow()