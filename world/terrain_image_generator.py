import math
import random
from PIL import Image, ImageDraw
from world.terrain_generator import TerrainGenerator

def generate_terrain_image(seed, output_path, width=1000, height=800, canvas_width=1600, canvas_height=1200, params=None):
    """
    Generate a terrain image using the same logic as test_terrain.py.
    Returns the image and the heightmap (for hex sampling).
    """
    gen = TerrainGenerator(seed, width, height)
    # Set parameters (defaults match test script tuned values)
    gen.ocean_height = params.get('ocean_height', -1.0) if params else -1.0
    gen.coast_height = params.get('coast_height', -1.0) if params else -1.0
    gen.lake_height = params.get('lake_height', 0.05) if params else 0.05
    gen.plains_high = params.get('plains_high', 0.35) if params else 0.35
    gen.hills_high = params.get('hills_high', 0.8) if params else 0.8
    gen.mountains_high = params.get('mountains_high', 0.9) if params else 0.9
    gen.snowcaps_low = params.get('snowcaps_low', 0.97) if params else 0.97
    gen.forest_min_moisture = params.get('forest_min_moisture', 0.5) if params else 0.5
    gen.forest_height_min = params.get('forest_height_min', 0.5) if params else 0.5
    gen.forest_height_max = params.get('forest_height_max', 0.65) if params else 0.65
    gen.river_target_per_10000_cells = params.get('river_target_per_10000_cells', 0.0002) if params else 0.0002
    gen.river_hill_threshold = params.get('river_hill_threshold', 0.7) if params else 0.7
    gen.river_mountain_threshold = params.get('river_mountain_threshold', 0.95) if params else 0.95

    heightmap = gen.generate_heightmap()
    moisture = gen.generate_moisture_map()
    river_mask, river_paths = gen.generate_rivers(heightmap)

    img = gen.render_terrain_image(heightmap, moisture, river_mask, river_paths, canvas_width, canvas_height)
    img.save(output_path)
    return img, heightmap, moisture, river_mask