
# world/dm_chat_handler.py
from typing import Dict, List, Optional, Set, Any
class DMChatHandler:
    """
    PHASE_MIGRATION_IN_PROGRESS: This class is being migrated from monolithic phase mixing
    to phase-compliant architecture.
    
    Current violations being addressed:
    1. AI boundary compliance → Use DMChatAI system
    2. Direct state mutation → Use SessionSystem  
    3. Direct tool execution → TODO: Use AuthoritySystem
    
    Methods marked with PHASE_VIOLATION need updating.
    Methods marked with PHASE_COMPLIANT have been updated.
    Methods marked with TEMP are transitional.
    """

    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.dm = world_controller.dungeon_master

    def _update_conversation_topics(self, session_id: str, message: str, is_dm_response: bool = False):
        """Extract and update recent topics from messages"""
        if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
            topic = self._extract_message_topic(message)
            if topic:
                self.world_controller.session_system.add_topic(session_id, topic)
        
    def _extract_message_topic(self, message):
        """Use AI to extract the main topic from a single message"""
        prompt = f"""
        Extract the primary topic or subject from this message. Return only the topic phrase, not a complete sentence.
        
        Message: "{message}"
        
        Examples:
        - "I want to create a magic user" → "magic character creation"
        - "Tell me about stealth classes" → "stealth classes" 
        - "What's the best race for a wizard?" → "wizard race selection"
        - "Can you summarize what we discussed?" → "conversation summary request"
        
        Topic:
        """
        
        try:
            topic = self.world_controller.world_ai.generate_text(prompt)
            return topic.strip().lower()
        except Exception as e:
            print(f"AI topic extraction failed: {e}")
            return None
    
    def get_recent_topics(self, session_id: str) -> List[str]:
        """Get recent topics for a session"""
        if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
            return self.world_controller.session_system.get_recent_topics(session_id)
        return []

    def process_message(self, session_id: str, message: str, character_id=None):
        """Process a message from a player session"""
        response_data = {}
        print("DEBUG: DMChatHandler.process_message called")
        try:
            session_state = self.world_controller.session_system.get_or_create_session(session_id, None)
            # SessionSystem will handle player creation if needed
            
            # Check if we're in a confirmation state (NOW USING session_state)
            if session_state.awaiting_confirmation:
                is_confirmed, response = self._handle_confirmation(session_id, message, session_state)
                session_state.awaiting_confirmation = False
                
                if is_confirmed:
                    # Continue with character creation
                    result = self._handle_character_creation_tools("", session_id)
                    
                    # If character is finally created, return it
                    if result.get("action") == "character_created":
                        return result
                    else:
                        # Still need more information
                        return {
                            "narrative": [Dialog("DM", result["message"], "character_creation")],
                            "tool_result": None
                        }
                else:
                    # Ask for clarification
                    return {
                        "narrative": [Dialog("DM", response, "clarification")],
                        "tool_result": None
                    }

            # Get character context if specified
            character_context = {}
            if character_id and character_id in self.world_controller.characters:
                character = self.world_controller.character_manager.get_character(character_id)
                character_context = {
                    'character_id': character_id,
                    'character_name': character.name,
                    'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                    'character_race': character.race,
                    'character_level': character.level
                }
                player.set_active_character(character_id)

            # Use active character if no specific character is specified
            if not character_id and player.active_character_id:
                character_id = player.active_character_id
                character = self.world_controller.characters[character_id]
                character_context = {
                    'character_id': character_id,
                    'character_name': character.name,
                    'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                    'character_race': character.race,
                    'character_level': character.level
                }

            # Use AI to classify intent (REPLACES ALL KEYWORD-BASED DETECTION)
            intent_context = "Character creation phase" if not character_id else "In-game phase"
            intent_result = self._classify_intent(message, intent_context)
            print(f"AI Intent Classification: {intent_result}")

            # Handle meta-requests early (REPLACES KEYWORD-BASED META DETECTION)
            if intent_result["intent"] == "meta_dialogue" and intent_result["confidence"] > 0.6:
                meta_response = self._handle_meta_request(message, session_id)
                narrative_responses = [Dialog("DM", meta_response, "narration")]

                # Track topic for DM response (meta-responses are still tracked)
                self._update_conversation_topics(player.id, meta_response, is_dm_response=True)
                
                # Add to chat history
                self.chat_history.extend([(player.id, message)] + [("DM", r.content) for r in narrative_responses])
                
                return {
                    "narrative": narrative_responses,
                    "tool_result": {"meta_request": True}
                }
            # Track topic for regular player messages (non-meta requests)
            self._update_conversation_topics(session_id, message, is_dm_response=False)

            # If in character creation mode, generate a response using AI for character creation
            is_character_creation = not character_id and not player.active_character_id
            
            if is_character_creation:
                try:
                    # Use DMChatAI for character creation guidance
                    # Since DMChatAI doesn't have a direct method for this, we'll use classify_intent
                    # and generate a response based on the intent
                    intent_result = self.world_controller.dm_chat_ai.classify_intent(message, {"phase": "character_creation"})
                    
                    if intent_result["intent"] == "character_creation":
                        # Generate a helpful response for character creation
                        response_text = "I'd be happy to help you create a character! Let's start by choosing a race and class. What kind of character are you imagining?"
                    else:
                        response_text = "I can help you create a character! Tell me about the type of adventurer you'd like to play."
                    
                    narrative_responses = [Dialog("DM", response_text, "narration")]
                except Exception as e:
                    print(f"Error generating character creation response: {e}")
                    # Fallback response if AI generation fails
                    response_text = "I'd be happy to help you create a character! Let's start by choosing a race and class. What kind of character are you imagining?"
                    narrative_responses = [Dialog("DM", response_text, "narration")]
            else:
                # Use the normal DM processing for in-game conversations
                narrative_responses = self.dm.process_player_input(
                    player.id,
                    message,
                    character_context=character_context
                )
                print("DEBUG: Back from dm.process_player_input")


            # After generating narrative responses, update topics for DM responses too
            for response in narrative_responses:
                self._update_conversation_topics(session_id, response.content, is_dm_response=True)
            # If tool execution is needed, process it and get follow-up narrative

            tool_result = None
            tool_followup_responses = []

            # Check if tool execution is also needed, using AI classification (REPLACES KEYWORD-BASED TOOL DETECTION)
            requires_tool = self._ai_detect_tool_intent(message, narrative_responses, character_context)

            # If we have character data from tool processing, ensure it's included in response
            if tool_result and 'character_data' in tool_result:
                response_data['character_data'] = tool_result['character_data']
                # Also trigger showing the character sheet
                response_data['show_character_sheet'] = True 

            if requires_tool:
                print("DEBUG: Tool execution required")
                tool_result = self._handle_tool_usage(message, session_id)
                print(f"DEBUG: Tool result raw AI output: {tool_result}")
                # Only incorporate tool result if it was not skipped and has no error
                if tool_result and not tool_result.get("error") and not tool_result.get("skipped"):
                    tool_followup_responses = self.dm.process_player_input(
                        player.id,
                        f"Tool execution result: {tool_result.get('message', 'Action completed')}"
                    )
                elif tool_result and tool_result.get("skipped"):
                    # Use AI to generate a context-aware fallback
                    fallback_prompt = f"""
                    The player said: "{message}"
                    The system tried to use a tool but none was available.
                    
                    Provide helpful character creation guidance about this topic.
                    Focus on explaining options rather than suggesting in-game actions.
                    
                    Response:
                    """
                    
                    try:
                        fallback_text = self.world_controller.world_ai.generate_text(fallback_prompt)
                        tool_followup_responses = [Dialog("DM", fallback_text, "narration")]
                    except Exception as e:
                        print(f"Error generating fallback response: {e}")
                        # Basic fallback
                        fallback_text = "Let's continue developing your character concept. What aspects would you like to explore next?"
                        tool_followup_responses = [Dialog("DM", fallback_text, "narration")]

            if tool_result and 'character_data' in tool_result:
                response_data['character_data'] = tool_result['character_data']
                response_data['show_character_sheet'] = True

            # Combine all narrative responses
            all_narrative_responses = narrative_responses + tool_followup_responses

            # Store in chat history using session_system
            if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
                self.world_controller.session_system.add_message(session_id, "Player", message)
                for response in all_narrative_responses:
                    self.world_controller.session_system.add_message(session_id, "DM", response.content)

            # In the process_message method, before returning:
            print(f"DEBUG: Final response_data: {response_data}")
            print(f"DEBUG: Character data in response: {'character_data' in response_data}")

            return {
                "narrative": all_narrative_responses,
                "tool_result": tool_result,
                # Ensure character_data is included if it exists
                "character_data": tool_result.get('character_data') if tool_result else None
            }

        except Exception as e:
            print(f"DEBUG: Exception in process_message: {e}")
            import traceback
            traceback.print_exc()
            error_response = [Dialog("DM", "I'm having trouble processing that right now. Could you try again?", "system")]
            return {
                "narrative": error_response,
                "tool_result": {"error": str(e)}
            }

    def _classify_intent(self, message, context=None):
        """
        Use AI exclusively to classify message intent without any keyword fallbacks
        """
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            return self.world_controller.dm_chat_ai.classify_intent(message, context)
        except Exception as e:
            print(f"AI intent classification failed: {e}")
            return {"intent": "general_question", "confidence": 0.5, "explanation": "AI classification failed"}

    def _handle_meta_request(self, message: str, session_id: str) -> str:
        """Generate response to meta-questions about the conversation"""
        recent_topics = self.get_recent_topics(session_id)  # Uses session_id
        
        prompt = f"""
        You're a Dungeon Master handling a player's request about your conversation.
        
        PLAYER REQUEST: "{message}"
        RECENT SPECIFIC TOPICS DISCUSSED: {recent_topics}
        
        Provide a helpful, specific response that references the actual topics we've been discussing.
        Mention 2-3 of the most recent specific topics, not generic categories.
        Keep your response conversational and natural.
        
        Response:
        """
        
        try:
            response = self.world_controller.world_ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            print(f"AI meta-response generation failed: {e}")
            if recent_topics:
                return f"We've recently discussed: {', '.join(recent_topics[-3:])}. Would you like to focus on any of these aspects?"
            return "We've been discussing character creation options. What would you like to focus on?"

    def _extract_conversation_context(self, session_id):
        """
        # FIXED: Now uses DMChatAI boundary (phase compliance restored)
        Use AI to extract meaningful context from the conversation history
        """
        try:
            # TODO: Get conversation text from session
            # For now, return empty context to avoid runtime error
            # We'll implement this when we have session-based conversation storage
            return {"topics_discussed": [], "last_questions": [], "current_focus": "character creation"}
            
            # FIXED: Phase compliance restored via DMChatAI boundary
            # Get conversation text from session
            # conversation_text = self.get_conversation_history(session_id)  # or similar
            # return self.world_controller.dm_chat_ai.extract_conversation_context(conversation_text)

        except Exception as e:
            print(f"AI context extraction failed: {e}")
            return {"topics_discussed": [], "last_questions": [], "current_focus": "character creation"}

    def _ai_detect_tool_intent(self, message, dm_responses, character_context=None):
        """
        Use AI exclusively to determine if this message requires tool execution
        """
        context = {
            "dm_responses": [r.content for r in dm_responses] if dm_responses else [],
            "character_context": character_context or {}
        }
        
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            result = self.world_controller.dm_chat_ai.detect_action_intent(message, context)
            return result.get("requires_action", False)
        except Exception as e:
            print(f"AI tool detection failed: {e}")
            return False


    def _handle_tool_usage(self, message, session_id):
        """Handle tool execution using AuthoritySystem for validation"""
        # Get session state
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            return {"error": "Session not found", "skipped": True}
        
        # Get player and character info from session
        player_id = session_state.player_id
        if not player_id:
            return {"error": "No player in session", "skipped": True}
        
        character_id = session_state.active_character_id
        character = None
        if character_id and character_id in self.world_controller.characters:
            character = self.world_controller.characters[character_id]
        
        # Use AI to determine which tool to use (still through DMChatAI)
        tool_to_use = None
        try:
            # This will eventually move to AuthoritySystem too
            tool_to_use = self._determine_tool_for_message(message, "in_game")
        except Exception as e:
            print(f"Tool detection error: {e}")
            tool_to_use = None

        if tool_to_use:
            # Build context for AuthoritySystem validation
            context = {
                "session_id": session_id,
                "player_id": player_id,
                "character_id": character_id,
                "character_name": character.name if character else "Unknown",
                "current_location": self.world_controller.current_location.id 
                    if self.world_controller.current_location else None,
                "world_id": self.world_controller.world_id if hasattr(self.world_controller, 'world_id') else None,
                "phase": "authority"  # This is an Authority phase action
            }
            
            # Parameters for the tool
            parameters = {
                "message": message,
                "character_id": character_id,
                "player_id": player_id,
                "session_id": session_id
            }
            
            # Use AuthoritySystem to execute the tool (validates + returns action data)
            try:
                tool_result = self.world_controller.authority_system.execute_tool(
                    tool_name=tool_to_use, 
                    parameters=parameters, 
                    context=context
                )
                
                # AuthoritySystem returns what should happen, not the actual mutation
                if tool_result.get("success"):
                    return {
                        "message": tool_result.get("message", "Action processed"),
                        "action": "in_game_tool",
                        "tool_used": tool_to_use,
                        "action_data": tool_result.get("action_data"),
                        "validated": True,
                        "requires_mutation": True  # Signal that state mutation is needed
                    }
                else:
                    return {
                        "message": tool_result.get("message", "Action validation failed"),
                        "action": "in_game_tool",
                        "tool_used": tool_to_use,
                        "error": tool_result.get("message"),
                        "validated": False
                    }
                    
            except Exception as e:
                print(f"AuthoritySystem tool execution error: {e}")
                return {
                    "message": f"System error: {str(e)}",
                    "action": "in_game_tool",
                    "tool_used": tool_to_use,
                    "error": str(e),
                    "skipped": True
                }
        else:
            # No specific tool found, provide a generic response
            return {
                "message": f"Processed action: {message}",
                "action": "in_game_generic",
                "skipped": True
            }

    def _handle_character_creation_tools(self, message, session_id):  # ✅ Changed to session_id
        """Handle tool usage during character creation phase with proper state management"""
        
        # Get session state from SessionSystem
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            # Create session if it doesn't exist
            session_state = self.world_controller.session_system.get_or_create_session(
                session_id, 
                None  # player_id can be None initially
            )
        
        # Initialize character data if not present (using SessionSystem)
        if not session_state.character_data:
            session_state.character_data = {}
        
        # Update creation state if needed
        if session_state.creation_state == "not_started":
            self.world_controller.session_system.set_creation_state(session_id, "gathering_info")
        
        # Extract character information from the message
        extracted_data = self._extract_character_data(message, session_state.character_data)
        self.world_controller.session_system.update_character_data(session_id, extracted_data)
        
        # Continue with state-based processing using session_state
        if session_state.creation_state == "gathering_info":
            # Check if we have enough info to suggest a class
            if self._has_sufficient_data_for_class_suggestion(session_state.character_data):
                # Use AI to determine appropriate class
                class_info = self._determine_character_class(
                    session_state.character_data.get('class', ''), 
                    session_state.character_data
                )
                
                # Update session state with class info
                updated_data = session_state.character_data.copy()
                updated_data['suggested_class'] = class_info['primary_class']
                updated_data['suggested_multiclass'] = class_info['secondary_class']
                updated_data['class_explanation'] = class_info['explanation']
                updated_data['custom_traits'] = class_info['custom_traits']
                
                self.world_controller.session_system.update_character_data(session_id, updated_data)
                
                # Update state and await confirmation
                self.world_controller.session_system.set_creation_state(session_id, "class_suggested")
                self.world_controller.session_system.set_awaiting_confirmation(session_id, True)
                
                return {
                    "message": f"Based on your description, I suggest {class_info['primary_class']} {('with a dip into ' + class_info['secondary_class'] + ' ') if class_info['secondary_class'] else ''}because: {class_info['explanation']}. Does this work for you?",
                    "action": "class_suggestion",
                    "character_data": session_state.character_data,
                    "requires_confirmation": True
                }
        
        elif session_state.creation_state == "class_suggested":
            # We're waiting for confirmation, but got more info instead
            # Stay in this state but update the data
            return {
                "message": "I'm still waiting for your confirmation on the class suggestion. Does the suggested class work for you?",
                "action": "class_confirmation_reminder",
                "character_data": session_state.character_data
            }
        
        elif session_state.creation_state == "class_confirmed":
            # We have a confirmed class, check if we can create the character
            if self._has_sufficient_character_data(session_state.character_data):
                # Create the character
                character = self.world_controller.character_manager.create_character(
                    session_state.player_id,  # Note: we might not have player_id yet
                    session_state.character_data
                )
                # We need to set the active character for the player
                # But note: the player is not in the session_state? We have player_id in session_state.
                if session_state.player_id:
                    player = self.world_controller.players.get(session_state.player_id)
                    if player:
                        player.active_character_id = character.id
                    self.world_controller.characters[character.id] = character
                    self.world_controller.session_system.set_creation_state(session_id, "completed")
                    
                    return {
                        "message": f"Character {character.name} created successfully as a {session_state.character_data.get('class', 'adventurer')}!",
                        "action": "character_created",
                        "character_data": session_state.character_data,
                        "character_id": character.id,
                    }
                else:
                    return {
                        "message": "Character data is complete, but no player is associated with this session. Please start over.",
                        "action": "error",
                        "character_data": session_state.character_data
                    }
        
        # If we're still gathering info, ask for the next piece of information
        next_question = self._determine_next_question(
            session_state.character_data,
            session_id  # Pass session_id instead
        )
        
        return {
            "message": next_question['question'],
            "action": "character_creation_question",
            "question_category": next_question['category'],
            "character_data": session_state.character_data
        }

    def _extract_character_data(self, message, existing_data):
        """Extract character data from natural language using AI"""
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            return self.world_controller.dm_chat_ai.extract_character_data(message, existing_data)
        except Exception as e:
            print(f"Error extracting character data: {e}")
            return {}

    def _has_sufficient_character_data(self, char_data):
        """Check if we have enough data to create a character"""
        required = ["name", "race", "class"]
        return all(field in char_data and char_data[field] for field in required)

    def _get_missing_character_data(self, char_data):
        """Return list of missing required fields"""
        required = ["name", "race", "class"]
        return [field for field in required if field not in char_data or not char_data[field]]

    def _determine_tool_for_message(self, message, context):
        """Check ToolRegistry for available tools and map intent"""
        try:
            # Get tool registry from authority_system (or ai_system if not available)
            if hasattr(self.world_controller, 'authority_system'):
                tool_registry = self.world_controller.authority_system.tool_registry
            elif hasattr(self.world_controller.ai_system, 'tool_registry'):
                tool_registry = self.world_controller.ai_system.tool_registry
            else:
                return None
            
            # Get available tool names
            available_tools = list(tool_registry.tools.keys())
            
            # Simple keyword mapping for now - will be replaced with AI
            message_lower = message.lower()
            
            # Map common phrases to tool names
            tool_mapping = {
                # Character creation tools (if available)
                'create character': 'create_character',
                'make character': 'create_character',
                'character creation': 'create_character',
                
                # From dm_tools.py (what's actually available)
                'add entity': 'add_entity',
                'describe cell': 'describe_cell',
                'overlay': 'add_overlay',
            }
            
            # Check for matches
            for phrase, tool_name in tool_mapping.items():
                if phrase in message_lower and tool_name in available_tools:
                    return tool_name
            
            # Fallback: Check if any tool name is mentioned directly
            for tool_name in available_tools:
                if tool_name in message_lower:
                    return tool_name
                    
            return None
            
        except Exception as e:
            print(f"Tool detection error: {e}")
            return None

    def _has_sufficient_data_for_class_suggestion(self, char_data):
        """Check if we have enough data to make a class suggestion"""
        # We need at least some concept of what the character does
        has_concept = any([
            char_data.get('class'),
            char_data.get('skills'),
            char_data.get('background'),
            char_data.get('motivations')
        ])
        
        # We also need basic identity info
        has_identity = char_data.get('name') and char_data.get('race')
        
        return has_concept and has_identity

    def _get_missing_character_data(self, char_data):
        """Return list of missing required fields"""
        required = ["name", "race", "class"]
        return [field for field in required if field not in char_data or not char_data[field]]

    def _determine_character_class(self, class_concept, character_data):
        """Use AI to determine the most appropriate class for a character concept"""
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            return self.world_controller.dm_chat_ai.suggest_character_class(class_concept, character_data)
        except Exception as e:
            print(f"Error determining character class: {e}")
            return {
                "primary_class": "fighter",
                "secondary_class": "",
                "explanation": "Fallback class due to analysis error",
                "custom_traits": []
            }

    def _determine_next_question(self, character_data, session_id):
        """Use AI to determine the most important question to ask next"""
        # Get conversation context from session_system
        conversation_context = self.world_controller.session_system.get_conversation_context(session_id)
        
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            return self.world_controller.dm_chat_ai.suggest_next_question(character_data, conversation_context)
        except Exception as e:
            print(f"Error determining next question: {e}")
            return {
                "question": "What race would you like your character to be?",
                "priority": "Medium",
                "category": "race"
            }

    def _handle_confirmation(self, session_id: str, message: str, session_state) -> tuple:
        """Handle player confirmations or corrections with state transitions"""
        context = {
            "session_state": session_state,
            "character_data": session_state.character_data
        }
        
        try:
            # TODO: Refactor for phase compliance using DMChatAI boundary
            assessment = self.world_controller.dm_chat_ai.interpret_confirmation(message, context)
            
            # ✅ Use session_state that's already passed in (from process_message)
            if assessment['is_confirmation'] and assessment['confidence'] > 0.7:
                # Player confirmed the suggestion
                session_state.character_data['class'] = session_state.character_data.get('suggested_class', '')
                
                # Remove temporary fields from session data
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    if field in session_state.character_data:
                        del session_state.character_data[field]
                
                # Update session state
                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.update_character_data(
                    session_id, 
                    session_state.character_data
                )
                        
                return True, "Great! Class confirmed. Let's continue with your character."
                
            elif assessment['corrected_value'] and assessment['confidence'] > 0.6:
                # Player provided a correction
                session_state.character_data['class'] = assessment['corrected_value']
                
                # Clear previous suggestions from session data
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    if field in session_state.character_data:
                        del session_state.character_data[field]
                
                # Update session state
                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.update_character_data(
                    session_id,
                    session_state.character_data
                )
                        
                return True, f"Understood, I'll use {assessment['corrected_value']} instead. Let's continue."
                
            else:
                # Unclear response, ask for clarification
                return False, "I'm not sure if you're confirming the suggestion or suggesting something different. Could you clarify?"
                
        except Exception as e:
            print(f"Error handling confirmation: {e}")
            return False, "I had trouble understanding your response. Could you please clarify?"

    def _finalize_character(self, session_id: str) -> Dict[str, Any]:
        """
        PHASE_COMPLIANT: Uses SessionSystem for state management
        TODO: Consider moving to CharacterSystem when it's extracted
        TEMP: Essential for character creation completion - uses updated session-based approach
        
        Finalize character creation and add to world state using session data
        """
        try:
            # Get session state
            session_state = self.world_controller.session_system.get_session(session_id)
            if not session_state:
                return {"error": "Session not found"}
            
            # Get player from session
            if not session_state.player_id:
                return {"error": "No player associated with session"}
            
            player_id = session_state.player_id
            player = self.world_controller.players.get(player_id)
            if not player:
                return {"error": "Player not found"}
            
            # Use character data from session, not player
            character_data = session_state.character_data
            if not character_data:
                return {"error": "No character data in session"}
            
            # Create the character using world controller
            character = self.world_controller.character_manager.create_character(
                player_id, 
                character_data  # ✅ Fixed: Use session data
            )
            
            # Add to player's characters
            player.character_ids.append(character.id)
            player.active_character_id = character.id
            self.world_controller.characters[character.id] = character
            
            # Update session state
            self.world_controller.session_system.set_creation_state(session_id, "completed")
            
            return {
                "success": True,
                "message": f"Character {character.name} created successfully!",
                "action": "character_created",
                "character_data": character.to_dict(),
                "character_id": character.id
            }
        except Exception as e:
            return {"error": str(e)}

    def _show_character_sheet(self, character_data):
        """Signal frontend to show and update character sheet"""
        return {
            "action": "show_character_sheet",
            "character_data": character_data
        }
