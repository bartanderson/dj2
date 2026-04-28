from statemachine import StateMachine, State
from typing import Dict, Any, Optional
from world.fsm.registry import get_guard, get_action

class BarterFSM(StateMachine):
    awaiting = State(initial=true, final=false)
    countering = State(initial=false, final=false)
    completed = State(initial=false, final=true)

    def __init__(self, context: Dict[str, Any]):
        self.context = context
        super().__init__()

    # Transitions are defined as class attributes using .to with cond/on
    confirm = (
                    awaiting.to(completed, on=[get_action('') for act in ["execute_barter"]])
 |                     countering.to(completed, on=[get_action('') for act in ["execute_barter"]])
    )
    offer = (
                awaiting.to(countering, cond=get_guard('need_more_gold'), on=[get_action('') for act in ["add_gold"]])
 |                 countering.to(countering, cond=get_guard('need_more_gold'), on=[get_action('') for act in ["add_gold"]])
    )
    cancel = (
                    awaiting.to(completed)
 |                     countering.to(completed)
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
            'awaiting': {
                'prompt': 'Your {give_item} (worth {give_value} gp) for {receive_item} (worth {receive_value} gp). Need {shortage} more gp. Offer that amount or say 'yes'.',
            },
            'countering': {
                'prompt': 'Need exactly {shortage} gp. Offer that amount or say 'yes'.',
            },
            'completed': {
                'prompt': 'Barter completed!',
            },
        }