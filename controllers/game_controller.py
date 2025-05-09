from flask import Blueprint, request, jsonify
from database import SessionLocal
from services.game_service import GameService

router = Blueprint('game_controller', __name__)

@router.route("/move", methods=["POST"])
def move():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    success = service.move_player(data["player_id"], data["direction"])
    db.close()
    return jsonify({"success": success})

@router.route("/place_wall", methods=["POST"])
def place_wall():
    db = SessionLocal()
    data = request.json
    service = GameService(db)
    success = service.place_wall(data["player_id"], data["x"], data["y"], data["direction"])
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
    service.create_game(data["player1"], data["player2"], data["board"])
    db.close()
    return jsonify({"game_created": True})