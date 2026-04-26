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
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        
        # Use frame.item first, then frame.target
        item_name = frame.item or frame.target
        if not item_name:
            return {"success": False, "message": "What item do you want to buy?"}
        
        # Fuzzy match against merchant inventory
        from difflib import get_close_matches
        inventory_names = [i.name.lower() for i in merchant.inventory]
        matches = get_close_matches(item_name.lower(), inventory_names, n=1, cutoff=0.6)
        if not matches:
            available = ", ".join([i.name for i in merchant.inventory[:5]])
            return {"success": False, "message": f"I don't have '{item_name}'. I have: {available}."}
        
        matched_name = matches[0]
        item = next((i for i in merchant.inventory if i.name.lower() == matched_name), None)
        if not item:
            return {"success": False, "message": f"Item '{matched_name}' not found in inventory."}
        
        # Compute price
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        price = self.world._compute_price(item, merchant, rel, frame.context)
        
        # If no price given, ask for confirmation
        if not frame.price:
            return {
                "success": False,
                "message": f"{item.name} costs {price} gp. To buy it, say 'buy {item.name} for {price} gp'.",
                "action": "request_price"
            }
        
        # Proceed with purchase
        if char.currency < frame.price:
            return {"success": False, "message": f"You need {frame.price} gp but only have {char.currency}."}
        
        char.currency -= frame.price
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=item.name,
            description=f"Bought from {merchant.name}",
            type=item.tags.pop() if item.tags else "adventuring_gear",
            cost=frame.price
        )
        char.inventory.append(new_item)
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1)
        self.world.character_manager._save_character_to_db(char)
        
        from world.event_log import get_event_log
        get_event_log().emit("economy.buy", {
            "item": item.name,
            "price": frame.price,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")

        self.world.emit_inventory_update(char.id)

        return {
            "success": True,
            "message": f"You bought {item.name} for {frame.price} gp.",
            "action": "refresh_inventory"
        }

    def _handle_barter(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        """Handle barter: player gives item (+optional gold) for merchant's item."""
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here to barter with."}
        
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        
        # Check if merchant allows barter
        if not merchant.constraints.barter_allowed:
            return {"success": False, "message": f"{merchant.name} doesn't barter. You can buy or sell only."}
        
        # Player gives item
        give_item_name = frame.item or frame.target  # item they give
        want_item_name = frame.target if frame.item else None  # if only one, assume give=item, want=target
        # Better: if both item and target are set, give=item, want=target.
        if frame.item and frame.target:
            give_item_name = frame.item
            want_item_name = frame.target
        elif not want_item_name:
            return {"success": False, "message": "Barter requires both what you give and what you want. Example: 'barter shortsword for potion'."}
        
        # Fuzzy match for player's give item
        from difflib import get_close_matches
        def get_item_from_inventory(inv, name):
            inv_names = [i.name.lower() for i in inv]
            matches = get_close_matches(name.lower(), inv_names, n=1, cutoff=0.6)
            if not matches:
                return None
            matched = matches[0]
            return next((i for i in inv if i.name.lower() == matched), None)
        
        give_item_obj = get_item_from_inventory(char.inventory, give_item_name)
        if not give_item_obj:
            return {"success": False, "message": f"You don't have '{give_item_name}' to barter."}
        
        # Fuzzy match for merchant's wanted item
        want_item_obj = get_item_from_inventory(merchant.inventory, want_item_name)
        if not want_item_obj:
            available = ", ".join([i.name for i in merchant.inventory[:5]])
            return {"success": False, "message": f"{merchant.name} doesn't have '{want_item_name}'. They have: {available}."}
        
        # Check visibility of merchant's item
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        if not self.world._is_item_visible(want_item_obj, rel):
            return {"success": False, "message": f"You don't see '{want_item_obj.name}' in the {merchant.display_name}."}
        
        # Compute values
        # Player's item value = what merchant would pay for it (sell price)
        give_value = self._compute_sell_price(give_item_obj, merchant, rel)
        # Merchant's item value = what player would pay (buy price)
        want_value = self.world._compute_price(want_item_obj, merchant, rel, frame.context)
        
        # Gold adjustment from player (positive = player adds gold)
        gold_diff = frame.price if frame.price else 0
        
        # Check if barter is fair
        player_total = give_value + gold_diff
        merchant_total = want_value
        
        if player_total < merchant_total:
            shortage = merchant_total - player_total
            return {
                "success": False,
                "message": f"Your {give_item_obj.name} (worth {give_value} gp) plus {gold_diff} gp = {player_total} gp. The {want_item_obj.name} costs {want_value} gp. You need {shortage} more gold.",
                "action": "counter_offer"
            }
        elif player_total > merchant_total:
            overpay = player_total - merchant_total
            # Optionally, merchant might give change or just accept overpay as generosity (improves relationship)
            # For simplicity, we accept overpay but note it
            pass
        
        # Accept barter
        # Remove give item from player
        if give_item_obj in char.inventory:
            char.inventory.remove(give_item_obj)
        else:
            return {"success": False, "message": "Item removal failed."}
        
        # Add wanted item to player (create copy)
        from world.character import InventoryItem
        new_item = InventoryItem(
            name=want_item_obj.name,
            description=f"Bartered from {merchant.name}",
            type=want_item_obj.tags.pop() if want_item_obj.tags else "adventuring_gear",
            cost=want_item_obj.base_price
        )
        char.inventory.append(new_item)
        
        # Adjust gold
        if gold_diff > 0:
            if char.currency < gold_diff:
                # Rollback? For now, fail
                char.inventory.append(give_item_obj)  # give back
                char.inventory.remove(new_item)
                return {"success": False, "message": f"You don't have {gold_diff} gp to add."}
            char.currency -= gold_diff
            merchant_currency = getattr(merchant, 'currency', 0)  # merchants may not track gold; we can ignore or add to a hidden pool
        elif gold_diff < 0:
            # Merchant adds gold (unlikely but possible)
            char.currency += abs(gold_diff)
        
        # Merchant loses wanted item, gains give item (simplified – we just remove from merchant inventory, add give item)
        # In a real system you'd update merchant inventory, but for simplicity we remove wanted item
        merchant.inventory.remove(want_item_obj)
        # Optionally add give_item_obj to merchant inventory (but may not persist)
        
        # Update relationship (positive for successful barter)
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=2, trust_delta=1)
        self.world.character_manager._save_character_to_db(char)
        
        # Emit event
        from world.event_log import get_event_log
        get_event_log().emit("economy.barter", {
            "give_item": give_item_obj.name,
            "receive_item": want_item_obj.name,
            "gold_diff": gold_diff,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")

        self.world.emit_inventory_update(char.id)
        
        return {
            "success": True,
            "message": f"You barter your {give_item_obj.name} for {merchant.name}'s {want_item_obj.name}. {'You add ' + str(gold_diff) + ' gp.' if gold_diff > 0 else ''}",
            "action": "refresh_inventory"
        }

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

    def _handle_sell(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        """Sell an item to the merchant."""
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here to sell to."}
        
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        
        # Get item name from frame.item or frame.target
        item_name = frame.item or frame.target
        if not item_name:
            return {"success": False, "message": "What item do you want to sell?"}
        
        # Fuzzy match against character's inventory
        from difflib import get_close_matches
        
        # Get list of item names from character's inventory
        def get_name(i):
            return i.name.lower() if hasattr(i, 'name') else i.get('name', '').lower()
        
        inventory_names = [get_name(i) for i in char.inventory]
        matches = get_close_matches(item_name.lower(), inventory_names, n=1, cutoff=0.6)
        if not matches:
            available = ", ".join([get_name(i) for i in char.inventory[:5]])
            return {"success": False, "message": f"You don't have '{item_name}'. You have: {available}."}
        
        matched_name = matches[0]
        # Find the actual item object
        item_obj = next((i for i in char.inventory if get_name(i) == matched_name), None)
        if not item_obj:
            return {"success": False, "message": f"Item '{matched_name}' not found in your inventory."}
        
        # Compute sell price (typically half of base price, modified by merchant personality and relationship)
        base_price = item_obj.cost if hasattr(item_obj, 'cost') else 10
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        
        # Merchant's greed increases price (bad for seller), affinity/trust increase price (good for seller)
        price_multiplier = 1.0
        price_multiplier += (merchant.personality.greed - 5) * 0.05  # greed 0-10 → -0.25 to +0.25
        price_multiplier += rel.affinity * 0.03   # +0.03 per affinity point
        price_multiplier += rel.trust * 0.02      # +0.02 per trust point
        price_multiplier -= rel.fear * 0.04       # fear lowers price
        
        # Clamp between 0.2 and 1.0 (merchant won't pay more than base price usually)
        price_multiplier = max(0.2, min(1.0, price_multiplier))
        price = int(base_price * price_multiplier)
        price = max(1, price)  # at least 1 gp
        
        # If no price offered, inform the player
        if not frame.price:
            return {
                "success": False,
                "message": f"I'll give you {price} gp for your {matched_name}. To sell, say 'sell {matched_name} for {price} gp'.",
                "action": "request_price"
            }
        
        # Player offered a price – check if it's acceptable (simple: accept if offered <= computed price? Actually player wants to sell, so offered is what they ask for)
        offered = frame.price
        if offered > price:
            # Player asks for more than merchant is willing to pay – can haggle or reject
            return {
                "success": False,
                "message": f"I can't pay {offered} gp for that. I'll give you {price} gp. Want to sell for {price}?",
                "action": "counter_offer"
            }
        # Accept the sale (offered <= price, merchant agrees)
        # Use offered price (usually player will match exactly the computed price)
        final_price = offered if offered <= price else price
        
        # Perform transaction
        char.currency += final_price
        # Remove item from inventory
        if item_obj in char.inventory:
            char.inventory.remove(item_obj)
        else:
            # Handle dict-style if needed
            char.custom_items.remove(item_obj) if hasattr(char, 'custom_items') else None
        
        # Update merchant relationship (positive for selling, slight affinity bump)
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1, trust_delta=1)
        self.world.character_manager._save_character_to_db(char)
        
        # Emit event
        from world.event_log import get_event_log
        get_event_log().emit("economy.sell", {
            "item": matched_name,
            "price": final_price,
            "character": char.id,
            "merchant": merchant.id
        }, source="adjudication_engine")
        
        self.world.emit_inventory_update(char.id)

        return {
            "success": True,
            "message": f"You sold {matched_name} for {final_price} gp.",
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
