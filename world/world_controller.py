# world_controller.py
import json
import math
import random
import uuid
import numpy as np
from scipy.ndimage import gaussian_filter
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict

from dnd_character import CLASSES
from world.db import Database
from world.utils import convex_hull, cross
from world.world_map import WorldMap
from world.campaign import Location, Quest, Faction, WorldState
from world.narrative_system import NarrativeSystem
from world.character_builder import CharacterBuilder
from world.character import Character
from world.persistence import WorldManager
from world.ai_integration import WorldAI, DungeonAI # <---- soon we have to work on dungeon too
from world.world_session import SessionManager

import warnings
warnings.filterwarnings("ignore", message=".*Triton.*")
warnings.filterwarnings("ignore", message=".*redirects.*")

# WorldGenerator creates the content (locations, NPCs, quests, factions)
# WorldController handles the world state, terrain, and navigation
# This maintains the original architecture where:
# WorldController is responsible for the game world state
# WorldGenerator is responsible for procedural content generation
# Terrain and path generation remain with the controller that manages the world state

# from party_system import PartySystem
# from dungeon import DungeonSystem
# from narrative_engine import NarrativeEngine
# from pacing_controller import PacingManager
# from game_state import GameState


class WorldController:
    def __init__(self, world_id: str, ai_system: Any, seed: int = 42):
        TERRAIN_TYPES = {
            "ocean": {"weight": 0.25, "height": -0.5},
            "coast": {"weight": 0.05, "height": -0.2},
            "lake": {"weight": 0.05, "height": -0.3},
            "river": {"weight": 0.05, "height": -0.1},
            "plains": {"weight": 0.25, "height": 0.2},
            "hills": {"weight": 0.15, "height": 0.4},
            "mountains": {"weight": 0.15, "height": 0.7},
            "snowcaps": {"weight": 0.05, "height": 0.9}
        }
        # Initialize core components
        self.seed = seed
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)
        self.world_map = WorldMap()
        self.narrative_system = NarrativeSystem(self, ai_system)
        self.character_builder = CharacterBuilder(ai_system)
        self.ai_system = ai_system
        self.seed = seed
        self.terrain_types = TERRAIN_TYPES
        self.fog_of_war = True
        
        # Initialize state tracking
        self.known_locations = set()
        self.quests: Dict[str, Quest] = {}
        self.active_quests: List[Quest] = []
        self.session_log: List[str] = []
        self.current_location: Optional[Location] = None
        self.time = 0
        self.time_factor = 1
        self.game_started = False
        
        # Initialize character and party systems
        self.characters: Dict[str, Character] = {}
        self.parties: Dict[str, Dict] = {}
        self.character_parties: Dict[str, str] = {}
        self.active_parties: Set[str] = set()
        self.next_quest_id = 1
        self.default_party_id = "main_party"
        
        # Initialize world manager and load world data
        self.world_manager = WorldManager(ai_system)
        self.world_data = self.world_manager.load_from_db(world_id)
        
        # Set up the world
        self.setup_world(self.world_data)
        
        # Set starting location
        starting_id = self.world_data.get("starting_location_id", "starting_tavern")
        self.starting_location_id = starting_id
        self.reveal_location(starting_id)
        self.travel_to_location(starting_id)
        
        # Initialize default party AFTER loading world data
        self.parties[self.default_party_id] = {
            "name": "Main Party",
            "members": [],
            "location": self.starting_location_id
        }

        # Initialize AI systems
        self.world_ai = WorldAI(world_state=self)
        self.dungeon_ai = None  # Will be initialized when entering dungeon
        self.session_manager = SessionManager()

    def setup_world(self, world_data):
        """Load world data into game systems"""
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
                x=loc.get("x", 0),
                y=loc.get("y", 0),
                dungeon_type=loc.get("dungeon_type"),
                dungeon_level=loc.get("dungeon_level", 1),
                image_url=loc.get("image_url"),
                features=loc.get("features", []),
                services=loc.get("services", [])
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
            # Handle both database and JSON formats
            if "data" in quest_data:  # Database format
                q = quest_data["data"]
            else:  # Direct JSON format
                q = quest_data
                
            quest = Quest(
                id=q["id"],
                title=q["title"],
                description=q["description"],
                objectives=q["objectives"],
                location_id=q["location_id"],
                dungeon_required=q.get("dungeon_required", False),
                completed=q.get("completed", False)
            )
            
            # Store quest in global dictionary
            self.quests[quest.id] = quest
            
            # Add quest reference to location
            location = self.world_map.get_location(quest.location_id)
            if location:
                if not hasattr(location, 'quests'):
                    location.quests = []
                location.quests.append(quest.id)
            else:
                print(f"Warning: Location {quest.location_id} not found for quest {quest.id}")
        
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
        self.terrain_grid = self.generate_terrain()
        self.hexes = self.generate_hex_map(self.terrain_grid)
        # location dicts not part of the object, just a temp var to simplify self.paths call
        location_dicts = [loc.to_dict() for loc in self.world_map.locations.values()]
        self.paths = self.generate_paths(location_dicts, self.hexes)

    def load_world_data(self, world_id):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Load world metadata
                cur.execute("SELECT theme, seed FROM worlds WHERE id = %s", (world_id,))
                world_row = cur.fetchone()
                if world_row:
                    self.theme, self.seed = world_row
                
                # Load locations
                cur.execute("""
                    SELECT id, name, type, position[0] AS x, position[1] AS y, 
                           data->>'description' AS description,
                           data->>'dungeon_type' AS dungeon_type,
                           (data->>'dungeon_level')::int AS dungeon_level,
                           data->>'image_url' AS image_url,
                           data->'features' AS features,
                           data->'services' AS services,
                           discovered
                    FROM locations 
                    WHERE world_id = %s
                """, (world_id,))
                
                for row in cur.fetchall():
                    location = Location(
                        id=row[0],
                        name=row[1],
                        type=row[2],
                        x=row[3],
                        y=row[4],
                        description=row[5],
                        dungeon_type=row[6],
                        dungeon_level=row[7],
                        image_url=row[8],
                        features=row[9],
                        services=row[10],
                        discovered=row[11]
                    )
                    self.world_map.add_location(location)
                
                # Load quests
                cur.execute("SELECT * FROM quests WHERE world_id = %s", (world_id,))
                for row in cur.fetchall():
                    quest = Quest(
                        id=row[0],
                        title=row[2],
                        description=row[3],
                        objectives=row[4],
                        location_id=row[5],
                        completed=row[6],
                        dungeon_required=row[7]
                    )
                    self.quests[quest.id] = quest
                    
                    # Add to location
                    if quest.location_id in self.world_map.locations:
                        location = self.world_map.locations[quest.location_id]
                        if not hasattr(location, 'quests'):
                            location.quests = []
                        location.quests.append(quest.id)
        finally:
            Database.return_connection(conn)

    def reveal_location(self, location_id: str):
        """Mark location as discovered"""
        if location_id in self.world_map.locations:
            self.known_locations.add(location_id)
            location = self.world_map.locations[location_id]
            location.discovered = True
            
            # First discovery triggers events
            if not hasattr(location, 'discovered_count'):
                location.discovered_count = 0
            location.discovered_count += 1
            
            # Safely add to session log if it exists
            if hasattr(self, 'session_log'):
                self.session_log.append(f"Discovered {location.name}")

    def travel_to_location(self, location_id: str) -> bool:
        if self.world_map.travel_to(location_id):
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

    def set_current_scene(self, location_id: str):
        """Set narrative scene when arriving at a location"""
        location = self.world_map.get_location(location_id)
        scene_desc = f"{location.name}: {location.description}"
        self.narrative_system.set_current_scene(scene_desc)

    def generate_terrain(self, width=1000, height=800):
        heightmap = self._generate_heightmap(width, height)
        terrain_grid = []
        
        tolerance = 1e-5

        for y in range(height):
            row = []
            for x in range(width):
                height_val = heightmap[y][x]
                
                # Adjusted thresholds for better distribution
                if height_val < 0.2 + tolerance:  # Increased ocean range
                    terrain = "ocean"
                elif height_val < 0.25 + tolerance:
                    terrain = "coast"
                elif height_val < 0.35 + tolerance:  # Added lake range
                    terrain = "lake"
                elif height_val < 0.45 + tolerance:  # Added river range
                    terrain = "river"
                elif height_val < 0.6 + tolerance:
                    terrain = "plains"
                elif height_val < 0.75 + tolerance:  # Reduced hill range
                    terrain = "hills"
                elif height_val < 0.9 + tolerance:
                    terrain = "mountains"
                else:
                    terrain = "snowcaps"  # Only highest peaks
                    
                row.append(terrain)
            terrain_grid.append(row)
        
        return terrain_grid

    def _generate_heightmap(self, width, height, octaves=4):
        # Replace all random calls with deterministic versions:
        # Instead of np.random.rand()
        # Create coherent noise with multiple frequencies

        heightmap = np.zeros((height, width))
        scale = 0.01
        persistence = 0.5
        
        for octave in range(octaves):
            freq = 2 ** octave
            amplitude = persistence ** octave
            
            # Generate noise layer
            layer = self.np_rng.random((height, width)) * amplitude # (()) make it a tuple
   
            # Stretch and scale
            y_coords = np.linspace(0, scale*freq, height)
            x_coords = np.linspace(0, scale*freq, width)
            y_indices = np.floor(y_coords).astype(int) % height
            x_indices = np.floor(x_coords).astype(int) % width
            
            layer = layer[y_indices][:, x_indices]
            
            # Apply Gaussian blur for smoothness
            layer = gaussian_filter(layer, sigma=1 + octave)
            
            heightmap += layer
        
        # Create continent shapes - BEFORE normalization
        center_x, center_y = width//2, height//2
        max_distance = math.sqrt((width/2)**2 + (height/2)**2)
        
        for y in range(height):
            for x in range(width):
                # Create radial gradient (continents surrounded by ocean)
                distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                distance_factor = distance / max_distance  # 0-1 range
                
                # Subtract more at edges to create oceans
                heightmap[y][x] -= distance_factor * 0.7  # Increased from 0.5
                
                # Add mountain ranges more conservatively
                if 0.3 < heightmap[y][x] < 0.7 and self.rng.random() < 0.03:  # Reduced frequency
                    heightmap[y][x] += 0.15  # Reduced from 0.3
        
        # Add water bodies
        for _ in range(3):  # Create 3 lakes
            lake_x = self.np_rng.integers(100, width-100)
            lake_y = self.np_rng.integers(100, height-100)
            lake_size = self.np_rng.integers(30, 80)
            for dy in range(-lake_size, lake_size):
                for dx in range(-lake_size, lake_size):
                    nx, ny = lake_x + dx, lake_y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        distance = math.sqrt(dx**2 + dy**2) / lake_size
                        if distance < 1:
                            # Create lake depression
                            heightmap[ny][nx] -= (1 - distance) * 0.4

        # Add rivers
        for _ in range(2):  # Create 2 rivers
            start_x, start_y = self.np_rng.integers(0, width-1), self.np_rng.integers(0, height-1)
            for _ in range(200):  # River length
                heightmap[start_y][start_x] -= 0.2  # Dig deeper riverbed
                # Flow downhill
                start_x = (start_x + self.np_rng.choice([-1, 0, 1])) % width
                start_y = (start_y + 1) % height  # Generally flow south
        
        # Normalize to 0-1 range AFTER all modifications
        min_val = heightmap.min()
        max_val = heightmap.max()
        if max_val - min_val > 0:
            heightmap = (heightmap - min_val) / (max_val - min_val)
        else:
            heightmap = np.zeros((height, width))
        
        return heightmap    

    def generate_hex_map(self, terrain_grid, hex_size=60):
        hexes = []
        width = len(terrain_grid[0])
        height = len(terrain_grid)
        
        # Distance between hex centers
        x_step = int(hex_size * 1.5)
        y_step = int(hex_size * math.sqrt(3))
        
        # Create hex grid that follows terrain
        for x in range(0, width, x_step):
            for y in range(0, height, y_step):
                # Offset every other column for hex pattern
                y_offset = (hex_size * math.sqrt(3)/2) if (x//x_step) % 2 else 0
                py = y + y_offset
                
                # Skip hexes outside boundaries
                if x >= width or py >= height:
                    continue
                
                # Get terrain at center point
                terrain = terrain_grid[min(height-1, int(py))][min(width-1, int(x))]
                
                # Calculate hex points
                points = []
                for i in range(6):
                    angle = math.pi/3 * i
                    px = x + hex_size * math.cos(angle)
                    py = y + hex_size * math.sin(angle) + y_offset
                    points.append(f"{px},{py}")
                
                # Add imperfections
                jitter = 0.2  # 20% position variation
                jittered_points = [
                    f"{float(p.split(',')[0]) + self.rng.uniform(-hex_size*jitter, hex_size*jitter)},"
                    f"{float(p.split(',')[1]) + self.rng.uniform(-hex_size*jitter, hex_size*jitter)}"
                    for p in points
                ]
                
                hexes.append({
                    "x": x,
                    "y": y + y_offset,
                    "terrain": terrain,
                    "points": " ".join(points), #(jittered_points)
                    "height": self.terrain_types[terrain]["height"]
                })
        
        return hexes

    def generate_paths(self, locations, hexes):
        """Generate logical, non-crossing paths with regional hierarchy"""
        paths = []
        connected_pairs = set()
        
        # Step 1: Group locations into regions
        regions = self._cluster_locations(locations, hexes)
        
        # Step 2: Create intra-region connections
        for region in regions:
            if len(region) > 1:
                region_paths = self._create_minimum_spanning_tree(region, hexes)
                for path in region_paths:
                    pair_id = frozenset([path['start'], path['end']])
                    paths.append(path)
                    connected_pairs.add(pair_id)
        
        # Step 3: Connect regions
        region_centroids = self._calculate_region_centroids(regions)
        region_connections = self._connect_regions(region_centroids, regions, hexes)
        paths.extend(region_connections)
        
        # Step 4: Ensure water locations are connected
        water_paths = self._connect_water_locations(locations, hexes, connected_pairs)
        paths.extend(water_paths)
        
        return paths

    def _cluster_locations(self, locations, hexes, max_distance=250):
        """Group locations into regions based on proximity"""
        regions = []
        unassigned = locations.copy()
        
        while unassigned:
            # Start new region with first unassigned location
            region = [unassigned.pop(0)]
            base_x, base_y = region[0]['x'], region[0]['y']
            
            # Find nearby locations
            i = 0
            while i < len(region):
                current = region[i]
                j = 0
                while j < len(unassigned):
                    other = unassigned[j]
                    distance = math.sqrt((current['x']-other['x'])**2 + 
                                         (current['y']-other['y'])**2)
                    if distance < max_distance:
                        region.append(unassigned.pop(j))
                    else:
                        j += 1
                i += 1
            
            regions.append(region)
        
        return regions

    def _create_minimum_spanning_tree(self, locations, hexes):
        """Create efficient network using Kruskal's algorithm"""
        paths = []
        connections = []
        
        # Create all possible connections
        for i in range(len(locations)):
            for j in range(i+1, len(locations)):
                start = locations[i]
                end = locations[j]
                distance = math.sqrt((start['x']-end['x'])**2 + (start['y']-end['y'])**2)
                connections.append((distance, start, end))
        
        # Sort by distance
        connections.sort(key=lambda x: x[0])
        
        # Union-Find data structure
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
        
        # Build MST
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

    def _create_organic_path(self, start, end, hexes):
        """Create a winding path that follows terrain contours"""
        points = [f"{start['x']},{start['y']}"]
        
        # Calculate direct vector
        dx = end["x"] - start["x"]
        dy = end["y"] - start["y"]
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Number of segments based on distance
        segments = max(3, int(distance / 50))
        
        # Create winding path with terrain avoidance
        for i in range(1, segments):
            t = i / segments
            # Base position (linear interpolation)
            x = start["x"] + dx * t
            y = start["y"] + dy * t
            
            # Apply terrain-based offset
            terrain_height = self._get_terrain_height_at(x, y, hexes)
            if terrain_height > 0.6:  # Avoid high mountains
                # Create switchbacks
                offset_dir = 1 if i % 2 == 0 else -1
                x += math.sin(t * math.pi * 4) * 20 * offset_dir
                y += math.cos(t * math.pi * 4) * 15 * offset_dir
            elif terrain_height < 0:  # Avoid ocean
                # Coast-hugging path
                x += math.sin(t * math.pi * 8) * 15
                y += math.cos(t * math.pi * 8) * 10
            
            # Add some random winding for organic feel
            x += self.rng.gauss(0, 5)
            y += self.rng.gauss(0, 5)
            
            points.append(f"{x},{y}")
        
        points.append(f"{end['x']},{end['y']}")
        return " ".join(points)

    def _get_terrain_height_at(self, x, y, hexes, radius=100):
        """Get interpolated terrain height at coordinates"""
        if not hexes:
            return 0.0
        
        total_weight = 0.0
        weighted_height = 0.0
        
        for hex in hexes:
            distance = math.sqrt((x - hex['x'])**2 + (y - hex['y'])**2)
            if distance < radius:
                # Inverse distance weighting
                weight = 1.0 / (distance + 1)  # +1 to avoid division by zero
                total_weight += weight
                weighted_height += hex.get('height', 0.0) * weight
        
        if total_weight > 0:
            return weighted_height / total_weight
        return 0.0

    def _get_path_type(self, start_terrain, end_terrain):
        """Determine path type based on endpoints"""
        # Create a set of both terrains
        terrains = {start_terrain, end_terrain}
        
        # Check for water types
        water_types = {"ocean", "coast", "lake", "river"}
        if terrains & water_types:  # If there's any intersection
            if "ocean" in terrains:
                return "sea_route"
            if "lake" in terrains:
                return "lake_route"
            if "river" in terrains:
                return "river_path"
            return "coastal_route"
        
        # Check for mountain types
        mountain_types = {"mountains", "snowcaps"}
        if terrains & mountain_types:
            return "mountain_pass"
        
        if "hills" in terrains:
            return "hiking_trail"
        
        return "road"

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

    def _calculate_region_centroids(self, regions):
        """Calculate center points of each region"""
        centroids = []
        for region in regions:
            x_sum = sum(loc['x'] for loc in region)
            y_sum = sum(loc['y'] for loc in region)
            centroids.append({
                'x': x_sum / len(region),
                'y': y_sum / len(region),
                'region': region
            })
        return centroids

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
        """Get complete map data for rendering"""
        locations = []
        for loc in self.world_map.locations.values():
            loc_dict = loc.to_dict()
            loc_dict["imageUrl"] = loc.image_url
            locations.append(loc_dict)
        
        # Return generation parameters instead of terrain data
        return {
            "width": 1000,
            "height": 800,
            "connections": self.get_connections(),
            "locations": locations,
            "currentLocation": self.world_map.current_location_id,
            "paths": self.paths,
            "terrainColors": {
                "ocean": "#4d6fb8",
                "coast": "#a2c4c9",
                "lake": "#4d6fb8",
                "river": "#4d6fb8",
                "plains": "#689f38",
                "hills": "#8d9946",
                "mountains": "#8d99ae",
                "snowcaps": "#ffffff"
            },
            "generation": {
                "seed": self.seed,
                "width": 1000,
                "height": 800
            },
            "fog_of_war": self.fog_of_war,
            "known_locations": list(self.known_locations),
            "starting_location": self.starting_location_id
        }

    def get_connections(self):
        """Generate logical connections based on location types"""
        locations = list(self.world_map.locations.values())
        
        # Group locations by type
        location_groups = defaultdict(list)
        for loc in locations:
            location_groups[loc.type].append(loc)
        
        connections = []
        
        # 1. Connect within groups using proximity
        for group_type, group_locs in location_groups.items():
            if len(group_locs) > 1:
                # Connect each location to its 2 nearest neighbors
                for loc in group_locs:
                    distances = []
                    for other in group_locs:
                        if loc != other:
                            dx = loc.x - other.x
                            dy = loc.y - other.y
                            dist = (dx*dx + dy*dy)**0.5
                            distances.append((dist, other))
                    
                    distances.sort(key=lambda x: x[0])
                    for _, neighbor in distances[:2]:
                        connections.append({
                            "x1": loc.x, "y1": loc.y,
                            "x2": neighbor.x, "y2": neighbor.y
                        })
        
        # 2. Connect groups using minimum spanning tree
        group_centers = []
        for group_type, group_locs in location_groups.items():
            if group_locs:
                center_x = sum(loc.x for loc in group_locs) / len(group_locs)
                center_y = sum(loc.y for loc in group_locs) / len(group_locs)
                group_centers.append({"x": center_x, "y": center_y, "type": group_type})
        
        if len(group_centers) > 1:
            # Create MST between group centers
            dist_matrix = []
            for i, center1 in enumerate(group_centers):
                for j, center2 in enumerate(group_centers):
                    if i < j:
                        dx = center1["x"] - center2["x"]
                        dy = center1["y"] - center2["y"]
                        dist = (dx*dx + dy*dy)**0.5
                        dist_matrix.append((dist, i, j))
            
            dist_matrix.sort(key=lambda x: x[0])
            
            # Simple MST implementation
            groups_connected = set()
            for dist, i, j in dist_matrix:
                if i not in groups_connected or j not in groups_connected:
                    connections.append({
                        "x1": group_centers[i]["x"], "y1": group_centers[i]["y"],
                        "x2": group_centers[j]["x"], "y2": group_centers[j]["y"],
                        "inter_region": True
                    })
                    groups_connected.add(i)
                    groups_connected.add(j)
        
        return connections

    def get_current_location_data(self) -> dict:
        if not self.current_location:
            return {}
        return self.current_location.to_dict()

    def get_active_parties(self):
        """Get all active parties"""
        return [party for party in self.parties.values() if party["members"]]

    def move_character(self, char_id, new_position):
        char = self.characters.get(char_id)
        if char:
            char.position = new_position
            # Update world map representation
            self.world_map.update_character_position(char_id, new_position)

    def create_character(self, player_id, char_data):
        """Create a new character"""
        character = self.character_builder.create_character(player_id, char_data)
        self.characters[character.id] = character
        return character

    def update_character_avatar(self, char_id, avatar_url):
        if char_id in self.characters:
            self.characters[char_id].avatar_url = avatar_url
        
    def get_available_classes(self):
        """Get list of available classes"""
        return list(CLASSES.keys())
        
    def get_starting_equipment_options(self, class_name):
        """Get starting equipment options for a class"""
        char_class = CLASSES.get(class_name.lower())
        if char_class:
            return {
                "packages": char_class.starting_equipment,
                "choices": char_class.player_options
            }
        return {}

    def get_player_inventory(self, player_id):
        """Get narrative-focused inventory description"""
        character = self.characters.get(player_id)
        if not character:
            return {"error": "Character not found"}
        
        # Let AI generate contextual description
        prompt = f"Describe {character.name}'s inventory considering:"
        prompt += f"\n- Location: {self.current_location.name}"
        prompt += f"\n- Campaign theme: {self.campaign_theme}"
        prompt += f"\n- Recent events: {self.get_recent_events()}"
        
        inventory_description = self.ai_system.generate_text(prompt)
        
        # Return narrative-focused inventory
        return {
            "description": inventory_description,
            "significant_items": self.get_significant_items(player_id),
            "currency": character.currency,
            "weight": f"{character.current_carry_weight}/{character.max_carry_weight}",
            "campaign_rules": self.get_inventory_rules()
        }

    def get_inventory_rules(self):
        """Get campaign-specific inventory rules"""
        rules = {
            "currency": self.campaign_data.get("currency", "gold pieces"),
            "weight_units": self.campaign_data.get("weight", "stones"),
            "restricted": self.campaign_data.get("restricted_items", []),
            "special": self.campaign_data.get("special_items", [])
        }
        return rules

    def add_item(self, player_id, item_description):
        """Add an item through narrative discovery"""
        # AI determines item properties
        prompt = f"Create item based on: {item_description}\n"
        prompt += f"Campaign restrictions: {self.get_inventory_rules()['restricted']}\n"
        prompt += "Format: JSON with name, description, type, significance"
        
        item_data = self.ai_system.generate_structured_data(prompt, {
            "name": "string",
            "description": "string",
            "type": "string",
            "significance": "string"
        })
        
        # Add to character
        character = self.characters[player_id]
        character.inventory.append(item_data)
        
        # Narrative event
        self.narrative_system.add_event(
            f"{character.name} acquired {item_data['name']}",
            details=item_data['description']
        )
        
        return item_data


    def start_game_time(self):
        self.game_start_time = datetime.now()
        
    def get_game_time(self):
        if not self.game_started:
            return "Not started"
        
        elapsed = (datetime.now() - self.game_start_time).total_seconds()
        game_minutes = int(self.time + elapsed * self.time_factor)
        return f"{game_minutes // 60}h {game_minutes % 60}m"

    def complete_tavern_intro(self, party_id, player_id):
        """Mark that a player has completed the initial tavern scene"""
        if party_id not in self.parties:
            return {"status": "error", "error": "Party not found"}
        
        if player_id not in self.parties[party_id]["members"]:
            return {"status": "error", "error": "Player not in party"}
        
        # Mark player as completed tavern intro
        if "tavern_completed" not in self.parties[party_id]:
            self.parties[party_id]["tavern_completed"] = set()
        
        self.parties[party_id]["tavern_completed"].add(player_id)
        
        # Assign quest if all party members have completed
        party_members = self.parties[party_id]["members"]
        completed_members = self.parties[party_id].get("tavern_completed", set())
        
        if set(party_members).issubset(completed_members):
            self.assign_starting_quest(party_id)
            return {"status": "success", "quest_assigned": True}
        
        return {"status": "success", "quest_assigned": False}

    def get_world_state(self):
        # Get active parties with their quests
        party_states = []
        for party_id in self.active_parties:
            party = self.parties[party_id]
            party_quests = [self.quests[qid] for qid in party.get("quests", []) 
                            if qid in self.quests]
            
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
            "time": self.time,
            "time_factor": self.time_factor,
            
            # Player progression
            "parties": party_states,
            "fog_of_war": self.fog_of_war,
            "known_locations": list(self.known_locations),
            "starting_location": self.starting_location_id,
            
            # NPC and event data
            "npcs": self.npc_controller.get_npc_states(),
            "events": self.event_scheduler.get_active_events(),
            
            # Game state flags
            "game_started": self.game_started,
            "game_time": self.get_game_time(),
            
            # Player-specific data (if applicable)
            "player_data": self.player_data_manager.get_state()
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
        self.characters[char_id] = character_data
        return char_id
        
    def create_party(self, party_name, member_ids):
        party_id = f"party_{self.next_party_id}"
        self.next_party_id += 1
        
        self.parties[party_id] = {
            "id": party_id,
            "name": party_name,
            "members": member_ids,
            "quests": [],  # Initialize with no quests
            "location": self.starting_location_id,
            "in_tavern": True  # Start in tavern
        }
        self.active_parties.add(party_id)
        return party_id
        
    def add_to_party(self, char_id, party_id):
        """Add character to a party"""
        if char_id not in self.characters:
            return False
        
        # Remove from current party
        current_party = self.character_parties.get(char_id)
        if current_party and current_party in self.parties:
            self.parties[current_party]["members"].remove(char_id)
        
        # Add to new party
        if party_id not in self.parties:
            self.create_party(f"Party for {self.characters[char_id]['name']}", [char_id])
        else:
            self.parties[party_id]["members"].append(char_id)
            self.character_parties[char_id] = party_id
        return True
    
    def remove_from_party(self, char_id):
        """Remove character from their current party"""
        party_id = self.character_parties.get(char_id)
        if party_id and party_id in self.parties:
            self.parties[party_id]["members"].remove(char_id)
            del self.character_parties[char_id]
        return True
    
    def disband_party(self, party_id):
        """Disband a party and return members to solo status"""
        if party_id not in self.parties or party_id == self.default_party_id:
            return False
        
        for char_id in self.parties[party_id]["members"][:]:
            self.remove_from_party(char_id)
        del self.parties[party_id]
        return True
    
    def get_character_party(self, char_id):
        """Get party data for a character"""
        party_id = self.character_parties.get(char_id)
        if party_id and party_id in self.parties:
            return self.parties[party_id]
        return None
    

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        return self.quests.get(quest_id)

    def get_quests_for_location(self, location_id: str) -> List[Quest]:
        """Get full quest objects for a location"""
        location = self.world_map.get_location(location_id)
        if not location:
            return []
        
        # Return actual quest objects for the location
        return [
            self.quests[qid] 
            for qid in location.quests 
            if qid in self.quests
        ]


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

    def debug_terrain_distribution(self, terrain_grid):
        from collections import defaultdict
        counts = defaultdict(int)
        total = 0
        
        for row in terrain_grid:
            for terrain in row:
                counts[terrain] += 1
                total += 1
        
        print("Terrain Distribution:")
        for terrain, count in counts.items():
            print(f"{terrain}: {count/total*100:.1f}%")
        
        return counts

    # removed see world.js for its rendering of terrain and the paths which we follow with place_locations
    # def get_terrain_data(self):
    #     terrain_map = defaultdict(list)
    #     for location in self.locations.values():
    #         if hasattr(location, 'terrain'):
    #             terrain_map[location.terrain].append((location.x, location.y))
    #     return terrain_map

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

    def terrain_color(self, terrain_type):
        """Get color for terrain type"""
        colors = {
            "forest": "#2d6a4f",
            "mountains": "#8d99ae",
            "water": "#4d6fb8",
            "plains": "#689f38"
        }
        return colors.get(terrain_type, "#888888")

    def complete_tavern_intro(self, party_id):
        """Mark that a party has completed the initial tavern scene"""
        if party_id in self.parties:
            self.parties[party_id]["in_tavern"] = False
            self.assign_starting_quest(party_id)

    def assign_starting_quest(self, party_id):
        """Assign the initial quest to a party"""
        if party_id not in self.parties:
            return
        
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
        
        # Add to global quests registry
        self.quests[quest_id] = starting_quest
        
        # Assign to party
        self.parties[party_id]["quests"].append(quest_id)
        
        # Reveal starting location
        self.reveal_location(self.starting_location_id)
        
        return quest_id

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
        """Route commands to appropriate AI system"""
        if self.dungeon_ai:
            return self.dungeon_ai.process_command(command)
        return self.world_ai.process_command(command)


    # def complete_dungeon(self, success: bool, rewards: dict):
    #     location_id = self.game_state.dungeon_location
    #     location = self.world_map.get_location(location_id)
        
    #     if success:
    #         # Apply rewards
    #         self.party_system.apply_rewards(rewards)
            
    #         # Complete related quests
    #         for quest in location.quests:
    #             if quest.dungeon_required and not quest.completed:
    #                 quest.completed = True
    #                 self.narrative.on_quest_complete(quest)
        
    #     # Return to world
    #     self.game_state.set_mode('world')
    #     self.game_state.current_dungeon = None
    #     self.pacing.on_dungeon_complete(success)
        
    #     return self.world_map.current_location