from flask import Flask, send_file
from core.game_state import GameState
from routes.api import api_bp

def create_app():
    app = Flask(__name__)
    app.game_state = GameState()  # Single game state instance

    # Configure logging
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        
        file_handler = RotatingFileHandler('dungeon.log', maxBytes=1024*1024, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
            
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    # Add root route directly
    @app.route('/')
    def dungeon_view():
        return send_file('templates\\dungeon.html')  # Serve HTML directly
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5002, debug=True)