from statemachine import StateMachine, State
from typing import Dict, Any, Optional
from world.fsm.registry import get_guard, get_action

class EncounterFSM(StateMachine):
    initiating = State(initial=true, final=false)
    awaiting_choice = State(initial=false, final=false)
    resolving_fight = State(initial=false, final=false)
    completed = State(initial=false, final=true)

    def __init__(self, context: Dict[str, Any]):
        self.context = context
        super().__init__()

    # Transitions are defined as class attributes using .to with cond/on
    next = (
                initiating.to(awaiting_choice)
    )
    fight = (
                awaiting_choice.to(resolving_fight, on=[get_action('') for act in ["start_combat"]])
    )
    flee = (
                awaiting_choice.to(completed, cond=get_guard('flee_possible'), on=[get_action('') for act in ["resolve_flee"]])
    )
    parley = (
                awaiting_choice.to(completed, cond=get_guard('parley_possible'), on=[get_action('') for act in ["resolve_parley"]])
    )
    combat_ended = (
                resolving_fight.to(completed)
    )

    def get_prompt(self) -> str:
        """Return the prompt for the current state, using the state's 'prompt' template."""
        state_id = self.current_state.id
        for s in self.__class__.states:
            if s.id == state_id:
                # Find the original state definition from the JSON (stored in class attribute)
                # We can store the state definitions when building the class.
                # Simpler: assume the state definitions are available in a dictionary.
                # We'll add a class attribute _state_meta after instantiation.
                if hasattr(self, '_state_meta') and state_id in self._state_meta:
                    template = self._state_meta[state_id].get('prompt', '')
                else:
                    template = ''
                try:
                    return template.format(**self.context)
                except KeyError:
                    return template
        return ""

    # After instance creation, attach state metadata from the definition
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # This runs when the class is created, but we need the original JSON.
        # Since the template has the original data, we can embed a dictionary.
        # Let's embed the state metadata as a class attribute.
        cls._state_meta = {
            'initiating': {
                'prompt': '{description}',
            },
            'awaiting_choice': {
                'prompt': '{description} What do you do? (fight/flee/parley)',
            },
            'resolving_fight': {
                'prompt': 'Combat starts!',
            },
            'completed': {
                'prompt': 'Encounter ended.',
            },
        }