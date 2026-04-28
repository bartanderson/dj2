from statemachine import StateMachine, State
from typing import Dict, Any, Optional
from world.fsm.registry import get_guard, get_action

class SellFSM(StateMachine):
    awaiting = State(initial=true, final=false)
    countering = State(initial=false, final=false)
    completed = State(initial=false, final=true)

    def __init__(self, context: Dict[str, Any]):
        self.context = context
        super().__init__()

    # Transitions are defined as class attributes using .to with cond/on
    confirm = (
                    awaiting.to(completed, on=[get_action('') for act in ["execute_sell"]])
 |                     countering.to(completed, on=[get_action('') for act in ["execute_sell"]])
    )
    offer = (
                awaiting.to(countering, cond=get_guard('offer_too_high'), on=[get_action('') for act in ["store_offer"]])
 |                 countering.to(countering, cond=get_guard('offer_too_high'), on=[get_action('') for act in ["store_offer"]])
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
                'prompt': 'I'll give you {merchant_price} gp for your {item_name}. Say 'yes' to sell, or offer a price.',
            },
            'countering': {
                'prompt': 'Offer too high. I'll pay {merchant_price} gp. Say 'yes' or offer again.',
            },
            'completed': {
                'prompt': 'You sold {item_name} for {price} gp.',
            },
        }