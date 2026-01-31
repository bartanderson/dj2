# world/dm_chat_ai.py
"""
DM Chat AI Boundary - AI methods for DM conversation
Phase: Interpretation (intent analysis) and Consequence (narration)
"""

from typing import Dict, Any, Optional, List
from ai.ai_boundary import AIBoundary
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DMChatAI(AIBoundary):
    """AI boundary for DM conversation interactions"""
    
    def __init__(self, ai_system):
        super().__init__(ai_system)
        
    def classify_intent(self, player_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify player intent specifically for DM conversation
        Override base method with DM-specific intents
        """
        prompt = f"""
        Classify player intent from natural language in a D&D conversation.
        
        Player says: "{player_input}"
        
        Conversation Context:
        - Recent topics: {context.get('recent_topics', [])}
        - Character creation state: {context.get('creation_state', 'not_started')}
        - Awaiting confirmation: {context.get('awaiting_confirmation', False)}
        
        DM-Specific Intent Categories:
        1. character_creation - Discussing character options, classes, races, backgrounds
        2. world_inquiry - Questions about the game world, lore, or story
        3. action_request - Attempting to perform an in-game action
        4. meta_dialogue - Questions about our conversation (summarize, recap, what did you ask)
        5. rules_question - Questions about game rules or mechanics
        6. narrative_input - Contributing to story or describing character actions
        7. confirmation - Yes/no or confirming choices
        8. clarification - Asking for more information or clarification
        
        Return JSON with intent, confidence, target, and parameters.
        """
        
        try:
            result = self.ai_system.generate_structured_data(prompt, {
                "intent": "string",
                "confidence": "float",
                "target": "string",
                "parameters": "dict",
                "reasoning": "string"
            })
            
            # Ensure confidence is bounded
            result["confidence"] = max(0.0, min(1.0, result.get("confidence", 0.5)))
            
            return result
            
        except Exception as e:
            # Fallback to simpler classification
            return self._fallback_dm_intent_classification(player_input)
    
    def _fallback_dm_intent_classification(self, text: str) -> Dict[str, Any]:
        """Fallback intent classification for DM chat"""
        text_lower = text.lower()
        
        # DM-specific keyword matching
        if any(word in text_lower for word in ["character", "create", "race", "class", "background"]):
            intent = "character_creation"
        elif any(word in text_lower for word in ["what is", "tell me about", "explain", "how does"]):
            intent = "world_inquiry"
        elif any(word in text_lower for word in ["i want to", "i try to", "attempt", "roll"]):
            intent = "action_request"
        elif any(word in text_lower for word in ["summarize", "recap", "what did we", "previous"]):
            intent = "meta_dialogue"
        elif any(word in text_lower for word in ["rule", "mechanic", "how to", "can i"]):
            intent = "rules_question"
        elif any(word in text_lower for word in ["yes", "no", "confirm", "agree", "disagree"]):
            intent = "confirmation"
        elif "?" in text_lower:
            intent = "clarification"
        else:
            intent = "narrative_input"
            
        return {
            "intent": intent,
            "confidence": 0.5,
            "target": "unknown",
            "parameters": {},
            "reasoning": "Fallback keyword matching"
        }
    
    def extract_character_data(self, message: str, existing_data: Dict = None) -> Dict[str, Any]:
        """Extract character creation information from natural language"""
        prompt = f"""
        Extract character creation information from this message:
        "{message}"
        
        Existing data: {json.dumps(existing_data) if existing_data else 'None'}
        
        Extract any mentioned: name, race, class, background, personality, fears, motivations, skills.
        Return as JSON with the extracted information.
        For missing fields, use null.
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "name": "string",
                "race": "string",
                "class": "string",
                "background": "string",
                "personality": "string",
                "fears": "string",
                "motivations": "string",
                "skills": "string"
            })
        except Exception as e:
            print(f"AI character data extraction failed: {e}")
            return {}
    
    def suggest_character_class(self, character_concept: str, existing_data: Dict = None) -> Dict[str, Any]:
        """Suggest appropriate character class based on concept"""
        prompt = f"""
        Based on this character concept, suggest the most appropriate D&D 5e class:
        
        CONCEPT: "{character_concept}"
        EXISTING DATA: {json.dumps(existing_data) if existing_data else 'None'}
        
        Consider:
        - Combat style preferences
        - Magic vs non-magic orientation
        - Role in a party
        - Alignment with character background
        
        Return JSON with:
        - primary_class: The most appropriate standard D&D class
        - secondary_class: An optional multiclass suggestion if appropriate
        - explanation: Brief reasoning for the choice
        - custom_traits: Any special traits that don't fit standard classes
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "primary_class": "string",
                "secondary_class": "string",
                "explanation": "string",
                "custom_traits": "list"
            })
        except Exception as e:
            print(f"AI class suggestion failed: {e}")
            return {
                "primary_class": "fighter",
                "secondary_class": "",
                "explanation": "Fallback suggestion",
                "custom_traits": []
            }
    
    def suggest_next_question(self, character_data: Dict, conversation_context: str = "") -> Dict[str, Any]:
        """Suggest the next question to ask in character creation"""
        prompt = f"""
        Based on this partial character data and conversation, 
        determine the single most important question to ask to move character creation forward:
        
        CHARACTER DATA: {json.dumps(character_data)}
        CONVERSATION CONTEXT: {conversation_context}
        
        Consider:
        - What essential information is still missing?
        - What would provide the most clarity for class selection?
        - What aspects need refinement?
        - Avoid asking about things already discussed
        
        Return JSON with:
        - question: The single most important question to ask
        - priority: High/Medium/Low indicating how essential this question is
        - category: race/class/background/personality/abilities/etc.
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "question": "string",
                "priority": "string",
                "category": "string"
            })
        except Exception as e:
            print(f"AI next question suggestion failed: {e}")
            return {
                "question": "What race would you like your character to be?",
                "priority": "Medium",
                "category": "race"
            }
    
    def interpret_confirmation(self, message: str, context: Dict) -> Dict[str, Any]:
        """Interpret if a message is confirmation, correction, or neither"""
        prompt = f"""
        Determine if this message is a confirmation, correction, or neither:
        "{message}"
        
        Context: {json.dumps(context)}
        
        Return JSON with:
        - is_confirmation: true/false
        - corrected_value: if it's a correction, what's the new value (null if not)
        - confidence: 0-1 confidence in the assessment
        - interpretation: brief explanation of your interpretation
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "is_confirmation": "boolean",
                "corrected_value": "string",
                "confidence": "float",
                "interpretation": "string"
            })
        except Exception as e:
            print(f"AI confirmation interpretation failed: {e}")
            return {
                "is_confirmation": False,
                "corrected_value": None,
                "confidence": 0.5,
                "interpretation": "Could not interpret"
            }
    
    def generate_meta_response(self, message: str, recent_topics: List[str]) -> str:
        """Generate response to meta-questions about the conversation"""
        prompt = f"""
        You're a Dungeon Master handling a player's request about your conversation.
        
        PLAYER REQUEST: "{message}"
        RECENT TOPICS DISCUSSED: {recent_topics}
        
        Provide a helpful, specific response that references the actual topics we've been discussing.
        Mention 2-3 of the most recent specific topics, not generic categories.
        Keep your response conversational and natural.
        
        Example good response: "We've been talking about shadow magic, rogue classes, 
        and your character's background as a thief from a small town. Would you like me to focus on any of these?"
        
        Response:
        """
        
        try:
            response = self.ai_system.generate_text(prompt)
            return response.strip()
        except Exception as e:
            print(f"AI meta-response generation failed: {e}")
            if recent_topics:
                return f"We've recently discussed: {', '.join(recent_topics[-3:])}. Would you like to focus on any of these aspects?"
            return "We've been discussing character creation options. What would you like to focus on?"
    
    def generate_character_narration(self, character_data: Dict, action: str = "created") -> str:
        """Generate narrative description for character events"""
        prompt = f"""
        Generate narrative description for character {action}:
        
        CHARACTER: {json.dumps(character_data)}
        
        Write 1-2 sentences in second person ("Your character...") that vividly describe 
        this character coming into existence or taking action in the world.
        """
        
        try:
            narration = self.ai_system.generate_text(prompt)
            return narration.strip()
        except Exception as e:
            print(f"AI character narration failed: {e}")
            return f"Your character has been {action}."
    
    def detect_action_intent(self, message: str, context: Dict) -> Dict[str, Any]:
        """Detect if message requires game action/tool execution"""
        prompt = f"""
        Determine if this player message requires executing a game mechanic/tool.
        
        PLAYER MESSAGE: "{message}"
        CONTEXT: {json.dumps(context)}
        
        Consider:
        - Character creation actions (selecting options, making choices) may need tools
        - In-game actions (combat, exploration, social) typically need tools
        - Questions about options or lore typically don't need tools
        
        Return JSON:
        - requires_action: true/false
        - action_type: character_creation/world_action/combat/etc. or null
        - reason: Brief explanation
        """
        
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "requires_action": "boolean",
                "action_type": "string",
                "reason": "string"
            })
        except Exception as e:
            print(f"AI action detection failed: {e}")
            return {
                "requires_action": False,
                "action_type": None,
                "reason": "AI detection failed"
            }

    def generate_embedding(self, text):
        """Generate text embedding using the AI system"""
        try:
            return self.ai_system.generate_embedding(text)
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return None

    def extract_conversation_context(self, conversation_text: str) -> Dict[str, Any]:
        """
        Extract structured context from conversation text.
        AI Boundary method - handles conversation context extraction for phase compliance.
        """
        prompt = f"""
        Analyze this conversation excerpt and extract key information:
        
        CONVERSATION:
        {conversation_text}
        
        Extract the following information as JSON:
        - topics_discussed: List of 3-5 main topics covered
        - last_questions: List of 1-3 recent questions asked by the DM
        - current_focus: What the conversation is currently focused on
        
        Respond with JSON: {{
            "topics_discussed": ["topic1", "topic2", ...],
            "last_questions": ["question1", "question2", ...],
            "current_focus": "brief description of current focus"
        }}
        """
        
        try:
            response_format = {
                "topics_discussed": "list",
                "last_questions": "list",
                "current_focus": "string"
            }
            context = self.ai_system.generate_structured_data(prompt, response_format)
            return context
        except Exception as e:
            print(f"AI context extraction failed: {e}")
            return {"topics_discussed": [], "last_questions": [], "current_focus": "character creation"}