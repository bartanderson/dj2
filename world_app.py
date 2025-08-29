# world_app.py
# import eventlet
# eventlet.monkey_patch() # this has to be run before importing any other modules
import os
from flask import Flask, jsonify, current_app, render_template, send_from_directory, session, request, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
import sys
import random
import uuid
import json
from datetime import datetime
from pathlib import Path
from world.world_controller import WorldController
from world.world_map import WorldMap
from world.t2i import TextToImage  # Import the image generator
from world.persistence import WorldManager
from world.ai_integration import BaseAI, WorldAI


# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

app = Flask(__name__)

avatar_dir = Path("static/character_avatars")
t2i = None

# Initialize SocketIO
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=True,
                   engineio_logger=True)

@app.route('/api/test2', methods=['GET'])
def test_endpoint2():
    try:
        world_controller = get_world_controller()
        if world_controller is None:
            return jsonify({'status': 'error', 'message': 'World controller not initialized'})
        
        return jsonify({
            'status': 'success', 
            'message': 'Server is working',
            'world_controller': 'Initialized' if hasattr(world_controller, 'dm_chat_handler') else 'Not initialized'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if the server is fully initialized"""
    if hasattr(app, 'world_controller') and app.world_controller is not None:
        return jsonify({
            'status': 'ready',
            'message': 'World controller is initialized'
        })
    else:
        return jsonify({
            'status': 'initializing',
            'message': 'World controller is not ready yet'
        }), 503  # Service Unavailable status code

def get_world_controller():
    """Safely get the world controller instance"""
    if hasattr(app, 'world_controller') and app.world_controller is not None:
        return app.world_controller
    else:
        print("World controller not available")
        return None

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({'status': 'ok', 'message': 'Server is running'})

@app.route('/api/chat/dm', methods=['POST'])
def dm_chat():
    try:
        data = request.get_json()
        player_id = data.get('player_id')
        message = data.get('message')
        
        if not player_id or not message:
            return jsonify({'error': 'Missing player_id or message'}), 400
        
        # Get chat handler from world controller
        chat_handler = current_app.world_controller.dm_chat_handler
        responses = chat_handler.process_message(player_id, message)
        
        return jsonify({
            'responses': [{
                'speaker': r.speaker,
                'content': r.content,
                'type': r.dialog_type
            } for r in responses]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def setup_world_system():
    """Complete world initialization flow with proper integration"""
    print("Initializing world system...")
    
    try:
        # 1. Initialize base AI system
        base_ai = BaseAI(ollama_host="http://localhost:11434", seed=42)
        print("✓ Base AI system initialized")
        
        # 2. Set up image generation paths
        model_path = Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors"
        image_output_dir = Path("static/world_images")
        t2i = TextToImage(model_path)

        # 3. Create world manager with image capabilities
        world_manager = WorldManager(ai_system=base_ai)
        print("✓ World manager initialized")
        
        # 4. Check for existing worlds with proper error handling
        try:
            existing_worlds = world_manager.get_existing_worlds()
            
            # Ensure we have a list and it's not empty
            if isinstance(existing_worlds, list) and len(existing_worlds) > 0:
                # Load first existing world
                world_id = existing_worlds[0].get('id') if isinstance(existing_worlds[0], dict) else existing_worlds[0]
                print(f"✓ Loading existing world: {world_id}")
                world_data = world_manager.load_from_db(world_id)
            else:
                raise ValueError("No existing worlds found")
                
        except (ValueError, IndexError, TypeError) as e:
            print(f"No existing worlds found or error loading: {e}")
            print("Creating new world...")
            
            # Create new world with customizable parameters
            world_id = world_manager.create_new_world(
                theme="dark_fantasy",
                region_count=3,
                locations_per_region=4,
                quest_density=0.8,
                dungeon_probability=0.6,
                faction_count=2,
                npc_density=0.7,
                generate_images=True,
                model_path=model_path,
                image_output_dir=image_output_dir,
                seed=42
            )
            print(f"✓ Created new world with ID: {world_id}")
            world_data = world_manager.load_from_db(world_id)
        
        # 5. Initialize world controller
        world_controller = WorldController(
            world_id=world_id,
            ai_system=base_ai,
            seed=42
        )
        print("✓ World controller initialized")
        
        # 6. Initialize AI systems with proper state
        world_controller.world_ai = WorldAI(world_state=world_controller)
        world_controller.dungeon_ai = None  # Will be set when entering dungeon
        print("✓ AI systems initialized")
        
        # 7. Verify everything is working
        print(f"✓ World loaded with {len(world_controller.world_map.locations)} locations")
        print(f"✓ Starting at: {world_controller.starting_location_id}")
        
        return world_controller, world_id
        
    except Exception as e:
        print(f"❌ Error initializing world system: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point for the world application"""
    try:
        world_controller, world_id = setup_world_system()
        print(f"\n🎉 World system ready! World ID: {world_id}")
        
        # # This was a nice idea, but was not completed. There is no tool World Map.
        # # Test command processing
        # test_command = "describe the starting location"
        # result = controller.process_command(test_command)
        # print(f"\nTest command result: {result}")

        # Attach the world_controller to the Flask app
        app.world_controller = world_controller
        
        return world_controller
        
    except Exception as e:
        print(f"❌ Failed to initialize world system: {e}")
        return None


# World loading endpoint
@app.route('/api/load-world/<int:world_id>', methods=['POST'])
def load_world(world_id):
    global world_controller
    world_controller = WorldController(world_id, ai_system)
    return jsonify({"success": True})

# Get context endpoint
@app.route('/api/context/<player_id>')
def get_context(player_id):
    context = dm.get_recent_context(player_id)
    return jsonify({"context": context})

# serve world.html
@app.route('/', endpoint='index')
def index():
    return render_template('world.html')

# Serve static images
@app.route('/static/world_images/<path:filename>')
def serve_world_images(filename):
    return send_from_directory('static/world_images', filename)

@app.route('/static/character_avatars/<path:filename>')
def serve_character_avatars(filename):
    return send_from_directory('static/character_avatars', filename)

@app.route('/api/retry-failed-images', methods=['POST'])
def retry_failed_images():
    try:
        # Load failure data
        with open('failed_generations.json', 'r') as f:
            failures = json.load(f)
        
        # Retry failed generations
        successes, new_failures = t2i.generate_batch(
            generation_requests=failures,
            output_dir=avatar_dir  # Use avatar directory for retries
        )
        
        # Update character avatars
        updated_characters = []
        for char_id in successes:
            if char_id in world_controller.characters:
                world_controller.characters[char_id].avatar_url = f"/static/character_avatars/{successes[char_id]}"
                updated_characters.append(char_id)
        
        return jsonify({
            "success": True,
            "updated_characters": updated_characters,
            "succeeded": len(successes),
            "failed": len(new_failures)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ===== Character Endpoints =====
@app.route('/api/player/characters', methods=['GET'])
def get_player_characters():
    try:
        session_id = request.cookies.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session ID'}), 400
            
        player = app.world_controller.get_or_create_player(session_id)
        characters = []
        
        for char_id in player.character_ids:
            if char_id in app.world_controller.characters:
                characters.append(app.world_controller.characters[char_id].to_dict())
        
        return jsonify({
            'success': True,
            'characters': characters,
            'player_id': player.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/player/active-character', methods=['POST'])
def set_active_character():
    try:
        session_id = request.cookies.get('session_id')
        data = request.get_json()
        character_id = data.get('character_id')
        
        if not session_id:
            return jsonify({'error': 'No session ID'}), 400
            
        player = app.world_controller.get_or_create_player(session_id)
        
        if character_id not in player.character_ids:
            return jsonify({'error': 'Character does not belong to player'}), 400
            
        success = player.set_active_character(character_id)
        
        return jsonify({
            'success': success,
            'active_character_id': player.active_character_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/character-classes', methods=['GET'])
def get_character_classes():
    classes = world_controller.get_available_classes()
    return jsonify({"classes": classes})

@app.route('/api/character-backgrounds', methods=['GET'])
def get_character_backgrounds():
    backgrounds = world_controller.get_available_backgrounds()
    return jsonify({"backgrounds": backgrounds})

@app.route('/api/starting-equipment/<class_name>', methods=['GET'])
def get_starting_equipment(class_name):
    equipment = world_controller.get_starting_equipment_options(class_name)
    return jsonify(equipment)

# @app.route('/api/create-character', methods=['POST'])
# def create_character():
#     data = request.get_json()
#     user_id = session.get('user_id', 'default_user')
    
#     # Create character using new system
#     character = world_controller.create_character(user_id, data)
    
#     # Generate avatar
#     avatar_prompt = (
#         f"Fantasy portrait: {character.race} {character.classs.name} "
#         f"{character.background.name}, {character.ai_personality['traits']}"
#     )
#     try:
#         avatar_filename = t2i.generate_image(avatar_prompt, output_dir=avatar_dir)
#         character.avatar_url = f"/static/character_avatars/{avatar_filename}"
#     except Exception as e:
#         print(f"Avatar generation failed: {e}")
#         character.avatar_url = "/static/images/default_avatar.png"
    
#     # Add character to world controller
#     world_controller.characters[character.id] = character
    
#     # Add to session party
#     party = session.get('party', [])
#     if len(party) < 4:  # Maintain party size limit
#         party.append(character.id)
#         session['party'] = party
    
#     return jsonify({
#         "success": True,
#         "character": character.to_dict(),
#         "party_size": len(party)
#     })

@app.route('/api/create-character', methods=['POST'])
def create_character():
    try:
        data = request.get_json()
        session_id = request.cookies.get('session_id') or str(uuid.uuid4())
        
        # Get or create player for this session
        player = app.world_controller.get_or_create_player(session_id)

        # Create character using your world controller
        character = app.world_controller.create_character(player_id, data)

        # Associate character with player
        app.world_controller.associate_character_with_player(player.id, character.id)
        
        return jsonify({
            'success': True,
            'character': character.to_dict(),
            'player_id': player.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-personal-item', methods=['POST'])
def generate_personal_item():
    data = request.get_json()
    char_concept = data.get('concept', '')
    item = world_controller.character_builder.generate_personal_item(char_concept)
    return jsonify(item)
    
# ===== World Navigation Endpoints =====
@app.route('/api/travel/<location_id>', methods=['POST'])
def travel_to(location_id):
    success = world_controller.travel_to_location(location_id)
    return jsonify({
        "success": success,
        "location": world_controller.get_current_location_data()
    })

@app.route('/api/location/<location_id>/rumors')
def get_location_rumors(location_id):
    rumors = world_controller.get_rumors(location_id)
    return jsonify({"rumors": rumors})

@app.route('/api/enter-dungeon', methods=['POST'])
def enter_dungeon():
    success = world_controller.enter_dungeon()
    return jsonify({"success": success})

# ===== Party Management Endpoints =====
@app.route('/api/create-party', methods=['POST'])
def create_party():
    data = request.json
    party_id = world_controller.create_party(
        name=data.get('name', 'New Party'),
        initial_members=data.get('members', [])
    )
    return jsonify({"success": True, "party_id": party_id})

@app.route('/api/move-character', methods=['POST'])
def move_character():
    data = request.json
    success = app.world_controller.add_to_party(
        char_id=data['char_id'],
        party_id=data['party_id']
    )
    return jsonify({"success": success})

@app.route('/api/parties')
def get_parties():
    return jsonify({
        "parties": app.world_controller.get_active_parties(),
        "default_party": app.world_controller.default_party_id
    })

@app.route('/api/disband-party/<party_id>', methods=['POST'])
def disband_party(party_id):
    success = app.world_controller.disband_party(party_id)
    return jsonify({"success": success})

# ===== Core Game State Endpoints =====
@app.route('/api/world-state')
def world_state():
    try:
        # Check if world_controller is available
        if not hasattr(app, 'world_controller') or app.world_controller is None:
            return jsonify({
                "worldMap": {"error": "World controller not initialized"},
                "currentLocation": None,
                "parties": [],
                "characters": {}
            })
            
        # Convert characters to dict representation
        characters_dict = {}
        if hasattr(app.world_controller, 'characters'):
            for char_id, char in app.world_controller.characters.items():
                characters_dict[char_id] = char.to_dict()

        return jsonify({
            "worldMap": app.world_controller.get_map_data(),
            "currentLocation": app.world_controller.get_current_location_data(),
            "parties": app.world_controller.get_active_parties(),
            "characters": characters_dict
        })
    except Exception as e:
        print(f"Error in world_state: {str(e)}")
        return jsonify({
            "worldMap": {"error": "Map data unavailable"},
            "currentLocation": None,
            "parties": [],
            "characters": {}
        })

@app.route('/api/analyze-motivation', methods=['POST'])
def analyze_motivation():
    data = request.get_json()
    message = data['message']
    
    # Use the narrative system to analyze motivation
    motivation = app.world_controller.narrative_system.motivation.analyze_action(
        message, 
        app.world_controller.narrative_system.characters.get(session.get('user_id', 'guest'))
    )
    
    return jsonify({'motivation': motivation})

@app.route('/api/narrative-guidance', methods=['POST'])
def narrative_guidance():
    data = request.get_json()
    motivation = data['motivation']
    context = data.get('context', {})
    
    # Get narrative guidance
    guidance = app.world_controller.narrative_system.guide.get_gentle_nudge({
        'motivation': motivation,
        'context': context
    })
    
    return jsonify({'guidance': guidance})

@app.route('/api/locations')
def all_locations():
    try:
        return jsonify({
            "locations": [
                loc.to_dict() 
                for loc in app.world_controller.world_map.locations.values()
            ]
        })
    except Exception as e:
        print(f"Error in all_locations: {str(e)}")
        return jsonify({"locations": []})


@app.route('/api/dm-response', methods=['POST'])
def dm_response():
    try:
        print("DEBUG: dm-response endpoint called")
        
        # Check if world_controller is available
        if not hasattr(app, 'world_controller') or app.world_controller is None:
            print("DEBUG: world_controller is not available")
            return jsonify({'error': 'World controller not initialized'}), 500
            
        # Check if dm_chat_handler is available
        if not hasattr(app.world_controller, 'dm_chat_handler'):
            print("DEBUG: dm_chat_handler is not available")
            return jsonify({'error': 'DM chat handler not initialized'}), 500
            
        data = request.get_json()
        
        message = data.get('message')
        character_id = data.get('character_id')  # Allow specifying which character is speaking
        
        # Get session ID from cookie or generate a new one
        session_id = request.cookies.get('session_id')
        is_new_session = False
        
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True
            print(f"DEBUG: Generated new session ID: {session_id}")
        
        # Get or create player for this session
        print("DEBUG: About to call get_or_create_player")
        player = app.world_controller.get_or_create_player(session_id)
        print(f"DEBUG: Got player: {player.id if player else 'None'}")
        
        # If character_id is specified, validate it belongs to the player
        if character_id:
            if character_id not in player.character_ids:
                return jsonify({'error': 'Character does not belong to player'}), 400
            # Set this as the active character
            player.set_active_character(character_id)
        
        # Use active character if no specific character is specified
        active_character_id = character_id or player.active_character_id
        
        result = app.world_controller.dm_chat_handler.process_message(
            session_id, 
            message, 
            character_id=active_character_id
        )
        
        response_data = {
            'responses': [{
                'speaker': r.speaker,
                'content': r.content,
                'type': r.dialog_type
            } for r in result['narrative']],
            'tool_result': result['tool_result'].get('message') if result['tool_result'] else None,
            'session_id': session_id,
            'character_id': active_character_id,
            'player_id': player.id  # Include player ID for reference
        }
        
        # Create response and set cookie if it's a new session
        response = jsonify(response_data)
        if is_new_session:
            response.set_cookie(
                'session_id', 
                session_id, 
                max_age=60*60*24*7,  # 1 week
                path='/',
                secure=False,  # Set to True in production with HTTPS
                httponly=True,
                samesite='Lax'
            )
            
        return response
        
    except Exception as e:
        print(f"Error in dm-response: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

def recognize_player(self, session_id, player_data):
    """Try to recognize a returning player based on browser fingerprint or other data"""
    # Example: Use browser fingerprinting
    browser_fingerprint = player_data.get('browser_fingerprint')
    if browser_fingerprint:
        # Check if we've seen this browser before
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT player_id FROM player_sessions WHERE browser_fingerprint = %s ORDER BY last_seen DESC LIMIT 1",
                    (browser_fingerprint,)
                )
                result = cur.fetchone()
                if result:
                    return result[0]
        finally:
            Database.return_connection(conn)
    
    return None

@app.route('/api/guide-character-creation', methods=['POST'])
def guide_character_creation():
    data = request.get_json()
    player_id = session.get('user_id', 'guest')
    message = data.get('message', '')
    
    # Get current creation state
    creation_state = session.get('creation_state', {
        'step': 0,
        'character': {
            'race': None,
            'class': None,
            'background': None,
            'personality': None,
            'ideals': None,
            'bonds': None,
            'flaws': None
        }
    })
    
    # Process through AI narrative system
    result = app.world_controller.narrative_system.guide_character_creation(
        player_id, 
        message, 
        creation_state
    )
    
    # Update session state
    session['creation_state'] = result['new_state']
    return jsonify(result)


#### start of socketio stuff #################################################################

# Add these WebSocket event handlers after your existing routes
@socketio.on('connect')
def handle_connect():
    session_id = request.sid
    print(f"Client connected: {session_id}")
    emit('connected', {'session_id': session_id, 'timestamp': datetime.now().isoformat()})

@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    print(f"Client disconnected: {session_id}")
    
    # Clean up session data
    if hasattr(world_controller, 'session_manager'):
        session_data = app.world_controller.session_manager.sessions.get(session_id)
        if session_data:
            character_id = session_data.get('character_id')
            party_id = session_data.get('party_id')
            
            # Notify party members about disconnection
            if party_id:
                emit('player_left', {
                    'session_id': session_id,
                    'player_name': session_data.get('player_name'),
                    'character_id': character_id
                }, room=party_id)
            
            # Clean up session
            app.world_controller.session_manager.cleanup_session(session_id)

@socketio.on('player_register')
def handle_player_register(data):
    session_id = request.sid
    player_name = data.get('player_name', 'Unknown Player')
    device_info = data.get('device_info', {})
    
    # Generate a device ID if not provided
    if 'device_id' not in device_info:
        device_info['device_id'] = f"device_{uuid.uuid4().hex[:8]}"
    
    # Create a new session
    session_data = app.world_controller.session_manager.create_session(
        player_name, device_info, session_id
    )
    
    # Get available characters (not assigned to any session)
    available_chars = []
    for char_id, char_data in app.world_controller.characters.items():
        if char_id not in app.world_controller.session_manager.character_assignments:
            available_chars.append({
                'id': char_id,
                'name': char_data.name,
                'class': char_data.classs.name if hasattr(char_data.classs, 'name') else 'Unknown',
                'race': char_data.race
            })
    
    emit('registration_success', {
        'session_id': session_id,
        'player_name': player_name,
        'available_characters': available_chars
    })

@socketio.on('assign_character')
def handle_assign_character(data):
    session_id = request.sid
    character_id = data.get('character_id')
    
    if character_id not in app.world_controller.characters:
        emit('error', {'message': 'Character not found'})
        return
    
    success = app.world_controller.session_manager.assign_character(session_id, character_id)
    if success:
        character = app.world_controller.characters[character_id]
        session_data = app.world_controller.session_manager.sessions[session_id]
        
        # Assign to default party if not in one
        party_id = character.party_id or app.world_controller.default_party_id
        app.world_controller.session_manager.assign_to_party(session_id, party_id)
        
        # Join the party room
        join_room(party_id)
        
        # Notify all party members
        emit('character_assigned', {
            'character_id': character_id,
            'session_id': session_id,
            'player_name': session_data['player_name'],
            'character_name': character.name,
            'party_id': party_id
        }, room=party_id)
        
        # Send full party state to the new member
        party_members = []
        for member_sid in app.world_controller.session_manager.party_views.get(party_id, []):
            if member_sid in app.world_controller.session_manager.sessions:
                member_data = app.world_controller.session_manager.sessions[member_sid]
                if member_data.get('character_id'):
                    char_data = app.world_controller.characters[member_data['character_id']]
                    party_members.append({
                        'session_id': member_sid,
                        'player_name': member_data['player_name'],
                        'character_id': member_data['character_id'],
                        'character_name': char_data.name,
                        'position': char_data.position
                    })
        
        emit('party_state', {
            'party_id': party_id,
            'members': party_members
        })
    else:
        emit('error', {'message': 'Failed to assign character'})

@socketio.on('character_move')
def handle_character_move(data):
    session_id = request.sid
    character_id = data.get('character_id')
    new_position = data.get('position')
    
    # Verify this session owns the character
    if (world_controller.session_manager.character_assignments.get(character_id) == session_id and
        character_id in app.world_controller.characters):
        
        # Update character position
        app.world_controller.characters[character_id].position = new_position
        
        # Broadcast to all party members
        character = app.world_controller.characters[character_id]
        party_id = character.party_id or app.world_controller.default_party_id
        
        emit('character_moved', {
            'character_id': character_id,
            'position': new_position,
            'session_id': session_id
        }, room=party_id)

@socketio.on('join_party')
def handle_join_party(data):
    session_id = request.sid
    party_id = data.get('party_id')
    
    if session_id not in app.world_controller.session_manager.sessions:
        emit('error', {'message': 'Session not registered'})
        return
    
    # Leave current party
    current_party = app.world_controller.session_manager.sessions[session_id].get('party_id')
    if current_party:
        leave_room(current_party)
        emit('player_left_party', {
            'session_id': session_id,
            'player_name': app.world_controller.session_manager.sessions[session_id]['player_name']
        }, room=current_party)
    
    # Join new party
    success = app.world_controller.session_manager.assign_to_party(session_id, party_id)
    if success:
        join_room(party_id)
        
        # Notify new party members
        session_data = app.world_controller.session_manager.sessions[session_id]
        character_id = session_data.get('character_id')
        character_name = app.world_controller.characters[character_id].name if character_id else "No character"
        
        emit('player_joined_party', {
            'session_id': session_id,
            'player_name': session_data['player_name'],
            'character_id': character_id,
            'character_name': character_name
        }, room=party_id)
        
        # Send full party state to the new member
        party_members = []
        for member_sid in app.world_controller.session_manager.party_views.get(party_id, []):
            if member_sid != session_id and member_sid in app.world_controller.session_manager.sessions:
                member_data = app.world_controller.session_manager.sessions[member_sid]
                if member_data.get('character_id'):
                    char_data = app.world_controller.characters[member_data['character_id']]
                    party_members.append({
                        'session_id': member_sid,
                        'player_name': member_data['player_name'],
                        'character_id': member_data['character_id'],
                        'character_name': char_data.name,
                        'position': char_data.position
                    })
        
        emit('party_state', {
            'party_id': party_id,
            'members': party_members
        })
    else:
        emit('error', {'message': 'Failed to join party'})

@socketio.on('request_world_state')
def handle_request_world_state():
    session_id = request.sid
    emit('world_state', {
        'characters': {cid: char.to_dict() for cid, char in app.world_controller.characters.items()},
        'parties': app.world_controller.get_active_parties(),
        'locations': [loc.to_dict() for loc in app.world_controller.world_map.locations.values()]
    })
#######end of socketio stuff###########

#utility stuff for ip detection
import socket
import subprocess
import re

def get_ip_address():
    """Get the local IP address"""
    try:
        # Create a socket connection to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_zerotier_ip():
    """Try to get ZeroTier IP address with multiple methods"""
    # Method 1: Try zerotier-cli command
    try:
        result = subprocess.run(["zerotier-cli", "listnetworks"], 
                              capture_output=True, text=True, timeout=5)
        # Parse the output to find the IP address
        lines = result.stdout.split('\n')
        for line in lines:
            if "OK" in line and "PRIVATE" in line:
                parts = line.split()
                if len(parts) > 8:
                    ip_cidr = parts[8]
                    # Extract just the IP address from CIDR notation
                    ip = ip_cidr.split('/')[0]
                    return ip
    except:
        pass


def initialize_app():
    """Initialize the Flask application with world controller"""
    try:
        world_controller = main()
        
        if world_controller is not None:
            # Attach to app
            app.world_controller = world_controller
            
            # Display connection information
            print("🌍 DUNGEON WORLD SERVER")
            print("Server running on:")
            print(f"Local URL: http://localhost:5000")
            print(f"Network URL: http://{get_ip_address()}:5000")
            print(f"ZeroTier URL: http://{get_zerotier_ip()}:5000")
            print("Server starting... (Press Ctrl+C to stop)")
            
            return world_controller
        else:
            print("❌ Failed to initialize world controller")
            return None
    except Exception as e:
        print(f"❌ Error initializing app: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Only initialize when not in reloader
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        world_controller = initialize_app()
    
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False) 