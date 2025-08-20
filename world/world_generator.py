# world\world_generator.py
import json
import uuid
import time
import random
from psycopg2.extras import Json
from pathlib import Path
from world.db import Database
from world.world_builder import WorldBuilder
from world.campaign import WorldState, Location, Faction, Quest, NPC
from world.ai_integration import DungeonAI
from world.t2i import TextToImage  # New image generator

class WorldGenerator:
    def __init__(self, ai_system=None, seed=42, model_path=None, image_output_dir=None):
        self.ai = ai_system
        self.seed = seed
        self.builder = WorldBuilder(ai_system)
        self.name_gen = NameGenerator(seed)
        
        # Image generation setup
        self.model_path = model_path or (Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors")
        self.image_output_dir = Path(image_output_dir or "static/world_images")
        self.t2i = None  # Will be initialized when needed
        
        # Configurable world parameters
        self.default_params = {
            "region_count": 3,
            "locations_per_region": 4,
            "quest_density": 0.8,
            "dungeon_probability": 0.6,
            "faction_count": 2,
            "npc_density": 0.7,
            "generate_images": True  # Added image generation flag
        }

    def generate(self, theme="dark_fantasy", **custom_params):
        """Generate a complete world with configurable parameters including images"""
        # Merge default and custom parameters
        params = {**self.default_params, **custom_params}
        
        # Initialize image generator if needed
        if params.get("generate_images", True):
            self._initialize_image_generator()
        
        # Generate campaign foundation
        foundation = self.builder.generate("campaign_foundation", theme=theme)
        
        # Create world state
        world = WorldState()
        
        # Generate starting location (always first)
        starting_loc = self._generate_starting_location(theme)
        world.add_location(starting_loc)
        
        # Generate regions with thematic consistency
        regions = self._generate_regions(theme, params, foundation)
        
        # Populate each region
        for region_idx, region_data in enumerate(regions):
            self._populate_region(world, region_data, region_idx, theme, params)
        
        # Generate factions with relationships
        self._generate_factions(world, theme, params, foundation)
        
        # Generate images if enabled
        if params.get("generate_images", True):
            self._generate_world_images(world, theme)
        
        # Generate world map with proper scaling
        world_data = self._finalize_world(world, theme, params)
        
        return world_data

    def save_world(world_data):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Insert world metadata
                cur.execute(
                    "INSERT INTO worlds (theme, seed) VALUES (%s, %s) RETURNING id",
                    (world_data["theme"], world_data["seed"])
                )
                world_id = cur.fetchone()[0]
                
                # Save locations
                for loc in world_data["locations"]:
                    cur.execute(
                        "INSERT INTO locations (world_id, name, type, position, data) "
                        "VALUES (%s, %s, %s, POINT(%s, %s), %s)",
                        (
                            world_id,
                            loc["name"],
                            loc["type"],
                            loc["x"],
                            loc["y"],
                            Json(loc)  # Store entire location as JSONB
                        )
                    )
                
                # Save factions
                for fac in world_data["factions"]:
                    cur.execute(
                        "INSERT INTO factions (world_id, name, ideology, goals, relationships, activities) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            world_id,
                            fac["name"],
                            fac["ideology"],
                            fac["goals"],
                            Json(fac.get("relationships", {})),
                            fac.get("activities", [])
                        )
                    )
                
                # Save quests
                for quest in world_data["quests"]:
                    cur.execute(
                        "INSERT INTO quests (world_id, title, description, objectives, location_id, "
                        "completed, dungeon_required) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                        (
                            world_id,
                            quest["title"],
                            quest["description"],
                            quest["objectives"],
                            quest["location_id"],
                            quest.get("completed", False),
                            quest.get("dungeon_required", False)
                        )
                    )
                
                conn.commit()
                return world_id
        finally:
            Database.return_connection(conn)

    def _initialize_image_generator(self):
        """Initialize the image generation system"""
        if self.t2i is None:
            self.t2i = TextToImage(self.model_path)
            self.image_output_dir.mkdir(exist_ok=True, parents=True)

    def _generate_world_images(self, world, theme):
        """Generate images for all locations in the world"""
        print(f"\nGenerating images for {len(world.locations)} locations...")
        
        image_requests = []
        locations_to_update = []
        
        # Create image requests for all locations
        for location in world.locations.values():
            prompt = self._generate_location_image_prompt(location, theme)
            
            image_requests.append({
                "request_id": f"loc-{location.id}",
                "prompt": prompt,
                "seed": abs(hash(location.id)) % 1000000  # Deterministic seed based on location ID
            })
            locations_to_update.append(location)
        
        # Batch generate all images
        start_time = time.time()
        successes, failures = self.t2i.generate_batch(
            generation_requests=image_requests,
            output_dir=self.image_output_dir
        )
        gen_time = time.time() - start_time
        
        print(f"Image generation completed in {gen_time:.1f} seconds")
        print(f"  Successful: {len(successes)}")
        print(f"  Failed: {len(failures)}")
        
        # Process results and update locations
        for location in locations_to_update:
            request_id = f"loc-{location.id}"
            
            if request_id in successes:
                location.image_url = f"/static/world_images/{request_id}.jpg"
                print(f"  ✓ {location.name}: {location.image_url}")
            else:
                # Find failure details
                failure = next((f for f in failures if f['request_id'] == request_id), None)
                error_msg = failure['exception'] if failure else "Unknown error"
                print(f"  ✗ {location.name}: {error_msg}")
                
                # Create placeholder URL
                name_clean = location.name.replace(' ', '%20')
                location.image_url = f"https://via.placeholder.com/300x200/333/fff?text={name_clean}"
        
        # Save failed requests for retry
        if failures:
            failure_file = Path("failed_generations.json")
            with failure_file.open("w") as f:
                json.dump(failures, f, indent=2)
            print(f"Saved failure details to: {failure_file}")

    def _generate_location_image_prompt(self, location, theme):
        """Create robust prompt for location image generation"""
        # Base description
        prompt = f"{theme} {location.type}: {location.name}"
        
        # Add description details
        if location.description:
            desc = location.description[:200].replace('\n', ' ').strip()
            if desc:
                prompt += f", {desc}"
        
        # Add features if available
        if location.features:
            features = ", ".join(location.features[:3])
            prompt += f", featuring {features}"
        
        # Add quality boosters
        prompt += ", detailed, atmospheric, fantasy art, digital painting"
        
        # Add style modifiers based on theme
        if "dark" in theme:
            prompt += ", dark fantasy, grim, mysterious"
        elif "high" in theme or "epic" in theme:
            prompt += ", epic fantasy, majestic, grand scale"
        else:
            prompt += ", imaginative fantasy landscape"
        
        # Ensure minimum length
        if len(prompt) < 30:
            prompt += ", fantasy landscape environment"
        
        return prompt

    def _generate_starting_location(self, theme):
        """Generate starting location using WorldBuilder"""
        # Use WorldBuilder for the starting location
        tavern_data = self.builder.generate_tavern_start(theme)
        
        # Convert to Location object with proper positioning
        return Location(
            id=tavern_data["id"],
            name=tavern_data["name"],
            type=tavern_data["type"],
            description=tavern_data["description"],
            x=500, y=400,  # Center of the map
            features=tavern_data["features"],
            services=tavern_data["services"],
            dungeon_type=tavern_data["dungeon_type"]
        )

    def _generate_regions(self, theme, params, foundation):
        """Generate thematic regions based on campaign foundation"""
        regions = []
        core_conflict = foundation["core_conflict"].lower()
        
        # Determine region types based on campaign theme
        if "war" in core_conflict:
            region_types = ["borderlands", "war-torn", "fortified", "contested"]
        elif "magic" in core_conflict:
            region_types = ["arcane", "cursed", "enchanted", "ley-line"]
        else:
            region_types = ["wilderness", "civilized", "frontier", "ruined"]
        
        for i in range(params["region_count"]):
            region_type = region_types[i % len(region_types)]
            region = self.builder.generate("region", theme=theme, region_type=region_type)
            regions.append(region)
        
        return regions

    def _populate_region(self, world, region_data, region_idx, theme, params):
        """Populate a region with locations, quests, and NPCs"""
        # Calculate region boundaries for proper spacing
        region_width = 800 // params["region_count"]
        region_x = region_idx * region_width + region_width // 2
        
        # Track existing names to ensure uniqueness
        existing_names = {loc.name for loc in world.locations.values()}
        
        for loc_idx in range(params["locations_per_region"]):
            # Determine location type based on region type
            location_type = self._determine_location_type(region_data, loc_idx)
            
            # Generate location using WorldBuilder with existing names
            location = self._generate_location(
                theme, location_type, region_data, region_x, loc_idx, params, existing_names
            )
            
            world.add_location(location)
            existing_names.add(location.name)  # Add to existing names
            
            # Add quests based on density parameter
            if random.random() < params["quest_density"]:
                self._add_quest_to_location(world, location, theme)
            
            # Add NPCs based on density parameter
            if random.random() < params["npc_density"]:
                self._add_npcs_to_location(world, location, theme)

    def _determine_location_type(self, region_data, loc_idx):
        """Determine appropriate location type based on region"""
        region_type = region_data.get("type", "").lower()
        
        if "wilderness" in region_type:
            return random.choice(["forest", "mountain", "ruin", "cave"])
        elif "civilized" in region_type:
            return random.choice(["town", "village", "farm", "outpost"])
        elif "arcane" in region_type:
            return random.choice(["tower", "sanctum", "library", "observatory"])
        else:
            return random.choice(["village", "forest", "ruin", "outpost"])

    def _generate_location(self, theme, location_type, region_data, region_x, loc_idx, params, existing_names):
        """Generate a location with proper positioning and features"""
        # Use WorldBuilder for location content with existing names
        loc_data = self.builder.generate("location", 
                                       theme=theme, 
                                       location_type=location_type,
                                       region=region_data["name"],
                                       existing_names=", ".join(existing_names))
        
        # Calculate position within region
        region_height = 600 // params["locations_per_region"]
        y_pos = loc_idx * region_height + region_height // 2
        
        # Add dungeon based on probability
        dungeon_type = None
        dungeon_level = None
        if random.random() < params["dungeon_probability"]:
            dungeon_data = self.builder.generate("dungeon_type", 
                                              theme=theme, 
                                              location=loc_data["name"])
            dungeon_type = dungeon_data["type"]
            dungeon_level = random.randint(1, 5)
        
        return Location(
            id=f"loc_{uuid.uuid4().hex[:8]}",
            name=loc_data["name"],
            type=location_type,
            description=loc_data["description"],
            x=region_x + random.randint(-100, 100),  # Some variation within region
            y=y_pos + random.randint(-50, 50),
            dungeon_type=dungeon_type,
            dungeon_level=dungeon_level,
            features=loc_data["features"],
            services=loc_data["services"]
        )

    def _add_quest_to_location(self, world, location, theme):
        """Add a quest to a location"""
        quest_data = self.builder.generate("quest", 
                                        theme=theme, 
                                        location=location.name)
        
        quest = Quest(
            id=f"quest_{uuid.uuid4().hex[:8]}",
            title=quest_data["title"],
            description=quest_data["description"],
            objectives=quest_data["objectives"],
            location_id=location.id,
            dungeon_required=quest_data.get("dungeon_required", False)
        )
        
        world.add_quest(quest)
        location.quests.append(quest.id)

    def _add_npcs_to_location(self, world, location, theme):
        """Add NPCs to a location"""
        npc_count = random.randint(1, 3)  # 1-3 NPCs per location
        
        for _ in range(npc_count):
            try:

                npc_data = self.builder.generate("npc", 
                                               theme=theme, 
                                               location=location.name)

                # Ensure all required fields are present
                if not all(key in npc_data for key in ["name", "role", "motivation"]):
                    print(f"Warning: Incomplete NPC data: {npc_data}")
                    continue
                
                # Create NPC and add to world
                npc = NPC(
                    id=f"npc_{uuid.uuid4().hex[:8]}",
                    name=npc_data["name"],
                    role=npc_data["role"],
                    motivation=npc_data["motivation"]
                )
                
                # Add dialogue if available
                if "dialogue" in npc_data:
                    npc.dialogue = npc_data["dialogue"]
                
                world.add_npc(npc)

            except Exception as e:
                print(f"Error creating NPC: {e}")
                continue

    def _generate_factions(self, world, theme, params, foundation):
        """Generate factions with relationships based on campaign"""
        core_conflict = foundation["core_conflict"]
        major_factions = foundation.get("major_factions", [])
        
        # Determine faction relationships based on conflict
        relationships = self._determine_faction_relationships(core_conflict)
        
        for i in range(params["faction_count"]):
            # Use existing faction names from foundation or generate new ones
            faction_name = major_factions[i] if i < len(major_factions) else self.name_gen.generate_name("faction", theme)
            
            faction_data = self.builder.generate("faction", 
                                              theme=theme, 
                                              faction_name=faction_name)
            
            faction = Faction(
                id=f"fac_{uuid.uuid4().hex[:8]}",
                name=faction_data["name"],
                ideology=faction_data["ideology"],
                goals=faction_data["goals"]
            )
            
            # Add relationships
            faction.relationships = relationships.get(faction.name, {})
            faction.activities = faction_data.get("activities", [])
            
            world.add_faction(faction)

    def _determine_faction_relationships(self, core_conflict):
        """Determine faction relationships based on campaign conflict"""
        relationships = {}
        
        if "war" in core_conflict.lower():
            relationships = {
                "Order of the Sun": {"Shadow Collective": "enemy", "Merchant Guild": "neutral"},
                "Shadow Collective": {"Order of the Sun": "enemy", "Merchant Guild": "ally"},
                "Merchant Guild": {"Order of the Sun": "neutral", "Shadow Collective": "ally"}
            }
        elif "magic" in core_conflict.lower():
            relationships = {
                "Arcane Collegium": {"Druidic Circle": "rival", "Church of Light": "enemy"},
                "Druidic Circle": {"Arcane Collegium": "rival", "Church of Light": "neutral"},
                "Church of Light": {"Arcane Collegium": "enemy", "Druidic Circle": "neutral"}
            }
        
        return relationships

    def _finalize_world(self, world, theme, params):
        """Finalize world data without terrain and paths - those are handled by WorldController"""
        # Create the final world data structure
        world_data = {
            "theme": theme,
            "seed": self.seed,
            "params": params,
            "starting_location_id": "starting_tavern",
            "locations": [loc.to_dict() for loc in world.locations.values()],
            "quests": [q.to_dict() for q in world.quests.values()],
            "factions": [fac.to_dict() for fac in world.factions.values()],
            "npcs": [npc.to_dict() for npc in world.npcs.values()]
            # terrain_grid and paths are handled by WorldController
        }
        
        return world_data


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



if __name__ == "__main__":
    world_data = generate(self, theme="dark_fantasy", region_count=2)
    with open("dark_fantasy_world.json", "w") as f:
        json.dump(world_data, f, indent=2)
    print(f"World generation complete! Saved to dark_fantasy_world.json")