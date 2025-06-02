import random
from models.player import Player
from models.enums import Direction
from .board_logic import GameBoard

class RandomAI:
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        if not player or not board:
            return None

        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        directions = ["up", "down", "left", "right"]
        valid_moves = []

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                valid_moves.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos  # Ajout de la nouvelle position
                })

        return random.choice(valid_moves) if valid_moves else None


class BasicAI:
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        if not player or not board:
            return None

        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        directions = ["up", "down", "left", "right"]
        best_move = None
        best_distance = float("inf")

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                dist = new_pos["x"] if player.direction == Direction.UP else (board.height - 1 - new_pos["x"])
                
                if dist < best_distance:
                    best_distance = dist
                    best_move = {
                        "type": "player",
                        "direction": d,
                        "position": new_pos
                    }

        return best_move


class AdvancedAI(BasicAI):
    def __init__(self, game_service, player_id):
        super().__init__(game_service, player_id)
        # Pourrait implémenter des stratégies plus avancées ici
        # comme la recherche de chemin ou l'analyse des murs adverses