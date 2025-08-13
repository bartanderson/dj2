#app_standalone.py
from flask import Flask, send_file, request, jsonify, session
from core.dungeon_standalone import DungeonSystem
from dungeon_neo.test_campaign import TestCampaign
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import uuid
import logging

app = Flask(__name__)
app.secret_key = 'standalone_secret_key'
app.campaign = TestCampaign()
app.dungeon = DungeonSystem()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('standalone_app')

@app.before_request
def init_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        logger.info(f"New session started: {session['session_id']}")
    
    # Initialize dungeon if not already created
    if not hasattr(app, 'dungeon_initialized') or not app.dungeon_initialized:
        location = app.campaign.get_location("test_dungeon")
        dungeon_type = location["dungeon_type"] if location else "cave"
        success = app.dungeon.generate(dungeon_type)
        
        if success:
            app.dungeon_initialized = True
            logger.info("Dungeon initialized successfully")
        else:
            logger.error("Dungeon initialization failed")

@app.route('/')
def index():
    return send_file('templates\\dungeon_standalone.html')

@app.route('/dungeon-image')
def dungeon_image():
    debug = request.args.get('debug', 'false').lower() == 'true'
    try:
        img = app.dungeon.get_image(debug)
        if img is None:
            return create_placeholder_image("Image generation failed")
        return serve_pil_image(img)
    except Exception as e:
        logger.exception("Image generation error")
        return create_placeholder_image(f"Rendering error: {str(e)}")

@app.route('/move', methods=['POST'])
def move():
    data = request.json
    direction = data.get('direction')
    steps = data.get('steps', 1)
    
    if not direction:
        return jsonify({"success": False, "message": "Missing direction"})
    
    try:
        result = app.dungeon.state.movement.move_party(direction, steps)
        return jsonify(result)
    except Exception as e:
        logger.exception("Movement error")
        return jsonify({
            "success": False, 
            "message": f"Movement error: {str(e)}"
        })

@app.route('/ai-command', methods=['POST'])
def ai_command():
    data = request.json
    command = data.get('command', '')
    
    if not command:
        return jsonify({"success": False, "message": "Empty command"})
    
    try:
        result = app.dungeon.process_ai_command(command)
        return jsonify(result)
    except Exception as e:
        logger.exception("AI command error")
        return jsonify({
            "success": False,
            "message": f"AI processing error: {str(e)}"
        })

@app.route('/position')
def get_position():
    if app.dungeon.state and app.dungeon.state.party_position:
        return jsonify({"position": app.dungeon.state.party_position})
    return jsonify({"position": [0, 0]})

@app.route('/reset', methods=['POST'])
def reset_dungeon():
    location = app.campaign.get_location("test_dungeon")
    dungeon_type = location["dungeon_type"] if location else "cave"
    success = app.dungeon.reset_dungeon(dungeon_type)
    return jsonify({
        "success": success,
        "message": "Dungeon reset" if success else "Reset failed"
    })

def serve_pil_image(pil_img):
    img_io = BytesIO()
    pil_img.save(img_io, 'PNG', quality=100)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

def create_placeholder_image(message):
    try:
        img = Image.new('RGB', (800, 600), color='black')
        draw = ImageDraw.Draw(img)
        
        # Use a larger font
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Split message into multiple lines
        lines = []
        line = ""
        for word in message.split():
            test_line = line + word + " "
            if draw.textlength(test_line, font=font) > 750:
                lines.append(line)
                line = word + " "
            else:
                line = test_line
        lines.append(line)
        
        # Draw text
        y = 250
        for line in lines:
            draw.text((50, y), line, fill='white', font=font)
            y += 30
        
        return serve_pil_image(img)
    except Exception as e:
        return f"Placeholder image error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5003, use_reloader=False)