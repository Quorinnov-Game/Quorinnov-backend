from sqlalchemy.orm import Session
from models.board import Board
from models.player import Player
from models.wall import Wall
from models.enums import Direction

class GameService:
    def __init__(self, db: Session):
        self.db = db

    def create_game(self, player1: dict, player2: dict, board: dict):
        board_obj = Board(width=board["width"], height=board["height"])
        print(f"[create_game] Board size: {board_obj.width}x{board_obj.height}")
        self.db.add(board_obj)

        player1_obj = Player(
            color=player1["color"],
            position=player1["position"],
            walls_left=player1["walls_left"]
        )
        player2_obj = Player(
            color=player2["color"],
            position=player2["position"],
            walls_left=player2["walls_left"]
        )

        print(f"[create_game] Creating game with players {player1_obj.name} and {player2_obj.name}")
        self.db.add_all([player1_obj, player2_obj])

        self.db.commit()
        print("[create_game] Game created successfully")

    def get_player(self, player_id: int) -> Player:
        return self.db.query(Player).filter(Player.id == player_id).first()

    def move_player(self, player_id: int, direction: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        if board.is_valid_move(player, direction):
            player.position = board.calculate_new_position(player.position, direction)
            self.db.commit()
            return True
        return False

    def place_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        print(f"[place_wall] Request from player {player_id} to place at ({x}, {y}) - {orientation}")

        player = self.get_player(player_id)
        if not player:
            print("[place_wall] Failed: player not found")
            return False
        if player.walls_left <= 0:
            print("[place_wall] Failed: no walls left")
            return False

        board = self.db.query(Board).first()
        if not board:
            print("[place_wall] Failed: no board")
            return False

        players = self.db.query(Player).all()
        new_wall = Wall(x=x, y=y, direction=orientation, playerId=player_id)

        if not board.place_wall(new_wall, players):
            print("[place_wall] Failed: invalid placement")
            return False

        print("[place_wall] Success: wall placed")
        self.db.add(new_wall)
        player.walls_left -= 1
        self.db.commit()
        return True

    def check_winner(self) -> str:
        players = self.db.query(Player).all()
        board = self.db.query(Board).first()
        for player in players:
            if board.check_win_condition(player):
                return player.name
        return ""

    def reset_game(self):
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.commit()
