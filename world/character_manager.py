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
            player.active_character_id = character_id
        
        # Save both to database
        if self.world_controller:
            self.world_controller._save_player_to_db(player)
        
        self._save_character_to_db(character)
        
        # Update cache
        if self.world_controller:
            self.world_controller.characters[character_id] = character

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

    def get_character(self, char_id: str) -> Optional[Character]:
        return self.characters.get(char_id)

    def get_player_characters(self, player_id: str) -> List[Character]:
        return [char for char in self.characters.values() if char.owner_id == player_id]

    def delete_character(self, char_id: str) -> bool:
        if char_id in self.characters:
            del self.characters[char_id]
            return True
        return False

    def _save_character_to_db(self, character: Character):
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO characters (id, player_id, name, race, class, level, attributes, inventory, avatar_url) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (id) DO UPDATE SET "
                    "name = EXCLUDED.name, race = EXCLUDED.race, class = EXCLUDED.class, "
                    "level = EXCLUDED.level, attributes = EXCLUDED.attributes, "
                    "inventory = EXCLUDED.inventory, avatar_url = EXCLUDED.avatar_url, "
                    "updated_at = CURRENT_TIMESTAMP",
                    (
                        character.id, character.owner_id, character.name,
                        character.race, character.classs.name if hasattr(character, 'classs') else None,
                        character.level, json.dumps(character.attributes),
                        json.dumps([item.to_dict() for item in character.get_full_inventory()]),
                        character.avatar_url
                    )
                )
                conn.commit()
        except Exception as e:
            print(f"Error saving character to DB: {e}")
            conn.rollback()
        finally:
            Database.return_connection(conn)

    def update_character_position(self, char_id: str, position: Dict[str, float]) -> bool:
        if char_id in self.characters:
            self.characters[char_id].position = position
            return True
        return False