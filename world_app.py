from flask import Flask, jsonify, render_template, send_from_directory
from world.world_controller import WorldController
from world.world_map import WorldMap
import json

app = Flask(__name__)

# Load world data
with open('dark_fantasy_world.json', 'r') as f:
    world_data = json.load(f)

# Initialize world controller
controller = WorldController(world_data, seed=42)

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

@app.route('/api/world-state')
def world_state():
    return jsonify({
        "worldMap": controller.get_map_data(),
        "currentLocation": controller.get_current_location_data()
    })

@app.route('/api/travel/<location_id>', methods=['POST'])
def travel_to(location_id):
    success = controller.travel_to_location(location_id)
    return jsonify({
        "success": success,
        "location": controller.get_current_location_data()
    })

@app.route('/api/locations')
def all_locations():
    return jsonify({
        "locations": [loc.to_dict() for loc in controller.world_map.locations.values()]
    })

@app.route('/api/enter-dungeon', methods=['POST'])
def enter_dungeon():
    success = controller.enter_dungeon()
    return jsonify({"success": success})

if __name__ == '__main__':
    app.run(debug=True)