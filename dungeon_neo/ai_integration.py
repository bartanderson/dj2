# File: dungeon_neo/ai_integration.py
from world.tool_system import ToolRegistry, tool
##from .tool_system import ToolRegistry, tool # local tool_registry.py is removed in favor of identical version in world
from ollama import Client
from .dm_tools import DMTools
from .overlay import Overlay
import re
import json
import time

class DungeonAI:
    def __init__(self, dungeon_state, ollama_host="http://localhost:11434"):
        self.state = dungeon_state
        #self._current_party_id = party_id  # If we need it for party split/join have to add it back
        self.ollama = Client(host=ollama_host)
        self.tool_registry = ToolRegistry()
        
        # Register tools from this class
        self.tool_registry.register_from_class(self)
        
        # Register tools from DMTools
        self.dm_tools = DMTools(dungeon_state)
        self.tool_registry.register_from_class(self.dm_tools)
        self.pending_action = None  # Stores action requiring confirmation
        self.pending_context = None  # Additional context for the action

        # If we need to register other tools, do it like DMTools above
        #
        #
        #
        #
        #

        
        # Generate dynamic system prompt
        self.system_prompt = self._create_system_prompt()

    def set_pending_action(self, action_type: str, action_data: dict, confirmation_prompt: str):
        """Store an action that requires player confirmation."""
        self.pending_action = {
            'type': action_type,
            'data': action_data,
            'prompt': confirmation_prompt,
            'timestamp': time.time()
        }

    def process_prompt(self, prompt: str) -> str:
        # For testing, return a mock location in JSON format
        if "location" in prompt:
            return json.dumps({
                "name": "Starter Town",
                "description": "A small town for new adventurers",
                "features": ["Town Square", "Blacksmith", "Tavern"],
                "npcs": [
                    {"name": "Old Man", "role": "Mayor", "motivation": "Keep the town safe"},
                    {"name": "Blacksmith", "role": "Weaponsmith", "motivation": "Sell weapons"}
                ],
                "quest_hooks": ["Bandits in the forest", "Missing child"],
                "services": ["Inn", "Shop", "Temple"],
                "image_prompt": "A small fantasy town with a square and a few buildings"
            })
        return json.dumps({})  # Default empty response
        
    def _get_primitive_params(self, primitive):
        """Get parameter description for each primitive"""
        params = {
            "circle": "size (0.1-1.0, default=0.8)",
            "square": "size (0.1-1.0, default=0.8), rotation (degrees)",
            "triangle": "size (0.1-1.0, default=0.8), rotation (degrees)",
            "line": "start_x, start_y, end_x, end_y (0.0-1.0), width (pixels)",
            "text": "content (string), size (font scale)",
            "polygon": "points (list of [x,y] coordinates 0.0-1.0)"
        }
        return params.get(primitive, "")

    def create_dm_prompt(game_state, player_action):
        prompt = f"""
You are the Dungeon Master for an ongoing adventure. 
Current story arc: {game_state.narrative.active_arc}
Player motivation: {game_state.motivations.current_motivation}
Tension level: {game_state.pacing.tension_level}/100

The players just: {player_action}

Consider these narrative tools:
1. Gentle nudge: {game_state.guide.get_gentle_nudge(player_action)}
2. Motivational leverage: {game_state.motivations.get_narrative_leverage()}
3. Available consequence: {game_state.consequences.get_pending_consequence()}

Respond by:
- Acknowledging the player action
- Incorporating narrative guidance if needed
- Advancing the story meaningfully
- Maintaining dramatic tension
- Preserving player agency
"""
        return prompt
    
    def _create_system_prompt(self) -> str:
        """Generate system prompt dynamically from registered tools."""
        tools_list = []
        for tool in self.tool_registry.tools.values():
            tools_list.append(tool.to_prompt_string())
        
        tools_description = "\n".join(tools_list)
        
        return f"""
You are a Dungeon Master assistant. The player can give you commands to interact with the dungeon.

You MUST respond with VALID JSON containing exactly these fields:
- "thoughts": Brief reasoning about what to do
- "tool": The name of the tool to execute (must be one of the tools listed below)
- "arguments": An object with the required parameters for that tool

DO NOT output any text outside the JSON. DO NOT invent tools not listed.

Available tools:
{tools_description}

Rules:
- If the player says "yes" or "no" in response to a prompt, interpret it as confirmation for the pending action.
- If no tool matches, respond with a narrative description instead (use tool="none", arguments={{}}, and put narrative in "thoughts").
- Always include "thoughts" explaining your reasoning.
    """

    @tool(
        name="inspect_cell",
        description="Get detailed information about a dungeon cell. If coordinates omitted, uses current party position.",
        x="X coordinate (optional, defaults to current party x)",
        y="Y coordinate (optional, defaults to current party y)"
    )
    def inspect_cell(self, x: int = None, y: int = None) -> dict:
        """Get detailed information about a cell, default to current party position"""
        if x is None or y is None:
            px, py = self.state.party_position
            if x is None:
                x = px
            if y is None:
                y = py
        
        cell = self.state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": f"No cell at ({x}, {y})"}
        
        # Get cell type safely
        cell_type = "unknown"
        if hasattr(self, 'dm_tools') and hasattr(self.dm_tools, 'get_cell_type'):
            cell_type = self.dm_tools.get_cell_type(x, y)
        
        # Build detailed description
        description = f"Cell at ({x}, {y}):\n"
        description += f"- Type: {cell_type}\n"
        description += f"- Base flags: {hex(cell.base_type)}\n"
        description += f"- Is room: {cell.is_room}\n"
        description += f"- Is corridor: {cell.is_corridor}\n"
        description += f"- Is blocked: {cell.is_blocked}\n"
        description += f"- Is door: {cell.is_door}\n"
        description += f"- Is arch: {cell.is_arch}\n"
        description += f"- Is stairs: {cell.is_stairs}\n"
        description += f"- Is secret: {cell.is_secret}\n"
        description += f"- Description: {cell.description or 'None'}\n"
        description += f"- Entities: {len(cell.entities)}\n"
        description += f"- Overlays: {len(cell.overlays)}"
        
        return {
            "success": True,
            "message": description
        }

    @tool(
        name="move",
        description="Move the party in a direction. Steps default to 1.",
        direction="Direction: north, south, east, west, northeast, northwest, southeast, southwest",
        steps="Number of steps (optional, default=1)"
    )
    def move(self, direction: str, steps: int = 1) -> dict:
        if not hasattr(self.state, 'movement') or not self.state.movement:
            return {"success": False, "message": "Movement service not available"}
        try:
            result = self.state.movement.move_party(direction, steps)
            print(f"[DEBUG move] result = {result}, type = {type(result)}")
            
            # If result is a tuple, convert to dict
            if isinstance(result, tuple):
                if len(result) >= 2:
                    result = {"success": result[0], "message": result[1]}
                else:
                    return {"success": False, "message": str(result)}
            if not isinstance(result, dict):
                return {"success": False, "message": f"Unexpected result type: {type(result)}"}
            
            print(f"[DEBUG] move result message: {result.get('message')}")
            
            # Check for stairs confirmation
            if result.get('success') is False and 'stairs' in result.get('message', '').lower():
                print(f"[DEBUG] Stairs detected! Setting pending action.")
                self.set_pending_action(
                    action_type='stairs',
                    action_data={'direction': direction, 'steps': steps},
                    confirmation_prompt=result.get('message', 'Do you wish to take the stairs?')
                )
                print(f"[DEBUG] pending_action set to: {self.pending_action}")
                result['requires_confirmation'] = True
                result['message'] = result.get('message', '') + " (Type 'yes' to confirm)"
            
            return result
        except Exception as e:
            return {"success": False, "message": f"Movement error: {str(e)}"}

    @tool(
        name="inspect",
        description="Describe the current cell and visible surroundings."
    )
    def inspect(self, radius: int = 2) -> dict:
        """Describe the current cell and visible cells within radius."""
        x, y = self.state.party_position
        
        # Get current cell description
        current = self._describe_cell(x, y)
        
        # Get surrounding cells
        surroundings = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self.state.get_cell(nx, ny):
                    # Only include if it's not blocked by line of sight (simplified)
                    # For now, include all within radius
                    cell_desc = self._describe_cell(nx, ny, direction=(dx, dy))
                    surroundings.append(cell_desc)
        
        description = f"You are {current}.\n"
        if surroundings:
            description += "You see:\n" + "\n".join(surroundings)
        
        return {"success": True, "message": description}

    def _describe_cell(self, x: int, y: int, direction: tuple = None) -> str:
        """Return a description of a single cell."""
        cell = self.state.get_cell(x, y)
        if not cell:
            return "nothing (out of bounds)"
        
        dir_text = ""
        if direction:
            dx, dy = direction
            if dx < 0: dir_text = "west"
            elif dx > 0: dir_text = "east"
            if dy < 0: dir_text += "north" if not dir_text else "-north"
            elif dy > 0: dir_text += "south" if not dir_text else "-south"
            dir_text = f" to the {dir_text}" if dir_text else ""
        
        if cell.is_room:
            return f"a room{dir_text}"
        elif cell.is_corridor:
            return f"a corridor{dir_text}"
        elif cell.is_door:
            door_type = "arch" if cell.is_arch else "door"
            return f"a {door_type}{dir_text}"
        elif cell.is_stairs:
            stair_type = "up" if cell.is_stair_up else "down"
            return f"stairs leading {stair_type}{dir_text}"
        elif cell.is_blocked:
            return f"a solid wall{dir_text}"
        else:
            return f"an empty space{dir_text}"

    @tool(
        name="exit_dungeon",
        description="Exit the current dungeon. Optionally specify a destination location ID.",
        location_id="(Optional) Destination location ID. If not provided, returns to the entrance."
    )
    def exit_dungeon(self, location_id: str = None) -> dict:
        """Exit the dungeon, optionally to a specific location."""
        return {
            "success": True,
            "exit_dungeon": True,
            "location_id": location_id,
            "message": "You exit the dungeon." + 
                       (f" You find yourself at {location_id}." if location_id else "")
        }

    @tool(
        name="get_current_position",
        description="Get the party's current position coordinates."
    )
    def get_current_position(self) -> dict:
        """Get party's current position"""
        x, y = self.state.party_position
        return {
            "success": True,
            "message": f"Party is at ({x}, {y})",
            "position": (x, y)
        }

    def log_tool_call(self, tool_name, arguments):
        """Log detailed tool call information for debugging"""
        import inspect
        tool = self.tool_registry.get_tool(tool_name)
        
        if not tool:
            return f"Tool not found: {tool_name}"
        
        debug_info = f"Tool Call: {tool_name}\n"
        debug_info += f"Arguments: {arguments}\n"
        debug_info += f"Function: {tool.func.__name__}\n"
        debug_info += f"Docstring: {inspect.getdoc(tool.func)}\n"
        
        # Get source code if available
        try:
            import inspect
            source_lines = inspect.getsourcelines(tool.func)
            debug_info += "Source:\n"
            debug_info += "".join(source_lines[0][:20]) + "\n..."
        except:
            debug_info += "Source unavailable\n"
        
        return debug_info        
        
    def process_command(self, natural_language: str) -> dict:
        print(f"[DEBUG] process_command: pending_action = {self.pending_action}")
        print(f"[DEBUG] natural_language = '{natural_language}'")
        print(f"\n=== USER COMMAND ===\n{natural_language}\n")
        
        # ===== STEP 1: Check for pending action confirmation =====
        if self.pending_action and natural_language.lower() in ['yes', 'y', 'confirm', 'take', 'proceed', 'take stairs']:
            print(f"[DEBUG] Confirming stairs with confirm_stairs=True")
            print(f"[DEBUG] Confirmation detected for pending action: {self.pending_action['type']}")
            action = self.pending_action
            self.pending_action = None
            
            if action['type'] == 'stairs':
                print(f"[DEBUG CONFIRM] Taking stairs: direction={action['data']['direction']}, steps={action['data']['steps']}")
                result = self.state.movement.move_party(
                    action['data']['direction'],
                    action['data']['steps'],
                    confirm_stairs=True
                )
                print(f"[DEBUG CONFIRM] move_party result = {result}")
                if result.get('success'):
                    narrative = f"You take the stairs. {result.get('message', '')}"
                else:
                    narrative = f"Unable to take stairs: {result.get('message', 'Unknown error')}"
                return {
                    "success": result.get('success', False),
                    "message": narrative,
                    "tool": "move",
                    "confirmed": True,
                    "refresh_map": True,
                    "exit_dungeon": result.get('exit_dungeon', False)
                }
            # TODO: Add other action types (doors, traps, etc.) here
            # elif action['type'] == 'door':
            #     ...
            else:
                return {"success": False, "message": f"Unknown pending action type: {action['type']}"}
        
        # ===== STEP 2: Clear pending action if user didn't confirm =====
        if self.pending_action:
            print(f"Clearing pending action (user didn't confirm): {natural_language}")
            self.pending_action = None
        
        # ===== STEP 3: Normal AI processing =====
        response_chunks = self.ollama.generate(
            model="llama3.2:3b",
            system=self.system_prompt,
            prompt=natural_language,
            format="json",
            options={"temperature": 0.1},
            stream=True
        )
        full_response = ""
        for chunk in response_chunks:
            full_response += chunk.get("response", "")
        print(f"AI DBG Response{full_response}")
        
        try:
            response_json = json.loads(full_response)
            tool_name = response_json.get("tool")
            arguments = response_json.get("arguments", {})
            
            # Narrative-only response
            if tool_name == "none" or tool_name is None:
                return {
                    "success": True,
                    "message": response_json.get("thoughts", "The DM considers your words..."),
                    "ai_response": full_response
                }
            
            # Validate tool exists
            if tool_name not in self.tool_registry.tools:
                return {
                    "success": False,
                    "message": f"Tool '{tool_name}' not found. Available: {', '.join(self.tool_registry.tools.keys())}"
                }
            
            # Execute the tool
            result = self.tool_registry.execute_tool(tool_name, arguments)
            
            # If the tool requires confirmation (e.g., stairs), return immediately
            if result.get('requires_confirmation'):
                return result
            
            # Generate narrative for successful tool execution
            if result.get('success'):
                try:
                    narrative_prompt = f"""
The player said: "{natural_language}"
The tool '{tool_name}' was executed with arguments: {json.dumps(arguments)}
The result was: {json.dumps(result, indent=2)}
Write a short, immersive narrative (1-2 sentences) describing what happened.
Do not include technical details like coordinates or flags.
Do NOT start your response with any label like "AI:" or "DM:". Start directly with the narrative.
"""

                    system_prompt = "You are a narrator. Respond directly with the narrative, without any labels or prefixes."
                    narrative_response = self.ollama.generate(
                        model="llama3.2:3b",
                        system=system_prompt,
                        prompt=narrative_prompt,
                        options={"temperature": 0.7},
                        stream=True
                    )
                    narrative = ""
                    for chunk in narrative_response:
                        # Extract the 'response' attribute correctly
                        if hasattr(chunk, 'response'):
                            narrative += chunk.response
                        elif isinstance(chunk, dict):
                            narrative += chunk.get("response", "")
                        else:
                            narrative += str(chunk)
                    print(f"[DEBUG] Raw narrative from model: {repr(narrative)}") 
                    result['message'] = narrative.strip() if narrative.strip() else result.get('message', 'Action completed.')
                except Exception as e:
                    print(f"[ERROR] Narrative generation failed: {e}")
                    result['message'] = result.get('message', 'Action completed.')
            
            return result
            
        except json.JSONDecodeError:
            return {"success": False, "message": "AI returned invalid JSON", "ai_response": full_response}
        except Exception as e:
            return {"success": False, "message": f"Tool execution error: {str(e)}", "ai_response": full_response}

    def generate_structured_data(self, prompt: str, response_format: dict) -> dict:
        """
        Generate structured data based on a prompt and response format
        Used for world building content generation
        """
        # Create system prompt for structured generation
        system_prompt = f"""
        You are a world building assistant. Generate structured data in JSON format.
        Respond ONLY with JSON that matches this format:
        {json.dumps(response_format, indent=2)}
        
        Do not include any other text or explanations.
        """
        
        # Generate response
        response_chunks = self.ollama.generate(
            model="llama3.2:3b",
            system=system_prompt,
            prompt=prompt,
            format="json",
            options={"temperature": 0.7},  # More creative for world building
            stream=True
        )
        
        # Collect response
        full_response = ""
        for chunk in response_chunks:
            full_response += chunk.get("response", "")
        
        try:
            return json.loads(full_response)
        except json.JSONDecodeError:
            # Try to extract JSON from malformed response
            try:
                json_match = re.search(r'\{.*\}', full_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return {"error": "Invalid JSON response", "raw": full_response}
            except:
                return {"error": "JSON parsing failed", "raw": full_response}

