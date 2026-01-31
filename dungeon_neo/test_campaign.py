#test_campaign.py
class TestCampaign:
    def __init__(self):
        self.theme = "fantasy"
        self.locations = {
            "test_dungeon": {
                "id": "test_dungeon",
                "name": "Test Dungeon",
                "type": "dungeon",
                "description": "A test dungeon for development purposes",
                "dungeon_type": "cave",
                "dungeon_level": 1,
                "features": ["Stone walls", "Torch lighting", "Damp corridors"],
                "services": [],
                "quests": ["test_quest"]
            }
        }
        self.quests = {
            "test_quest": {
                "id": "test_quest",
                "title": "Test Quest",
                "description": "Explore the test dungeon and find the exit",
                "objectives": ["Explore the dungeon", "Find the exit"],
                "location_id": "test_dungeon",
                "dungeon_required": True,
                "rewards": ["Gold", "Experience"],
                "completion_state": "active"
            }
        }
        self.factions = {
            "test_faction": {
                "id": "test_faction",
                "name": "Testers Guild",
                "ideology": "Quality assurance through adventure",
                "goals": ["Find bugs", "Improve systems"],
                "relationships": {},
                "activities": ["Testing", "Debugging"]
            }
        }
        self.npcs = {
            "test_npc": {
                "id": "test_npc",
                "name": "Test NPC",
                "role": "Dungeon Guide",
                "motivation": "Help adventurers navigate test dungeons",
                "dialogue": ["Welcome to the test dungeon!", "Be careful of the debug traps."]
            }
        }
        
    def get_location(self, location_id):
        return self.locations.get(location_id)
    
    def get_quest(self, quest_id):
        return self.quests.get(quest_id)
    
    def get_faction(self, faction_id):
        return self.factions.get(faction_id)
    
    def get_npc(self, npc_id):
        return self.npcs.get(npc_id)
    
    def get_location_quests(self, location_id):
        location = self.get_location(location_id)
        if not location:
            return []
        return [self.get_quest(qid) for qid in location.get("quests", [])]