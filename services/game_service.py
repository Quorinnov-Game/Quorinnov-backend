from sqlalchemy.orm import Session
from models.board import Board
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from services.utils import is_valid_move, is_valid_wall_placement, check_win_condition

class GameService:
    def __init__(self, db: Session):
        self.db = db

    def create_game(self, player1: Player, player2: Player, board: Board):
        board = Board(width=board["width"], height=board["height"])
        print(f"[create_game] Board size: {board.width}x{board.height}")
        self.db.add(board)

        player1 = Player(
            color=player1["color"],
            position=player1["position"],
            walls_left=player1["walls_left"]
        )
        player2 = Player(
            color=player2["color"],
            position=player2["position"],
            walls_left=player2["walls_left"]
        )

        print(f"[create_game] Creating game with players {player1.name} and {player2.name}")
        self.db.add_all([player1, player2])

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

        if is_valid_move(player, direction, board):
            player.position = self.calculate_new_position(player.position, direction)
            self.db.commit()
            return True
        return False

    def calculate_new_position(self, position: str, direction: str) -> str:
        col = ord(position[0]) - ord('a')
        row = int(position[1]) - 1

        if direction == Direction.UP:
            row -= 1
        elif direction == Direction.DOWN:
            row += 1
        elif direction == Direction.LEFT:
            col -= 1
        elif direction == Direction.RIGHT:
            col += 1

        new_col = chr(col + ord('a'))
        new_row = str(row + 1)
        return new_col + new_row

    def place_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        player = self.get_player(player_id)
        if not player or player.walls_left <= 0:
            return False

        new_wall = Wall(x=x, y=y, direction=orientation)
        board = self.db.query(Board).first()

        if is_valid_wall_placement(new_wall, board):
            self.db.add(new_wall)
            player.walls_left -= 1
            self.db.commit()
            return True
        return False

    def check_winner(self) -> str:
        players = self.db.query(Player).all()
        for player in players:
            if check_win_condition(player):
                return player.name
        return ""

    def reset_game(self):
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.commit()
