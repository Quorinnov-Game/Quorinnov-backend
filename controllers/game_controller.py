from flask import Blueprint, request, jsonify
from database import SessionLocal
from services.game_service import GameService

router = Blueprint('game_controller', __name__)

@router.route("/move", methods=["POST"])
def move():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    success = service.move_player(data["player_id"], data["x"], data["y"])
    db.close()
    return jsonify({"success": success})

@router.route("/place_wall", methods=["POST"])
def place_wall():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    success = service.place_wall(data["player_id"], data["x"], data["y"], data["orientation"],data["is_valid"])
    db.close()
    return jsonify({"success": success})

@router.route("/check_winner", methods=["GET"])
def check_winner():
    db = SessionLocal()
    service = GameService(db)
    winner = service.check_winner()
    db.close()
    return jsonify({"winner": winner})

@router.route("/reset", methods=["POST"])
def reset():
    db = SessionLocal()
    service = GameService(db)
    service.reset_game()
    db.close()
    return jsonify({"reset": True})

@router.route("/create_game", methods=["POST"])
def create_game():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    board = service.create_game(data["player1"], data["player2"])
    db.close()
    return jsonify({
        "game_created": True,
        "board_id": board.id,
        "state_id": board.state_id
    })

@router.route("/is_valid_wall", methods=["POST"])
def is_valid_wall():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    valid = service.is_valid_wall(data["player_id"], data["x"], data["y"], data["orientation"])
    db.close()
    return jsonify({"is_valid": valid})

@router.route("/action", methods=["POST"])
def perform_action():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    success = service.perform_action(data["player_id"], data["action"])
    db.close()
    return jsonify({"success": success})

@router.route("/turns/<int:turn_number>", methods=["GET"])
def get_turns(turn_number):
    db = SessionLocal()
    service = GameService(db)
    result = service.get_turns(turn_number)
    db.close()

    if result is None:
        return jsonify({"error": "Turn number exceeds existing turns"}), 400
    return jsonify({
        "success": True if result else False,
        "history": result
    }), 200


@router.route("/ia_play", methods=["POST", "OPTIONS"])
def ia_play():
    db = SessionLocal()
    try:
        # Gestion des requêtes OPTIONS pour CORS
        if request.method == "OPTIONS":
            return jsonify({"success": True}), 200
            
        data = request.get_json()
        print(f"IA play request data: {data}")
        
        if not data or "game_id" not in data or "difficulty" not in data:
            return jsonify({"error": "Missing parameters"}), 400
            
        service = GameService(db)
        result = service.ia_play(data["game_id"], data["difficulty"])
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"Error in ia_play: {str(e)}")
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()