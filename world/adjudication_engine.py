import random
from typing import Dict, Any, Optional
from dataclasses import dataclass

from world.intent import IntentFrame
from world.event_log import get_event_log
from world.escalation_engine import EscalationEngine
from world.context_builder import ContextBuilder
from world.entity_resolver import EntityResolver
from world.input_parser import parse_player_input
from world.fsm.generic_fsm import GenericFSM
from world.fsm import builtins
from difflib import get_close_matches

DEBUG = True

# ----------------------------------------------------------------------
# Transaction Configuration (for generic handler)
# ----------------------------------------------------------------------
@dataclass
class TransactionConfig:
    name: str
    json_path: str
    get_item_from_merchant: bool
    price_func: callable
    guard_registry: dict
    action_registry: dict
    context_updates: dict = None
    is_barter: bool = False


class AdjudicationEngine:
    def __init__(self, world_controller):
        self.world = world_controller
        self.event_log = get_event_log()
        self.conversations: Dict[str, Dict] = {}
        self.active_fsms = {}
        self.entity_resolver = EntityResolver()
        self.event_log = get_event_log()
        self.escalation = EscalationEngine(self.event_log, world_controller)
        self.escalation.load_rules("config/escalation_rules.yaml")   # create this file
        self.escalation.register_action("log_buy", self._log_buy_action)
        self._escalation_subscription = self.event_log.on_any(self.escalation.process_event)
        self.event_log.on_any(self.escalation.process_event)
        self.context_builder = ContextBuilder(world_controller, self.event_log, self.escalation)
        # Transaction configurations (buy, sell, barter)
        self.buy_config = TransactionConfig(
            name='buy',
            json_path='config/fsms/buy.json',
            get_item_from_merchant=True,
            price_func=lambda item, merchant, rel, ctx: self.world._compute_price(item, merchant, rel, ctx),
            guard_registry={'price_too_low': builtins.price_lt, 'price_acceptable': builtins.price_ge},
            action_registry={'store_offer': builtins.store_offer, 'execute_purchase': builtins.execute_purchase},
        )
        self.sell_config = TransactionConfig(
            name='sell',
            json_path='config/fsms/sell.json',
            get_item_from_merchant=False,
            price_func=lambda item, merchant, rel, ctx: self._compute_sell_price(item, merchant, rel),
            guard_registry={'offer_too_high': builtins.offer_gt, 'offer_acceptable': builtins.offer_le},
            action_registry={'store_offer': builtins.store_offer, 'execute_sell': builtins.execute_sell},
        )
        self.barter_config = TransactionConfig(
            name='barter',
            json_path='config/fsms/barter.json',
            get_item_from_merchant=False,
            price_func=lambda item, merchant, rel, ctx: self._compute_sell_price(item, merchant, rel),
            guard_registry={'need_more_gold': builtins.need_more_gold, 'offer_acceptable': builtins.shortage_met},
            action_registry={'add_gold': builtins.add_gold, 'execute_barter': builtins.execute_barter},
            is_barter=True,
        )
        self.escalation.register_action("log_buy", self._log_buy_action)

    def _log_buy_action(self, event, params):
        print(f"Buy event logged: {event.data.item}")

    # ------------------------------------------------------------------
    # Helper: start a generic FSM and store it
    # ------------------------------------------------------------------
    def _start_fsm(self, session_id: str, json_path: str, context: dict,
                   guard_registry: dict, action_registry: dict) -> dict:
        """Create a GenericFSM, store it, and return the initial prompt."""
        context['_guard_registry'] = guard_registry
        context['_action_registry'] = action_registry
        fsm = GenericFSM(json_path, context)
        self.active_fsms[session_id] = fsm
        return {"success": False, "message": fsm.get_prompt()}

    # ------------------------------------------------------------------
    # Generic transaction handler (buy, sell, barter)
    # ------------------------------------------------------------------
    def _handle_transaction(self, frame: IntentFrame, session_id: str, config: TransactionConfig) -> dict:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}

        # --- BARTER ---
        if config.is_barter:
            give_name = frame.item or frame.target
            want_name = frame.target if frame.item else None
            if frame.item and frame.target:
                give_name = frame.item
                want_name = frame.target
            if not want_name:
                return {"success": False, "message": "Barter requires both what you give and what you want."}

            # resolve give item (player inventory)
            inv_names = [i.name.lower() for i in char.inventory]
            matches = get_close_matches(give_name.lower(), inv_names, n=1, cutoff=0.6)
            if not matches:
                available = ", ".join([i.name for i in char.inventory[:5]])
                return {"success": False, "message": f"You don't have '{give_name}'. You have: {available}."}
            give_item = next(i for i in char.inventory if i.name.lower() == matches[0])

            # resolve want item (merchant inventory)
            self.entity_resolver.load_merchant_items(merchant)
            want_item = self.entity_resolver.resolve_item(want_name)
            if not want_item:
                available = ", ".join([i.name for i in merchant.inventory[:5]])
                return {"success": False, "message": f"{merchant.name} doesn't have '{want_name}'. They have: {available}."}

            rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
            if not self.world._is_item_visible(want_item, rel):
                return {"success": False, "message": f"You don't see '{want_item.name}' in the {merchant.display_name}."}

            give_value = self._compute_sell_price(give_item, merchant, rel)
            want_value = self.world._compute_price(want_item, merchant, rel, frame.context)
            shortage = want_value - give_value

            if shortage <= 0:
                self._execute_barter(char, merchant, give_item, want_item, 0)
                return {"success": True, "message": f"You bartered your {give_item.name} for {want_item.name}.", "action": "refresh_inventory"}

            context = {
                'give_item': give_item.name,
                'receive_item': want_item.name,
                'give_value': give_value,
                'receive_value': want_value,
                'shortage': shortage,
                'character': char,
                'merchant': merchant,
                'give_item_obj': give_item,
                'receive_item_obj': want_item,
                'engine': self,
            }
            if config.context_updates:
                context.update(config.context_updates)
            return self._start_fsm(session_id, config.json_path, context,
                                   config.guard_registry, config.action_registry)

        # --- BUY / SELL (non-barter) ---
        item_name = frame.item or frame.target
        if not item_name:
            return {"success": False, "message": f"What item do you want to {config.name}?"}

        if config.get_item_from_merchant:
            self.entity_resolver.load_merchant_items(merchant)
            item = self.entity_resolver.resolve_item(item_name)
            if not item:
                available = ", ".join([i.name for i in merchant.inventory[:5]])
                return {"success": False, "message": f"I don't have '{item_name}'. I have: {available}."}
        else:
            inv_names = [i.name.lower() for i in char.inventory]
            matches = get_close_matches(item_name.lower(), inv_names, n=1, cutoff=0.6)
            if not matches:
                available = ", ".join([i.name for i in char.inventory[:5]])
                return {"success": False, "message": f"You don't have '{item_name}'. You have: {available}."}
            item = next(i for i in char.inventory if i.name.lower() == matches[0])

        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        price = config.price_func(item, merchant, rel, frame.context) if callable(config.price_func) else config.price_func

        context = {
            'item_name': item.name,
            ('current_price' if config.name == 'buy' else 'merchant_price'): price,
            'character': char,
            'merchant': merchant,
            'item': item,
            'engine': self,
        }
        if config.context_updates:
            context.update(config.context_updates)

        return self._start_fsm(session_id, config.json_path, context,
                               config.guard_registry, config.action_registry)

    # ------------------------------------------------------------------
    # Process method (handles active FSMs and normal routing)
    # ------------------------------------------------------------------
    def process(self, frame: IntentFrame, session_id: Optional[str] = None) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] AdjudicationEngine.process: action={frame.action}, category={frame.category}, target={frame.target}, item={frame.item}, price={frame.price}")

        # Active FSM handling (generic)
        if session_id and session_id in self.active_fsms:
            fsm = self.active_fsms[session_id]
            canonical_event, event_data = parse_player_input(frame.raw_text)
            # Use event_map if the FSM provides one (for GenericFSM, we have to simulate)
            # Since GenericFSM does not have event_map, we rely on send_event.
            # We'll unify by using send_event directly.
            event_name = None
            if canonical_event == 'CONFIRM':
                event_name = 'confirm'
            elif canonical_event == 'NUMBER':
                event_name = 'offer'
            elif canonical_event == 'CANCEL':
                event_name = 'cancel'
            elif canonical_event == 'FIGHT':
                event_name = 'fight'
            elif canonical_event == 'FLEE':
                event_name = 'flee'
            elif canonical_event == 'PARLEY':
                event_name = 'parley'
            elif canonical_event == 'RAW':
                # If raw text is exactly the event name, use it (for custom events)
                event_name = event_data.get('text')
            if event_name:
                try:
                    # Send the event via send_event (which calls the state machine's method)
                    fsm.send_event(event_name, event_data if canonical_event == 'NUMBER' else None)
                    if fsm.is_completed:
                        del self.active_fsms[session_id]
                        return {"success": True, "message": fsm.get_prompt(), "action": "refresh_inventory"}
                    else:
                        return {"success": False, "message": fsm.get_prompt()}
                except Exception as e:
                    del self.active_fsms[session_id]
                    return {"success": False, "message": f"FSM error: {e}"}
            else:
                del self.active_fsms[session_id]
                return {"success": False, "message": "Interaction cancelled."}

        # Normal category routing
        if DEBUG:
            print(f"category value: '{frame.category}'")
        if frame.category == "movement":
            return self._handle_move(frame, session_id)
        elif frame.category == "economy":
            return self._handle_economy(frame, session_id)
        elif frame.category == "social":
            return self._handle_social(frame, session_id)
        elif frame.category == "exploration":
            return self._handle_exploration(frame, session_id)
        else:
            self.event_log.emit("category.missing", {"category": frame.category, "action": frame.action}, source="adjudication")
            return {"success": False, "message": f"Unhandled category: {frame.category}", "action": None}

    # ------------------------------------------------------------------
    # Economy router – uses generic transaction handlers
    # ------------------------------------------------------------------
    def _handle_economy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_economy: action={frame.action}, item={frame.item}, price={frame.price}")
        canonical = self._normalize_action(frame.action, frame.raw_text)
        if canonical == "buy":
            return self._handle_transaction(frame, session_id, self.buy_config)
        elif canonical == "sell":
            return self._handle_transaction(frame, session_id, self.sell_config)
        elif canonical == "barter":
            return self._handle_transaction(frame, session_id, self.barter_config)
        elif canonical == "haggle":
            return self._handle_haggle(frame, session_id)
        else:
            return {"success": False, "message": f"Unknown economic action: {canonical}"}

    # ------------------------------------------------------------------
    # Normalise action (synonyms mapping)
    # ------------------------------------------------------------------
    def _normalize_action(self, action: str, raw_text: str) -> str:
        action_lower = action.lower()
        if action_lower in ("buy","purchase","offer","bid","pay","get","acquire"):
            return "buy"
        if action_lower in ("sell","dispose","trade","pawn","vend"):
            return "sell"
        if action_lower in ("haggle","negotiate","bargain","dicker"):
            return "haggle"
        if action_lower in ("barter","swap","exchange"):
            return "barter"
        text = raw_text.lower()
        if any(w in text for w in ("barter","swap","exchange")):
            return "barter"
        if any(w in text for w in ("buy","purchase","offer","bid","pay","get","acquire")):
            return "buy"
        if any(w in text for w in ("sell","trade","pawn","vend","dispose")):
            return "sell"
        if any(w in text for w in ("haggle","negotiate","bargain","dicker")):
            return "haggle"
        return action

    # ------------------------------------------------------------------
    # Movement handler
    # ------------------------------------------------------------------
    def _handle_move(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print("[DEBUG] _handle_move called")
        direction = frame.destination or frame.target
        if not direction:
            return {"success": False, "message": "No direction specified.", "action": None}

        dir_map = {
            "north": "n", "south": "s", "east": "e", "west": "w",
            "northeast": "ne", "northwest": "nw",
            "southeast": "se", "southwest": "sw"
        }
        short_dir = dir_map.get(direction.lower(), direction)
        result = self.world.move_hex(short_dir)

        if result is None:
            result = {"success": False, "message": "Movement failed (no result).", "action": None}
        elif not isinstance(result, dict):
            result = {"success": False, "message": "Invalid movement result.", "action": None}
        else:
            if result.get("success"):
                self.world.emit_party_moved(result.get('new_col'), result.get('new_row'), session_id)
                result["action"] = "centerOnParty"
                result["map_data"] = self.world.get_map_data()
        return result

    # ------------------------------------------------------------------
    # Social stub
    # ------------------------------------------------------------------
    def _handle_social(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_social: action={frame.action}, target={frame.target}, motivation={frame.motivation}")
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        target = frame.target or "someone"
        return {
            "success": True,
            "message": f"You try to {frame.action}. {target} seems {random.choice(['unconvinced', 'interested', 'suspicious'])}.",
            "action": None
        }

    # ------------------------------------------------------------------
    # Exploration handler (look, examine, etc.)
    # ------------------------------------------------------------------
    def _handle_exploration(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_exploration: action={frame.action}, destination={frame.destination or frame.target}")

        action_lower = frame.action.lower()
        if action_lower in ("look", "examine", "inspect", "search"):
            return self._handle_look(frame, session_id)
        if action_lower == "move" and frame.destination:
            return self._handle_move(frame, session_id)
        return {"success": False, "message": f"I don't know how to '{frame.action}' in exploration.", "action": None}

    # ------------------------------------------------------------------
    # Look handler (including merchant display)
    # ------------------------------------------------------------------
    def _handle_look(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character.", "action": None}

        target = frame.target or frame.item
        location = self.world.current_location
        merchant = None
        if location and location.merchant_id:
            merchant = self.world.campaign_state.get_merchant(location.merchant_id)

        # No target – describe area
        if not target:
            parts = []
            if location:
                parts.append(f"You are at {location.name}.")
            else:
                parts.append("You are in the wilderness.")

            col, row = self.world.campaign_state.party_position
            hex_data = self.world.campaign_state.get_hex(col, row)
            if hex_data:
                terrain = hex_data.get('terrain', 'unknown terrain')
                parts.append(f"The terrain is {terrain}.")
                pois = hex_data.get('pois', [])
                discovered_pois = [p['name'] for p in pois if p.get('discovered')]
                if discovered_pois:
                    parts.append(f"You see: {', '.join(discovered_pois)}.")
            if merchant:
                parts.append(f"{merchant.name} the merchant is here, standing near {merchant.display_name}.")
            return {"success": True, "message": " ".join(parts), "action": None}

        # Target is merchant's display
        if merchant and target.lower() == merchant.display_name.lower():
            rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
            visible_items = []
            for item in merchant.inventory:
                if self.world._is_item_visible(item, rel):
                    visible_items.append(f"{item.name} ({item.base_price} gp)")
            if visible_items:
                msg = f"{merchant.name}'s {merchant.display_name} contains: {', '.join(visible_items)}."
            else:
                msg = f"{merchant.name}'s {merchant.display_name} appears empty, or you don't see anything of interest."
            return {"success": True, "message": msg, "action": None}

        # Target is merchant (NPC)
        if merchant and (target.lower() == merchant.name.lower() or target.lower() == "merchant"):
            return {"success": True, "message": f"{merchant.name} the merchant stands by his {merchant.display_name}.", "action": None}

        # Generic fallback
        return {"success": True, "message": f"You look at {target} but see nothing special.", "action": None}

    # ------------------------------------------------------------------
    # Haggle (stub)
    # ------------------------------------------------------------------
    def _handle_haggle(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        item_name = frame.target
        if not item_name:
            return {"success": False, "message": "No item specified."}
        offered_price = frame.price
        if not offered_price:
            return {"success": False, "message": "No price offered."}
        result = self.world.merchant_haggle(item_name, offered_price)
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "action": result.get("action")
        }

    # ------------------------------------------------------------------
    # Price helpers
    # ------------------------------------------------------------------
    def _compute_sell_price(self, item, merchant, rel):
        base_price = item.cost if hasattr(item, 'cost') else 10
        multiplier = 1.0
        multiplier -= (merchant.personality.greed - 5) * 0.05
        multiplier += rel.affinity * 0.03
        multiplier += rel.trust * 0.02
        multiplier -= rel.fear * 0.04
        multiplier = max(0.2, min(1.0, multiplier))
        return max(1, int(base_price * multiplier))

    # ------------------------------------------------------------------
    # Transaction execution helpers (used by builtins)
    # ------------------------------------------------------------------
    def _execute_purchase(self, character, merchant, item, price):
        if character.currency < price:
            return False
        character.currency -= price
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=item.name,
            description=f"Bought from {merchant.name}",
            type=item.tags.pop() if item.tags else "adventuring_gear",
            cost=price
        )
        character.inventory.append(new_item)
        self.world.campaign_state.update_merchant_relationship(merchant.id, character.id, affinity_delta=1)
        self.world.character_manager._save_character_to_db(character)
        self.event_log.emit(
            "economy.buy",
            {
                "item": item.name,
                "price": price,
                "character": character.id,
                "merchant": merchant.id,
                "entity_id": character.id,      # for salience
                "target_id": merchant.id
            },
            source_system="adjudication_engine",
            actor_id=character.id
        )
        return True

    def _execute_sell(self, character, merchant, item, price):
        character.currency += price
        if item in character.inventory:
            character.inventory.remove(item)
        self.world.campaign_state.update_merchant_relationship(merchant.id, character.id, trust_delta=1)
        self.world.character_manager._save_character_to_db(character)
        self.event_log.emit("economy.sell", {
            "item": item.name,
            "price": price,
            "character": character.id,
            "merchant": merchant.id
        }, source="adjudication_engine")

    def _execute_barter(self, character, merchant, give_item, receive_item, extra_gold):
        character.inventory.remove(give_item)
        if extra_gold > 0:
            character.currency -= extra_gold
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=receive_item.name,
            description=f"Bartered from {merchant.name}",
            type=receive_item.tags.pop() if receive_item.tags else "adventuring_gear",
            cost=receive_item.base_price
        )
        character.inventory.append(new_item)
        self.world.campaign_state.update_merchant_relationship(merchant.id, character.id, affinity_delta=2)
        self.world.character_manager._save_character_to_db(character)
        self.event_log.emit("economy.barter", {
            "give_item": give_item.name,
            "receive_item": receive_item.name,
            "extra_gold": extra_gold,
            "character": character.id,
            "merchant": merchant.id
        }, source="adjudication_engine")

    # ------------------------------------------------------------------
    # Encounter support
    # ------------------------------------------------------------------
    def start_encounter(self, session_id: str, encounter_data: dict) -> Dict[str, Any]:
        guard_reg = {
            'flee_possible': builtins.flee_possible,
            'parley_possible': builtins.parley_possible,
        }
        action_reg = {
            'start_combat': builtins.start_combat,
            'resolve_flee': builtins.resolve_flee,
            'resolve_parley': builtins.resolve_parley,
        }
        context = {
            'description': encounter_data.get('description', 'Something happens!'),
            'encounter_data': encounter_data,
            'engine': self,
            'session_id': session_id,
            '_guard_registry': guard_reg,   # <-- ADD THIS
            '_action_registry': action_reg, # <-- ADD THIS
        }
        fsm = GenericFSM('config/fsms/encounter.json', context)
        fsm.send_event('next')
        self.active_fsms[session_id] = fsm
        return {"success": False, "message": fsm.get_prompt()}