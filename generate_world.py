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

class NameGenerator:
    """Sophisticated name generator with thematic consistency and uniqueness"""
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.used_names = set()
        
        # Thematic components database
        self.themes = {
            "dark_fantasy": {
                "prefixes": ["Black", "Shadow", "Gloom", "Dread", "Bleak", "Raven", "Crow", "Viper", "Serpent"],
                "cores": ["wood", "fell", "mire", "fen", "scar", "wound", "grave", "crypt", "bone", "ash"],
                "suffixes": ["rest", "keep", "hold", "watch", "spire", "peak", "vale", "hollow"],
                "titles": ["Curse", "Shadow", "Blood", "Doom", "Crypt", "Bone", "Ashes", "Viper", "Serpent"]
            },
            "high_fantasy": {
                "prefixes": ["Silver", "Golden", "High", "Bright", "Sun", "Star", "Moon", "Dragon"],
                "cores": ["wood", "glen", "field", "meadow", "brook", "haven", "light", "hope"],
                "suffixes": ["shire", "rest", "hold", "watch", "spire", "peak", "vale", "grove"],
                "titles": ["Light", "Hope", "Crown", "Sword", "Shield", "Dragon", "Star", "Moon"]
            }
        }
    
    def generate_name(self, base_type, theme="dark_fantasy", location_type=None):
        """Generate unique thematic name"""
        theme_data = self.themes.get(theme, self.themes["dark_fantasy"])
        
        # Special cases for location types
        if location_type == "mountain":
            components = [self.rng.choice(["Peak", "Spire", "Crag", "Summit"]),
                          self.rng.choice(theme_data["prefixes"])]
            name = f"{components[1]}{components[0]}"
        elif location_type == "ruin":
            components = [self.rng.choice(theme_data["titles"]),
                          self.rng.choice(theme_data["suffixes"])]
            name = f"{components[0]}{components[1]} Ruins"
        elif location_type == "village":
            components = [self.rng.choice(theme_data["prefixes"]),
                          self.rng.choice(theme_data["cores"])]
            name = f"{components[0]}{components[1]}"
        else:
            # Standard name generation
            components = [
                self.rng.choice(theme_data["prefixes"]),
                self.rng.choice(theme_data["cores"]),
                self.rng.choice(theme_data["suffixes"])
            ]
            name = f"{components[0]}{components[1]}{components[2]}"
        
        # Ensure uniqueness
        original_name = name
        counter = 1
        while name in self.used_names:
            name = f"{original_name} {self.rng.choice(['of', 'in', 'at'])} {self.rng.choice(theme_data['prefixes'])}{self.rng.choice(theme_data['suffixes'])}"
            counter += 1
            if counter > 5:  # Prevent infinite loops
                break
        
        self.used_names.add(name)
        return name

    def generate_quest_title(self, location_name, theme="dark_fantasy"):
        """Generate unique quest title related to location"""
        theme_data = self.themes.get(theme, self.themes["dark_fantasy"])
        patterns = [
            f"The {self.rng.choice(theme_data['titles'])} of {location_name}",
            f"{location_name}'s {self.rng.choice(['Secret', 'Curse', 'Legacy', 'Doom'])}",
            f"The {self.rng.choice(theme_data['prefixes'])}{self.rng.choice(theme_data['suffixes'])} {self.rng.choice(['Incident', 'Affair', 'Mystery'])}",
            f"{self.rng.choice(['Lost', 'Forgotten', 'Hidden'])} {self.rng.choice(theme_data['titles'])}",
            f"{self.rng.choice(theme_data['prefixes'])} {self.rng.choice(['Conspiracy', 'Betrayal', 'Reckoning'])}"
        ]
        
        title = self.rng.choice(patterns)
        counter = 1
        while title in self.used_names:
            title = f"{title}: {self.rng.choice(['Part', 'Chapter', 'Saga'])} {counter}"
            counter += 1
        
        self.used_names.add(title)
        return title

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


def generate_unique_name(base_name, existing_names, theme, location_type, seed, region_idx, loc_idx):
    """Generate unique name with thematic modifiers"""
    modifiers = {
        "dark_fantasy": [
            "Black", "Shadow", "Gloom", "Dread", "Bleak", "Ashen", "Crimson", 
            "Dire", "Grim", "Raven", "Vile", "Forsaken", "Doom", "Wraith"
        ],
        "generic": [
            "North", "South", "East", "West", "Upper", "Lower", "New", "Old",
            "Port", "Fort", "Crossing", "Bridge", "Haven", "Hold", "Spire"
        ],
        "features": [
            "Falls", "Peak", "Vale", "Wood", "Marsh", "Crag", "Hollow", "Gorge",
            "Cliff", "Summit", "Pass", "Reach", "Watch", "Keep", "Sanctum"
        ]
    }

def generate_world(theme="dark_fantasy", region_count=3, locations_per_region=4, seed=42):
    # Set all random seeds
    random.seed(seed)
    
    # Initialize name generator
    name_gen = NameGenerator(seed)
    
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
        region_name = name_gen.generate_name("region", theme)
        region_desc = f"{name_gen.rng.choice(['Mountainous', 'Forested', 'Coastal', 'Riverine'])} region with {name_gen.rng.choice(['ancient ruins', 'deep caves', 'hidden valleys', 'forgotten temples'])}"
        
        print(f"\nRegion {region_idx+1}: {region_name}")
        print(f"  Geography: {region_desc}")
        
        for loc_idx in range(locations_per_region):
            location_type = rng.choice(["town", "village", "ruin", "forest", "mountain"])
            print(f"\nGenerating {location_type} location...")
            
            # Generate unique names
            loc_name = name_gen.generate_name("location", theme, location_type)
            quest_title = name_gen.generate_quest_title(loc_name, theme)
            
            # Create rich location description
            loc_desc = f"A {location_type} known for its {rng.choice(['mysterious past', 'strategic importance', 'dark secrets', 'ancient guardians'])}"
            
            # Create Location object
            loc_obj = Location(
                id=f"loc_{region_idx}_{loc_idx}_{uuid.uuid4().hex[:8]}",
                name=loc_name,
                type=location_type,
                description=loc_desc,
                x=rng.randint(50, 950),
                y=rng.randint(50, 750),
                dungeon_type=f"{theme}_{rng.choice(['crypt', 'caverns', 'fortress', 'lair'])}",
                dungeon_level=rng.randint(1, 5)
            )
            
            # Add features and services
            loc_obj.features = [
                f"{rng.choice(['Ancient', 'Forgotten', 'Hidden'])} {rng.choice(['Temple', 'Monument', 'Observatory'])}",
                f"{rng.choice(['Haunted', 'Sacred', 'Cursed'])} {rng.choice(['Woods', 'Spring', 'Grounds'])}"
            ]
            
            if location_type == "town":
                loc_obj.services = ["Inn", "Blacksmith", "Market", "Temple", "Tavern"]
            elif location_type == "village":
                loc_obj.services = ["Healer", "General Store", "Meeting Hall"]
            else:
                loc_obj.services = []
            
            world.add_location(loc_obj)
            print(f"  Location: {loc_obj.name} at ({loc_obj.x}, {loc_obj.y})")
            
            # Prepare image request
            prompt = generate_location_image_prompt({
                "name": loc_name,
                "description": loc_desc,
                "features": loc_obj.features
            }, theme, location_type)
            
            image_requests.append({
                "request_id": f"loc-{loc_obj.id}",
                "prompt": prompt,
                "seed": region_idx * 100 + loc_idx  # Unique seed
            })
            
            # Store for later image assignment
            locations_to_update.append((loc_obj.id, loc_obj))
            
            # Generate faction for region
            if region_idx == 0 and loc_idx == 0:
                faction_name = f"{rng.choice(['Order', 'Brotherhood', 'Circle'])} of {name_gen.generate_name('faction', theme)}"
                faction_desc = f"{rng.choice(['Secret society', 'Ancient order', 'Power-hungry cult'])} seeking {rng.choice(['forbidden knowledge', 'eternal life', 'dominion over all'])}"
                
                faction_obj = Faction(
                    id=f"fac_{uuid.uuid4().hex[:8]}",
                    name=faction_name,
                    ideology=faction_desc,
                    goals=[
                        f"{rng.choice(['Control', 'Destroy', 'Protect'])} the {rng.choice(['artifact', 'relic', 'tome'])}",
                        f"{rng.choice(['Conquer', 'Liberate', 'Purify'])} {name_gen.generate_name('region', theme)}"
                    ]
                )
                world.add_faction(faction_obj)
                print(f"  Faction: {faction_obj.name} ({faction_obj.ideology})")
            
            # Generate quest
            quest_obj = Quest(
                id=f"quest_{uuid.uuid4().hex[:8]}",
                title=quest_title,
                description=f"{rng.choice(['Investigate', 'Recover', 'Destroy'])} the {rng.choice(['ancient artifact', 'forbidden tome', 'cursed relic'])} in {loc_name}",
                objectives=[
                    f"{rng.choice(['Find clues', 'Gather allies', 'Decipher texts'])} in {loc_name}",
                    f"{rng.choice(['Confront', 'Negotiate with', 'Evade'])} the {rng.choice(['guardian', 'spirit', 'beast'])}",
                    f"{rng.choice(['Retrieve', 'Destroy', 'Purify'])} the {rng.choice(['artifact', 'relic', 'source'])}"
                ],
                location_id=loc_obj.id,
                dungeon_required=rng.random() > 0.3
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