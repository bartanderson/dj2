# dm_chat_ai.py – OG System version
# Provides AI functions for topic extraction and response generation.

import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Replace this stub with your actual LLM call (e.g., to Ollama)
# ----------------------------------------------------------------------
def _call_llm(prompt: str) -> str:
    """
    Stub for LLM call. In production, replace with actual API call.
    Should return a JSON string.
    """
    # Example: response = requests.post(..., json={"prompt": prompt, ...})
    # For now, we'll raise an error to remind you to implement it.
    raise NotImplementedError("Replace _call_llm with your actual LLM integration")

# ----------------------------------------------------------------------
# Core function: generate a response from a prompt and return parsed JSON
# ----------------------------------------------------------------------
def _llm_json_response(prompt: str) -> Dict[str, Any]:
    """Call LLM with prompt and parse JSON response."""
    response_text = _call_llm(prompt)
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON from LLM: {response_text}")
        return {"narrative": "The DM considers your words thoughtfully.", "updates": {}, "needs_confirmation": False}

# ----------------------------------------------------------------------
# Topic extraction: determine what the player is asking about
# ----------------------------------------------------------------------
def extract_topic(message: str, game_context: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Uses AI to determine the topic of the player's message.
    Returns a dict with 'type' and 'value' (e.g., {'type': 'race', 'value': 'Elf'}).
    If no clear topic, returns {'type': 'general', 'value': None}.
    """
    prompt = f"""You are a topic extractor for an OG System game.
Given a player message, identify if they are asking about a specific race, class, skill, attribute, background, or spell.
Use only the following valid options from the OG System:

Races: {', '.join(game_context['races'])}
Classes: {', '.join(game_context['classes'])}
Skills: {', '.join(game_context['skills'])}
Attributes: {', '.join(game_context['attributes'])}
Backgrounds: {', '.join(game_context['backgrounds'])}
Spells: {', '.join(game_context['spells'][:20])}... (and more)

If the message asks about something not in these lists, or is a general question, return {{"type": "general", "value": null}}.

Player message: "{message}"

Respond with a JSON object containing "type" and "value". Examples:
- For "Tell me about elves" -> {{"type": "race", "value": "Elf"}}
- For "What does Brawn do?" -> {{"type": "attribute", "value": "Brawn"}}
- For "How do I become a mage?" -> {{"type": "class", "value": "Mage"}}
- For "What skills can I choose?" -> {{"type": "general", "value": null}}
"""
    data = _llm_json_response(prompt)
    # Ensure the response has the expected structure
    if "type" in data and "value" in data:
        return data
    return {"type": "general", "value": None}

# ----------------------------------------------------------------------
# Main response generation for character creation and game interaction
# ----------------------------------------------------------------------
def generate_response(message: str, session: Any, game_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates an AI response for the DM, including narrative, updates, and confirmation flag.
    Returns a dict with keys: narrative (str), updates (dict), needs_confirmation (bool).
    """
    # Build the prompt using OG System data
    prompt = f"""You are the AI Dungeon Master for an OG System game.

OG SYSTEM RULES:
- Attributes: Brawn, Finesse, Wits, Will (each 0-4, total 4 points, max 3 per attribute)
- Skills: {', '.join(game_context['skills'])}
- Classes: {', '.join(game_context['classes'])}
- Races: {', '.join(game_context['races'])}
- Backgrounds: {', '.join(game_context['backgrounds'])}
- Spells: {', '.join(game_context['spells'][:10])}... (and more)

Character creation steps:
1. Choose race and class.
2. Distribute 4 attribute points among Brawn, Finesse, Wits, Will.
3. Choose 2-3 skills.
4. Optionally pick a background.
5. If a spellcaster (Mage, Priest, Warlock, Bard), choose spells known.

Current character state: {session.character_data if not session.active_character_id else 'Character exists but details omitted for brevity'}

Player message: "{message}"

Respond in JSON with these fields:
- "narrative": Your immersive response, guiding the player or reacting to their input.
- "updates": A dictionary of any character field changes (e.g., {{"race": "Elf", "brawn": 3}}). Use only OG field names: race, class, background, brawn, finesse, wits, will, skills (list), spells (list).
- "needs_confirmation": true if you need the player to confirm these updates before applying.

Examples:
- Player: "I want to be a strong warrior" -> {{"narrative": "A Warrior with high Brawn! Let's set Brawn to 3.", "updates": {{"class": "Warrior", "brawn": 3}}, "needs_confirmation": false}}
- Player: "I'd like to play an elf" -> {{"narrative": "An elf, excellent choice.", "updates": {{"race": "Elf"}}, "needs_confirmation": false}}
- Player: "I want to be a mage" -> {{"narrative": "A mage! You'll need high Wits for spellcasting. How many points do you want in Wits?", "updates": {{"class": "Mage"}}, "needs_confirmation": false}}
- Player: "I choose Survival and Lore" -> {{"narrative": "Skills noted.", "updates": {{"skills": ["Survival", "Lore"]}}, "needs_confirmation": false}}

Always keep responses helpful and consistent with OG System rules.
"""
    data = _llm_json_response(prompt)
    # Ensure all required keys exist
    if "narrative" not in data:
        data["narrative"] = "The DM ponders your words..."
    if "updates" not in data:
        data["updates"] = {}
    if "needs_confirmation" not in data:
        data["needs_confirmation"] = False
    return data

# ----------------------------------------------------------------------
# Public API: get_ai_response (used by dm_chat_handler)
# ----------------------------------------------------------------------
def get_ai_response(prompt_or_message: str, session: Any, game_context: Dict[str, Any]) -> str:
    """
    Unified entry point for AI responses.
    - If the first argument is a long structured prompt (contains "Respond in JSON"), it is used directly.
    - Otherwise, it's treated as a player message and generate_response is called.
    Returns a JSON string.
    """
    # Heuristic: if the prompt contains the word "JSON" and "Respond in", treat as custom prompt
    if "Respond in JSON" in prompt_or_message or "JSON object" in prompt_or_message:
        # It's a custom prompt (e.g., from topic extraction)
        data = _llm_json_response(prompt_or_message)
    else:
        # It's a player message
        data = generate_response(prompt_or_message, session, game_context)
    return json.dumps(data)

# ----------------------------------------------------------------------
# Compatibility class for legacy code
# ----------------------------------------------------------------------
class DMChatAI:
    """Wrapper to maintain backward compatibility with world_controller.py."""
    def __init__(self, *args, **kwargs):
        pass

    def generate_response(self, message, session, game_context):
        return generate_response(message, session, game_context)

    def extract_topic(self, message, game_context):
        return extract_topic(message, game_context)

# ----------------------------------------------------------------------
# Explicit exports
# ----------------------------------------------------------------------
__all__ = [
    "get_ai_response",
    "generate_response",
    "extract_topic",
    "DMChatAI"
]