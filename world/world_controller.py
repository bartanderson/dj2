# world_controller.py

"""
================================================================================
WorldController – Active Record pattern for world state and system coordination
================================================================================

This controller serves as both:
1. A coordinator between game systems (WorldMap, CampaignState, PartyManager, etc.)
2. A data model for the active game state (campaign, party position, etc.)

Current issues (to be addressed in refactoring):
- Many commands (movement, buy/sell, teleport) bypass the GameEngine phases,
  leading to inconsistent encounter generation and consequences.
- The controller has grown too large and mixes responsibilities.

================================================================================
Architectural Refactoring Plan (HIGHEST PRIORITY)
================================================================================

Goal: Route all player commands through GameEngine.advance() so that every action
goes through the full phase cycle (INPUT → INTERPRETATION → AUTHORITY → MUTATION
→ CONSEQUENCE → VIEW). This will unify encounter generation, state changes, and
narrative consequences.

Implementation steps (to be done in order):

1. [x] Modify WorldController.process_command to send ALL commands (movement, buy,
   sell, teleport, fast travel, rest, etc.) to self.game_engine.advance().
   - Removed direct command handling (direction_map, buy/sell blocks, etc.).
   - Kept only admin/debug commands (e.g., "reveal locations") as bypass.

2. [ ] Extend GameEngine._execute_interpretation_phase to parse:
   - [x] Movement directions (n, s, e, w, ne, nw, se, sw, go <dir>)
   - [ ] Buy/sell commands (e.g., "buy shortsword", "sell dagger")
   - [ ] Teleport commands ("teleport <col> <row>")
   - [ ] Fast travel ("travel to <location name>")
   - [ ] Rest, inventory, party commands.

3. [ ] Extend _execute_authority_phase to validate each command type:
   - [x] Movement: check passability (water, mountains) and party assets.
   - [ ] Buy/sell: verify shop presence, item existence, gold/stock.
   - [ ] Teleport: validate coordinates.
   - [ ] Fast travel: location discovered and reachable.

4. [ ] Extend _execute_mutation_phase to apply state changes:
   - [x] Update party position, reveal hexes, advance time.
   - [ ] Modify character inventory and gold.
   - [ ] Apply healing, condition changes.

5. [x] Extend _execute_consequence_phase to:
   - [x] Generate narration for the action.
   - [x] Check for random encounters after any action (not just movement).
   - [x] Generate encounter using encounter_generator and store in ui_data["encounter"].
   - [ ] Optionally trigger AI narration via the existing dm-response flow (already handled by frontend).

6. [ ] Update frontend (world.js) to handle the unified response format (encounter
   and action fields at top level) – already partially done; needs full integration.

================================================================================
PHASE 4c TODOs (in priority order, after refactoring)
================================================================================

1. **Generate encounter points on world map** – Random encounters are now generated
   on the fly using region danger and party level. Future: use pre‑placed EncounterPoint
   instances with persistent state (cleared, evolved, etc.).

2. **Implement region system from 14_campaign.json** – Load factions, quests,
   and use them to flavor encounters (e.g., faction patrols, quest-related
   monsters). Partially done (regions exist, encounter uses danger level).

3. **Add services to settlements** – Shops (already partially done), temples,
   quest boards, etc., based on settlement size and type.

4. **Determine dungeon type from terrain** – When entering a dungeon, derive
   type (cave, crypt, etc.) from the region's terrain.

5. **Remove test dungeon hack** – The temporary dungeon at starting location.

6. **Multi-player test button** – Open new tab with different session.

Already completed (marked with x):
  [x] Implement fast travel to discovered locations
  [x] Add shop system and inventory management (basic)
  [x] Cache world terrain image on server
  [x] Replace client-side terrain generation with backend data
  [x] AI-powered name generation (with caching)
  [x] Movement routed through GameEngine (steps 1 and 5 partially done)
  [x] Implement AdjudicationEngine for move, buy, sell.
  [ ] Add more actions (talk, rest, look) to AdjudicationEngine.
  [x] Remove old merchant_buy/sell tools (optional, keep for compatibility).

================================================================================
Before PHASE 5 TODO
================================================================================

- Refactor WorldController into smaller modules (e.g., WorldState, WorldMovement,
  WorldEncounter, WorldShop) to improve maintainability. This will be done after
  the GameEngine refactoring is stable.

- [ ] Implement ActionPlanner and ResolverLoop (completed).
- [ ] Add intent field to all tools.
- [ ] Extend ActionPlanner to support dynamic tool lookup via tool registry.
- [ ] Add Adjudication phase (skill checks, dice rolls) before planning.
- [ ] Implement reactions and interrupts.

================================================================================
"""

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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from collections import Counter
from world import dnd_data
from world.db import Database
from world.utils import convex_hull, cross
from world.perlin import PerlinNoise
from world.world_map import WorldMap, Location
from world.campaign import Region, Faction, Quest, CampaignState
from world.narrative_system import NarrativeSystem
from world.character_builder import CharacterBuilder
from world.character import Character
from world.persistence import WorldManager
from world.chat_ai import ChatAI
# TODO: since world and dungeon are separate, do we need to create a unified shared AI that manages either/both to address whether we actually import DungeonAI
from world.ai_integration import WorldAI, DungeonAI # <---- soon we have to work on dungeon too
from world.world_session import SessionManager
from world.ai_dungeon_master import AIDungeonMaster, Dialog # AIDungeonMaster also imported in narrative_system.py
from engine.game_engine import GameEngine, GamePhase
from .paths import PathGenerator
from .map_utils import MapUtils
from .party_manager import PartyManager
from .quest_manager import QuestManager
from .character_manager import CharacterManager
from world.dm_chat_handler import DMChatHandler
from world.player import Player           
from world.consequence_engine import ConsequenceEngine
from world.tool_system import ToolRegistry, tool
from world.authority_system import AuthoritySystem
from world.encounter_models import EncounterPoint
from world.bestiary import Monster
from world.name_generator import NameGenerator
from world.terrain_generator import TerrainGenerator
from world.terrain_image_generator import generate_terrain_image
from world.campaign import Merchant, MerchantItem, MerchantRelationship, MerchantPersonality, MerchantConstraints, VisibilityRule, PartyMerchantState
from world.merchant_utils import compute_price

print("Loading world_controller.py (new version with exit_dungeon fix)")

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
        self.world_id = world_id
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        self.path_generator = PathGenerator(seed)
        self.map_utils = MapUtils(seed)
        self.world_map = WorldMap()
        self.starting_location_id = None
        
        # Create chat_ai FIRST (needed by many systems)
        self.chat_ai = ChatAI()

        # Initialize authority system with proper tool registry
        self.tool_registry = ToolRegistry()
        self.tool_registry.register_from_class(self) # scan for @tool decorated methods
        self.authority_system = AuthoritySystem(self.tool_registry)

        # Create ConsequenceEngine immediately after chat_ai
        self.consequence_engine = ConsequenceEngine(
            world_controller=self,
            dm_chat_ai=self.chat_ai
        )

        # For backward compatibility, point dungeon_master to the new engine
        self.dungeon_master = self.consequence_engine

        # Now create other systems that depend on chat_ai or consequence_engine

        self.narrative_system = NarrativeSystem(self, ai_system, dm_chat_ai=self.chat_ai)
        self.character_builder = CharacterBuilder(ai_system)
        
        # Register character builder tools for AI use
        if hasattr(ai_system, 'tool_registry'):
            ai_system.tool_registry.register_from_class(self.character_builder)
        
        self.ai_system = ai_system
        self.fog_of_war = True

        # Initialize state tracking
        self.session_log: List[str] = []
        self.current_location: Optional[Location] = None
        
        self.default_party_id = None
        self.party_id = self.default_party_id

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

        # Name generator
        self.name_gen = NameGenerator(self.seed, self.campaign_data.get("theme", "generic"))

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
        self.narrative_system = NarrativeSystem(self, ai_system, dm_chat_ai=self.chat_ai)

        # Minimal world generation (placeholder)
        if not self.campaign_state.surface_regions:
            self.generate_world_structure()

        # Initialize world manager and load world data
        self.world_manager = WorldManager(ai_system)
        self.world_data = self.world_manager.load_from_db(world_id)
        
        # Set up the world
        self.setup_world(self.world_data)
        
        # Find the starting location (tavern)
        starting_location = None
        for location in self.world_map.locations.values():
            if location.type == "tavern" and "adventurer" in location.name.lower():
                starting_location = location
                break

        if starting_location:
            # Assign hex to the starting location using pixel coordinates
            hex = self._find_hex_at_pixel(starting_location.x, starting_location.y)
            if hex:
                starting_location.col = hex['grid_x']
                starting_location.row = hex['grid_y']
                self.campaign_state.party_position = (hex['grid_x'], hex['grid_y'])
                hex['discovered'] = True
                print(f"Starting hex discovered: {hex['grid_x']},{hex['grid_y']}")
            else:
                # Fallback: use hex (0,0)
                default_hex = self.campaign_state.get_hex(0,0)
                if default_hex:
                    starting_location.col = 0
                    starting_location.row = 0
                    self.campaign_state.party_position = (0,0)
                    default_hex['discovered'] = True
                    print("Using fallback hex (0,0) as starting hex")


            print("Found starting location")
            self.starting_location_id = starting_location.id
            self.reveal_location(starting_location.id)
            self.travel_to_location(starting_location.id)

            # For testing only - add dungeon to starting location
            # TODO: Remove temporary dungeon assignment once proper dungeon locations are generated
            if self.current_location:
                self.current_location.dungeon_type = 'cave'
                self.current_location.dungeon_level = 1
                print(f"[DEBUG] Added dungeon to {self.current_location.name}")

            merchant = self._create_sample_merchant(starting_location.name)
            self.campaign_state.merchants[merchant.id] = merchant
            # Store merchant reference on the location for quick access
            starting_location.merchant_id = merchant.id

        # else:
        #     # Fallback to first location if no tavern found
        #     first_location_id = list(self.world_map.locations.keys())[0]
        #     self.starting_location_id = first_location_id
        #     self.reveal_location(first_location_id)
        #     self.travel_to_location(first_location_id)

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

        # Dungeon integration now
        self.current_dungeon = None           # Will hold DungeonSystem instance
        self.current_dungeon_location_id = None   # Which world location we're in
        
        # Ensure dungeon_mode exists (it may already be set elsewhere)
        if not hasattr(self, 'dungeon_mode'):
            self.dungeon_mode = False

        # Dungeon tracking
        self.parties_in_dungeon = {}  # party_id -> {"location_id": str, "dungeon_id": str, "entered_at": datetime}

        print(f"[OK] ConsequenceEngine initialized: {hasattr(self.dungeon_master, 'chat_ai')}")

        print(f"[TEST] Loaded {len(self.campaign_state.factions)} factions: {list(self.campaign_state.factions.keys())}")
        print(f"[TEST] Loaded {len(self.campaign_state.quests)} quests from database")

    def wealth_to_gold(wealth_str: str) -> int:
        # TODO: Make this configurable (e.g., from economy settings or region)
        mapping = {"meager": 5, "cheap": 10, "medium": 50, "expensive": 150}
        try:
            return int(wealth_str)
        except (ValueError, TypeError):
            return mapping.get(wealth_str.lower(), 10)

    def _create_sample_merchant(self, location_name: str) -> Merchant:
        from world.campaign import Merchant, MerchantPersonality, MerchantConstraints, MerchantItem, VisibilityRule
        from world import dnd_data

        equipment = dnd_data._get_equipment_data().get("equipment", {})
        weapons = equipment.get("weapons", {})
        gear = equipment.get("gear", {})

        def wealth_to_gold(wealth_str: str) -> int:
            mapping = {"meager": 5, "cheap": 10, "medium": 50, "expensive": 150}
            try:
                return int(wealth_str)
            except (ValueError, TypeError):
                return mapping.get(wealth_str.lower(), 10)

        items = []

        # Healing Potion (hardcoded, not from equipment)
        items.append(MerchantItem(
            item_id="healing_potion",
            item_name="Healing Potion",
            base_price=10,
            steal_dc=12,
            quantity=3,
            tags={"consumable", "potion"}
        ))

        # Shortsword
        if "shortsword" in weapons:
            sw = weapons["shortsword"]
            cost_str = sw.get("cost", "cheap")
            items.append(MerchantItem(
                item_id="shortsword",
                item_name=sw["name"],
                base_price=wealth_to_gold(cost_str),
                steal_dc=15,
                quantity=1,
                tags={"weapon", "melee"}
            ))

        # Backpack
        if "backpack" in gear:
            bp = gear["backpack"]
            cost_str = bp.get("cost", "meager")
            items.append(MerchantItem(
                item_id="backpack",
                item_name=bp["name"],
                base_price=wealth_to_gold(cost_str),
                steal_dc=10,
                quantity=5,
                tags={"gear"}
            ))

        merchant = Merchant(
            merchant_id="grom_trader",
            name="Grom the Trader",
            location=location_name,
            personality=MerchantPersonality(greed=6, paranoia=4, honor=5, sociability=7, risk_tolerance=4),
            constraints=MerchantConstraints(max_discount=0.4, max_markup=1.8, barter_allowed=True),
            inventory=items,
            global_bias=1
        )
        return merchant

    def _is_item_visible(self, item: MerchantItem, rel: MerchantRelationship) -> bool:
        """Check visibility rules."""
        if not item.visibility_rules:
            return True  # default visible
        for rule in item.visibility_rules:
            if rule.type == "affinity" and rel.affinity >= rule.threshold:
                return True
            if rule.type == "trust" and rel.trust >= rule.threshold:
                return True
            if rule.type == "fear" and rel.fear >= rule.threshold:
                return True
            if rule.type == "respect" and rel.respect >= rule.threshold:
                return True
            if rule.type == "flag" and rule.threshold in rel.flags:
                return True
            if rule.type == "quest" and rule.threshold in self.campaign_state.active_quests:  # simplistic
                return True
        return False

    def _compute_price(self, item, merchant, rel, context):
        """Compute dynamic price based on merchant personality, relationship, and context."""
        price = item.base_price
        price *= (1 + merchant.personality.greed * 0.05)
        price *= (1 - rel.affinity * 0.03)
        price *= (1 - rel.trust * 0.02)
        price *= (1 + rel.fear * 0.04)
        if context.get('desperate'):
            price *= 1.25
        if context.get('scarcity'):
            price *= 1.1
        max_price = item.base_price * (1 + merchant.constraints.max_markup)
        min_price = item.base_price * (1 - merchant.constraints.max_discount)
        return int(max(min_price, min(price, max_price)))

    def get_region_for_hex(self, col, row):
        hex_data = self.campaign_state.get_hex(col, row)
        if not hex_data:
            return None
        region_id = hex_data.get('region_id')
        if region_id:
            return self.campaign_state.surface_regions.get(region_id)
        return None

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
        import random
        import json

        # Get grid size from campaign data, it defaults to 80x80
        world_gen = self.campaign_data.get("world_generation", {})
        surface = world_gen.get("world_layers", {}).get("surface", {})
        hex_grid_params = surface.get("hex_grid", {})
        size_str = hex_grid_params.get("size", "50x50")
        try:
            w, h = map(int, size_str.split('x'))
        except:
            w, h = 50, 50

        self.campaign_state.grid_width = w
        self.campaign_state.grid_height = h
        self.campaign_state.hex_size = 60

        seed = int(self.campaign_state.world_seed) if self.campaign_state.world_seed else 42
        rng = random.Random(seed)

        # Build empty hex grid (placeholder terrain)
        hexes = []
        for y in range(h):
            for x in range(w):
                x_pos = x * self.campaign_state.hex_size * 0.75
                y_pos = y * self.campaign_state.hex_size + (self.campaign_state.hex_size/2 if x % 2 else 0)
                hexes.append({
                    "x": x_pos,
                    "y": y_pos,
                    "grid_x": x,
                    "grid_y": y,
                    "terrain": 'plains',
                    "region_id": None,
                    "discovered": False
                })
        self.campaign_state.hex_grid = hexes

        # Set party position based on starting location (will be refined later)
        start_loc = self.world_map.get_location(self.starting_location_id)
        if start_loc:
            for h in hexes:
                if (h['x'] <= start_loc.x <= h['x'] + self.campaign_state.hex_size * 0.75 and
                    h['y'] <= start_loc.y <= h['y'] + self.campaign_state.hex_size):
                    self.campaign_state.party_position = (h['grid_x'], h['grid_y'])
                    h['discovered'] = True
                    break
        else:
            self.campaign_state.party_position = (0,0)
            hexes[0]['discovered'] = True

        # ------------------------------------------------------------
        # Generate terrain image using high‑resolution heightmap
        # ------------------------------------------------------------

        static_dir = Path("static/world_images")
        static_dir.mkdir(parents=True, exist_ok=True)

        # Parameters (tuned to match test_terrain.py)
        terrain_params = {
            'ocean_height': -1.0,
            'coast_height': -1.0,
            'lake_height': 0.05,
            'plains_high': 0.35,
            'hills_high': 0.8,
            'mountains_high': 0.9,
            'snowcaps_low': 0.97,
            'forest_min_moisture': 0.5,
            'forest_height_min': 0.5,
            'forest_height_max': 0.65,
            'river_target_per_10000_cells': 0.0002,
            'river_hill_threshold': 0.7,
            'river_mountain_threshold': 0.95
        }

        canvas_w = int(self.campaign_state.grid_width * self.campaign_state.hex_size * 0.75)
        canvas_h = int(self.campaign_state.grid_height * self.campaign_state.hex_size)
        hm_w = 1000
        hm_h = 800

        img, heightmap, moisture, river_mask = generate_terrain_image(
            seed=self.seed,
            output_path=str(static_dir / f"world_{self.world_id}_terrain.png"),
            width=hm_w,
            height=hm_h,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            params=terrain_params
        )
        self.campaign_state.terrain_image_url = f"/static/world_images/world_{self.world_id}_terrain.png"

        # Now assign terrain to each hex by sampling the high‑res heightmap

        # Map hex centers to heightmap indices
        for hex in self.campaign_state.hex_grid:
            # hex center (x, y) in world pixel coordinates
            cx = hex['x']
            cy = hex['y']
            # Map to heightmap grid (0..hm_w-1, 0..hm_h-1)
            gx = int((cx / canvas_w) * (hm_w - 1))
            gy = int((cy / canvas_h) * (hm_h - 1))
            gx = max(0, min(gx, hm_w - 1))
            gy = max(0, min(gy, hm_h - 1))
            h_val = heightmap[gy][gx]
            m_val = moisture[gy][gx]

            # Classify terrain (same logic as in render_terrain_image)
            if h_val < terrain_params['ocean_height']:
                terrain = 'ocean'
            elif h_val < terrain_params['coast_height']:
                terrain = 'coast'
            elif h_val < terrain_params['plains_high']:
                terrain = 'plains'
            elif h_val < terrain_params['hills_high']:
                terrain = 'hills'
            elif h_val < terrain_params['mountains_high']:
                terrain = 'mountains'
            else:
                terrain = 'snowcaps'
            if terrain_params['forest_height_min'] <= h_val <= terrain_params['forest_height_max'] and m_val > terrain_params['forest_min_moisture']:
                terrain = 'forest'
            if h_val < terrain_params['lake_height']:
                terrain = 'lake'
            hex['terrain'] = terrain

        # Debug prints

        terrain_counts = Counter(hex['terrain'] for hex in self.campaign_state.hex_grid)
        print(f"Hex grid dimensions: {self.campaign_state.grid_width} x {self.campaign_state.grid_height}")
        print(f"Terrain distribution: {dict(terrain_counts)}")
        print(f"Total hexes: {len(self.campaign_state.hex_grid)}")

        # ------------------------------------------------------------
        # Generate potential locations based on terrain density
        # ------------------------------------------------------------
        self.campaign_state.potential_locations = {}
        terrain_density = {
            'plains': 0.05,
            'forest': 0.07,
            'hills': 0.08,
            'mountains': 0.10,
            'snowcaps': 0.03,
            'lake': 0.0,      # no locations on lakes
            'ocean': 0.0,
            'coast': 0.0
        }

        for hex in self.campaign_state.hex_grid:
            terrain = hex["terrain"]
            density = terrain_density.get(terrain, 0.03)
            if self.rng.random() < density:
                pot_id = f"loc_{hex['grid_x']}_{hex['grid_y']}"
                loc_type = self.rng.choice(["settlement", "dungeon", "poi"])
                self.campaign_state.potential_locations[pot_id] = {
                    "region_id": None,
                    "col": hex["grid_x"],
                    "row": hex["grid_y"],
                    "type": loc_type,
                    "generated": False
                }

        # Surface regions remain empty for now (we are not using regions yet)
        self.campaign_state.surface_regions = {}

        print(f"[WORLD] Hex grid generated: {len(self.campaign_state.hex_grid)} hexes")
        print(f"[WORLD] Potential locations: {len(self.campaign_state.potential_locations)} potential locations")

        loc_type_counts = Counter(p['type'] for p in self.campaign_state.potential_locations.values())
        print(f"Potential locations by type: {dict(loc_type_counts)}")

        # TODO: Implement region generation from campaign data (14_campaign.json) and use for encounter points, faction control, etc.
        # TODO: Generate encounter points on the world map (using encounter_points system, not dependent on regions)
        # TODO: is there anything that could benefit from having heightmap, moisture_map, and river_mask after having used them to generate the image data?


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
        # TODO: Add services (shop, temple, quest board) based on settlement size and region
        # TODO: Determine dungeon type from terrain (cave, crypt, ruins, etc.)
        # TODO: Generate POI descriptions using AI
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
        
        self.paths = []

    def get_party_list_html(self, session_id=None):
        active_char = self._get_active_character(session_id)
        if not active_char:
            return "<p>No active character. Please create a character first.</p>"
        party = self.party_manager.get_character_party(active_char.id)
        if not party:
            return """
            <p>You are not in any party.</p>
            <button onclick="showCreatePartyModal()" class="btn">Create Party</button>
            <button onclick="showJoinPartyModal()" class="btn secondary">Join Party</button>
            """
        member_names = []
        for member_id in party.get("members", []):
            char = self.character_manager.get_character(member_id)
            member_names.append(char.name if char else member_id)
        html = f"""
        <div class="party-card">
            <h3>{party['name']}</h3>
            <p>ID: {party['id']}</p>
            <p>Members: {', '.join(member_names)}</p>
            <button onclick="leaveParty()" class="btn secondary">Leave Party</button>
        </div>
        """
        return html
        
    def get_active_party_id(self):
        """Return the current party ID (default or from session)."""
        # For now, use default. Later can be per player.
        return self.default_party_id

    def get_party_characters(self, party_id=None):
        """Return list of Character objects for the party."""
        if party_id is None:
            party_id = self.get_active_party_id()
        member_ids = self.party_manager.get_party_members(party_id)
        chars = []
        for cid in member_ids:
            char = self.character_manager.get_character(cid)
            if char:
                chars.append(char)
        return chars

    def get_party_average_level(self, party_id=None):
        chars = self.get_party_characters(party_id)
        if not chars:
            return 1
        total = sum(c.level for c in chars)
        return total // len(chars)  # integer average

    def get_party_size(self, party_id=None):
        return len(self.get_party_characters(party_id))

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

    def create_party(self, name: str, initial_members: List[str]) -> Optional[str]:
        print(f"DEBUG: WorldController.create_party called with name={name}, members={initial_members}")
        party_id = self.party_manager.create_party(name, initial_members)
        self.default_party_id = party_id
        print(f"DEBUG: party_manager.create_party returned {party_id}")
        return party_id

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

        map_data["discovered_hexes"] = [
            {"col": h['grid_x'], "row": h['grid_y']}
            for h in self.campaign_state.hex_grid
            if h.get('discovered', False)
        ]
        map_data["party_position"] = {
            "col": self.campaign_state.party_position[0],
            "row": self.campaign_state.party_position[1]
        }
        # Include party color for the marker
        party = None
        if hasattr(self, 'party_manager') and self.party_manager:
            try:
                party = self.party_manager.parties.get(self.party_id)
                map_data["party_color"] = party.get("color", "#FFD700") if party else "#FFD700"
            except Exception:
                map_data["party_color"] = "#FFD700"

        map_data["hexes"] = self.campaign_state.hex_grid
        map_data["terrain_image_url"] = self.campaign_state.terrain_image_url        
        return map_data

    def get_current_location_data(self) -> dict:
        if not self.current_location:
            return {}
        return self.current_location.to_dict()

    def emit_party_moved(self, col, row, session_id):
        from flask_socketio import emit
        char = self._get_active_character(session_id)
        if not char:
            return
        party = self.party_manager.get_character_party(char.id)
        if not party:
            return
        map_data = self.get_map_data()   # includes discovered hexes
        emit('party_moved', {
            'party_id': party['id'],
            'col': col,
            'row': row,
            'map_data': map_data
        }, namespace='/', broadcast=True)

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
        
    #     inventory_description = self.chat_ai.generate_text(prompt)
        
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
        
        item_data = self.chat_ai.generate_structured_data(prompt, {
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
        print("get_world_state called")
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

        # Build characters dictionary (outside the loop)
        print(f"DEBUG: get_world_state called, characters count: {len(self.character_manager.characters)}")
        characters_dict = {}
        for char_id, char in self.character_manager.characters.items():
            print(f"  character: {char_id} - {char.name}")
            characters_dict[char_id] = char.to_dict()
        print(f"DEBUG: get_world_state returning {len(characters_dict)} characters")

        return {
            # Core world data
            "world_map": self.world_map.serialize(),
            "time": self.campaign_state.game_time,
            "time_factor": self.campaign_state.time_factor,
            
            # Player progression
            "parties": party_states,
            "characters": characters_dict,
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

    def exit_dungeon(self, party_id: str = None, exiting_characters: list = None,
                     elapsed_minutes: int = 0, partial_exit: bool = False,
                     remaining_character_ids: list = None) -> dict:
        """
        Handle exit from dungeon. Can be called with just a party_id (simple exit)
        or with full character data (when dungeon server calls back).
        """
        print("exit_dungeon method called with parameters:", party_id, exiting_characters)
        # CASE 1: Called with exiting_characters (dungeon server callback)
        if exiting_characters is not None:
            # Update characters with dungeon changes
            for char_data in exiting_characters:
                char_id = char_data.get('id')
                char = self.character_manager.get_character(char_id)
                if char:
                    char.hp = char_data.get('hp', char.hp)
                    char.sp = char_data.get('sp', char.sp)
                    char.conditions = char_data.get('conditions', char.conditions)
                    char.inventory = char_data.get('inventory', char.inventory)
                    char.in_dungeon = False
                    char.dungeon_party_id = None
                    self.character_manager._save_character_to_db(char)

            # Advance world time
            self.campaign_state.advance_time(elapsed_minutes or 10)

            # Remove party from dungeon tracking if applicable
            if party_id and party_id in self.parties_in_dungeon:
                del self.parties_in_dungeon[party_id]

            # If partial exit, update the party members list? (Optional, later)
            return {"success": True, "message": f"Updated {len(exiting_characters)} characters."}

        # CASE 2: Simple exit by party_id (called from frontend "Return to World" button)
        if party_id and party_id in self.parties_in_dungeon:
            dungeon_info = self.parties_in_dungeon[party_id]
            location_id = dungeon_info['location_id']
            self.campaign_state.advance_time(10)  # placeholder
            if party_id in self.party_manager.parties:
                self.party_manager.set_party_location(party_id, location_id)
            del self.parties_in_dungeon[party_id]
            location = self.world_map.get_location(location_id)
            return {"success": True, "message": f"Party returns to {location.name if location else 'the entrance'}."}

        return {"success": False, "message": "No exit data provided."}

    def enter_dungeon(self, party_id: str, location_id: str, characters: List[dict]) -> dict:
        """
        Called when a party enters a dungeon.
        Returns dungeon_id and confirmation.
        """
        location = self.world_map.get_location(location_id)
        if not location or not location.dungeon_type:
            return {"success": False, "message": "Location has no dungeon"}
        
        # Generate a unique dungeon ID for this location (same for all parties entering same location)
        dungeon_id = f"dungeon_{location_id}"
        
        # Mark party as in dungeon
        self.parties_in_dungeon[party_id] = {
            "location_id": location_id,
            "dungeon_id": dungeon_id,
            "entered_at": datetime.now()
        }
        
        # Mark all characters as in dungeon
        for char_data in characters:
            char_id = char_data.get("id")
            if char_id in self.character_manager.characters:
                self.character_manager.characters[char_id].in_dungeon = True
                self.character_manager.characters[char_id].dungeon_party_id = party_id
        
        # Advance world time (dungeon will track actual elapsed time)
        self.campaign_state.advance_time(10)  # 10 minutes to descend
        
        return {
            "success": True,
            "dungeon_id": dungeon_id,
            "message": f"You descend into {location.name}."
        }

    def _update_party_position(self, new_col, new_row, reason="movement", advance_minutes=0):
        """Update party position, reveal hexes, advance time, and return response."""
        self.campaign_state.party_position = (new_col, new_row)
        self._reveal_hexes_around(new_col, new_row)

        # Encounter check
        if random.randint(1, 6) == 1:
            # Get region for the new hex
            hex_data = self.campaign_state.get_hex(new_col, new_row)
            region_id = hex_data.get('region_id') if hex_data else None
            region = self.campaign_state.surface_regions.get(region_id) if region_id else None
            danger_mod = region.danger_level if region else 0
            # Adjust chance by danger? For now, just use base chance.
            # Generate encounter context
            context = {
                "point_id": f"move_{new_col}_{new_row}",
                "party_level": self.get_party_average_level(),
                "party_size": self.get_party_size(),
                "region": {
                    "danger_level": danger_mod,
                    "terrain": hex_data.get('terrain') if hex_data else "plains",
                    "faction": region.faction_control if region else "contested"
                },
                "point_type": "travel"
            }
            from world.encounter_generator import generate_encounter
            encounter = generate_encounter(context)
            # Store encounter in a temporary attribute for later use in the response
            self.pending_encounter = encounter

        if advance_minutes:
            self.campaign_state.advance_time(advance_minutes)
        # Update current_location if the new hex contains a location
        loc = None
        for location in self.world_map.locations.values():
            if location.col == new_col and location.row == new_row:
                loc = location
                break
        if loc:
            self.current_location = loc
        else:
            self.current_location = None
        response = {
            "response": f"You {reason} to ({new_col},{new_row}).",
            "map_data": self.get_map_data(),
            "location_data": self.get_current_location_data(),
            "action": "centerOnParty",
            "success": True
        }
        if hasattr(self, 'pending_encounter') and self.pending_encounter:
            response["encounter"] = self.pending_encounter.to_dict()
            del self.pending_encounter
        return response

    def process_command(self, input_data, session_id=None):
        """Process a command (string or dict) and return response dict."""
        print(f"[DEBUG] process_command called with input_data={input_data}, session_id={session_id}")
        if isinstance(input_data, str):
            command = input_data
            target_terrain = None
        else:
            command = input_data.get('command', '')
            target_terrain = input_data.get('target_terrain')

        # =================================================================
        # ADMIN / DEBUG COMMANDS – bypass the GameEngine (temporary)
        # =================================================================
        if command.lower() == "reveal locations":
            count = 0
            for pot_id, pot in self.campaign_state.potential_locations.items():
                if not pot.get("generated"):
                    self._generate_location_from_potential(pot_id)
                    count += 1
            return {"response": f"Generated {count} locations.", "map_data": self.get_map_data()}

        # =================================================================
        # NORMAL COMMANDS – route through GameEngine
        # =================================================================
        if hasattr(self, 'game_engine') and self.game_engine:
            try:
                # Pass the command to the engine
                result = self.game_engine.advance(player_input=command)
                ui_data = result.get('ui_data', {})

                # Map engine output to expected frontend format
                response = {
                    "response": ui_data.get('narration', ''),
                    "map_data": ui_data.get('map', self.get_map_data()),
                    "location_data": ui_data.get('location', self.get_current_location_data()),
                    "encounter": ui_data.get('encounter'),      # may be None
                    "action": ui_data.get('action'),           # e.g., "centerOnParty"
                    "success": True
                }
                return response
            except Exception as e:
                print(f"✗ GameEngine processing failed: {e}")
                import traceback
                traceback.print_exc()
                return {"response": f"Engine error: {str(e)}", "success": False}
        else:
            # Fallback to legacy AI (should not happen after refactor)
            print(f"↻ GameEngine not available, using legacy AI for: '{command[:50]}...'")
            if self.dungeon_ai:
                result = self.dungeon_ai.process_command(command)
            else:
                result = self.world_ai.process_command(command)
            self.campaign_state.advance_time(10)
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

    def _get_active_character(self, session_id: str = None):
        if not session_id:
            return None
        player = self.get_player_by_session(session_id)
        if not player or not player.active_character_id:
            return None
        return self.character_manager.get_character(player.active_character_id)

    def get_or_create_player(self, session_id, player_name=None):
        """Get existing player or create a new one for the session"""
        
        if session_id in self.session_players:
            player_id = self.session_players[session_id]
            return self.players[player_id]
        
        # Create new player
        player = Player(name=player_name or f"Player_{session_id[:8]}")
        if player.active_character_id:
            party = self.party_manager.get_character_party(player.active_character_id)
            if party:
                self.default_party_id = party['id']
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


    def get_available_hex_moves(self, col, row):
        """Return list of (direction, target_hex) for passable adjacent hexes."""
        # Flat‑top hex directions (no east/west)
        dir_map = {
            'n': (0, -1),
            'ne': (1, -1),
            'se': (1, 0),
            's': (0, 1),
            'sw': (-1, 1),
            'nw': (-1, 0)
        }
        available = []
        for dir_name, (dc, dr) in dir_map.items():
            nc, nr = col + dc, row + dr
            target = self.campaign_state.get_hex(nc, nr)
            if target:
                # We'll consider all hexes as potentially traversable; obstacles handled later
                available.append((dir_name, target))
        return available

    def move_hex(self, direction, terrain=None):
        """Move party one hex in the given direction, optionally setting hex terrain."""
        col, row = self.campaign_state.party_position
        dir_map = {
            'n': (0, -1), 'ne': (1, -1), 'se': (1, 0),
            's': (0, 1), 'sw': (-1, 1), 'nw': (-1, 0)
        }
        if direction not in dir_map:
            return {"success": False, "message": f"Unknown direction: {direction}"}
        dc, dr = dir_map[direction]
        nc, nr = col + dc, row + dr
        target = self.campaign_state.get_hex(nc, nr)
        if not target:
            return {"success": False, "message": "You cannot go that way (edge of the world)."}

        # Set terrain if provided (from frontend)
        if terrain is not None:
            target['terrain'] = terrain

        # Passability check (optional, but safe)
        if not self._is_hex_passable(target):
            return {
                "success": False,
                "blocked": True,
                "reason": f"The {target['terrain']} blocks your path.",
                "terrain": target['terrain']
            }

        # Move
        self.campaign_state.party_position = (nc, nr)
        target['discovered'] = True
        self._reveal_hexes_around(nc, nr)
        self.explore_hex()
        return {
            "success": True,
            "new_hex": target,
            "new_col": nc,
            "new_row": nr
        }

    def _is_hex_passable(self, hex):
        """Basic passability based on terrain. Later we'll check party assets."""
        terrain = hex['terrain']
        # For now, water is impassable unless party has boat/swim (to be added)
        if terrain in ('ocean', 'lake', 'river'):
            # TODO: check party inventory for boat or other method of travel through/over/under water
            return False
        return True

    def _find_hex_at_pixel(self, x, y):
        """
        Return the hex dict containing pixel (x, y), or None.
        Uses approximate bounding box: hex width ~ hex_size * 0.75, height = hex_size.
        """
        for h in self.campaign_state.hex_grid:
            # Check if (x,y) lies within the hex's bounding box
            # Hex center is at (h['x'], h['y'])
            if (abs(h['x'] - x) < self.campaign_state.hex_size * 0.75 and
                abs(h['y'] - y) < self.campaign_state.hex_size):
                return h
        return None

    def _reveal_hexes_around(self, col, row, radius=1):
        """Mark hexes within radius as discovered."""
        for dc in range(-radius, radius+1):
            for dr in range(-radius, radius+1):
                h = self.campaign_state.get_hex(col+dc, row+dr)
                if h:
                    h['discovered'] = True

    def explore_hex(self):
        """Mark current hex as explored and generate its POIs."""
        hex = self.campaign_state.get_hex(*self.campaign_state.party_position)
        if not hex:
            return {"success": False, "message": "Not in a hex."}
        if hex.get('explored'):
            return {"success": True, "new_pois": []}
        hex['explored'] = True
        pois = self.campaign_state.get_or_generate_pois(hex)
        new_pois = [p for p in pois if not p['discovered']]
        for p in new_pois:
            p['discovered'] = True
        return {"success": True, "new_pois": new_pois}