# world/context_builder.py
import logging
from typing import Dict, List, Optional, Set

from world.event_log import Event, get_event_log
from world.escalation_engine import EscalationEngine

logger = logging.getLogger(__name__)

# Configuration constants
MAX_SCAN = 1000          # maximum number of events to scan backwards
SALIENT_LIMIT = 20       # number of salient events to collect


class ContextBuilder:
    def __init__(self, world_controller, escalation_engine: EscalationEngine):
        self.world = world_controller
        self.event_log = get_event_log()
        self.escalation = escalation_engine

    def build(self, session_id: str) -> dict:
        """
        Build a UnifiedContext dictionary for the given session.
        Returns a dict with sections: visible_entities, environment, awareness,
        salient_events, knowledge_gaps, encounter_context, combat_context, escalation_context.
        """
        character = self.world._get_active_character(session_id)
        if not character:
            logger.warning(f"No active character for session {session_id}, returning empty context")
            return self._empty_context()

        # 1. compute visible entities (simplified for v1)
        visible_ids, hidden_ids, partially_ids = self._compute_visibility(character)

        # 2. collect salient events
        salient_events = self._get_salient_events(visible_ids, character.id)

        # 3. environment and awareness
        environment = self._get_environment()
        awareness = self._get_awareness(character, visible_ids)

        # 4. knowledge gaps
        knowledge_gaps = self._get_knowledge_gaps(visible_ids, hidden_ids, partially_ids)

        # 5. active encounter/combat context (if any)
        encounter_ctx = self._get_encounter_context(session_id)
        combat_ctx = self._get_combat_context(session_id)

        # 6. escalation context (active effects)
        escalation_ctx = self.escalation.get_active_effects()

        return {
            "timestamp": self._get_timestamp(),
            "visible_entities": [self._entity_to_dict(eid) for eid in visible_ids],
            "hidden_entities": [self._entity_to_dict(eid) for eid in hidden_ids],
            "partially_known_entities": [self._entity_to_dict(eid) for eid in partially_ids],
            "environment": environment,
            "awareness": awareness,
            "salient_events": salient_events,
            "knowledge_gaps": knowledge_gaps,
            "encounter_context": encounter_ctx,
            "combat_context": combat_ctx,
            "escalation_context": escalation_ctx,
        }

    # ------------------------------------------------------------------
    # Helper methods (private – implement as needed)
    # ------------------------------------------------------------------
    def _compute_visibility(self, character) -> tuple:
        """Return three sets: visible_ids, hidden_ids, partially_known_ids."""
        # Placeholder – in v1, assume all entities in same location are visible.
        # Later, incorporate lighting, stealth, darkvision, etc.
        location = getattr(self.world, 'current_location', None)
        if not location:
            return set(), set(), set()
        # Get all entity IDs in current location (simplified)
        # This depends on how your world controller tracks entities
        all_ids = set()
        # For now, return empty sets – will be filled when integrated with real world.
        return set(), set(), set()

    def _entity_to_dict(self, entity_id: str) -> dict:
        """Return a dict representation of an entity (id, type, name, etc.)."""
        # Implementation depends on your entity data model.
        # For v1, return minimal dict.
        return {"id": entity_id, "type": "unknown", "name": "Unknown"}

    def _get_salient_events(self, visible_ids: Set[str], character_id: str) -> List[dict]:
        """Backward scan the event log, collect salient events up to SALIENT_LIMIT."""
        all_events = self.event_log.get_all_events()   # full history
        salient = []
        for event in reversed(all_events):   # newest first
            if len(salient) >= SALIENT_LIMIT:
                break
            if self._is_salient(event, visible_ids, character_id):
                salient.append(self._event_to_dict(event))
        return list(reversed(salient))   # chronological order

    def _is_salient(self, event: Event, visible_ids: Set[str], character_id: str) -> bool:
        # Rule: actor is the player
        if event.actor_id == character_id:
            return True
        # Rule: source system is always relevant
        if event.source_system in {'perception', 'sound', 'combat', 'escalation', 'encounter'}:
            return True
        # Rule: involves a visible entity (using entity reference convention)
        ids = set()
        if hasattr(event.data, 'entity_id'):
            ids.add(event.data.entity_id)
        if hasattr(event.data, 'target_id'):
            ids.add(event.data.target_id)
        if hasattr(event.data, 'involved_entities'):
            ids.update(event.data.involved_entities)
        return not ids.isdisjoint(visible_ids)

    def _event_to_dict(self, event: Event) -> dict:
        """Convert Event to a plain dict (serializable)."""
        return {
            "type": event.type,
            "data": dict(event.data) if hasattr(event.data, 'items') else event.data,
            "source_system": event.source_system,
            "actor_id": event.actor_id,
            "depth": event.depth,
            "timestamp": event.timestamp,
        }

    def _get_environment(self) -> dict:
        """Return environment dict: location, terrain, lighting, sound, weather."""
        location = getattr(self.world, 'current_location', None)
        if location:
            return {
                "location": getattr(location, 'name', 'Unknown'),
                "terrain": getattr(location, 'terrain', 'unknown'),
                "lighting": 1.0,   # placeholder
                "sound_level": 0.0,
                "weather": "clear",
            }
        return {"location": "Unknown", "terrain": "unknown", "lighting": 1.0, "sound_level": 0.0, "weather": "clear"}

    def _get_awareness(self, character, visible_ids: Set[str]) -> dict:
        """Return awareness dict: known threats, allies, unknown threat signals."""
        # Placeholder – future: compute from faction standings, perception checks, etc.
        return {
            "known_threats": [],
            "known_allies": [],
            "unknown_threat_signals": [],
        }

    def _get_knowledge_gaps(self, visible_ids, hidden_ids, partially_ids) -> dict:
        """Return knowledge gaps dict."""
        return {
            "unidentified_entities": list(partially_ids),
            "unknown_sounds": [],
        }

    def _get_encounter_context(self, session_id: str) -> dict:
        """Query active EncounterFSM for context."""
        # This will be implemented when encounter system is built.
        return {}

    def _get_combat_context(self, session_id: str) -> dict:
        """Query active CombatFSM for context."""
        return {}

    def _get_timestamp(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _empty_context(self) -> dict:
        """Return an empty context when no character is available."""
        return {
            "timestamp": self._get_timestamp(),
            "visible_entities": [],
            "hidden_entities": [],
            "partially_known_entities": [],
            "environment": {},
            "awareness": {},
            "salient_events": [],
            "knowledge_gaps": {},
            "encounter_context": {},
            "combat_context": {},
            "escalation_context": [],
        }