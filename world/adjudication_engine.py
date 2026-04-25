import random
from typing import Dict, Any, Optional
from world.intent import IntentFrame
from flask_socketio import emit
from world.event_log import get_event_log

DEBUG = True   # set to False to reduce console output

class AdjudicationEngine:
    def __init__(self, world_controller):
        self.world = world_controller
        self.event_log = get_event_log()
        # Conversation state store for multi‑turn (e.g., haggling)
        self.conversations: Dict[str, Dict] = {}  # conversation_id -> state

    def process(self, frame: IntentFrame, session_id: Optional[str] = None) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] AdjudicationEngine.process: action={frame.action}, category={frame.category}, target={frame.target}, item={frame.item}, price={frame.price}")

        # Route by category
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
            return {
                "success": False,
                "message": f"I understand you want to '{frame.action}', but I'm not yet sure how to handle that category. The game master will work on it."
            }

    def _handle_move(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print("[DEBUG] _handle_move called")
        direction = frame.destination or frame.target
        if not direction:
            return {"success": False, "message": "No direction specified."}
        dir_map = {
            "north": "n", "south": "s", "east": "e", "west": "w",
            "northeast": "ne", "northwest": "nw",
            "southeast": "se", "southwest": "sw"
        }
        short_dir = dir_map.get(direction.lower(), direction)
        result = self.world.move_hex(short_dir)
        if result.get("success"):
            self.world.emit_party_moved(result.get('new_col'), result.get('new_row'), session_id)
            return {
                "success": True,
                "message": f"You move {direction}.",
                "map_data": self.world.get_map_data(),
                "action": "centerOnParty"
            }
        else:
            return {"success": False, "message": result.get("message", "Cannot move.")}

    def _handle_talk(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        target = frame.target or "someone"
        # For now, simple response. Later, can trigger AI conversation.
        return {
            "success": True,
            "message": f"You talk to {target}. They respond in a friendly manner.",
            "action": None
        }

    def _handle_buy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        item_name = frame.target
        if not item_name:
            return {"success": False, "message": "No item specified."}

        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}

        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}

        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            self.event_log.emit("economy.buy.fail", {"reason": "no_merchant", "location": self.world.current_location.name}, source="adjudication")
            return {"success": False, "message": "No merchant here."}

        item = next((i for i in merchant.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            self.event_log.emit("economy.buy.fail", {"reason": "item_not_found", "item": item_name}, source="adjudication")
            return {"success": False, "message": f"Item '{item_name}' not found."}

        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        base_price = self.world._compute_price(item, merchant, rel, {})
        final_price = base_price
        if frame.modifiers.get("haggle"):
            persuasion = random.randint(1, 20) + char.get_skill_rank('social')
            difficulty = 10 + merchant.personality.greed - merchant.personality.honor
            if persuasion >= difficulty:
                discount = random.randint(1, 20) // 10
                final_price = max(1, base_price - discount)

        if char.currency < final_price:
            self.event_log.emit("economy.buy.fail", {"reason": "insufficient_gold", "need": final_price, "have": char.currency}, source="adjudication")
            return {"success": False, "message": f"Not enough gold. Need {final_price} gp."}

        char.currency -= final_price
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=item.name,
            description=f"Bought from {merchant.name}",
            type=item.tags.pop() if item.tags else "adventuring_gear",
            cost=final_price
        )
        char.inventory.append(new_item)
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1)
        self.world.character_manager._save_character_to_db(char)

        from world.event_log import get_event_log
        get_event_log().emit("economy.buy", {
            "item": item.name,
            "price": final_price,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")
        
        if frame.action == "buy":
            if frame.currency:
                return self._handle_haggle(frame, session_id)
            else:
                return self._handle_buy(frame, session_id)

        return {
            "success": True,
            "message": f"You bought {item.name} for {final_price} gp.",
            "action": "refresh_inventory"
        }

    def _handle_sell(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        item_name = frame.target
        if not item_name:
            return {"success": False, "message": "No item specified."}

        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}

        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}

        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            self.event_log.emit("economy.buy.fail", {"reason": "no_merchant", "location": self.world.current_location.name}, source="adjudication")
            return {"success": False, "message": "Merchant not found."}

        # Find item in inventory (handles both objects and dicts)
        def get_name(i):
            return i.name if hasattr(i, 'name') else i.get('name', '')
        def get_cost(i):
            return i.cost if hasattr(i, 'cost') else i.get('cost', 0)

        item = next((i for i in char.inventory if get_name(i).lower() == item_name.lower()), None)
        if not item:
            self.event_log.emit("economy.buy.fail", {"reason": "item_not_found", "item": item_name}, source="adjudication")
            return {"success": False, "message": f"Item '{item_name}' not found."}

        sell_price = get_cost(item) // 2
        char.currency += sell_price
        if item in char.inventory:
            char.inventory.remove(item)
        else:
            char.custom_items.remove(item)

        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, trust_delta=1)
        self.world.character_manager._save_character_to_db(char)

        from world.event_log import get_event_log
        get_event_log().emit("economy.sell", {
            "item": item_name,
            "price": sell_price,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")

        return {
            "success": True,
            "message": f"You sold {item_name} for {sell_price} gp.",
            "action": "refresh_inventory"
        }

    def _handle_look(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}

        col, row = self.world.campaign_state.party_position
        hex_data = self.world.campaign_state.get_hex(col, row)
        if not hex_data:
            return {"success": False, "message": "You are in an unknown area."}

        target = frame.target
        location = self.world.current_location
        merchant = None
        if location and location.merchant_id:
            merchant = self.world.campaign_state.get_merchant(location.merchant_id)

        # ------------------------------------------------
        # No target – area description
        # ------------------------------------------------
        if not target:
            parts = []
            if location:
                parts.append(f"You are at {location.name}.")
            else:
                parts.append("You are in the wilderness.")
            terrain = hex_data.get('terrain', 'unknown terrain')
            parts.append(f"The terrain is {terrain}.")
            pois = hex_data.get('pois', [])
            discovered_pois = [p['name'] for p in pois if p.get('discovered')]
            if discovered_pois:
                parts.append(f"You see: {', '.join(discovered_pois)}.")
            if merchant:
                parts.append(f"{merchant.name} the merchant is here, standing near {merchant.display_name}.")
            return {"success": True, "message": " ".join(parts), "action": None}

        # ------------------------------------------------
        # Target is the merchant's display
        # ------------------------------------------------
        if merchant and target.lower() == merchant.display_name.lower():
            rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
            visible = []
            for item in merchant.inventory:
                if self.world._is_item_visible(item, rel):
                    visible.append(f"{item.name} ({item.base_price} gp)")
            if visible:
                msg = f"{merchant.name}'s {merchant.display_name} holds: {', '.join(visible)}."
            else:
                msg = f"{merchant.name}'s {merchant.display_name} is empty."
            return {"success": True, "message": msg, "action": None}

        # ------------------------------------------------
        # Target is the merchant (NPC)
        # ------------------------------------------------
        if merchant and (target.lower() == merchant.name.lower() or target.lower() == "merchant"):
            return {"success": True, "message": f"{merchant.name} the merchant stands by his {merchant.display_name}.", "action": None}

        # ------------------------------------------------
        # Target is a location
        # ------------------------------------------------
        for loc in self.world.world_map.locations.values():
            if loc.discovered and loc.name.lower() == target.lower():
                return {"success": True, "message": f"{loc.name}: {loc.description}", "action": None}

        # ------------------------------------------------
        # Generic
        # ------------------------------------------------
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

    def _handle_economy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        if DEBUG:
            print(f"[DEBUG] _handle_economy: action={frame.action}, item={frame.item}, price={frame.price}")
        action = frame.action.lower()
        if "buy" in action:
            if frame.price:
                result = self.world.haggle(frame.item, frame.price) if hasattr(self.world, 'haggle') else None
            else:
                result = self.world.buy(frame.item) if hasattr(self.world, 'buy') else None
        elif "sell" in action:
            result = self.world.sell(frame.item) if hasattr(self.world, 'sell') else None
        elif "haggle" in action:
            result = self.world.haggle(frame.item, frame.price) if hasattr(self.world, 'haggle') else None
        else:
            return {"success": False, "message": f"Unknown economic action: {action}"}
        if result:
            return {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "action": result.get("action")
            }
        else:
            return {"success": False, "message": "Economy feature not fully implemented yet."}

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
        # Special case for "look" – keep existing behavior
        if "look" in frame.action.lower() or "examine" in frame.action.lower():
            return self._handle_look(frame, session_id)

        destination = frame.destination or frame.target
        if not destination:
            return {"success": False, "message": "Where do you want to go?"}
        # Stub – later implement travel to named locations, searching, etc.
        return {
            "success": False,
            "message": f"Travel to '{destination}' is not yet implemented. The game master will work on it.",
            "action": None
        }
