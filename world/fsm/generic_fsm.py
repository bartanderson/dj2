import json
from statemachine import StateMachine, State
from statemachine.factory import StateMachineMetaclass
from typing import Dict, Any, Optional

class GenericFSM:
    def __init__(self, json_path: str, initial_context: Dict[str, Any]):
        with open(json_path, 'r') as f:
            self.definition = json.load(f)
        self.context = initial_context
        self._machine = self._build_machine()
        self._machine.context = self.context   # attach for callbacks

    def _build_machine(self):
        # Create State objects
        states = {}
        for s in self.definition['states']:
            name = s['name']
            initial = s.get('initial', False)
            final = s.get('final', False)
            states[name] = State(name, initial=initial, final=final)

        # Build transitions per event
        events = {}
        for event_name, trans_list in self.definition['events'].items():
            trans_objects = []
            for t in trans_list:
                source = states[t['from']]
                target = states[t['to']]
                cond = t.get('cond')
                actions = t.get('actions', [])
                transition = source.to(target, event=event_name, cond=cond, on=actions)
                trans_objects.append(transition)
            # Combine transitions for the same event
            combined = trans_objects[0]
            for other in trans_objects[1:]:
                combined |= other
            events[event_name] = combined

        # Build class attributes: states and events
        attrs = {}
        attrs.update({name: state for name, state in states.items()})
        attrs.update({name: event for name, event in events.items()})

        # Add guard and action callbacks as class methods
        guard_registry = self.context.get('_guard_registry', {})
        action_registry = self.context.get('_action_registry', {})
        for name, func in guard_registry.items():
            attrs[name] = func
        for name, func in action_registry.items():
            attrs[name] = func

        # Create the class dynamically
        machine_cls = StateMachineMetaclass(
            self.definition.get('name', 'GenericFSM'),
            (StateMachine,),
            attrs
        )
        return machine_cls()

    def send_event(self, event_name: str, event_data: Optional[Dict] = None):
        method = getattr(self._machine, event_name)
        if event_data:
            method(**event_data)
        else:
            method()
        return self

    def get_prompt(self) -> str:
        # Get the current configuration; for a flat machine, this is a set with one item.
        current_state_id = next(iter(self._machine.configuration)).id
        for s in self.definition['states']:
            if s['name'] == current_state_id:
                template = s.get('prompt', '')
                try:
                    return template.format(**self.context)
                except KeyError:
                    return template
        return ""

    @property
    def is_completed(self) -> bool:
        return self._machine.current_state.is_final

    @property
    def state(self) -> str:
        return next(iter(self._machine.configuration)).id