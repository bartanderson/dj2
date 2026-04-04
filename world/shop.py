from world import dnd_data

class Shop:
    def __init__(self, shop_type="general"):
        self.inventory = []
        self._load_items(shop_type)

    def _load_items(self, shop_type):
        eq = dnd_data._get_equipment_data().get("equipment", {})
        if shop_type == "general":
            for item in eq.get("gear", []):
                self.inventory.append(item)
            for w in eq.get("weapons", {}).values():
                if w.get("cost") in ["cheap", "meager"]:
                    self.inventory.append(w)

    def buy(self, item_name, character):
        for item in self.inventory:
            if item["name"].lower() == item_name.lower():
                cost = item.get("cost", "cheap")
                price_map = {"free": 0, "meager": 5, "cheap": 10, "medium": 50, "expensive": 100}
                price = price_map.get(cost, 10)
                if character.gold >= price:
                    character.gold -= price
                    character.add_item(item)
                    return {"success": True, "message": f"You bought {item['name']} for {price} gold."}
                else:
                    return {"success": False, "message": f"Not enough gold. Need {price} gold."}
        return {"success": False, "message": "Item not found in shop."}

    def sell(self, item_name, character):
        for item in character.inventory:
            if item["name"].lower() == item_name.lower():
                cost = item.get("cost", "cheap")
                price_map = {"free": 0, "meager": 5, "cheap": 10, "medium": 50, "expensive": 100}
                price = price_map.get(cost, 10) // 2
                character.gold += price
                character.remove_item(item_name)
                return {"success": True, "message": f"You sold {item['name']} for {price} gold."}
        return {"success": False, "message": "Item not found in inventory."}