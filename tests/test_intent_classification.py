# tools/test_intent_classification.py
import sys
from world.dm_chat_ai import DMChatAI
from world.ai_integration import BaseAI

# Initialize real AI (or use a mock)
ai_system = BaseAI()  # assuming BaseAI is the underlying system
dm_chat_ai = DMChatAI(ai_system)

test_messages = [
    "Can I be a giraffe?",
    "can I be a god?",
    "What kind of magic is there?",
    "Arcana sounds interesting",
    "Maybe incantations instead?",
    "Maybe enchantment",
    "Tell me about it",
    "That sounds cool. I want that",
    "No, I said enchantment",
    "Enchantment",
    "What class did you write down?",
    "I thought Arcana and Enchantment were different",
    "I want divine magic, not arcane",
    "what are my choices so far?",
]

for msg in test_messages:
    result = dm_chat_ai.classify_intent(msg, {})
    print(f"Message: {msg}")
    print(f"Intent: {result}")
    print("-" * 40)