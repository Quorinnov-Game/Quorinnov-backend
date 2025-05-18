from sqlalchemy.orm import Session
from models.board import Board          # Board đóng vai trò là Game
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from models.state import State
from .board_logic import GameBoard


from sqlalchemy.orm import Session
from models.board import Board
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from models.state import State
from .board_logic import GameBoard


class GameService:
    def __init__(self, db: Session):
        self.db = db

    def create_game(self, player1: dict, player2: dict):
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.commit()

        # Create empty state
        state_obj = State(playerA=[], playerB=[])
        self.db.add(state_obj)
        self.db.commit()

        # Create new game (board)
        board_obj = Board(state_id=state_obj.id, width=9, height=9)
        self.db.add(board_obj)
        self.db.commit()

        # Create players with fixed ID
        player1_obj = Player(
            id=1,
            board_id=board_obj.id,
            color=player1["color"],
            position=player1["position"],
            direction="up",
            walls_left=player1["walls_left"]
        )
        player2_obj = Player(
            id=2,
            board_id=board_obj.id,
            color=player2["color"],
            position=player2["position"],
            direction="down",
            walls_left=player2["walls_left"]
        )
        self.db.add_all([player1_obj, player2_obj])
        self.db.commit()

    def get_player(self, player_id: int) -> Player:
        return self.db.query(Player).filter(Player.id == player_id).first()

    def get_board_and_state(self):
        board = self.db.query(Board).first()
        if not board:
            return None, None, None
        state = self.db.query(State).filter(State.id == board.state_id).first()
        walls = self.db.query(Wall).all()
        return board, state, walls

    def move_player(self, player_id: int, direction: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board, state, walls = self.get_board_and_state()
        if not board or not state:
            return False

        players = self.db.query(Player).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        if not board_logic.is_valid_move(player, direction):
            return False

        # Update player position
        player.position = board_logic.calculate_new_position(player.position, direction)

        # Log the move to state
        self.log_action_to_state(state, player_id, {"type": "player", "direction": direction})
        self.db.commit()
        return True

    def place_wall(self, player_id: int, x: int, y: int, orientation: str, is_valid: bool) -> bool:
        print(f"[place_wall] Request from player {player_id} to place at ({x}, {y}) - {orientation}, confirmed: {is_valid}")

        player = self.get_player(player_id)
        if not player:
            print("[place_wall] Failed: player not found")
            return False
        if player.walls_left <= 0:
            print("[place_wall] Failed: no walls left")
            return False

        board_data = self.db.query(Board).first()
        if not board_data:
            print("[place_wall] Failed: no board")
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()
        state = self.db.query(State).filter(State.id == board_data.state_id).first()

        board_logic = GameBoard(size=board_data.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        new_wall = Wall(x=x, y=y, orientation=orientation, playerId=player_id, is_valid=is_valid)

        if not board_logic._is_valid_wall(new_wall):
            print("[place_wall] Failed: wall not valid by logic")
            return False

        if is_valid:
            print("[place_wall] Confirmed wall placed")
            self.db.add(new_wall)
            player.walls_left -= 1

            self.log_action_to_state(state, player_id, {
                "type": "wall",
                "x": x,
                "y": y,
                "orientation": orientation
            })

            self.db.commit()
        else:
            print("[place_wall] Wall not confirmed, skipping DB write and log")

        return True

    def is_valid_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board, _, walls = self.get_board_and_state()
        if not board:
            return False

        players = self.db.query(Player).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        test_wall = Wall(x=x, y=y, orientation=orientation, playerId=player_id)
        return board_logic._is_valid_wall(test_wall)

    def log_action_to_state(self, state: State, player_id: int, action: dict):
        if player_id == 1:
            state.playerA.append(action)
        elif player_id == 2:
            state.playerB.append(action)

    def reset_game(self):
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.commit()


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

