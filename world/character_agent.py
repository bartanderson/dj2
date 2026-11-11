# world/character_agent.py
import json
import logging
import copy
from typing import Dict, Any, Tuple

from world import dnd_data
from world.character_templates import render_templates_for_prompt

logger = logging.getLogger(__name__)

DEFAULT_DRAFT = {
    "name": None,
    "race": None,
    "class": None,
    "background": None,
    "abilities": {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10},
    "skills": [],
    "ideals": None,
    "bonds": None,
    "flaws": None,
    "description": None,
    "status": "in_progress",
}


class CharacterAgent:
    def __init__(self, chat_ai, world_context: Dict[str, Any] = None):
        """
        world_context: optional dict with keys like 'locations', 'factions', 'regions'
                       to give the DM ambient world knowledge.
        """
        self.chat_ai = chat_ai
        self.world_context = world_context or {}

    def process_turn(
        self, player_message: str, draft: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], str, bool]:
        """
        Returns: (updated_draft, dm_response_text, ready_to_build)
        """
        # Base rule data
        races = ", ".join(dnd_data.get_race_list())
        classes = ", ".join(dnd_data.get_class_list())
        backgrounds = ", ".join(dnd_data.get_background_list())
        skills = ", ".join(dnd_data.get_skill_list())

        # Ambient world knowledge (optional)
        world_blurb = ""
        if self.world_context:
            locs = self.world_context.get("locations") or []
            if locs:
                world_blurb += f"\nNamed places in this world you may reference: {', '.join(locs[:15])}"
            facts = self.world_context.get("factions") or []
            if facts:
                world_blurb += f"\nFactions/peoples of this world: {', '.join(facts[:10])}"

        topics = render_templates_for_prompt()

        system_prompt = f"""You are a wise, warm Dungeon Master, guiding a player through the creation of their character through natural conversation.

You are NOT a form. You do NOT march through a checklist. You follow the player's lead.

## The Draft (your notepad)
This is what you know so far. Update it as the player reveals things. Do not force fields to be filled — let them emerge.
{json.dumps(draft, indent=2)}

## Topic templates (your prep notes)
These are topics you MAY explore. Use them as inspiration, not as a script. Do not ask about a topic the player hasn't touched unless the conversation naturally invites it.
{topics}

## What you must remember
- The world's valid options are: Races [{races}], Classes [{classes}], Backgrounds [{backgrounds}], Skills [{skills}].{world_blurb}
- If the player describes something that implies a race/class, say so and confirm it warmly ("A mountain dwarf — that sounds right for someone who speaks of stone the way you do. Does that fit?"). Do NOT silently assign it.
- If the player is joking or ambiguous ("make him a unicorn lol"), do NOT write it to the Draft. Laugh with them and ask warmly ("A unicorn! I don't think we have those here — did you mean something else, or were you picturing a horse that thinks very highly of itself?").
- If the player asks a rules/lore question ("what's good for healing?"), answer it, then gently return to them ("Does any of that speak to you?").
- If the player says "surprise me" or "you pick," you MAY roll for abilities and propose a random concept, but still confirm before committing.
- If the player says "just give me the numbers" or "I don't care about story," respect it: ask for the mechanical pieces quickly and skip the narrative topics.
- Each turn, ask AT MOST ONE question. Never chain questions.

## Finalizing
When the draft has: name, race, class, and background (or the player has explicitly said they're happy with a minimal character), AND the player has confirmed — set ready_to_build to true. Until then, keep conversing.

## Output format (STRICT)
Return ONLY a JSON object:
{{
  "updated_draft": {{ ...the full updated draft with any new info... }},
  "dm_response": "Your reply here.",
  "ready_to_build": false
}}
"""

        try:
            ai_data = self.chat_ai.json_response(
                system_prompt + f"\n\nPlayer says: {player_message}"
            )

            updated_draft = ai_data.get("updated_draft", draft)
            dm_response = ai_data.get(
                "dm_response", "I'm listening — tell me more?"
            )
            ready_to_build = bool(ai_data.get("ready_to_build", False))

            # Validate
            updated_draft = self._validate_draft(updated_draft)

            # If validation stripped a required field that the AI thought was set,
            # don't let ready_to_build pass — the player will need to clarify.
            if ready_to_build and not self._is_buildable(updated_draft):
                ready_to_build = False

            return updated_draft, dm_response, ready_to_build

        except Exception as e:
            logger.error(f"CharacterAgent failed: {e}")
            return draft, "Forgive me — I lost the thread for a moment. Where were we?", False

    def _is_buildable(self, draft: Dict[str, Any]) -> bool:
        """Checks whether the draft has the minimum viable fields to build."""
        return bool(
            draft.get("name")
            and draft.get("race")
            and draft.get("class")
            and draft.get("background")
        )

    def _validate_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitizes the LLM's output against actual dnd_data. Never invents."""
        if not isinstance(draft, dict):
            return copy.deepcopy(DEFAULT_DRAFT)

        for key, default in DEFAULT_DRAFT.items():
            if key not in draft:
                draft[key] = copy.deepcopy(default)

        # Race
        if draft.get("race") and not dnd_data.validate_race(draft["race"]):
            logger.warning(f"Rejected invalid race from LLM: {draft['race']}")
            draft["race"] = None

        # Class
        if draft.get("class") and not dnd_data.validate_class(draft["class"]):
            logger.warning(f"Rejected invalid class from LLM: {draft['class']}")
            draft["class"] = None

        # Background
        valid_bgs = [b.lower() for b in dnd_data.get_background_list()]
        if draft.get("background"):
            if draft["background"].lower() not in valid_bgs and draft["background"].lower() != "unknown":
                logger.warning(f"Rejected invalid background from LLM: {draft['background']}")
                draft["background"] = None

        # Skills
        valid_skills = {s.lower(): s for s in dnd_data.get_skill_list()}
        if isinstance(draft.get("skills"), list):
            cleaned = []
            for s in draft["skills"]:
                key = str(s).lower()
                if key in valid_skills:
                    cleaned.append(valid_skills[key])
                else:
                    logger.warning(f"Rejected invalid skill from LLM: {s}")
            draft["skills"] = cleaned
        else:
            draft["skills"] = []

        # Abilities
        if not isinstance(draft.get("abilities"), dict):
            draft["abilities"] = copy.deepcopy(DEFAULT_DRAFT["abilities"])
        else:
            for ab in ("STR", "DEX", "CON", "INT", "WIS", "CHA"):
                try:
                    val = int(draft["abilities"].get(ab, 10))
                    draft["abilities"][ab] = max(3, min(18, val))
                except (ValueError, TypeError):
                    draft["abilities"][ab] = 10

        return draft