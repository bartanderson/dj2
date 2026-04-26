# world/fsm/trade_machine.py

from statemachine import StateMachine, State

class TradeMachine(StateMachine):
    awaiting = State(initial=True)
    countering = State()
    completed = State(final=True)

    confirm = awaiting.to(completed) | countering.to(completed)
    offer = awaiting.to(countering, cond="price_too_low") | \
            countering.to(countering, cond="price_too_low") | \
            awaiting.to(completed, cond="price_acceptable") | \
            countering.to(completed, cond="price_acceptable")

    def __init__(self, current_price, character, merchant, item, engine):
        self.current_price = current_price
        self.character = character
        self.merchant = merchant
        self.item = item
        self.engine = engine
        super().__init__()

    def price_too_low(self, price):
        return price < self.current_price

    def price_acceptable(self, price):
        return price >= self.current_price

    def on_enter_completed(self):
        # When we enter completed state, execute the purchase
        # Use the last offered price if available, otherwise current_price
        price = getattr(self, '_last_offer', self.current_price)
        self.engine._execute_purchase(self.character, self.merchant, self.item, price)

    def on_offer(self, price):
        # Store the offered price in case we need it later
        self._last_offer = price