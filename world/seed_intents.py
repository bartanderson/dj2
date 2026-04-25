# world/seed_intents.py
from world.intent_manager import IntentManager

def main():
    im = IntentManager()

    # ------------------------------------------------------------------
    # 1. Add intents (idempotent)
    # ------------------------------------------------------------------
    im.add_intent("acquire_goods", "Player wants to buy or obtain an item")
    im.add_intent("dispose_goods", "Player wants to sell or give away an item")
    im.add_intent("negotiate_price", "Player wants to haggle over price")
    im.add_intent("relocate_self", "Player wants to move to a different location")
    im.add_intent("survey_environment", "Player wants to look around the area")
    im.add_intent("survey_entity", "Player wants to examine a specific entity superficially")
    im.add_intent("inspect_entity", "Player wants to inspect an entity in detail (e.g., merchant's inventory)")
    im.add_intent("clarification_needed", "Fallback for ambiguous input")

    # ------------------------------------------------------------------
    # 2. Define examples per intent
    # ------------------------------------------------------------------
    examples = {
        "acquire_goods": [
            "buy healing potion", "purchase shortsword", "get the shield",
            "i want to buy the dagger", "acquire a healing potion"
        ],
        "dispose_goods": [
            "sell shield", "trade away shortsword", "get rid of this dagger",
            "i want to sell the healing potion"
        ],
        "negotiate_price": [
            "haggle on price", "can you lower the price", "negotiate better deal",
            "that's too expensive", "make it cheaper", "how about giving me that healing potion for 7 gp",
            "I'll give you 5 gold for the shortsword"
        ],
        "relocate_self": [
            "go north", "move south", "walk east", "head west",
            "travel to the tavern", "go to the forest", "move towards the mountains",
            "head to the village", "go to the merchant", "walk to the shop"
        ],
        "survey_environment": [
            "look around", "examine the area", "what do I see", "describe surroundings"
        ],
        "survey_entity": [
            "look at merchant", "examine the trader", "look at Grom",
            "look at table", "examine the cart", "check the stall",
            "look at the wooden table", "what's on the wagon",
            "examine the coat", "look at pockets", "inspect the backpack"
        ]
    }

    # ------------------------------------------------------------------
    # 3. Clear and repopulate examples for each intent
    # ------------------------------------------------------------------
    for intent, texts in examples.items():
        if intent.endswith("_neg"):
            # Negative examples are added with is_positive=False
            base_intent = intent.replace("_neg", "")
            for text in texts:
                im.add_example(base_intent, text, is_positive=False)
        else:
            # Positive examples: clear first, then add
            im.clear_examples(intent)
            for text in texts:
                im.add_example(intent, text, is_positive=True)

    print("Intent examples seeded successfully.")

if __name__ == "__main__":
    main()