from flask import Flask, jsonify, render_template, send_from_directory, session, current_app
import random
import uuid
import json
from world.world_controller import WorldController
from world.world_map import WorldMap
from world.ai_integration import DungeonAI

app = Flask(__name__)

# Load world data
with open('dark_fantasy_world.json', 'r') as f:
    world_data = json.load(f)

# Initialize AI system
ai_system = DungeonAI(dungeon_state=None, ollama_host="http://localhost:11434")

# Initialize world controller
world_controller = WorldController(world_data, ai_system, seed=42)

# Temporary storage (replace with database in production)
character_database = {}

# Serve static images
@app.route('/static/world_images/<path:filename>')
def serve_world_images(filename):
    return send_from_directory('static/world_images', filename)

@app.route('/api/retry-failed-images', methods=['POST'])
def retry_failed_images():
    try:
        from t2i import TextToImage
        import json
        
        # Load failure data
        with open('failed_generations.json', 'r') as f:
            failures = json.load(f)
        
        # Initialize generator
        model_path = Path.home() / ".sdkit" / "models" / "stable-diffusion" / "realisticVisionV60B1_v51VAE.safetensors"
        t2i = TextToImage(model_path)
        image_dir = Path("static/world_images")
        
        # Retry failed generations
        successes, new_failures = t2i.generate_batch(
            generation_requests=failures,
            output_dir=image_dir
        )
        
        # Update world data with new images
        updated_locations = []
        for req_id in successes:
            loc_id = req_id.replace("loc-", "")
            # In a real app, update your database here
            updated_locations.append(loc_id)
        
        return jsonify({
            "success": True,
            "updated_locations": updated_locations,
            "succeeded": len(successes),
            "failed": len(new_failures)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/', endpoint='index')
def index():
    return render_template('world.html')

@app.route('/api/start-journey', methods=['POST'])
def start_journey():
    data = request.get_json()
    destination_id = data.get('destination_id')
    success = world_controller.travel_system.start_journey(destination_id)
    return jsonify({"success": success})

@app.route('/api/travel-progress', methods=['GET'])
def travel_progress():
    progress = world_controller.travel_system.progress_journey()
    return jsonify(progress)

@app.route('/api/resolve-encounter', methods=['POST'])
def resolve_encounter():
    data = request.get_json()
    choice = data.get('choice')
    result = world_controller.travel_system.resolve_encounter(choice)
    return jsonify({"result": result})


@app.route('/api/dm-response', methods=['POST'])
def dm_response():
    print("got here dm-response")
    data = request.get_json()
    player_id = session.get('user_id', 'guest')
    message = data['message']
    print(f"data {data} player_id {player_id} message {message}")
    
    # Process through narrative system
    result = world_controller.narrative_system.process_player_action(player_id, message)
    
    return jsonify(result)

@app.route('/api/world-state')
def world_state():
    try:
        return jsonify({
            "worldMap": world_controller.get_map_data(),
            "currentLocation": world_controller.get_current_location_data(),
            "parties": world_controller.get_active_parties(),
            "characters": world_controller.characters
            })
    except Exception as e:
        print(f"Error in world_state: {str(e)}")
        return jsonify({
            "worldMap": {"error": "Map data unavailable"},
            "currentLocation": None,
            "party": []
        })

@app.route('/api/locations')
def all_locations():
    try:
        return jsonify({
            "locations": [
                loc.to_dict() 
                for loc in world_controller.world_map.locations.values()
            ]
        })
    except Exception as e:
        print(f"Error in all_locations: {str(e)}")
        return jsonify({"locations": []})

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

@app.route('/api/create-character', methods=['POST'])
def create_character():
    data = request.get_json()
    user_id = session.get('user_id', 'default_user')
    
    # Generate character details (your existing code)
    character = {
        "id": str(uuid.uuid4()),
        "owner": user_id,
        "name": generate_character_name(data['race'], data['class']),
        "race": data["race"],
        "class": data["class"],
        "background": data["background"],
        "personality": data.get("personality", ""),
        "ideals": data.get("ideals", ""),
        "bonds": data.get("bonds", ""),
        "flaws": data.get("flaws", ""),
        "level": 1,
        "hit_points": calculate_starting_hp(data['class']),
        "max_hp": calculate_starting_hp(data['class']),
        "abilities": generate_abilities(data['race'], data['class']),
        "avatar_url": "/static/images/default_avatar.png"  # Placeholder
    }
    
    # Generate avatar (your existing code)
    avatar_prompt = f"Fantasy portrait: {data['race']} {data['class']} {data['background']}"
    character["avatar_url"] = t2i.generate_image(avatar_prompt)
    
    # Save character to user database (your existing code)
    if user_id not in character_database:
        character_database[user_id] = []
    character_database[user_id].append(character)
    
    # Add to session party (your existing code)
    party = session.get('party', [])
    if len(party) < 4:  # Maintain your party size limit
        party.append(character['id'])
        session['party'] = party
    
    # Add to world_controller
    world_controller.add_character(character)  # Add to characters dictionary
    world_controller.add_to_party(character['id'])  # Add to party list
    
    return jsonify({
        "success": True, 
        "character": character,
        "party_size": len(party)  # Return current party size
    })

@app.route('/api/create-party', methods=['POST'])
def create_party():
    data = request.json
    party_id = controller.create_party(
        name=data.get('name', 'New Party'),
        initial_members=data.get('members', [])
    )
    return jsonify({"success": True, "party_id": party_id})

# Move character between parties
@app.route('/api/move-character', methods=['POST'])
def move_character():
    data = request.json
    success = controller.add_to_party(
        char_id=data['char_id'],
        party_id=data['party_id']
    )
    return jsonify({"success": success})

# Get all parties
@app.route('/api/parties')
def get_parties():
    return jsonify({
        "parties": controller.get_active_parties(),
        "default_party": controller.default_party_id
    })

# Disband a party
@app.route('/api/disband-party/<party_id>', methods=['POST'])
def disband_party(party_id):
    success = controller.disband_party(party_id)
    return jsonify({"success": success})


def generate_character_name(race, cls):
    name_parts = {
        "human": ["James", "Sarah", "Robert", "Emily"],
        "elf": ["Aerindel", "Lyra", "Thalorin", "Faelar"],
        "dwarf": ["Thorin", "Borin", "Dvalin", "Hilda"],
        "wizard": ["the Wise", "the Learned", "the Arcane"],
        "fighter": ["the Bold", "the Strong", "the Brave"]
    }
    first = random.choice(name_parts.get(race, ["Unknown"]))
    last = random.choice(name_parts.get(cls, ["Adventurer"]))
    return f"{first} {last}"

def calculate_starting_hp(cls):
    base_hp = {
        "fighter": 10, "paladin": 10, "ranger": 10,
        "wizard": 6, "sorcerer": 6, "bard": 8,
        "cleric": 8, "druid": 8, "rogue": 8
    }
    return base_hp.get(cls, 8) + random.randint(1, 4)

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
    result = controller.narrative_system.guide_character_creation(
        player_id, 
        message, 
        creation_state
    )
    
    # Update session state
    session['creation_state'] = result['new_state']
    
    return jsonify(result)

def generate_abilities(race, cls):
    abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
    scores = {ab: random.randint(8, 15) for ab in abilities}
    
    # Racial bonuses
    if race == "elf":
        scores["dexterity"] += 2
    elif race == "dwarf":
        scores["constitution"] += 2
    
    # Class bonuses
    if cls == "wizard":
        scores["intelligence"] += 1
    elif cls == "fighter":
        scores["strength"] += 1
    
    return scores

@app.route('/api/get-party')
def get_party():
    # Replace with proper method that exists
    return jsonify({
        "active_parties": world_controller.get_active_parties(),
        "characters": world_controller.characters
    })

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")