# recovered_enhanced_tools.py
"""
Recovered Enhanced AI Tools for dungeon_neo
Based on analysis of old/src/AIDMFramework.py
"""

import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class QuestType(Enum):
    """Types of quests"""
    FETCH = "fetch"
    KILL = "kill"
    EXPLORE = "explore"
    ESCORT = "escort"
    DISCOVER = "discover"
    DEFEND = "defend"
    RESCUE = "rescue"


class QuestDifficulty(Enum):
    """Quest difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DEADLY = "deadly"


class DungeonFeature(Enum):
    """Types of dungeon environmental features"""
    FOUNTAIN = "fountain"
    ALTAR = "altar"
    PIT = "pit"
    CHASM = "chasm"
    STATUE = "statue"
    SHRINE = "shrine"
    BRAZIER = "brazier"
    LECTERN = "lectern"
    CRYPT = "crypt"
    PEDESTAL = "pedestal"


@dataclass
class NPC:
    """Non-player character"""
    name: str
    role: str
    personality: str
    goals: List[str]
    location: Optional[tuple] = None
    dialogue: List[str] = field(default_factory=list)
    inventory: List[str] = field(default_factory=list)
    hostile: bool = False
    
    def add_dialogue(self, line: str) -> None:
        """Add a dialogue line"""
        self.dialogue.append(line)
    
    def speak(self) -> str:
        """Get a random dialogue line"""
        if self.dialogue:
            return random.choice(self.dialogue)
        return f"{self.name} has nothing to say."


@dataclass
class Quest:
    """Quest definition"""
    quest_id: str
    quest_type: QuestType
    title: str
    description: str
    difficulty: QuestDifficulty
    objectives: List[str]
    reward: str
    giver: Optional[str] = None  # NPC who gave the quest
    target_location: Optional[tuple] = None
    completed: bool = False
    failed: bool = False
    
    def complete(self) -> None:
        """Mark quest as completed"""
        self.completed = True
    
    def fail(self) -> None:
        """Mark quest as failed"""
        self.failed = True
    
    def get_status(self) -> str:
        """Get quest status"""
        if self.completed:
            return "completed"
        if self.failed:
            return "failed"
        return "active"


@dataclass
class DungeonFeatureObj:
    """Dungeon environmental feature"""
    feature_id: str
    feature_type: DungeonFeature
    description: str
    location: tuple
    interactive: bool = True
    effects: List[str] = field(default_factory=list)
    
    def interact(self) -> Dict[str, Any]:
        """Interact with the feature"""
        if not self.interactive:
            return {
                "success": False,
                "message": f"The {self.feature_type.value} doesn't respond."
            }
        
        # Generate random effect
        if self.effects:
            effect = random.choice(self.effects)
        else:
            effect = f"The {self.feature_type.value} reacts in some way."
        
        return {
            "success": True,
            "message": f"You interact with the {self.feature_type.value}. {effect}",
            "effect": effect
        }


class EnhancedToolSystem:
    """System for enhanced AI tools"""
    
    def __init__(self, dungeon_state):
        self.dungeon_state = dungeon_state
        self.quests: Dict[str, Quest] = {}
        self.npcs: Dict[str, NPC] = {}
        self.features: Dict[str, DungeonFeatureObj] = {}
        self.quest_counter = 0
        self.npc_counter = 0
        self.feature_counter = 0
    
    # Quest Generation
    def generate_quest(self, 
                      quest_type: Union[str, QuestType],
                      difficulty: Union[str, QuestDifficulty],
                      thematic_elements: List[str] = None) -> Quest:
        """Generate a quest with given parameters"""
        
        # Convert strings to enums if needed
        if isinstance(quest_type, str):
            quest_type = QuestType(quest_type.lower())
        if isinstance(difficulty, str):
            difficulty = QuestDifficulty(difficulty.lower())
        
        # Generate quest ID
        self.quest_counter += 1
        quest_id = f"quest_{self.quest_counter}"
        
        # Build title and description
        title = self._generate_quest_title(quest_type, difficulty, thematic_elements)
        description = self._generate_quest_description(quest_type, difficulty, thematic_elements)
        objectives = self._generate_quest_objectives(quest_type, difficulty)
        reward = self._generate_quest_reward(difficulty)
        
        # Create quest
        quest = Quest(
            quest_id=quest_id,
            quest_type=quest_type,
            title=title,
            description=description,
            difficulty=difficulty,
            objectives=objectives,
            reward=reward
        )
        
        self.quests[quest_id] = quest
        return quest
    
    def _generate_quest_title(self, quest_type: QuestType, difficulty: QuestDifficulty, themes: List[str]) -> str:
        """Generate a quest title"""
        themes_str = " and ".join(themes) if themes else "mysterious"
        
        titles = {
            QuestType.FETCH: f"{difficulty.value.capitalize()} {themes_str} Retrieval",
            QuestType.KILL: f"Slay the {themes_str} Beast",
            QuestType.EXPLORE: f"Explore the {themes_str} Ruins",
            QuestType.ESCORT: f"Escort through {themes_str} Territory",
            QuestType.DISCOVER: f"Discover the {themes_str} Secret",
            QuestType.DEFEND: f"Defend against {themes_str} Threat",
            QuestType.RESCUE: f"Rescue from {themes_str} Peril"
        }
        
        return titles.get(quest_type, f"{quest_type.value.capitalize()} Quest")
    
    def _generate_quest_description(self, quest_type: QuestType, difficulty: QuestDifficulty, themes: List[str]) -> str:
        """Generate quest description"""
        difficulty_desc = {
            QuestDifficulty.EASY: "A relatively simple task",
            QuestDifficulty.MEDIUM: "A challenging endeavor",
            QuestDifficulty.HARD: "A dangerous mission",
            QuestDifficulty.DEADLY: "A potentially fatal undertaking"
        }.get(difficulty, "A quest")
        
        themes_str = ", ".join(themes) if themes else "unknown forces"
        
        return f"{difficulty_desc} involving {themes_str}. This {quest_type.value} quest will test your abilities."
    
    def _generate_quest_objectives(self, quest_type: QuestType, difficulty: QuestDifficulty) -> List[str]:
        """Generate quest objectives"""
        base_objectives = []
        
        if quest_type == QuestType.FETCH:
            base_objectives = [
                "Locate the target item",
                "Retrieve it safely",
                "Return to the quest giver"
            ]
        elif quest_type == QuestType.KILL:
            base_objectives = [
                "Find the target creature",
                "Defeat it in combat",
                "Provide proof of defeat"
            ]
        elif quest_type == QuestType.EXPLORE:
            base_objectives = [
                "Reach the target location",
                "Map the area",
                "Discover any secrets"
            ]
        
        # Add difficulty-based objectives
        if difficulty == QuestDifficulty.MEDIUM:
            base_objectives.append("Avoid detection by enemies")
        elif difficulty == QuestDifficulty.HARD:
            base_objectives.append("Survive environmental hazards")
            base_objectives.append("Defeat guardian creatures")
        elif difficulty == QuestDifficulty.DEADLY:
            base_objectives.append("Overcome deadly traps")
            base_objectives.append("Face the final challenge alone")
        
        return base_objectives
    
    def _generate_quest_reward(self, difficulty: QuestDifficulty) -> str:
        """Generate quest reward description"""
        rewards = {
            QuestDifficulty.EASY: "A modest sum of gold and basic supplies",
            QuestDifficulty.MEDIUM: "Substantial gold and a useful magic item",
            QuestDifficulty.HARD: "A treasure hoard and powerful artifacts",
            QuestDifficulty.DEADLY: "Legendary treasure and fame across the land"
        }
        return rewards.get(difficulty, "Appropriate reward for your efforts")
    
    # Dungeon Features
    def add_dungeon_feature(self,
                           feature_type: Union[str, DungeonFeature],
                           description: str,
                           location: tuple,
                           interactive: bool = True,
                           effects: List[str] = None) -> DungeonFeatureObj:
        """Add a dungeon feature"""
        
        if isinstance(feature_type, str):
            feature_type = DungeonFeature(feature_type.lower())
        
        self.feature_counter += 1
        feature_id = f"feature_{self.feature_counter}"
        
        feature = DungeonFeatureObj(
            feature_id=feature_id,
            feature_type=feature_type,
            description=description,
            location=location,
            interactive=interactive,
            effects=effects or []
        )
        
        self.features[feature_id] = feature
        
        # Also add to dungeon cell if location is valid
        try:
            x, y = location
            cell = self.dungeon_state.get_cell(x, y)
            if cell:
                if 'features' not in cell.properties:
                    cell.properties['features'] = []
                cell.properties['features'].append(feature_id)
        except:
            pass  # Location might not be in current dungeon
        
        return feature
    
    # NPC Creation
    def create_npc(self,
                  name: str,
                  role: str,
                  personality: str,
                  goals: List[str],
                  location: Optional[tuple] = None,
                  dialogue: List[str] = None) -> NPC:
        """Create an NPC"""
        
        self.npc_counter += 1
        npc_id = f"npc_{self.npc_counter}"
        
        npc = NPC(
            name=name,
            role=role,
            personality=personality,
            goals=goals,
            location=location,
            dialogue=dialogue or [],
            hostile=False
        )
        
        self.npcs[npc_id] = npc
        
        # Add to dungeon if location specified
        if location:
            try:
                x, y = location
                cell = self.dungeon_state.get_cell(x, y)
                if cell:
                    if 'npcs' not in cell.properties:
                        cell.properties['npcs'] = []
                    cell.properties['npcs'].append(npc_id)
            except:
                pass
        
        return npc
    
    # Additional enhanced tools from old AIDMFramework
    def generate_dungeon_level(self,
                              theme: str = "cavern",
                              difficulty: str = "medium",
                              special_features: List[str] = None) -> Dict[str, Any]:
        """Generate a dungeon level with specific parameters"""
        # This would typically interface with the dungeon generator
        # For now, return a placeholder structure
        
        themes = {
            "cavern": "Natural cave system with stalactites and underground rivers",
            "ruins": "Ancient civilization ruins with crumbling architecture",
            "fortress": "Military stronghold with defensive structures",
            "temple": "Religious site with altars and sacred chambers",
            "labyrinth": "Complex maze with confusing passages"
        }
        
        return {
            "theme": theme,
            "description": themes.get(theme, "A mysterious dungeon level"),
            "difficulty": difficulty,
            "special_features": special_features or [],
            "estimated_rooms": random.randint(5, 20),
            "estimated_treasure": f"{difficulty} level treasure",
            "recommended_level": self._get_recommended_level(difficulty)
        }
    
    def _get_recommended_level(self, difficulty: str) -> int:
        """Get recommended party level for difficulty"""
        levels = {
            "easy": 1,
            "medium": 3,
            "hard": 5,
            "deadly": 7
        }
        return levels.get(difficulty, 3)
    
    def transform_cell(self, x: int, y: int, new_type: str) -> Dict[str, Any]:
        """Transform a cell to a new type"""
        cell = self.dungeon_state.get_cell(x, y)
        if not cell:
            return {
                "success": False,
                "message": f"No cell at ({x}, {y})"
            }
        
        # This would need to integrate with dungeon_neo's cell modification system
        # For now, just return a placeholder
        
        return {
            "success": True,
            "message": f"Cell at ({x}, {y}) would be transformed to {new_type}",
            "action": {
                "type": "transform_cell",
                "x": x,
                "y": y,
                "new_type": new_type
            }
        }


# Enhanced tools for integration with DMTools
class EnhancedTools:
    """Enhanced tool methods (to be added to DMTools)"""
    
    def __init__(self, enhanced_system: EnhancedToolSystem):
        self.enhanced_system = enhanced_system
    
    # Note: These @tool decorators would be added when integrating with DMTools
    
    def generate_quest_tool(self, 
                           quest_type: str,
                           difficulty: str,
                           thematic_elements: str = "") -> Dict[str, Any]:
        """Generate a quest (tool version)"""
        try:
            themes = [t.strip() for t in thematic_elements.split(',')] if thematic_elements else []
            quest = self.enhanced_system.generate_quest(quest_type, difficulty, themes)
            
            return {
                "success": True,
                "message": f"Generated quest: {quest.title}",
                "quest": {
                    "id": quest.quest_id,
                    "title": quest.title,
                    "description": quest.description,
                    "type": quest.quest_type.value,
                    "difficulty": quest.difficulty.value,
                    "objectives": quest.objectives,
                    "reward": quest.reward
                }
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to generate quest: {str(e)}"
            }
    
    def add_dungeon_feature_tool(self,
                                feature_type: str,
                                description: str,
                                x: int,
                                y: int,
                                interactive: bool = True) -> Dict[str, Any]:
        """Add a dungeon feature (tool version)"""
        try:
            feature = self.enhanced_system.add_dungeon_feature(
                feature_type=feature_type,
                description=description,
                location=(x, y),
                interactive=interactive
            )
            
            return {
                "success": True,
                "message": f"Added {feature_type} at ({x}, {y}): {description}",
                "feature_id": feature.feature_id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to add feature: {str(e)}"
            }
    
    def create_npc_tool(self,
                       name: str,
                       role: str,
                       personality: str,
                       goals: str,
                       x: int = None,
                       y: int = None) -> Dict[str, Any]:
        """Create an NPC (tool version)"""
        try:
            goals_list = [g.strip() for g in goals.split(',')] if goals else []
            location = (x, y) if x is not None and y is not None else None
            
            npc = self.enhanced_system.create_npc(
                name=name,
                role=role,
                personality=personality,
                goals=goals_list,
                location=location
            )
            
            location_msg = f" at ({x}, {y})" if location else " (no specific location)"
            return {
                "success": True,
                "message": f"Created NPC {name}, the {role}{location_msg}",
                "npc_id": f"npc_{self.enhanced_system.npc_counter}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create NPC: {str(e)}"
            }
    
    def transform_cell_tool(self, x: int, y: int, new_type: str) -> Dict[str, Any]:
        """Transform a cell (tool version)"""
        return self.enhanced_system.transform_cell(x, y, new_type)