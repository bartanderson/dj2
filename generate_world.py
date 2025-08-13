import json
import random
from pathlib import Path
from world.world_builder import WorldBuilder
from world.campaign import WorldState, Location, Faction, Quest
from world.ai_integration import DungeonAI
from world.t2i import TextToImage  # New image generator
import uuid
import time

class MinimalState:
    """Dummy state for AI initialization"""
    def __init__(self):
        self.party_position = (0, 0)
        self.grid_system = None
        self.secret_mask = []

def generate_location_image_prompt(location_data, theme, location_type):
    """Create robust prompt for location image generation"""
    # Base description
    prompt = f"{theme} {location_type}: {location_data['name']}"
    
    # Add description details
    if location_data.get('description'):
        desc = location_data['description'][:200].replace('\n', ' ').strip()
        if desc:
            prompt += f", {desc}"
    
    # Add features if available
    if location_data.get('features'):
        features = ", ".join(location_data['features'][:3])
        prompt += f", featuring {features}"
    
    # Add quality boosters
    prompt += ", detailed, atmospheric, fantasy art, digital painting"
    
    # Ensure minimum length
    if len(prompt) < 30:
        prompt += ", imaginative fantasy landscape"
    
    return prompt

def generate_world(theme="fantasy", region_count=3, locations_per_region=4, seed=42):
    # Set all random seeds
    random.seed(seed)

    # Initialize AI system
    ai = DungeonAI(MinimalState(), seed=seed)
    builder = WorldBuilder(ai)
    
    print("Generating campaign foundation...")
    foundation = builder.generate("campaign_foundation", theme=theme)
    print(f"Campaign: {foundation['name']}")
    print(f"Core Conflict: {foundation['core_conflict']}")
    
    # Initialize world state
    world = WorldState()
    
    # Initialize image generator
    model_path = Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors"
    t2i = TextToImage(model_path)
    image_dir = Path("static/world_images")
    image_dir.mkdir(exist_ok=True, parents=True)
    
    # Prepare data structures
    image_requests = []
    locations_to_update = []

    # Deterministic coordinate generation
    rng = random.Random(seed)
    
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
            
            # Add coordinates
            x = rng.randint(50, 950)
            y = rng.randint(50, 750)
            
            # Create Location object without image
            loc_obj = Location(
                id=location['id'],
                name=location['name'],
                type=location['type'],
                description=location['description'],
                x=x,
                y=y,
                dungeon_type=location.get('dungeon_type'),
                dungeon_level=location.get('dungeon_level', 1)
            )
            
            # Add features and services
            loc_obj.features = location.get('features', [])
            loc_obj.services = location.get('services', [])
            
            world.add_location(loc_obj)
            print(f"  Location: {loc_obj.name} at ({x}, {y})")
            
            # Prepare image request
            prompt = generate_location_image_prompt(location, theme, location_type)
            image_requests.append({
                "request_id": f"loc-{location['id']}",
                "prompt": prompt,
                "seed": region_idx * 100 + loc_idx  # Unique seed
            })
            
            # Store for later image assignment
            locations_to_update.append((location['id'], loc_obj))
            
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
    
    # Batch generate all images
    print(f"\nGenerating {len(image_requests)} location images...")
    start_time = time.time()
    successes, failures = t2i.generate_batch(
        generation_requests=image_requests,
        output_dir=image_dir
    )
    gen_time = time.time() - start_time
    
    print(f"Image generation completed in {gen_time:.1f} seconds")
    print(f"  Successful: {len(successes)}")
    print(f"  Failed: {len(failures)}")
    
    # Process results and update locations
    for loc_id, loc_obj in locations_to_update:
        request_id = f"loc-{loc_id}"
        
        if request_id in successes:
            loc_obj.image_url = f"/static/world_images/{request_id}.jpg"
        else:
            # Find failure details
            failure = next((f for f in failures if f['request_id'] == request_id), None)
            error_msg = failure['exception'] if failure else "Unknown error"
            print(f"⚠️ Using placeholder for {loc_obj.name}: {error_msg}")
            
            # Create placeholder URL
            name_clean = loc_obj.name.replace(' ', '%20')
            loc_obj.image_url = f"https://via.placeholder.com/300x200?text={name_clean}"
    
    # Save failed requests for retry
    if failures:
        failure_file = Path("failed_generations.json")
        with failure_file.open("w") as f:
            json.dump(failures, f, indent=2)
        print(f"Saved failure details to: {failure_file}")
    
    # Save generated world
    save_world(world, f"{theme}_world.json", seed)
    print(f"\nWorld generation complete! Saved to {theme}_world.json")

def save_world(world_state, filename, seed):
    """Save world state to JSON file"""
    data = {
        "locations": [loc.to_dict() for loc in world_state.locations.values()],
        "factions": [fac.to_dict() for fac in world_state.factions.values()],
        "quests": [q.to_dict() for q in world_state.quests.values()],
        "seed": seed
    }
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    generate_world(theme="dark_fantasy", region_count=2)