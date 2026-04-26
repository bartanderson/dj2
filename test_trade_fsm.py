from statemachine import StateMachine, State

class TradeMachine(StateMachine):
    awaiting = State(initial=True)
    countering = State()
    completed = State(final=True)

    confirm = (awaiting.to(completed) | countering.to(completed))
    offer = awaiting.to(countering) | countering.to(countering)

    def __init__(self, current_price):
        self.current_price = current_price
        self.offer = None
        super().__init__()

    def on_offer(self, price):
        self.offer = price
        if price >= self.current_price:
            # transition to completed directly? Not possible here because event already fired.
            # So we'll use a guard instead.
            pass

    # Guard method – must be named exactly as string in transition
    def price_too_low(self, price):
        return price < self.current_price

    def price_acceptable(self, price):
        return price >= self.current_price

# Define transitions with guards
TradeMachine.offer.cond = TradeMachine.price_too_low   # default
# Actually, we need multiple transitions per event. Let's use the class syntax.

# Better: Define at class level using the declarative API
class TradeMachine2(StateMachine):
    awaiting = State(initial=True)
    countering = State()
    completed = State(final=True)

    confirm = awaiting.to(completed) | countering.to(completed)
    offer = awaiting.to(countering, cond="price_too_low") | \
            countering.to(countering, cond="price_too_low") | \
            awaiting.to(completed, cond="price_acceptable") | \
            countering.to(completed, cond="price_acceptable")

    def __init__(self, current_price):
        self.current_price = current_price
        super().__init__()

    def price_too_low(self, price):
        return price < self.current_price

    def price_acceptable(self, price):
        return price >= self.current_price

# Test
machine = TradeMachine2(13)
print(machine.current_state.id)  # awaiting
machine.offer(10)
print(machine.current_state.id)  # countering
machine.offer(13)
print(machine.current_state.id)  # completed