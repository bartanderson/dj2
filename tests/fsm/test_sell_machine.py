# tests/fsm/test_sell_machine.py

import pytest
from world.fsm.sell_machine import SellMachine

class MockWorld:
    def __init__(self):
        self.sell_executed = False
        self.last_sell = None

    def _execute_sell(self, character, merchant, item, price):
        self.sell_executed = True
        self.last_sell = (character, merchant, item, price)

class MockCharacter:
    currency = 100
    name = "TestChar"

class MockMerchant:
    name = "TestMerchant"

class MockItem:
    name = "Shortsword"
    cost = 10

@pytest.fixture
def mock_world():
    return MockWorld()

@pytest.fixture
def mock_character():
    return MockCharacter()

@pytest.fixture
def mock_merchant():
    return MockMerchant()

@pytest.fixture
def mock_item():
    return MockItem()

def test_initial_state(mock_world, mock_character, mock_merchant, mock_item):
    fsm = SellMachine(6, mock_character, mock_merchant, mock_item, mock_world)
    assert fsm.current_state.id == "awaiting"
    assert "I'll give you 6 gp" in fsm.get_prompt()

def test_offer_too_high(mock_world, mock_character, mock_merchant, mock_item):
    fsm = SellMachine(6, mock_character, mock_merchant, mock_item, mock_world)
    fsm.offer(10)
    assert fsm.current_state.id == "countering"
    assert "Offer too high" in fsm.get_prompt()
    assert fsm._last_offer == 10
    assert not mock_world.sell_executed

def test_offer_acceptable(mock_world, mock_character, mock_merchant, mock_item):
    fsm = SellMachine(6, mock_character, mock_merchant, mock_item, mock_world)
    fsm.offer(5)
    assert fsm.current_state.id == "completed"
    assert "sold" in fsm.get_prompt()
    assert mock_world.sell_executed
    assert mock_world.last_sell[3] == 5

def test_confirm_after_offer(mock_world, mock_character, mock_merchant, mock_item):
    fsm = SellMachine(6, mock_character, mock_merchant, mock_item, mock_world)
    fsm.offer(10)   # enters countering
    fsm.confirm()   # should complete at merchant_price (6)
    assert fsm.current_state.id == "completed"
    assert mock_world.sell_executed
    assert mock_world.last_sell[3] == 6

def test_cancel(mock_world, mock_character, mock_merchant, mock_item):
    fsm = SellMachine(6, mock_character, mock_merchant, mock_item, mock_world)
    fsm.cancel()
    assert fsm.current_state.id == "completed"
    assert not mock_world.sell_executed