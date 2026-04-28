import pytest
from unittest.mock import Mock
from world.adjudication_engine import AdjudicationEngine
from world.intent import IntentFrame

# ----------------------------------------------------------------------
# Mock WorldController with proper string attributes
# ----------------------------------------------------------------------
class MockWorldController:
    def __init__(self):
        self.campaign_state = Mock()
        self.current_location = Mock()
        self.current_location.merchant_id = "grom"
        self.current_location.name = "Adventurer's Respite"
        self.campaign_state.get_merchant = Mock(return_value=self._create_mock_merchant())
        self.campaign_state.get_merchant_relationship = Mock(return_value=Mock(affinity=0, trust=0, fear=0))
        self.campaign_state.update_merchant_relationship = Mock()
        self.character_manager = Mock()
        self.character_manager._save_character_to_db = Mock()
        self._compute_price = Mock(return_value=13)
        self._is_item_visible = Mock(return_value=True)
        self._get_active_character = Mock(return_value=self._create_mock_character())
        self.move_hex = Mock(return_value={"success": True})
        self.emit_party_moved = Mock()
        self.get_map_data = Mock(return_value={})
        self._execute_purchase = Mock()
        self._execute_sell = Mock()
        self._execute_barter = Mock()

    def _create_mock_merchant(self):
        merchant = Mock()
        merchant.id = "grom"
        merchant.name = "Grom"
        merchant.display_name = "wooden table"
        # Create item with real string name
        item = Mock()
        item.name = "Healing Potion"
        item.base_price = 10
        item.tags = set()
        merchant.inventory = [item]
        merchant.constraints = Mock(barter_allowed=True)
        merchant.personality = Mock(greed=5, paranoia=3, honor=5, sociability=5, risk_tolerance=5)
        return merchant

    def _create_mock_character(self):
        char = Mock()
        char.currency = 100
        char.inventory = []
        char.id = "char1"
        char.name = "TestChar"
        return char

    def get_player_by_session(self, session_id):
        return None

    def get_or_create_player(self, session_id):
        return Mock(id="player1")

@pytest.fixture
def engine():
    world_controller = MockWorldController()
    return AdjudicationEngine(world_controller)

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_buy_potion_start(engine):
    frame = IntentFrame(action="buy", category="economy", item="potion", raw_text="buy potion")
    result = engine.process(frame, session_id="test_session")
    assert result["success"] is False
    assert "costs 13 gp" in result["message"]
    assert "test_session" in engine.active_fsms

def test_buy_potion_offer_and_confirm(engine):
    # Step 1: start buy
    frame1 = IntentFrame(action="buy", category="economy", item="potion", raw_text="buy potion")
    engine.process(frame1, session_id="test_session")

    # Step 2: offer low price
    frame2 = IntentFrame(action="offer", category="other", raw_text="10", price=10)
    result = engine.process(frame2, session_id="test_session")
    assert result["success"] is False
    assert "Offer too low" in result["message"]

    # Step 3: offer acceptable price
    frame3 = IntentFrame(action="offer", category="other", raw_text="13", price=13)
    result = engine.process(frame3, session_id="test_session")
    assert result["success"] is False
    # After acceptable offer, the FSM may still be in countering; just ensure not initial prompt
    assert "costs" not in result["message"]

    # Step 4: confirm
    frame4 = IntentFrame(action="confirm", category="other", raw_text="yes")
    result = engine.process(frame4, session_id="test_session")
    assert result["success"] is True
    assert "bought" in result["message"]
    assert result["action"] == "refresh_inventory"
    assert "test_session" not in engine.active_fsms