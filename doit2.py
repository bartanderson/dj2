#!/usr/bin/env python3
"""
Standalone terrain image generator replicating the JavaScript tuner.
Usage: python terrain_gen_standalone.py --seed 42 --output terrain.png --width 1600 --height 1200
"""

import argparse
import math
import random
from PIL import Image

# ============================================================================
# Perlin Noise – exact port of the JS version from your tuner
# ============================================================================
class PerlinNoise:
    def __init__(self, seed):
        self.p = [0] * 512
        perm = self._generate_permutation(seed)
        for i in range(512):
            self.p[i] = perm[i % 256]

    def _generate_permutation(self, seed):
        rng = random.Random(seed)
        p = list(range(256))
        for i in range(255, -1, -1):
            j = rng.randint(0, i)
            p[i], p[j] = p[j], p[i]
        return p

    def _fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def _lerp(self, t, a, b):
        return a + t * (b - a)

    def _grad(self, hash_val, x, y, z):
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else z)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x, y, z=0):
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        Z = int(math.floor(z)) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        z -= math.floor(z)
        u = self._fade(x)
        v = self._fade(y)
        w = self._fade(z)

        A = (self.p[X] + Y) & 255
        AA = (self.p[A] + Z) & 255
        AB = (self.p[A + 1] + Z) & 255
        B = (self.p[X + 1] + Y) & 255
        BA = (self.p[B] + Z) & 255
        BB = (self.p[B + 1] + Z) & 255

        return self._lerp(w,
            self._lerp(v, self._lerp(u, self._grad(self.p[AA], x, y, z), self._grad(self.p[BA], x - 1, y, z)),
                          self._lerp(u, self._grad(self.p[AB], x, y - 1, z), self._grad(self.p[BB], x - 1, y - 1, z))),
            self._lerp(v, self._lerp(u, self._grad(self.p[AA + 1], x, y, z - 1), self._grad(self.p[BA + 1], x - 1, y, z - 1)),
                          self._lerp(u, self._grad(self.p[AB + 1], x, y - 1, z - 1), self._grad(self.p[BB + 1], x - 1, y - 1, z - 1))))

# ============================================================================
# Terrain Generator (exact JS logic)
# ============================================================================
class TerrainGenerator:
    def __init__(self, seed, grid_width, grid_height):
        self.seed = seed
        self.grid_w = grid_width
        self.grid_h = grid_height
        self.rng = random.Random(seed)
        self.perlin = PerlinNoise(seed)
        self.moisture_perlin = PerlinNoise(seed + 1000)

        # Default parameters (can be overridden)
        self.ocean_height = 0.2
        self.coast_height = 0.35
        self.lake_height = 0.36
        self.river_hill_threshold = 0.5
        self.river_mountain_threshold = 0.65
        self.river_target_per_10000_cells = 5.0
        self.forest_min_moisture = 0.5
        self.forest_height_min = 0.5
        self.forest_height_max = 0.65
        self.plains_high = 0.58
        self.hills_high = 0.65
        self.mountains_high = 0.73
        self.snowcaps_low = 0.73

    def generate_heightmap(self):
        width, height = self.grid_w, self.grid_h
        scale = 0.005
        octaves = 4
        persistence = 0.5
        lacunarity = 2.0
        max_noise = 0
        amp = 1
        for _ in range(octaves):
            max_noise += amp
            amp *= persistence
        heightmap = [[0.0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                noise = 0
                a = 1
                f = 1
                for _ in range(octaves):
                    noise += self.perlin.noise(x * scale * f, y * scale * f) * a
                    a *= persistence
                    f *= lacunarity
                heightmap[y][x] = (noise + max_noise) / (2 * max_noise)
        return heightmap

    def generate_moisture_map(self):
        width, height = self.grid_w, self.grid_h
        scale = 0.005
        octaves = 4
        persistence = 0.5
        lacunarity = 2.0
        max_noise = 0
        amp = 1
        for _ in range(octaves):
            max_noise += amp
            amp *= persistence
        moisture = [[0.0] * width for _ in range(height)]
        for y in range(height):
            for x in range(width):
                noise = 0
                a = 1
                f = 1
                for _ in range(octaves):
                    noise += self.moisture_perlin.noise(x * scale * f, y * scale * f) * a
                    a *= persistence
                    f *= lacunarity
                moisture[y][x] = (noise + max_noise) / (2 * max_noise)
        return moisture

    def generate_rivers(self, heightmap):
        width, height = self.grid_w, self.grid_h
        area = width * height
        target_count = int(area / 8000 * self.river_target_per_10000_cells * 10000)
        river_mask = [[False] * width for _ in range(height)]
        rng = random.Random(self.seed + 10000)

        # Find start candidates (cells with height between hill and mountain thresholds)
        candidates = []
        for y in range(height):
            for x in range(width):
                h = heightmap[y][x]
                if self.river_hill_threshold <= h <= self.river_mountain_threshold:
                    candidates.append((x, y))
        rng.shuffle(candidates)

        max_steps = 300
        for r in range(min(target_count, len(candidates))):
            x, y = candidates[r]
            visited = set()
            path = []
            steps = 0
            while True:
                if not (0 <= x < width and 0 <= y < height):
                    break
                key = (x, y)
                if key in visited:
                    break
                visited.add(key)
                path.append((x, y))
                h = heightmap[y][x]
                if h < self.lake_height:
                    break
                # Find lower neighbors
                neighbors = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                            nh = heightmap[ny][nx]
                            if nh < h:
                                neighbors.append((nx, ny, nh))
                if not neighbors:
                    break
                # Weighted random selection
                total = sum((h - nh) + 0.1 for _, _, nh in neighbors)
                rand = rng.random() * total
                cum = 0
                chosen = None
                for nx, ny, nh in neighbors:
                    cum += (h - nh) + 0.1
                    if rand < cum:
                        chosen = (nx, ny)
                        break
                if chosen is None:
                    chosen = neighbors[0][:2]
                x, y = chosen
                steps += 1
                if steps > max_steps:
                    break
            for (px, py) in path:
                river_mask[py][px] = True
        return river_mask

    def render_terrain_image(self, heightmap, moisture_map, river_mask, canvas_width, canvas_height):
        # Bilinear interpolation to scale the grid to canvas size
        grid_w, grid_h = self.grid_w, self.grid_h
        img = Image.new('RGB', (canvas_width, canvas_height))
        pixels = img.load()

        color_map = {
            'ocean':    (77, 111, 184),
            'coast':    (162, 196, 201),
            'plains':   (104, 159, 56),
            'forest':   (44, 94, 46),
            'hills':    (141, 153, 70),
            'mountains':(141, 153, 174),
            'snowcaps': (255, 255, 255),
            'river':    (74, 144, 226),
            'lake':     (58, 128, 194)
        }

        for py in range(canvas_height):
            for px in range(canvas_width):
                # Map pixel to grid coordinates
                nx = (px / canvas_width) * (grid_w - 1)
                ny = (py / canvas_height) * (grid_h - 1)

                x0 = int(math.floor(nx))
                x1 = min(x0 + 1, grid_w - 1)
                y0 = int(math.floor(ny))
                y1 = min(y0 + 1, grid_h - 1)
                dx = nx - x0
                dy = ny - y0

                # Bilinear interpolation of height
                h00 = heightmap[y0][x0]
                h01 = heightmap[y1][x0]
                h10 = heightmap[y0][x1]
                h11 = heightmap[y1][x1]
                h = (1-dx)*(1-dy)*h00 + dx*(1-dy)*h10 + (1-dx)*dy*h01 + dx*dy*h11

                # Bilinear interpolation of moisture
                m00 = moisture_map[y0][x0]
                m01 = moisture_map[y1][x0]
                m10 = moisture_map[y0][x1]
                m11 = moisture_map[y1][x1]
                m = (1-dx)*(1-dy)*m00 + dx*(1-dy)*m10 + (1-dx)*dy*m01 + dx*dy*m11

                # Base terrain (same as JS)
                if h < self.ocean_height:
                    terrain = 'ocean'
                elif h < self.coast_height:
                    terrain = 'coast'
                elif h < self.plains_high:
                    terrain = 'plains'
                elif h < self.hills_high:
                    terrain = 'hills'
                elif h < self.mountains_high:
                    terrain = 'mountains'
                else:
                    terrain = 'snowcaps'

                # Forest override (same as JS)
                if self.forest_height_min <= h <= self.forest_height_max and m > self.forest_min_moisture:
                    terrain = 'forest'

                # Lake override (same as JS)
                if h < self.lake_height:
                    terrain = 'lake'

                pixels[px, py] = color_map[terrain]

        # Rivers: draw 1‑pixel lines at the scaled positions of river cells
        for y in range(grid_h):
            for x in range(grid_w):
                if river_mask[y][x]:
                    px = int((x / (grid_w - 1)) * (canvas_width - 1))
                    py = int((y / (grid_h - 1)) * (canvas_height - 1))
                    if 0 <= px < canvas_width and 0 <= py < canvas_height:
                        pixels[px, py] = color_map['river']

        return img

def main():
    parser = argparse.ArgumentParser(description='Generate terrain image (exact JS replica)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--grid-width', type=int, default=400, help='Grid width (number of cells)')
    parser.add_argument('--grid-height', type=int, default=300, help='Grid height (number of cells)')
    parser.add_argument('--canvas-width', type=int, default=1600, help='Output image width')
    parser.add_argument('--canvas-height', type=int, default=1200, help='Output image height')
    parser.add_argument('--output', type=str, default='terrain.png', help='Output PNG file')
    # Tuning parameters (defaults from your tuner)
    parser.add_argument('--ocean-height', type=float, default=0.2)
    parser.add_argument('--coast-height', type=float, default=0.35)
    parser.add_argument('--lake-height', type=float, default=0.36)
    parser.add_argument('--river-multiplier', type=float, default=5.0)
    parser.add_argument('--hill-threshold', type=float, default=0.5)
    parser.add_argument('--forest-min-moisture', type=float, default=0.5)
    args = parser.parse_args()

    gen = TerrainGenerator(args.seed, args.grid_width, args.grid_height)
    gen.ocean_height = args.ocean_height
    gen.coast_height = args.coast_height
    gen.lake_height = args.lake_height
    gen.river_target_per_10000_cells = args.river_multiplier
    gen.river_hill_threshold = args.hill_threshold
    gen.forest_min_moisture = args.forest_min_moisture

    heightmap = gen.generate_heightmap()
    moisture = gen.generate_moisture_map()
    rivers = gen.generate_rivers(heightmap)
    img = gen.render_terrain_image(heightmap, moisture, rivers, args.canvas_width, args.canvas_height)
    img.save(args.output)
    print(f"Saved terrain image to {args.output}")

if __name__ == '__main__':
    main()