
# world\narrative_system.py
from world.ai_dungeon_master import AIDungeonMaster, Character, GameState
from enum import Enum
from collections import defaultdict
from typing import Literal

# Define the pacing phase type
PacingPhase = Literal['exploration', 'downtime', 'tension', 'climax']

class NarrativeGuide:
    def __init__(self):
        self.fallback_hooks = [
            "A mysterious stranger approaches you with urgent news",
            "You overhear a conversation about strange occurrences nearby",
            "A sudden environmental change demands attention"
        ]
    
    def get_gentle_nudge(self, player_actions):
        """Provide subtle narrative guidance based on player behavior"""
        if player_actions.get('distracted', False):
            return self._create_distraction_resolution()
        if player_actions.get('off_track', False):
            return self._redirect_to_storyline()
        return None
    
    def _create_distraction_resolution(self):
        """Resolve player distractions by tying them to main plot"""
        return "As you investigate the side path, you discover evidence connecting it to the main quest"
    
    def _redirect_to_storyline(self):
        """Redirect players without breaking immersion"""
        return "Your exploration leads you back to the main path, where new developments await"
    
    def emergency_nudge(self):
        """Forceful but narratively justified redirection"""
        hook = random.choice(self.fallback_hooks)
        return f"Suddenly, {hook} - demanding your immediate attention"

class ConsequenceSystem:
    def __init__(self, world_state):
        self.world = world_state
        self.action_registry = []
    
    def log_action(self, action, significance):
        """Track player actions and their narrative weight"""
        self.action_registry.append({
            "action": action,
            "significance": significance,
            "resolved": False
        })
    
    def apply_delayed_consequences(self):
        """Apply consequences for past actions at dramatically appropriate moments"""
        unresolved = [a for a in self.action_registry if not a['resolved']]
        for action in unresolved:
            if self._is_appropriate_moment(action):
                consequence = self._generate_consequence(action)
                # Add to world events or directly to narrative
                if hasattr(self.world, 'add_event'):
                    self.world.add_event(consequence)
                action['resolved'] = True

    def _is_appropriate_moment(self, action):
        """Determine if now is a good time to apply this consequence"""
        # Simple implementation - 30% chance when there are unresolved actions
        # todo - is there a better way to do this that takes a look at complexity of story arc
        return random.random() < 0.3
    
    def _generate_consequence(self, action):
        consequence_map = {
            "save_npc": "The NPC you saved returns to aid you in a critical moment",
            "kill_important": "Allies of the fallen seek vengeance against you",
            "steal_artifact": "The artifact's original owners track you down",
            "ignore_quest": "The ignored problem has now grown beyond control"
        }
        return consequence_map.get(action['action'], "Your past actions have unexpected consequences")

class MotivationTracker:
    def __init__(self):
        self.player_profiles = {}
        self.session_tendencies = []
    
    def analyze_action(self, action, character):
        """Categorize player actions into motivation types"""
        if "explore" in action.lower():
            return "curiosity"
        if "fight" in action.lower() or "attack" in action.lower():
            return "combat"
        if "loot" in action.lower() or "take" in action.lower():
            return "acquisition"
        if "talk" in action.lower() or "ask" in action.lower():
            return "social"
        return "unknown"
    
    def get_narrative_leverage(self, motivation):
        """Suggest story elements that appeal to player motivations"""
        leverage_map = {
            "curiosity": "You notice something strange that begs investigation",
            "combat": "Dangerous foes appear, blocking your path forward",
            "acquisition": "A glint of treasure catches your eye nearby",
            "social": "An NPC approaches with potentially valuable information"
        }
        return leverage_map.get(motivation, "New developments unfold around you")

class ChoiceArchitect:
    def __init__(self):
        self.decision_points = {}
    
    def create_branching_path(self, key_point):
        """Create narrative branches that converge at key points"""
        branches = {
            "path_a": f"If you choose path A: {self._create_path_description('a')}",
            "path_b": f"If you choose path B: {self._create_path_description('b')}"
        }
        convergence = self._create_convergence_point(key_point)
        return {"branches": branches, "convergence": convergence}
    
    def _create_path_description(self, path):
        return {
            "a": "You take the mountain path, encountering harsh weather but finding ancient ruins",
            "b": "You follow the river, facing dangerous rapids but discovering hidden caves"
        }.get(path, "You journey through challenging terrain")
    
    def _create_convergence_point(self, key_point):
        return f"Both paths lead to {key_point}, where the next phase of your adventure awaits"


class PacingController:
    def __init__(self):
        self.current_phase: PacingPhase = 'exploration'
        self.phase_progress = 0  # 0-100 scale
        self.player_actions = 0
    
    def handle_player_action(self, action_type: str):
        self.player_actions += 1
        
        # Pacing adjustments based on action
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
        
        # Phase transitions
        if self.phase_progress >= 75 and self.current_phase != 'climax':
            self.current_phase = 'climax'
        elif self.phase_progress >= 50 and self.current_phase not in ['tension', 'climax']:
            self.current_phase = 'tension'
    
    def _decrease_tension(self, amount: int):
        self.phase_progress = max(0, self.phase_progress - amount)
        
        # Phase transitions
        if self.phase_progress < 25 and self.current_phase != 'exploration':
            self.current_phase = 'exploration'
        elif self.phase_progress < 50 and self.current_phase == 'tension':
            self.current_phase = 'exploration'
    
    def get_pacing_recommendation(self) -> str:
        if self.current_phase == 'exploration':
            return "Introduce new locations or NPCs"
        elif self.current_phase == 'downtime':
            return "Provide roleplaying opportunities"
        elif self.current_phase == 'tension':
            return "Hint at upcoming dangers"
        elif self.current_phase == 'climax':
            return "Trigger major story event or boss battle"
        return "Maintain current pacing"
    
    # Optional: Add a method to get the current phase and progress for debugging
    def get_status(self) -> dict:
        return {
            "phase": self.current_phase,
            "progress": self.phase_progress,
            "actions": self.player_actions,
            "recommendation": self.get_pacing_recommendation()
        }



class NarrativeSystem:
    RACE_GUIDES = {
        "human": {
            "description": "Humans are adaptable and ambitious. They thrive in diverse environments and master various skills.",
            "traits": "+1 to all ability scores\nExtra skill proficiency\nBonus feat at 1st level",
            "playstyle": "Versatile generalists who excel in any role",
            "questions": ["What drives your ambition?", "How do you stand out in a world of specialists?"]
        },
        "elf": {
            "description": "Elves are graceful, perceptive beings with deep connections to nature and magic. They live for centuries.",
            "traits": "+2 Dexterity\nAdvantage vs. charm\nImmunity to magical sleep\nTrance (4hr rest)",
            "playstyle": "Stealthy archers, nimble fighters, or nature-based spellcasters",
            "questions": ["What ancient secrets have you learned?", "How do you view shorter-lived races?"]
        },
        "dwarf": {
            "description": "Dwarves are resilient, stalwart folk who value tradition and craftsmanship. They're natural miners and warriors.",
            "traits": "+2 Constitution\nAdvantage vs. poison\nStonecunning\nCombat training with axes/hammers",
            "playstyle": "Tough front-line fighters, skilled artisans, or underground explorers",
            "questions": ["What great work have you crafted?", "How do you honor your ancestors?"]
        },
        "halfling": {
            "description": "Halflings are cheerful, nimble folk who find joy in simple pleasures. They're surprisingly brave.",
            "traits": "+2 Dexterity\nLucky (reroll 1s)\nBrave (advantage vs. fear)\nNimbleness (move through spaces)",
            "playstyle": "Stealthy rogues, charming diplomats, or lucky adventurers",
            "questions": ["What comforts do you miss from home?", "How do you face dangers larger than you?"]
        },
        "dragonborn": {
            "description": "Dragonborn are proud, honorable beings descended from dragons. They command elemental breath.",
            "traits": "+2 Strength, +1 Charisma\nDraconic ancestry (choose element)\nBreath weapon\nDamage resistance",
            "playstyle": "Powerful warriors, inspiring leaders, or elemental spellcasters",
            "questions": ["What legacy does your draconic blood carry?", "How do you control your inner fire?"]
        }
    }
    
    CLASS_GUIDES = {
        "fighter": {
            "description": "Masters of combat who excel with all weapons and armor. They adapt to any battle situation.",
            "abilities": "Extra attacks\nCombat maneuvers\nArmor mastery\nSecond Wind healing",
            "playstyle": "Front-line defenders, versatile warriors, or tactical commanders",
            "archetypes": ["Champion (simple, powerful)", "Battle Master (tactical maneuvers)", "Eldritch Knight (magic warrior)"]
        },
        "wizard": {
            "description": "Scholars of arcane magic who wield power through knowledge and spellbooks.",
            "abilities": "Spellbook preparation\nRitual casting\nArcane recovery\nSpecialized schools of magic",
            "playstyle": "Powerful spellcasters, problem solvers, or knowledge seekers",
            "archetypes": ["Evoker (damage dealer)", "Abjurer (protective magic)", "Illusionist (deception master)"]
        },
        "rogue": {
            "description": "Agile specialists who rely on stealth, precision, and cunning over brute force.",
            "abilities": "Sneak Attack precision damage\nExpertise (double proficiency)\nCunning Action (dash/disengage/hide)\nUncanny Dodge",
            "playstyle": "Scouts, spies, trap disablers, or charismatic tricksters",
            "archetypes": ["Thief (fast and sneaky)", "Assassin (deadly strikes)", "Arcane Trickster (magic-enhanced rogue)"]
        },
        "cleric": {
            "description": "Divine agents who channel their deity's power to heal, protect, or smite foes.",
            "abilities": "Divine spellcasting\nChannel Divinity\nDomain specialization\nTurn Undead",
            "playstyle": "Healers, protectors, frontline combatants, or divine emissaries",
            "archetypes": ["Life Domain (healing)", "War Domain (combat)", "Knowledge Domain (lore)"]
        },
        "bard": {
            "description": "Artistic performers who inspire allies and manipulate reality through creative expression.",
            "abilities": "Bardic Inspiration\nJack of All Trades\nMagical secrets\nExpertise in skills",
            "playstyle": "Party supporters, versatile spellcasters, or charismatic leaders",
            "archetypes": ["Lore (knowledge and magic)", "Valor (combat inspiration)", "Glamour (charm and enchantment)"]
        }
    }
    
    BACKGROUND_GUIDES = {
        "acolyte": {
            "description": "You served in a religious order, learning rites and sacred lore.",
            "features": "Shelter of the Faithful\nKnowledge of religious hierarchies",
            "skills": ["Insight", "Religion"],
            "equipment": "Holy symbol, prayer book, vestments"
        },
        "criminal": {
            "description": "You lived outside the law as a thief, smuggler, or underworld contact.",
            "features": "Criminal contact network\nKnowledge of underworld operations",
            "skills": ["Deception", "Stealth"],
            "equipment": "Crowbar, dark common clothes, thieves' tools"
        },
        "folk hero": {
            "description": "You defended your community against threats, becoming a local legend.",
            "features": "Rustic hospitality\nPeople recognize and help you",
            "skills": ["Animal Handling", "Survival"],
            "equipment": "Artisan's tools, shovel, pot"
        },
        "sage": {
            "description": "You were a researcher and scholar obsessed with uncovering knowledge.",
            "features": "Researcher (access to obscure information)\nSpecialized field of study",
            "skills": ["Arcana", "History"],
            "equipment": "Bottle of ink, scholar's robes, letters from colleagues"
        },
        "soldier": {
            "description": "You served in a military force, learning discipline and combat tactics.",
            "features": "Military rank\nAccess to military resources",
            "skills": ["Athletics", "Intimidation"],
            "equipment": "Insignia of rank, trophy from fallen enemy, dice set"
        }
    }
    
    ABILITY_SCORE_METHODS = {
        "standard": "Balanced preset scores: 15, 14, 13, 12, 10, 8",
        "point_buy": "27 points to customize scores (min 8, max 15)",
        "manual": "Roll 4d6 and drop lowest die six times",
        "dice_pool": "Roll 24d6 and assign sets of 3 dice to abilities"
    }
    
    ABILITY_SCORE_IMPORTANCE = {
        "fighter": ["Strength", "Constitution"],
        "wizard": ["Intelligence", "Constitution"],
        "rogue": ["Dexterity", "Charisma"],
        "cleric": ["Wisdom", "Strength"],
        "bard": ["Charisma", "Dexterity"]
    }
    
    def __init__(self, world_state, ai_system, dm_chat_ai=None):  # [OK] Add dm_chat_ai parameter
        self.world = world_state
        self.ai = ai_system

        # Initialize the AI Dungeon Master only if AI system is available
        if ai_system:
            self.dm = AIDungeonMaster(dm_chat_ai=dm_chat_ai)  # [OK] Pass dm_chat_ai
        else:
            self.dm = None

        self.game_state = GameState()

        self.guide = NarrativeGuide()
        self.consequences = ConsequenceSystem(world_state)
        self.motivation = MotivationTracker()
        self.choices = ChoiceArchitect()
        self.pacing = PacingController()
        
        # Initialize characters from world state
        self._initialize_characters()

    def on_location_discovered(self, location_id: str):
        """
        Handle location discovery narrative events including pacing updates
        """
        # Call the pacing system to handle the discovery event
        self.pacing.handle_discovery_event()
        
        # Your existing location discovery logic goes here
        location = self.world.world_map.get_location(location_id)
        if location and not location.discovered:
            location.discovered = True
            # Generate initial quest for new location
            new_quest = self.generate_quest(location_id, "First discovery")
            self.world.add_quest(new_quest)
            # Start tracking the new quest
            if hasattr(self, 'active_quests'):
                self.active_quests.append(new_quest.id)
            
            # Log the discovery
            if hasattr(self, 'session_log'):
                self.session_log.append(f"Discovered {location.name}")
    
    def on_dungeon_completed(self, success: bool):
        """
        Handle dungeon completion for pacing updates
        """
        # Call the pacing system to handle the dungeon completion
        self.pacing.handle_dungeon_completion(success)
        
        # Add any additional dungeon completion logic here
        if success:
            # Handle successful dungeon completion
            if hasattr(self, 'session_log'):
                self.session_log.append("Dungeon completed successfully!")
        else:
            # Handle failed dungeon completion  
            if hasattr(self, 'session_log'):
                self.session_log.append("Dungeon attempt failed!")


    
    def guide_character_creation(self, player_id, message, creation_state):
        """Fully guided character creation with deep explanations"""
        # Initialize state
        if not creation_state:
            creation_state = {
                'phase': 'welcome',
                'scores': {},
                'race': None,
                'class': None,
                'background': None,
                'personality': None,
                'ideals': None,
                'bonds': None,
                'flaws': None,
                'conversation': []
            }
        
        # Add player message to conversation history
        if message:
            creation_state['conversation'].append(("player", message))
        
        responses = []
        phase = creation_state['phase']
        
        # --- Welcome Phase ---
        if phase == 'welcome':
            responses.append(Dialog(
                "DM",
                "Welcome to character creation! I'll guide you through crafting your adventurer. "
                "This process has 7 steps:\n"
                "1. Ability Scores - Your character's core capabilities\n"
                "2. Race - Your character's species and heritage\n"
                "3. Class - Your character's profession and abilities\n"
                "4. Background - Your character's history and training\n"
                "5. Personality - How your character thinks and behaves\n"
                "6. Bonds & Flaws - What drives and hinders your character\n"
                "7. Finalization - Bringing it all together\n\n"
                "Where would you like to begin? Or ask me anything!",
                "narration"
            ))
            creation_state['phase'] = 'method_selection'
        
        # --- Method Selection Phase ---
        elif phase == 'method_selection':
            if not message:
                # Initial prompt
                responses.append(Dialog(
                    "DM",
                    "First, how would you like to determine your ability scores? Options:\n"
                    "- Standard Array: Balanced preset scores\n"
                    "- Point Buy: Customize with points\n"
                    "- Manual Roll: Roll dice for randomness\n"
                    "- Dice Pool: Advanced dice assignment\n\n"
                    "Which method interests you? Or ask about them!",
                    "narration"
                ))
            elif "standard" in message.lower():
                creation_state['method'] = 'standard'
                responses.append(Dialog(
                    "DM",
                    "Excellent choice! The standard array gives you balanced scores: "
                    "15, 14, 13, 12, 10, 8. We'll assign these later.\n\n"
                    "Now, let's choose your race. Which heritage calls to you? "
                    "(Human, Elf, Dwarf, Halfling, Dragonborn)",
                    "narration"
                ))
                creation_state['phase'] = 'race_selection'
            elif "point" in message.lower():
                creation_state['method'] = 'point_buy'
                responses.append(Dialog(
                    "DM",
                    "Point buy offers great customization! You have 27 points to spend:\n"
                    "Score  Cost\n"
                    "8      0\n9      1\n10     2\n11     3\n12     4\n13     5\n14     7\n15     9\n\n"
                    "What scores would you like? (Example: 15,14,13,12,10,8)",
                    "narration"
                ))
            elif "roll" in message.lower():
                creation_state['method'] = 'manual'
                responses.append(Dialog(
                    "DM",
                    "The thrill of the dice! I'll roll 4d6 six times, dropping the lowest die each time.\n"
                    "Rolling now...\n",
                    "narration"
                ))
                rolls = [sorted([random.randint(1,6) for _ in range(4)])[1:] for _ in range(6)]
                results = [sum(r) for r in rolls]
                responses.append(Dialog(
                    "DM",
                    f"Results: {results}\n"
                    "You can assign these to: Strength, Dexterity, Constitution, "
                    "Intelligence, Wisdom, Charisma.\n"
                    "How would you like to assign them?",
                    "narration"
                ))
            elif "dice pool" in message.lower():
                creation_state['method'] = 'dice_pool'
                responses.append(Dialog(
                    "DM",
                    "Advanced method! I'll roll 24d6 for you to create ability score pools.\n"
                    "Rolling now...",
                    "narration"
                ))
                dice = [random.randint(1,6) for _ in range(24)]
                responses.append(Dialog(
                    "DM",
                    f"Dice rolled: {dice}\n"
                    "Group them into six sets of 3-4 dice for each ability score. "
                    "Each set must total at least 9. How would you like to group them?",
                    "narration"
                ))
            else:
                # Explain methods
                responses.append(Dialog(
                    "DM",
                    f"Let me explain ability score methods:\n"
                    f"1. Standard Array: {self.ABILITY_SCORE_METHODS['standard']}\n"
                    f"2. Point Buy: {self.ABILITY_SCORE_METHODS['point_buy']}\n"
                    f"3. Manual Roll: {self.ABILITY_SCORE_METHODS['manual']}\n"
                    f"4. Dice Pool: {self.ABILITY_SCORE_METHODS['dice_pool']}\n\n"
                    "Which would you prefer?",
                    "narration"
                ))
        
        # --- Race Selection Phase ---
        elif phase == 'race_selection':
            if not message:
                # Initial prompt
                responses.append(Dialog(
                    "DM",
                    "Your race shapes your physical traits and innate abilities. Options:\n"
                    "- Human: Versatile and ambitious\n"
                    "- Elf: Graceful and perceptive\n"
                    "- Dwarf: Resilient and sturdy\n"
                    "- Halfling: Nimble and lucky\n"
                    "- Dragonborn: Strong and charismatic\n\n"
                    "Which interests you? Or ask about a specific race!",
                    "narration"
                ))
            else:
                selected_race = None
                for race in self.RACE_GUIDES:
                    if race in message.lower():
                        selected_race = race
                        break
                
                if selected_race:
                    guide = self.RACE_GUIDES[selected_race]
                    responses.append(Dialog(
                        "DM",
                        f"{guide['description']}\n\n"
                        f"Key Traits:\n{guide['traits']}\n\n"
                        f"Playstyle: {guide['playstyle']}\n\n"
                        f"To help develop your character:\n"
                        f"{guide['questions'][0]}\n"
                        f"{guide['questions'][1]}",
                        "narration"
                    ))
                    creation_state['race'] = selected_race
                    creation_state['phase'] = 'class_selection'
                else:
                    # Explain specific race
                    race_to_explain = None
                    for race in self.RACE_GUIDES:
                        if race in message.lower():
                            race_to_explain = race
                            break
                    
                    if race_to_explain:
                        guide = self.RACE_GUIDES[race_to_explain]
                        responses.append(Dialog(
                            "DM",
                            f"Let me tell you about {race_to_explain.capitalize()}:\n"
                            f"{guide['description']}\n\n"
                            f"Key Traits:\n{guide['traits']}\n\n"
                            f"Playstyle: {guide['playstyle']}",
                            "narration"
                        ))
                    else:
                        responses.append(Dialog(
                            "DM",
                            "I didn't recognize that race. Please choose from: Human, Elf, Dwarf, Halfling, Dragonborn. "
                            "Or ask about a specific race!",
                            "narration"
                        ))
        
        # --- Class Selection Phase ---
        elif phase == 'class_selection':
            if not message:
                # Initial prompt
                responses.append(Dialog(
                    "DM",
                    "Your class defines your core capabilities and role in the party. Options:\n"
                    "- Fighter: Master of combat\n"
                    "- Wizard: Scholar of arcane magic\n"
                    "- Rogue: Stealthy specialist\n"
                    "- Cleric: Divine agent\n"
                    "- Bard: Inspiring performer\n\n"
                    "Which calls to you? Or ask about a specific class!",
                    "narration"
                ))
            else:
                selected_class = None
                for cls in self.CLASS_GUIDES:
                    if cls in message.lower():
                        selected_class = cls
                        break
                
                if selected_class:
                    guide = self.CLASS_GUIDES[selected_class]
                    responses.append(Dialog(
                        "DM",
                        f"{guide['description']}\n\n"
                        f"Key Abilities:\n{guide['abilities']}\n\n"
                        f"Playstyle: {guide['playstyle']}\n\n"
                        f"Specializations:\n- " + "\n- ".join(guide['archetypes']) + "\n\n"
                        f"Which specialization interests you?",
                        "narration"
                    ))
                    creation_state['class'] = selected_class
                else:
                    # Explain specific class
                    class_to_explain = None
                    for cls in self.CLASS_GUIDES:
                        if cls in message.lower():
                            class_to_explain = cls
                            break
                    
                    if class_to_explain:
                        guide = self.CLASS_GUIDES[class_to_explain]
                        responses.append(Dialog(
                            "DM",
                            f"Let me tell you about the {class_to_explain.capitalize()}:\n"
                            f"{guide['description']}\n\n"
                            f"Key Abilities:\n{guide['abilities']}\n\n"
                            f"Playstyle: {guide['playstyle']}\n\n"
                            f"Specializations:\n- " + "\n- ".join(guide['archetypes']),
                            "narration"
                        ))
                    else:
                        responses.append(Dialog(
                            "DM",
                            "I didn't recognize that class. Please choose from: Fighter, Wizard, Rogue, Cleric, Bard. "
                            "Or ask about a specific class!",
                            "narration"
                        ))
        
        # --- Background Selection Phase ---
        elif phase == 'background_selection':
            if not message:
                # Initial prompt
                responses.append(Dialog(
                    "DM",
                    "Your background defines your history and non-adventuring skills. Options:\n"
                    "- Acolyte: Religious service\n"
                    "- Criminal: Underworld connections\n"
                    "- Folk Hero: Champion of common people\n"
                    "- Sage: Scholar and researcher\n"
                    "- Soldier: Military experience\n\n"
                    "Which shaped your past? Or ask about a specific background!",
                    "narration"
                ))
            else:
                selected_bg = None
                for bg in self.BACKGROUND_GUIDES:
                    if bg in message.lower():
                        selected_bg = bg
                        break
                
                if selected_bg:
                    guide = self.BACKGROUND_GUIDES[selected_bg]
                    responses.append(Dialog(
                        "DM",
                        f"{guide['description']}\n\n"
                        f"Key Features: {guide['features']}\n"
                        f"Skills: {', '.join(guide['skills'])}\n"
                        f"Equipment: {guide['equipment']}\n\n"
                        f"What specific event from your background drives you to adventure?",
                        "narration"
                    ))
                    creation_state['background'] = selected_bg
                    creation_state['phase'] = 'personality_development'
                else:
                    # Explain specific background
                    bg_to_explain = None
                    for bg in self.BACKGROUND_GUIDES:
                        if bg in message.lower():
                            bg_to_explain = bg
                            break
                    
                    if bg_to_explain:
                        guide = self.BACKGROUND_GUIDES[bg_to_explain]
                        responses.append(Dialog(
                            "DM",
                            f"Let me tell you about the {bg_to_explain.capitalize()} background:\n"
                            f"{guide['description']}\n\n"
                            f"Key Features: {guide['features']}\n"
                            f"Skills: {', '.join(guide['skills'])}\n"
                            f"Equipment: {guide['equipment']}",
                            "narration"
                        ))
                    else:
                        responses.append(Dialog(
                            "DM",
                            "I didn't recognize that background. Please choose from: Acolyte, Criminal, Folk Hero, Sage, Soldier. "
                            "Or ask about a specific background!",
                            "narration"
                        ))
        
        # --- Personality Development Phase ---
        elif phase == 'personality_development':
            if not creation_state['personality']:
                responses.append(Dialog(
                    "DM",
                    "How would you describe your character's personality? "
                    "(Examples: Brave, cautious, charming, stoic, curious, pragmatic)",
                    "narration"
                ))
            elif not creation_state['ideals']:
                responses.append(Dialog(
                    "DM",
                    "What ideals drive your character? "
                    "(Examples: Justice, knowledge, freedom, power, redemption)",
                    "narration"
                ))
            elif not creation_state['bonds']:
                responses.append(Dialog(
                    "DM",
                    "What bonds connect your character to the world? "
                    "(Examples: Family, mentor, homeland, oath, artifact)",
                    "narration"
                ))
            elif not creation_state['flaws']:
                responses.append(Dialog(
                    "DM",
                    "What flaws or secrets burden your character? "
                    "(Examples: Pride, fear of water, greedy, haunted past)",
                    "narration"
                ))
            else:
                # All personality aspects completed
                responses.append(Dialog(
                    "DM",
                    "Magnificent! Your character is nearly complete. "
                    "Let's review everything before finalizing.",
                    "narration"
                ))
                creation_state['phase'] = 'finalization'
        
        # --- Finalization Phase ---
        elif phase == 'finalization':
            character = self._create_character(creation_state)
            responses.append(Dialog(
                "DM",
                f"Behold {character['name']}, the {character['race']} {character['class']}!\n\n"
                f"Background: {character['background']}\n"
                f"Personality: {character['personality']}\n"
                f"Ideals: {character['ideals']}\n"
                f"Bonds: {character['bonds']}\n"
                f"Flaws: {character['flaws']}\n\n"
                "Would you like to make any changes? (Or say 'finalize' to complete)",
                "narration"
            ))
            # Show character card in UI
            responses.append(Dialog(
                "System",
                f"PREVIEW_CHARACTER:{json.dumps(character)}",
                "system"
            ))
        
        # --- Completion ---
        elif phase == 'complete':
            character = self._create_character(creation_state)
            responses.append(Dialog(
                "DM",
                f"Magnificent! {character['name']} is ready for adventure! "
                "Your character has been added to your party.",
                "narration"
            ))
            # Show final character card
            responses.append(Dialog(
                "System",
                f"FINAL_CHARACTER:{json.dumps(character)}",
                "system"
            ))
            creation_state = None
        
        # Add player message to history if exists
        if message:
            responses.insert(0, Dialog(
                "Player",
                message,
                "character"
            ))
        
        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state
        }
    
        
    def _initialize_characters(self):
        """Load characters from world state into the DM system"""

        # Safely handle missing characters attribute
        if not hasattr(self.world, 'characters') or not self.world.characters:
            return

        for player_id, character_data in self.world.characters.items():
            character = Character(
                name=character_data['name'],
                player_id=player_id,
                backstory={
                    'race': character_data['race'],
                    'class': character_data['class'],
                    'background': character_data['background']
                },
                traits=[
                    character_data['personality'],
                    character_data['ideals'],
                    character_data['bonds'],
                    character_data['flaws']
                ]
            )
            self.dm.add_character(player_id, character)


    def guide_character_creation(self, player_id, message, creation_state):
        """Guide character creation through conversation"""
        # Set up DM persona for character creation
        self.dm.game_state.current_scene = "Character Creation Session"
        
        # Process player response
        if message:
            # Save player's response to the current question
            current_step = creation_state['step']
            if current_step == 1:
                creation_state['character']['race'] = message
            elif current_step == 2:
                creation_state['character']['class'] = message
            elif current_step == 3:
                creation_state['character']['background'] = message
            elif current_step == 4:
                creation_state['character']['personality'] = message
            elif current_step == 5:
                creation_state['character']['ideals'] = message
            elif current_step == 6:
                creation_state['character']['bonds'] = message
            elif current_step == 7:
                creation_state['character']['flaws'] = message
            
            # Move to next step
            creation_state['step'] += 1
        
        # Determine next step
        step = creation_state['step']
        responses = []
        
        if step == 0:
            responses.append(Dialog(
                "DM",
                "Welcome to character creation! I'll help you build your adventurer. "
                "First, what race calls to you? (Human, Elf, Dwarf, Halfling, etc.)",
                "narration"
            ))
        elif step == 1:
            responses.append(Dialog(
                "DM",
                f"Excellent choice! A {creation_state['character']['race']} adventurer. "
                "Now, what class suits your character? (Fighter, Wizard, Rogue, Cleric, etc.)",
                "narration"
            ))
        elif step == 2:
            responses.append(Dialog(
                "DM",
                f"A {creation_state['character']['class']} - a fine profession! "
                "What background shaped your character? (Noble, Urchin, Soldier, Sage, etc.)",
                "narration"
            ))
        elif step == 3:
            responses.append(Dialog(
                "DM",
                f"Ah, a {creation_state['character']['background']} background - that explains much. "
                "How would you describe your character's personality? (Brave, Cunning, Stoic, etc.)",
                "narration"
            ))
        elif step == 4:
            responses.append(Dialog(
                "DM",
                f"{creation_state['character']['personality']} - I can see that. "
                "What ideals drive your character? (Justice, Freedom, Knowledge, etc.)",
                "narration"
            ))
        elif step == 5:
            responses.append(Dialog(
                "DM",
                f"{creation_state['character']['ideals']} - noble aspirations! "
                "What bonds connect your character to the world? (Family, Oath, Lost homeland, etc.)",
                "narration"
            ))
        elif step == 6:
            responses.append(Dialog(
                "DM",
                f"{creation_state['character']['bonds']} - powerful motivations! "
                "Finally, what flaws or weaknesses does your character have? (Pride, Fear, Addiction, etc.)",
                "narration"
            ))
        elif step == 7:  # Completion
            # Create character
            character = self._create_character(creation_state['character'])
            responses.append(Dialog(
                "DM",
                f"Magnificent! {character['name']} is ready for adventure. "
                f"Here are your details:\n"
                f"Race: {character['race']}\n"
                f"Class: {character['class']}\n"
                f"Background: {character['background']}\n"
                f"Personality: {character['personality']}\n"
                f"Ideals: {character['ideals']}\n"
                f"Bonds: {character['bonds']}\n"
                f"Flaws: {character['flaws']}\n\n"
                "Your journey begins now!",
                "narration"
            ))
            
            # Show character card
            responses.append(Dialog(
                "System",
                f"CHARACTER_CARD:{json.dumps(character)}",
                "system"
            ))
            
            # Reset state
            creation_state = {'step': 0, 'character': {}}
            
        # Add to dialog history
        if message:
            responses.insert(0, Dialog(
                self.characters[player_id].name if player_id in self.characters else "Player",
                message,
                "character"
            ))
        
        return {
            "responses": [r.to_dict() for r in responses],
            "new_state": creation_state
        }

    
    def _create_character(self, char_data):
        """Finalize character creation"""
        # Generate missing details
        char_data['id'] = f"char_{uuid.uuid4().hex[:6]}"
        char_data['name'] = self.generate_character_name(
            char_data['race'], 
            char_data['class']
        )
        char_data['hit_points'] = self.calculate_starting_hp(char_data['class'])
        char_data['max_hp'] = char_data['hit_points']
        char_data['abilities'] = self.generate_abilities(
            char_data['race'], 
            char_data['class']
        )
        char_data['avatar_url'] = "/static/images/default_avatar.png"
        
        # Save character
        self.world.add_character(char_data)
        return char_data
    
    def generate_character_name(self, race, cls):
        name_parts = {
            "human": ["James", "Sarah", "Robert", "Emily"],
            "elf": ["Aerindel", "Lyra", "Thalorin", "Faelar"],
            "dwarf": ["Thorin", "Borin", "Dvalin", "Hilda"],
            "halfling": ["Bilbo", "Pippin", "Merry", "Rosie"],
            "dragonborn": ["Draxx", "Sithrak", "Vermithrax", "Tiamat"]
        }
        first = random.choice(name_parts.get(race.lower(), ["Unknown"]))
        last = f"{race} {cls}"
        return f"{first} {last}"
    
    def calculate_starting_hp(self, cls):
        base_hp = {
            "fighter": 10, "paladin": 10, "ranger": 10,
            "wizard": 6, "sorcerer": 6, "bard": 8,
            "cleric": 8, "druid": 8, "rogue": 8
        }
        return base_hp.get(cls.lower(), 8) + random.randint(1, 4)
    
    def generate_abilities(self, race, cls):
        abilities = ["strength", "dexterity", "constitution", 
                    "intelligence", "wisdom", "charisma"]
        scores = {ab: random.randint(8, 15) for ab in abilities}
        
        # Racial bonuses
        race = race.lower()
        if race == "elf":
            scores["dexterity"] += 2
        elif race == "dwarf":
            scores["constitution"] += 2
        elif race == "halfling":
            scores["dexterity"] += 2
        elif race == "dragonborn":
            scores["strength"] += 2
            scores["charisma"] += 1
        
        # Class bonuses
        cls = cls.lower()
        if cls == "wizard":
            scores["intelligence"] += 1
        elif cls == "fighter":
            scores["strength"] += 1
        elif cls == "rogue":
            scores["dexterity"] += 1
        elif cls == "cleric":
            scores["wisdom"] += 1
        
        return scores


    
    def process_player_action(self, player_id: str, message: str):
        """Process player input through the AI Dungeon Master"""

        # If no DM system, return simple response
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

        # Analyze player motivation
        motivation = self.motivation.analyze_action(message, self.characters.get(player_id))

        # Map motivation to action type for pacing
        action_type_map = {
            "combat": "combat",
            "curiosity": "discovery", 
            "acquisition": "discovery",
            "social": "dialogue",
            "unknown": "dialogue"
        }
        pacing_action_type = action_type_map.get(motivation, "dialogue")
        
        # Update pacing based on action type
        self.pacing.on_player_action(pacing_action_type)
        
        # Log action for consequences
        self.consequences.log_action(message, motivation)
        
        # Update pacing
        self.pacing.update_pace(message)
        
        # Process through DM system
        dialogs = self.dm.process_player_input(player_id, message)
        
        # Extract responses
        responses = []
        for dialog in dialogs:
            responses.append({
                "speaker": dialog.speaker,
                "content": dialog.content,
                "type": dialog.dialog_type
            })

        # Apply gentle narrative guidance if needed
        guidance = self.guide.get_gentle_nudge({
            'action': message,
            'motivation': motivation,
            'pacing': self.pacing.current_pace
        })
        
        if guidance:
            responses.append({
                "speaker": "DM",
                "content": guidance,
                "type": "narration"
            })
        
        # Process consequences periodically
        if random.random() < 0.3:  # 30% chance to trigger consequences
            self.consequences.apply_delayed_consequences()
        
        return {
            "responses": responses,
            "dialog_history": [d.to_dict() for d in self.dm.get_dialog_history()],
            "motivation": motivation,
            "pacing": self.pacing.current_pace
        }
    
    def set_current_scene(self, scene_description: str):
        """Update the current scene for narrative context"""
        self.game_state.current_scene = scene_description
        self.dm.game_state.current_scene = scene_description