# world/entity_resolver.py

class EntityResolver:
    """
    Resolves player terms (e.g., "potion", "sword") to actual game objects.
    Uses a merchant's inventory as the source of truth.
    """
    def __init__(self):
        self.synonyms = {
            "potion": "Healing Potion",
            "hp pot": "Healing Potion",
            "health pot": "Healing Potion",
            "sword": "Shortsword",
            "blade": "Shortsword",
            "short sword": "Shortsword",
        }
        self.item_index = {}   # normalized name -> item object

    def load_merchant_items(self, merchant):
        """Build index from merchant's inventory."""
        self.item_index = {}
        for item in merchant.inventory:
            name_lower = item.name.lower()
            self.item_index[name_lower] = item
        # Add synonyms
        for alias, real_name in self.synonyms.items():
            real_lower = real_name.lower()
            if real_lower in self.item_index:
                self.item_index[alias] = self.item_index[real_lower]

    def resolve_item(self, user_term: str):
        """Return item object or None."""
        term = user_term.lower().strip()
        return self.item_index.get(term)

    def load_character_inventory(self, character):
        self.item_index = {}
        for item in character.inventory:
            name_lower = item.name.lower()
            self.item_index[name_lower] = item
        # also add synonyms as before
        for alias, real in self.synonyms.items():
            real_lower = real.lower()
            if real_lower in self.item_index:
                self.item_index[alias] = self.item_index[real_lower]

    def _compute_sell_price(self, item, merchant, rel):
        """Helper to compute how much merchant will pay for an item (sell value)."""
        base_price = item.cost if hasattr(item, 'cost') else 10
        # Merchant's greed reduces price (since they want to keep money), affinity/trust increases price
        multiplier = 1.0
        multiplier -= (merchant.personality.greed - 5) * 0.05
        multiplier += rel.affinity * 0.03
        multiplier += rel.trust * 0.02
        multiplier -= rel.fear * 0.04
        multiplier = max(0.2, min(1.0, multiplier))
        price = int(base_price * multiplier)
        return max(1, price)