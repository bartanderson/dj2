# world/persistence.py
import json
from world.world_generator import WorldGenerator
from world.db import Database  # Your DB connection module
from world.world_builder import WorldBuilder

class WorldManager:
    def __init__(self, ai_system):
        self.ai = ai_system
        self.generator = WorldGenerator(ai_system)
        self.builder = WorldBuilder(ai_system)  # Add WorldBuilder

    def get_existing_worlds(self):
        """Get list of all existing worlds - fixed implementation"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, theme, created_at FROM worlds ORDER BY created_at DESC")
                rows = cur.fetchall()
                
                # Convert to list of dictionaries
                worlds = []
                for row in rows:
                    worlds.append({
                        "id": row[0],
                        "theme": row[1],
                        "created_at": row[2]
                    })
                
                return worlds
        except Exception as e:
            print(f"Error fetching existing worlds: {e}")
            return []  # Return empty list on error
        finally:
            Database.return_connection(conn)


    def get_default_world_id(self) -> str:
        """Get or create a default world ID"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Check for existing worlds
                cur.execute("SELECT id FROM worlds LIMIT 1")
                if row := cur.fetchone():
                    return row[0]  # Return first world ID found
                
                # Create new world if none exists
                return self.create_new_world()
        finally:
            Database.return_connection(conn)

    def create_new_world(self, theme="dark_fantasy", **kwargs):
        """Generate and persist a new world with customizable parameters"""
        # Reconfigure generator with provided parameters
        if 'seed' in kwargs:
            self.generator.seed = kwargs['seed']
        
        # Set up image generation if specified
        if 'generate_images' in kwargs and kwargs['generate_images']:
            if 'model_path' in kwargs:
                self.generator.model_path = kwargs['model_path']
            if 'image_output_dir' in kwargs:
                self.generator.image_output_dir = kwargs['image_output_dir']
        
        # Generate the world data with all provided parameters
        world_data = self.generator.generate(theme, **kwargs)

        # Ensure the seed is included in the world data
        world_data["seed"] = self.generator.seed

        # Save to database
        world_id = self.save_to_db(world_data)
        return world_id
    
    def save_to_db(self, world_data):
        """Save world to PostgreSQL"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Insert world metadata
                cur.execute(
                    "INSERT INTO worlds (theme, seed) VALUES (%s, %s) RETURNING id",
                    (world_data["theme"], world_data.get("seed", 42))
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
                            Json(quest["objectives"]),
                            quest["location_id"],
                            quest.get("completed", False),
                            quest.get("dungeon_required", False)
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
                            Json(fac.get("goals", [])),
                            Json(fac.get("relationships", {})),
                            Json(fac.get("activities", []))
                        )
                    )
                
                # Save NPCs
                for npc in world_data["npcs"]:
                    cur.execute(
                        "INSERT INTO npcs (world_id, name, role, motivation, dialogue, location_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            world_id,
                            npc["name"],
                            npc["role"],
                            npc["motivation"],
                            Json(npc.get("dialogue", [])),
                            npc.get("location_id")
                        )
                    )
                
                conn.commit()
                return world_id
        finally:
            Database.return_connection(conn)
    
    def load_from_db(self, world_id):
        """Load complete world data from database"""
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Load world metadata
                cur.execute("SELECT id, theme, seed FROM worlds WHERE id = %s", (world_id,))
                world_row = cur.fetchone()
                if not world_row:
                    raise ValueError(f"World {world_id} not found")
                
                world_data = {
                    "id": world_row[0],
                    "theme": world_row[1],
                    "seed": world_row[2],
                    "locations": [],
                    "quests": [],
                    "factions": [],
                    "npcs": []
                }
                
                # Load locations
                cur.execute("""
                    SELECT id, name, type, position[0] AS x, position[1] AS y, 
                           data->>'description' AS description,
                           data->>'dungeon_type' AS dungeon_type,
                           (data->>'dungeon_level')::int AS dungeon_level,
                           data->>'image_url' AS image_url,
                           data->'features' AS features,
                           data->'services' AS services,
                           discovered
                    FROM locations 
                    WHERE world_id = %s
                """, (world_id,))
                
                for row in cur.fetchall():
                    world_data["locations"].append({
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "x": row[3],
                        "y": row[4],
                        "description": row[5],
                        "dungeon_type": row[6],
                        "dungeon_level": row[7],
                        "image_url": row[8],
                        "features": row[9],
                        "services": row[10],
                        "discovered": row[11]
                    })
                
                # Load quests
                cur.execute("""
                    SELECT id, title, description, objectives, 
                           location_id, completed, dungeon_required
                    FROM quests 
                    WHERE world_id = %s
                """, (world_id,))
                
                for row in cur.fetchall():
                    world_data["quests"].append({
                        "id": row[0],
                        "title": row[1],
                        "description": row[2],
                        "objectives": row[3],
                        "location_id": row[4],
                        "completed": row[5],
                        "dungeon_required": row[6]
                    })
                
                # Load factions
                cur.execute("""
                    SELECT id, name, ideology, goals, relationships, activities
                    FROM factions 
                    WHERE world_id = %s
                """, (world_id,))
                
                for row in cur.fetchall():
                    world_data["factions"].append({
                        "id": row[0],
                        "name": row[1],
                        "ideology": row[2],
                        "goals": row[3],
                        "relationships": row[4],
                        "activities": row[5]
                    })
                
                # Load NPCs
                cur.execute("""
                    SELECT id, name, role, motivation, dialogue, location_id
                    FROM npcs 
                    WHERE world_id = %s
                """, (world_id,))
                
                for row in cur.fetchall():
                    world_data["npcs"].append({
                        "id": row[0],
                        "name": row[1],
                        "role": row[2],
                        "motivation": row[3],
                        "dialogue": row[4],
                        "location_id": row[5]
                    })
                
                return world_data
        finally:
            Database.return_connection(conn)
