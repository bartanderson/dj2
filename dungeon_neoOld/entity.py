# In dungeon_neo/entity.py
class Entity:
    ENTITY_SYMBOLS = {
        "npc": "👤",
        "monster": "👹",
        "item": "🔼",
        "trap": "⚠️",
        "portal": "🌀",
        "chest": "🧰",
        "corpse": "💀",
        "altar": "⚖️",
        "fountain": "⛲"
    }
    
    def __init__(self, entity_type, **kwargs):
        self.type = entity_type
        self.properties = kwargs
        
    def get_symbol(self):
        return self.ENTITY_SYMBOLS.get(self.type, "❓")