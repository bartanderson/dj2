# world/escalation_engine.py
import fnmatch
import re
import logging
import copy
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import yaml
from simpleeval import simple_eval

from world.event_log import Event, AttrDict, get_event_log

logger = logging.getLogger(__name__)

MAX_DEPTH = 10


class DotDict(dict):
    """Allows dot‑access to dict keys. Used only for evaluation context."""
    def __getattr__(self, item):
        try:
            value = self[item]
        except KeyError:
            raise AttributeError(item)
        return value
    def __setattr__(self, key, value):
        self[key] = value


class EscalationEngine:
    def __init__(self, world_controller):
        self.world = world_controller
        self.rules = []
        self.action_registry = {}
        self.active_effects = []

    # ------------------------------------------------------------------
    # Rule Loading
    # ------------------------------------------------------------------
    def load_rules(self, yaml_path: str) -> None:
        with open(yaml_path, 'r') as f:
            rules_data = yaml.safe_load(f)
        if not isinstance(rules_data, dict) or 'rules' not in rules_data:
            raise ValueError("Invalid rules file: missing top-level 'rules' key")
        self.rules = []
        for rule in rules_data['rules']:
            pattern = rule.get('event_pattern')
            if not pattern:
                raise ValueError(f"Rule missing 'event_pattern': {rule}")
            rule['_compiled'] = re.compile(fnmatch.translate(pattern))
            self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.get('priority', 0))

    # ------------------------------------------------------------------
    # Action Registry
    # ------------------------------------------------------------------
    def register_action(self, name: str, func: Callable[[Event, dict], None]) -> None:
        self.action_registry[name] = func

    # ------------------------------------------------------------------
    # Event Processing
    # ------------------------------------------------------------------
    def process_event(self, event: Event) -> None:
        if event.depth >= MAX_DEPTH:
            logger.warning(f"Event depth {event.depth} exceeded limit, discarding: {event.type}")
            return

        world_facade = self._get_world_facade()

        for rule in self.rules:
            if not rule['_compiled'].fullmatch(event.type):
                continue
            # Evaluate conditions
            conditions_ok = True
            for cond in rule.get('conditions', []):
                if not self._eval_condition(cond, event, world_facade):
                    conditions_ok = False
                    break
            if not conditions_ok:
                continue
            # Execute actions
            for action_def in rule.get('actions', []):
                action_name = action_def.get('name')
                params = action_def.get('params', {})
                func = self.action_registry.get(action_name)
                if func:
                    try:
                        func(event, params)
                    except Exception as e:
                        logger.error(f"Error executing escalation action '{action_name}': {e}", exc_info=True)
                else:
                    logger.error(f"Unknown escalation action: {action_name}")
            if rule.get('stop_on_match', False):
                break

    # ------------------------------------------------------------------
    # Evaluation Helpers
    # ------------------------------------------------------------------
    def _event_to_eval_dict(self, event: Event) -> DotDict:
        """Convert Event to a DotDict for simpleeval dot‑access."""
        return DotDict({
            "type": event.type,
            "data": event.data,          # event.data is AttrDict, which already supports dot‑access
            "source_system": event.source_system,
            "actor_id": event.actor_id,
            "depth": event.depth,
            "timestamp": event.timestamp,
        })

    def _eval_condition(self, expr: str, event: Event, world: Dict) -> bool:
        eval_event = self._event_to_eval_dict(event)
        context = {
            'event': eval_event,
            'world': world,
        }
        try:
            result = simple_eval(expr, functions={}, names=context)   # operators allowed by default
            return bool(result)
        except Exception as e:
            logger.warning(f"Condition evaluation failed: {expr} – {e}")
            return False

    def _get_world_facade(self) -> Dict:
        location = getattr(self.world, 'current_location', None)
        if location:
            location_info = {
                'terrain': getattr(location, 'terrain', None),
                'name': getattr(location, 'name', None),
            }
        else:
            location_info = {}
        return {
            'current_location': location_info,
            'get_faction_standing': (
                lambda fid: self.world.campaign_state.get_faction_standing(fid)
                if hasattr(self.world, 'campaign_state') else 0
            ),
        }

    # ------------------------------------------------------------------
    # Effect Management
    # ------------------------------------------------------------------
    def add_effect(self, effect: Dict) -> None:
        required = {"id", "type", "source_event", "expires_at", "data"}
        if not required.issubset(effect):
            raise ValueError(f"Invalid effect structure: missing keys {required - effect.keys()}")
        self.active_effects.append(effect)

    def remove_effect(self, effect_id: str) -> None:
        self.active_effects = [e for e in self.active_effects if e['id'] != effect_id]

    def get_active_effects(self) -> List[Dict]:
        self.prune_effects()
        return copy.deepcopy(self.active_effects)

    def prune_effects(self) -> None:
        now = datetime.now(timezone.utc)
        self.active_effects = [e for e in self.active_effects
                               if e.get('expires_at') is None or e['expires_at'] > now.isoformat()]

    # ------------------------------------------------------------------
    # Helper Event Emission
    # ------------------------------------------------------------------
    @staticmethod
    def emit_event(parent_event: Event, event_type: str, data: dict,
                   source_system: str = "escalation_engine",
                   actor_id: Optional[str] = None) -> None:
        get_event_log().emit(
            event_type,
            data,
            source_system,
            actor_id,
            depth=parent_event.depth + 1
        )