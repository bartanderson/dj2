import pytest
from world.fsm.generic_fsm import GenericFSM

# ----------------------------------------------------------------------
# Mock callbacks (guards and actions) with correct signatures
# ----------------------------------------------------------------------
def make_mock_registry():
    guard_registry = {}
    action_registry = {}

    def extract_value(event_data):
        """Extract the 'value' from event_data regardless of library version."""
        if hasattr(event_data, 'kwargs') and event_data.kwargs:
            return event_data.kwargs.get('value', 0)
        elif hasattr(event_data, 'args') and event_data.args:
            first = event_data.args[0]
            if isinstance(first, dict):
                return first.get('value', 0)
            else:
                return first
        return 0

    # ---------- Guards ----------
    # Buy guards
    def price_too_low(self, event_data):
        offered = extract_value(event_data)
        current = self.context.get('current_price', 0)
        return offered < current

    def price_acceptable(self, event_data):
        offered = extract_value(event_data)
        current = self.context.get('current_price', 0)
        return offered >= current

    # Sell guards
    def offer_too_high(self, event_data):
        offered = extract_value(event_data)
        merchant_price = self.context.get('merchant_price', 0)
        return offered > merchant_price

    def offer_acceptable(self, event_data):
        offered = extract_value(event_data)
        merchant_price = self.context.get('merchant_price', 0)
        return offered <= merchant_price

    # Barter guards
    def need_more_gold(self, event_data):
        offered = extract_value(event_data)
        shortage = self.context.get('shortage', 0)
        return offered < shortage

    def barter_acceptable(self, event_data):
        offered = extract_value(event_data)
        shortage = self.context.get('shortage', 0)
        return offered >= shortage

    # Encounter guards
    def flee_possible(self, event_data):
        return self.context.get('flee_success', False)

    def parley_possible(self, event_data):
        return self.context.get('parley_success', False)

    # ---------- Actions ----------
    def store_offer(self, event_data):
        self.context['price'] = extract_value(event_data)
        return self.context

    def execute_purchase(self, event_data):
        self.context['purchase_executed'] = True
        return self.context

    def execute_sell(self, event_data):
        self.context['sell_executed'] = True
        return self.context

    def add_gold(self, event_data):
        extra = extract_value(event_data)
        self.context['offered_extra'] = extra
        self.context['shortage'] = self.context.get('shortage', 0) - extra
        return self.context

    def execute_barter(self, event_data):
        self.context['barter_executed'] = True
        return self.context

    def start_combat(self, event_data):
        self.context['combat_started'] = True
        return self.context

    def resolve_flee(self, event_data):
        self.context['flee_resolved'] = True
        return self.context

    def resolve_parley(self, event_data):
        self.context['parley_resolved'] = True
        return self.context

    # Register all guards and actions
    guard_registry = {
        'price_too_low': price_too_low,
        'price_acceptable': price_acceptable,
        'offer_too_high': offer_too_high,
        'offer_acceptable': offer_acceptable,
        'need_more_gold': need_more_gold,
        'offer_acceptable': barter_acceptable,   # alias for barter
        'flee_possible': flee_possible,
        'parley_possible': parley_possible,
    }
    action_registry = {
        'store_offer': store_offer,
        'execute_purchase': execute_purchase,
        'execute_sell': execute_sell,
        'add_gold': add_gold,
        'execute_barter': execute_barter,
        'start_combat': start_combat,
        'resolve_flee': resolve_flee,
        'resolve_parley': resolve_parley,
    }
    return guard_registry, action_registry

# Create global registries
GUARD_REG, ACTION_REG = make_mock_registry()

def make_fsm(json_path, context_overrides=None):
    base_context = {
        '_guard_registry': GUARD_REG,
        '_action_registry': ACTION_REG,
    }
    if context_overrides:
        base_context.update(context_overrides)
    return GenericFSM(json_path, base_context)

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_buy_flow():
    fsm = make_fsm('config/fsms/buy.json', {
        'item_name': 'Potion',
        'current_price': 13,
    })
    assert fsm.state == 'awaiting'
    assert 'costs 13 gp' in fsm.get_prompt()

    fsm.send_event('offer', {'value': 10})
    assert fsm.state == 'countering'
    assert 'Offer too low' in fsm.get_prompt()

    fsm.send_event('offer', {'value': 13})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'bought' in fsm.get_prompt()
    assert fsm.context.get('purchase_executed') is True

def test_sell_flow():
    fsm = make_fsm('config/fsms/sell.json', {
        'item_name': 'Sword',
        'merchant_price': 6,
    })
    assert fsm.state == 'awaiting'
    assert 'give you 6 gp' in fsm.get_prompt()

    fsm.send_event('offer', {'value': 10})
    assert fsm.state == 'countering'
    assert 'Offer too high' in fsm.get_prompt()

    fsm.send_event('offer', {'value': 5})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'sold' in fsm.get_prompt()
    assert fsm.context.get('sell_executed') is True

def test_barter_flow():
    fsm = make_fsm('config/fsms/barter.json', {
        'give_item': 'Shortsword',
        'receive_item': 'Healing Potion',
        'give_value': 6,
        'receive_value': 13,
        'shortage': 7,
    })
    assert fsm.state == 'awaiting'
    assert 'Need 7 more gp' in fsm.get_prompt()

    fsm.send_event('offer', {'value': 5})
    assert fsm.state == 'countering'
    fsm.send_event('offer', {'value': 2})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert fsm.context.get('barter_executed') is True

def test_encounter_flee_success():
    fsm = make_fsm('config/fsms/encounter.json', {
        'description': 'Goblin attacks!',
        'flee_success': True,
        'parley_success': False,
    })
    fsm.send_event('next')
    assert fsm.state == 'awaiting_choice'
    fsm.send_event('flee')
    assert fsm.state == 'completed'
    assert fsm.context.get('flee_resolved') is True

def test_encounter_flee_failure():
    fsm = make_fsm('config/fsms/encounter.json', {
        'description': 'Goblin attacks!',
        'flee_success': False,
        'parley_success': False,
    })
    fsm.send_event('next')
    try:
        fsm.send_event('flee')
    except Exception:
        pass
    assert fsm.state == 'awaiting_choice'

def test_encounter_parley_failure():
    fsm = make_fsm('config/fsms/encounter.json', {
        'description': 'Goblin attacks!',
        'flee_success': False,
        'parley_success': False,
    })
    fsm.send_event('next')
    try:
        fsm.send_event('parley')
    except Exception:
        pass
    assert fsm.state == 'awaiting_choice'