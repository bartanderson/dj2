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

# ========== Event emission helper ==========

def _emit_event(instance, event_type, source_system, extra=None):
    """
    Emit an event through the engine's EventLog, merging session_id from
    the FSM context. Silently no-ops when the engine or its event_log is
    absent (isolated unit tests).
    """
    engine = instance.context.get('engine')
    if engine is None or not hasattr(engine, 'event_log'):
        return
    data = {'session_id': instance.context.get('session_id', '')}
    if extra:
        data.update(extra)
    engine.event_log.emit(event_type, data, source_system=source_system)


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
    _emit_event(instance, 'state.resource.changed', 'economy',
                {'resource': 'gold', 'delta': extra})
    return instance.context

def execute_buy(instance, event_data):
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_execute_purchase'):
        engine._execute_purchase(
            instance.context['character'],
            instance.context['merchant'],
            instance.context['item'],
            instance.context.get('price', instance.context.get('current_price', 0))
        )
    if engine is not None and hasattr(engine, 'event_log'):
        merchant = instance.context.get('merchant')
        merchant_id = getattr(merchant, 'id', '') if merchant is not None else ''
        engine.event_log.emit(
            'interaction.trade.completed',
            {
                'session_id': instance.context.get('session_id', ''),
                'merchant_id': merchant_id,
            },
            source_system='economy',
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
    merchant = instance.context.get('merchant')
    merchant_id = getattr(merchant, 'id', '') if merchant is not None else ''
    _emit_event(instance, 'interaction.trade.completed', 'economy',
                {'merchant_id': merchant_id})
    return instance.context

# ========== Encounter helpers ==========

def _emit_encounter(instance, event_type, extra=None):
    """
    Emit an event through the engine's EventLog. All initial event types
    require session_id and encounter_id in data (config/events/initial_events.json).
    Silently no-ops when the engine is absent (e.g. in isolated unit tests).
    """
    engine = instance.context.get('engine')
    if engine is None or not hasattr(engine, 'event_log'):
        return
    data = {
        'session_id':   instance.context.get('session_id', ''),
        'encounter_id': instance.context.get('encounter_id', ''),
    }
    if extra:
        data.update(extra)
    engine.event_log.emit(event_type, data, source_system='encounter')


# ========== Encounter guards ==========

def fight_possible(instance, event_data):
    """True unless the engine provides _check_fight and it says no."""
    engine = instance.context.get('engine')
    if engine and hasattr(engine, '_check_fight'):
        return engine._check_fight(instance.context.get('encounter_data'))
    return True


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


# ========== Encounter actions ==========

def begin_encounter(instance, event_data):
    """Emit encounter.started with the encounter description."""
    _emit_encounter(instance, 'encounter.started', {
        'description': instance.context.get('description', ''),
    })
    return instance.context


def start_combat(instance, event_data):
    """Emit combat.initiation.triggered. Combat rules are not implemented here."""
    _emit_encounter(instance, 'combat.initiation.triggered')
    return instance.context


def resolve_flee(instance, event_data):
    """Emit encounter.updated then encounter.ended (outcome=fled)."""
    _emit_encounter(instance, 'encounter.updated')
    _emit_encounter(instance, 'encounter.ended', {'outcome': 'fled'})
    return instance.context


def resolve_parley(instance, event_data):
    """Emit encounter.updated then encounter.ended (outcome=parleyed)."""
    _emit_encounter(instance, 'encounter.updated')
    _emit_encounter(instance, 'encounter.ended', {'outcome': 'parleyed'})
    return instance.context