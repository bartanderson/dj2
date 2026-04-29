# world/fsm/builtins.py
# Reusable guard and action functions.

def _get_event_value(event_data):
    """
    Extract the 'value' from event_data regardless of whether it is a dict,
    an EventData object, or a tuple. Returns 0 if not found.
    """
    if event_data is None:
        return 0
    # If it's a dict, just use .get
    if hasattr(event_data, 'get'):
        return event_data.get('value', 0)
    # If it's an EventData object (from python-statemachine), it has kwargs and args
    if hasattr(event_data, 'kwargs') and event_data.kwargs:
        return event_data.kwargs.get('value', 0)
    if hasattr(event_data, 'args') and event_data.args:
        first = event_data.args[0]
        if isinstance(first, dict):
            return first.get('value', 0)
        # If it's a plain number, return it
        if isinstance(first, (int, float)):
            return first
    return 0

# ========== Guards ==========

def price_lt(instance, event_data):
    offered = _get_event_value(event_data)
    current = instance.context.get('current_price', 0)
    return offered < current

def price_ge(instance, event_data):
    offered = _get_event_value(event_data)
    current = instance.context.get('current_price', 0)
    print(f"[DEBUG price_ge] offered={offered}, current={current}")
    return offered >= current

def offer_gt(instance, event_data):
    offered = _get_event_value(event_data)
    merchant = instance.context.get('merchant_price', 0)
    return offered > merchant

def offer_le(instance, event_data):
    offered = _get_event_value(event_data)
    merchant = instance.context.get('merchant_price', 0)
    return offered <= merchant

def need_more_gold(instance, event_data):
    offered = _get_event_value(event_data)
    shortage = instance.context.get('shortage', 0)
    return offered < shortage

def shortage_met(instance, event_data):
    offered = _get_event_value(event_data)
    shortage = instance.context.get('shortage', 0)
    return offered >= shortage

# ========== Actions ==========

def store_offer(instance, event_data):
    offered = _get_event_value(event_data)
    instance.context['price'] = offered
    return instance.context

def update_price(instance, event_data):
    # Same as store_offer
    return store_offer(instance, event_data)

def add_gold(instance, event_data):
    extra = _get_event_value(event_data)
    instance.context['offered_extra'] = extra
    shortage = instance.context.get('shortage', 0)
    instance.context['shortage'] = shortage - extra
    return instance.context

def execute_purchase(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_execute_purchase'):
        engine._execute_purchase(
            instance.context['character'],
            instance.context['merchant'],
            instance.context['item'],
            instance.context.get('price', instance.context.get('current_price', 0))
        )
    return instance.context

def execute_sell(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_execute_sell'):
        engine._execute_sell(
            instance.context['character'],
            instance.context['merchant'],
            instance.context['item'],
            instance.context.get('price', instance.context.get('merchant_price', 0))
        )
    return instance.context

def execute_barter(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_execute_barter'):
        engine._execute_barter(
            instance.context['character'],
            instance.context['merchant'],
            instance.context['give_item_obj'],
            instance.context['receive_item_obj'],
            instance.context.get('offered_extra', 0)
        )
    return instance.context

# Encounter actions (simple stubs)
def flee_possible(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_check_flee'):
        return engine._check_flee(instance.context.get('encounter_data'))
    return False

def parley_possible(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_check_parley'):
        return engine._check_parley(instance.context.get('encounter_data'))
    return False

def start_combat(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_start_combat'):
        engine._start_combat(instance.context.get('encounter_data'))
    return instance.context

def resolve_flee(instance, event_data):
    return instance.context

def resolve_parley(instance, event_data):
    return instance.context