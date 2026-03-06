# ai/ai_boundary.py
"""
Strict AI boundary enforcing phase separation.
AI can only:
- Interpret intent (Interpretation Phase)
- Generate narration (Consequence Phase)
AI must NEVER:
- Mutate game state
- Roll dice or make authoritative decisions
- Hold references to game state
"""

from typing import Dict, Any, Optional

class AIBoundary:
    """Phase-compliant AI interface"""
    
    def __init__(self, ai_system):
        self.ai_system = ai_system
        
    # === INTERPRETATION PHASE METHODS ===
    
    def classify_intent(self, player_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify player intent for Interpretation Phase.
        
        Returns:
            {
                "intent": "move|attack|talk|inspect|etc",
                "confidence": 0.0-1.0,
                "target": "optional target",
                "parameters": {}
            }
        """
        prompt = f"""
        Classify player intent from natural language.
        
        Player says: "{player_input}"
        
        Game Context:
        - Current location: {context.get('location', 'unknown')}
        - Available actions: {context.get('available_actions', [])}
        - Recent events: {context.get('recent_events', [])}
        
        Return JSON with intent, confidence, target, and parameters.
        """
        
        try:
            result = self.ai_system.generate_structured_data(prompt, {
                "intent": "string",
                "confidence": "float",
                "target": "string",
                "parameters": "dict"
            })
            
            # Ensure confidence is bounded
            result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.5)))
            
            return result
            
        except Exception as e:
            # Fallback to keyword matching if AI fails
            return self._fallback_intent_classification(player_input)
            
    def _fallback_intent_classification(self, text: str) -> Dict[str, Any]:
        """Fallback intent classification without AI"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["move", "go", "travel", "walk", "head"]):
            intent = "move"
        elif any(word in text_lower for word in ["attack", "fight", "hit", "strike", "kill"]):
            intent = "attack"
        elif any(word in text_lower for word in ["talk", "speak", "ask", "say", "tell"]):
            intent = "talk"
        elif any(word in text_lower for word in ["look", "inspect", "examine", "check"]):
            intent = "inspect"
        elif any(word in text_lower for word in ["take", "get", "grab", "pick up"]):
            intent = "take"
        elif any(word in text_lower for word in ["use", "cast", "activate"]):
            intent = "use"
        else:
            intent = "unknown"
            
        return {
            "intent": intent,
            "confidence": 0.5,
            "target": "unknown",
            "parameters": {}
        }
        
    def disambiguate_intent(self, ambiguous_intent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to disambiguate when intent is unclear"""
        prompt = f"""
        Disambiguate player intent when multiple interpretations are possible.
        
        Initial intent: {ambiguous_intent}
        
        Context:
        - Game state: {context.get('game_state', {})}
        - Available options: {context.get('available_options', [])}
        
        Return the most likely specific intent.
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "intent": "string",
                "confidence": "float",
                "reasoning": "string"
            })
        except Exception as e:
            return ambiguous_intent
            
    # === CONSEQUENCE PHASE METHODS ===
    
    def generate_narration(self, event: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate narrative description for Consequence Phase"""
        prompt = f"""
        Generate narrative description for this game event.
        
        Event: {event.get('type', 'unknown')}
        Details: {event.get('details', {})}
        
        Context:
        - Location: {context.get('location', 'unknown')}
        - Characters involved: {context.get('characters', [])}
        - Campaign tone: {context.get('tone', 'adventurous')}
        
        Write 1-3 sentences in second person ("You see...") or third person.
        Be descriptive but concise.
        """
        
        try:
            narration = self.ai_system.generate_text(prompt)
            # Clean up the narration
            narration = narration.strip()
            if narration.startswith('"') and narration.endswith('"'):
                narration = narration[1:-1]
            return narration
        except Exception as e:
            return f"{event.get('type', 'Something')} happens."
            
    def describe_location(self, location_data: Dict[str, Any]) -> str:
        """Generate location description for Consequence Phase"""
        prompt = f"""
        Describe this location in vivid detail.
        
        Location: {location_data.get('name', 'Unknown')}
        Type: {location_data.get('type', 'unknown')}
        Features: {location_data.get('features', [])}
        Atmosphere: {location_data.get('atmosphere', 'mysterious')}
        
        Write 2-3 sentences that set the scene for players.
        """
        
        try:
            return self.ai_system.generate_text(prompt)
        except Exception as e:
            return f"You are at {location_data.get('name', 'a location')}."
            
    def generate_dialogue_response(self, npc_data: Dict[str, Any], player_input: str) -> str:
        """Generate NPC dialogue response for Consequence Phase"""
        prompt = f"""
        Generate NPC dialogue response.
        
        NPC: {npc_data.get('name', 'Someone')}
        Personality: {npc_data.get('personality', 'neutral')}
        Current mood: {npc_data.get('mood', 'neutral')}
        
        Player says: "{player_input}"
        
        Write the NPC's response in first person.
        """
        
        try:
            response = self.ai_system.generate_text(prompt)
            return response.strip()
        except Exception as e:
            return "I have nothing to say about that."
            
    # === FORBIDDEN METHODS (These should not exist) ===
    # We explicitly do NOT implement:
    # - mutate_game_state()
    # - roll_dice()
    # - validate_action()
    # - assign_rewards()
    # - any method that changes game state or makes authoritative decisions
    
    def validate_phase_compliance(self) -> bool:
        """Check that this boundary doesn't violate phase rules"""
        forbidden_methods = [
            'mutate',
            'roll',
            'validate',
            'assign',
            'decide',
            'update_state',
            'apply',
            'set_'
        ]
        
        # Check all methods don't contain forbidden words
        for method_name in dir(self):
            if any(forbidden in method_name.lower() for forbidden in forbidden_methods):
                if callable(getattr(self, method_name)):
                    return False
                    
        return True