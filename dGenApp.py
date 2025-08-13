from flask import Flask, render_template, jsonify, request, send_file
from io import BytesIO
from dGen import DungeonGenerator
import time

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('dGen.html')

@app.route('/generate', methods=['POST'])
def generate_dungeon():
    params = request.json
    generator = DungeonGenerator(params)
    dungeon = generator.create_dungeon()
    
    # Generate PNG image
    #png_data = generator.generate_png() no clue why this one would be called here
    
    return jsonify({
        'rooms': generator.n_rooms,
        'opts': generator.opts,
        'stats': generator.get_stats(),
        'door_list': generator.doorList
    })

@app.route('/dungeon.png')
def dungeon_png():
    params = {
        'seed': int(request.args.get('seed', time.time() * 1000)),
        'n_rows': int(request.args.get('rows', 39)),
        'n_cols': int(request.args.get('cols', 39)),
        'cell_size': int(request.args.get('cellSize', 18)),
        'room_min': int(request.args.get('roomMin', 3)),
        'room_max': int(request.args.get('roomMax', 9)),
        'room_layout': request.args.get('roomLayout', 'Scattered'),
        'corridor_layout': request.args.get('corridorLayout', 'Bent'),
        'remove_deadends': int(request.args.get('deadEndRemoval', 50)),
        'dungeon_layout': request.args.get('dungeonLayout', 'None'),
        'add_stairs': int(request.args.get('stairs', 2))
    }
    
    generator = DungeonGenerator(params)
    generator.create_dungeon()
    png_data = generator.generate_png()
    
    return send_file(
        BytesIO(png_data),
        mimetype='image/png',
        as_attachment=False
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)