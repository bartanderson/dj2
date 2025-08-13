import json
import random
from world_builder import WorldBuilder
from campaign import WorldState, Location, Faction, Quest
from ai_integration import DungeonAI
from t2i import TextToImage
from pathlib import Path

class MinimalState:
    """Dummy state for AI initialization"""
    def __init__(self):
        self.party_position = (0, 0)
        self.grid_system = None
        self.secret_mask = []

def generate_terrain_features(world):
    # Add terrain based on location types
    for location in world.locations.values():
        if location.type == "forest":
            location.terrain = "forest"
        elif location.type == "mountain":
            location.terrain = "mountain"

def generate_world(theme="fantasy", region_count=3, locations_per_region=4):
    # Initialize AI system
    ai = DungeonAI(MinimalState())
    builder = WorldBuilder(ai)

    model_path = Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors"
    t2i = TextToImage(model_path)
    image_dir = Path("static/world_images")
    image_dir.mkdir(exist_ok=True, parents=True)
    
    print("Generating campaign foundation...")
    foundation = builder.generate("campaign_foundation", theme=theme)
    print(f"Campaign: {foundation['name']}")
    print(f"Core Conflict: {foundation['core_conflict']}")
    
    # Initialize world state
    world = WorldState()
    
    # Generate regions and locations
    for region_idx in range(region_count):
        region = builder.generate("region", theme=theme)
        print(f"\nRegion {region_idx+1}: {region['name']}")
        print(f"  Geography: {region['geography']}")
        
        for loc_idx in range(locations_per_region):
            location_type = random.choice(["town", "village", "ruin", "forest", "mountain"])
            print(f"\nGenerating {location_type} location...")
            location = builder.generate("location", 
                                      location_type=location_type, 
                                      theme=theme)
            # Generate image URL
            image_url = generate_location_image(location, theme)

            # Generate image
            prompt = f"{theme} {location_type}: {location['name']}, {location['description'][:100]}"
            image_id = f"loc-{location['id']}"

            # Add coordinates
            x = random.randint(50, 950)
            y = random.randint(50, 750)

            try:
                img_id, img_path = t2i.generate(
                    prompt=prompt,
                    output_dir=image_dir,
                    image_id=image_id
                )
                image_url = f"/static/world_images/{img_id}.jpg"
            except Exception as e:
                print(f"Image generation failed: {e}")
                name_clean = location['name'].replace(' ', '%20')
                image_url = f"https://via.placeholder.com/300x200?text={name_clean}"            
            
            # Create Location object
            loc_obj = Location(
                id=location['id'],
                name=location['name'],
                type=location['type'],
                description=location['description'],
                x=x,
                y=y,
                dungeon_type=location.get('dungeon_type'),
                dungeon_level=location.get('dungeon_level', 1),
                image_url=image_url
            )
            
            # Add features and services
            loc_obj.features = location.get('features', [])
            loc_obj.services = location.get('services', [])
            
            world.add_location(loc_obj)
            print(f"  Location: {loc_obj.name} at ({x}, {y})")
            
            # Generate faction for region
            if region_idx == 0 and loc_idx == 0:  # First location in region
                faction = builder.generate("faction", theme=theme)
                faction_obj = Faction(
                    id=faction['id'],
                    name=faction['name'],
                    ideology=faction['ideology'],
                    goals=faction['goals']
                )
                world.add_faction(faction_obj)
                print(f"  Faction: {faction_obj.name} ({faction_obj.ideology})")
            
            # Generate quest
            quest = builder.generate("quest", 
                                   location=location['name'], 
                                   theme=theme)
            quest_obj = Quest(
                id=quest['id'],
                title=quest['title'],
                description=quest['description'],
                objectives=quest['objectives'],
                location_id=location['id'],
                dungeon_required=quest['dungeon_required']
            )
            world.add_quest(quest_obj)
            print(f"  Quest: {quest_obj.title}")
    
    # Save generated world
    save_world(world, f"{theme}_world.json")
    print(f"\nWorld generation complete! Saved to {theme}_world.json")

def save_world(world_state, filename):
    """Save world state to JSON file"""
    data = {
        "locations": [loc.to_dict() for loc in world_state.locations.values()],
        "factions": [fac.to_dict() for fac in world_state.factions.values()],
        "quests": [q.to_dict() for q in world_state.quests.values()]
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def generate_location_image(location):
    print(f"Generating image for {location.name}...")
    # ... your image generation code ...
    print(f"Generated image URL: {image_url}")
    return image_url

if __name__ == "__main__":
    generate_world(theme="dark_fantasy", region_count=2)