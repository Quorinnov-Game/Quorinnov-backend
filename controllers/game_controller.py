from flask import Blueprint, request, jsonify
from services.game_service import GameService

# Create a Flask Blueprint to group the game-related endpoints
game_blueprint = Blueprint('game', __name__)

# Instantiate a single GameService to handle game logic
game_service = GameService()

@game_blueprint.route('/init', methods=['POST'])
def init_game():
    """
    Initialize a new Quoridor board.
    Returns the initial board state (JSON).

    Example:
    POST /api/game/init
    Response: {
      "size": 9,
      "players": [...],
      "walls": []
    }
    """
    result = game_service.init_game()
    return jsonify(result)

@game_blueprint.route('/state', methods=['GET'])
def get_state():
    """
    Retrieve the current state of the board:
    - board size
    - player positions
    - remaining walls
    - any placed walls

    Example:
    GET /api/game/state
    Response: {
      "size": 9,
      "players": [...],
      "walls": [...]
    }
    """
    result = game_service.get_current_state()
    return jsonify(result)

@game_blueprint.route('/move', methods=['POST'])
def move_player():
    """
    Move the specified player in a given direction.
    Expects a JSON body with:
        { "player_id": 1, "direction": "up" }
    Valid directions: "up", "down", "left", "right"

    Example:
    POST /api/game/move
    Body: { "player_id": 1, "direction": "up" }
    Response: updated board state
    """
    data = request.json
    player_id = data.get('player_id')
    direction = data.get('direction')
    result = game_service.move_player(player_id, direction)
    return jsonify(result)

@game_blueprint.route('/place_wall', methods=['POST'])
def place_wall():
    """
    Place a wall on the board for the specified player.
    Expects a JSON body with:
        { "player_id": 1, "row": 2, "col": 3, "orientation": "H" }
    orientation can be "H" (horizontal) or "V" (vertical).

    Example:
    POST /api/game/place_wall
    Body: { "player_id": 1, "row": 2, "col": 3, "orientation": "H" }
    Response: updated board state
    """
    data = request.json
    player_id = data.get('player_id')
    row = data.get('row')
    col = data.get('col')
    orientation = data.get('orientation')
    result = game_service.place_wall(player_id, row, col, orientation)
    return jsonify(result)
