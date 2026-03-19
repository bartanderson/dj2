# world/ai_integration.py
import re
import json
import inspect
import uuid
import random
import numpy as np
from typing import Dict, Any, Optional
from ollama import Client
from pgvector.psycopg2 import register_vector
from .tool_system import ToolRegistry, tool
from .dm_tools import DMTools
from .overlay import Overlay
from .world_map import Location
from .campaign import Quest, Faction, CampaignState

class BaseAI:
    def __init__(self, ollama_host="http://localhost:11434", seed=42):
        self.ollama = Client(host=ollama_host)
        self.seed = seed
        self.tool_registry = ToolRegistry()
        self.system_prompt = self._create_system_prompt()
        
    # def load_embedding_model(self):
    #     """Load sentence transformer model for embeddings"""
    #     return SentenceTransformer('all-MiniLM-L6-v2')
    
    # def generate_embedding(self, text):
    #     """Generate text embedding"""
    #     return self.embedding_model.encode([text])[0].tolist()

    # def load_embedding_model(self):
    #     """No need to load a model directly when using Ollama's API"""
    #     return None

    def generate_embedding(self, text):
        """Generate text embedding using Ollama's API"""
        try:
            response = self.ollama.embeddings(model='all-minilm:l6-v2', prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Fallback to a simple zero vector
            return [0.0] * 384  # all-minilm:l6-v2 has 384 dimensions
    
    def save_context_with_embedding(world_id, player_id, context_type, content, embedding):
        """Save context with embedding to database"""
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO narrative_context "
                    "(world_id, player_id, context_type, content, embedding) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (world_id, player_id, context_type, Json(content), embedding)
                )
                conn.commit()
        except Exception as e:
            print(f"Error saving context: {e}")
            conn.rollback()
        finally:
            conn.close()

    def find_similar_contexts(embedding, world_id=None, player_id=None, limit=5):
        """Find similar contexts using vector similarity"""
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        
        try:
            with conn.cursor() as cur:
                query = """
                    SELECT content, 1 - (embedding <=> %s) as similarity
                    FROM narrative_context
                    WHERE (%s IS NULL OR world_id = %s)
                    AND (%s IS NULL OR player_id = %s)
                    ORDER BY embedding <=> %s
                    LIMIT %s
                """
                cur.execute(query, (
                    embedding, 
                    world_id, world_id,
                    player_id, player_id,
                    embedding,
                    limit
                ))
                return cur.fetchall()
        except Exception as e:
            print(f"Error finding similar contexts: {e}")
            return []
        finally:
            conn.close()
    
    def generate_structured_data(self, prompt: str, response_format: dict) -> dict:
        """Generate structured data with deterministic seeding"""
        system_prompt = f"Respond ONLY with JSON matching this format:\n{json.dumps(response_format, indent=2)}"
        
        response = self.ollama.generate(
            model="llama3.2:3b",
            system=system_prompt,
            prompt=prompt,
            format="json",
            options={"temperature": 0.7, "seed": self.seed}
        )
        
        try:
            return json.loads(response["response"])
        except json.JSONDecodeError:
            # Fallback extraction
            match = re.search(r'\{.*\}', response["response"], re.DOTALL)
            return json.loads(match.group()) if match else {"error": "Invalid JSON"}

    def generate_text(self, prompt: str, temperature: float = 0.7, max_retries: int = 2) -> str:
        """Generate natural language text with robust error handling"""
        responses = [
           "Yes, err... I mean, well, um... no?",
           "As I see it, maybe, maybe not.",
           "Reply hazy, try again.",
           "Cannot predict now. Let's play it out a bit.",
           "You've got to know when to hold 'em, fold 'em, you get the picture, yeah?",
           "My sources say ... hmm? That's odd. What do you think?",
           "Outlook not so good, but who knows, right?",
           "Very doubtful but then again, it is your story to tell. Prove me wrong."
        ]
        for attempt in range(max_retries + 1):
            try:
                response = self.ollama.generate(
                    model="llama3.2:3b",
                    system="You are a helpful Assistant. Provide clear, informative responses, but you do not give away secrets, plots, story arcs or anything that will majorly further the character or party. If that is what is asked for, gently nudge the player into making a decision on their own.",
                    prompt=prompt,
                    options={"temperature": temperature, "seed": self.seed}
                )
                return response["response"]
            except Exception as e:
                if attempt == max_retries:
                    print(f"AI text generation failed after {max_retries} attempts: {e}")
                    # Return a graceful hazy fallback instead of raising
                    return random.choice(responses)
                print(f"AI text generation attempt {attempt + 1} failed: {e}")
                # Wait briefly before retrying
                time.sleep(0.5 * (attempt + 1))
        
        # This should never be reached but provides a safety net
        return "I'm at my wits end here. Perhaps you can figure it out on your own?"

    
    def process_command(self, natural_language: str) -> dict:
        """Core command processing pipeline"""
        # Get tools specification
        tools_spec = self.tool_registry.get_tools_spec()
        
        # Generate AI response
        response = self.ollama.generate(
            model="llama3.2:3b",
            system=self.system_prompt,
            prompt=natural_language,
            format="json",
            options={"temperature": 0.1}
        )
        
        try:
            response_json = json.loads(response["response"])
            tool_name = response_json["tool"]
            arguments = response_json["arguments"]
            
            # Execute tool
            result = self.tool_registry.execute_tool(tool_name, arguments)
            result["ai_response"] = response_json
            return result
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}", "response": response}
    
    def _create_system_prompt(self) -> str:
        """Base system prompt (to be overridden by subclasses)"""
        return "You are an AI assistant. Respond with JSON containing 'tool' and 'arguments'."

class WorldAI(BaseAI):
    # TODO: When adding new tools or updating tool invocation logic, always check that the tool name provided by the AI is valid and registered.
    # If the AI does not specify a valid tool, handle the request narratively and do not attempt tool execution.
    def __init__(self, campaign_state=None, world_controller=None, *args, **kwargs):
        # Handle both naming conventions during transition
        if campaign_state is not None:
            self.campaign_state = campaign_state
        elif world_controller is not None:
            self.campaign_state = world_controller
        else:
            raise ValueError("Either campaign_state or world_controller must be provided")

        super().__init__(*args, **kwargs)
        self.tool_registry.register_from_class(self)
        self._register_world_tools()
        
    def _create_system_prompt(self) -> str:
        """World-specific system prompt"""
        tools_spec = self.tool_registry.get_tools_spec()
        return f"""
        You are a World Master in a fantasy RPG. Your responsibilities:
        - Manage world state and locations
        - Generate quests and narrative content
        - Handle travel between locations
        - Maintain faction relationships

        Available Tools (JSON format):
        {json.dumps(tools_spec, indent=2)}

        IMPORTANT:
        - Only use tools listed above. Do NOT call tools that are not registered or shown.
        - If a player request cannot be handled by a tool, respond narratively as a DM would, gently guiding the player and making up details as needed.
        - If the player goes off the designed path, improvise and help them make choices, keeping the story engaging and interactive.

        Always respond with JSON containing:
        {{
            "thoughts": "Reasoning",
            "tool": "tool_name or null",
            "arguments": {{...}} or null,
            "narrative": "Your DM response if no tool is used"
        }}
        """
    
    def _register_world_tools(self):
        """Register world-specific tools"""
        # Additional tools can be added here
        pass
    
    @tool(
        name="generate_location",
        description="Create a new location in the world",
        terrain_type="Type of terrain (forest, mountains, plains, etc.)",
        significance="Importance of location (major, minor, hidden)"
    )
    def generate_location(self, terrain_type: str, significance: str) -> dict:
        """Generate a new location using AI"""
        prompt = f"Create a {significance} {terrain_type} location with name, description, and features"
        response_format = {
            "name": "string",
            "description": "string",
            "features": ["list", "of", "features"],
            "services": ["list", "of", "services"]
        }
        
        location_data = self.generate_structured_data(prompt, response_format)
        location_id = f"loc_{uuid.uuid4().hex[:6]}"
        
        # Create and add location to world state
        location = Location(
            id=location_id,
            name=location_data["name"],
            type=terrain_type,
            description=location_data["description"],
            features=location_data.get("features", []),
            services=location_data.get("services", [])
        )
        self.campaign_state.add_location(location)
        
        return {"success": True, "location_id": location_id}
    
    @tool(
        name="create_quest",
        description="Generate a new quest for a location",
        location_id="ID of the location where quest starts",
        quest_type="Type of quest (rescue, retrieval, elimination)"
    )
    def create_quest(self, location_id: str, quest_type: str) -> dict:
        """Generate a new quest using AI"""
        location = self.campaign_state.get_location(location_id)
        if not location:
            return {"success": False, "message": "Location not found"}
        
        prompt = f"Create a {quest_type} quest starting at {location.name} with objectives"
        response_format = {
            "title": "string",
            "description": "string",
            "objectives": ["list", "of", "objectives"]
        }
        
        quest_data = self.generate_structured_data(prompt, response_format)
        quest_id = f"quest_{uuid.uuid4().hex[:6]}"
        
        # Create and add quest to world state
        quest = Quest(
            id=quest_id,
            title=quest_data["title"],
            description=quest_data["description"],
            objectives=quest_data["objectives"],
            location_id=location_id
        )
        self.campaign_state.add_quest(quest)
        location.quests.append(quest_id)
        
        return {"success": True, "quest_id": quest_id}

class DungeonAI(BaseAI):
    def __init__(self, dungeon_state=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dungeon_state = dungeon_state
        self.dm_tools = DMTools(dungeon_state) if dungeon_state else None
        # Register tools only if state is available
        if self.dm_tools:
            self.tool_registry.register_from_class(self.dm_tools)
        self.tool_registry.register_from_class(self) # always register it for its tools?

        self.system_prompt = self._create_system_prompt()

    def process_command(self, natural_language: str) -> dict:
        """Handle case where dungeon state is missing"""
        if not self.dungeon_state:
            return {
                "success": False,
                "message": "Dungeon state not initialized"
            }
        return super().process_command(natural_language)
        
    def _create_system_prompt(self) -> str:
        """Dungeon-specific system prompt"""
        primitives_desc = "\n".join([
            f"- {prim}: Parameters: {self._get_primitive_params(prim)}"
            for prim in Overlay.PRIMITIVE_TYPES
        ])
        
        return f"""
        You are a Dungeon Master. Your responsibilities:
        - Manage dungeon layout and rooms
        - Place traps, monsters, and treasure
        - Describe dungeon environments
        - Handle dungeon exploration mechanics
        
        Important Rules:
        1. Use relative coordinates (0.0-1.0) within cells
        2. Specify colors in hexadecimal format (#RRGGBB)
        3. For overlays: Available types: {primitives_desc}
        
        Always respond with JSON containing:
        {{
            "thoughts": "Reasoning",
            "tool": "tool_name",
            "arguments": {{...}}
        }}
        """
    
    def _get_primitive_params(self, primitive):
        """Get parameters for overlay primitives"""
        params = {
            "circle": "size (0.1-1.0)",
            "square": "size (0.1-1.0), rotation",
            "triangle": "size (0.1-1.0), rotation",
            "line": "start_x, start_y, end_x, end_y (0.0-1.0), width",
            "text": "content, size",
            "polygon": "points (list of [x,y] coordinates)"
        }
        return params.get(primitive, "")
    
    @tool(
        name="inspect_cell",
        description="Get detailed information about a dungeon cell",
        x="X coordinate",
        y="Y coordinate"
    )
    def inspect_cell(self, x: int, y: int) -> dict:
        """Get cell inspection details"""
        cell = self.dungeon_state.get_cell(x, y)
        if not cell:
            return {"success": False, "message": "Cell not found"}
        
        return {
            "success": True,
            "type": str(cell.type),
            "description": cell.description,
            "entities": [e.type for e in cell.entities],
            "overlays": len(cell.overlays)
        }