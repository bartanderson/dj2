# dungeon_neo_web_app.py
# coding: utf-8
from flask import Flask, send_file, request, jsonify, session, g
from core.dungeon_standalone import DungeonSystem
from dungeon_neo.test_campaign import TestCampaign
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import uuid
import logging

# Global dungeon cache
DUNGEON_CACHE = {}

app = Flask(__name__)
app.secret_key = 'standalone_secret_key'
# Session configuration for cross-origin requests
app.config.update(
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=False,   # Set to True if using HTTPS in production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_PATH='/'
)
app.campaign = TestCampaign()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('standalone_app')

# ===== ADD CORS CODE RIGHT HERE =====
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
    # 1. Try to get game_id from query string or POST body
    game_id = request.args.get('game_id')
    if not game_id and request.method == 'POST' and request.is_json:
        game_id = request.json.get('game_id')
    
    # 2. If not provided, use session (or create new one)
    if not game_id:
        game_id = session.get('dungeon_game_id')
        if game_id:
            logger.info(f"Using game_id from session: {game_id}")
        else:
            game_id = str(uuid.uuid4())
            session['dungeon_game_id'] = game_id
            session.modified = True
            logger.info(f"New session created: {game_id}")
    else:
        # Store in session for future requests
        session['dungeon_game_id'] = game_id
        session.modified = True
        logger.info(f"Using provided game_id: {game_id}")
    
    # 3. Get or create dungeon
    if game_id not in DUNGEON_CACHE:
        dungeon = DungeonSystem()
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        if dungeon.generate(dungeon_type):
            DUNGEON_CACHE[game_id] = dungeon
            logger.info(f"Created dungeon for {game_id}")
        else:
            logger.error(f"Dungeon init failed for {game_id}")
    
    g.dungeon = DUNGEON_CACHE[game_id]
    g.game_id = game_id

@app.route('/')
def index():
    return send_file('templates\\dungeon_standalone.html')

@app.route('/dungeon-image')
def dungeon_image():
    debug = request.args.get('debug', 'false').lower() == 'true'
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return create_placeholder_image("Dungeon not initialized")
    
    try:
        img = g.dungeon.get_image(debug)
        return serve_pil_image(img)
    except Exception as e:
        logger.exception("Image rendering error")
        return create_placeholder_image(f"Rendering error: {str(e)}")

@app.route('/move', methods=['POST'])
def move():
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify({"success": False, "message": "Dungeon not initialized"})
    
    data = request.json
    logger.info(f"/move received data: {data}")
    direction = data.get('direction')
    steps = data.get('steps', 1)
    
    try:
        result = g.dungeon.state.movement.move_party(direction, steps)
        # No need to store dungeon in session – cache already holds it
        logger.info(f"Move: new position {g.dungeon.state.party_position}")
        return jsonify(result)
    except Exception as e:
        logger.exception("Movement error")
        return jsonify({"success": False, "message": f"Movement error: {str(e)}"})

@app.route('/position', methods=['GET'])
def get_position():
    """Get current party position"""
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify({"error": "Dungeon not initialized"})
    
    try:
        # Direct access to party_position as you said
        position = g.dungeon.state.party_position
        return jsonify({"position": position})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/debug-state', methods=['GET'])
def debug_state():
    """Debug endpoint to see what's in the dungeon state"""
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify({"error": "No dungeon"})
    
    dungeon = g.dungeon
    return jsonify({
        "has_state": hasattr(dungeon, 'state'),
        "state_attrs": dir(dungeon.state) if hasattr(dungeon, 'state') else [],
        "party_position": dungeon.state.party_position if hasattr(dungeon.state, 'party_position') else "No party_position",
        "state_type": type(dungeon.state).__name__
    })

@app.route('/ai-command', methods=['POST'])
def ai_command():
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify({"success": False, "message": "Dungeon not initialized"})
    
    data = request.json
    command = data.get('command', '')
    
    try:
        result = g.dungeon.process_ai_command(command)
        return jsonify(result)
    except Exception as e:
        logger.exception("AI error")
        return jsonify({"success": False, "message": f"AI error: {str(e)}"})

@app.route('/api/new-game', methods=['POST'])
def new_game():
    """Create a new game instance with a unique ID (overwrites session)."""
    data = request.json
    game_id = data.get('game_id', f"game_{uuid.uuid4()}")
    
    if game_id not in DUNGEON_CACHE:
        dungeon = DungeonSystem()
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        if dungeon.generate(dungeon_type):
            DUNGEON_CACHE[game_id] = dungeon
            # Update session to use this new game_id
            session['game_id'] = game_id
            session.modified = True
            return jsonify({"game_id": game_id, "created": True})
        else:
            return jsonify({"error": "Failed to create dungeon"}), 500
    
    return jsonify({"game_id": game_id, "exists": True})

@app.route('/reset', methods=['POST'])
def reset_dungeon():
    """Reset the current dungeon (uses game_id from init)"""
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify(success=False, message="Dungeon not initialized")
    
    location = app.campaign.get_location("test_dungeon")
    dungeon_type = location["dungeon_type"] if location else "cave"
    success = g.dungeon.reset_dungeon(dungeon_type)
    
    return jsonify(
        success=success,
        message="Dungeon reset" if success else "Reset failed"
    )

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