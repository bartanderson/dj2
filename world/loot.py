import random
from world import dnd_data

def generate_loot(cr_range):
    """Return a list of item dicts for the given CR range string."""
    equipment = dnd_data._get_equipment_data().get("equipment", {})
    weapons = equipment.get("weapons", {})
    gear = equipment.get("gear", {})
    all_items = []
    for key, item in weapons.items():
        all_items.append({"id": key, "name": item["name"], "cost": item.get("cost", 10), "type": "weapon"})
    for key, item in gear.items():
        all_items.append({"id": key, "name": item["name"], "cost": item.get("cost", 5), "type": "gear"})
    
    if cr_range == "CR1-5":
        # Mundane + potion
        mundane = random.choice([i for i in all_items if i["cost"] < 50])
        potion = {"name": "Healing Potion", "cost": 10, "type": "consumable"}
        return [mundane, potion]
    elif cr_range == "CR6-10":
        # +1 weapon or armor
        plus1 = random.choice([i for i in all_items if i["type"] in ["weapon", "armor"]])
        plus1["name"] = f"+1 {plus1['name']}"
        plus1["cost"] = plus1["cost"] * 2
        return [plus1]
    elif cr_range == "CR11-15":
        # Rare consumable
        rare = random.choice([i for i in all_items if i["cost"] > 100])
        return [rare]
    else:
        # Legendary
        legendary = random.choice([i for i in all_items if i["cost"] > 500])
        return [legendary]