# world/dm_chat_handler.py
# coding=utf-8
from typing import Dict, List, Optional, Tuple
from world.ai_dungeon_master import Dialog  # Ensure Dialog is imported

class DMChatHandler:
    """
    PHASE_MIGRATION_IN_PROGRESS: This class is being migrated from monolithic phase mixing
    to phase-compliant architecture.
    
    Current violations being addressed:
    1. AI boundary compliance → Use DMChatAI system
    2. Direct state mutation → Use SessionSystem (NOW COMPLIANT ✅)
    3. Direct tool execution → TODO: Use AuthoritySystem (NOW COMPLIANT ✅)
    """

    def __init__(self, world_controller):
        self.world_controller = world_controller
        self.dm = world_controller.dungeon_master  # Will be replaced by ConsequenceEngine in step 4
        self.consequence_engine = world_controller.consequence_engine   # new

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
            # Retrieve player object if a player_id is associated with the session
            player = None
            if session_state.player_id:
                player = self.world_controller.players.get(session_state.player_id)

            # Check if we're in a confirmation state
            if session_state.awaiting_confirmation:
                is_confirmed, response = self._handle_confirmation(session_id, message, session_state)
                # Use session system to clear confirmation flag
                self.world_controller.session_system.set_awaiting_confirmation(session_id, False)

                if is_confirmed:
                    # Continue with character creation
                    result = self._handle_character_creation_tools("", session_id)
                    if result.get("action") == "character_created":
                        return result
                    else:
                        return {
                            "narrative": [Dialog("DM", result["message"], "character_creation")],
                            "tool_result": None
                        }
                else:
                    return {
                        "narrative": [Dialog("DM", response, "clarification")],
                        "tool_result": None
                    }

            # Get character context if specified – use character_manager exclusively
            character_context = {}
            if character_id:
                character = self.world_controller.character_manager.get_character(character_id)
                if character:
                    character_context = {
                        'character_id': character_id,
                        'character_name': character.name,
                        'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                        'character_race': character.race,
                        'character_level': character.level
                    }
                    # Store active character in session
                    self.world_controller.session_system.set_active_character(session_id, character_id)

            # Use active character from session if no specific character was provided
            if not character_id and session_state.active_character_id:
                character_id = session_state.active_character_id
                character = self.world_controller.character_manager.get_character(character_id)
                if character:
                    character_context = {
                        'character_id': character_id,
                        'character_name': character.name,
                        'character_class': character.classs.name if hasattr(character, 'classs') else 'Unknown',
                        'character_race': character.race,
                        'character_level': character.level
                    }

            # Use AI to classify intent
            intent_context = "Character creation phase" if not character_id else "In-game phase"
            intent_result = self._classify_intent(message, intent_context)
            print(f"AI Intent Classification: {intent_result}")

            # Handle meta-requests early
            if intent_result["intent"] == "meta_dialogue" and intent_result["confidence"] > 0.6:
                meta_response = self._handle_meta_request(message, session_id)
                narrative_responses = [Dialog("DM", meta_response, "narration")]
                # Track topic for DM response
                self._update_conversation_topics(session_id, meta_response, is_dm_response=True)
                return {
                    "narrative": narrative_responses,
                    "tool_result": {"meta_request": True}
                }

            # Track topic for regular player messages
            self._update_conversation_topics(session_id, message, is_dm_response=False)

            # If in character creation mode (no active character), use the dedicated creation flow
            is_character_creation = not character_id and (not player or not player.active_character_id)
            if is_character_creation:
                try:
                    intent_result = self.world_controller.dm_chat_ai.classify_intent(
                        message, {"phase": "character_creation"}
                    )
                    if intent_result["intent"] == "character_creation":
                        response_text = "I'd be happy to help you create a character! Let's start by choosing a race and class. What kind of character are you imagining?"
                    else:
                        response_text = "I can help you create a character! Tell me about the type of adventurer you'd like to play."
                    narrative_responses = [Dialog("DM", response_text, "narration")]
                except Exception as e:
                    print(f"Error generating character creation response: {e}")
                    narrative_responses = [Dialog("DM", "I'd be happy to help you create a character! Let's start by choosing a race and class. What kind of character are you imagining?", "narration")]
            else:
                # ---- NEW: Use ConsequenceEngine instead of self.dm ----
                # First, check if tool execution is needed
                requires_tool = self._ai_detect_tool_intent(message, [], character_context)  # we don't have dm_responses yet
                tool_result = None
                if requires_tool:
                    tool_result = self._handle_tool_usage(message, session_id)
                    print(f"DEBUG: Tool result: {tool_result}")

                # Build context for consequence engine
                context = {
                    "player_id": player.id if player else session_state.player_id,
                    "character_context": character_context,
                    "session_id": session_id,
                }

                # Generate narrative responses using the consequence engine
                if tool_result and not tool_result.get("error"):
                    # If a tool was used, generate narrative based on tool result
                    narrative_responses = self.consequence_engine.generate_response_for_action(tool_result, context)
                else:
                    # No tool used, generate narrative based on intent
                    # We need to pass the original message or intent details
                    intent_result["message"] = message  # attach original message for AI use
                    narrative_responses = self.consequence_engine.generate_response_for_intent(intent_result, context)

                # If tool_result contains character data, propagate for frontend
                if tool_result and 'character_data' in tool_result:
                    response_data['character_data'] = tool_result['character_data']
                    response_data['show_character_sheet'] = True
                # ---- END NEW ----

            # Update topics for DM responses
            for response in narrative_responses:
                self._update_conversation_topics(session_id, response.content, is_dm_response=True)

            # Store in chat history using session_system
            if hasattr(self.world_controller, 'session_system') and self.world_controller.session_system:
                self.world_controller.session_system.add_message(session_id, "Player", message)
                for response in narrative_responses:
                    self.world_controller.session_system.add_message(session_id, "DM", response.content)

            print(f"DEBUG: Final response_data: {response_data}")
            return {
                "narrative": narrative_responses,
                "tool_result": tool_result,
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

            tool_result = None
            tool_followup_responses = []

            # Check if tool execution is needed
            requires_tool = self._ai_detect_tool_intent(message, narrative_responses, character_context)

            if requires_tool:
                print("DEBUG: Tool execution required")
                tool_result = self._handle_tool_usage(message, session_id)
                print(f"DEBUG: Tool result: {tool_result}")

                # If a tool was successfully used, generate a narrative follow-up
                if tool_result and not tool_result.get("error"):
                    tool_followup_responses = self.dm.process_player_input(
                        player.id if player else session_id,
                        f"Tool execution result: {tool_result.get('message', 'Action completed')}"
                    )
                # No separate 'skipped' branch – if no tool was applicable, we simply have no tool_followup_responses

            # If tool_result contains character data, propagate it for frontend display
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

            print(f"DEBUG: Final response_data: {response_data}")
            return {
                "narrative": all_narrative_responses,
                "tool_result": tool_result,
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
        """Use AI exclusively to classify message intent without any keyword fallbacks"""
        try:
            return self.world_controller.dm_chat_ai.classify_intent(message, context)
        except Exception as e:
            print(f"AI intent classification failed: {e}")
            return {"intent": "general_question", "confidence": 0.5, "explanation": "AI classification failed"}

    def _handle_meta_request(self, message: str, session_id: str) -> str:
        """Generate response to meta-questions about the conversation"""
        recent_topics = self.get_recent_topics(session_id)
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
        """Use AI to extract meaningful context from the conversation history (placeholder)"""
        # Placeholder – will be implemented with DMChatAI later
        return {"topics_discussed": [], "last_questions": [], "current_focus": "character creation"}

    def _ai_detect_tool_intent(self, message, dm_responses, character_context=None):
        """Use AI exclusively to determine if this message requires tool execution"""
        context = {
            "dm_responses": [r.content for r in dm_responses] if dm_responses else [],
            "character_context": character_context or {}
        }
        try:
            result = self.world_controller.dm_chat_ai.detect_action_intent(message, context)
            return result.get("requires_action", False)
        except Exception as e:
            print(f"AI tool detection failed: {e}")
            return False

    def _handle_tool_usage(self, message, session_id):
        """Handle tool execution using AuthoritySystem for validation"""
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            return {"error": "Session not found"}

        player_id = session_state.player_id
        if not player_id:
            return {"error": "No player in session"}

        character_id = session_state.active_character_id
        character = None
        if character_id:
            character = self.world_controller.character_manager.get_character(character_id)

        # Use AI to determine which tool to use
        tool_to_use = None
        try:
            tool_to_use = self._determine_tool_for_message(message, "in_game")
        except Exception as e:
            print(f"Tool detection error: {e}")

        if tool_to_use:
            context = {
                "session_id": session_id,
                "player_id": player_id,
                "character_id": character_id,
                "character_name": character.name if character else "Unknown",
                "current_location": self.world_controller.current_location.id if self.world_controller.current_location else None,
                "world_id": self.world_controller.world_id if hasattr(self.world_controller, 'world_id') else None,
                "phase": "authority"
            }
            parameters = {
                "message": message,
                "character_id": character_id,
                "player_id": player_id,
                "session_id": session_id
            }
            try:
                tool_result = self.world_controller.authority_system.execute_tool(
                    tool_name=tool_to_use,
                    parameters=parameters,
                    context=context
                )
                if tool_result.get("success"):
                    return {
                        "message": tool_result.get("message", "Action processed"),
                        "action": "in_game_tool",
                        "tool_used": tool_to_use,
                        "action_data": tool_result.get("action_data"),
                        "validated": True,
                        "requires_mutation": True
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
                    "error": str(e)
                }
        else:
            # No tool found – return a generic result without a 'skipped' flag
            return {
                "message": f"Processed action: {message}",
                "action": "in_game_generic",
                "action_data": {"original_message": message}
            }

    def _determine_tool_for_message(self, message, context):
        """Use AI to determine which tool to invoke."""
        try:
            tool_registry = self._get_tool_registry()
            if not tool_registry:
                return None
            available_tools = list(tool_registry.tools.keys())

            ai_result = self.world_controller.dm_chat_ai.detect_action_intent(
                message,
                {"available_tools": available_tools, "context": context}
            )
            if ai_result.get("requires_action") and ai_result.get("action_type"):
                return ai_result.get("action_type")
            return None
        except Exception as e:
            print(f"Tool detection error: {e}")
            return None

    def _get_tool_registry(self):
        """Helper to get tool registry from authority_system or ai_system."""
        if hasattr(self.world_controller, 'authority_system'):
            return self.world_controller.authority_system.tool_registry
        elif hasattr(self.world_controller.ai_system, 'tool_registry'):
            return self.world_controller.ai_system.tool_registry
        return None

    # ----------------------------------------------------------------------
    # Character creation helper methods – now using SessionSystem for all state mutations
    # ----------------------------------------------------------------------
    def _handle_character_creation_tools(self, message, session_id):
        """Handle tool usage during character creation phase with proper state management"""
        session_state = self.world_controller.session_system.get_session(session_id)
        if not session_state:
            session_state = self.world_controller.session_system.get_or_create_session(session_id, None)

        # Reset character data if needed (use session system to replace)
        if not session_state.character_data:
            self.world_controller.session_system.set_character_data(session_id, {})

        if session_state.creation_state == "not_started":
            self.world_controller.session_system.set_creation_state(session_id, "gathering_info")

        extracted_data = self._extract_character_data(message, session_state.character_data)
        self.world_controller.session_system.update_character_data(session_id, extracted_data)

        if session_state.creation_state == "gathering_info":
            if self._has_sufficient_data_for_class_suggestion(session_state.character_data):
                class_info = self._determine_character_class(
                    session_state.character_data.get('class', ''),
                    session_state.character_data
                )
                # Get fresh data to avoid stale reference
                current_data = self.world_controller.session_system.get_session(session_id).character_data
                updated_data = current_data.copy()
                updated_data['suggested_class'] = class_info['primary_class']
                updated_data['suggested_multiclass'] = class_info['secondary_class']
                updated_data['class_explanation'] = class_info['explanation']
                updated_data['custom_traits'] = class_info['custom_traits']

                self.world_controller.session_system.update_character_data(session_id, updated_data)
                self.world_controller.session_system.set_creation_state(session_id, "class_suggested")
                self.world_controller.session_system.set_awaiting_confirmation(session_id, True)
                self.world_controller.session_system.set_pending_suggestion(session_id, class_info)

                return {
                    "message": f"Based on your description, I suggest {class_info['primary_class']} "
                               f"{('with a dip into ' + class_info['secondary_class'] + ' ') if class_info['secondary_class'] else ''}"
                               f"because: {class_info['explanation']}. Does this work for you?",
                    "action": "class_suggestion",
                    "character_data": session_state.character_data,
                    "requires_confirmation": True
                }

        elif session_state.creation_state == "class_suggested":
            return {
                "message": "I'm still waiting for your confirmation on the class suggestion. Does the suggested class work for you?",
                "action": "class_confirmation_reminder",
                "character_data": session_state.character_data
            }

        elif session_state.creation_state == "class_confirmed":
            if self._has_sufficient_character_data(session_state.character_data):
                character = self.world_controller.character_manager.create_character(
                    session_state.player_id,
                    session_state.character_data
                )
                if session_state.player_id:
                    # Use the new manager method to assign character to player
                    self.world_controller.character_manager.assign_character_to_player(
                        session_state.player_id, character.id
                    )
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

        next_question = self._determine_next_question(session_state.character_data, session_id)
        return {
            "message": next_question['question'],
            "action": "character_creation_question",
            "question_category": next_question['category'],
            "character_data": session_state.character_data
        }

    def _extract_character_data(self, message, existing_data):
        try:
            return self.world_controller.dm_chat_ai.extract_character_data(message, existing_data)
        except Exception as e:
            print(f"Error extracting character data: {e}")
            return {}

    def _has_sufficient_character_data(self, char_data):
        required = ["name", "race", "class"]
        return all(field in char_data and char_data[field] for field in required)

    def _has_sufficient_data_for_class_suggestion(self, char_data):
        has_concept = any([
            char_data.get('class'),
            char_data.get('skills'),
            char_data.get('background'),
            char_data.get('motivations')
        ])
        has_identity = char_data.get('name') and char_data.get('race')
        return has_concept and has_identity

    def _determine_character_class(self, class_concept, character_data):
        try:
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
        conversation_context = self.world_controller.session_system.get_conversation_context(session_id)
        try:
            return self.world_controller.dm_chat_ai.suggest_next_question(character_data, conversation_context)
        except Exception as e:
            print(f"Error determining next question: {e}")
            return {
                "question": "What race would you like your character to be?",
                "priority": "Medium",
                "category": "race"
            }

    def _handle_confirmation(self, session_id: str, message: str, session_state) -> tuple:
        context = {
            "session_state": session_state,
            "character_data": session_state.character_data
        }
        try:
            assessment = self.world_controller.dm_chat_ai.interpret_confirmation(message, context)
            if assessment['is_confirmation'] and assessment['confidence'] > 0.7:
                # Player confirmed the suggestion – update class and remove temporary fields
                self.world_controller.session_system.update_character_data(
                    session_id,
                    {"class": session_state.character_data.get('suggested_class', '')}
                )
                # Remove temporary suggestion fields
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    self.world_controller.session_system.remove_character_data_field(session_id, field)

                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                return True, "Great! Class confirmed. Let's continue with your character."

            elif assessment['corrected_value'] and assessment['confidence'] > 0.6:
                # Player provided a correction
                self.world_controller.session_system.update_character_data(
                    session_id,
                    {"class": assessment['corrected_value']}
                )
                for field in ['suggested_class', 'suggested_multiclass', 'class_explanation']:
                    self.world_controller.session_system.remove_character_data_field(session_id, field)

                self.world_controller.session_system.set_creation_state(session_id, "class_confirmed")
                self.world_controller.session_system.set_pending_suggestion(session_id, None)
                return True, f"Understood, I'll use {assessment['corrected_value']} instead. Let's continue."

            else:
                return False, "I'm not sure if you're confirming the suggestion or suggesting something different. Could you clarify?"
        except Exception as e:
            print(f"Error handling confirmation: {e}")
            return False, "I had trouble understanding your response. Could you please clarify?"

    # The _finalize_character method has been removed as it is redundant and unused.