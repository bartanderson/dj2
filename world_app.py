from flask import Flask, jsonify, render_template, send_from_directory
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
controller = WorldController(world_data, ai_system, seed=42)

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
    success = controller.travel_system.start_journey(destination_id)
    return jsonify({"success": success})

@app.route('/api/travel-progress', methods=['GET'])
def travel_progress():
    progress = controller.travel_system.progress_journey()
    return jsonify(progress)

@app.route('/api/resolve-encounter', methods=['POST'])
def resolve_encounter():
    data = request.get_json()
    choice = data.get('choice')
    result = controller.travel_system.resolve_encounter(choice)
    return jsonify({"result": result})


@app.route('/api/dm-response', methods=['POST'])
def dm_response():
    data = request.get_json()
    player_id = session.get('user_id', 'guest')
    message = data['message']
    
    # Process through narrative system
    result = controller.narrative_system.process_player_action(player_id, message)
    
    return jsonify(result)

@app.route('/api/world-state')
def world_state():
    return jsonify({
        "worldMap": controller.get_map_data(),
        "currentLocation": controller.get_current_location_data()
    })

@app.route('/api/locations')
def all_locations():
    return jsonify({
        "locations": [loc.to_dict() for loc in controller.world_map.locations.values()]
    })

@app.route('/api/travel/<location_id>', methods=['POST'])
def travel_to(location_id):
    success = controller.travel_to_location(location_id)
    return jsonify({
        "success": success,
        "location": controller.get_current_location_data()
    })

@app.route('/api/location/<location_id>/rumors')
def get_location_rumors(location_id):
    rumors = controller.get_rumors(location_id)
    return jsonify({"rumors": rumors})

@app.route('/api/enter-dungeon', methods=['POST'])
def enter_dungeon():
    success = controller.enter_dungeon()
    return jsonify({"success": success})

@app.route('/api/create-character', methods=['POST'])
def create_character():
    data = request.get_json()
    user_id = session.get('user_id', 'default_user')
    
    # Generate character details
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
        "abilities": generate_abilities(data['race'], data['class'])
    }
    
    # Generate avatar
    avatar_prompt = f"Fantasy portrait: {data['race']} {data['class']} {data['background']}"
    character["avatar_url"] = t2i.generate_image(avatar_prompt)
    
    # Save character
    if user_id not in character_database:
        character_database[user_id] = []
    character_database[user_id].append(character)
    
    # Add to party if not full
    party = session.get('party', [])
    if len(party) < 4:
        party.append(character['id'])
        session['party'] = party

    controller.add_character(character)
    
    return jsonify({"success": True, "character": character})

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


if __name__ == '__main__':
    app.run(debug=True)