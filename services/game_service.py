from sqlalchemy.orm import Session
from models.board import Board          # Board đóng vai trò là Game
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from models.state import State
from .board_logic import GameBoard


class GameService:
    def __init__(self, db: Session):
        self.db = db

    def create_game(self, player1: dict, player2: dict):
        # Tạo state ban đầu rỗng
        state_obj = State(playerA=[], playerB=[])
        self.db.add(state_obj)
        self.db.commit()

        # Tạo board (game)
        board_obj = Board(
            width=9,
            height=9,
            state_id=state_obj.id,
            winner=None
        )
        self.db.add(board_obj)
        self.db.commit()

        # Tạo 2 người chơi
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
        self.db.add_all([player1_obj, player2_obj])
        self.db.commit()

        print(f"[create_game] Created board with ID {board_obj.id}")

    def get_player(self, player_id: int) -> Player:
        return self.db.query(Player).filter(Player.id == player_id).first()

    def move_player(self, player_id: int, direction: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()

        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        if board_logic.is_valid_move(player, direction):
            player.position = board_logic.calculate_new_position(player.position, direction)
            self.db.commit()
            return True
        return False

    def place_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        print(f"[place_wall] Player {player_id} at ({x}, {y}) - {orientation}")

        player = self.get_player(player_id)
        if not player or player.walls_left <= 0:
            print("[place_wall]  Invalid player or no walls left")
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()

        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        new_wall = Wall(x=x, y=y, orientation=orientation, playerId=player_id)

        if not board_logic.add_wall(new_wall):
            print("[place_wall] Wall placement invalid")
            return False

        self.db.add(new_wall)
        player.walls_left -= 1
        self.db.commit()
        print("[place_wall]  Wall placed")
        return True

    def is_valid_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()

        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        test_wall = Wall(x=x, y=y, orientation=orientation, playerId=player_id)
        return board_logic._is_valid_wall(test_wall)

    def check_winner(self) -> str:
        players = self.db.query(Player).all()
        board = self.db.query(Board).first()
        if not board:
            return ""

        walls = self.db.query(Wall).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        for player in players:
            if board_logic.has_path(player):
                if player.direction == Direction.UP and player.position["x"] == 0:
                    return player.name
                elif player.direction == Direction.DOWN and player.position["x"] == board.height - 1:
                    return player.name
        return ""

    def reset_game(self):
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.query(State).delete()
        self.db.commit()

    def log_action_to_state(self, player_id: int, action: dict):
        player = self.get_player(player_id)
        if not player:
            return

        board = self.db.query(Board).first()
        if not board:
            return

        state = self.db.query(State).filter(State.id == board.state_id).first()
        if not state:
            return

        if player_id == 1:
            state.playerA.append(action)
        elif player_id == 2:
            state.playerB.append(action)

        self.db.commit()

    def perform_action(self, player_id: int, action: dict) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()

        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        if action["type"] == "player":
            direction = action["direction"]
            if board_logic.is_valid_move(player, direction):
                new_pos = board_logic.calculate_new_position(player.position, direction)
                player.position = new_pos
                self.log_action_to_state(player_id, {"player": new_pos})
                self.db.commit()
                return True

        elif action["type"] == "wall":
            x, y, orientation = action["x"], action["y"], action["orientation"]

            if player.walls_left <= 0:
                return False

            new_wall = Wall(x=x, y=y, orientation=orientation, playerId=player_id)
            if board_logic.add_wall(new_wall):
                self.db.add(new_wall)
                player.walls_left -= 1
                self.log_action_to_state(player_id, {
                    "wall": {
                        "x": x,
                        "y": y,
                        "orientation": orientation
                    }
                })
                self.db.commit()
                return True

        return False

