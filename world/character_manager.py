"""
Character Management System - handles character creation, loading, and updates
Phase: State Mutation (character state changes)
"""
from typing import Dict, List, Optional, Any
from world.character import Character
from world.db import Database
import json

class CharacterManager:
    """Manages character state and operations"""

    def __init__(self, character_builder):
        self.characters: Dict[str, Character] = {}
        self.character_builder = character_builder
        # We need a reference to world_controller to access players
        self.world_controller = None   # Will be set later by world_controller

    def set_world_controller(self, world_controller):
        self.world_controller = world_controller

    def create_character(self, player_id: str, char_data: Dict[str, Any]) -> Character:
        """Create a new character and save to database"""
        character = self.character_builder.create_character(player_id, char_data)
        self.characters[character.id] = character
        self._save_character_to_db(character)
        return character

    def add_character(self, character):
        """Add a character to the in‑memory cache and persist to database."""
        self.characters[character.id] = character
        self._save_character_to_db(character)

    def assign_character_to_player(self, player_id: str, character_id: str):
        """Assign a character to a player and persist the relationship."""
        character = self.get_character(character_id)
        if not character:
            raise ValueError(f"Character {character_id} not found")

        player = self.world_controller.players.get(player_id) if self.world_controller else None
        if not player:
            raise ValueError(f"Player {player_id} not found")

        # Ensure character has player_id set
        character.player_id = player_id

        # Update player's character list (avoid duplicates)
        if character_id not in player.character_ids:
            player.character_ids.append(character_id)

        # Set as active if none
        if not player.active_character_id:
            player.set_active_character(character_id)

        # Save both to database
        if self.world_controller:
            self.world_controller._save_player_to_db(player)

        self._save_character_to_db(character)

    def _load_character_from_db(self, character_id):
        """Load a character from the database and cache it."""
        from world.db import Database
        import json
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, player_id, name, race, class, level, attributes, inventory, avatar_url,
                           backstory, connections, secrets, vows
                    FROM characters WHERE id = %s
                """, (character_id,))
                row = cur.fetchone()
                if not row:
                    return None
                
                # Convert JSON fields
                attributes = row[6] if row[6] else {}
                inventory = row[7] if row[7] else []
                backstory = row[9] if row[9] else {}
                connections = row[10] if row[10] else []
                secrets = row[11] if row[11] else []
                vows = row[12] if row[12] else {}
                
                # Create a basic character object – you'll need to adjust to match your __init__
                # This assumes you have a way to create a character from minimal data
                from world.character import Character
                char = Character(
                    name=row[2],
                    race=row[3],
                    classs=row[4],      # class name (string)
                    level=row[5],
                    player_id=row[1],
                    # Pass the already-parsed dicts
                    backstory=backstory,
                    connections=connections,
                    secrets=secrets,
                    vows=vows
                )
                # Override auto‑generated ID
                char.id = row[0]
                # Set other fields from JSON
                char.attributes = attributes
                char.inventory = inventory
                # Set avatar_url if present
                if row[8]:
                    char.avatar_url = row[8]
                # If there are other fields like hp, sp, they should be in attributes or recomputed
                # For now, assume they are in attributes or you'll recompute later
                
                # Cache it
                self.characters[char.id] = char
                return char
        finally:
            Database.return_connection(conn)

    def load_characters_for_player(self, player_id: str) -> List[Character]:
        """Load all characters for a player from database"""
        conn = Database.get_connection()
        loaded_characters = []
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, name, race, class, level, attributes, inventory, avatar_url "
                    "FROM characters WHERE player_id = %s",
                    (player_id,)
                )
                for row in cur.fetchall():
                    character = Character(
                        owner_id=player_id,
                        name=row[1],
                        race=row[2],
                        classs=row[3],
                        level=row[4]
                    )
                    character.id = row[0]
                    character.attributes = row[5] or {}
                    if row[6]:
                        for item_data in row[6]:
                            character.add_custom_item(item_data['name'], item_data.get('description', ''))
                    character.avatar_url = row[7]
                    self.characters[character.id] = character
                    loaded_characters.append(character)
        except Exception as e:
            print(f"Error loading characters from DB: {e}")
        finally:
            Database.return_connection(conn)
        return loaded_characters

    def update_character_avatar(self, char_id: str, avatar_url: str) -> bool:
        if char_id in self.characters:
            self.characters[char_id].avatar_url = avatar_url
            return True
        return False

    def get_character(self, character_id):
        """Return character from cache or load from database."""
        # Check cache first
        if character_id in self.characters:
            return self.characters[character_id]
        
        # Not in cache, try to load from database
        return self._load_character_from_db(character_id)

    def get_player_characters(self, player_id: str) -> List[Character]:
        return [char for char in self.characters.values() if char.owner_id == player_id]

    def delete_character(self, char_id: str) -> bool:
        if char_id in self.characters:
            del self.characters[char_id]
            return True
        return False

    def _save_character_to_db(self, character):
        """Save character to database."""
        from world.db import Database
        import json
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                # Get class name safely
                if hasattr(character, 'classs'):
                    if hasattr(character.classs, 'name'):
                        class_name = character.classs.name
                    else:
                        class_name = str(character.classs)
                else:
                    class_name = ''

                # Prepare data with fallbacks
                attributes = json.dumps(getattr(character, 'attributes', {}))
                inventory_list = getattr(character, 'inventory', [])
                inventory_dicts = []
                for item in inventory_list:
                    if hasattr(item, 'to_dict'):
                        inventory_dicts.append(item.to_dict())
                    elif isinstance(item, dict):
                        inventory_dicts.append(item)
                    else:
                        # fallback: try to convert using vars or just str
                        inventory_dicts.append(vars(item) if hasattr(item, '__dict__') else str(item))
                inventory = json.dumps(inventory_dicts)
                backstory = json.dumps(getattr(character, 'backstory', {}))
                connections = json.dumps(getattr(character, 'connections', []))
                secrets = json.dumps(getattr(character, 'secrets', []))
                vows = json.dumps(getattr(character, 'vows', {}))
                avatar_url = getattr(character, 'avatar_url', None)

                cur.execute("""
                    INSERT INTO characters (id, player_id, name, race, class, level, attributes, inventory, avatar_url, backstory, connections, secrets, vows)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        player_id = EXCLUDED.player_id,
                        name = EXCLUDED.name,
                        race = EXCLUDED.race,
                        class = EXCLUDED.class,
                        level = EXCLUDED.level,
                        attributes = EXCLUDED.attributes,
                        inventory = EXCLUDED.inventory,
                        avatar_url = EXCLUDED.avatar_url,
                        backstory = EXCLUDED.backstory,
                        connections = EXCLUDED.connections,
                        secrets = EXCLUDED.secrets,
                        vows = EXCLUDED.vows
                """, (
                    character.id,
                    character.player_id,
                    character.name,
                    character.race,
                    class_name,
                    character.level,
                    attributes,
                    inventory,
                    avatar_url,
                    backstory,
                    connections,
                    secrets,
                    vows
                ))
                conn.commit()
        finally:
            Database.return_connection(conn)

    def update_character_position(self, char_id: str, position: Dict[str, float]) -> bool:
        if char_id in self.characters:
            self.characters[char_id].position = position
            return True
        return False