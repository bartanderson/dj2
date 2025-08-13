# world_controller.py
import math
import random
from typing import Dict, List, Optional 
from world.world_map import WorldMap
from world.campaign import Location, Quest
from world.utils import convex_hull, cross
import json
import numpy as np
from collections import defaultdict
from scipy.ndimage import gaussian_filter
# from party_system import PartySystem
# from dungeon import DungeonSystem
# from narrative_engine import NarrativeEngine
# from pacing_controller import PacingManager
# from game_state import GameState


class WorldController:
    # some stuff to add after we get this working consistently
    # def __init__(self, game_state: GameState):
    #     self.game_state = game_state
    #     self.world_map = game_state.world_map
    #     self.party_system = game_state.party_system
    #     self.narrative = game_state.narrative
    #     self.pacing = PacingManager()
    def __init__(self, world_data, seed=42):
        self.world_map = WorldMap()
        self.quests: Dict[str, Quest] = {}  # Global quest storage

        # Load seed and create deterministic RNG
        self.seed = world_data.get("seed", 42)
        self.rng = random.Random(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

        self.load_world_data(world_data)
        self.current_location = None
        self.active_quests = []
        self.terrain_types = {
            "ocean": {"color": "#4d6fb8", "height": -1.0},
            "coast": {"color": "#a2c4c9", "height": -0.3},
            "lake": {"color": "#4d6fb8", "height": -0.6},  # Higher than ocean
            "river": {"color": "#4d6fb8", "height": -0.4},  # Between lake and coast
            "plains": {"color": "#689f38", "height": 0.1},
            "hills": {"color": "#8d9946", "height": 0.4},
            "mountains": {"color": "#8d99ae", "height": 0.8},
            "snowcaps": {"color": "#ffffff", "height": 1.0}
        }

        # Precompute deterministic terrain data
        self.terrain_grid = self.generate_terrain()
        self.hexes = self.generate_hex_map(self.terrain_grid)
        self.paths = self.generate_paths(
            [loc.to_dict() for loc in self.world_map.locations.values()], 
            self.hexes
        )


    def load_world_data(self, world_data):
        # Load locations
        for loc_data in world_data["locations"]:
            location = Location(
                id=loc_data["id"],
                name=loc_data["name"],
                type=loc_data["type"],
                description=loc_data["description"],
                x=loc_data.get("x", 0),
                y=loc_data.get("y", 0),
                dungeon_type=loc_data.get("dungeon_type"),
                dungeon_level=loc_data.get("dungeon_level", 1),
                image_url=loc_data.get("image_url")
            )
            location.features = loc_data.get("features", [])
            location.services = loc_data.get("services", [])
            self.world_map.add_location(location)
            print(f"Loading location: {loc_data['name']} from JSON: x={loc_data.get('x')}, y={loc_data.get('y')}")

        
        # Create connections between locations
        location_ids = [loc.id for loc in self.world_map.locations.values()]
        for i in range(len(location_ids) - 1):
            self.world_map.connect_locations(location_ids[i], location_ids[i+1])
        
        # Load quests
        for quest_data in world_data["quests"]:
            quest = Quest(
                id=quest_data["id"],
                title=quest_data["title"],
                description=quest_data["description"],
                objectives=quest_data["objectives"],
                location_id=quest_data["location_id"],
                dungeon_required=quest_data["dungeon_required"]
            )
            # Store quest in global dictionary
            self.quests[quest.id] = quest
            
            # Add quest reference to location
            location = self.world_map.get_location(quest.location_id)
            if location:
                # Initialize quests list if needed
                if not hasattr(location, 'quests'):
                    location.quests = []
                location.quests.append(quest.id)  # Store quest ID only
            else:
                print(f"Warning: Location {quest.location_id} not found for quest {quest.id}")

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

    def get_location_data(self):
        """Get location data for frontend"""
        return [loc.to_dict() for loc in self.world_map.locations.values()]

    def travel_to_location(self, location_id: str) -> bool:
        if self.world_map.travel_to(location_id):
            location = self.world_map.get_location(location_id)
            self.current_location = location
            
            # First discovery triggers events
            if not location.discovered:
                location.discovered = True
                #self.narrative.on_location_discovered(location)
                #self.pacing.on_discovery_event()
                print(f"Discovered new location: {location.name}")

                # Update game state
                self.current_location = location            
            return True
        return False

    
    def get_current_location_data(self) -> dict:
        if not self.current_location:
            return {}
        return self.current_location.to_dict()
        
    def get_map_data(self) -> dict:
        """Get complete map data for rendering"""
        locations = []
        for loc in self.world_map.locations.values():
            loc_dict = loc.to_dict()
            loc_dict["imageUrl"] = loc.image_url
            locations.append(loc_dict)
        
        # Generate terrain grid
        terrain_grid = self.generate_terrain(width=1000, height=800)
        self.debug_terrain_distribution(terrain_grid)
        
        # Generate hex map
        hexes = self.generate_hex_map(terrain_grid, hex_size=60)
        
        # Generate paths between locations
        paths = self.generate_paths([loc.to_dict() for loc in self.world_map.locations.values()], hexes)
        currentLocation = self.current_location.id if self.current_location else None
        print(f"len(hexes {len(hexes)}")
        print(f"paths {paths}")
        return {
            "width": 1000,
            "height": 800,
            "terrain": terrain_grid,
            "connections": self.get_connections(),
            "locations": locations,
            "currentLocation": currentLocation,
            "hexes": hexes,
            "paths": paths,
            "terrainColors": {
                "ocean": "#4d6fb8",
                "coast": "#a2c4c9",
                "lake": "#4d6fb8",
                "river": "#4d6fb8",
                "plains": "#689f38",
                "hills": "#8d9946",
                "mountains": "#8d99ae",
                "snowcaps": "#ffffff"
            }
        }

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

    def get_terrain_data(self):
        terrain_map = defaultdict(list)
        for location in self.locations.values():
            if hasattr(location, 'terrain'):
                terrain_map[location.terrain].append((location.x, location.y))
        return terrain_map
    
    def generate_terrain(self, width=1000, height=800):
        heightmap = self._generate_heightmap(width, height)
        terrain_grid = []
        
        for y in range(height):
            row = []
            for x in range(width):
                height_val = heightmap[y][x]
                
                # Adjusted thresholds for better distribution
                if height_val < 0.2:  # Increased ocean range
                    terrain = "ocean"
                elif height_val < 0.25:
                    terrain = "coast"
                elif height_val < 0.35:  # Added lake range
                    terrain = "lake"
                elif height_val < 0.45:  # Added river range
                    terrain = "river"
                elif height_val < 0.6:
                    terrain = "plains"
                elif height_val < 0.75:  # Reduced hill range
                    terrain = "hills"
                elif height_val < 0.9:
                    terrain = "mountains"
                else:
                    terrain = "snowcaps"  # Only highest peaks
                    
                row.append(terrain)
            terrain_grid.append(row)
        
        return terrain_grid

    # world_controller.py
    def _generate_heightmap(self, width, height, octaves=4):
        # Replace all random calls with deterministic versions:
        # Instead of np.random.rand()
        # Create coherent noise with multiple frequencies
        terrain_rng = random.Random(self.seed)  # Dedicated RNG
        np_terrain_rng = np.random.default_rng(self.seed)  # NumPy RNG
        heightmap = np.zeros((height, width))
        scale = 0.01
        persistence = 0.5
        
        for octave in range(octaves):
            freq = 2 ** octave
            amplitude = persistence ** octave
            
            # Generate noise layer
            layer = np_terrain_rng.random(height, width) * amplitude
   
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
            lake_x = self.rng.randint(100, width-100)
            lake_y = self.rng.randint(100, height-100)
            lake_size = self.rng.randint(30, 80)
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
            start_x, start_y = self.rng.randint(0, width-1), self.rng.randint(0, height-1)
            for _ in range(200):  # River length
                heightmap[start_y][start_x] -= 0.2  # Dig deeper riverbed
                # Flow downhill
                start_x = (start_x + self.rng.choice([-1, 0, 1])) % width
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

    def generate_paths(self, locations, hexes):
        paths = []
        connected_pairs = set()  # Track already connected pairs
        # Sort locations for consistent processing order
        locations = sorted(locations, key=lambda loc: loc['id'])

        # Ensure water locations are connected
        water_types = {"ocean", "coast", "lake", "river"}
        water_locations = [loc for loc in locations if loc.get("terrain") in water_types]
        
        # Connect locations based on terrain accessibility
        for i, start in enumerate(locations):
            # Find closest locations that make sense to connect to
            possible_targets = []
            for j, end in enumerate(locations):
                if i == j:
                    continue
                
                # Don't connect extremely distant locations
                distance = math.sqrt((start["x"]-end["x"])**2 + (start["y"]-end["y"])**2)
                if distance > 300:
                    continue

                # Get terrain types from hex data
                start_terrain = self._get_terrain_for_location(start, hexes)
                end_terrain = self._get_terrain_for_location(end, hexes)
                
                # Only connect compatible terrains
                terrain_compatible = (
                    (start_terrain, end_terrain) in [
                        ("plains", "plains"),
                        ("plains", "hills"),
                        ("hills", "mountains"),
                        ("hills", "snowcaps"),  # Added
                        ("mountains", "snowcaps"),  # Added
                        ("coast", "plains"),
                        ("coast", "hills"),
                        ("mountain_pass", "mountains"),
                        ("mountain_pass", "plains"),
                        # Water connections
                        ("coast", "ocean"),
                        ("lake", "plains"),
                        ("lake", "hills"),
                        ("river", "plains"),
                        ("river", "hills"),
                        # Allow all same-terrain connections
                        (start_terrain, start_terrain)
                    ] or start_terrain == end_terrain  # Always allow same terrain
                )
                
                if terrain_compatible:
                    possible_targets.append((distance, end))
            
            # Connect to 1-3 nearest compatible locations
            # Deterministic connection count based on ID
            connect_count = 1 + (hash(start['id']) % 3)

            possible_targets.sort(key=lambda x: x[0])
            for _, target in possible_targets[:connect_count]:
                # Create unique pair identifier
                pair_id = tuple(sorted([start["id"], target["id"]]))

                if pair_id not in connected_pairs:
                    connected_pairs.add(pair_id)
                    path_points = self._create_organic_path(start, target, hexes)
                    paths.append({
                        "points": path_points,
                        "type": self._get_path_type(start_terrain, end_terrain),
                        "start": start["id"],
                        "end": target["id"]
                    })

                path_points = self._create_organic_path(start, target, hexes)
                paths.append({
                    "points": path_points,
                    "type": self._get_path_type(start_terrain, end_terrain),
                    "start": start["id"],
                    "end": target["id"]
                })

            for loc in water_locations:
                # Find closest land location
                land_locations = [l for l in locations if l.get("terrain") not in water_types]
                if not land_locations:
                    continue
                    
                # Find closest land location deterministically
                closest = min(
                    land_locations,
                    key=lambda l: math.sqrt((loc['x']-l['x'])**2 + (loc['y']-l['y'])**2)
                )
                
                # Create connection if not exists
                pair_id = tuple(sorted([loc["id"], closest["id"]]))
                if pair_id not in connected_pairs:
                    connected_pairs.add(pair_id)
                    path_points = self._create_organic_path(loc, closest, hexes)
                    paths.append({
                        "points": path_points,
                        "type": "ferry_route",
                        "start": loc["id"],
                        "end": closest["id"]
                    })
        
        return paths

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

    def terrain_color(self, terrain_type):
        """Get color for terrain type"""
        colors = {
            "forest": "#2d6a4f",
            "mountains": "#8d99ae",
            "water": "#4d6fb8",
            "plains": "#689f38"
        }
        return colors.get(terrain_type, "#888888")

    def enter_dungeon(self) -> bool:
        #location = self.world_map.get_location(location_id)
        if not self.current_location or not self.current_location.dungeon_type:
            return False
        
        print(f"Entering dungeon at {self.current_location.name}")
        # Generate dungeon based on location properties
        dungeon_type = self.current_location.dungeon_type
        dungeon_level = self.current_location.dungeon_level
        # dungeon.generate(
        #     dungeon_type=location.dungeon_type,
        #     level=location.dungeon_level
        # )

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