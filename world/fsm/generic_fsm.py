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

    def _build_machine(self):
        # Create State objects
        states = {}
        for s in self.definition['states']:
            name = s['name']
            initial = s.get('initial', False)
            final = s.get('final', False)
            states[name] = State(name, initial=initial, final=final)

        # Build transitions per event – expects event_def to be dict with 'transitions' list
        events = {}
        for event_name, event_def in self.definition['events'].items():
            # Support both old (list) and new (dict with 'transitions') formats
            if isinstance(event_def, dict) and 'transitions' in event_def:
                trans_list = event_def['transitions']
            else:
                trans_list = event_def  # old format
            trans_objects = []
            for t in trans_list:
                source = states[t['from']]
                target = states[t['to']]
                cond = t.get('cond')
                actions = t.get('actions', [])
                transition = source.to(target, event=event_name, cond=cond, on=actions)
                trans_objects.append(transition)
            if not trans_objects:
                continue
            combined = trans_objects[0]
            for other in trans_objects[1:]:
                combined |= other
            events[event_name] = combined

        # Build class attributes
        attrs = {}
        attrs.update({name: state for name, state in states.items()})
        attrs.update({name: event for name, event in events.items()})

        # Create class dynamically
        machine_cls = StateMachineMetaclass(
            self.definition.get('name', 'GenericFSM'),
            (StateMachine,),
            attrs
        )

        # Attach guard/action functions to the class **before** instantiating
        for name, func in self.context.get('_guard_registry', {}).items():
            setattr(machine_cls, name, func)
        for name, func in self.context.get('_action_registry', {}).items():
            setattr(machine_cls, name, func)

        # Now instantiate the class (the methods are present)
        instance = machine_cls()
        instance.context = self.context
        return instance

    def send_event(self, event_name: str, event_data: Optional[Dict] = None):
        method = getattr(self._machine, event_name)
        if event_data:
            method(**event_data)
        else:
            method()
        return self

    def get_prompt(self) -> str:
        state_id = self._machine.current_state.id
        for s in self.definition['states']:
            if s['name'] == state_id:
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
        return self._machine.current_state.id