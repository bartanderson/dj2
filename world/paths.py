import math
import random

class PathGenerator:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
    
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
        if not hexes:
            return "plains"  # Default terrain

        closest_hex = None
        min_distance = float('inf')
        
        for hex in hexes:
            distance = math.sqrt((location['x']-hex['x'])**2 + (location['y']-hex['y'])**2)
            if distance < min_distance:
                min_distance = distance
                closest_hex = hex
        
        return closest_hex.get("terrain", "plains")
    
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