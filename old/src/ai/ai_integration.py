# ai_integration.py - Core AI orchestration
class AIDungeonMaster:
    def __init__(self, game_state):
        self.game_state = game_state
        self.agent = EnhancedDMAgent(game_state)
        self.campaign_journal = ""
        
    def initialize_campaign(self, campaign_theme, party_info):
        """Set up new campaign with AI-generated content"""
        self.campaign_journal = self.generate_opening_narrative(campaign_theme, party_info)
        
        # Generate starting dungeon
        dungeon_params = self.generate_dungeon_parameters(campaign_theme)
        self.game_state.initialize_dungeon(**dungeon_params)
        
        # Create initial NPCs
        self.create_initial_npcs(party_info['location'])
        
        # Generate starting quest
        self.generate_starting_quest(party_info)
        
    def generate_opening_narrative(self, theme, party_info) -> str:
        """Generate campaign opening with AI"""
        party_desc = ", ".join([f"{c['name']} the {c['class']}" for c in party_info['members']])
        prompt = (
            f"Create an engaging opening narrative for a {theme} D&D campaign. "
            f"Party members: {party_desc}. Start in {party_info['location']}. "
            "Include a hook for adventure."
        )
        return self.agent.model.invoke(prompt)
    
    def process_player_input(self, player_id, input_text):
        """Main processing pipeline for player input"""
        # Update game state context
        context = {
            "campaign_journal": self.campaign_journal,
            "party_status": self.get_party_status(),
            "current_situation": self.get_current_situation(),
            "recent_events": "\n".join(self.game_state.game_log[-3:])
        }
        
        # Process command through agent
        response = self.agent.process_command(input_text, player_id, context)
        
        # Handle AI-generated actions
        if response.get("hidden_actions"):
            self.execute_hidden_actions(response["hidden_actions"])
            
        # Update campaign journal
        self.update_journal(response["narrative"])
        
        return response
    
    def execute_hidden_actions(self, actions):
        """Process hidden actions from AI response"""
        for action in actions:
            action_type = action["type"]
            if action_type == "reveal_secret":
                self.game_state.dungeon_state.reveal_secrets(action["target"])
            elif action_type == "trigger_trap":
                self.trigger_trap(action["target"])
            elif action_type == "npc_reaction":
                self.handle_npc_reaction(action["npc_id"], action["reaction"])
    
    def generate_dynamic_encounter(self):
        """Create context-appropriate encounter"""
        party_level = max(c.level for c in self.game_state.characters.values())
        location_type = self.get_current_environment()
        
        prompt = (
            f"Design an appropriate encounter for level {party_level} party "
            f"in a {location_type} area. Include environment, monsters, and special conditions."
        )
        encounter_design = self.agent.model.invoke(prompt)
        
        # Parse and implement encounter
        return self.implement_encounter_design(encounter_design)