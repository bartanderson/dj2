#!/usr/bin/env python3
"""
Standalone test for TerrainGenerator.
Usage: python test_terrain.py --seed 42 --grid-width 80 --grid-height 80 --canvas-width 1600 --canvas-height 1200
"""

import argparse
from collections import Counter
from world.terrain_generator import TerrainGenerator
from PIL import ImageDraw

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--grid-width', type=int, default=80)
    parser.add_argument('--grid-height', type=int, default=80)
    parser.add_argument('--canvas-width', type=int, default=1600)
    parser.add_argument('--canvas-height', type=int, default=1200)
    parser.add_argument('--output', type=str, default='terrain_test.png')
    # Parameters to tune
    parser.add_argument('--ocean-height', type=float, default=-1.0)
    parser.add_argument('--coast-height', type=float, default=-1.0)
    parser.add_argument('--lake-height', type=float, default=-1.0)
    parser.add_argument('--plains-high', type=float, default=0.7)
    parser.add_argument('--hills-high', type=float, default=0.8)
    parser.add_argument('--mountains-high', type=float, default=0.9)
    parser.add_argument('--snowcaps-low', type=float, default=0.97)
    parser.add_argument('--forest-min-moisture', type=float, default=0.5)
    parser.add_argument('--forest-height-min', type=float, default=0.5)
    parser.add_argument('--forest-height-max', type=float, default=0.65)
    parser.add_argument('--river-target', type=float, default=0.0)
    parser.add_argument('--hill-threshold', type=float, default=0.5)
    parser.add_argument('--mountain-threshold', type=float, default=0.65)

    args = parser.parse_args()

    gen = TerrainGenerator(
        seed=args.seed,
        grid_width=args.grid_width,
        grid_height=args.grid_height,
        ocean_height=args.ocean_height,
        coast_height=args.coast_height,
        lake_height=args.lake_height,
        plains_high=args.plains_high,
        hills_high=args.hills_high,
        mountains_high=args.mountains_high,
        snowcaps_low=args.snowcaps_low,
        forest_min_moisture=args.forest_min_moisture,
        forest_height_min=args.forest_height_min,
        forest_height_max=args.forest_height_max,
        river_target_per_10000_cells=args.river_target,
        river_hill_threshold=args.hill_threshold,
        river_mountain_threshold=args.mountain_threshold
    )

    print("river_mountain_threshold: ", gen.river_mountain_threshold)

    heightmap = gen.generate_heightmap()
    moisture = gen.generate_moisture_map()
    rivers, river_paths = gen.generate_rivers(heightmap)

    # Simulate hex terrain assignment (sample at grid centers)
    hex_terrain_counts = Counter()
    for y in range(args.grid_height):
        for x in range(args.grid_width):
            h = heightmap[y][x]
            m = moisture[y][x]
            if h < gen.ocean_height:
                terrain = 'ocean'
            elif h < gen.coast_height:
                terrain = 'coast'
            elif h < gen.plains_high:
                terrain = 'plains'
            elif h < gen.hills_high:
                terrain = 'hills'
            elif h < gen.mountains_high:
                terrain = 'mountains'
            else:
                terrain = 'snowcaps'
            if gen.forest_height_min <= h <= gen.forest_height_max and m > gen.forest_min_moisture:
                terrain = 'forest'
            if h < gen.lake_height:
                terrain = 'lake'
            hex_terrain_counts[terrain] += 1
    print("Hex terrain distribution:", dict(hex_terrain_counts))

    img = gen.render_terrain_image(heightmap, moisture, rivers, river_paths, args.canvas_width, args.canvas_height)
    # draw = ImageDraw.Draw(img)
    # draw.line([(0, 0), (100, 100)], fill=(255, 0, 0), width=5)
    img.save(args.output)
    print(f"Saved image to {args.output}")

if __name__ == '__main__':
    main()