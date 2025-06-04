from copy import deepcopy
import random
from collections import deque
import math

from models.player import Player
from models.wall import Wall 
from models.enums import Direction
from .board_logic import GameBoard

MAX_DEPTH = 2

class BasePathMixin:
    """Base mixin contient des methodes communes"""
    
    def is_path_blocked(self, x1, y1, x2, y2, walls):
        """Vérifie si le chemin entre deux points est bloqué par un mur"""
        if y1 == y2:  # Horizontal movement
            wall_x = min(x1, x2)
            return any(wall.orientation == "horizontal" and
                      wall.x == wall_x and
                      (wall.y == y1 or wall.y == y1 - 1)
                      for wall in walls)
        elif x1 == x2:  # Vertical movement
            wall_y = min(y1, y2)
            return any(wall.orientation == "vertical" and
                      wall.y == wall_y and
                      (wall.x == x1 or wall.x == x1 - 1)
                      for wall in walls)
        return False

class WallValidationMixin(BasePathMixin):
    """Mixin class pour la validation des murs"""
    
    def is_valid_wall(self, wall, existing_walls, board):
        x = wall.get("x") if isinstance(wall, dict) else wall.x
        y = wall.get("y") if isinstance(wall, dict) else wall.y
        orientation = wall.get("orientation") if isinstance(wall, dict) else wall.orientation

        # Vérification des coordonnées
        if orientation == "horizontal":
            if x < 0 or x >= board.width - 1 or y < 0 or y >= board.height:
                print(f"Wall out of bounds: ({x}, {y}) - {orientation}")
                return False
        else:  # vertical
            if x < 0 or x >= board.width or y < 0 or y >= board.height - 1:
                print(f"Wall out of bounds: ({x}, {y}) - {orientation}")
                return False

        # Vérification intersection
        if self._is_wall_crossing(wall, existing_walls):
            print(f"Wall crossing detected at ({x}, {y})")
            return False

        # Vérification de chevauchement
        if self._is_overlapping_wall(wall, existing_walls):
            print(f"Wall overlap detected at ({x}, {y})")
            return False

        # Vérification le chemin vers l'objectif
        if not self._has_path_to_goal(wall, existing_walls, board):
            print(f"Wall blocks path to goal at ({x}, {y})")
            return False

        return True
    
    def _is_wall_crossing(self, wall, existing_walls):
        """Vérifiez si les murs se croisent"""
        x = wall.get("x") if isinstance(wall, dict) else wall.x
        y = wall.get("y") if isinstance(wall, dict) else wall.y
        orientation = wall.get("orientation") if isinstance(wall, dict) else wall.orientation

        for existing in existing_walls:
            if (existing.orientation != orientation and
                existing.x == x and existing.y == y):
                return True
        return False
    
    def _is_overlapping_wall(self, wall, existing_walls):
        """Vérifiez si le mur se chevauche"""
        x = wall.get("x") if isinstance(wall, dict) else wall.x
        y = wall.get("y") if isinstance(wall, dict) else wall.y
        orientation = wall.get("orientation") if isinstance(wall, dict) else wall.orientation

        for existing in existing_walls:
            if existing.orientation == orientation:
                if orientation == "horizontal":
                    if (existing.x == x and 
                        abs(existing.y - y) <= 1):
                        return True
                else:  # vertical
                    if (existing.y == y and 
                        abs(existing.x - x) <= 1):
                        return True
        return False
    
    def _has_path_to_goal(self, new_wall, existing_walls, board):
        """Vérifiez qu'il y a de la place pour les deux joueurs après avoir placé le mur"""
        # Créer un presse-papiers avec un nouveau mur
        temp_walls = existing_walls + [Wall(
            x=new_wall.get("x") if isinstance(new_wall, dict) else new_wall.x,
            y=new_wall.get("y") if isinstance(new_wall, dict) else new_wall.y,
            orientation=new_wall.get("orientation") if isinstance(new_wall, dict) else new_wall.orientation
        )]

        def bfs_to_goal(start_pos, target_row):
            visited = set()
            queue = deque([(start_pos["x"], start_pos["y"])])

            while queue:
                x, y = queue.popleft()
                if x == target_row:
                    return True

                pos_key = f"{x},{y}"
                if pos_key in visited:
                    continue
                visited.add(pos_key)

                # Kiểm tra 4 hướng
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nx, ny = x + dx, y + dy
                    if (0 <= nx < board.width and 
                        0 <= ny < board.height and
                        not self.is_path_blocked(x, y, nx, ny, temp_walls)):
                        queue.append((nx, ny))

            return False

        players = self.game_service.db.query(Player).all()
        # Vérifiez le chemin pour les deux joueurs
        for player in players:
            target_row = 0 if player.direction == Direction.UP else board.height - 1
            if not bfs_to_goal(player.position, target_row):
                print(f"No path found for player {player.id}")
                return False

        return True

class PathfindingMixin(BasePathMixin):
    """Mixin class pour pathfinding"""
    
    def calculate_shortest_path(self, player, board, walls):
        start = (player.position["x"], player.position["y"])
        target_row = 0 if player.direction == Direction.UP else board.height - 1
        
        visited = set()
        queue = deque([(start[0], start[1], [])])

        while queue:
            x, y, path = queue.popleft()
            if (x, y) in visited:
                continue
            
            visited.add((x, y))
            if x == target_row:
                return path

            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < board.width and 0 <= ny < board.height and
                    not self.is_path_blocked(x, y, nx, ny, walls)):
                    queue.append((nx, ny, path + [(nx, ny)]))
        return None

class AdvancedAI(WallValidationMixin, PathfindingMixin):
    """AI sử dụng minimax với alpha-beta pruning"""
    
    def __init__(self, game_service, player_id):
        self.game = game_service
        self.player_id = player_id 
        self.opponent_id = 1 if player_id == 2 else 2

    def choose_move(self):
        board, state, walls = self.game.get_board_and_state()
        players = {
            p.id: p for p in self.game.db.query(type(self.game.get_player(self.player_id))).all()
        }

        _, best_move = self.minimax(players, walls, depth=MAX_DEPTH, maximizing=True, alpha=-math.inf, beta=math.inf)
        return best_move

    def minimax(self, players, walls, depth, maximizing, alpha, beta):
        winner = self._check_terminal(players)
        if depth == 0 or winner:
            return self.evaluate(players, walls), None

        valid_moves = self.get_valid_moves(players, walls, self.player_id if maximizing else self.opponent_id)
        best_move = None
        
        if maximizing:
            max_eval = -math.inf
            for move in valid_moves:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                self.apply_move(new_players, new_walls, self.player_id, move)

                eval_score, _ = self.minimax(new_players, new_walls, depth - 1, False, alpha, beta)
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break
            return max_eval, best_move
        else:
            min_eval = math.inf 
            for move in valid_moves:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                self.apply_move(new_players, new_walls, self.opponent_id, move)

                eval_score, _ = self.minimax(new_players, new_walls, depth - 1, True, alpha, beta)
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def evaluate(self, players, walls):
        player = players[self.player_id]
        opponent = players[self.opponent_id]

        player_dist = self.calculate_shortest_path(player, self.game.board, walls)
        opponent_dist = self.calculate_shortest_path(opponent, self.game.board, walls)

        player_score = len(player_dist) if player_dist else 100
        opponent_score = len(opponent_dist) if opponent_dist else 100

        wall_bonus = players[self.player_id].walls_left * 0.5
        wall_penalty = players[self.opponent_id].walls_left * 0.3

        return (opponent_score - player_score) + wall_bonus - wall_penalty

    def get_valid_moves(self, players, walls, player_id):
        board_logic = GameBoard(size=9)
        board_logic.set_players(players)
        board_logic.walls = walls
        player = players[player_id]

        move_list = []
        # Valid movements
        directions = ["up", "down", "left", "right"]
        for direction in directions:
            if board_logic.is_valid_move(player, direction):
                new_pos = board_logic.calculate_new_position(player.position, direction)
                move_list.append({
                    "type": "player",
                    "position": new_pos
                })

        # Valid walls
        if players[player_id].walls_left > 0:
            for x in range(8):
                for y in range(8):
                    for orientation in ["H", "V"]:
                        wall = Wall(x=x, y=y, orientation=orientation, player_id=player_id)
                        if board_logic._is_valid_wall(wall):
                            move_list.append({
                                "type": "wall",
                                "x": x,
                                "y": y,
                                "orientation": orientation
                            })

        return move_list

    def apply_move(self, players, walls, player_id, move):
        if move["type"] == "player":
            players[player_id].position = move["position"]
        else:  # wall move
            wall = Wall(
                x=move["x"],
                y=move["y"],
                orientation=move["orientation"],
                player_id=player_id,
                is_valid=True
            )
            walls.append(wall)
            players[player_id].walls_left -= 1

    def _check_terminal(self, players):
        for pid, player in players.items():
            if player.direction == Direction.UP and player.position["x"] == 0:
                return True
            if player.direction == Direction.DOWN and player.position["x"] == 8:
                return True
        return False

class RandomAI(WallValidationMixin, PathfindingMixin):
    """AI with random strategy"""
    
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        print(f"Player {player.id} choosing move...")
        print(f"Current position: {player.position}, Walls left: {player.walls_left}")
        if not player or not board:
            return None

        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        # 30% chance to place wall
        if player.walls_left > 0 and random.random() < 0.3:
            max_attempts = 5
            for _ in range(max_attempts):
                possible_walls = self._generate_possible_walls(board, walls)
                if possible_walls:
                    wall = random.choice(possible_walls)
                    # Double check wall validity
                    temp_wall = Wall(
                        x=wall["x"],
                        y=wall["y"],
                        orientation=wall["orientation"],
                        player_id=player.id
                    )
                    if self.is_valid_wall(temp_wall, walls, board):
                        print(f"Found valid wall at ({wall['x']}, {wall['y']}) - {wall['orientation']}")
                        return wall
                    print(f"Wall validation failed, trying again...")
            print("All wall placement attempts failed, switching to movement")

        # Random movement
        directions = ["up", "down", "left", "right"]
        valid_moves = []

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                print(f"Valid move: {d} to {new_pos}")
                valid_moves.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        return random.choice(valid_moves) if valid_moves else None

    def _generate_possible_walls(self, board, existing_walls):
        possible_walls = []
        
        # Horizontal walls
        for x in range(board.width - 1):
            for y in range(board.height - 1):
                wall = {
                    "x": x,
                    "y": y,
                    "orientation": "horizontal",
                    "type": "wall"
                }
                if self.is_valid_wall(wall, existing_walls, board):
                    possible_walls.append(wall)
        
        # Vertical walls 
        for x in range(board.width - 1):
            for y in range(board.height - 1):
                wall = {
                    "x": x,
                    "y": y,
                    "orientation": "vertical",
                    "type": "wall"
                }
                if self.is_valid_wall(wall, existing_walls, board):
                    possible_walls.append(wall)
        
        return possible_walls

class BasicAI(WallValidationMixin, PathfindingMixin):
    """AI với chiến lược cơ bản"""
    
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self.board = None
        self.players = None  
        self.walls = None
        self.board_logic = None

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        if not player or not board:
            return None

        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        # 20% chance to place strategic wall
        if player.walls_left > 0 and random.random() < 0.2:
            strategic_wall = self._find_strategic_wall(board, walls, players, player)
            if strategic_wall:
                return strategic_wall

        # Best forward movement
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

    def _find_strategic_wall(self, board, existing_walls, players, current_player):
        opponent = next(p for p in players if p.id != current_player.id)
        
        if opponent.direction == Direction.UP:
            target_y = opponent.position["y"]
            for x in range(board.width - 1):
                wall = {
                    "type": "wall",
                    "x": x,
                    "y": target_y,
                    "orientation": "horizontal" 
                }
                if self.is_valid_wall(wall, existing_walls, board):
                    return wall
        else:
            target_x = opponent.position["x"]
            for y in range(board.height - 1):
                wall = {
                    "type": "wall",
                    "x": target_x,
                    "y": y,
                    "orientation": "vertical"
                }
                if self.is_valid_wall(wall, existing_walls, board):
                    return wall
        return None