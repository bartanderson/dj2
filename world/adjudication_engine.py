import random
from typing import Dict, Any, Optional
from world.intent import IntentFrame
from flask_socketio import emit
from world.event_log import get_event_log
from difflib import get_close_matches


DEBUG = True   # set to False to reduce console output

class AdjudicationEngine:
    def __init__(self, world_controller):
        self.world = world_controller
        self.event_log = get_event_log()
        # Conversation state store for multi‑turn (e.g., haggling)
        self.conversations: Dict[str, Dict] = {}  # conversation_id -> state
        self.active_trades = {}

    def process(self, frame: IntentFrame, session_id: Optional[str] = None) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] AdjudicationEngine.process: action={frame.action}, category={frame.category}, target={frame.target}, item={frame.item}, price={frame.price}")

        # === New FSM (TradeMachine) handling ===
        if session_id and session_id in self.active_trades:
            fsm = self.active_trades[session_id]
            raw = frame.raw_text.lower().strip()
            if raw in ('yes', 'yeah', 'sure', 'ok', 'deal', 'accept', 'y'):
                try:
                    fsm.confirm()
                except Exception as e:
                    del self.active_trades[session_id]
                    return {"success": False, "message": f"Error: {e}"}
                if fsm.current_state.id == 'completed':
                    del self.active_trades[session_id]
                    return {"success": True, "message": "Purchase completed.", "action": "refresh_inventory"}
                else:
                    del self.active_trades[session_id]
                    return {"success": False, "message": "Trade cancelled."}
            elif raw.isdigit():
                price = int(raw)
                try:
                    fsm.offer(price)
                except Exception as e:
                    del self.active_trades[session_id]
                    return {"success": False, "message": f"Error: {e}"}
                if fsm.current_state.id == 'completed':
                    del self.active_trades[session_id]
                    return {"success": True, "message": "Purchase completed.", "action": "refresh_inventory"}
                else:
                    return {"success": False, "message": f"Offer too low. Current price {fsm.current_price} gp. Say 'yes' or offer again."}
            else:
                del self.active_trades[session_id]
                return {"success": False, "message": "Trade cancelled. What would you like to do?"}

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

        # Safety: ensure result is a dict
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

    def _handle_talk(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        target = frame.target or "someone"
        # For now, simple response. Later, can trigger AI conversation.
        return {
            "success": True,
            "message": f"You talk to {target}. They respond in a friendly manner.",
            "action": None
        }


    def _handle_buy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}

        item_name = frame.item or frame.target
        if not item_name:
            return {"success": False, "message": "What item do you want to buy?"}

        # Fuzzy match
        from difflib import get_close_matches
        inv_names = [i.name.lower() for i in merchant.inventory]
        matches = get_close_matches(item_name.lower(), inv_names, n=1, cutoff=0.6)
        if not matches:
            available = ", ".join([i.name for i in merchant.inventory[:5]])
            return {"success": False, "message": f"I don't have '{item_name}'. I have: {available}."}
        matched = matches[0]
        item = next(i for i in merchant.inventory if i.name.lower() == matched)

        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        price = self.world._compute_price(item, merchant, rel, frame.context)

        # Create FSM
        from world.fsm.trade_machine import TradeMachine
        fsm = TradeMachine(price, char, merchant, item, self)
        self.active_trades[session_id] = fsm
        return {"success": False, "message": f"{item.name} costs {price} gp. Say 'yes' or offer a price."}

    def _handle_sell(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        
        item_name = frame.item or frame.target
        if not item_name:
            return {"success": False, "message": "What item do you want to sell?"}
        
        def get_name(i):
            return i.name.lower() if hasattr(i, 'name') else i.get('name', '').lower()
        inv_names = [get_name(i) for i in char.inventory]
        matches = get_close_matches(item_name.lower(), inv_names, n=1, cutoff=0.6)
        if not matches:
            available = ", ".join([get_name(i) for i in char.inventory[:5]])
            return {"success": False, "message": f"You don't have '{item_name}'. You have: {available}."}
        matched = matches[0]
        item_obj = next(i for i in char.inventory if get_name(i) == matched)
        
        base_price = getattr(item_obj, 'cost', 10)
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        multiplier = 1.0
        multiplier -= (merchant.personality.greed - 5) * 0.05
        multiplier += rel.affinity * 0.03
        multiplier += rel.trust * 0.02
        multiplier -= rel.fear * 0.04
        multiplier = max(0.2, min(1.0, multiplier))
        price = max(1, int(base_price * multiplier))
                
        # Accept
        char.currency += offered
        char.inventory.remove(item_obj)
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1, trust_delta=1)
        self.world.character_manager._save_character_to_db(char)
        from world.event_log import get_event_log
        get_event_log().emit("economy.sell", {"item": matched, "price": offered, "character": char.id, "merchant": merchant.id})
        return {"success": True, "message": f"You sold {matched} for {offered} gp.", "action": "refresh_inventory"}

    def _handle_barter(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        if not merchant.constraints.barter_allowed:
            return {"success": False, "message": f"{merchant.name} doesn't barter."}
        
        give_name = frame.item or frame.target
        want_name = frame.target if frame.item else None
        if frame.item and frame.target:
            give_name = frame.item
            want_name = frame.target
        elif not want_name:
            return {"success": False, "message": "Barter requires both what you give and what you want."}
        
        def get_item_inv(inv, name):
            names = [i.name.lower() for i in inv]
            matches = get_close_matches(name.lower(), names, n=1, cutoff=0.6)
            if not matches:
                return None
            matched = matches[0]
            return next(i for i in inv if i.name.lower() == matched)
        
        give_item = get_item_inv(char.inventory, give_name)
        if not give_item:
            return {"success": False, "message": f"You don't have '{give_name}' to barter."}
        want_item = get_item_inv(merchant.inventory, want_name)
        if not want_item:
            available = ", ".join([i.name for i in merchant.inventory[:5]])
            return {"success": False, "message": f"{merchant.name} doesn't have '{want_name}'. They have: {available}."}
        
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        if not self.world._is_item_visible(want_item, rel):
            return {"success": False, "message": f"You don't see '{want_item.name}' in the {merchant.display_name}."}
        
        give_value = self._compute_sell_price(give_item, merchant, rel)
        want_value = self.world._compute_price(want_item, merchant, rel, frame.context)
        gold_diff = frame.price if frame.price else 0
        player_total = give_value + gold_diff
        merchant_total = want_value
                
        # Accept barter
        char.inventory.remove(give_item)
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=want_item.name,
            description=f"Bartered from {merchant.name}",
            type=want_item.tags.pop() if want_item.tags else "adventuring_gear",
            cost=want_item.base_price
        )
        char.inventory.append(new_item)
        if gold_diff > 0:
            if char.currency < gold_diff:
                char.inventory.append(give_item)
                char.inventory.remove(new_item)
                return {"success": False, "message": f"You don't have {gold_diff} gp to add."}
            char.currency -= gold_diff
        merchant.inventory.remove(want_item)
        # Optionally add give_item to merchant, but not needed for basic gameplay
        
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=2, trust_delta=1)
        self.world.character_manager._save_character_to_db(char)
        from world.event_log import get_event_log
        get_event_log().emit("economy.barter", {"give_item": give_item.name, "receive_item": want_item.name, "gold_diff": gold_diff, "character": char.id, "merchant": merchant.id})
        return {"success": True, "message": f"You bartered your {give_item.name} for {merchant.name}'s {want_item.name}.", "action": "refresh_inventory"}


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
        
        # Target is a location (if you have a world map)
        if hasattr(self.world, 'world_map') and self.world.world_map:
            for loc in self.world.world_map.locations.values():
                if getattr(loc, 'discovered', False) and loc.name.lower() == target.lower():
                    return {"success": True, "message": f"{loc.name}: {loc.description}", "action": None}
        
        # Generic fallback
        return {"success": True, "message": f"You look at {target} but see nothing special.", "action": None}

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
        offered_price = frame.currency
        if not offered_price:
            return {"success": False, "message": "No price offered."}
        # Use the merchant_haggle tool
        result = self.world.merchant_haggle(item_name, offered_price)
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "action": result.get("action")
        }

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
        # fallback to keyword scan
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

    def _handle_economy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_economy: action={frame.action}, item={frame.item}, price={frame.price}")
        
        canonical = self._normalize_action(frame.action, frame.raw_text)

        action = frame.action.lower()
        if action in ["buy", "purchase"]:
            # Call the existing _handle_buy method (already defined)
            return self._handle_buy(frame, session_id)
        elif action in ["sell", "dispose"]:
            return self._handle_sell(frame, session_id)
        elif action in ["haggle", "negotiate"]:
            return self._handle_haggle(frame, session_id)
        elif canonical == "barter":
            return self._handle_barter(frame, session_id)
        else:
            return {"success": False, "message": f"Unknown economic action: {action}"}


    def _handle_social(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_social: action={frame.action}, target={frame.target}, motivation={frame.motivation}")
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        target = frame.target or "someone"
        # Stub – will later include persuasion/intimidation skill checks and AI narrative
        return {
            "success": True,
            "message": f"You try to {frame.action}. {target} seems {random.choice(['unconvinced', 'interested', 'suspicious'])}.",
            "action": None
        }

    def _handle_exploration(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_exploration: action={frame.action}, destination={frame.destination or frame.target}")
        
        action_lower = frame.action.lower()
        # Handle look / examine
        if action_lower in ("look", "examine", "inspect", "search"):
            return self._handle_look(frame, session_id)
        
        # Handle movement within exploration (e.g., "go to the fountain")
        if action_lower == "move" and frame.destination:
            # Treat as movement (but you may have a separate movement handler)
            # For simplicity, pass to movement handler
            return self._handle_move(frame, session_id)
        
        # Other exploration actions (e.g., "search for traps", "listen")
        # You can add more specific handlers here
        return {"success": False, "message": f"I don't know how to '{frame.action}' in exploration.", "action": None}

    # Guards (return True/False)
    def _fsm_guard_price_too_low(self, event_data=None):
        offered = event_data.get('offer', 0) if event_data else 0
        current = self.context.get('current_price', 0)
        return offered < current

    def _fsm_guard_price_acceptable(self, event_data=None):
        offered = event_data.get('offer', 0) if event_data else 0
        current = self.context.get('current_price', 0)
        return offered >= current

    # Actions (update context or execute purchase)
    def _fsm_action_update_price(self, event_data=None):
        if event_data and 'offer' in event_data:
            self.context['offer'] = event_data['offer']
        return self.context

    def _fsm_action_execute_buy(self, event_data=None):
        # Get data from context
        char = self.context['character']
        merchant = self.context['merchant']
        item = self.context['item']
        price = event_data.get('offer', 0) if event_data else 0
        if not price:
            price = self.context.get('current_price', 0)
        engine = self.context['engine']   # <-- get the AdjudicationEngine instance

        if char.currency < price:
            return self.context

        char.currency -= price
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=item.name,
            description=f"Bought from {merchant.name}",
            type=item.tags.pop() if item.tags else "adventuring_gear",
            cost=price
        )
        char.inventory.append(new_item)

        # Use engine to update relationship and save
        engine.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1)
        engine.world.character_manager._save_character_to_db(char)

        from world.event_log import get_event_log
        get_event_log().emit("economy.buy", {
            "item": item.name,
            "price": price,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")
        return self.context

    def _execute_purchase(self, character, merchant, item, price):
        """Executes the actual purchase (gold deduction, inventory, relationships, events)."""
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
        from world.event_log import get_event_log
        get_event_log().emit("economy.buy", {
            "item": item.name,
            "price": price,
            "character": character.id,
            "merchant": merchant.id
        }, source="adjudication_engine")
        return True