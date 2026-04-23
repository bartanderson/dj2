import random
from typing import Dict, Any, Optional
from world.intent import IntentFrame
from flask_socketio import emit

class AdjudicationEngine:
    def __init__(self, world_controller):
        self.world = world_controller

    def process(self, frame: IntentFrame, session_id: Optional[str] = None) -> Dict[str, Any]:
        if frame.action == "move":
            return self._handle_move(frame, session_id)
        elif frame.action == "buy":
            return self._handle_buy(frame, session_id)
        elif frame.action == "sell":
            return self._handle_sell(frame, session_id)
        else:
            return {"success": False, "message": f"Unknown action: {frame.action}"}

    def _handle_move(self, frame: IntentFrame, session_id: Optional[str] = None) -> Dict[str, Any]:
        direction = frame.target
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

    def _handle_buy(self, frame: IntentFrame, session_id: Optional[str]) -> Dict[str, Any]:
        item_name = frame.target
        if not item_name:
            return {"success": False, "message": "No item specified."}
        if not self.world.current_location or not self.world.current_location.merchant_id:
            return {"success": False, "message": "No merchant here."}
        merchant = self.world.campaign_state.get_merchant(self.world.current_location.merchant_id)
        if not merchant:
            return {"success": False, "message": "Merchant not found."}
        item = next((i for i in merchant.inventory if i.name.lower() == item_name.lower()), None)
        if not item:
            return {"success": False, "message": f"Item '{item_name}' not found."}
        char = self.world._get_active_character(session_id)
        if not char:
            return {"success": False, "message": "No active character."}
        rel = self.world.campaign_state.get_merchant_relationship(merchant.id, char.id)
        base_price = self.world._compute_price(item, merchant, rel, {})
        final_price = base_price
        if frame.modifiers.get("haggle"):
            persuasion = random.randint(1, 20) + char.get_skill_rank('social')
            difficulty = 10 + merchant.personality.greed - merchant.personality.honor
            if persuasion >= difficulty:
                discount = random.randint(1, 20) // 10
                final_price = max(1, base_price - discount)
        print(f"[DEBUG] Found item: {item.name}, price: {final_price}")  # moved after price calc
        print(f"[DEBUG] Character before: gold={char.currency}")
        if char.currency < final_price:
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
        print(f"[DEBUG] Character after: gold={char.currency}")
        self.world.campaign_state.update_merchant_relationship(merchant.id, char.id, affinity_delta=1)
        self.world.character_manager._save_character_to_db(char)
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
        
        def get_name(i):
            if hasattr(i, 'name'):
                return i.name
            elif isinstance(i, dict):
                return i.get('name', '')
            return ''
        
        def get_cost(i):
            if hasattr(i, 'cost'):
                return i.cost
            elif isinstance(i, dict):
                return i.get('cost', 0)
            return 0
        
        item = next((i for i in char.inventory if get_name(i).lower() == item_name.lower()), None)
        if not item:
            item = next((i for i in char.custom_items if get_name(i).lower() == item_name.lower()), None)
        if not item:
            return {"success": False, "message": f"You don't have {item_name}."}
        
        sell_price = get_cost(item) // 2
        char.currency += sell_price
        if item in char.inventory:
            char.inventory.remove(item)
        else:
            char.custom_items.remove(item)
        self.world.character_manager._save_character_to_db(char)
        return {
            "success": True,
            "message": f"You sold {item_name} for {sell_price} gp.",
            "action": "refresh_inventory"
        }