import uuid
from typing import List, Dict, Optional

#classes defined here Location, NPC, Quest, Faction, WorldState

class Location:
    def __init__(self, id: str, name: str, type: str, description: str, 
                 x: int = 0, y: int = 0,  # Add coordinates here
                 dungeon_type: Optional[str] = None, dungeon_level: int = 1,
                 image_url: Optional[str] = None,
                 features: Optional[List[str]] = None,
                 services: Optional[List[str]] = None,
                 discovered: bool = False):
        self.id = id
        self.name = name
        self.type = type
        self.description = description
        self.x = x  
        self.y = y  
        self.dungeon_type = dungeon_type
        self.dungeon_level = dungeon_level
        self.features = features or []  # Initialize with empty list if None
        self.services = services or []   # Initialize with empty list if None
        self.image_url = image_url
        self.quests: List[str] = []  # Store quest IDs, not objects
        self.discovered = discovered

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "x": self.x,
            "y": self.y,
            "dungeon_type": self.dungeon_type,
            "dungeon_level": self.dungeon_level,
            "features": self.features,
            "services": self.services,
            "image_url": self.image_url,
            "discovered": self.discovered,
            "quests": self.quests # Include quest IDs in serialization
        }

class NPC:
    def __init__(self, id: str, name: str, role: str, motivation: str):
        self.id = id
        self.name = name
        self.role = role
        self.motivation = motivation
        self.dialogue: List[str] = []
        self.quests: List[str] = []  # Quest IDs

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "motivation": self.motivation,
            "dialogue": self.dialogue
        }

class Quest:
    def __init__(self, id: str, title: str, description: str, 
                 objectives: List[str], location_id: str,
                 dungeon_required: bool = False):
        self.id = id
        self.title = title
        self.description = description
        self.objectives = objectives
        self.location_id = location_id
        self.completed = False
        self.dungeon_required = dungeon_required

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "objectives": self.objectives,
            "location_id": self.location_id,
            "completed": self.completed,
            "dungeon_required": self.dungeon_required
        }

class Faction:
    def __init__(self, id: str, name: str, ideology: str, goals: List[str]):
        self.id = id
        self.name = name
        self.ideology = ideology
        self.goals = goals
        self.relationships: Dict[str, str] = {}  # faction_id -> relationship
        self.activities: List[str] = []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ideology": self.ideology,
            "goals": self.goals,
            "relationships": self.relationships,
            "activities": self.activities
        }

class WorldState:
    def __init__(self):
        self.locations: Dict[str, Location] = {}
        self.npcs: Dict[str, NPC] = {}
        self.quests: Dict[str, Quest] = {}
        self.factions: Dict[str, Faction] = {}
    
    def add_location(self, location: Location):
        self.locations[location.id] = location

    def get_location(self, location_id: str) -> Optional[Location]:
        return self.locations.get(location_id)

    def get_locations_by_type(self, location_type: str) -> List[Location]:
        return [loc for loc in self.locations.values() if loc.type == location_type]
    
    def get_npc(self, npc_id: str) -> Optional[NPC]:
        return self.npcs.get(npc_id)

    def add_npc(self, npc: NPC):
        self.npcs[npc.id] = npc
    
    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self.quests.get(quest_id)
    
    def add_quest(self, quest: Quest):
        self.quests[quest.id] = quest
    
    def add_faction(self, faction: Faction):
        self.factions[faction.id] = faction

    def get_faction(self, faction_id: str) -> Optional[Faction]:
        return self.factions.get(faction_id)
    
    def get_active_quests(self) -> List[Quest]:
        return [q for q in self.quests.values() if not q.completed]
    
    def get_location_quests(self, location_id: str) -> List[Quest]:
        return [q for q in self.quests.values() if q.location_id == location_id]