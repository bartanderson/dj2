# test_ai.py
import sys
import json
from world.ai_integration import BaseAI

def main():
    # Hardcoded prompt for testing intent extraction
    hardcoded_prompt = """You are the AI Dungeon Master. Your job is to interpret the player's message and output a JSON object with 'intent' and 'parameters'.

Examples:
- For buying: {"intent": "buy", "parameters": {"item": "healing potion"}}
- For asking a rule: {"intent": "answer", "parameters": {"question": "What is Brawn?"}}

Player message: "go north"

Output only the JSON, no extra text.
"""
    # Use command-line argument if provided, otherwise use hardcoded prompt
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = hardcoded_prompt

    print("\nSending prompt to AI...")
    ai = BaseAI()
    response = ai.generate_text(prompt)
    print("\n--- Raw AI Response ---")
    print(response)
    print("----------------------\n")

    try:
        data = json.loads(response)
        print("Successfully parsed JSON:")
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")

if __name__ == "__main__":
    main()