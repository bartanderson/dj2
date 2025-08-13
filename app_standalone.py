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
app.campaign = TestCampaign()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('standalone_app')

@app.before_request
def init_session_and_dungeon():
    # Initialize session
    if 'session_id' not in session:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        logger.info(f"New session: {session_id}")
    
    # Get or create dungeon for session
    session_id = session['session_id']
    if session_id not in DUNGEON_CACHE:
        dungeon = DungeonSystem()
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        if dungeon.generate(dungeon_type):
            DUNGEON_CACHE[session_id] = dungeon
            logger.info(f"Created dungeon for session {session_id}")
        else:
            logger.error(f"Dungeon init failed for {session_id}")
    
    # Attach to request context
    g.dungeon = DUNGEON_CACHE.get(session_id)

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
        return create_placeholder_image(f"Rendering error: {str(e)}")

@app.route('/move', methods=['POST'])
def move():
    if not hasattr(g, 'dungeon') or not g.dungeon:
        return jsonify({"success": False, "message": "Dungeon not initialized"})
    
    data = request.json
    direction = data.get('direction')
    steps = data.get('steps', 1)
    
    try:
        result = g.dungeon.state.movement.move_party(direction, steps)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": f"Movement error: {str(e)}"})

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
        return jsonify({"success": False, "message": f"AI error: {str(e)}"})

@app.route('/reset', methods=['POST'])
def reset_dungeon():
    session_id = session.get('session_id')
    if not session_id or session_id not in DUNGEON_CACHE:
        return jsonify(success=False, message="Session not initialized")
    
    dungeon = DUNGEON_CACHE[session_id]
    location = app.campaign.get_location("test_dungeon")
    dungeon_type = location["dungeon_type"] if location else "cave"
    success = dungeon.reset_dungeon(dungeon_type)
    
    # Update cache
    DUNGEON_CACHE[session_id] = dungeon
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
    app.run(debug=True, port=5003, use_reloader=False)