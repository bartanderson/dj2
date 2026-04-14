import random
from world import dnd_data

class Merchant:
    def __init__(self, name, location_name):
        self.name = name
        self.location = location_name
        self.inventory = self._generate_inventory()
        self.greeting = f"Welcome to {location_name}! I am {name}. Would you like to buy or sell?"

    def _generate_inventory(self):
        equipment = dnd_data._get_equipment_data().get("equipment", {})
        weapons = equipment.get("weapons", {})
        gear = equipment.get("gear", {})
        items = []
        for key, item in weapons.items():
            items.append({"id": key, "name": item["name"], "cost": self._get_cost(item), "type": "weapon"})
        for key, item in gear.items():
            items.append({"id": key, "name": item["name"], "cost": self._get_cost(item), "type": "gear"})
        # Return a subset (e.g., 6-10 items)
        return random.sample(items, min(8, len(items)))

    def _get_cost(self, item):
        return item.get("cost", 10)

    def buy(self, item_name, character):
        from world.character import InventoryItem
        for item in self.inventory:
            if item["name"].lower() == item_name.lower():
                if character.currency >= item["cost"]:
                    character.currency -= item["cost"]
                    character.add_custom_item(item["name"], "", item["type"], item["cost"])
                    return {"success": True, "message": f"{self.name} says: Here you go! That'll be {item['cost']} gold."}
                else:
                    return {"success": False, "message": f"{self.name} says: You don't have enough gold. Need {item['cost']}."}
        return {"success": False, "message": f"{self.name} says: I don't have that item."}

    def sell(self, item_name, character):
        for idx, item in enumerate(character.custom_items):
            if item.name.lower() == item_name.lower():
                # Default sell price half of 10 (if cost not stored)
                sell_price = item.cost // 2
                character.currency += sell_price
                character.custom_items.pop(idx)
                return {"success": True, "message": f"{self.name} says: I'll give you {sell_price} gold for that."}
        return {"success": False, "message": f"{self.name} says: You don't have that item."}