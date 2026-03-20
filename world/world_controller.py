# world_controller.py
"""
WorldController Module
=====================

Active Record pattern combining world state management with system coordination.
See class docstring for architectural details.
"""
import json
import math
import random
import uuid
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from collections import Counter

from world import dnd_data
from world.db import Database
from world.utils import convex_hull, cross
from world.world_map import WorldMap, Location
from world.campaign import Region, Faction, Quest, CampaignState
from world.narrative_system import NarrativeSystem
from world.character_builder import CharacterBuilder
from world.character import Character
from world.persistence import WorldManager
from world.dm_chat_ai import DMChatAI
from world.ai_integration import WorldAI, DungeonAI # <---- soon we have to work on dungeon too
from world.world_session import SessionManager
from world.ai_dungeon_master import AIDungeonMaster, Dialog # AIDungeonMaster also imported in narrative_system.py
from engine.game_engine import GameEngine, GamePhase
from .terrain import TerrainGenerator
from .paths import PathGenerator
from .map_utils import MapUtils
from .party_manager import PartyManager
from .quest_manager import QuestManager
from .character_manager import CharacterManager
from world.dm_chat_handler import DMChatHandler
from world.player import Player           
from world.consequence_engine import ConsequenceEngine
from world.tool_system import ToolRegistry
from world.authority_system import AuthoritySystem
from world.encounter_models import EncounterPoint
from world.bestiary import Monster


import warnings
warnings.filterwarnings("ignore", message=".*Triton.*")
warnings.filterwarnings("ignore", message=".*redirects.*")

"""
ARCHITECTURAL OVERVIEW: ACTIVE RECORD PATTERN
=============================================

This WorldController uses the Active Record pattern, meaning it serves as BOTH:
1. A Controller (coordinator between systems)
2. A Data Model (campaign state containing locations, quests, factions)

This design choice was made because:
- It simplifies the initial implementation
- It reduces abstraction layers during prototyping  
- It's common in game development for world-state management

Key Implications:
1. WorldAI receives this controller as its "campaign_state"
2. The controller delegates to internal managers (WorldMap, QuestManager, etc.)
3. Phase enforcement happens via GameEngine when it's active

State Models in the System:
- Campaign State: This controller (Active Record pattern)
- Narrative State: AIDungeonMaster.game_state
- Game Engine State: GameEngine (planned, partially implemented)
- AI State: Distributed across AI systems

For future refactoring: Consider separating state from controller if:
1. Testing becomes difficult
2. Concurrent access is needed
3. State persistence requirements change
"""

class WorldController:
    def __init__(self, world_id: str, ai_system: Any, seed: int = 42):
        # Initialize core components
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        self.terrain_generator = TerrainGenerator(seed)
        self.path_generator = PathGenerator(seed)
        self.map_utils = MapUtils(seed)
        self.world_map = WorldMap()
        self.starting_location_id = None
        
        # Create dm_chat_ai FIRST (needed by many systems)
        self.dm_chat_ai = DMChatAI(ai_system)

        # Initialize authority system with proper tool registry
        self.tool_registry = ToolRegistry()
        self.authority_system = AuthoritySystem(self.tool_registry)

        # Create ConsequenceEngine immediately after dm_chat_ai
        self.consequence_engine = ConsequenceEngine(
            world_controller=self,
            dm_chat_ai=self.dm_chat_ai
        )

        # For backward compatibility, point dungeon_master to the new engine
        self.dungeon_master = self.consequence_engine

        # Now create other systems that depend on dm_chat_ai or consequence_engine

        self.narrative_system = NarrativeSystem(self, ai_system, dm_chat_ai=self.dm_chat_ai)
        self.character_builder = CharacterBuilder(ai_system)
        
        # Register character builder tools for AI use
        if hasattr(ai_system, 'tool_registry'):
            ai_system.tool_registry.register_from_class(self.character_builder)
        
        self.ai_system = ai_system
        self.terrain_types = self.terrain_generator.terrain_types
        self.fog_of_war = True

        # Initialize state tracking
        self.session_log: List[str] = []
        self.current_location: Optional[Location] = None
        
        self.default_party_id = "main_party"

        # Initialize players
        self.players: Dict[str, Player] = {}
        self.session_players: Dict[str, str] = {}  # session_id -> player_id
        
        

        # Load OG System campaign data
        campaign_json = dnd_data._get_campaign_data()   # returns the whole 14_campaign.json dict
        if not campaign_json:
            print("[WARN] Campaign data not found; using minimal defaults.")
            campaign_json = {"campaign": {}}

        campaign_data = campaign_json.get("campaign", {})
        self.campaign_data = campaign_data

        # Create CampaignState with seed and metadata
        self.campaign_state = CampaignState(
            world_seed=str(self.seed),
            generation_timestamp=datetime.now().isoformat(),
            og_system_version=campaign_data.get("meta", {}).get("schema_version", "1.0")
        )

        # Set core game state via campaign_state
        self.campaign_state.game_time = 0
        self.campaign_state.time_factor = 1  
        self.campaign_state.game_started = False


        # Load calendar rules
        time_tracking = campaign_data.get("time_tracking", {})
        calendar_data = time_tracking.get("calendar", {})
        self.campaign_state.load_calendar_rules(calendar_data)


        # Load static factions from JSON
        factions_data = campaign_data.get("faction_system", {}).get("factions", [])
        for f_data in factions_data:
            faction = Faction.from_json(f_data)
            self.campaign_state.factions[faction.id] = faction

        # Store quest archetypes for later generation
        self.quest_archetypes = campaign_data.get("quest_system", {}).get("quest_archetypes", {})

        # Load player narrative framework
        narrative_json = dnd_data._get_player_narrative_data()
        print("[WorldController] narrative_json keys:", narrative_json.keys() if narrative_json else "None")
        if narrative_json and narrative_json.get("player_narrative"):
            self.narrative_framework = narrative_json.get("player_narrative")
            print("[WorldController] self.narrative_framework keys:", self.narrative_framework.keys())
        else:
            print("[WorldController] No player_narrative found, using fallback")
            self.narrative_framework = {
                "backstory_framework": {
                    "phases": [
                        {
                            "phase": "origin",
                            "prompts": ["Where were you born?", "What was your family like?", "Why did you leave?"]
                        },
                        {
                            "phase": "formative_wound",
                            "prompts": ["What event changed you?", "Who was involved?", "What did you vow?"]
                        },
                        {
                            "phase": "recent_history",
                            "prompts": ["What were you doing 6 months ago?", "Who did you wrong?", "What opportunity did you seize?"]
                        }
                    ],
                    "secret_generation": {
                        "types": {
                            "lineage": "secret lineage",
                            "connection": "secret connection",
                            "prophecy": "prophecy"
                        },
                        "revelation_triggers": [
                            {"type": "random", "target": ""}
                        ]
                    }
                }
            }

        # Now create narrative system (it will access self.narrative_framework)
        self.narrative_system = NarrativeSystem(self, ai_system, dm_chat_ai=self.dm_chat_ai)

        # Minimal world generation (placeholder)
        if not self.campaign_state.surface_regions:
            self.generate_world_structure()

        # Initialize world manager and load world data
        self.world_manager = WorldManager(ai_system)
        self.world_data = self.world_manager.load_from_db(world_id)
        
        # Set up the world
        self.setup_world(self.world_data)
        
        # Set starting location
        starting_location = None
        self.starting_location_id = None
        # After loading all locations, find the tavern and set its grid position
        grid_w = self.campaign_state.grid_width
        grid_h = self.campaign_state.grid_height
        if grid_w and grid_h:
            center_col = grid_w // 2
        for location in self.world_map.locations.values():
            if location.type == "tavern" and "adventurer" in location.name.lower(): #and "respite" in location.name.lower():
                starting_location = location
                break

        if starting_location:
            print("Found starting location")
            self.starting_location_id = starting_location.id
            self.reveal_location(starting_location.id)
            self.travel_to_location(starting_location.id)
        else:
            # Fallback to first location if no tavern found
            first_location_id = list(self.world_map.locations.keys())[0]
            self.starting_location_id = first_location_id
            self.reveal_location(first_location_id)
            self.travel_to_location(first_location_id)

        # Initialize managers
        self.quest_manager = QuestManager()
        self.party_manager = PartyManager(self.starting_location_id)
        self.character_manager = CharacterManager(self.character_builder)

        # Give character_manager a reference to this world controller
        self.character_manager.set_world_controller(self)

        # What was this trying to do. Is there an equivalent or is this unneeded?
        # # Transfer existing quests from world data to quest manager
        # for quest_id, quest in self.quest_manager.quests.items():
        #     self.quest_manager.quests[quest_id] = quest
        # self.quest_manager.quests = {}  # Clear old quests dict

        # # Transfer existing characters to character manager
        # self.character_manager.characters = self.character_manager.characters
        # self.character_manager.characters = {}  # Clear old characters dict

        # Initialize GameEngine for phase compliance
        try:
            self.game_engine = GameEngine(self)
            print(f"[OK] GameEngine initialized for world {world_id}")
            print(f"  Phase enforcement: ACTIVE")
        except Exception as e:
            print(f"[FAIL] Failed to initialize GameEngine: {e}")
            print(f"  Continuing without phase enforcement")
            self.game_engine = None

        from .session_system import SessionSystem
        self.session_system = SessionSystem()

        # Initialize AI systems
        self.world_ai = WorldAI(campaign_state=self)
        self.dungeon_ai = None  # Will be initialized when entering dungeon
        self.session_manager = SessionManager()

        # No need to create AIDungeonMaster here; we already have consequence_engine.
        # But if some legacy code still expects dungeon_master to be an AIDungeonMaster instance,
        # we could keep it, but we've already set dungeon_master = consequence_engine.
        # We'll leave it as is.

        # Finally, create DMChatHandler (needs consequence_engine, which is now available)
        self.dm_chat_handler = DMChatHandler(self)

        print(f"[OK] ConsequenceEngine initialized: {hasattr(self.dungeon_master, 'dm_chat_ai')}")




        print(f"[TEST] Loaded {len(self.campaign_state.factions)} factions: {list(self.campaign_state.factions.keys())}")
        print(f"[TEST] Loaded {len(self.campaign_state.quests)} quests from database")

    def _generate_encounter_points_for_region(self, region_id: str, region_hexes: list, rng: random.Random) -> dict:
        """
        Generate encounter points for a single region.
        Returns a dict {point_id: EncounterPoint dict}.
        """
        density = 0.05   # 5% of hexes become points – adjust as desired
        point_dict = {}
        # Use a deterministic RNG derived from region seed (but we'll just use the passed rng)
        region_rng = random.Random(rng.getrandbits(64))

        for hex in region_hexes:
            if region_rng.random() < density:
                point_id = f"{region_id}_enc_{len(point_dict)}"
                terrain = hex["terrain"]
                type_hint = self._choose_point_type(terrain, region_rng)
                point = EncounterPoint(
                    point_id=point_id,
                    region_id=region_id,
                    x=hex["x"],
                    y=hex["y"],
                    type_hint=type_hint
                )
                point_dict[point_id] = point.to_dict()
        return point_dict

    def _choose_point_type(self, terrain: str, rng: random.Random) -> str:
        """Simple terrain‑to‑type mapping – expand as desired."""
        mapping = {
            "plains": ["camp", "hunting_ground"],
            "forest": ["camp", "lair", "hunting_ground"],
            "mountain": ["cave", "lair", "ruin"],
            "swamp": ["lair", "ruin", "camp"],
            "desert": ["ruin", "camp"],
            "coast": ["camp", "lair"],
        }
        options = mapping.get(terrain, ["camp"])
        return rng.choice(options)

    def generate_world_structure(self):
        """Generate hex grid and regions from seed and campaign parameters."""
        import random
        import math
        from collections import defaultdict

        # Get generation parameters from stored campaign_data
        world_gen = self.campaign_data.get("world_generation", {})
        surface = world_gen.get("world_layers", {}).get("surface", {})
        hex_grid_params = surface.get("hex_grid", {})
        print(f"Hex grid size from JSON: {hex_grid_params.get('size')}")
        size_str = hex_grid_params.get("size", "50x50")
        try:
            w, h = map(int, size_str.split('x'))
        except:
            w, h = 50, 50
        print(f"Width: { w }, Height: { h }")
        self.campaign_state.grid_width = w
        self.campaign_state.grid_height = h
        self.campaign_state.hex_size = 60  # could also come from JSON

        terrain_types = hex_grid_params.get("terrain_types", 
            ["plains", "forest", "mountain", "swamp", "desert", "coast", "urban"])

        # Use a deterministic RNG based on the seed
        seed = int(self.campaign_state.world_seed) if self.campaign_state.world_seed else 42
        rng = random.Random(seed)

        # Generate a simple terrain grid (random with smoothing)
        terrain_grid = [[rng.choice(terrain_types) for _ in range(w)] for _ in range(h)]

        # ----- Smoothing pass to create larger contiguous areas -----
        smooth_iterations = 3  # adjust as needed; more iterations = larger regions
        # Define neighbor offsets for hex grid (flat-top, axial coordinates)
        # For a given (x,y) in a rectangular grid approximating hexes, we use:
        neighbors = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, -1)  # these approximate diagonals for hex connectivity
        ]
        for _ in range(smooth_iterations):
            new_grid = [row[:] for row in terrain_grid]  # copy
            for y in range(h):
                for x in range(w):
                    # Collect terrain of current cell and its valid neighbors
                    terrain_counts = Counter()
                    terrain_counts[terrain_grid[y][x]] += 1
                    for dx, dy in neighbors:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            terrain_counts[terrain_grid[ny][nx]] += 1
                    # Set to most common terrain (mode)
                    most_common = terrain_counts.most_common(1)[0][0]
                    new_grid[y][x] = most_common
            terrain_grid = new_grid
        # -------------------------------------------------------------

        # Convert to hex list (axial coordinates or pixel coordinates)
        hexes = []
        for y in range(h):
            for x in range(w):
                # Convert to pixel coordinates (flat-top hex grid)
                x_pos = x * self.campaign_state.hex_size * 0.75
                y_pos = y * self.campaign_state.hex_size + (self.campaign_state.hex_size/2 if x % 2 else 0)
                hexes.append({
                    "x": x_pos,
                    "y": y_pos,
                    "grid_x": x,
                    "grid_y": y,
                    "terrain": terrain_grid[y][x],
                    "region_id": None
                })

        # Cluster hexes into regions using flood fill
        region_id_counter = 0
        visited = set()
        regions = {}  # This will hold the region objects keyed by ID

        def flood_fill(start_x, start_y, terrain):
            stack = [(start_x, start_y)]
            region_hexes = []
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in visited or cx < 0 or cx >= w or cy < 0 or cy >= h:
                    continue
                if terrain_grid[cy][cx] != terrain:
                    continue
                visited.add((cx, cy))
                region_hexes.append((cx, cy))
                # Add neighbors (axial neighbors for hex grid)
                # For simplicity, we'll use 4-directional neighbors plus two diagonals
                # Adjust based on actual hex connectivity
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1), (1,1), (-1,-1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        stack.append((nx, ny))
            return region_hexes

        for y in range(h):
            for x in range(w):
                if (x, y) not in visited:
                    terrain = terrain_grid[y][x]
                    hex_list = flood_fill(x, y, terrain)
                    if hex_list:
                        region_id = f"region_{region_id_counter}"
                        region_id_counter += 1
                        # Compute region centroid (average grid coordinates)
                        avg_col = sum(hx for hx, hy in hex_list) / len(hex_list)
                        avg_row = sum(hy for hx, hy in hex_list) / len(hex_list)
                        # Determine danger level based on terrain
                        danger = self._terrain_danger(terrain)
                        # Create Region object (import Region from campaign)
                        from world.campaign import Region
                        region = Region(
                            id=region_id,
                            name=f"{terrain.capitalize()} Region",
                            terrain_tags=[terrain],
                            faction_control="contested",
                            danger_level=danger,
                            discovered=False,
                            explored=0.0,
                            settlements=[],
                            dungeons=[],
                            active_quests=[]
                        )
                        regions[region_id] = region
                        # Assign region_id to hexes
                        for hx, hy in hex_list:
                            for hex_item in hexes:
                                if hex_item["grid_x"] == hx and hex_item["grid_y"] == hy:
                                    hex_item["region_id"] = region_id
                                    break

        # Store in campaign_state
        self.campaign_state.surface_regions = regions
        self.campaign_state.hex_grid = hexes
        self.campaign_state.terrain_grid = terrain_grid

        # Initialize potential_locations dict if not present
        if not hasattr(self.campaign_state, 'potential_locations'):
            self.campaign_state.potential_locations = {}

        # Generate potential locations for each region
        for region_id, region in regions.items():
            # Number of settlements (0-3) based on region terrain
            if region.terrain_tags[0] in ["plains", "coast"]:
                num_settlements = rng.randint(0, 3)
            else:
                num_settlements = rng.randint(0, 2)
            for i in range(num_settlements):
                # Get all hexes in this region
                region_hexes = [(h["grid_x"], h["grid_y"]) for h in hexes if h["region_id"] == region_id]
                if not region_hexes:
                    continue
                col, row = rng.choice(region_hexes)
                pot_id = f"settlement_{region_id}_{i}"
                region.settlements.append(pot_id)
                self.campaign_state.potential_locations[pot_id] = {
                    "region_id": region_id,
                    "col": col,
                    "row": row,
                    "type": "settlement"
                }
            # Number of dungeons (0-2) based on terrain
            if region.terrain_tags[0] in ["mountain", "forest", "swamp"]:
                num_dungeons = rng.randint(0, 2)
            else:
                num_dungeons = rng.randint(0, 1)
            for i in range(num_dungeons):
                region_hexes = [(h["grid_x"], h["grid_y"]) for h in hexes if h["region_id"] == region_id]
                if not region_hexes:
                    continue
                col, row = rng.choice(region_hexes)
                pot_id = f"dungeon_{region_id}_{i}"
                region.dungeons.append(pot_id)
                self.campaign_state.potential_locations[pot_id] = {
                    "region_id": region_id,
                    "col": col,
                    "row": row,
                    "type": "dungeon"
                }

        # Note this is outside of the for loop above
        # Generate encounter points for each region
        # We need a deterministic RNG for the whole world; use self.rng (already seeded)
        for region_id, region in self.campaign_state.surface_regions.items():
            # Collect hexes belonging to this region
            region_hexes = [h for h in self.campaign_state.hex_grid if h.get("region_id") == region_id]
            if region_hexes:
                points = self._generate_encounter_points_for_region(region_id, region_hexes, self.rng)
                region.encounter_points.update(points)

        print(f"[WORLD] Generated {len(regions)} regions, {len(self.campaign_state.potential_locations)} potential locations")
        print(f"[WORLD] Hex grid generated: {len(self.campaign_state.hex_grid)} hexes")
        print(f"[ENCOUNTER] Generated {sum(len(r.encounter_points) for r in self.campaign_state.surface_regions.values())} encounter points.")

    def test_generate_random_encounter(self):
        """Test: pick a random untouched encounter point and generate an encounter."""
        import random
        # Collect all untouched points
        untouched = []
        for region in self.campaign_state.surface_regions.values():
            for point_id, point_dict in region.encounter_points.items():
                if point_dict.get("state") == "untouched":
                    untouched.append((region, point_id, point_dict))
        if not untouched:
            print("No untouched encounter points found.")
            return None
        # Pick one at random
        region, point_id, point_dict = random.choice(untouched)
        from world.encounter_models import EncounterPoint
        point = EncounterPoint.from_dict(point_dict)
        print(f"Testing encounter at point {point_id} ({point.type_hint}) in region {region.name}")
        # Build context
        context = {
            "point_id": point.id,
            "party_level": 3,   # placeholder
            "party_size": 4,
            "region": {
                "danger_level": region.danger_level,
                "terrain": region.terrain_tags[0] if region.terrain_tags else "plains",
                "faction": region.faction_control
            },
            "point_type": point.type_hint
        }
        from world.encounter_generator import generate_encounter
        encounter = generate_encounter(context)
        # Activate the point
        point.activate(encounter.id)
        region.encounter_points[point_id] = point.to_dict()
        # Store encounter
        if not hasattr(self, 'active_encounters'):
            self.active_encounters = {}
        self.active_encounters[encounter.id] = encounter
        # Print result
        print(f"Generated encounter: {encounter.description}")
        for m in encounter.monsters:
            monster_data = Monster.get(m.monster_id)
            print(f"  - {monster_data.name} (HP {m.current_hp})")
        return encounter

    def _terrain_danger(self, terrain: str) -> int:
        """Return danger level (1-5) for a given terrain type."""
        mapping = {
            "plains": 1,
            "forest": 2,
            "hills": 3,
            "mountain": 5,
            "swamp": 4,
            "desert": 3,
            "coast": 1,
            "urban": 1,
            "ocean": 0,      # not typically traversable
            "lake": 0,
            "river": 0
        }
        return mapping.get(terrain, 1)  # default 1 for unknown terrains
    
    def generate_location_from_potential(self, pot_id: str) -> Optional[Location]:
        pot = self.campaign_state.potential_locations.get(pot_id)
        if not pot:
            return None
        region = self.campaign_state.surface_regions.get(pot["region_id"])
        if not region:
            return None

        loc_seed = f"{self.campaign_state.world_seed}:{pot_id}"
        rng = random.Random(loc_seed)

        if pot["type"] == "settlement":
            name = self._generate_settlement_name(region, rng)
            loc_type = self._determine_settlement_type(region, rng)
            dungeon_type = None
            dungeon_level = None
        else:
            name = self._generate_dungeon_name(region, rng)
            loc_type = "dungeon"
            dungeon_type = self._determine_dungeon_type(region, rng)
            dungeon_level = region.danger_level

        description = f"A {loc_type} in the {region.name}."

        location = Location(
            id=pot_id,
            name=name,
            type=loc_type,
            description=description,
            col=pot["col"],
            row=pot["row"],
            dungeon_type=dungeon_type,
            dungeon_level=dungeon_level,
            discovered=False
        )
        self.world_map.add_location(location)
        return location

    def setup_world(self, world_data):
        """Load world data into game systems"""
        # Extract seed from world_data with a fallback
        self.seed = world_data.get("seed", 42)
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        # 1. Load locations
        for loc_data in world_data["locations"]:
            # Handle both database and JSON formats
            if "data" in loc_data:  # Database format
                loc = loc_data["data"]
            else:  # Direct JSON format
                loc = loc_data
                
            # Create Location object
            location = Location(
                id=loc["id"],
                name=loc["name"],
                type=loc["type"],
                description=loc["description"],
                # Set grid coordinates – for now, default to (0,0) or calculate
                col=loc.get("col", 0),   # if saved, use; else default
                row=loc.get("row", 0),
                # Legacy pixel coordinates (still read from DB if present)
                x=loc.get("x", 0),
                y=loc.get("y", 0),
                dungeon_type=loc.get("dungeon_type"),
                dungeon_level=loc.get("dungeon_level", 1),
                image_url=loc.get("image_url"),
                features=loc.get("features", []),
                services=loc.get("services", []),
                discovered=loc.get("discovered", False)
            )
            
            # Set discovery status
            location.discovered = loc.get("discovered", False)
            
            # Initialize quests list
            location.quests = loc.get("quests", [])
            
            # Add to world map
            self.world_map.add_location(location)
        
        # 2. Create connections between locations
        location_ids = [loc.id for loc in self.world_map.locations.values()]
        for i in range(len(location_ids) - 1):
            self.world_map.connect_locations(location_ids[i], location_ids[i+1])
        
        # 3. Load quests
        for quest_data in world_data["quests"]:
            if "data" in quest_data:
                q = quest_data["data"]
            else:
                q = quest_data
            # Create quest using the new Quest class (which expects more fields)
            # We need to map old fields to new structure. For now, we'll create a minimal Quest
            # that matches the new schema. We'll use archetype=None, etc., because old data may not have them.
            quest = Quest(
                id=q["id"],
                archetype=q.get("archetype", "unknown"),   # fallback
                patron=q.get("patron", ""),                 # fallback
                target=q["location_id"],                     # treat location as target
                opposition=q.get("opposition", []),
                stages=[{                                     # create a single stage from old data
                    "order": 1,
                    "type": "travel",
                    "location": q["location_id"],
                    "completion_condition": "arrive",
                    "rewards": []
                }],
                consequences={
                    "success": {},
                    "failure": {},
                    "ignored": {}
                },
                time_pressure={"exists": False},
                completed=q.get("completed", False)
            )
            self.campaign_state.quests[quest.id] = quest    # store in campaign state

            # Update location quest list (if location exists)
            location = self.world_map.get_location(quest.target)
            if location:
                if not hasattr(location, 'quests'):
                    location.quests = []
                location.quests.append(quest.id)
        
        # 4. Load factions (if any)
        for faction_data in world_data.get("factions", []):
            # Handle both database and JSON formats
            if "data" in faction_data:  # Database format
                fac = faction_data["data"]
            else:  # Direct JSON format
                fac = faction_data
                
            faction = Faction(
                id=fac["id"],
                name=fac["name"],
                ideology=fac["ideology"],
                goals=fac["goals"]
            )
            # Add relationships if they exist
            if "relationships" in fac:
                faction.relationships = fac["relationships"]
            if "activities" in fac:
                faction.activities = fac["activities"]
                
            # Add to world state
            self.world_map.factions[faction.id] = faction
        
        # 5. Generate terrain
        self.terrain_grid = self.terrain_generator.generate_terrain()
        self.hexes = self.terrain_generator.generate_hex_map(self.terrain_grid)
        # location dicts not part of the object, just a temp var to simplify self.paths call
        location_dicts = [loc.to_dict() for loc in self.world_map.locations.values()]
        self.paths = self.path_generator.generate_paths(location_dicts, self.hexes)

    def get_quests_for_location(self, location_id: str) -> List[Quest]:
        """Return all quests (active or completed) that involve this location."""
        result = []
        for quest in self.campaign_state.quests.values():
            # Check if any stage references this location
            for stage in quest.stages:
                if stage.get("location") == location_id:
                    result.append(quest)
                    break
            # Also check if the target is this location
            if quest.target == location_id:
                if quest not in result:
                    result.append(quest)
        return result

    def _get_terrain_for_location(self, location, hexes):
        """Determine terrain type for a location based on nearby hexes"""
        # Handle case where no hexes are available
        if not hexes:
            return "plains"  # Default terrain

        # Find the closest hex to the location
        closest_hex = None
        min_distance = float('inf')
        
        for hex in hexes:
            distance = math.sqrt((location['x']-hex['x'])**2 + (location['y']-hex['y'])**2)
            if distance < min_distance:
                min_distance = distance
                closest_hex = hex
        
        # Return the terrain of the closest hex
        return closest_hex.get("terrain", "plains")  # Added .get() for safety

    # TODO: will need to fix/replace with og_system data/methods
    def _connect_regions(self, centroids, regions, hexes):
        """Connect regions using direct paths between closest points"""
        paths = []
        if len(centroids) < 2:
            return paths
        
        # Find closest region pairs
        region_pairs = []
        for i in range(len(centroids)):
            for j in range(i+1, len(centroids)):
                dist = math.sqrt((centroids[i]['x']-centroids[j]['x'])**2 + 
                                 (centroids[i]['y']-centroids[j]['y'])**2)
                region_pairs.append((dist, i, j))
        
        # Sort by distance
        region_pairs.sort(key=lambda x: x[0])
        
        # Connect closest regions first
        connected_regions = set()
        for dist, i, j in region_pairs:
            if i not in connected_regions or j not in connected_regions:
                # Find closest locations between regions
                start_loc = min(centroids[i]['region'], 
                               key=lambda loc: math.sqrt((loc['x']-centroids[j]['x'])**2 + 
                                                        (loc['y']-centroids[j]['y'])**2))
                end_loc = min(centroids[j]['region'], 
                             key=lambda loc: math.sqrt((loc['x']-centroids[i]['x'])**2 + 
                                                      (loc['y']-centroids[i]['y'])**2))
                
                path_points = self._create_organic_path(start_loc, end_loc, hexes)
                path_type = "highway"
                
                paths.append({
                    "points": path_points,
                    "type": path_type,
                    "start": start_loc['id'],
                    "end": end_loc['id']
                })
                
                connected_regions.add(i)
                connected_regions.add(j)
        
        return paths

    def _connect_water_locations(self, locations, hexes, connected_pairs):
        """Ensure water locations are properly connected"""
        water_types = {"ocean", "coast", "lake", "river"}
        water_locations = [loc for loc in locations if 
                          self._get_terrain_for_location(loc, hexes) in water_types]
        
        paths = []
        
        # Connect water locations to their nearest land neighbor
        for water_loc in water_locations:
            # Find closest land location
            closest_land = None
            min_distance = float('inf')
            for loc in locations:
                if loc == water_loc:
                    continue
                    
                loc_terrain = self._get_terrain_for_location(loc, hexes)
                if loc_terrain not in water_types:
                    distance = math.sqrt((water_loc['x']-loc['x'])**2 + (water_loc['y']-loc['y'])**2)
                    if distance < min_distance and distance < 400:
                        min_distance = distance
                        closest_land = loc
            
            if closest_land:
                pair_id = frozenset([water_loc['id'], closest_land['id']])
                if pair_id not in connected_pairs:
                    path_points = f"{water_loc['x']},{water_loc['y']} {closest_land['x']},{closest_land['y']}"
                    paths.append({
                        "points": path_points,
                        "type": "ferry_route",
                        "start": water_loc['id'],
                        "end": closest_land['id']
                    })
                    connected_pairs.add(pair_id)
        
        return paths

    def get_map_data(self) -> dict:
        locations = []
        for loc in self.world_map.locations.values():
            loc_dict = loc.to_dict()
            locations.append(loc_dict)

        seed = getattr(self, 'seed', 42)
        connections = self.map_utils.get_connections(self.world_map)
        hexes = getattr(self.campaign_state, 'hex_grid', [])
        if hexes:
            world_width = max(h['x'] for h in hexes) + self.campaign_state.hex_size
            world_height = max(h['y'] for h in hexes) + self.campaign_state.hex_size
        else:
            world_width, world_height = 1000, 800
            print(f"DEBUG Don't want to see this: hexes length in get_map_data = {len(hexes)}")

        # Build the base map data as before
        map_data = {
            "width": world_width,
            "height": world_height,
            "connections": connections,
            "locations": locations,
            "currentLocation": self.world_map.current_location_id,
            "hexes": hexes,
            "paths": self.paths,
            "terrainColors": self.terrain_generator.get_terrain_colors(),
            "generation": {
                "seed": seed,
                "width": world_width,
                "height": world_height
            },
            "fog_of_war": self.fog_of_war,
            "starting_location": self.starting_location_id,
            "seed": seed
        }

        # Add new fields from campaign_state (they may be empty initially)
        map_data["regions"] = [r.to_dict() for r in self.campaign_state.surface_regions.values()]
        map_data["potentialLocations"] = [
            {
                "id": pid,
                "col": p["col"],
                "row": p["row"],
                "type": p["type"],
                "generated": False
            }
            for pid, p in self.campaign_state.potential_locations.items()
            if pid not in self.world_map.locations
        ]
        return map_data

    def get_current_location_data(self) -> dict:
        if not self.current_location:
            return {}
        return self.current_location.to_dict()

    def move_character(self, char_id, new_position):
        char = self.character_manager.get_character(char_id)
        if char:
            char.position = new_position
            # Update world map representation
            self.world_map.update_character_position(char_id, new_position)
        
    def get_available_classes(self):
        """Get list of available classes"""
        return dnd_data.get_class_list()
    
    # TODO: likely will need fixes to use og_system data    
    def get_starting_equipment_options(self, class_name):
        """Get starting equipment options for a class"""
        char_class = dnd_data.get_class_object(class_name)
        if char_class:
            return {
                "packages": getattr(char_class, 'starting_equipment', []),
                "choices": getattr(char_class, 'player_options', {})
            }
        return {}

    def get_player_by_id(self, player_id):
        """Load a player from database by ID, cache in self.players."""
        if player_id in self.players:
            return self.players[player_id]
        # Load from DB
        from world.db import Database
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, attributes FROM players WHERE id = %s", (player_id,))
                row = cur.fetchone()
                if row:
                    # Convert UUID to string if necessary
                    import uuid
                    pid = str(row[0]) if isinstance(row[0], uuid.UUID) else row[0]
                    from world.player import Player
                    player = Player(id=pid, name=row[1], attributes=row[2])
                    print(f"[DEBUG] get_player_by_id: loaded player {player.id} with character_ids = {player.character_ids}")
                    self.players[player.id] = player
                    return player
        finally:
            Database.return_connection(conn)
        return None

    def get_player_by_session(self, session_id):
        print(f"get_player_by_session called with session_id: {session_id}")
        player_id = self.session_players.get(session_id)
        print(f"  in-memory player_id: {player_id}")
        if player_id:
            player = self.players.get(player_id)
            print(f"  in-memory player: {player}")
            return player
        from world.db import Database
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT player_id FROM player_sessions WHERE session_id = %s", (session_id,))
                row = cur.fetchone()
                if row:
                    player_id = row[0]
                    print(f"  DB player_id: {player_id}")
                    player = self.get_player_by_id(player_id)
                    print(f"  DB player: {player}")
                    return player
        finally:
            Database.return_connection(conn)
        print("  no player found")
        return None

    # TODO: see if this is needed after inventory (og_system) is created
    # def get_player_inventory(self, player_id):
    #     """Get narrative-focused inventory description"""
    #     character = self.character_manager.characters.get(player_id)
    #     if not character:
    #         return {"error": "Character not found"}
        
    #     # Let AI generate contextual description
    #     prompt = f"Describe {character.name}'s inventory considering:"
    #     prompt += f"\n- Location: {self.current_location.name}"
    #     prompt += f"\n- Campaign theme: {self.campaign_theme}"
    #     prompt += f"\n- Recent events: {self.get_recent_events()}"
        
    #     inventory_description = self.dm_chat_ai.generate_text(prompt)
        
    #     # Return narrative-focused inventory
    #     return {
    #         "description": inventory_description,
    #         "significant_items": self.get_significant_items(player_id),
    #         "currency": character.currency,
    #         "weight": f"{character.current_carry_weight}/{character.max_carry_weight}",
    #         "campaign_rules": self.get_inventory_rules()
    #     }

    def add_item(self, player_id, item_description):
        """Add an item through narrative discovery"""
        # AI determines item properties
        prompt = f"Create item based on: {item_description}\n"
        prompt += f"Campaign restrictions: {self.get_inventory_rules()['restricted']}\n"
        prompt += "Format: JSON with name, description, type, significance"
        
        item_data = self.dm_chat_ai.generate_structured_data(prompt, {
            "name": "string",
            "description": "string",
            "type": "string",
            "significance": "string"
        })
        
        # Add to character
        character = self.character_manager.get_character(player_id)
        character.inventory.append(item_data)
        
        # Narrative event
        self.narrative_system.add_event(
            f"{character.name} acquired {item_data['name']}",
            details=item_data['description']
        )
        
        return item_data

    def get_inventory_rules(self):
        """Get campaign-specific inventory rules"""
        rules = {
            "currency": self.campaign_state.get("currency", "gold pieces"),
            "weight_units": self.campaign_state.get("weight", "stones"),
            "restricted": self.campaign_state.get("restricted_items", []),
            "special": self.campaign_state.get("special_items", [])
        }
        return rules

    def start_game_time(self):
        self.game_start_time = datetime.now()
        
    def get_game_time(self):
        if not self.campaign_state.game_started:
            return "Not started"
        
        elapsed = (datetime.now() - self.game_start_time).total_seconds()
        game_minutes = int(self.campaign_state.game_time + elapsed * self.campaign_state.time_factor)
        return f"{game_minutes // 60}h {game_minutes % 60}m"

    def complete_tavern_intro(self, party_id, player_id):
        if party_id not in self.party_manager.parties:
            return {"status": "error", "error": "Party not found"}
        if player_id not in self.party_manager.parties[party_id]["members"]:
            return {"status": "error", "error": "Player not in party"}
        
        if "tavern_completed" not in self.party_manager.parties[party_id]:
            self.party_manager.parties[party_id]["tavern_completed"] = set()
        
        self.party_manager.parties[party_id]["tavern_completed"].add(player_id)
        
        party_members = self.party_manager.parties[party_id]["members"]
        completed_members = self.party_manager.parties[party_id].get("tavern_completed", set())
        
        if set(party_members).issubset(completed_members):
            self.assign_starting_quest(party_id)   # This method would create a quest
            return {"status": "success", "quest_assigned": True}
        
        return {"status": "success", "quest_assigned": False}

    def get_world_state(self):
        # Get active parties with their quests
        party_states = []
        for party_id in self.party_manager.active_parties:
            party = self.party_manager.parties[party_id]
            party_quests = [self.campaign_state.quests[qid] for qid in party.get("quests", []) if qid in self.campaign_state.quests]
            
            party_states.append({
                "id": party_id,
                "name": party["name"],
                "members": party["members"],
                "location": party["location"],
                "in_tavern": party.get("in_tavern", False),
                "quests": party_quests
            })
        
        return {
            # Core world data
            "world_map": self.world_map.serialize(),
            "time": self.campaign_state.game_time,
            "time_factor": self.campaign_state.time_factor,
            
            # Player progression
            "parties": party_states,
            "fog_of_war": self.fog_of_war,
            "starting_location": self.starting_location_id,
            
            # Game state flags
            "game_started": self.campaign_state.game_started,
            "current_date": self.campaign_state.get_current_date(),
            "game_time": self.get_game_time(),
            
            "events": [],  # TODO: implement event scheduler
            "player_data": {}  # TODO: implement player data manager
        }

    def get_all_locations(self):
        """Get all locations as dictionaries"""
        return [
            loc.to_dict()
            for loc in self.world_map.locations.values()
        ]
        
    def add_character(self, character_data):
        """Add a new character"""
        char_id = f"char_{uuid.uuid4().hex[:6]}"
        self.character_manager.characters[char_id] = character_data
        return char_id

    def get_location_data(self):
        """Get location data for frontend"""
        return [loc.to_dict() for loc in self.world_map.locations.values()]

    def get_rumors(self, location_id: str) -> list:
        """Generate 3 rumors about nearby locations"""
        location = self.world_map.get_location(location_id)
        if not location:
            return []
        
        # Get nearby locations (excluding current)
        nearby = sorted(
            [loc for loc in self.world_map.locations.values() if loc.id != location_id],
            key=lambda l: ((l.x - location.x)**2 + (l.y - location.y)**2)
        )[:3]  # Get 3 closest
        
        directions = ["north", "northeast", "east", "southeast", 
                     "south", "southwest", "west", "northwest"]
        
        rumors = []
        for loc in nearby:
            dx, dy = loc.x - location.x, loc.y - location.y
            angle = math.atan2(dy, dx)
            dir_idx = int((angle + math.pi) / (math.pi/4)) % 8
            rumors.append(f"Travelers speak of {loc.name} to the {directions[dir_idx]}")
        
        return rumors

    # This is a stub we created for complete_tavern_quest
    def assign_starting_quest(self, party_id):
        # TODO: implement proper quest generation
        quest = Quest(
            id=f"quest_tavern_{party_id}",
            archetype="recover",
            patron="tavern_keeper",
            target=self.starting_location_id,
            opposition=[],
            stages=[{
                "order": 1,
                "type": "travel",
                "location": self.starting_location_id,
                "completion_condition": "arrive",
                "rewards": [{"xp": 10}]
            }],
            consequences={},
            time_pressure={"exists": False},
            completed=False
        )
        self.campaign_state.quests[quest.id] = quest
        # Add quest to party
        if party_id in self.party_manager.parties:
            if "quests" not in self.party_manager.parties[party_id]:
                self.party_manager.parties[party_id]["quests"] = []
            self.party_manager.parties[party_id]["quests"].append(quest.id)
        return quest
    # TODO: need to fix or replace with og_system locations implementation
    def place_locations(self, hexes, terrain_grid):
        locations = []
        
        # Define location types by terrain
        location_rules = {
            "ocean": ["pirate_cove", "floating_market", "whale_graveyard"],
            "coast": ["fishing_village", "port", "lighthouse"],
            "lake": ["fishing_village", "lake_temple", "island_fortress"],
            "river": ["bridge", "river_town", "ferry"],
            "plains": ["farm", "village", "town"],
            "hills": ["mine", "watchtower", "fort"],
            "mountains": ["monastery", "dwarf_hold", "dragon_lair"],
            "snowcaps": ["shrine", "observatory", "gate_to_underworld"]
        }
        
        # Place major locations at terrain transitions
        for hex in hexes:
            terrain = hex["terrain"]

            # Skip open ocean (too far from land)
            if terrain == "ocean" and not self._is_near_land(hex, terrain_grid):
                continue

            # Determine if special position
            is_transition = False
            neighbor_terrains = set()
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = hex["x"] + dx * 60, hex["y"] + dy * 60
                if 0 <= nx < len(terrain_grid[0]) and 0 <= ny < len(terrain_grid):
                    neighbor_terrain = terrain_grid[ny][nx]
                    neighbor_terrains.add(neighbor_terrain)

            # Place water locations
            if terrain in ["ocean", "coast", "lake", "river"]:
                if self.rng.random() < 0.3:  # 30% chance for water location
                    location_type = self.rng.choice(location_rules.get(terrain, ["harbor"]))
                    locations.append({
                        "x": hex["x"],
                        "y": hex["y"],
                        "type": location_type,
                        "terrain": terrain,
                        "special": True
                    })
                continue

            # Place land locations
            if terrain in ["ocean", "coast", "lake", "river"]:
                continue
            
            # Determine if this is a special position
            is_transition = False
            neighbor_terrains = set()
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = hex["x"] + dx * 60, hex["y"] + dy * 60
                if 0 <= nx < len(terrain_grid[0]) and 0 <= ny < len(terrain_grid):
                    neighbor_terrains.add(terrain_grid[ny][nx])
            
            # Place special locations at transitions
            if len(neighbor_terrains) > 1:

                # Check for water transitions
                water_types = {"ocean", "coast", "lake", "river"}
                has_water = any(t in water_types for t in neighbor_terrains)

                if "mountains" in neighbor_terrains and "plains" in neighbor_terrains:
                    location_type = "mountain_pass"
                elif has_water and "mountains" in neighbor_terrains:
                    location_type = "coastal_cliff"
                elif has_water:
                    location_type = "coastal_town" if "coast" in neighbor_terrains else "waterside"
                elif "hills" in neighbor_terrains and "plains" in neighbor_terrains:
                    location_type = "river_ford"  # Even if no river, good crossing point
                else:
                    location_type = self.rng.choice(location_rules[terrain])
                
                locations.append({
                    "x": hex["x"],
                    "y": hex["y"],
                    "type": location_type,
                    "terrain": hex["terrain"],
                    "special": True
                })
            # Place regular locations
            elif random.random() < 0.1:  # 10% density
                location_type = self.rng.choice(location_rules[hex["terrain"]])
                locations.append({
                    "x": hex["x"],
                    "y": hex["y"],
                    "type": location_type,
                    "terrain": hex["terrain"],
                    "special": False
                })
        
        # Ensure at least some key locations
        if not any(loc["special"] for loc in locations):
            for hex in hexes:
                if hex["terrain"] == "mountains":
                    locations.append({
                        "x": hex["x"],
                        "y": hex["y"],
                        "type": "mountain_pass",
                        "terrain": hex["terrain"],
                        "special": True
                    })
                    break
        
        return locations

    def _is_near_land(self, hex, terrain_grid, radius=3):
        """Check if ocean hex is near land"""
        x, y = int(hex["x"]), int(hex["y"])
        for dy in range(-radius, radius+1):
            for dx in range(-radius, radius+1):
                nx, ny = x + dx, y + dy
                if (0 <= nx < len(terrain_grid[0]) and 
                   0 <= ny < len(terrain_grid)):
                    if terrain_grid[ny][nx] not in ["ocean"]:
                        return True
        return False

    def _create_region_network(self, locations, hexes):
        """Create efficient network within a region using minimum spanning tree"""
        paths = []
        if len(locations) < 2:
            return paths
        
        # Create all possible connections
        connections = []
        for i in range(len(locations)):
            for j in range(i+1, len(locations)):
                start = locations[i]
                end = locations[j]
                distance = math.sqrt((start['x']-end['x'])**2 + (start['y']-end['y'])**2)
                connections.append((distance, start, end))
        
        # Sort by distance
        connections.sort(key=lambda x: x[0])
        
        # Kruskal's algorithm for MST
        parent = {loc['id']: loc['id'] for loc in locations}
        
        def find(loc_id):
            if parent[loc_id] != loc_id:
                parent[loc_id] = find(parent[loc_id])
            return parent[loc_id]
        
        def union(loc1_id, loc2_id):
            root1 = find(loc1_id)
            root2 = find(loc2_id)
            if root1 != root2:
                parent[root2] = root1
                return True
            return False
        
        # Add connections until we have a spanning tree
        for dist, start, end in connections:
            if union(start['id'], end['id']):
                path_points = self._create_organic_path(start, end, hexes)
                path_type = self._get_path_type(
                    self._get_terrain_for_location(start, hexes),
                    self._get_terrain_for_location(end, hexes)
                )
                paths.append({
                    "points": path_points,
                    "type": path_type,
                    "start": start['id'],
                    "end": end['id']
                })
        
        return paths

    def enter_dungeon(self) -> bool:
        """Enter dungeon at current location"""
        if not self.current_location or not self.current_location.dungeon_type:
            return False
        
        # Initialize dungeon AI with current state
        self.dungeon_ai = DungeonAI(dungeon_state=self)
        
        # Generate dungeon based on location properties
        dungeon_type = self.current_location.dungeon_type
        dungeon_level = self.current_location.dungeon_level
        
        # Placeholder for actual dungeon generation
        print(f"Generating {dungeon_type} dungeon (Level {dungeon_level})")

        # # Transfer party
        # party = self.party_system.get_active_party()
        # dungeon.set_party(party)
        
        # # Set game state
        # self.game_state.set_mode('dungeon')
        # self.game_state.current_dungeon = dungeon
        # self.game_state.dungeon_location = location_id
        
        # # Narrative trigger
        # self.narrative.on_dungeon_enter(location)
        
        # Return to world map after dungeon completion
        return True

    def process_command(self, command: str) -> dict:
        """Process command through GameEngine for phase compliance"""
        # Try to use GameEngine if available
        if hasattr(self, 'game_engine') and self.game_engine:
            try:
                print(f"↻ Processing command via GameEngine: '{command[:50]}...'")
                
                # Pass through GameEngine for phase-compliant processing
                result = self.game_engine.advance(player_input=command)
                
                # Extract UI data from engine result
                ui_data = result.get("ui_data", {})
                
                # Check for phase violations
                violations = result.get("violations", 0)
                if violations > 0:
                    print(f"⚠  Phase violations detected: {violations}")
                    # Log violations for debugging
                    for violation in self.game_engine.get_phase_violations().get("recent_violations", []):
                        print(f"   - {violation}")
                
                # Maintain backward compatibility with existing callers
                return {
                    "response": ui_data.get("narration", "Command processed via GameEngine"),
                    "map_data": ui_data.get("map", self.get_map_data()),
                    "location_data": ui_data.get("location", self.get_current_location_data()),
                    "engine_result": result,  # Include full result for debugging
                    "phase_compliant": True,
                    "violations": violations
                }
                
            except Exception as e:
                print(f"✗ GameEngine processing failed: {e}")
                print("  Falling back to legacy AI processing")
                # Fall through to legacy processing
        
        # LEGACY PROCESSING (fallback if GameEngine fails or not available)
        print(f"↻ Processing command via legacy AI: '{command[:50]}...'")
        if self.dungeon_ai:
            result = self.dungeon_ai.process_command(command)
        else:
            result = self.world_ai.process_command(command)
        # Assume action takes 10 minutes
        self.campaign_state.advance_time(10) # advance time 10 minutes
        return result

    def get_game_engine_state(self) -> dict:
        """Get GameEngine status and phase information"""
        if not hasattr(self, 'game_engine') or not self.game_engine:
            return {"status": "not_initialized"}
        
        try:
            violations = self.game_engine.get_phase_violations()
            return {
                "status": "active",
                "current_phase": self.game_engine.current_phase.value,
                "phase_history": [phase.value for phase in self.game_engine.phase_history[-5:]],
                "violations": violations["total_violations"],
                "recent_violations": violations["recent_violations"]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_or_create_player(self, session_id, player_name=None):
        """Get existing player or create a new one for the session"""
        
        if session_id in self.session_players:
            player_id = self.session_players[session_id]
            return self.players[player_id]
        
        # Create new player
        player = Player(name=player_name or f"Player_{session_id[:8]}")
        self.players[player.id] = player
        self.session_players[session_id] = player.id
        
        # First, save the player to the database
        player_saved = self._save_player_to_db(player)
        
        if not player_saved:
            # Remove from memory if save failed
            del self.players[player.id]
            del self.session_players[session_id]
            raise Exception(f"Failed to save player {player.id} to database")
        
        
        # Then, save the session to the database
        session_saved = self._save_session_to_db(session_id, player.id)
        
        if not session_saved:
            print(f"DEBUG: Failed to save session {session_id} to database")
            # We might want to handle this differently, but for now just log it
            print(f"DEBUG: Session save failed, but player {player.id} was saved")
        
        return player

    def _save_player_to_db(self, player):
        """Save player to database with detailed error handling"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO players (id, name, attributes) VALUES (%s, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, attributes = EXCLUDED.attributes",
                    (player.id, player.name, json.dumps(player.attributes))
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"DEBUG: Error saving player to DB: {e}")
            conn.rollback()
            return False
        finally:
            Database.return_connection(conn)

    def _save_session_to_db(self, session_id, player_id):
        """Save session-player mapping to database with detailed error handling"""
        conn = Database.get_connection()
        try:
            # First, verify the player exists in the database
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM players WHERE id = %s", (player_id,))
                result = cur.fetchone()
                if not result:
                    print(f"DEBUG: Player {player_id} does not exist in database")
                    return False
                    
                # Now save the session
                cur.execute(
                    "INSERT INTO player_sessions (session_id, player_id) VALUES (%s, %s) "
                    "ON CONFLICT (session_id) DO UPDATE SET player_id = EXCLUDED.player_id, last_seen = NOW()",
                    (session_id, player_id)
                )
                conn.commit()
                print("DEBUG: Session saved successfully")
                return True
        except Exception as e:
            print(f"DEBUG: Error saving session to DB: {e}")
            conn.rollback()
            return False
        finally:
            Database.return_connection(conn)

    def _get_player_id_for_session(self, session_id):
        """Get player ID for a session from database"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT player_id FROM player_sessions WHERE session_id = %s",
                    (session_id,)
                )
                result = cur.fetchone()
                return result[0] if result else None
        finally:
            Database.return_connection(conn)

    def travel_to_location(self, location_id: str) -> bool:
        if self.world_map.travel_to(location_id):

            # Travel takes 1 day (1440 minutes)
            self.campaign_state.advance_time(24 * 60)

            location = self.world_map.get_location(location_id)
            self.current_location = location
            
            # Reveal location when traveled to
            self.reveal_location(location_id)
            
            # First discovery triggers events
            if not hasattr(location, 'visited') or not location.visited:
                location.visited = True
                print(f"Discovered new location: {location.name}")
                # Add narrative event
                # Safely log if session_log exists
                if hasattr(self, 'session_log'):
                    self.session_log.append(f"First visit to {location.name}")
            self.set_current_scene(location_id)  # Update narrative scene
            return True
        return False

    def reveal_location(self, location_id: str):
        """Mark location as discovered"""
        if location_id in self.world_map.locations:
            self.world_map.locations[location_id].discovered = True
            location = self.world_map.locations[location_id]
            location.discovered = True
            
            # First discovery triggers events
            if not hasattr(location, 'discovered_count'):
                location.discovered_count = 0
            location.discovered_count += 1

            # Call narrative system for pacing
            if hasattr(self, 'narrative_system'):
                self.narrative_system.on_location_discovered(location_id)
            
            # Safely add to session log if it exists
            if hasattr(self, 'session_log'):
                self.session_log.append(f"Discovered {location.name}")

    def set_current_scene(self, location_id: str):
        """Set narrative scene when arriving at a location"""
        location = self.world_map.get_location(location_id)
        scene_desc = f"{location.name}: {location.description}"
        self.narrative_system.set_current_scene(scene_desc)
