# world_map.py
from world.campaign import Location
from world.utils import convex_hull
from typing import Dict, List, Optional

class WorldMap:
    TERRAIN_COLORS = {
        "forest": "#2d6a4f",
        "mountains": "#8d99ae",
        "water": "#4d6fb8",
        "plains": "#689f38"
    }

    def __init__(self):
        self.locations: Dict[str, Location] = {}
        self.connections: Dict[str, List[str]] = {}
        self.current_location_id: Optional[str] = None  # Change to ID
    
    def add_location(self, location: Location):
        self.locations[location.id] = location
        
    def connect_locations(self, loc1_id: str, loc2_id: str, bidirectional=True):
        if loc1_id not in self.connections:
            self.connections[loc1_id] = []
        self.connections[loc1_id].append(loc2_id)
        
        if bidirectional:
            if loc2_id not in self.connections:
                self.connections[loc2_id] = []
            self.connections[loc2_id].append(loc1_id)
    
    def get_location(self, location_id: str) -> Location:
        return self.locations.get(location_id)

    def get_current_location(self) -> Optional[Location]:
        if self.current_location_id:
            return self.locations[self.current_location_id]
        return None
    
    def get_adjacent_locations(self, location_id: str) -> List[Location]:
        return [self.locations[adj_id] for adj_id in self.connections.get(location_id, [])]
    
    def travel_to(self, location_id: str) -> bool:
        if location_id in self.locations:
            self.current_location_id = location_id
            return True
        return False
    
    def get_map_data(self) -> dict:
        return {
            "locations": {id: loc.to_dict() for id, loc in self.locations.items()},
            "connections": self.connections,
            "currentLocation": self.current_location
        }

    def generate_terrain(self):
        terrain = []
        terrain_groups = {"forest": [], "mountains": [], "water": []}
        
        for loc in self.locations.values():
            loc_type = loc.type.lower()
            if "forest" in loc_type:
                terrain_groups["forest"].append((loc.x, loc.y))
            elif "mountain" in loc_type:
                terrain_groups["mountains"].append((loc.x, loc.y))
            elif any(w in loc_type for w in ["lake", "river", "sea"]):
                terrain_groups["water"].append((loc.x, loc.y))
        
        for terrain_type, points in terrain_groups.items():
            if points:
                hull = convex_hull(points)
                points_str = " ".join(f"{x+random.randint(-20,20)},{y+random.randint(-20,20)}" for x,y in hull)
                terrain.append({
                    "type": terrain_type,
                    "points": points_str,
                    "fill": self.TERRAIN_COLORS.get(terrain_type, "#888888")
                })
        
        # Add background plains
        terrain.append({
            "type": "plains",
            "points": "0,0 1000,0 1000,800 0,800",
            "fill": self.TERRAIN_COLORS["plains"]
        })
        
        return terrain

    def get_connection_data(self):
        connections = []
        location_ids = list(self.locations.keys())
        for i in range(len(location_ids) - 1):
            loc1 = self.locations[location_ids[i]]
            loc2 = self.locations[location_ids[i+1]]
            connections.append({
                "x1": loc1.x, "y1": loc1.y,
                "x2": loc2.x, "y2": loc2.y
            })
        return connections