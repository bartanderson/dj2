from flask import render_template, Flask, send_file, request, jsonify, session, g
from core.dungeon import DungeonSystem
from dungeon_neo.test_campaign import TestCampaign
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import uuid
import logging
import json
import requests

# Global dungeon cache
DUNGEON_CACHE = {}

app = Flask(__name__)
app.secret_key = 'dungeon_secret_key'
app.campaign = TestCampaign()

# In-memory dungeon storage
dungeon_states = {}  # location_id -> dungeon

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('dungeon_app')
logger.setLevel(logging.ERROR)

# ===== CORS CODE =====
@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return "", 200

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response
# ===== END CORS CODE =====

@app.before_request
def init_session_and_dungeon():
    # Get game_id from multiple sources
    game_id = None
    
    # Priority 1: Explicit game_id from query params (GET requests)
    if request.args.get('game_id'):
        game_id = request.args.get('game_id')
        logger.info(f"Using game_id from query params: {game_id}")
    
    # Priority 2: Explicit game_id from JSON body (POST requests)
    elif request.is_json and request.json and 'game_id' in request.json:
        game_id = request.json.get('game_id')
        logger.info(f"Using game_id from JSON body: {game_id}")
    
    # Priority 3: Session-based game_id (for standalone page)
    if not game_id:
        # Ensure session exists
        if 'session_id' not in session:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            logger.info(f"Created new session: {session_id}")
        
        # CRITICAL FIX: Always use session_id as game_id when no explicit game_id provided
        # This was the bug: original code had 'else:' here, so game_id was only set if session already existed
        game_id = session['session_id']
        logger.info(f"Using session-based game_id: {game_id}")
    
    # Get or create dungeon for game_id
    if game_id not in DUNGEON_CACHE:
        dungeon = DungeonSystem()
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        if dungeon.generate(dungeon_type):
            DUNGEON_CACHE[game_id] = dungeon
            logger.info(f"Created new dungeon for game_id: {game_id}")
        else:
            logger.error(f"Failed to create dungeon for game_id: {game_id}")
    
    # Attach to request context
    g.dungeon = DUNGEON_CACHE.get(game_id)
    g.game_id = game_id

@app.route('/')
def index():
    return render_template('dungeon.html')

@app.route('/dungeon-image')
def dungeon_image():
    game_id = request.args.get('game_id')
    debug = request.args.get('debug', 'false').lower() == 'true'
    if not game_id:
        return create_placeholder_image("Missing game_id")
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return create_placeholder_image("Dungeon not found")
    try:
        img = dungeon.get_image(debug)
        return serve_pil_image(img)
    except Exception as e:
        logger.error(f"Rendering error: {str(e)}")
        return create_placeholder_image(f"Rendering error: {str(e)}")
        
@app.route('/move', methods=['POST'])
def move():
    data = request.json or {}
    game_id = data.get('game_id')
    direction = data.get('direction')
    steps = data.get('steps', 1)
    confirm_stairs = data.get('confirm_stairs', False)   # <-- add this
    if not game_id:
        return jsonify({"success": False, "message": "Missing game_id"})
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return jsonify({"success": False, "message": "Dungeon not found"})
    try:
        result = dungeon.state.movement.move_party(direction, steps, confirm_stairs)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Movement error: {str(e)}")
        return jsonify({"success": False, "message": f"Movement error: {str(e)}"})

@app.route('/position', methods=['GET'])
def get_position():
    game_id = request.args.get('game_id')
    if not game_id:
        return jsonify({"error": "Missing game_id"})
    dungeon = dungeon_states.get(game_id)
    print(f"[DEBUG] /position called with game_id: {game_id}")
    print(f"[DEBUG] dungeon_states keys: {list(dungeon_states.keys())}")
    print(f"[DEBUG] parties in dungeon: {dungeon.state.parties.keys()}")
    if not game_id:
        return jsonify({"error": "Missing game_id"})
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return jsonify({"error": "Dungeon not found"})
    try:
        position = dungeon.state.party_position
        return jsonify({"position": position, "game_id": game_id})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug-state', methods=['GET'])
def debug_state():
    game_id = request.args.get('game_id')
    if not game_id:
        game_id = session.get('active_game_id')
    if not game_id:
        return jsonify({"error": "Missing game_id"})
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return jsonify({"error": "Dungeon not found"})
    return jsonify({
        "game_id": game_id,
        "has_state": hasattr(dungeon, 'state'),
        "party_position": dungeon.state.party_position if hasattr(dungeon.state, 'party_position') else "No party_position",
        "state_type": type(dungeon.state).__name__
    })

@app.route('/ai-command', methods=['POST'])
def ai_command():
    data = request.json or {}
    game_id = data.get('game_id')
    if not game_id:
        return jsonify({"success": False, "message": "Missing game_id"})
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return jsonify({"success": False, "message": "Dungeon not found"})
    command = data.get('command', '')
    try:
        result = dungeon.process_ai_command(command)
        return jsonify(result)
    except Exception as e:
        logger.error(f"AI error: {str(e)}")
        return jsonify({"success": False, "message": f"AI error: {str(e)}"})

@app.route('/api/new-game', methods=['POST'])
def new_game():
    data = request.json or {}
    game_id = data.get('game_id', f"game_{uuid.uuid4()}")
    print(f"[DEBUG] /api/new-game called with game_id: {game_id}")
    if game_id not in dungeon_states:
        print(f"[DEBUG] Creating new dungeon for {game_id}")
        dungeon = DungeonSystem()
        # Use a default location type or get from campaign
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        if dungeon.generate(dungeon_type):
            dungeon_states[game_id] = dungeon
            print(f"[DEBUG] Dungeon created, now dungeon_states keys: {list(dungeon_states.keys())}")
            return jsonify({"game_id": game_id, "created": True})
        else:
            print(f"[DEBUG] Dungeon generation failed")
            return jsonify({"error": "Failed to create dungeon"}), 500
    return jsonify({"game_id": game_id, "exists": True})

@app.route('/reset', methods=['POST'])
def reset_dungeon():
    data = request.json or {}
    game_id = data.get('game_id')
    if not game_id:
        return jsonify(success=False, message="Missing game_id")
    dungeon = dungeon_states.get(game_id)
    if not dungeon:
        return jsonify(success=False, message="Dungeon not found")
    location = app.campaign.get_location("test_dungeon")
    dungeon_type = location["dungeon_type"] if location else "cave"
    success = dungeon.reset_dungeon(dungeon_type)
    return jsonify(success=success, message="Dungeon reset" if success else "Reset failed")

@app.route('/api/dungeon/enter', methods=['POST'])
def dungeon_enter():
    data = request.get_json()
    party_id = data.get('party_id')
    location_id = data.get('location_id')
    print(f"[DEBUG] Enter: party_id={party_id}, location_id={location_id}")
    world_url = data.get('world_url', 'http://localhost:5000')
    if not party_id or not location_id:
        return jsonify({"success": False, "message": "Missing party_id or location_id"})

    # Fetch party data from world server
    try:
        resp = requests.get(f"{world_url}/api/party/{party_id}", timeout=5)
        if resp.status_code != 200:
            return jsonify({"success": False, "message": "Failed to fetch party data"})
        party_data = resp.json()
        characters = party_data.get('characters', [])
    except Exception as e:
        return jsonify({"success": False, "message": f"Error fetching party data: {str(e)}"})

    # Get or create dungeon state
    dungeon = dungeon_states.get(location_id)
    if not dungeon:
        dungeon = DungeonSystem(enable_ai=True)
        success = dungeon.generate()
        if not success:
            return jsonify({"success": False, "message": "Failed to generate dungeon"})
        dungeon.location_id = location_id
        dungeon_states[location_id] = dungeon

    print(f"[DEBUG] /api/dungeon/enter: party_id={party_id}, characters count={len(characters)}")
    dungeon.state.add_party(party_id, characters)
    print(f"[DEBUG] After add_party, dungeon.state.parties keys: {list(dungeon.state.parties.keys())}")
    dungeon.world_url = world_url

    return jsonify({
        "success": True,
        "dungeon_id": location_id,
        "message": f"Party entered dungeon. {len(dungeon.state.parties)} party(s) now inside."
    })

@app.route('/api/dungeon/exit', methods=['POST'])
def dungeon_exit():
    """Party exits dungeon. Send updates back to world."""
    data = request.get_json()
    party_id = data.get('party_id')
    print(f"[DEBUG] Exit: party_id={party_id}")
    exiting_character_ids = data.get('exiting_character_ids', [])
    all_characters = data.get('all_characters', False)
    
    print(f"[Dungeon] Exit request: party={party_id}, exiting={len(exiting_character_ids)}, all={all_characters}")
    
    # Find which dungeon this party is in
    dungeon = None
    location_id = None
    for loc_id, d in dungeon_states.items():
        print(f"[DEBUG] Checking {loc_id}: parties = {d.state.parties.keys()}")
        if party_id in d.state.parties:
            dungeon = d
            location_id = loc_id
            break
    
    if not dungeon:
        return jsonify({"success": False, "message": "Party not found in any dungeon"}), 404
    
    party = dungeon.state.get_party(party_id)
    print(f"[DEBUG] Party object from state: {party}")
    if party:
        print(f"[DEBUG] Party characters list: {party.get('characters')}")
        print(f"[DEBUG] Length of characters: {len(party.get('characters', []))}")

    if not party:
        return jsonify({"success": False, "message": "Party not found"}), 404
    
    # Determine which characters are exiting
    if all_characters:
        exiting_characters = party["characters"]
        remaining_characters = []
        print(f"[DEBUG] all_characters True, exiting_characters count: {len(exiting_characters)}")
    else:
        exiting_characters = [c for c in party["characters"] if c.get("id") in exiting_character_ids]
        remaining_characters = [c for c in party["characters"] if c.get("id") not in exiting_character_ids]
        print(f"[DEBUG] partial exit, exiting count: {len(exiting_characters)}")
    
    # Calculate elapsed time
    elapsed = getattr(dungeon, 'elapsed_minutes', 0)
    
    # Send exiting characters back to world
    if exiting_characters:
        import requests
        try:
            world_response = requests.post(
                f"{dungeon.world_url}/api/dungeon/exit",
                json={
                    "party_id": party_id,
                    "characters": exiting_characters,
                    "elapsed_minutes": elapsed,
                    "partial_exit": len(remaining_characters) > 0,
                    "remaining_characters": [c["id"] for c in remaining_characters]
                },
                timeout=5
            )
            print(f"[Dungeon] World response: {world_response.status_code}")
        except Exception as e:
            print(f"[Dungeon] Error calling world: {e}")
    
    # Update dungeon state
    if remaining_characters:
        # Update party with remaining characters
        party["characters"] = remaining_characters
        dungeon.state.parties[party_id] = party
        print(f"[Dungeon] Party {party_id} now has {len(remaining_characters)} characters")
    else:
        # Remove party from dungeon
        del dungeon.state.parties[party_id]
        if hasattr(dungeon.state, 'party_positions') and party_id in dungeon.state.party_positions:
            del dungeon.state.party_positions[party_id]
        print(f"[Dungeon] Party {party_id} removed from dungeon")
    
    # If no parties left, unload dungeon state
    if not dungeon.state.parties:
        print(f"[Dungeon] No parties left in dungeon {location_id}, unloading")
        del dungeon_states[location_id]
    
    return jsonify({
        "success": True,
        "message": f"{len(exiting_characters)} character(s) exited. {len(remaining_characters)} remain in dungeon."
    })
    
# ---------- HELPER FUNCTIONS ----------
def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'PNG', quality=100)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

def create_placeholder_image(message):
    img = Image.new('RGB', (800, 600), color='black')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Basic text wrapping
    lines = []
    words = message.split()
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if draw.textlength(test_line, font=font) > 750:
            lines.append(line)
            line = word
        else:
            line = test_line
    lines.append(line)
    
    y = 250
    for line in lines:
        draw.text((50, y), line, fill='white', font=font)
        y += 30
    
    return serve_pil_image(img)

if __name__ == '__main__':
    app.run(debug=True, port=5005, use_reloader=False)