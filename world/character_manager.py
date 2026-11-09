# world/character_manager.py
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

    def create_character(self, player_id: str, char_data: dict) -> Character:
        character = self.character_builder._create_character_impl(player_id, char_data)
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
        from world.db import Database
        from world.character import Character, ABILITIES

        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, player_id, name, race, class, level, attributes,
                              inventory, avatar_url, backstory, connections, secrets, vows
                       FROM characters WHERE id = %s""",
                    (character_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                attr_blob = row[6] or {}
                if isinstance(attr_blob, dict) and "abilities" in attr_blob:
                    abilities = attr_blob["abilities"]
                    saves = attr_blob.get("save_proficiencies", [])
                    skills = attr_blob.get("skill_proficiencies", [])
                    expertise = attr_blob.get("skill_expertise", [])
                    saved_hp = attr_blob.get("hp")
                    saved_sp = attr_blob.get("sp")

                char = Character(
                    name=row[2], race=row[3], classs=row[4], level=row[5],
                    player_id=row[1], owner_id=row[1],
                    abilities=abilities,
                    save_proficiencies=saves,
                    skill_proficiencies=skills,
                    skill_expertise=expertise,
                    backstory=row[9] or {},
                    connections=row[10] or [],
                    secrets=row[11] or [],
                    vows=row[12] or {},
                    add_starting_gear=False,
                )
                char.id = row[0]
                char.avatar_url = row[8] or "/static/images/default_avatar.png"
                if saved_hp is not None:
                    char.hp = saved_hp
                if saved_sp is not None:
                    char.sp = saved_sp

                char.inventory = []
                for item_data in (row[7] or []):
                    try:
                        char.inventory.append(char.normalize_inventory_item(item_data))
                    except (TypeError, ValueError):
                        pass

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
                    "SELECT id, name, race, class, level, attributes, inventory, avatar_url, backstory, connections, secrets, vows "
                    "FROM characters WHERE player_id = %s",
                    (player_id,)
                )
                for row in cur.fetchall():
                    attr_blob = row[5] or {}
                    # Same shim as _load_character_from_db: prefer the nested
                    # 'abilities' key (post-migration schema). If the blob
                    # predates the migration, fall back to Character defaults.
                    if isinstance(attr_blob, dict) and "abilities" in attr_blob:
                        abilities = attr_blob["abilities"]
                    else:
                        abilities = None  # Character() fills in defaults

                    character = Character(
                        owner_id=player_id,
                        name=row[1],
                        race=row[2],
                        classs=row[3],
                        level=row[4],
                        abilities=abilities,
                    )
                    character.id = row[0]

                    # Restore persisted hp/sp if present (mirrors what
                    # _save_character_to_db writes into the blob).
                    if isinstance(attr_blob, dict):
                        for key in ("hp", "max_hp", "sp", "max_sp"):
                            if key in attr_blob and hasattr(character, key):
                                try:
                                    setattr(character, key, attr_blob[key])
                                except Exception:
                                    pass

                    if row[6]:
                        for item_data in row[6]:
                            character.add_custom_item(item_data['name'], item_data.get('description', ''))
                    character.avatar_url = row[7]
                    # Load narrative fields
                    character.backstory = row[8] or {}
                    character.connections = row[9] or []
                    character.secrets = row[10] or []
                    character.vows = row[11] or {}
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
        from world.db import Database
        import json

        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                class_name = (
                    character.classs.name
                    if hasattr(character.classs, "name")
                    else str(character.classs)
                )

                # Serialise abilities + proficiency state + current hp/sp into `attributes`.
                attr_payload = {
                    "abilities": character.abilities,
                    "save_proficiencies": character.save_proficiencies,
                    "skill_proficiencies": character.skill_proficiencies,
                    "skill_expertise": character.skill_expertise,
                    "hp": character.hp,
                    "sp": character.sp,
                }

                def _ser_item(i):
                    if hasattr(i, "__dict__"):
                        return {k: v for k, v in vars(i).items() if not k.startswith("_")}
                    return i

                inventory = json.dumps([_ser_item(i) for i in character.inventory])
                backstory = json.dumps(getattr(character, "backstory", {}))
                connections = json.dumps(getattr(character, "connections", []))
                secrets = json.dumps(getattr(character, "secrets", []))
                vows = json.dumps(getattr(character, "vows", {}))

                cur.execute(
                    """INSERT INTO characters
                           (id, player_id, name, race, class, level, attributes,
                            inventory, avatar_url, backstory, connections, secrets, vows)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                           vows = EXCLUDED.vows""",
                    (
                        character.id,
                        character.player_id,
                        character.name,
                        character.race,
                        class_name,
                        character.level,
                        json.dumps(attr_payload),
                        inventory,
                        getattr(character, "avatar_url", None),
                        backstory,
                        connections,
                        secrets,
                        vows,
                    ),
                )
                conn.commit()
        finally:
            Database.return_connection(conn)

    def update_character_position(self, char_id: str, position: Dict[str, float]) -> bool:
        if char_id in self.characters:
            self.characters[char_id].position = position
            return True
        return False