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
        - Recent dialogs: {context.get('recent_dialogs', [])}
        - Character creation state: {context.get('creation_state', 'not_started')}
        - Awaiting confirmation: {context.get('awaiting_confirmation', False)}
        
        DM-Specific Intent Categories:
        1. character_creation - Statements or questions that are about starting or proceeding with character creation, such as "I want to make a character", "Let's create a new character". NOT for questions about game rules or lore, even if related to character options.
        2. world_inquiry - Questions about the game world, lore, or story. This includes any expression of desire to learn about aspects of the world, such as "I want to explore magic", "Tell me about dragons", "What kinds of magic exist?", "I'm curious about elves", etc.
        3. action_request - Attempting to perform an in-game action.
        4. meta_dialogue - Questions about our conversation (summarize, recap, what did you ask).
        5. rules_question - Questions about game rules or mechanics, such as "How does magic work?" or "Can any class use magic?"
        6. narrative_input - Contributing to story or describing character actions.
        7. confirmation - Yes/no or confirming choices.
        8. clarification - Asking for more information or clarification.
        9. seeking_guidance - Asking for help, suggestions, or recommendations ("what should I do?", "help me decide").
        10. declare_intent - Explicitly stating a character choice ("I want to be a wizard", "My character is an elf").
        11. describe_character - Describing the character's personality, background, or appearance.
        12. make_choice - Making a specific decision (selecting equipment, ability scores, etc.).
        
        Important: If the player is asking a question about how something works (e.g., magic, classes), use rules_question or world_inquiry, NOT character_creation. Character_creation is only for meta statements about the process itself.
        
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

    # DEPRECATED: Will be removed when AI is reliable enough to always succeed.    
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
        elif any(word in text_lower for word in ["help", "suggest", "recommend", "what should", "any ideas"]):
            intent = "seeking_guidance"
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

    def extract_action_parameters(self, message: str, intent: str) -> Dict[str, Any]:
        """
        Extract structured parameters for a given intent from the message.
        For example, for an action_request, extract the action verb and target.
        """
        prompt = f"""
        Extract structured parameters from this player message for intent "{intent}".
        
        Message: "{message}"
        
        Return a JSON object with relevant parameters. For an action_request, include
        "action" (the action verb), "target" (optional), "details" (any additional info).
        For character_creation, you can call extract_character_data instead.
        """
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "parameters": "dict"
            }).get("parameters", {})
        except Exception:
            return {}
    
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
        """Suggest appropriate character class based on concept and existing data"""
        # Build a rich concept from existing data
        concept_parts = []
        if existing_data:
            if existing_data.get('race'):
                concept_parts.append(f"Race: {existing_data['race']}")
            if existing_data.get('background'):
                concept_parts.append(f"Background: {existing_data['background']}")
            if existing_data.get('personality'):
                concept_parts.append(f"Personality: {existing_data['personality']}")
            if existing_data.get('motivations'):
                concept_parts.append(f"Motivations: {existing_data['motivations']}")
            if existing_data.get('skills'):
                concept_parts.append(f"Skills: {existing_data['skills']}")
        if character_concept:
            concept_parts.append(f"Desired class/concept: {character_concept}")
        rich_concept = "\n".join(concept_parts) if concept_parts else "No details provided yet."

        prompt = f"""
        Based on this character concept, suggest the most appropriate D&D 5e class:
        
        CONCEPT: {rich_concept}
        
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
    
    def suggest_guidance(self, character_data: Dict, conversation_context: str = "") -> Dict[str, Any]:
        """Suggest a gentle next direction when the player asks for help."""
        prompt = f"""
        Based on what we know so far about the player's character, suggest a gentle, open‑ended question or topic to explore.
        CHARACTER DATA: {json.dumps(character_data)}
        CONVERSATION CONTEXT: {conversation_context}
        
        Do NOT interrogate. Instead, offer an interesting possibility or ask what aspect they'd like to learn more about.
        Examples:
        - "You've mentioned an interest in magic. Would you like to hear about the different magical traditions in this world?"
        - "Elves are known for their grace and long lives. Does that resonate with your idea?"
        - "We haven't talked about your character's background yet. Were they a soldier, a scholar, or something else entirely?"
        
        Return JSON with:
        - question: The suggestion or question
        - category: The general area (e.g., race, class, background, etc.)
        """
        try:
            return self.ai_system.generate_structured_data(prompt, {
                "question": "string",
                "category": "string"
            })
        except Exception as e:
            print(f"Guidance suggestion failed: {e}")
            return {
                "question": "What part of your character would you like to explore next?",
                "category": "general"
            }

    def interpret_confirmation(self, message: str, context: Dict) -> Dict[str, Any]:
        """Interpret if a message is confirmation, correction, or neither"""
        prompt = f"""
        Determine if this message is a confirmation, correction (offering a different class), or neither.
        "{message}"
        
        Context: The player was asked to confirm a suggested character class: {context.get('suggested_class', 'unknown')}
        
        Return JSON with:
        - is_confirmation: true if they agree (yes, sure, okay, that works, etc.)
        - corrected_value: if they offer a different class, extract the class name (e.g., "I'd rather be a wizard" → "wizard")
        - confidence: 0-1 confidence in the assessment
        - interpretation: brief explanation
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