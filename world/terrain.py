# world/terrain.py
import math
import random
import numpy as np
from scipy.ndimage import gaussian_filter

class TerrainGenerator:
    def __init__(self, seed=42):
        self.seed = seed
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)
        self.terrain_types = {
            "ocean": {"weight": 0.25, "height": -0.5},
            "coast": {"weight": 0.05, "height": -0.2},
            "lake": {"weight": 0.05, "height": -0.3},
            "river": {"weight": 0.05, "height": -0.1},
            "plains": {"weight": 0.25, "height": 0.2},
            "hills": {"weight": 0.15, "height": 0.4},
            "mountains": {"weight": 0.15, "height": 0.7},
            "snowcaps": {"weight": 0.05, "height": 0.9}
        }

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
            layer = self.np_rng.random((height, width)) * amplitude
            
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
                    f"{float(p.split(',')[0]) + self.rng.uniform(-hex_size*jitter, hex_size*jitter)}," +
                    f"{float(p.split(',')[1]) + self.rng.uniform(-hex_size*jitter, hex_size*jitter)}"
                    for p in points
                ]
                
                hexes.append({
                    "x": x,
                    "y": y + y_offset,
                    "terrain": terrain,
                    "points": " ".join(points),  # Using original points for now
                    "height": self.terrain_types[terrain]["height"]
                })
        
        return hexes

    def get_terrain_colors(self):
        """Return color mapping for frontend"""
        return {
            "ocean": "#4d6fb8",
            "coast": "#a2c4c9",
            "lake": "#4d6fb8",
            "river": "#4d6fb8",
            "plains": "#689f38",
            "hills": "#8d9946",
            "mountains": "#8d99ae",
            "snowcaps": "#ffffff"
        }

    # TODO: This was used at one time for testing, see if we want it when we test
    # def debug_terrain_distribution(self, terrain_grid):
    #     from collections import defaultdict
    #     counts = defaultdict(int)
    #     total = 0
        
    #     for row in terrain_grid:
    #         for terrain in row:
    #             counts[terrain] += 1
    #             total += 1
        
    #     print("Terrain Distribution:")
    #     for terrain, count in counts.items():
    #         print(f"{terrain}: {count/total*100:.1f}%")
        
    #     return counts

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