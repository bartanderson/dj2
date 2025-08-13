# File: dungeon_neo/ai_integration.py
from .tool_system import ToolRegistry, tool
from ollama import Client
from .dm_tools import DMTools
from .overlay import Overlay
import re
import json

class DungeonAI:
    def __init__(self, dungeon_state, ollama_host="http://localhost:11434"):
        self.state = dungeon_state
        self.ollama = Client(host=ollama_host)
        self.tool_registry = ToolRegistry()
        
        # Register tools from this class
        self.tool_registry.register_from_class(self)
        
        # Register tools from DMTools
        self.dm_tools = DMTools(dungeon_state)
        self.tool_registry.register_from_class(self.dm_tools)

        # If we need to register other tools, do it like DMTools above
        #
        #
        #
        #
        #

        
        # Generate dynamic system prompt
        self.system_prompt = self._create_system_prompt()

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
        """Create prompt with dynamic tool descriptions"""
        tools_spec = self.tool_registry.get_tools_spec()
        tools_json = json.dumps(tools_spec, indent=2)

        primitives_desc = "\n".join([
            f"- {prim}: Parameters: {self._get_primitive_params(prim)}"
            for prim in Overlay.PRIMITIVE_TYPES
        ])
        
        return f"""
        You are a Dungeon Master (but currently testing assistant) in a D&D type game. 
        The player can give you commands to interact with the dungeon. Follow these rules:

        1. ALWAYS respond with VALID JSON containing "thoughts", "tool", and "arguments"
        2. NEVER output tool specifications - only use them
        3. Use this exact JSON format:
            {{
                "thoughts": "Brief reasoning",
                "tool": "tool_name",
                "arguments": {{"arg1": value, "arg2": value}}
            }}
        4. Only use the tools provided
        5. Use simple, direct commands
        6. For movement: 'move_party direction steps'
        7. If a request requires multiple steps, break it into separate responses
        8. If there is a color, Always specify color parameter as hexadecimal (#000000 - #FFFFFF)
        9. If you need to set positions withing a cell, use relative coordinates (0.0-1.0)
        10. If overlay - Available types that you could possibly combine serially:
        {primitives_desc}

        Available tools (DO NOT OUTPUT THESE):
        {tools_json}

        Important command mappings:
        - "debug grid" -> use "get_debug_grid" tool
        - "reset" -> use "reset_dungeon" tool
        """

    @tool(
        name="inspect_cell",
        description="Get detailed information about a dungeon cell",
        x="X coordinate (number)",
        y="Y coordinate (number)"
    )
    def inspect_cell(self, x: int, y: int) -> dict:
        """Get detailed information about a cell"""
        cell = self.state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": f"No cell at ({x}, {y})"}
        
        # Get readable cell type from DMTools
        cell_type = self.tools.get_cell_type(x, y)
        
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
        name="get_current_position",
        description="Get the party's current position: if you have x,y then you don't use this"
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
        #print(f"\n=== FULL SYSTEM PROMPT ===\n{self.system_prompt}\n")
        print(f"\n=== USER COMMAND ===\n{natural_language}\n")
        # Generate response chunks
        response_chunks = self.ollama.generate(
            #model="deepseek-r1:8b",
            model="llama3.1:8b",
            system=self.system_prompt,
            prompt=natural_language,
            format="json",
            options={"temperature": 0.1},
            stream=True  # Enable streaming to get chunks
        )
        
        # Collect all response chunks
        full_response = ""
        for chunk in response_chunks:
            full_response += chunk.get("response", "")

        print(f"AI DBG Response{full_response}")
        
        try:
            # Parse the full response
            response_json = json.loads(full_response)
            tool_name = response_json.get("tool")
            arguments = response_json.get("arguments", {})
            
            # Execute the selected tool
            result = self.tool_registry.execute_tool(tool_name, arguments)
            # Add debug info to response
            debug_info = self.log_tool_call(tool_name, arguments)
            result["debug_info"] = debug_info
            return result
        except json.JSONDecodeError:
            return {"success": False, "message": "AI returned invalid JSON"}
        except Exception as e:
            return {
                "success": False,
                "message": f"Tool execution error: {str(e)}",
                "ai_response": full_response  # Use the full_response variable
            }

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
            model="llama3.1:8b",
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

