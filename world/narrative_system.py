# world/narrative_system.py
"""
Narrative System – handles backstory, connections, revelations, and pacing.
Uses OG System data for all mechanical references.
"""
import uuid
import random
from typing import Dict, List, Optional, Any

from world import dnd_data
from world.ai_dungeon_master import AIDungeonMaster, Dialog, GameState
from world.character import Character
from world.player import Player


class NarrativeGuide:
    """Provides gentle narrative nudges based on player behavior."""
    def __init__(self):
        self.fallback_hooks = [
            "A mysterious stranger approaches you with urgent news",
            "You overhear a conversation about strange occurrences nearby",
            "A sudden environmental change demands attention"
        ]

    def get_gentle_nudge(self, player_actions):
        if player_actions.get('distracted', False):
            return "As you investigate the side path, you discover evidence connecting it to the main quest"
        if player_actions.get('off_track', False):
            return "Your exploration leads you back to the main path, where new developments await"
        return None

    def emergency_nudge(self):
        hook = random.choice(self.fallback_hooks)
        return f"Suddenly, {hook} – demanding your immediate attention"


class ConsequenceSystem:
    """Tracks player actions and applies delayed consequences."""
    def __init__(self, world_state):
        self.world = world_state
        self.action_registry = []

    def log_action(self, action, significance):
        self.action_registry.append({
            "action": action,
            "significance": significance,
            "resolved": False
        })

    def apply_delayed_consequences(self):
        unresolved = [a for a in self.action_registry if not a['resolved']]
        for action in unresolved:
            if random.random() < 0.3:  # 30% chance
                consequence = self._generate_consequence(action)
                if hasattr(self.world, 'add_event'):
                    self.world.add_event(consequence)
                action['resolved'] = True

    def _generate_consequence(self, action):
        # Placeholder – expand with actual consequence logic
        return f"Your past action '{action['action']}' has unexpected consequences."


class MotivationTracker:
    """Analyzes player actions to infer motivations."""
    def analyze_action(self, action, character):
        action_lower = action.lower()
        if any(word in action_lower for word in ["explore", "look", "search"]):
            return "curiosity"
        if any(word in action_lower for word in ["fight", "attack", "kill"]):
            return "combat"
        if any(word in action_lower for word in ["take", "loot", "steal"]):
            return "acquisition"
        if any(word in action_lower for word in ["talk", "speak", "ask"]):
            return "social"
        return "unknown"

    def get_narrative_leverage(self, motivation):
        leverage_map = {
            "curiosity": "You notice something strange that begs investigation",
            "combat": "Dangerous foes appear, blocking your path forward",
            "acquisition": "A glint of treasure catches your eye nearby",
            "social": "An NPC approaches with potentially valuable information"
        }
        return leverage_map.get(motivation, "New developments unfold around you")


class PacingController:
    """Manages narrative tension and pacing."""
    def __init__(self):
        self.current_phase = 'exploration'  # exploration, downtime, tension, climax
        self.phase_progress = 0  # 0-100
        self.player_actions = 0

    def handle_player_action(self, action_type: str):
        self.player_actions += 1
        if action_type in ['combat', 'discovery']:
            self._increase_tension(10)
        elif action_type in ['rest', 'dialogue']:
            self._decrease_tension(5)

    def handle_discovery_event(self):
        self._increase_tension(15)

    def handle_dungeon_completion(self, success: bool):
        if success:
            self.current_phase = 'downtime'
            self.phase_progress = 0
        else:
            self._increase_tension(25)

    def _increase_tension(self, amount: int):
        self.phase_progress = min(100, self.phase_progress + amount)
        if self.phase_progress >= 75 and self.current_phase != 'climax':
            self.current_phase = 'climax'
        elif self.phase_progress >= 50 and self.current_phase not in ['tension', 'climax']:
            self.current_phase = 'tension'

    def _decrease_tension(self, amount: int):
        self.phase_progress = max(0, self.phase_progress - amount)
        if self.phase_progress < 25 and self.current_phase != 'exploration':
            self.current_phase = 'exploration'
        elif self.phase_progress < 50 and self.current_phase == 'tension':
            self.current_phase = 'exploration'

    def get_pacing_recommendation(self) -> str:
        if self.current_phase == 'exploration':
            return "Introduce new locations or NPCs"
        if self.current_phase == 'downtime':
            return "Provide roleplaying opportunities"
        if self.current_phase == 'tension':
            return "Hint at upcoming dangers"
        if self.current_phase == 'climax':
            return "Trigger major story event or boss battle"
        return "Maintain current pacing"

    def get_status(self) -> dict:
        return {
            "phase": self.current_phase,
            "progress": self.phase_progress,
            "actions": self.player_actions,
            "recommendation": self.get_pacing_recommendation()
        }


class NarrativeSystem:
    """
    Main narrative coordinator. Handles character creation guidance,
    backstory development, connection webs, revelations, and pacing.
    """

    def __init__(self, world_state, ai_system, dm_chat_ai=None):
        self.world = world_state
        self.ai = ai_system

        # Load narrative framework from OG System JSON
        self.narrative_framework = getattr(world_state, 'narrative_framework', {})

        # Initialize sub‑systems
        self.guide = NarrativeGuide()
        self.consequences = ConsequenceSystem(world_state)
        self.motivation = MotivationTracker()
        self.pacing = PacingController()

        # DM system (optional)
        if ai_system:
            self.dm = AIDungeonMaster(dm_chat_ai=dm_chat_ai)
            self.game_state = GameState()
        else:
            self.dm = None
            self.game_state = None

        # Active backstory creation sessions (character_id -> state)
        self.backstory_sessions = {}

    def on_location_discovered(self, location_id: str):
        """Handle location discovery: update pacing and trigger narrative hooks."""
        # Update pacing
        self.pacing.handle_discovery_event()

        # Get the location from world map
        location = self.world.world_map.get_location(location_id)
        if not location:
            return

        # If this is the first discovery, you might want to generate a quest or log it
        if not location.discovered:
            # Mark as discovered (though world_controller already does this)
            location.discovered = True

            # Optional: generate a quest for this location (will be implemented later)
            # For now, just log it
            if hasattr(self, 'session_log'):
                self.session_log.append(f"Discovered {location.name}")

            # Future: self.generate_quest(location_id, "First discovery")

    # ----------------------------------------------------------------------
    # Character Creation Guidance (OG System)
    # ----------------------------------------------------------------------
    def guide_character_creation(self, player_id, message, creation_state):
        """
        Fully guided character creation using OG System data.
        Returns responses and updated state.
        """
        # Initialize state if needed
        if not creation_state:
            creation_state = {
                'phase': 'welcome',
                'attributes': {},           # e.g., {"brawn": 2, "finesse": 1, ...}
                'race': None,
                'class': None,
                'background': None,
                'skills': [],                # list of chosen skill names
                'personality': None,
                'ideals': None,
                'bonds': None,
                'flaws': None,
                'conversation': []
            }

        if message:
            creation_state['conversation'].append(("player", message))

        responses = []
        phase = creation_state['phase']

        # Helper to load data
        def get_race_guide(race_name):
            race = dnd_data.Race.get(race_name)
            if not race:
                return None
            return {
                "description": f"{race.name}: {race.tags}",
                "traits": race.mechanical_bonus,
                "knacks": race.knacks,
                "questions": [
                    f"What drove your {race.name} to adventure?",
                    f"How do you embody your people's {race.tags}?"
                ]
            }

        def get_class_guide(class_name):
            cls = dnd_data.OGClass.get(class_name)
            if not cls:
                return None
            return {
                "description": cls.core_mechanic.get("description", f"A {cls.name}."),
                "abilities": f"HP per level: {cls.hp_per_level}, SP per level: {cls.sp_per_level}",
                "playstyle": cls.core_mechanic.get("playstyle", "Versatile."),
                "archetypes": list(cls.subclasses.keys())
            }

        def get_background_guide(bg_name):
            # OG System doesn't define backgrounds; we can keep a minimal set or load from elsewhere
            # For now, use a simple fallback.
            guides = {
                "acolyte": {"description": "Devoted to a faith.", "skills": ["Lore", "Social"]},
                "criminal": {"description": "Lived outside the law.", "skills": ["Stealth", "Social"]},
                "folk hero": {"description": "Champion of the common people.", "skills": ["Athletics", "Survival"]},
                "sage": {"description": "Scholar of forgotten lore.", "skills": ["Lore", "Craft"]},
                "soldier": {"description": "Trained for war.", "skills": ["Athletics", "Survival"]}
            }
            return guides.get(bg_name.lower(), {"description": bg_name, "skills": []})

        # --- Phase handling ---
        if phase == 'welcome':
            responses.append(Dialog(
                "DM",
                "Welcome to OG System character creation! I'll guide you through the steps.\n"
                "First, how would you like to determine your attributes? Options:\n"
                "- Point Buy: 4 points to spend (max 3 in any attribute)\n"
                "- Standard Array: 3,2,1,0 (assign to Brawn, Finesse, Wits, Will)\n"
                "- Manual: Roll 2d6 and assign (you can roll now)",
                "narration"
            ))
            creation_state['phase'] = 'attribute_method'

        elif phase == 'attribute_method':
            # Simplified: just accept choice and move to attribute assignment
            # In full implementation, you'd branch on method.
            creation_state['phase'] = 'attribute_assignment'
            responses.append(Dialog(
                "DM",
                "Let's use point buy. You have 4 points. Attributes are Brawn, Finesse, Wits, Will. "
                "Max 3 in any. How do you spend them? (e.g., 'brawn 2, finesse 1, wits 1, will 0')",
                "narration"
            ))

        elif phase == 'attribute_assignment':
            # Parse the player's input to assign points
            # This is a simplified parser – you'd want a more robust one.
            attrs = {"brawn": 0, "finesse": 0, "wits": 0, "will": 0}
            points_spent = 0
            # Very crude parsing – assume message like "brawn 2, finesse 1, wits 1, will 0"
            import re
            parts = message.lower().split(',')
            for part in parts:
                m = re.search(r'(brawn|finesse|wits|will)\s*(\d+)', part)
                if m:
                    attr, val = m.groups()
                    val = int(val)
                    if val < 0 or val > 3:
                        responses.append(Dialog("DM", f"{attr} must be 0-3.", "error"))
                        break
                    attrs[attr] = val
                    points_spent += val
            if points_spent != 4:
                responses.append(Dialog("DM", "You must spend exactly 4 points. Try again.", "error"))
            else:
                creation_state['attributes'] = attrs
                creation_state['phase'] = 'race_selection'
                responses.append(Dialog(
                    "DM",
                    f"Attributes set: {attrs}. Now choose your race. Available races:\n" +
                    ", ".join(dnd_data.get_race_list()),
                    "narration"
                ))

        elif phase == 'race_selection':
            if not message:
                responses.append(Dialog(
                    "DM",
                    f"Races: {', '.join(dnd_data.get_race_list())}. Which one calls to you?",
                    "narration"
                ))
            else:
                race = dnd_data.Race.get(message)
                if not race:
                    responses.append(Dialog("DM", f"'{message}' is not a valid race. Try again.", "error"))
                else:
                    creation_state['race'] = race.name
                    # Apply racial attribute bonus if any
                    for attr, bonus in race.mechanical_bonus.items():
                        if attr in creation_state['attributes']:
                            creation_state['attributes'][attr] += bonus
                    responses.append(Dialog(
                        "DM",
                        f"{race.name}: {race.tags}. Knacks: {', '.join(race.knacks)}. "
                        f"Your attributes adjusted accordingly. Now choose your class.",
                        "narration"
                    ))
                    creation_state['phase'] = 'class_selection'

        elif phase == 'class_selection':
            if not message:
                responses.append(Dialog(
                    "DM",
                    f"Classes: {', '.join(dnd_data.get_class_list())}. Which profession?",
                    "narration"
                ))
            else:
                cls = dnd_data.OGClass.get(message)
                if not cls:
                    responses.append(Dialog("DM", f"'{message}' is not a valid class.", "error"))
                else:
                    creation_state['class'] = cls.name
                    responses.append(Dialog(
                        "DM",
                        f"{cls.name}: {cls.core_mechanic.get('description', '')}\n"
                        f"HP per level: {cls.hp_per_level}, SP per level: {cls.sp_per_level}\n"
                        f"Subclasses: {', '.join(cls.subclasses.keys())}\n"
                        f"Now choose your background.",
                        "narration"
                    ))
                    creation_state['phase'] = 'background_selection'

        elif phase == 'background_selection':
            if not message:
                responses.append(Dialog(
                    "DM",
                    "Backgrounds: Acolyte, Criminal, Folk Hero, Sage, Soldier. Which fits your past?",
                    "narration"
                ))
            else:
                bg = get_background_guide(message)
                if not bg:
                    responses.append(Dialog("DM", f"'{message}' not recognized. Choose from: Acolyte, Criminal, Folk Hero, Sage, Soldier.", "error"))
                else:
                    creation_state['background'] = message
                    responses.append(Dialog(
                        "DM",
                        f"{message}: {bg['description']}. You gain proficiency in {', '.join(bg['skills'])}.\n"
                        f"Now select 3 skills to be proficient in. Available: " +
                        ", ".join([s.name for s in dnd_data.Skill.all()]),
                        "narration"
                    ))
                    creation_state['phase'] = 'skill_selection'

        elif phase == 'skill_selection':
            # Player should list 3 skills
            if not message:
                responses.append(Dialog("DM", "Please list 3 skills (e.g., 'Survival, Lore, Stealth').", "narration"))
            else:
                chosen = [s.strip() for s in message.split(',')]
                valid_skills = [s.name for s in dnd_data.Skill.all()]
                if len(chosen) != 3 or not all(s in valid_skills for s in chosen):
                    responses.append(Dialog("DM", "Please choose exactly 3 valid skills.", "error"))
                else:
                    creation_state['skills'] = chosen
                    creation_state['phase'] = 'personality_development'
                    responses.append(Dialog(
                        "DM",
                        f"Skills chosen: {', '.join(chosen)}. Now let's develop your personality.\n"
                        "How would you describe your character's personality? (e.g., brave, cunning, stoic)",
                        "narration"
                    ))

        elif phase == 'personality_development':
            # Simple sequential prompts for personality, ideals, bonds, flaws
            if not creation_state.get('personality'):
                creation_state['personality'] = message
                responses.append(Dialog("DM", "What ideals drive your character? (e.g., justice, freedom)", "narration"))
            elif not creation_state.get('ideals'):
                creation_state['ideals'] = message
                responses.append(Dialog("DM", "What bonds connect your character to the world? (e.g., family, oath)", "narration"))
            elif not creation_state.get('bonds'):
                creation_state['bonds'] = message
                responses.append(Dialog("DM", "What flaws or weaknesses does your character have? (e.g., pride, fear)", "narration"))
            elif not creation_state.get('flaws'):
                creation_state['flaws'] = message
                creation_state['phase'] = 'finalization'
                # fall through to finalization

        if phase == 'finalization' or (phase == 'personality_development' and creation_state.get('flaws')):
            # Build character
            char_data = {
                'race': creation_state['race'],
                'class': creation_state['class'],
                'background': creation_state['background'],
                'attributes': creation_state['attributes'],
                'skills': creation_state['skills'],
                'personality': creation_state['personality'],
                'ideals': creation_state['ideals'],
                'bonds': creation_state['bonds'],
                'flaws': creation_state['flaws']
            }
            # Use helper to compute derived stats (HP, SP, etc.)
            character = self._finalize_character(char_data)
            responses.append(Dialog(
                "DM",
                f"Behold {character.name}, the {character.race} {character.char_class}!\n"
                f"Your journey begins now.",
                "narration"
            ))
            # Optionally trigger backstory creation next
            creation_state = None   # reset

        # Add player message to history if exists
        if message:
            responses.insert(0, Dialog("Player", message, "character"))

        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state
        }

    def _finalize_character(self, char_data):
        """
        Create a Character object from collected data, using OG System rules.
        """
        # Compute derived stats
        attributes = char_data['attributes']  # dict like {'brawn':2, ...}
        race = dnd_data.Race.get(char_data['race'])
        cls = dnd_data.OGClass.get(char_data['class'])

        # Starting HP: base from class + Brawn*2
        base_hp = 6  # from 01_core.json: base_hp = 6
        brawn = attributes.get('brawn', 0)
        hp = base_hp + (brawn * 2)  # formula from 01_core.json

        # Spell points if class uses them
        sp = 0
        if cls and cls.sp_per_level > 0:
            will = attributes.get('will', 0)
            sp = will * 2  # from 01_core.json: Will gives 2 SP per point

        # Skills: just store the names
        skills = char_data.get('skills', [])

        # Create Character instance
        from world.character import Character
        character = Character(
            id=f"char_{uuid.uuid4().hex[:6]}",
            name=char_data.get('name', 'Unnamed'),
            race=char_data['race'],
            char_class=char_data['class'],
            level=1,
            attributes=attributes,
            skills=skills,
            hp=hp,
            max_hp=hp,
            sp=sp,
            max_sp=sp,
            # narrative fields start empty
            backstory={},
            connections=[],
            secrets=[],
            vows={}
        )
        # Add to world
        self.world.character_manager.add_character(character)
        return character

    # ----------------------------------------------------------------------
    # Backstory Creation (from 17_player_narrative.json)
    # ----------------------------------------------------------------------
    def guide_backstory_creation(self, character_id, message, creation_state):
        """
        Guided backstory creation using OG System framework.
        Expects creation_state to track phase (origin, wound, recent, secret_generation).
        """
        character = self.world.character_manager.get_character(character_id)
        if not character:
            return {"error": "Character not found"}

        # Load backstory framework from self.narrative_framework (loaded from JSON)
        framework = self.narrative_framework.get("backstory_framework", {})
        phases = framework.get("phases", [])

        if not creation_state:
            creation_state = {
                'phase': 'origin',
                'backstory': {},
                'conversation': []
            }

        if message:
            creation_state['conversation'].append(("player", message))

        responses = []
        current_phase = creation_state['phase']

        # Helper to find phase data by name
        def get_phase_data(phase_name):
            for p in phases:
                if p.get("phase") == phase_name:
                    return p
            return None

        if current_phase == 'origin':
            phase_data = get_phase_data('origin')
            if not creation_state['backstory'].get('origin'):
                # First time – show prompts
                prompts = phase_data.get('prompts', [])
                if not message:
                    # Initial prompt
                    responses.append(Dialog("DM", "Let's start with your origin. " + " ".join(prompts), "narration"))
                else:
                    # Store answers – for simplicity, store the whole message as origin dict
                    # In a full implementation, you'd parse answers to match prompts.
                    creation_state['backstory']['origin'] = {"raw": message}
                    creation_state['phase'] = 'formative_wound'
                    responses.append(Dialog("DM", "Now, tell me about the formative wound that shaped you.", "narration"))
            else:
                creation_state['phase'] = 'formative_wound'

        if current_phase == 'formative_wound':
            phase_data = get_phase_data('formative_wound')
            if not creation_state['backstory'].get('formative_wound'):
                if not message:
                    prompts = phase_data.get('prompts', [])
                    responses.append(Dialog("DM", "Your formative wound: " + " ".join(prompts), "narration"))
                else:
                    creation_state['backstory']['formative_wound'] = {"raw": message}
                    creation_state['phase'] = 'recent_history'
                    responses.append(Dialog("DM", "Now, what about your recent history?", "narration"))
            else:
                creation_state['phase'] = 'recent_history'

        if current_phase == 'recent_history':
            phase_data = get_phase_data('recent_history')
            if not creation_state['backstory'].get('recent_history'):
                if not message:
                    prompts = phase_data.get('prompts', [])
                    responses.append(Dialog("DM", "Your recent history: " + " ".join(prompts), "narration"))
                else:
                    creation_state['backstory']['recent_history'] = {"raw": message}
                    creation_state['phase'] = 'secret_generation'
                    responses.append(Dialog("DM", "Thank you. I will now weave in some hidden secrets...", "narration"))
            else:
                creation_state['phase'] = 'secret_generation'

        if current_phase == 'secret_generation':
            # Generate 1-2 secrets using framework rules
            secret_framework = framework.get("secret_generation", {})
            secret_types = secret_framework.get("types", {})
            triggers = secret_framework.get("revelation_triggers", [])
            import random
            rng = random.Random(self.world.seed + hash(character.id))
            num_secrets = rng.randint(1, 2)
            for i in range(num_secrets):
                sec_type = rng.choice(list(secret_types.keys()))
                trigger = rng.choice(triggers) if triggers else {"type": "random", "target": ""}
                secret = {
                    "id": str(uuid.uuid4()),
                    "type": sec_type,
                    "description": f"A hidden truth: {secret_types[sec_type]}",
                    "revelation_trigger": trigger,
                    "revealed": False
                }
                if 'secrets' not in creation_state['backstory']:
                    creation_state['backstory']['secrets'] = []
                creation_state['backstory']['secrets'].append(secret)

            # Store backstory in character
            character.backstory = creation_state['backstory']
            creation_state = None   # finished
            responses.append(Dialog("DM", "Your backstory is complete. Secrets lie waiting to be discovered.", "narration"))

            # Optionally build connection web now
            self.build_connection_web_for_character(character_id)

        # Add player message to history if exists
        if message:
            responses.insert(0, Dialog("Player", message, "character"))

        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state
        }

    # ----------------------------------------------------------------------
    # Connection Web
    # ----------------------------------------------------------------------
    def build_connection_web_for_character(self, character_id):
        """
        Generate connections between a character's backstory and world elements.
        Populates character.connections and character.secrets.
        """
        character = self.world.character_manager.get_character(character_id)
        if not character:
            return

        # Gather world elements
        elements = []
        # Regions
        for region in self.world.campaign_state.surface_regions.values():
            elements.append(("region", region.id, region.name, region.terrain_tags))
        # Factions
        for faction in self.world.campaign_state.factions.values():
            elements.append(("faction", faction.id, faction.name, faction.goals))
        # Locations (settlements, dungeons) from world_map
        for loc in self.world.world_map.locations.values():
            elements.append(("location", loc.id, loc.name, [loc.type]))
        # NPCs (if any)
        if hasattr(self.world.world_map, 'npcs'):
            for npc in self.world.world_map.npcs.values():   # assuming world_map has npcs
                elements.append(("npc", npc.id, npc.name, [npc.role]))

        # Use seed for determinism
        rng = random.Random(self.world.seed + hash(character.id))

        # Define connection types
        connection_types = ["direct", "reflection", "consequence", "parallel", "inversion", "prophecy"]

        # Keep track of used element IDs to avoid duplicates
        used_elements = set()

        # For each backstory node, try to create connections
        backstory = character.backstory
        if not backstory:
            return

        # Origin
        if "origin" in backstory:
            origin = backstory["origin"]
            origin_region = origin.get("origin_region")
            if origin_region:
                # Try to find a region with matching ID
                for etype, eid, ename, etags in elements:
                    if etype == "region" and eid == origin_region:
                        self._add_connection(character, "direct", "origin", etype, eid,
                                             f"Your homeland, {ename}.", rng, used_elements)
                        break

        # Formative wound
        if "formative_wound" in backstory:
            wound = backstory["formative_wound"]
            wound_actor_id = wound.get("wound_actor", {}).get("id")
            if wound_actor_id:
                for etype, eid, ename, etags in elements:
                    if eid == wound_actor_id:
                        self._add_connection(character, "direct", "formative_wound", etype, eid,
                                             f"The one who wronged you: {ename}.", rng, used_elements)
                        break

        # Recent history
        if "recent_history" in backstory:
            recent = backstory["recent_history"]
            debt_to = recent.get("outstanding_debt", {}).get("to")
            if debt_to:
                for etype, eid, ename, etags in elements:
                    if eid == debt_to:
                        self._add_connection(character, "direct", "recent_history", etype, eid,
                                             f"You owe a debt to {ename}.", rng, used_elements)
                        break

        # Ensure at least 2-3 connections. If not enough, create random ones.
        needed = max(0, 2 - len(character.connections))
        for _ in range(needed):
            # Pick a random element not used yet
            candidates = [e for e in elements if e[1] not in used_elements]
            if not candidates:
                break
            etype, eid, ename, etags = rng.choice(candidates)
            conn_type = rng.choice(connection_types)
            self._add_connection(character, conn_type, "random", etype, eid,
                                 f"A mysterious link to {ename}.", rng, used_elements)

        # Generate one hidden secret connection
        secret_type = rng.choice(["lineage", "connection", "prophecy", "infection", "duplicity", "obligation"])
        # Pick a random element that hasn't been used for a direct connection
        secret_candidates = [e for e in elements if e[1] not in used_elements]
        if secret_candidates:
            etype, eid, ename, etags = rng.choice(secret_candidates)
            secret = {
                "id": str(uuid.uuid4()),
                "type": secret_type,
                "description": f"Unknown truth linking you to {ename}.",
                "revelation_trigger": self._generate_trigger(etype, eid, rng),
                "revealed": False
            }
            character.secrets.append(secret)

    def _add_connection(self, character, conn_type, backstory_node, target_type, target_id, description, rng, used_elements):
        """Helper to create a connection dict and append to character.connections."""
        conn = {
            "id": str(uuid.uuid4()),
            "type": conn_type,
            "pc_node": backstory_node,
            "world_element": {"type": target_type, "id": target_id},
            "description": description,
            "tension": rng.choice(["harmony", "irony", "tragedy", "hope", "mystery"]),
            "visibility": "hidden" if backstory_node == "random" else "hinted"
        }
        character.connections.append(conn)
        used_elements.add(target_id)

    def _generate_trigger(self, etype, eid, rng):
        """Generate a revelation trigger for a secret based on world element type."""
        triggers = {
            "region": {"type": "enter_region", "target": eid},
            "faction": {"type": "meet_faction", "target": eid},
            "location": {"type": "enter_location", "target": eid},
            "npc": {"type": "meet_npc", "target": eid}
        }
        return triggers.get(etype, {"type": "random", "target": eid})

    # ----------------------------------------------------------------------
    # Revelation System
    # ----------------------------------------------------------------------
    def _check_revelation_triggers(self, character, context):
        """Check if any secret's trigger matches the current context."""
        for secret in character.secrets:
            if secret.get('revealed'):
                continue
            trigger = secret.get('revelation_trigger', {})
            trigger_type = trigger.get('type')
            target = trigger.get('target')

            if trigger_type == 'enter_region' and context.get('region_id') == target:
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'enter_location' and context.get('location_id') == target:
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'meet_faction' and target in context.get('faction_ids', []):
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'meet_npc' and target in context.get('npc_ids', []):
                self._deliver_revelation(character, secret, context)
            elif trigger_type == 'random' and random.random() < 0.05:
                self._deliver_revelation(character, secret, context)

    def _deliver_revelation(self, character, secret, context):
        """Generate a revelation dialog and update secret."""
        secret['revealed'] = True
        methods = ["environmental", "npc_slip", "confrontation", "dream_vision", "item_resonance", "transformation", "research", "betrayal"]
        method = random.choice(methods)

        lines = {
            "lineage": "You discover your true parentage...",
            "connection": "You realize that person is not who they seemed...",
            "prophecy": "An ancient prophecy speaks of you...",
            "infection": "Something stirs within you...",
            "duplicity": "You did something you don't remember...",
            "obligation": "A debt you didn't know you owed comes due..."
        }
        description = lines.get(secret['type'], "A truth is revealed.")

        if self.dm:
            self.dm.add_dialog(Dialog("DM", f"{description} ({method})", "revelation"))

    # ----------------------------------------------------------------------
    # Player Action Processing
    # ----------------------------------------------------------------------
    def process_player_action(self, player_id: str, message: str):
        """Process player input, update pacing, check revelations, and return DM response."""
        if not self.dm:
            return {
                "responses": [{
                    "speaker": "DM",
                    "content": "Narrative system is not fully initialized",
                    "type": "system"
                }],
                "dialog_history": []
            }

        # Update game state with current scene
        self.game_state.current_scene = self.world.get_current_scene()

        # Analyze motivation and update pacing
        player = self.world.players.get(player_id)
        character = None
        if player and player.active_character_id:
            character = self.world.character_manager.get_character(player.active_character_id)

        motivation = self.motivation.analyze_action(message, character)
        action_type_map = {
            "combat": "combat",
            "curiosity": "discovery",
            "acquisition": "discovery",
            "social": "dialogue",
            "unknown": "dialogue"
        }
        pacing_action_type = action_type_map.get(motivation, "dialogue")
        self.pacing.handle_player_action(pacing_action_type)

        # Log for consequences
        self.consequences.log_action(message, motivation)

        # Get DM response
        dialogs = self.dm.process_player_input(player_id, message)
        responses = [{"speaker": d.speaker, "content": d.content, "type": d.dialog_type} for d in dialogs]

        # Gentle nudge if needed
        guidance = self.guide.get_gentle_nudge({'action': message, 'motivation': motivation, 'pacing': self.pacing.current_phase})
        if guidance:
            responses.append({"speaker": "DM", "content": guidance, "type": "narration"})

        # Check revelations
        if character:
            context = {
                'location_id': self.world.current_location.id if self.world.current_location else None,
                'region_id': getattr(self.world.current_location, 'region_id', None),
                'faction_ids': [],  # TODO: populate
                'npc_ids': []       # TODO: populate
            }
            self._check_revelation_triggers(character, context)

        # Process consequences periodically
        if random.random() < 0.3:
            self.consequences.apply_delayed_consequences()

        return {
            "responses": responses,
            "dialog_history": [d.to_dict() for d in self.dm.get_dialog_history()],
            "motivation": motivation,
            "pacing": self.pacing.get_status()
        }

    # ----------------------------------------------------------------------
    # Scene Management
    # ----------------------------------------------------------------------
    def set_current_scene(self, scene_description: str):
        """Update the current scene for narrative context."""
        self.game_state.current_scene = scene_description
        if self.dm:
            self.dm.game_state.current_scene = scene_description

    # ----------------------------------------------------------------------
    # Utility: Execute narrative commands (vows, bonuses, etc.)
    # ----------------------------------------------------------------------
    def execute_narrative_command(self, command: str, context: dict) -> dict:
        """
        Execute a narrative‑system command (e.g., vow advancement).
        See previous answer for implementation.
        """
        parts = command.split()
        if not parts:
            return {"success": False, "error": "Empty command"}

        cmd = parts[0]
        if cmd == "vow_advance" and len(parts) == 4:
            char_id, vow_id, amount = parts[1], parts[2], int(parts[3])
            character = self.world.character_manager.get_character(char_id)
            if character and vow_id in character.vows:
                character.vows[vow_id]['progress'] += amount
                return {"success": True, "message": f"Vow {vow_id} advanced by {amount}"}
        elif cmd == "vow_complete" and len(parts) == 3:
            char_id, vow_id = parts[1], parts[2]
            character = self.world.character_manager.get_character(char_id)
            if character and vow_id in character.vows:
                character.vows[vow_id]['status'] = 'complete'
                return {"success": True, "message": f"Vow {vow_id} completed"}
        # Add more commands as needed

        return {"success": False, "error": f"Unknown command: {cmd}"}