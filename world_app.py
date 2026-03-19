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
from world.db import Database
from world.player import Player

# Add GameEngine imports
from engine.game_engine import GameEngine, GamePhase, GameContext

# Add to world_app.py, near other imports
import requests


# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

app = Flask(__name__)
from routes.api import api_bp
app.register_blueprint(api_bp, url_prefix='/api')

# begin filtering timestamp
import logging

class AccessLogFilter(logging.Filter):
    def filter(self, record):
        # Return False to exclude access log lines, True to keep others
        msg = record.getMessage()
        # Exclude lines with HTTP method and status code
        if ('"GET' in msg or '"POST' in msg or '"PUT' in msg or '"DELETE' in msg) and 'HTTP/1.' in msg:
            # Check for status code (200, 404, etc.)
            if any(f' {code} ' in msg for code in ['200', '201', '204', '300', '301', '302', '400', '401', '403', '404', '500']):
                return False
        return True

# Apply filter to Werkzeug logger
logging.getLogger('werkzeug').addFilter(AccessLogFilter())
# end filtering timestamp

avatar_dir = Path("static/character_avatars")
t2i = None

# Initialize SocketIO
socketio = SocketIO(app, 
                   cors_allowed_origins="*", 
                   async_mode='threading',
                   logger=True,
                   engineio_logger=True)

# Add this class to world_app.py or a separate test file
class DungeonConnectionHelper:
    @staticmethod
    def check_all_endpoints():
        """Check all critical endpoints"""
        endpoints = [
            ("GET", "http://localhost:5000/api/engine/status", None),
            ("GET", "http://localhost:5000/api/dungeon/status", None),
            ("GET", "http://localhost:5005/", None),
            ("POST", "http://localhost:5000/api/engine/mode", {"mode": "dungeon"}),
            ("GET", "http://localhost:5000/api/engine/mode", None),
            ("POST", "http://localhost:5000/api/engine/mode", {"mode": "world"}),
        ]
        
        results = []
        for method, url, data in endpoints:
            try:
                if method == "GET":
                    response = requests.get(url, timeout=2)
                else:
                    response = requests.post(url, json=data, timeout=2)
                
                results.append({
                    "method": method,
                    "url": url,
                    "status": response.status_code,
                    "success": response.status_code < 400
                })
            except Exception as e:
                results.append({
                    "method": method,
                    "url": url,
                    "status": "error",
                    "error": str(e),
                    "success": False
                })
        
        return results

# Add a debug endpoint to use this helper
@app.route('/api/debug/connectivity', methods=['GET'])
def debug_connectivity():
    """Debug endpoint to test all connections"""
    results = DungeonConnectionHelper.check_all_endpoints()
    
    # Count successes
    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)
    
    return jsonify({
        "overall_status": f"{successful}/{total} endpoints successful",
        "results": results,
        "recommendation": "Start dungeon_neo_web_app.py on port 5005 if dungeon endpoints fail"
    })
    
class DungeonHTTPClient:
    def __init__(self, base_url="http://localhost:5005"):
        self.base_url = base_url
        self.session = requests.Session()
        self.connected = self.test_connection()
    
    def test_connection(self):
        try:
            # Try multiple endpoints to see what's available
            endpoints_to_try = ["/", "/ai-command", "/dungeon-state"]
            
            for endpoint in endpoints_to_try:
                try:
                    response = self.session.get(
                        f"{self.base_url}{endpoint}", 
                        timeout=3
                    )
                    if response.status_code < 500:
                        print(f"  [OK] Dungeon endpoint {endpoint}: HTTP {response.status_code}")
                        return True
                except:
                    continue
            
            print(f"[ERROR] No responsive dungeon endpoints at {self.base_url}")
            return False
            
        except Exception as e:
            print(f"[ERROR] Dungeon connection test failed: {e}")
            return False

    def send_ai_command(self, command):
        """Send AI command to dungeon server with position handling"""
        try:
            response = self.session.post(
                f"{self.base_url}/ai-command",
                json={"command": command},
                timeout=30  # Longer timeout for AI processing
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Fix: If the AI wants to inspect_cell without coordinates, add them
                if (result.get("ai_response") and "inspect_cell" in result.get("ai_response", "") 
                    and "arguments" in result.get("ai_response", "") and "{}" in result.get("ai_response", "")):
                    
                    # Get current position
                    pos_x, pos_y = self.get_party_position()
                    
                    # Update the AI response with coordinates
                    import json
                    try:
                        ai_data = json.loads(result["ai_response"])
                        if "arguments" in ai_data and not ai_data["arguments"]:
                            ai_data["arguments"] = {"x": pos_x, "y": pos_y}
                            result["ai_response"] = json.dumps(ai_data, indent=2)
                    except:
                        pass
                
                return result
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_dungeon_state(self):
        """Get current dungeon state"""
        try:
            # First try the ai-command endpoint
            response = self.session.post(
                f"{self.base_url}/ai-command",
                json={"command": "where am i?"},
                timeout=3
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "party_position": "unknown",  # Would need parsing from response
                    "visible_cells": [],
                    "dungeon_available": True,
                    "last_response": result
                }
        except:
            pass
        
        return {
            "party_position": "unknown",
            "visible_cells": [],
            "dungeon_available": True
        }

    def get_party_position(self):
        """Get current party position from dungeon server"""
        try:
            # Try to get position through AI command
            response = self.session.post(
                f"{self.base_url}/ai-command",
                json={"command": "what is my current position"},
                timeout=10
            )
            if response.status_code == 200:
                result = response.json()
                # Try to parse position from response
                if result.get("success") and "position" in str(result):
                    # Extract position from response
                    import re
                    text = str(result)
                    match = re.search(r'\((\d+),\s*(\d+)\)', text)
                    if match:
                        return (int(match.group(1)), int(match.group(2)))
            return (0, 0)  # Default fallback
        except:
            return (0, 0)

    def move(self, direction, steps=1):
        """Send movement command to dungeon server with stair handling"""
        try:
            response = self.session.post(
                f"{self.base_url}/move",
                json={"direction": direction, "steps": steps},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle stairs confirmation
                if result.get("success") == False and "stairs" in result.get("message", "").lower():
                    # Auto-confirm stairs (for testing)
                    confirm_response = self.session.post(
                        f"{self.base_url}/ai-command",
                        json={"command": "yes, take the stairs"},
                        timeout=10
                    )
                    if confirm_response.status_code == 200:
                        return confirm_response.json()
                
                return result
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

@app.route('/api/test-dungeon-connection', methods=['GET'])
def test_dungeon_connection():
    """Test direct connection to dungeon server"""
    try:
        response = requests.get("http://localhost:5005/", timeout=2)
        return jsonify({
            "dungeon_server_status": response.status_code,
            "dungeon_server_response": response.text[:100] if response.text else "No content"
        })
    except Exception as e:
        return jsonify({
            "dungeon_server_status": "error",
            "error": str(e)
        })

class DungeonInputSystem:
    """Dungeon Input Phase - receives player input"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_input_phase(self, player_input, context):
        """GameEngine calls this during INPUT phase"""
        return {
            "type": "dungeon_command",
            "text": str(player_input),
            "session_id": context.get("session_id", "default"),
            "timestamp": datetime.now().isoformat()
        }

class DungeonInterpretationSystem:
    """Dungeon Interpretation Phase - uses dungeon AI via HTTP"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_interpretation_phase(self, input_data, context):
        """GameEngine calls this during INTERPRETATION phase"""
        command = input_data.get("text", "")
        
        # Send to dungeon AI
        result = self.client.send_ai_command(command)
        
        if result.get("success"):
            # Parse AI response
            import json
            try:
                ai_data = json.loads(result.get("ai_response", "{}"))
                return {
                    "intent": ai_data.get("tool", "explore"),
                    "action": ai_data.get("tool", "move"),
                    "arguments": ai_data.get("arguments", {}),
                    "confidence": 0.9,
                    "raw_text": command,
                    "dungeon_result": result
                }
            except:
                return {
                    "intent": "dungeon_action",
                    "action": "process_command",
                    "raw_text": command,
                    "dungeon_result": result
                }
        else:
            return {
                "intent": "error",
                "action": "handle_error",
                "error": result.get("error"),
                "raw_text": command
            }

class DungeonAuthoritySystem:
    """Dungeon Authority Phase - validates via HTTP"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_authority_phase(self, action, context):
        """GameEngine calls this during AUTHORITY phase"""
        # For dungeon, validation happens on the server side
        # We trust the dungeon AI's interpretation
        return {
            "valid": True,
            "action": action.get("action", "unknown"),
            "requires_dice": False,
            "message": "Dungeon action validated"
        }

class DungeonMutationSystem:
    """Dungeon Mutation Phase - executes via HTTP"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_mutation_phase(self, ruling, context):
        """GameEngine calls this during MUTATION phase"""
        action = ruling.get("action", "")
        
        # Handle different action types
        if "move" in action.lower():
            # Extract direction from action or arguments
            action_data = context.get_phase_data(GamePhase.INTERPRETATION, "action_data", {})
            args = action_data.get("arguments", {})
            
            direction = args.get("direction", "north")
            steps = args.get("steps", 1)
            
            result = self.client.move(direction, steps)
            return {
                "applied": result.get("success", False),
                "result": result,
                "action": "move"
            }
        else:
            # Generic command execution
            input_data = context.get_phase_data(GamePhase.INPUT, "raw_input", {})
            command = input_data.get("text", "")
            result = self.client.send_ai_command(command)
            return {
                "applied": result.get("success", False),
                "result": result,
                "action": "command"
            }

class DungeonConsequenceSystem:
    """Dungeon Consequence Phase - generates narration"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_consequence_phase(self, mutation_result, context):
        """GameEngine calls this during CONSEQUENCE phase"""
        result = mutation_result.get("result", {})
        ai_response = result.get("ai_response", "")
        
        # Parse AI response for narration
        import json
        try:
            ai_data = json.loads(ai_response)
            narration = ai_data.get("thoughts", "The dungeon responds...")
        except:
            narration = ai_response if ai_response else "Something happens in the dungeon..."
        
        # Get updated dungeon state
        dungeon_state = self.client.get_dungeon_state()
        
        return {
            "narration": narration,
            "dungeon_state": dungeon_state,
            "encounters": [],
            "phase_transitions": None
        }

class DungeonViewSystem:
    """Dungeon View Phase - renders dungeon state"""
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_view_phase(self, consequences, context):
        """GameEngine calls this during VIEW phase"""
        dungeon_state = self.client.get_dungeon_state()
        
        return {
            "dungeon_map": dungeon_state,
            "narration": consequences.get("narration", ""),
            "player_position": dungeon_state.get("party_position", (0, 0)),
            "visible_cells": dungeon_state.get("visible_cells", []),
            "mode": "dungeon",
            "phase_info": {
                "current_phase": "view",
                "violations": len(context.errors) if hasattr(context, 'errors') else 0,
                "warnings": len(context.warnings) if hasattr(context, 'warnings') else 0
            }
        }

class DungeonPersistenceSystem:
    """Dungeon Persistence Phase - saves dungeon state via HTTP"""
    
    def __init__(self, http_client):
        self.client = http_client
    
    def execute_persistence_phase(self, consequences, context):
        """GameEngine calls this during PERSISTENCE phase"""
        try:
            # Log the dungeon action
            from datetime import datetime
            import json
            
            # Get input data from context
            input_data = {}
            try:
                # Try to get from GameContext
                input_data = context.get_phase_data(GamePhase.INPUT, "raw_input", {})
            except:
                # Fallback
                pass
            
            command = input_data.get("text", "unknown command")
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "mode": "dungeon",
                "command": command,
                "narration": consequences.get("narration", ""),
                "dungeon_state_updated": True
            }
            
            # In a real implementation, we would save to the dungeon server
            # For now, just log it locally
            print(f"[Dungeon Persistence] {json.dumps(log_entry, indent=2)}")
            
            # Try to save dungeon state to server if it has persistence endpoint
            try:
                # Check if dungeon server has save endpoint
                response = self.client.session.post(
                    f"{self.client.base_url}/save",
                    json={"state": log_entry},
                    timeout=3
                )
                if response.status_code == 200:
                    return {"saved": True, "message": "Dungeon state saved"}
            except:
                # If no save endpoint, that's okay
                pass
            
            return {"saved": True, "message": "Dungeon action logged"}
            
        except Exception as e:
            print(f"[Dungeon Persistence Error] {e}")
            return {"saved": False, "error": str(e)}

#====+ outside of classes =====

def get_active_parties_helper():
    """Helper function to get active parties when WorldController doesn't have the method"""
    try:
        # Try to get parties from session_manager if available
        if hasattr(app, 'world_controller') and hasattr(app.world_controller, 'session_manager'):
            session_manager = app.world_controller.session_manager
            if hasattr(session_manager, 'party_views'):
                parties = []
                for party_id, members in session_manager.party_views.items():
                    parties.append({
                        'id': party_id,
                        'name': f'Party {party_id}',
                        'members': list(members) if members else [],
                        'location': 'unknown'
                    })
                return parties
        
        # Fallback to default party
        if hasattr(app, 'world_controller') and hasattr(app.world_controller, 'default_party_id'):
            return [{
                'id': app.world_controller.default_party_id,
                'name': 'Default Party',
                'members': [],
                'location': getattr(app.world_controller, 'starting_location_id', 'unknown')
            }]
        
        # Empty fallback
        return []
        
    except Exception as e:
        print(f"Error in get_active_parties_helper: {e}")
        return []

def initialize_dungeon_systems():
    """Initialize complete HTTP-based dungeon system with all phase systems"""
    print("\n" + "="*50)
    print("INITIALIZING COMPLETE DUNGEON SYSTEMS")
    print("="*50)
    
    try:
        # Create HTTP client
        dungeon_client = DungeonHTTPClient("http://localhost:5005")
        
        if not hasattr(dungeon_client, 'connected') or not dungeon_client.connected:
            print("[ERROR] Dungeon server not available at http://localhost:5005")
            print("   Start dungeon_neo_web_app.py first!")
            return None
        
        # Create all dungeon phase systems
        dungeon_systems = {
            GamePhase.INPUT: DungeonInputSystem(dungeon_client),
            GamePhase.INTERPRETATION: DungeonInterpretationSystem(dungeon_client),
            GamePhase.AUTHORITY: DungeonAuthoritySystem(dungeon_client),
            GamePhase.MUTATION: DungeonMutationSystem(dungeon_client),
            GamePhase.CONSEQUENCE: DungeonConsequenceSystem(dungeon_client),
            GamePhase.PERSISTENCE: DungeonPersistenceSystem(dungeon_client),
            GamePhase.VIEW: DungeonViewSystem(dungeon_client)
        }
        
        print("[OK] Created dungeon phase systems:")
        for phase, system in dungeon_systems.items():
            if system:
                print(f"  - {phase.value}: {type(system).__name__}")
        
        print("="*50)
        
        return {
            "systems": dungeon_systems,
            "client": dungeon_client,
            "available": True
        }
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize dungeon systems: {e}")
        import traceback
        traceback.print_exc()
        return {"available": False, "error": str(e)}

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

@app.route('/api/game/date', methods=['GET'])
def get_game_date():
    """Return formatted current date for display."""
    if not hasattr(app, 'world_controller') or app.world_controller is None:
        return "Date unavailable", 503
    try:
        date_dict = app.world_controller.campaign_state.get_current_date()
        # Format as "D3 W2 M5 Y1 - Morning" (compact)
        formatted = f"D{date_dict['day']} W{date_dict['week']} M{date_dict['month']} Y{date_dict['year']} - {date_dict['time_of_day'].capitalize()}"
        return formatted
    except Exception as e:
        return f"Date error", 500

def get_world_controller():
    """Safely get the world controller instance"""
    if hasattr(app, 'world_controller') and app.world_controller is not None:
        return app.world_controller
    else:
        print("World controller not available")
        return None

def get_active_parties_helper():
    """Helper function to get active parties when WorldController doesn't have the method"""
    try:
        # Try to get parties from session_manager if available
        if hasattr(app, 'world_controller') and hasattr(app.world_controller, 'session_manager'):
            session_manager = app.world_controller.session_manager
            if hasattr(session_manager, 'party_views'):
                parties = []
                for party_id, members in session_manager.party_views.items():
                    parties.append({
                        'id': party_id,
                        'name': f'Party {party_id}',
                        'members': list(members) if members else [],
                        'location': 'unknown'
                    })
                return parties
        
        # Fallback to default party
        if hasattr(app, 'world_controller') and hasattr(app.world_controller, 'default_party_id'):
            return [{
                'id': app.world_controller.default_party_id,
                'name': 'Default Party',
                'members': [],
                'location': getattr(app.world_controller, 'starting_location_id', 'unknown')
            }]
        
        # Empty fallback
        return []
        
    except Exception as e:
        print(f"Error in get_active_parties_helper: {e}")
        return []

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
        print("[OK] Base AI system initialized")
        
        # 2. Set up image generation paths
        model_path = Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors"
        image_output_dir = Path("static/world_images")
        t2i = TextToImage(model_path)

        # 3. Create world manager with image capabilities
        world_manager = WorldManager(ai_system=base_ai)
        print("[OK] World manager initialized")
        
        # 4. Check for existing worlds with proper error handling
        try:
            existing_worlds = world_manager.get_existing_worlds()
            
            # Ensure we have a list and it's not empty
            if isinstance(existing_worlds, list) and len(existing_worlds) > 0:
                # Load first existing world
                world_id = existing_worlds[0].get('id') if isinstance(existing_worlds[0], dict) else existing_worlds[0]
                print(f"[OK] Loading existing world: {world_id}")
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
            print(f"[OK] Created new world with ID: {world_id}")
            world_data = world_manager.load_from_db(world_id)
        
        # 5. Initialize world controller
        world_controller = WorldController(
            world_id=world_id,
            ai_system=base_ai,
            seed=42
        )
        print("[OK] World controller initialized")
        
        # 6. Initialize AI systems with proper state


        try:
            # Try the new way first
            world_controller.world_ai = WorldAI(world_controller=world_controller)
        except TypeError as e:
            # Fallback for backward compatibility
            print(f"Note: Using legacy parameter name: {e}")
            world_controller.world_ai = WorldAI(campaign_state=world_controller)

        world_controller.dungeon_ai = None  # Will be set when entering dungeon
        print("[OK] AI systems initialized")
        
        # 7. Verify everything is working
        print(f"[OK] World loaded with {len(world_controller.world_map.locations)} locations")
        print(f"[OK] Starting at: {world_controller.starting_location_id}")
        
        return world_controller, world_id
        
    except Exception as e:
        print(f"[ERROR] Error initializing world system: {e}")
        import traceback
        traceback.print_exc()
        raise

def main():
    """Main entry point for the world application with GameEngine integration"""
    try:
        world_controller, world_id = setup_world_system()
        print(f"\n[CELEBRATE] World system ready! World ID: {world_id}")
        
        # Initialize GameEngine with the world controller
        game_engine = GameEngine(world_controller)
        print(f"[OK] GameEngine initialized with {len(game_engine.systems)} phase systems")
        
        # Test the GameEngine
        test_result = game_engine.advance("test input")
        print(f"[OK] GameEngine test complete: {test_result.get('violations', 0)} violations")
        
        # Attach both to the Flask app
        app.world_controller = world_controller
        app.game_engine = game_engine
        
        return world_controller, game_engine
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize world system: {e}")
        import traceback
        traceback.print_exc()
        return None, None

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
    session_id = request.cookies.get('session_id')
    active_character_id = None
    player_logged_in = False
    if session_id:
        player = current_app.world_controller.get_player_by_session(session_id)
        if player:
            player_logged_in = True
            active_character_id = player.active_character_id
    return render_template('world.html',
                          active_character_id=active_character_id,
                          player_logged_in=player_logged_in)

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
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({'characters': []})
    player = current_app.world_controller.get_player_by_session(session_id)
    if not player:
        return jsonify({'characters': []})
    characters = []
    for char_id in player.character_ids:
        char = current_app.world_controller.character_manager.get_character(char_id)
        if char:
            characters.append(char.to_dict())
    return jsonify({'characters': characters})

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

@app.route('/api/create-character', methods=['POST'])
def create_character():
    try:
        data = request.get_json()
        session_id = request.cookies.get('session_id') or str(uuid.uuid4())
        
        # Get or create player for this session
        player = app.world_controller.get_or_create_player(session_id)
        if not player:
            return jsonify({'error': 'Unable to create or retrieve player'}), 500

        # Validate required fields
        required_fields = ['name', 'race', 'class']
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({'error': f'Missing required fields: {missing}'}), 400

        # Prepare intent for AuthoritySystem validation
        intent = {
            "intent": "character_creation",
            "parameters": {"character_data": data}
        }
        context = {"player_id": player.id}
        validation = app.world_controller.authority_system.validate_action(intent, context)
        if not validation.get("valid"):
            return jsonify({'error': validation.get('message', 'Invalid character data')}), 400

        # Create character using CharacterManager
        character = app.world_controller.character_manager.create_character(player.id, data)

        # Assign character to player (updates player's active character and caches)
        app.world_controller.character_manager.assign_character_to_player(player.id, character.id)

        # Optional: Generate a narrative event (e.g., for the DM chat)
        # This could be used to inform the player that the character was created.
        # If you have a consequence engine, you might call it here.
        if hasattr(app.world_controller, 'consequence_engine'):
            tool_result = {
                "action_type": "character_created",
                "success": True,
                "action_data": {"character": character}
            }
            app.world_controller.consequence_engine.generate_response_for_action(tool_result, context)

        return jsonify({
            'success': True,
            'character': character.to_dict(),
            'player_id': player.id
        })

    except Exception as e:
        print(f"Error in create_character: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-personal-item', methods=['POST'])
def generate_personal_item():
    data = request.get_json()
    char_concept = data.get('concept', '')
    item = world_controller.character_builder.generate_personal_item(char_concept)
    return jsonify(item)
# ===== Engine Endpoints =====

@app.route('/api/engine/status', methods=['GET'])
def engine_status():
    """Get GameEngine status and phase compliance information"""
    try:
        if not hasattr(app, 'game_engine') or app.game_engine is None:
            return jsonify({
                "status": "not_initialized",
                "message": "GameEngine not initialized"
            }), 503
        
        engine = app.game_engine
        
        # Get violations
        violations_info = engine.get_phase_violations()
        
        # Get current phase info
        current_phase = engine.current_phase.value if engine.current_phase else "unknown"
        
        # Count phase systems
        system_status = {}
        for phase, system in engine.systems.items():
            system_status[phase.value] = {
                "has_system": system is not None,
                "system_type": type(system).__name__ if system else "None"
            }
        
        return jsonify({
            "status": "active",
            "current_phase": current_phase,
            "phase_history": [phase.value for phase in engine.phase_history[-10:]],
            "system_status": system_status,
            "violations": violations_info,
            "mode": "world"  # Default mode for now
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/api/engine-test', methods=['POST'])
def engine_test():
    """Test GameEngine with various inputs"""
    try:
        data = request.get_json()
        test_input = data.get('input', 'test')
        
        if not hasattr(app, 'game_engine'):
            return jsonify({'error': 'GameEngine not initialized'})
        
        # Create context
        context = GameContext()
        
        # Run through GameEngine
        result = app.game_engine.advance(player_input=test_input, context=context)
        
        # Convert result to be JSON serializable
        serializable_result = {
            'success': True,
            'input': test_input,
            'ui_data': result.get('ui_data'),
            'current_phase': result.get('current_phase'),
            'violations': result.get('violations'),
            'warnings': result.get('warnings'),
            'context_data': {
                'errors': [str(e) for e in context.errors],
                'warnings': [str(w) for w in context.warnings]
            }
        }
        
        return jsonify(serializable_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/engine/mode', methods=['GET', 'POST'])
def engine_mode():
    """Get or set GameEngine mode"""
    if not hasattr(app, 'game_engine'):
        return jsonify({"error": "GameEngine not initialized"}), 503
    
    if request.method == 'GET':
        # Return current mode status
        status = app.game_engine.get_mode_status()
        return jsonify(status)
    
    else:  # POST        
        try:
            data = request.get_json()
        except Exception as e:
            print(f"DEBUG: JSON parse error: {e}")
            return jsonify({"error": f"JSON parse error: {str(e)}"}), 400
        
        new_mode = data.get('mode')
        
        if new_mode not in ["world", "dungeon"]:
            return jsonify({"error": "Invalid mode. Must be 'world' or 'dungeon'"}), 400
        
        try:
            app.game_engine.set_mode(new_mode)
            return jsonify({
                "success": True,
                "message": f"Switched to {new_mode} mode",
                "current_mode": app.game_engine.current_mode
            })
        except Exception as e:
            print(f"DEBUG: set_mode error: {e}")
            return jsonify({"error": str(e)}), 500

@app.route('/api/dungeon/status', methods=['GET'])
def dungeon_status():
    """Check dungeon system connectivity"""
    try:
        # Check if dungeon server is running
        dungeon_running = False
        try:
            response = requests.get("http://localhost:5005/", timeout=2)
            dungeon_running = response.status_code == 200
        except:
            dungeon_running = False
        
        return jsonify({
            "dungeon_server": {
                "url": "http://localhost:5005",
                "running": dungeon_running,
                "status": "connected" if dungeon_running else "disconnected"
            },
            "world_app": {
                "mode": app.game_engine.current_mode if hasattr(app, 'game_engine') else "unknown",
                "has_dungeon_systems": hasattr(app, 'dungeon_systems')
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dungeon/command', methods=['POST'])
def dungeon_command():
    """Send a command to the dungeon system through HTTP bridge"""
    try:
        if not hasattr(app, 'dungeon_systems') or not app.dungeon_systems:
            return jsonify({
                "success": False,
                "error": "Dungeon systems not initialized"
            })
        
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({"success": False, "error": "No command provided"})
        
        # Get the HTTP client
        dungeon_client = app.dungeon_systems.get('client')
        if not dungeon_client or not dungeon_client.connected:
            return jsonify({
                "success": False,
                "error": "Dungeon client not connected",
                "dungeon_server": "http://localhost:5005"
            })
        
        # Send command directly to dungeon server
        result = dungeon_client.send_ai_command(command)
        
        return jsonify({
            "success": True,
            "command": command,
            "result": result,
            "mode": app.game_engine.current_mode if hasattr(app, 'game_engine') else "unknown"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/debug/dungeon-structure', methods=['GET'])
def debug_dungeon_structure():
    """Debug endpoint to see what dungeon_neo files exist"""
    try:
        dungeon_path = None
        
        # Check multiple possible locations
        possible_paths = [
            "dungeon_neo",
            "../dungeon_neo", 
            "./dungeon_neo",
            os.path.join(os.path.dirname(__file__), "dungeon_neo")
        ]
        
        found_files = {}
        
        for path in possible_paths:
            if os.path.exists(path):
                dungeon_path = path
                # List files
                files = []
                for root, dirs, filenames in os.walk(path):
                    for filename in filenames:
                        if filename.endswith('.py'):
                            rel_path = os.path.relpath(os.path.join(root, filename), path)
                            files.append(rel_path)
                found_files[path] = files
                
        if not found_files:
            return jsonify({
                "status": "not_found",
                "message": "dungeon_neo directory not found in any expected location",
                "current_directory": os.getcwd()
            })
            
        return jsonify({
            "status": "found",
            "paths_found": list(found_files.keys()),
            "files": found_files,
            "current_directory": os.getcwd()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug/check-dungeon-endpoints', methods=['GET'])
def check_dungeon_endpoints():
    """Check what endpoints the dungeon web app (port 5005) exposes"""
    try:
        # Try to get the root endpoint to see what's available
        response = requests.get("http://localhost:5005/", timeout=2)
        endpoints = {
            "root": response.status_code
        }
        
        # Try common endpoints
        common_endpoints = [
            "/ai-command",
            "/move",
            "/dungeon-state",
            "/dungeon",
            "/api/status"
        ]
        
        for endpoint in common_endpoints:
            try:
                resp = requests.get(f"http://localhost:5005{endpoint}", timeout=1)
                endpoints[endpoint] = resp.status_code
            except:
                endpoints[endpoint] = "timeout or error"
        
        return jsonify({
            "dungeon_endpoints": endpoints,
            "note": "Status 200 means endpoint exists (GET), others may need POST"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)})

# ===== Character basic =====

@app.route('/character/<character_id>/basic')
def character_basic(character_id):
    """Return a partial HTML with basic character info."""
    if not character_id:
        return "", 204
    character = current_app.world_controller.character_manager.get_character(character_id)
    if not character:
        return "", 204
    return render_template('partials/character_basic.html', character=character)

# ===== Narrative System Endpoints (Phase 2) =====

@app.route('/character/<character_id>/narrative')
def character_narrative(character_id):
    """Return the narrative partial (backstory, connections, vows, secrets) for a character."""
    if not character_id:
        return "", 204  # No content
    character = current_app.world_controller.character_manager.get_character(character_id)
    if not character:
        return "", 204
    return render_template('partials/character_narrative.html', character=character)


@app.route('/character/<character_id>/start-backstory', methods=['POST'])
def start_backstory(character_id):
    """Start guided backstory creation for a character."""
    character = current_app.world_controller.character_manager.get_character(character_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404

    narrative = current_app.world_controller.narrative_system
    if not hasattr(narrative, 'backstory_sessions'):
        narrative.backstory_sessions = {}

    # Initialise a new backstory session (phase = 'origin')
    session_state = {
        'phase': 'origin',
        'backstory': {},
        'conversation': []
    }
    narrative.backstory_sessions[character_id] = session_state

    # Get the first DM prompt
    result = narrative.guide_backstory_creation(character_id, None, session_state)
    if result.get('responses'):
        first = result['responses'][0]
        if hasattr(first, 'to_dict'):
            first = first.to_dict()
        return jsonify({
            'speaker': first.get('speaker', 'DM'),
            'content': first.get('content', ''),
            'type': first.get('type', 'narration')
        })
    else:
        return jsonify({"error": "No response from narrative system"}), 500


@app.route('/character/<character_id>/backstory-continue', methods=['POST'])
def backstory_continue(character_id):
    """Send a message during backstory creation."""
    data = request.get_json()
    message = data.get('message', '')

    narrative = current_app.world_controller.narrative_system
    if not hasattr(narrative, 'backstory_sessions') or character_id not in narrative.backstory_sessions:
        return jsonify({"error": "No active backstory session"}), 400

    session_state = narrative.backstory_sessions[character_id]
    result = narrative.guide_backstory_creation(character_id, message, session_state)

    # Update stored state
    narrative.backstory_sessions[character_id] = result['new_state']

    # Convert responses to JSON-serializable dicts
    responses = []
    for r in result.get('responses', []):
        if hasattr(r, 'to_dict'):
            responses.append(r.to_dict())
        else:
            responses.append(r)

    # If session finished, remove it
    if result['new_state'] is None:
        del narrative.backstory_sessions[character_id]

    return jsonify({"responses": responses})


@app.route('/character/<character_id>/build-connections', methods=['POST'])
def build_connections(character_id):
    """Manually trigger connection web generation for a character."""
    narrative = current_app.world_controller.narrative_system
    narrative.build_connection_web_for_character(character_id)
    return jsonify({"success": True})
        
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
        "parties": get_active_parties_helper(), #app.world_controller.get_active_parties(),
        #"default_party": app.world_controller.default_party_id
        "default_party": getattr(app.world_controller, 'default_party_id', 'default')
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
            "parties": get_active_parties_helper(), #app.world_controller.get_active_parties(),
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

# ===== begin: Character Creation HTMX Endpoints =====
@app.route('/character-creation/random-all', methods=['POST'])
def random_all():
    raw = request.form.to_dict(flat=False)
    data = {}
    for key, values in raw.items():
        if key == 'skills':
            data[key] = values
        else:
            data[key] = values[0] if values else ''

    from world import character_generator, dnd_data   # use dnd_data directly
    complete = character_generator.random_fill_all(data)   # will be updated separately

    context = {
        'races': dnd_data.get_race_list(),
        'classes': dnd_data.get_class_list(),
        'backgrounds': dnd_data.get_background_list(),
        'skills_list': dnd_data.get_skill_list(),
        'ability_names': dnd_data.get_ability_score_lower_names(),
        'ability_display': dnd_data.get_ability_score_full_names(),
    }
    context.update(complete)

    # Class‑specific data – adapt from OGClass
    class_name = context.get('class')
    if class_name:
        og_class = dnd_data.OGClass.get(class_name.lower())
        if og_class:
            # Approximate hit die from hp_per_level (hp_per_level * 4 gives a die size)
            approx_hit_die = og_class.hp_per_level * 4
            context['hit_die'] = f'd{approx_hit_die}'   # e.g., d8 for hp_per_level=2
            skill_choices = og_class.skill_choices()
            context['class_skill_choose'] = skill_choices['choose']
            context['class_skill_options'] = [s.name for s in skill_choices['from']]
        else:
            context['hit_die'] = None
            context['class_skill_choose'] = 0
            context['class_skill_options'] = []
    else:
        context['hit_die'] = None
        context['class_skill_choose'] = 0
        context['class_skill_options'] = []

    return render_template('partials/creation_form.html', **context)
    
@app.route('/character-creation/submit', methods=['POST'])
def submit_character():
    session_id = request.cookies.get('session_id')
    if not session_id:
        return jsonify({"error": "No session"}), 401   # frontend will show player modal

    player = current_app.world_controller.get_player_by_session(session_id)
    if not player:
        return jsonify({"error": "No player selected"}), 401
        
    data = request.form
    session_id = request.cookies.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True
    else:
        is_new_session = False

    player = app.world_controller.get_or_create_player(session_id)
    if not player:
        return render_template('partials/error_message.html', errors=["Could not identify player"]), 400

    char_data = data.to_dict()
    skills = request.form.getlist('skills')
    if skills:
        char_data['skills'] = skills
    char_data['player_id'] = player.id

    from world import character_generator
    result = character_generator.create_character_from_form(
        char_data,
        builder=app.world_controller.character_builder
    )
    print(f"Character creation result: {result}")

    if result['success']:
        print(f"Character created: {result['character'].id}, name={result['character'].name}")
        char = result['character']
        char.player_id = player.id
        # Ensure character is in the manager's cache
        if not app.world_controller.character_manager.get_character(char.id):
            app.world_controller.character_manager.add_character(char)
        app.world_controller.character_manager.assign_character_to_player(player.id, char.id)
        print("Character assigned to player")
        
        # Rest of the response...
        response = make_response("""
            <script>
                location.reload();
            </script>
        """)
        if is_new_session:
            response.set_cookie(
                'session_id', session_id,
                max_age=60*60*24*7, path='/',
                secure=False, httponly=True, samesite='Lax'
            )
        return response
    else:
        print(f"Character creation failed: {result.get('errors')}")
        return render_template('partials/error_message.html', errors=result['errors']), 400

@app.route('/character-creation/form')
def character_creation_form():
    from world import dnd_data

    context = {
        'races': dnd_data.get_race_list(),
        'classes': dnd_data.get_class_list(),
        'backgrounds': dnd_data.get_background_list(),
        'skills_list': dnd_data.get_skill_list(),
        'ability_names': dnd_data.get_ability_score_lower_names(),
        'ability_display': dnd_data.get_ability_score_full_names(),
        'name': '',
        'race': '',
        'class': '',
        'background': '',
        'selected_skills': [],
        'ability_scores': {},
        'hit_die': None,
        'class_skill_choose': 0,
        'class_skill_options': []
    }
    return render_template('partials/creation_form.html', **context)

@app.route('/character-creation/update-form', methods=['POST'])
def update_character_form():
    # Get all form fields (including multi‑value 'skills')
    form_data = request.form.to_dict(flat=False)
    
    # Build a dict with single values (except skills)
    data = {}
    for key, values in form_data.items():
        if key == 'skills':
            data['selected_skills'] = values   # keep as list
        else:
            data[key] = values[0] if values else ''
    
    # Ensure all expected keys exist (set defaults if missing)
    data.setdefault('name', '')
    data.setdefault('race', '')
    data.setdefault('class', '')
    data.setdefault('background', '')
    data.setdefault('brawn', '1')
    data.setdefault('finesse', '1')
    data.setdefault('wits', '1')
    data.setdefault('will', '1')
    data.setdefault('selected_skills', [])
    
    # Convert ability scores to int (they come as strings)
    for attr in ['brawn', 'finesse', 'wits', 'will']:
        try:
            data[attr] = int(data[attr])
        except ValueError:
            data[attr] = 1   # fallback
    
    # Build full context for the template
    from world import dnd_data
    context = {
        # Static lists from og_data (now dnd_data)
        'races': dnd_data.get_race_list(),
        'classes': dnd_data.get_class_list(),
        'backgrounds': dnd_data.get_background_list(),
        'skills_list': dnd_data.get_skill_list(),
        'ability_names': dnd_data.get_ability_score_lower_names(),   # ['brawn', 'finesse', ...]
        'ability_display': dnd_data.get_ability_score_full_names(),  # ['Brawn', 'Finesse', ...]
        
        # Current values (from form submission)
        'name': data['name'],
        'race': data['race'],
        'class': data['class'],
        'background': data['background'],
        'ability_scores': {
            'brawn': data['brawn'],
            'finesse': data['finesse'],
            'wits': data['wits'],
            'will': data['will'],
        },
        'selected_skills': data['selected_skills'],
        'hit_die': None,
        'class_skill_choose': 0,
        'class_skill_options': []
    }
    
    return render_template('partials/creation_form.html', **context)

@app.route('/character-creation/help', methods=['POST'])
def character_creation_help():
    question = request.form.get('question', '').lower()
    response = "I can help with races, classes, attributes, skills, and backgrounds. Try asking about 'Warrior' or 'Brawn'."

    # Simple keyword matching using og_data
    from world import dnd_data

    # Check races
    for race in dnd_data.get_race_list():
        if race.lower() in question:
            race_obj = dnd_data.Race.get(race)
            if race_obj:
                bonus = race_obj.mechanical_bonus
                response = f"{race}: {bonus.get('description', 'A playable race.')}"
            break
    else:
        # Check classes
        for cls in dnd_data.get_class_list():
            if cls.lower() in question:
                class_obj = dnd_data.OGClass.get(cls)
                if class_obj:
                    response = f"{cls}: HP per level {class_obj.hp_per_level}, SP per level {class_obj.sp_per_level}. Core: {class_obj.core_mechanic.get('description', '')}"
                break
        else:
            # Check attributes
            for attr in dnd_data.get_ability_score_full_names():
                if attr.lower() in question:
                    attr_key = attr.lower()
                    attr_obj = dnd_data.Attribute.get(attr_key)
                    if attr_obj:
                        response = f"{attr}: {attr_obj.governs}"
                    break
            else:
                # Check skills
                for skill in dnd_data.get_skill_list():
                    if skill.lower() in question:
                        skill_obj = dnd_data.Skill.get(skill)
                        if skill_obj:
                            response = f"{skill}: {skill_obj.covers}"
                        break

    return render_template('partials/chat_message.html', sender='Helper', message=response)

@app.route('/api/dm-response', methods=['POST'])
def dm_response():
    try:
        data = request.get_json()
        message = data.get('message')
        character_id = data.get('character_id')
        session_id = request.cookies.get('session_id')
        is_new_session = False
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True

        player = app.world_controller.get_or_create_player(session_id)

        if character_id and character_id not in player.character_ids:
            return jsonify({'error': 'Character does not belong to player'}), 400

        active_character_id = character_id or player.active_character_id

        # ---------- CHARACTER CREATION PATH (no active character) ----------
        if not active_character_id:
            result = app.world_controller.dm_chat_handler.process_message(
                session_id, message, character_id=None
            )
            responses = [{
                'speaker': r.speaker,
                'content': r.content,
                'type': r.dialog_type
            } for r in result.get('narrative', [])]

            response_data = {
                'responses': responses,
                'tool_result': result.get('tool_result'),
                'session_id': session_id,
                'character_id': None,
                'player_id': player.id
            }

        # ---------- IN‑GAME PATH (character exists) ----------
        else:
            from engine.game_engine import GamePhase, GameContext
            context = GameContext()
            context.set_phase_data(GamePhase.INPUT, "session_id", session_id)
            context.set_phase_data(GamePhase.INPUT, "character_id", active_character_id)
            context.set_phase_data(GamePhase.INPUT, "player_id", player.id)

            engine_result = app.game_engine.advance(player_input=message, context=context)
            ui_data = engine_result.get('ui_data', {})
            narration = ui_data.get('narration', '')

            response_data = {
                'responses': [{
                    'speaker': 'DM',
                    'content': narration or "The DM considers your words...",
                    'type': 'narration'
                }],
                'session_id': session_id,
                'character_id': active_character_id,
                'player_id': player.id
            }

        response = jsonify(response_data)
        if is_new_session:
            response.set_cookie(
                'session_id', session_id,
                max_age=60*60*24*7, path='/',
                secure=False, httponly=True, samesite='Lax'
            )
        return response

    except Exception as e:
        print(f"Error in dm-response: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
def legacy_dm_response():
    """Fallback to original dm-response logic"""
    try:
        data = request.get_json()
        message = data.get('message')
        character_id = data.get('character_id')
        
        session_id = request.cookies.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
        
        player = app.world_controller.get_or_create_player(session_id)
        
        if character_id and character_id not in player.character_ids:
            return jsonify({'error': 'Character does not belong to player'}), 400
        
        active_character_id = character_id or player.active_character_id
        if active_character_id:
            player.set_active_character(active_character_id)
        
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
            'player_id': player.id
        }
        
        response = jsonify(response_data)
        response.set_cookie(
            'session_id', 
            session_id, 
            max_age=60*60*24*7,
            path='/',
            secure=False,
            httponly=True,
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
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
        'parties': get_active_parties_helper(), #app.world_controller.get_active_parties(),
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
    """Initialize the Flask application with world controller and GameEngine"""
    try:
        world_controller, game_engine = main()
        
        if world_controller is not None and game_engine is not None:
            # Attach to app
            app.world_controller = world_controller
            app.game_engine = game_engine
            
            # Try to initialize dungeon systems
            dungeon_systems = initialize_dungeon_systems()
            if dungeon_systems:
                print("[OK] Dungeon systems initialized")
                # Connect dungeon delegates to GameEngine
                success = game_engine.set_dungeon_delegates(dungeon_systems)
                if success:
                    print("[OK] Dungeon delegates connected to GameEngine")
                    # Store dungeon systems in app context
                    app.dungeon_systems = dungeon_systems
                else:
                    print("[WARNING] Failed to connect dungeon delegates")
            else:
                print("[WARNING] Dungeon systems not available (mode switching will fail)")
            
            # Display connection information
            print("[WORLD] DUNGEON WORLD SERVER WITH GAMEENGINE")
            print("Server running on:")
            print(f"Local URL: http://localhost:5000")
            print(f"Network URL: http://{get_ip_address()}:5000")
            
            print(f"[OK] GameEngine active with {len(game_engine.systems)} phase systems")
            print(f"[OK] Current mode: {game_engine.current_mode}")
            
            return world_controller, game_engine
        else:
            print("[ERROR] Failed to initialize world controller or GameEngine")
            return None, None
    except Exception as e:
        print(f"[ERROR] Error initializing app: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# ===== Player Selection Endpoints =====

@app.route('/api/players', methods=['GET'])
def list_players():
    """Return list of all existing players (id, name)."""
    conn = Database.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM players ORDER BY name")
            players = [{"id": str(row[0]), "name": row[1]} for row in cur.fetchall()]
        return jsonify({"players": players})
    finally:
        Database.return_connection(conn)


@app.route('/api/select-player', methods=['POST'])
def select_player():
    """Set session cookie for an existing player."""
    data = request.get_json()
    player_id = data.get('player_id')
    if not player_id:
        return jsonify({"error": "No player_id provided"}), 400

    # Load player from database (or from cache)
    player = current_app.world_controller.get_player_by_id(player_id)
    if not player:
        return jsonify({"error": "Player not found"}), 404

    # Create a new session ID
    session_id = str(uuid.uuid4())
    current_app.world_controller.session_players[session_id] = player.id

    response = jsonify({"success": True, "player": player.to_dict()})
    response.set_cookie(
        'session_id', session_id,
        max_age=60*60*24*7, path='/',
        secure=False, httponly=True, samesite='Lax'
    )
    return response


@app.route('/api/create-player', methods=['POST'])
def create_player():
    """Create a new player with a friendly name."""
    data = request.get_json()
    player_name = data.get('name', 'Adventurer').strip()
    if not player_name:
        player_name = "Adventurer"

    player = Player(name=player_name)
    current_app.world_controller.players[player.id] = player
    current_app.world_controller._save_player_to_db(player)

    # Create a new session ID
    session_id = str(uuid.uuid4())
    current_app.world_controller.session_players[session_id] = player.id

    response = jsonify({"success": True, "player": player.to_dict()})
    response.set_cookie(
        'session_id', session_id,
        max_age=60*60*24*7, path='/',
        secure=False, httponly=True, samesite='Lax'
    )
    return response

if __name__ == '__main__':
    # Only initialize when not in reloader
    if not os.environ.get('WERKZEUG_RUN_MAIN'):
        world_controller = initialize_app()
    
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, use_reloader=False) 