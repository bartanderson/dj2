# recovered_puzzle_system.py
"""
Recovered Puzzle System for dungeon_neo
Based on analysis of old/dungeon/generator.py, old/dungeon/state.py, old/test_puzzles.py
"""

import json
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class PuzzleType(Enum):
    """Types of puzzles supported"""
    RIDDLE = "riddle"
    LEVER = "lever"
    PRESSURE_PLATE = "pressure_plate"
    SEQUENCE = "sequence"
    SYMBOL = "symbol"
    LOCK = "lock"


class PuzzleState(Enum):
    """State of a puzzle"""
    UNSOLVED = "unsolved"
    SOLVED = "solved"
    LOCKED = "locked"
    FAILED = "failed"


@dataclass
class PuzzleHint:
    """Hint for a puzzle"""
    text: str
    level: int = 0  # 0 = easiest/most obvious, higher = more specific
    revealed: bool = False
    
    def reveal(self) -> None:
        """Mark hint as revealed"""
        self.revealed = True


@dataclass
class PuzzleComponent:
    """Interactive component of a puzzle"""
    name: str
    description: str
    interactions: Dict[str, str]  # action -> response
    state: Dict[str, Any] = field(default_factory=dict)
    
    def interact(self, action: str) -> Dict[str, Any]:
        """Interact with this component"""
        if action in self.interactions:
            return {
                "success": True,
                "response": self.interactions[action],
                "component": self.name
            }
        return {
            "success": False,
            "response": "Nothing happens",
            "component": self.name
        }


@dataclass
class Puzzle:
    """Complete puzzle definition"""
    puzzle_id: str
    puzzle_type: PuzzleType
    location: Tuple[int, int]
    description: str
    solution: Any  # Can be string, list, dict, etc. depending on puzzle type
    success_effect: str
    state: PuzzleState = PuzzleState.UNSOLVED
    hints: List[PuzzleHint] = field(default_factory=list)
    components: List[PuzzleComponent] = field(default_factory=list)
    attempts: int = 0
    max_attempts: Optional[int] = None
    
    def add_hint(self, hint_text: str, level: int = 0) -> None:
        """Add a hint to this puzzle"""
        self.hints.append(PuzzleHint(text=hint_text, level=level))
    
    def get_available_hints(self) -> List[PuzzleHint]:
        """Get hints that haven't been revealed yet"""
        return [h for h in self.hints if not h.revealed]
    
    def reveal_hint(self, level: Optional[int] = None) -> Optional[PuzzleHint]:
        """Reveal a hint (returns None if no hints available)"""
        available = self.get_available_hints()
        if not available:
            return None
        
        if level is not None:
            # Try to find hint at specific level
            for hint in available:
                if hint.level == level:
                    hint.reveal()
                    return hint
            # Fall back to lowest level
            hint = min(available, key=lambda h: h.level)
        else:
            # Reveal easiest hint
            hint = min(available, key=lambda h: h.level)
        
        hint.reveal()
        return hint
    
    def attempt_solution(self, attempt: Any) -> Dict[str, Any]:
        """Attempt to solve the puzzle"""
        self.attempts += 1
        
        # Check if max attempts exceeded
        if self.max_attempts and self.attempts > self.max_attempts:
            self.state = PuzzleState.FAILED
            return {
                "success": False,
                "message": "Puzzle has been permanently locked",
                "state": self.state.value,
                "attempts": self.attempts
            }
        
        # Check solution
        if attempt == self.solution:
            self.state = PuzzleState.SOLVED
            return {
                "success": True,
                "message": "Puzzle solved!",
                "effect": self.success_effect,
                "state": self.state.value,
                "attempts": self.attempts
            }
        
        # Failed attempt
        hint = self.reveal_hint()
        hint_message = f"Hint: {hint.text}" if hint else "No hints available."
        
        return {
            "success": False,
            "message": "Incorrect solution",
            "hint": hint_message if hint else None,
            "state": self.state.value,
            "attempts": self.attempts
        }
    
    def add_component(self, component: PuzzleComponent) -> None:
        """Add an interactive component to the puzzle"""
        self.components.append(component)
    
    def interact_with_component(self, component_name: str, action: str) -> Dict[str, Any]:
        """Interact with a specific component"""
        for component in self.components:
            if component.name == component_name:
                return component.interact(action)
        
        return {
            "success": False,
            "response": f"No component named {component_name}",
            "component": component_name
        }


class PuzzleManager:
    """Manages all puzzles in the dungeon"""
    
    def __init__(self, dungeon_state):
        self.dungeon_state = dungeon_state
        self.puzzles: Dict[str, Puzzle] = {}  # puzzle_id -> Puzzle
        self.location_to_puzzle: Dict[Tuple[int, int], str] = {}  # (x,y) -> puzzle_id
    
    def create_puzzle(self, 
                     location: Tuple[int, int],
                     puzzle_type: Union[str, PuzzleType],
                     description: str,
                     solution: Any,
                     success_effect: str = "A mechanism clicks and something unlocks.",
                     hints: Optional[List[str]] = None) -> str:
        """Create and register a new puzzle"""
        
        # Generate puzzle ID
        puzzle_id = f"puzzle_{location[0]}_{location[1]}_{len(self.puzzles)}"
        
        # Convert string to PuzzleType if needed
        if isinstance(puzzle_type, str):
            puzzle_type = PuzzleType(puzzle_type.lower().replace(' ', '_'))
        
        # Create puzzle
        puzzle = Puzzle(
            puzzle_id=puzzle_id,
            puzzle_type=puzzle_type,
            location=location,
            description=description,
            solution=solution,
            success_effect=success_effect
        )
        
        # Add hints if provided
        if hints:
            for i, hint_text in enumerate(hints):
                puzzle.add_hint(hint_text, level=i)
        
        # Register puzzle
        self.puzzles[puzzle_id] = puzzle
        self.location_to_puzzle[location] = puzzle_id
        
        # Store in dungeon state (if cell exists)
        cell = self.dungeon_state.get_cell(location[0], location[1])
        if cell:
            # Use the properties dict we know exists in dungeon_neo
            if 'puzzles' not in cell.properties:
                cell.properties['puzzles'] = []
            cell.properties['puzzles'].append(puzzle_id)
        
        return puzzle_id
    
    def add_hint_to_puzzle(self, puzzle_id: str, hint: str, level: int = 0) -> bool:
        """Add a hint to an existing puzzle"""
        if puzzle_id not in self.puzzles:
            return False
        
        self.puzzles[puzzle_id].add_hint(hint, level)
        return True
    
    def get_puzzle_at(self, x: int, y: int) -> Optional[Puzzle]:
        """Get puzzle at specific coordinates"""
        puzzle_id = self.location_to_puzzle.get((x, y))
        if puzzle_id:
            return self.puzzles.get(puzzle_id)
        return None
    
    def get_puzzle_hints(self, puzzle_id: str) -> List[PuzzleHint]:
        """Get all hints for a puzzle"""
        if puzzle_id not in self.puzzles:
            return []
        return self.puzzles[puzzle_id].hints
    
    def add_random_puzzles(self, density: float = 0.05) -> List[str]:
        """Add random puzzles throughout the dungeon"""
        created_puzzles = []
        
        # Get dungeon dimensions (assuming dungeon_neo state has these)
        if hasattr(self.dungeon_state, 'grid_system'):
            width = self.dungeon_state.grid_system.width
            height = self.dungeon_state.grid_system.height
            
            for x in range(width):
                for y in range(height):
                    cell = self.dungeon_state.get_cell(x, y)
                    # Only place in open cells (room or corridor)
                    if cell and (cell.is_room or cell.is_corridor):
                        if random.random() < density and (x, y) not in self.location_to_puzzle:
                            puzzle_type = random.choice(list(PuzzleType)).value
                            
                            # Create appropriate solution based on type
                            solution = self._generate_solution_for_type(puzzle_type)
                            description = f"A {puzzle_type.replace('_', ' ')} puzzle"
                            
                            puzzle_id = self.create_puzzle(
                                location=(x, y),
                                puzzle_type=puzzle_type,
                                description=description,
                                solution=solution,
                                success_effect="You hear a satisfying click."
                            )
                            
                            # Add random hints
                            hint_count = random.randint(1, 3)
                            for i in range(hint_count):
                                self.add_hint_to_puzzle(
                                    puzzle_id, 
                                    f"Hint {i+1}: Look for patterns in the {puzzle_type}.",
                                    level=i
                                )
                            
                            created_puzzles.append(puzzle_id)
        
        return created_puzzles
    
    def _generate_solution_for_type(self, puzzle_type: str) -> Any:
        """Generate an appropriate solution based on puzzle type"""
        if puzzle_type == "riddle":
            return "answer"  # Placeholder - would be specific riddle answer
        elif puzzle_type == "lever":
            return random.choice(["up", "down", "left", "right"])
        elif puzzle_type == "pressure_plate":
            return random.choice([True, False])  # Pressed/not pressed
        elif puzzle_type == "sequence":
            return random.sample(["red", "blue", "green", "yellow"], 3)
        elif puzzle_type == "symbol":
            return random.choice(["circle", "triangle", "square", "star"])
        elif puzzle_type == "lock":
            return random.randint(1000, 9999)  # Combination lock
        else:
            return "default_solution"


# Puzzle tools for integration with DMTools
class PuzzleTools:
    """Tool methods for puzzle interaction (to be added to DMTools)"""
    
    def __init__(self, puzzle_manager: PuzzleManager):
        self.puzzle_manager = puzzle_manager
    
    # Note: These @tool decorators would be added when integrating with DMTools
    # For now, they're just regular methods
    
    def place_puzzle(self, x: int, y: int, puzzle_type: str, description: str, solution: str) -> dict:
        """Place a puzzle at specified coordinates"""
        try:
            puzzle_id = self.puzzle_manager.create_puzzle(
                location=(x, y),
                puzzle_type=puzzle_type,
                description=description,
                solution=solution
            )
            return {
                "success": True,
                "message": f"Placed {puzzle_type} puzzle at ({x}, {y})",
                "puzzle_id": puzzle_id
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to place puzzle: {str(e)}"
            }
    
    def add_hint_to_puzzle_at(self, x: int, y: int, hint: str, level: int = 0) -> dict:
        """Add a hint to puzzle at coordinates"""
        puzzle = self.puzzle_manager.get_puzzle_at(x, y)
        if not puzzle:
            return {
                "success": False,
                "message": f"No puzzle found at ({x}, {y})"
            }
        
        success = self.puzzle_manager.add_hint_to_puzzle(puzzle.puzzle_id, hint, level)
        if success:
            return {
                "success": True,
                "message": f"Added hint to puzzle at ({x}, {y})",
                "puzzle_id": puzzle.puzzle_id
            }
        else:
            return {
                "success": False,
                "message": f"Failed to add hint to puzzle at ({x}, {y})"
            }
    
    def attempt_solve_puzzle(self, x: int, y: int, attempt: Any) -> dict:
        """Attempt to solve puzzle at coordinates"""
        puzzle = self.puzzle_manager.get_puzzle_at(x, y)
        if not puzzle:
            return {
                "success": False,
                "message": f"No puzzle found at ({x}, {y})"
            }
        
        result = puzzle.attempt_solution(attempt)
        return result
    
    def inspect_puzzle(self, x: int, y: int) -> dict:
        """Get information about puzzle at coordinates"""
        puzzle = self.puzzle_manager.get_puzzle_at(x, y)
        if not puzzle:
            return {
                "success": False,
                "message": f"No puzzle found at ({x}, {y})"
            }
        
        return {
            "success": True,
            "puzzle": {
                "id": puzzle.puzzle_id,
                "type": puzzle.puzzle_type.value,
                "description": puzzle.description,
                "state": puzzle.state.value,
                "attempts": puzzle.attempts,
                "hint_count": len(puzzle.hints),
                "available_hints": len([h for h in puzzle.hints if not h.revealed]),
                "component_count": len(puzzle.components)
            }
        }