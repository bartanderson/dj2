import pytest
from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins

# ----------------------------------------------------------------------
# Helper to create FSM instances with proper registries
# ----------------------------------------------------------------------
def make_buy_fsm():
    context = {
        'item_name': 'Potion',
        'current_price': 13,
        '_guard_registry': {
            'price_too_low': builtins.price_lt,
            'price_acceptable': builtins.price_ge,
        },
        '_action_registry': {
            'store_offer': builtins.store_offer,
            'execute_purchase': builtins.execute_purchase,
        },
        'character': None,
        'merchant': None,
        'item': None,
        'engine': None,
    }
    return GenericFSM('config/fsms/buy.json', context)

def make_sell_fsm():
    context = {
        'item_name': 'Sword',
        'merchant_price': 6,
        '_guard_registry': {
            'offer_too_high': builtins.offer_gt,
            'offer_acceptable': builtins.offer_le,
        },
        '_action_registry': {
            'store_offer': builtins.store_offer,
            'execute_sell': builtins.execute_sell,
        },
        'character': None,
        'merchant': None,
        'item': None,
        'engine': None,
    }
    return GenericFSM('config/fsms/sell.json', context)

def make_barter_fsm():
    # TODO: implement proper context for barter
    pytest.skip("Barter test not yet implemented")
    # The following is a placeholder – will be fixed later
    context = {
        'give_item': 'Shortsword',
        'receive_item': 'Potion',
        'give_value': 6,
        'receive_value': 13,
        'shortage': 7,
        '_guard_registry': {
            'need_more_gold': builtins.need_more_gold,
            'offer_acceptable': builtins.shortage_met,
        },
        '_action_registry': {
            'add_gold': builtins.add_gold,
            'execute_barter': builtins.execute_barter,
        },
        'character': None,
        'merchant': None,
        'give_item_obj': None,
        'receive_item_obj': None,
        'engine': None,
    }
    return GenericFSM('config/fsms/barter.json', context)

def make_encounter_fsm(flee_success=False, parley_success=False):
    context = {
        'description': 'Goblin attack!',
        'encounter_data': {'desc': 'Goblin'},
        'flee_success': flee_success,
        'parley_success': parley_success,
        '_guard_registry': {
            'flee_possible': builtins.flee_possible,
            'parley_possible': builtins.parley_possible,
        },
        '_action_registry': {
            'start_combat': builtins.start_combat,
            'resolve_flee': builtins.resolve_flee,
            'resolve_parley': builtins.resolve_parley,
        },
        'engine': None,
        'session_id': 'test',
    }
    fsm = GenericFSM('config/fsms/encounter.json', context)
    fsm.send_event('next')   # move from initiating to awaiting_choice
    return fsm

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
def test_buy_flow():
    fsm = make_buy_fsm()
    assert fsm.state == 'awaiting'
    assert 'costs 13 gp' in fsm.get_prompt()
    fsm.send_event('offer', {'value': 10})
    assert fsm.state == 'countering'
    assert 'Offer too low' in fsm.get_prompt()
    fsm.send_event('offer', {'value': 13})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'bought' in fsm.get_prompt()

def test_sell_flow():
    fsm = make_sell_fsm()
    assert fsm.state == 'awaiting'
    assert 'give you 6 gp' in fsm.get_prompt()
    fsm.send_event('offer', {'value': 10})
    assert fsm.state == 'countering'
    assert 'Offer too high' in fsm.get_prompt()
    fsm.send_event('offer', {'value': 5})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'
    assert 'sold' in fsm.get_prompt()

@pytest.mark.skip(reason="Barter test needs proper context and builtins")
def test_barter_flow():
    fsm = make_barter_fsm()
    assert fsm.state == 'awaiting'
    fsm.send_event('offer', {'value': 5})
    assert fsm.state == 'countering'
    fsm.send_event('offer', {'value': 2})
    fsm.send_event('confirm')
    assert fsm.state == 'completed'

@pytest.mark.skip(reason="Encounter test needs mock engine and event handling")
def test_encounter_flee_success():
    fsm = make_encounter_fsm(flee_success=True)
    assert fsm.state == 'awaiting_choice'
    fsm.send_event('flee')
    assert fsm.state == 'completed'

@pytest.mark.skip(reason="Encounter test needs mock engine and event handling")
def test_encounter_flee_failure():
    fsm = make_encounter_fsm(flee_success=False)
    assert fsm.state == 'awaiting_choice'
    fsm.send_event('flee')
    assert fsm.state == 'awaiting_choice'   # should stay because flee failed

@pytest.mark.skip(reason="Encounter test needs mock engine and event handling")
def test_encounter_parley_failure():
    fsm = make_encounter_fsm(parley_success=False)
    assert fsm.state == 'awaiting_choice'
    fsm.send_event('parley')
    assert fsm.state == 'awaiting_choice'   # failure returns to choices