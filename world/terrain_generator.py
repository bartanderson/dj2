import math
import random
from PIL import Image, ImageDraw

# ============================================================================
# Perlin Noise (exact JS port)
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
# Terrain Generator – exact JS logic with tunable parameters
# ============================================================================
class TerrainGenerator:
    def __init__(self, seed, grid_width, grid_height,
                 ocean_height=-1.0, coast_height=-1.0, lake_height=-1.0,
                 plains_high=0.7, hills_high=0.8, mountains_high=0.9, snowcaps_low=0.97,
                 forest_min_moisture=0.5, forest_height_min=0.5, forest_height_max=0.65,
                 river_target_per_10000_cells=0.0, river_hill_threshold=0.5, river_mountain_threshold=0.65,
                 contrast_exponent=1.0):
        self.seed = seed
        self.grid_w = grid_width
        self.grid_h = grid_height
        self.ocean_height = ocean_height
        self.coast_height = coast_height
        self.lake_height = lake_height
        self.plains_high = plains_high
        self.hills_high = hills_high
        self.mountains_high = mountains_high
        self.snowcaps_low = snowcaps_low
        self.forest_min_moisture = forest_min_moisture
        self.forest_height_min = forest_height_min
        self.forest_height_max = forest_height_max
        self.river_target_per_10000_cells = river_target_per_10000_cells
        self.river_hill_threshold = river_hill_threshold
        self.river_mountain_threshold = river_mountain_threshold
        self.contrast_exponent = contrast_exponent

        self.perlin = PerlinNoise(seed)
        self.moisture_perlin = PerlinNoise(seed + 1000)

    def generate_heightmap(self):
        w, h = self.grid_w, self.grid_h
        scale = 0.005
        octaves = 4
        persistence = 0.5
        lacunarity = 2.0

        # Compute max noise for normalization (as in JS)
        max_noise = 0
        amp = 1
        for _ in range(octaves):
            max_noise += amp
            amp *= persistence

        heightmap = [[0.0] * w for _ in range(h)]
        raw_min = float('inf')
        raw_max = -float('inf')
        for y in range(h):
            for x in range(w):
                noise_val = 0
                a = 1
                f = 1
                for _ in range(octaves):
                    noise_val += self.perlin.noise(x * scale * f, y * scale * f) * a
                    a *= persistence
                    f *= lacunarity
                raw_min = min(raw_min, noise_val)
                raw_max = max(raw_max, noise_val)
                heightmap[y][x] = (noise_val + max_noise) / (2 * max_noise)

        print(f"DEBUG: Raw noise range = {raw_min:.3f} to {raw_max:.3f} (max_noise={max_noise})")

        # Rescale to 0-1 based on actual min/max
        min_h = min(min(row) for row in heightmap)
        max_h = max(max(row) for row in heightmap)
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                heightmap[y][x] = (heightmap[y][x] - min_h) / (max_h - min_h)

        # Apply contrast enhancement
        for y in range(self.grid_h):
            for x in range(self.grid_w):
                heightmap[y][x] = heightmap[y][x] ** 2.0

        from collections import Counter
        buckets = [0]*10
        for row in heightmap:
            for v in row:
                idx = int(v*10)
                if idx == 10: idx = 9
                buckets[idx] += 1
        print("Height distribution (0-0.1, 0.1-0.2,...):", buckets)

        # Check normalized range
        norm_min = min(min(row) for row in heightmap)
        norm_max = max(max(row) for row in heightmap)
        print(f"DEBUG: Normalized heightmap range = {norm_min:.3f} to {norm_max:.3f}")
        return heightmap

    def generate_moisture_map(self):
        w, h = self.grid_w, self.grid_h
        scale = 0.005
        octaves = 4
        persistence = 0.5
        lacunarity = 2.0
        max_noise = 0
        amp = 1
        for _ in range(octaves):
            max_noise += amp
            amp *= persistence
        moisture = [[0.0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                noise_val = 0
                a = 1
                f = 1
                for _ in range(octaves):
                    noise_val += self.moisture_perlin.noise(x * scale * f, y * scale * f) * a
                    a *= persistence
                    f *= lacunarity
                moisture[y][x] = (noise_val + max_noise) / (2 * max_noise)
        return moisture

    def generate_rivers(self, heightmap):
        w, h = self.grid_w, self.grid_h
        area = w * h
        target_count = int(area / 8000 * self.river_target_per_10000_cells * 10000)
        river_mask = [[False] * w for _ in range(h)]
        river_paths = []
        used_cells = set()           # track all cells occupied by any river (or attempted)
        rng = random.Random(self.seed + 10000)

        # Find start candidates
        candidates = []
        for y in range(h):
            for x in range(w):
                h_val = heightmap[y][x]
                if self.river_hill_threshold <= h_val <= self.river_mountain_threshold:
                    candidates.append((x, y))
        rng.shuffle(candidates)

        max_steps = 300
        min_distance = 10   # cells, Chebyshev distance

        for r in range(min(target_count, len(candidates))):
            x, y = candidates[r]
            # Check if start cell is too close to any existing river cell
            too_close = False
            for (ux, uy) in used_cells:
                if max(abs(x - ux), abs(y - uy)) <= min_distance:
                    too_close = True
                    break
            if too_close:
                continue

            # Generate river path
            visited = set()
            path = []
            steps = 0
            cx, cy = x, y
            while True:
                if not (0 <= cx < w and 0 <= cy < h):
                    break
                key = (cx, cy)
                if key in visited:
                    break
                visited.add(key)
                path.append((cx, cy))
                h_val = heightmap[cy][cx]
                if h_val < self.lake_height:
                    break
                # Find lower neighbors
                neighbors = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                            nh = heightmap[ny][nx]
                            if nh < h_val:
                                neighbors.append((nx, ny, nh))
                if not neighbors:
                    break
                # Weighted random
                total = sum((h_val - nh) + 0.1 for _, _, nh in neighbors)
                rand = rng.random() * total
                cum = 0
                chosen = None
                for nx, ny, nh in neighbors:
                    cum += (h_val - nh) + 0.1
                    if rand < cum:
                        chosen = (nx, ny)
                        break
                if chosen is None:
                    chosen = neighbors[0][:2]
                cx, cy = chosen
                steps += 1
                if steps > max_steps:
                    break

            # Mark all cells in the path (even short) as used
            for (px, py) in path:
                used_cells.add((px, py))
            # Only keep longer paths as rivers
            if len(path) > 2:
                for (px, py) in path:
                    river_mask[py][px] = True
                river_paths.append(path)
        
        print(f"Target count: {target_count}")
        print(f"River mask cells: {sum(sum(row) for row in river_mask)}")
        print(f"Start candidates: {len(candidates)}")

        return river_mask, river_paths

    def render_terrain_image(self, heightmap, moisture_map, river_mask, river_paths, canvas_w, canvas_h):
        # Instead of setting pixels directly, we can keep the pixel loop, then draw lines over it.
        grid_w, grid_h = self.grid_w, self.grid_h
        img = Image.new('RGB', (canvas_w, canvas_h))
        draw = ImageDraw.Draw(img)

        pixels = img.load()

        # Color mapping (RGB tuples from JS hex colors)
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

        for py in range(canvas_h):
            for px in range(canvas_w):
                # Map to grid coordinates
                nx = (px / canvas_w) * (grid_w - 1)
                ny = (py / canvas_h) * (grid_h - 1)

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

                # Determine terrain (same order as JS)
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

                # Forest override
                if self.forest_height_min <= h <= self.forest_height_max and m > self.forest_min_moisture:
                    terrain = 'forest'

                # Lake override (low-lying)
                if h < self.lake_height:
                    terrain = 'lake'

                pixels[px, py] = color_map[terrain]

        #print(f"DEBUG: lake_height = {self.lake_height}")
        for path in river_paths:
            if len(path) < 2: continue
            points = [(int((x/(self.grid_w-1))*(canvas_w-1)), int((y/(self.grid_h-1))*(canvas_h-1))) for (x,y) in path]
            draw.line(points, fill=color_map['lake'], width=12)
        # river_img.save("rivers_only.png")

        return img
