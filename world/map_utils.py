import math
import random
from collections import defaultdict

class MapUtils:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
    
    def get_connections(self, world_map):
        """Generate logical connections based on location types"""
        locations = list(world_map.locations.values())
        
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