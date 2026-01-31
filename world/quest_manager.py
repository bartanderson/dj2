# world/quest_manager.py
"""
Quest Management System - handles quest assignment, tracking, and completion
Phase: State Mutation (quest state changes)
"""
from typing import Dict, List, Optional, Any
from world.campaign import Quest
import uuid

class QuestManager:
    """Manages quest state and operations"""
    
    def __init__(self):
        self.quests: Dict[str, Quest] = {}
        self.next_quest_id = 1

    def assign_starting_quest(self, party_id: str) -> str:
        """Assign the initial quest to a party"""
        quest_id = f"q{self.next_quest_id}"
        self.next_quest_id += 1
        
        starting_quest = {
            "id": quest_id,
            "name": "The Ancient Artifact",
            "description": "Recover the lost artifact from the ruins",
            "status": "active",
            "objectives": {
                "find_artifact": {
                    "description": "Locate the ancient artifact",
                    "completed": False
                }
            }
        }
        
        # Create Quest object
        quest = Quest(
            id=quest_id,
            title=starting_quest["name"],
            description=starting_quest["description"],
            objectives=starting_quest["objectives"],
            location_id=None,  # Will be set by location
            completed=False,
            dungeon_required=False
        )
        
        self.quests[quest_id] = quest
        return quest_id

    def get_quests_for_location(self, world_map, location_id: str) -> List[Quest]:
        """Get full quest objects for a location"""
        location = world_map.get_location(location_id)
        if not location:
            return []
        
        # Return actual quest objects for the location
        return [
            self.quests[qid] 
            for qid in location.quests 
            if qid in self.quests
        ]

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID"""
        return self.quests.get(quest_id)

    def create_quest(self, title: str, description: str, objectives: Dict, 
                     location_id: Optional[str] = None, 
                     dungeon_required: bool = False) -> str:
        """Create a new quest"""
        quest_id = f"quest_{uuid.uuid4().hex[:8]}"
        
        quest = Quest(
            id=quest_id,
            title=title,
            description=description,
            objectives=objectives,
            location_id=location_id,
            completed=False,
            dungeon_required=dungeon_required
        )
        
        self.quests[quest_id] = quest
        return quest_id

    def complete_quest(self, quest_id: str) -> bool:
        """Mark a quest as completed"""
        if quest_id in self.quests:
            self.quests[quest_id].completed = True
            return True
        return False

    def get_active_quests(self) -> List[Quest]:
        """Get all active (incomplete) quests"""
        return [quest for quest in self.quests.values() if not quest.completed]

    def get_completed_quests(self) -> List[Quest]:
        """Get all completed quests"""
        return [quest for quest in self.quests.values() if quest.completed]

    def link_quest_to_location(self, quest_id: str, location_id: str, world_map) -> bool:
        """Link a quest to a location"""
        if quest_id not in self.quests:
            return False
            
        location = world_map.get_location(location_id)
        if not location:
            return False
            
        self.quests[quest_id].location_id = location_id
        
        if not hasattr(location, 'quests'):
            location.quests = []
        if quest_id not in location.quests:
            location.quests.append(quest_id)
            
        return True