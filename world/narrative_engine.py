from typing import Dict, List, Optional
from dungeon_neo.campaign import Quest, Location, Faction, WorldState
from dungeon_neo.ai_integration import DungeonAI
from core.session_manager import SessionManager


class NarrativeEngine:
    def __init__(self, ai: DungeonAI, world: WorldState, session: SessionManager):
        self.ai = ai
        self.world = world
        self.session = session
        self.story_arcs: List[Dict] = []
        self.active_arc: Optional[Dict] = None
        # self.active_quests: List[str] = []  # Quest IDs
        # self.completed_quests: List[str] = []  # Quest IDs
        # self.failed_quests: List[str] = []  # Quest IDs
        self.global_events: List[Dict] = []

    def generate_story_arc(self, theme: str, scope: str = "regional") -> Dict:
        """Generate a story arc using AI"""
        return self.ai.generate_structured_data(
            f"Generate a {scope}-scope story arc for a {theme} campaign",
            response_format={
                "name": "string",
                "description": "string",
                "key_events": ["string"],
                "major_players": ["string"]
            }
        )
    
    def start_story_arc(self, arc_data: Dict):
        """Activate a new story arc"""
        self.active_arc = {
            "id": f"arc_{len(self.story_arcs)+1}",
            "name": arc_data["name"],
            "description": arc_data["description"],
            "current_step": 0,
            "total_steps": len(arc_data.get("key_events", [])),
            "key_events": arc_data.get("key_events", []),
            "completed": False
        }
        self.story_arcs.append(self.active_arc)
    
    def advance_story_arc(self):
        """Progress the active story arc"""
        if self.active_arc and not self.active_arc["completed"]:
            self.active_arc["current_step"] += 1
            if self.active_arc["current_step"] >= self.active_arc["total_steps"]:
                self.active_arc["completed"] = True
                self.on_arc_completed()
    
    def on_arc_completed(self):
        """Handle story arc completion"""
        # Trigger any completion events
        pass
    
    def start_quest(self, quest_id: str):
        """Start tracking a quest"""
        self.session.start_quest(quest_id)
        quest = self.world.get_quest(quest_id)
        
        # Generate quest start event
        event = self.ai.generate_structured_data(
            f"Create quest start event for: {quest.title}",
            response_format={
                "description": "string",
                "npcs_involved": ["string"],
                "locations_affected": ["string"]
            }
        )
        self.global_events.append(event)
    
    def complete_quest(self, quest_id: str):
        """Handle quest completion"""
        self.session.complete_quest(quest_id)
        quest = self.world.get_quest(quest_id)
        
        # Generate quest completion event
        event = self.ai.generate_structured_data(
            f"Create quest completion event for: {quest.title}",
            response_format={
                "description": "string",
                "rewards": ["string"],
                "consequences": ["string"]
            }
        )
        self.global_events.append(event)
        
        # Advance story arc if needed
        self.advance_story_arc()
    
    def fail_quest(self, quest_id: str):
        """Handle quest failure"""
        self.session.fail_quest(quest_id)
        quest = self.world.get_quest(quest_id)
        
        # Generate quest failure event
        event = self.ai.process_prompt(
            f"Create quest failure event for: {quest.title}",
            response_format={
                "description": "string",
                "consequences": ["string"],
                "new_opportunities": ["string"]
            }
        )
        self.global_events.append(event)
    
    def generate_quest(self, location_id: str, context: str = "") -> Quest:
        """Generate a new quest using AI"""
        location = self.world.get_location(location_id)
        quest_data = self.ai.generate_structured_data(
            f"Generate a quest in {location.name} with context: {context}",
            response_format={
                "id": "string",
                "title": "string",
                "description": "string",
                "objectives": ["string"],
                "dungeon_required": "boolean"
            }
        )
        return Quest(
            id=quest_data["id"],
            title=quest_data["title"],
            description=quest_data["description"],
            objectives=quest_data["objectives"],
            location_id=location_id,
            dungeon_required=quest_data.get("dungeon_required", False)
        )
    
    def on_location_discovered(self, location_id: str):
        """Handle location discovery narrative events"""
        location = self.world.get_location(location_id)
        if not location.discovered:
            location.discovered = True
            # Generate initial quest for new location
            new_quest = self.generate_quest(location_id, "First discovery")
            self.world.add_quest(new_quest)
            self.active_quests.append(new_quest.id) # Start tracking the new quest
    
    def on_quest_completed(self, quest_id: str):
        """Handle quest completion narrative events"""
        if quest_id in self.active_quests:
            self.active_quests.remove(quest_id)
            self.completed_quests.append(quest_id)
            self.advance_story_arc()
    
    def on_dungeon_enter(self, location_id: str):
        """Handle dungeon entrance narrative events"""
        location = self.world.get_location(location_id)
        if not location:
            # Handle missing location
            print(f"Warning: Location {location_id} not found for dungeon enter event")
            return
            
        # Generate dungeon-specific events
        event = self.ai.generate_structured_data(
            f"Create a narrative event for entering the dungeon at {location.name}",
            response_format={
                "description": "string",
                "consequences": ["string"]
            }
        )
        self.global_events.append(event)