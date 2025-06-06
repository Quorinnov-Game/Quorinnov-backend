from copy import deepcopy
import random
from collections import deque
import math

from models.player import Player
from models.wall import Wall 
from models.enums import Direction
from .board_logic import GameBoard

MAX_DEPTH = 6

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

            # Explore les 4 directions
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < board.width and 0 <= ny < board.height and
                    not self.is_path_blocked(x, y, nx, ny, walls)):
                    queue.append((nx, ny, path + [(nx, ny)]))
        return None

class AdvancedAIJaicompris(WallValidationMixin, PathfindingMixin):
    """AI utilisant minimax avec alpha-beta pruning"""
    
    def __init__(self, game_service, player_id):
        self.game = game_service
        self.player_id = player_id 
        self.opponent_id = 1 if player_id == 2 else 2

    def choose_move(self):
        """Choisit le meilleur mouvement selon l'algorithme Minimax"""
        board, state, walls = self.game.get_board_and_state()
        players = {
            p.id: p for p in self.game.db.query(type(self.game.get_player(self.player_id))).all()
        }

        _, best_move = self.minimax(players, walls, depth=MAX_DEPTH, maximizing=True, alpha=-math.inf, beta=math.inf)
        return best_move

    def minimax(self, players, walls, depth, maximizing, alpha, beta):
        game_board = GameBoard(9)
        winner = self._check_terminal(players)
        if depth == 0 or winner:
            return self.evaluate(players, walls, game_board), None

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
                if eval_score < min_eval: #comparer avec le précedent +l infini
                    min_eval = eval_score
                    best_move = move
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break
            return min_eval, best_move

    def evaluate(self, players, walls, game_board):
        #on récupere les deux joueurs
        player = players[self.player_id]
        opponent = players[self.opponent_id]

        player_dist = self.calculate_shortest_path(player, game_board, walls)
        opponent_dist = self.calculate_shortest_path(opponent, game_board, walls)

        # Si le joueur n'a pas de chemin, il est bloqué
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
    #Si le joueur a des murs à poser (walls_left > 0),
    #Tente jusqu’à 5 fois de choisir un mur valide aléatoire parmi tous les murs possibles
    #Pour chaque tentative, elle vérifie que la pose est valide (via is_valid_wall),
    #Si un mur valide est trouvé, elle le retourne comme action.
    #sinon elle rends un mouvement aléatoire valide parmi les deplacement valide

    
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
    #Avec 20% de chance (si le joueur a encore des murs), elle essaie de poser un mur stratégique en appelant _find_strategic_wall.
    #Si elle trouve un mur valide stratégique, elle le retourne et joue ce coup.
    #Sinon, elle cherche à avancer vers l’avant (vers la ligne d’arrivée) en évaluant les déplacements possible
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





from collections import deque
from copy import deepcopy

class BasicAIFaux(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score = float("-inf")
        best_action = None

        actions = self._generate_all_actions(player, board, walls)

        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=6,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _generate_all_actions(self, player, board, walls):
        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        directions = ["up", "down", "left", "right"]

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        if player.walls_left > 0:
            wall_actions = self._generate_possible_walls(board, walls)
            actions += wall_actions

        return actions

    def _generate_possible_walls(self, board, existing_walls):
        """Génère uniquement les murs valides via GameBoard.place_wall"""
        possible_walls = []
        players = self.game_service.db.query(Player).all()

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)

                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(existing_walls)

                    try:
                        test_board.place_wall(wall)
                        possible_walls.append({
                            "x": x,
                            "y": y,
                            "orientation": orientation,
                            "type": "wall"
                        })
                    except Exception:
                        continue  # Ignore murs invalides

        return possible_walls

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            return self._evaluate_state(current_player, opponent, walls, board)

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls)

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval

        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        # Ajout des murs dans l'évaluation
        my_walls = player.walls_left
        opp_walls = opponent.walls_left

        # Pondération des éléments : on peut ajuster ces coefficients
        dist_score = opp_dist - my_dist                # Favorise un chemin plus court pour soi
        wall_score = (my_walls - opp_walls) * 0.5      # Favorise le joueur avec plus de murs

        return dist_score + wall_score
 # Plus la distance de l'adversaire est grande, mieux c’est

import heapq
from copy import deepcopy

from copy import deepcopy
from collections import deque

from copy import deepcopy
import time

from collections import deque
from copy import deepcopy
import time

from copy import deepcopy
from collections import deque

from copy import deepcopy
from collections import deque

from copy import deepcopy

from copy import deepcopy

from copy import deepcopy
import math
from collections import deque, defaultdict
from heapq import heappush, heappop

class AdvancedAIPlusmliha(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score = float("-inf")
        best_action = None

        actions = self._generate_all_actions(player, board, walls, players)

        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=3,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _generate_all_actions(self, player, board, walls, players):
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        directions = ["up", "down", "left", "right"]

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        if player.walls_left > 0:
            wall_actions = self._generate_strategic_walls(board, walls, player)
            actions += wall_actions

        return actions

    def _generate_strategic_walls(self, board, existing_walls, player):
        """Filtre les murs qui allongent significativement le chemin adverse."""
        possible_walls = []
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        base_path = self.calculate_shortest_path(opponent, board, existing_walls)
        base_length = len(base_path) if base_path else float("inf")

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)

                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(existing_walls)

                    try:
                        test_board.place_wall(wall)
                        new_path = self.calculate_shortest_path(opponent, board, test_board.walls)
                        new_length = len(new_path) if new_path else float("inf")
                        if new_length > base_length:
                            possible_walls.append({
                                "x": x,
                                "y": y,
                                "orientation": orientation,
                                "type": "wall"
                            })
                    except Exception:
                        continue

        return possible_walls

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            return self._evaluate_state(current_player, opponent, walls, board)

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls, players)

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval

        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        # Amélioration : combiner murs restants et distance
        wall_factor = 3
        return (opp_dist - my_dist) + wall_factor * (player.walls_left - opponent.walls_left)

class AdvancedAIMarcheMaisKIFKIF(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score = float("-inf")
        best_action = None

        actions = self._generate_all_actions(player, board, walls, players, state)

        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=3,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _generate_all_actions(self, player, board, walls, players, state):
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        turn_number = getattr(state, "turn", 0)

        early_game = turn_number <= 3

        # Tentative de blocage avec des murs stratégiques
        if early_game and player.walls_left > 0:
            wall_actions = self._generate_strategic_walls(board, walls, player)
            if wall_actions:
                return wall_actions
            else:
                # fallback : poser un mur valide peu importe l'effet stratégique
                for x in range(board.width - 1):
                    for y in range(board.height - 1):
                        for orientation in ["horizontal", "vertical"]:
                            try:
                                test_board = GameBoard(size=board.width)
                                test_board.set_players({p.id: deepcopy(p) for p in players})
                                test_board.walls = deepcopy(walls)
                                test_board.place_wall(Wall(x=x, y=y, orientation=orientation))
                                return [{
                                    "x": x,
                                    "y": y,
                                    "orientation": orientation,
                                    "type": "wall"
                                }]
                            except Exception:
                                continue

        # Sinon : mouvement ou murs stratégiques plus tardifs
        directions = ["up", "down", "left", "right"]
        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        if player.walls_left > 0:
            wall_actions = self._generate_strategic_walls(board, walls, player)
            actions += wall_actions

        return actions

    def _generate_strategic_walls(self, board, existing_walls, player):
        """Filtre les murs qui allongent le chemin adverse."""
        possible_walls = []
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        base_path = self.calculate_shortest_path(opponent, board, existing_walls)
        base_length = len(base_path) if base_path else float("inf")

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)

                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(existing_walls)

                    try:
                        test_board.place_wall(wall)
                        new_path = self.calculate_shortest_path(opponent, board, test_board.walls)
                        new_length = len(new_path) if new_path else float("inf")
                        if new_length - base_length >= 1:  # Peut être 0 pour + d'agressivité
                            possible_walls.append({
                                "x": x,
                                "y": y,
                                "orientation": orientation,
                                "type": "wall"
                            })
                    except Exception:
                        continue

        return possible_walls

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            return self._evaluate_state(current_player, opponent, walls, board)

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls, players, {"turn": 99})  # Pas early_game en récursif

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        wall_factor = 3
        return (opp_dist - my_dist) + wall_factor * (player.walls_left - opponent.walls_left)


import math
from copy import deepcopy

import math
from copy import deepcopy

class AdvancedAIUnbattableFake(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self.used_wall_positions = set()

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score, best_action = -math.inf, None
        actions = self._generate_all_actions(player, board, walls, players)

        for action in actions:
            new_players, new_walls = deepcopy(players), deepcopy(walls)
            if action["type"] == "player":
                p = next(p for p in new_players if p.id == self.player_id)
                p.position = action["position"]
            else:
                new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

            score = self._minimax(new_players, new_walls, board, depth=4,
                                   maximizing=False, alpha=-math.inf, beta=math.inf)
            if score > best_score:
                best_score, best_action = score, action

        if best_action and best_action.get("type") == "wall":
            self.used_wall_positions.add((best_action["x"], best_action["y"], best_action["orientation"]))
        return best_action

    def _generate_all_actions(self, player, board, walls, players):
        bl = GameBoard(size=board.width)
        bl.set_players({p.id: p for p in players})
        bl.walls = walls

        moves = [{"type": "player", "position": bl.calculate_new_position(player.position, d)}
                 for d in ["up", "down", "left", "right"] if bl.is_valid_move(player, d)]

        if player.walls_left > 0:
            strat = self._generate_strategic_walls(board, walls, players, player)
            fallback = self._generate_any_valid_wall(board, walls, players)
            if strat:
                moves += strat
            elif fallback:
                moves += fallback

        return moves

    def _generate_strategic_walls(self, board, walls, players, player):
        opponent = next(p for p in players if p.id != self.player_id)
        base = self.calculate_shortest_path(opponent, board, walls)
        base_len = len(base) if base else float("inf")

        results = []
        for x in range(board.width - 1):
            for y in range(board.width - 1):
                for orient in ["horizontal", "vertical"]:
                    key = (x, y, orient)
                    if key in self.used_wall_positions:
                        continue
                    tb = GameBoard(size=board.width)
                    tb.set_players({p.id: deepcopy(p) for p in players})
                    tb.walls = deepcopy(walls)
                    try:
                        tb.place_wall(Wall(x=x, y=y, orientation=orient))
                        np = self.calculate_shortest_path(opponent, board, tb.walls)
                        if np and len(np) > base_len + 1:
                            results.append({"type": "wall", "x": x, "y": y, "orientation": orient})
                    except:
                        pass
        return results

    def _generate_any_valid_wall(self, board, walls, players):
        for x in range(board.width - 1):
            for y in range(board.width - 1):
                for orient in ["horizontal", "vertical"]:
                    key = (x, y, orient)
                    if key in self.used_wall_positions:
                        continue
                    tb = GameBoard(size=board.width)
                    tb.set_players({p.id: deepcopy(p) for p in players})
                    tb.walls = deepcopy(walls)
                    try:
                        tb.place_wall(Wall(x=x, y=y, orientation=orient))
                        return [{"type": "wall", "x": x, "y": y, "orientation": orient}]
                    except:
                        pass
        return []

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        me = next(p for p in players if p.id == self.player_id)
        opp = next(p for p in players if p.id != self.player_id)

        if depth == 0 or self._check_terminal(players, board):
            return self._evaluate(me, opp, walls, board)

        active = me if maximizing else opp
        moves = self._generate_all_actions(active, board, walls, players)

        best = -math.inf if maximizing else math.inf
        for m in moves:
            np_players, np_walls = deepcopy(players), deepcopy(walls)
            target = next(p for p in np_players if p.id == active.id)
            if m["type"] == "player":
                target.position = m["position"]
            else:
                np_walls.append(Wall(x=m["x"], y=m["y"], orientation=m["orientation"]))

            val = self._minimax(np_players, np_walls, board, depth - 1, not maximizing, alpha, beta)
            if maximizing:
                best = max(best, val)
                alpha = max(alpha, best)
            else:
                best = min(best, val)
                beta = min(beta, best)
            if beta <= alpha:
                break
        return best

    def _evaluate(self, me, opp, walls, board):
        myp = self.calculate_shortest_path(me, board, walls)
        oppp = self.calculate_shortest_path(opp, board, walls)
        md = len(myp) if myp else float("inf")
        od = len(oppp) if oppp else float("inf")

        score = (od - md) * 2
        score += 5 * (me.walls_left - opp.walls_left)
        if od - md > 3 and me.walls_left > 0:
            score += 10
        return score

    def _check_terminal(self, players, board):
        for p in players:
            if p.direction == Direction.UP and p.position["x"] == 0:
                return True
            if p.direction == Direction.DOWN and p.position["x"] == board.width - 1:
                return True
        return False


class AdvancedAIPlusmliha(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self.turn_count = 0  # Compteur pour suivre la phase du jeu

    def choose_move(self):
        self.turn_count += 1  # Incrémenter à chaque appel (tour)

        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score = float("-inf")
        best_action = None

        # Générer actions selon phase du jeu
        actions = self._generate_all_actions(player, board, walls, players)

        # Explorer chaque action possible avec minimax
        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=3,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _generate_all_actions(self, player, board, walls, players):
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        directions = ["up", "down", "left", "right"]

        # Stratégie de phase selon nombre de murs restants et tour actuel
        early_game = (self.turn_count < 10) and (player.walls_left > 0)

        # Si début de partie, priorité murs stratégiques
        if early_game:
            # Générer murs qui rallongent le chemin adverse
            wall_actions = self._generate_strategic_walls(board, walls, player)
            if wall_actions:
                actions += wall_actions
                return actions  # Ne pas ajouter déplacements dans early_game pour privilégier murs

        # Sinon (fin de partie ou pas de murs intéressants) générer déplacements
        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        # En phase plus avancée, on ajoute murs si utile
        if player.walls_left > 0 and not early_game:
            wall_actions = self._generate_strategic_walls(board, walls, player)
            actions += wall_actions

        return actions

    def _generate_strategic_walls(self, board, existing_walls, player):
        """Filtre les murs qui allongent significativement le chemin adverse."""
        possible_walls = []
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        base_path = self.calculate_shortest_path(opponent, board, existing_walls)
        base_length = len(base_path) if base_path else float("inf")

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)

                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(existing_walls)

                    try:
                        test_board.place_wall(wall)
                        new_path = self.calculate_shortest_path(opponent, board, test_board.walls)
                        new_length = len(new_path) if new_path else float("inf")
                        if new_length > base_length:
                            possible_walls.append({
                                "x": x,
                                "y": y,
                                "orientation": orientation,
                                "type": "wall"
                            })
                    except Exception:
                        continue

        return possible_walls

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            return self._evaluate_state(current_player, opponent, walls, board)

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls, players)

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"], y=action["y"], orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval

        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"], y=action["y"], orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        wall_factor = 3  # Poids pour murs restants

        # Score = différentiel distance + avantage murs restants
        return (opp_dist - my_dist) + wall_factor * (player.walls_left - opponent.walls_left)




from copy import deepcopy

class AdvancedAIsautedeuxCases(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.get_all_players()

        opponent = next(p for p in players if p.id != self.player_id)
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        print(f"[AdvancedAI] My path: {my_dist}, Opponent path: {opp_dist}")

        if player.walls_left > 0 and opp_dist - my_dist >= 2:
            best_wall = self._find_best_blocking_wall(board, walls, players)
            if best_wall:
                return best_wall

        if my_path and len(my_path) > 1:
            return {
                "type": "player",
                "position": {
                    "x": my_path[1][0],
                    "y": my_path[1][1]
                }
            }

        return None

    def _find_best_blocking_wall(self, board, walls, players):
        opponent = next(p for p in players if p.id != self.player_id)
        base_path = self.calculate_shortest_path(opponent, board, walls)
        base_len = len(base_path) if base_path else float("inf")

        best_wall = None
        best_increase = 0

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)
                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(walls)

                    try:
                        test_board.place_wall(wall)
                        new_path = self.calculate_shortest_path(opponent, board, test_board.walls)
                        new_len = len(new_path) if new_path else float("inf")
                        increase = new_len - base_len

                        if increase > best_increase and self._does_not_block_self(players, wall, board, walls):
                            best_increase = increase
                            best_wall = {
                                "type": "wall",
                                "x": x,
                                "y": y,
                                "orientation": orientation
                            }
                    except Exception:
                        continue

        return best_wall if best_increase >= 2 else None

    def _does_not_block_self(self, players, wall, board, walls):
        test_board = GameBoard(size=board.width)
        test_board.set_players({p.id: deepcopy(p) for p in players})
        test_board.walls = deepcopy(walls)

        try:
            test_board.place_wall(wall)
            me = next(p for p in players if p.id == self.player_id)
            path = self.calculate_shortest_path(me, board, test_board.walls)
            return path is not None
        except Exception:
            return False
        



from copy import deepcopy
import math
from collections import deque

import math
import random
import time
from copy import deepcopy
from collections import deque

class MCTSNode:
    def __init__(self, joueurs, murs, parent=None, coup=None, joueur_id=None):
        self.joueurs = joueurs              # dict id -> Player (copie)
        self.murs = murs                    # liste murs (copie)
        self.parent = parent
        self.coup = coup                    # coup qui mène à ce noeud
        self.joueur_id = joueur_id          # joueur qui a joué ce coup
        self.enfants = []
        self.visites = 0
        self.score = 0.0

    def est_feuille(self):
        return len(self.enfants) == 0

    def meilleur_enfant(self, c_param=1.4):
        # UCT : Upper Confidence Bound pour la sélection
        choices_weights = [
            (enfant.score / enfant.visites) + c_param * math.sqrt(math.log(self.visites) / enfant.visites)
            for enfant in self.enfants
        ]
        max_index = choices_weights.index(max(choices_weights))
        return self.enfants[max_index]

from copy import deepcopy
from collections import deque
import heapq

from copy import deepcopy

from copy import deepcopy

import heapq
from copy import deepcopy

import heapq
from copy import deepcopy

import heapq
import random
import time
from copy import deepcopy

import time
import random
import heapq
from copy import deepcopy
from math import sqrt

class MCTSNode:
    def __init__(self, state, current_player_id, parent=None, action=None):
        self.state = state  # (players, walls, board)
        self.current_player_id = current_player_id
        self.parent = parent
        self.children = []
        self.visits = 0
        self.wins = 0
        self.action = action

    def ucb1(self, c=sqrt(2)):
        if self.visits == 0:
            return float('inf')
        return (self.wins / self.visits) + c * sqrt((2 * (self.parent.visits if self.parent else 1)) / self.visits)



class AdvancedAIDump(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        best_score = float("-inf")
        best_action = None

        actions = self._generate_all_actions(player, board, walls, opponent)

        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=3,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

        return best_action

    def _generate_all_actions(self, player, board, walls, opponent):
        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        if player.walls_left > 0:
            wall_actions = self._generate_possible_walls(board, walls)
            aggressive_walls = self._generate_aggressive_walls(opponent, board, walls)
            actions += wall_actions + aggressive_walls

        return actions

    def _generate_possible_walls(self, board, existing_walls):
        possible_walls = []
        players = self.game_service.db.query(Player).all()

        for x in range(board.width - 1):
            for y in range(board.height - 1):
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)

                    test_board = GameBoard(size=board.width)
                    test_board.set_players({p.id: deepcopy(p) for p in players})
                    test_board.walls = deepcopy(existing_walls)

                    try:
                        test_board.place_wall(wall)
                        possible_walls.append({
                            "x": x,
                            "y": y,
                            "orientation": orientation,
                            "type": "wall"
                        })
                    except Exception:
                        continue

        return possible_walls

    def _generate_aggressive_walls(self, opponent, board, walls):
        path = self.calculate_shortest_path(opponent, board, walls)
        if not path or len(path) < 2:
            return []

        block_positions = []
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            block_positions.append((min(x1, x2), min(y1, y2)))

        candidate_walls = []
        for x, y in block_positions:
            for orientation in ["horizontal", "vertical"]:
                wall = Wall(x=x, y=y, orientation=orientation)
                test_board = GameBoard(size=board.width)
                test_board.set_players({p.id: deepcopy(p) for p in self.game_service.db.query(Player).all()})
                test_board.walls = deepcopy(walls)

                try:
                    test_board.place_wall(wall)
                    candidate_walls.append({
                        "x": x, "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
                except:
                    continue
        return candidate_walls

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            return self._evaluate_state(current_player, opponent, walls, board)

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls, opponent if maximizing else current_player)

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval

        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        wall_advantage = player.walls_left - opponent.walls_left
        center_bonus = -abs(player.position["x"] - board.width // 2)
        risk_penalty = 0

        if my_dist > opp_dist and player.walls_left < 2:
            risk_penalty = 5

        return (opp_dist - my_dist) + wall_advantage + center_bonus - risk_penalty




class AdvancedAI(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        best_score = float("-inf")
        best_action = None

        actions = self._generate_all_actions(player, board, walls, opponent)
        print(f"[DEBUG] Total actions generated: {len(actions)}")

        # Log murs valides uniquement
        valid_walls = [a for a in actions if a["type"] == "wall"]
        print(f"[DEBUG] Valid walls generated: {len(valid_walls)}")
        for w in valid_walls:
            print(f"  Wall candidate: x={w['x']} y={w['y']} orient={w['orientation']}")

        for action in actions:
            new_walls = deepcopy(walls)
            new_players = deepcopy(players)

            if action["type"] == "player":
                target_player = next(p for p in new_players if p.id == self.player_id)
                target_player.position = action["position"]
            else:
                new_walls.append(Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                ))

            score = self._minimax(
                new_players, new_walls, board, depth=2,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )
            print(f"[DEBUG] Action: {action} => score: {score}")

            if score > best_score:
                best_score = score
                best_action = action

        print(f"[DEBUG] Chosen action: {best_action} with score {best_score}")
        return best_action

    def _generate_all_actions(self, player, board, walls, opponent):
        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        actions = []
        directions = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]

        for d in directions:
            if board_logic.is_valid_move(player, d):
                new_pos = board_logic.calculate_new_position(player.position, d)
                actions.append({
                    "type": "player",
                    "direction": d,
                    "position": new_pos
                })

        if player.walls_left > 0:
            wall_actions = self._generate_possible_walls(board, walls)
            aggressive_walls = self._generate_aggressive_walls(opponent, board, walls)
            print(f"[DEBUG] Possible walls: {len(wall_actions)}, Aggressive walls: {len(aggressive_walls)}")
            actions += wall_actions + aggressive_walls

        return actions

    def _generate_possible_walls(self, board, existing_walls):
        from collections import defaultdict

        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        path = self.calculate_shortest_path(opponent, board, existing_walls)
        if not path or len(path) < 2:
            return []

        wall_candidates = []
        seen = set()
        grouped_by_segment = defaultdict(list)

        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            min_x, min_y = min(x1, x2), min(y1, y2)

            for orientation in ["horizontal", "vertical"]:
                key = (min_x, min_y, orientation)
                if key in seen:
                    continue
                seen.add(key)

                wall = Wall(x=min_x, y=min_y, orientation=orientation)
                test_board = GameBoard(size=board.width)
                test_board.set_players({p.id: deepcopy(p) for p in players})
                test_board.walls = deepcopy(existing_walls)

                if test_board.add_wall(wall):
                    grouped_by_segment[i].append({
                        "x": min_x,
                        "y": min_y,
                        "orientation": orientation,
                        "type": "wall"
                    })

        # Garder un seul mur par segment (filtrage agressif)
        for group in grouped_by_segment.values():
            if group:
                wall_candidates.append(group[0])  # on garde le premier valide

        print(f"[DEBUG][_generate_possible_walls] Filtered aggressive walls: {len(wall_candidates)}")
        return wall_candidates
    def _generate_aggressive_walls(self, opponent, board, walls):
        from collections import defaultdict

        players = self.game_service.db.query(Player).all()
        path = self.calculate_shortest_path(opponent, board, walls)

        if not path or len(path) < 2:
            return []

        seen = set()
        candidates = []
        for i in range(len(path) - 1):
            x1, y1 = path[i]
            x2, y2 = path[i + 1]
            min_x, min_y = min(x1, x2), min(y1, y2)

            for orientation in ["horizontal", "vertical"]:
                key = (min_x, min_y, orientation)
                if key in seen:
                    continue
                seen.add(key)

                wall = Wall(x=min_x, y=min_y, orientation=orientation)
                test_board = GameBoard(size=board.width)
                test_board.set_players({p.id: deepcopy(p) for p in players})
                test_board.walls = deepcopy(walls)

                if test_board.add_wall(wall):
                    candidates.append({
                        "x": min_x,
                        "y": min_y,
                        "orientation": orientation,
                        "type": "wall"
                    })

        print(f"[DEBUG][_generate_aggressive_walls] Found {len(candidates)} candidate aggressive walls")
        return candidates



    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
        current_player = next(p for p in players if p.id == self.player_id)
        opponent = next(p for p in players if p.id != self.player_id)

        if depth == 0:
            eval_score = self._evaluate_state(current_player, opponent, walls, board)
            print(f"[DEBUG][_minimax depth=0] Eval score: {eval_score}")
            return eval_score

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, board, walls, opponent if maximizing else current_player)

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    print("[DEBUG][_minimax pruning] Alpha-Beta cutoff (maximizing)")
                    break
            print(f"[DEBUG][_minimax maximizing] Best eval: {max_eval} at depth {depth}")
            return max_eval

        else:
            min_eval = float("inf")
            for action in actions:
                new_players = deepcopy(players)
                new_walls = deepcopy(walls)
                p = next(p for p in new_players if p.id == active_player.id)

                if action["type"] == "player":
                    p.position = action["position"]
                else:
                    new_walls.append(Wall(
                        x=action["x"],
                        y=action["y"],
                        orientation=action["orientation"]
                    ))

                eval = self._minimax(new_players, new_walls, board, depth - 1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    print("[DEBUG][_minimax pruning] Alpha-Beta cutoff (minimizing)")
                    break
            print(f"[DEBUG][_minimax minimizing] Best eval: {min_eval} at depth {depth}")
            return min_eval

    def _evaluate_state(self, player, opponent, walls, board):
        my_path = self.calculate_shortest_path(player, board, walls)
        opp_path = self.calculate_shortest_path(opponent, board, walls)

        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")

        wall_advantage = player.walls_left - opponent.walls_left
        center_bonus = -abs(player.position["x"] - board.width // 2)
        risk_penalty = 0

        if my_dist > opp_dist and player.walls_left < 2:
            risk_penalty = 5

        score = (opp_dist - my_dist) + wall_advantage + center_bonus - risk_penalty
        print(f"[DEBUG][_evaluate_state] Score: {score} (my_dist={my_dist}, opp_dist={opp_dist}, walls_adv={wall_advantage})")
        return score

from copy import deepcopy
from collections import deque
import heapq
import logging
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from copy import deepcopy
from collections import deque
import heapq
import logging
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from copy import deepcopy
from collections import deque
import heapq
import logging
from functools import lru_cache
from models.player import Player
from models.wall import Wall
from models.enums import Direction, Orientation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedAI3arafa(PathfindingMixin, WallValidationMixin ):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self._cache = {}
        self._last_moves = deque(maxlen=5)
        
    def choose_move(self):
        print("⚠️ CHOOSE_MOVE ACTIVE pour player", self.player_id)

        try:
            print("[DEBUG] Entrée dans choose_move")
            board, state, walls = self.game_service.get_board_and_state()
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(board, walls)
            
            print(f"[DEBUG] Derniers coups : {self._last_moves}")
            # Gestion des ouvertures
            if self._is_opening_move():
                move = self._make_opening_move(player, game_board)
                if move:
                    if move["type"] == "wall":
                        wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
                        if not self.is_fully_valid_wall(wall, game_board):
                            logger.warning(f"🛑 Opening move invalid: {wall}")
                            move = None  # ou return self._fallback_move(...)
                    if move:
                        self._last_moves.append(str(move))
                        return move
                    
            
            # Gestion de la fin de partie
            if self._is_endgame(player, game_board):
                move = self._make_endgame_move(player, game_board)
                if move:
                    if move["type"] == "wall":
                        wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
                        if not self.is_fully_valid_wall(wall, game_board):
                            logger.warning(f"🛑 Endgame move invalid: {wall}")
                            move = None  # ou return self._fallback_move(...)
                    if move:
                        self._last_moves.append(str(move))
                        return move

            
            # Vérification des répétitions de coups
            if len(self._last_moves) > 2 and self._last_moves.count(self._last_moves[-1]) >= 2:
                logger.warning("Detected repeated moves, changing strategy")
                return self._change_strategy(player, game_board)
            
            print("[DEBUG] Génération des actions...")
            # Génération des actions possibles
            actions = self._generate_all_actions(player, game_board)
            print(f"[DEBUG] {len(actions)} actions générées")

            if not actions:
                raise ValueError("No valid actions available")
            
            # Sélection de la meilleure action
            best_action = self._select_best_action(actions, player, game_board)
            print(f"[DEBUG] Action choisie : {best_action}")
            if best_action:
                if best_action["type"] == "wall":
                        wall_pos = (best_action["x"], best_action["y"])
                        existing_positions = {(w.x, w.y) for w in game_board.walls}
                        
                        if wall_pos in existing_positions:
                            logger.warning(f"Wall position {wall_pos} occupied, changing strategy")
                            return self._change_strategy(player, game_board)
                    
            
                self._last_moves.append(str(best_action))
                return best_action
            
            return self._fallback_move(player, game_board)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {str(e)}")
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(*self.game_service.get_board_and_state()[:2])
            return self._fallback_move(player, game_board)

    def _create_game_board(self, board, walls):
        """Crée un objet GameBoard à partir des données du jeu"""
        game_board = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        game_board.set_players({p.id: p for p in players})
        game_board.walls = walls
        return game_board

    def _select_best_action(self, actions, player, game_board):
        """Sélectionne la meilleure action avec l'algorithme Minimax"""
        best_score = float("-inf")
        best_action = None
        depth = self._determine_search_depth(player)
        
        for action in actions:
            # Copier les joueurs
            new_players = {
                pid: Player(
                    id=player.id,
                    position=dict(player.position),  # copie de la position
                    direction=player.direction,
                    walls_left=player.walls_left
                )
                for pid, player in game_board.players.items()
            }

            # Copier les murs
            new_walls = [
                Wall(x=w.x, y=w.y, orientation=w.orientation, player_id=w.player_id)
                for w in game_board.walls
            ]

            # Appliquer l'action
            if action["type"] == "player":
                new_players[self.player_id].position = action["position"]
            else:
                wall = Wall(
                    x=action["x"],
                    y=action["y"],
                    orientation=action["orientation"]
                )
                # Valider le mur sur un GameBoard temporaire
                test_board = GameBoard(size=game_board.size)
                test_board.set_players(new_players)
                test_board.walls = new_walls + [wall]
                if not self.is_fully_valid_wall(wall, test_board):
                    continue
                # Mur invalide, on ignore

                new_walls.append(wall)

            # Construire un nouveau GameBoard avec ces copies
            new_game_board = GameBoard(size=game_board.size)
            new_game_board.set_players(new_players)
            new_game_board.walls = new_walls

            try:
                score = self._minimax(
                    new_game_board, depth, False, float("-inf"), float("inf")
                )
            except Exception as e:
                logger.warning(f"Minimax error for action {action}: {str(e)}")
                continue  # Si l’évaluation échoue, on ignore cette action

            if score > best_score:
                best_score = score
                best_action = action


        return best_action


    def _generate_all_actions(self, player, game_board):
        """Génère toutes les actions possibles"""
        actions = []
        print("jes SUISSSS APPELLLE")
        # Mouvements du joueur
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                actions.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos
                })

        # Murs (seulement si le joueur en a)
        if player.walls_left > 0:
            wall_candidates = self._generate_strategic_walls(game_board)
            for wall_action in wall_candidates:
                wall = Wall(
                    x=wall_action["x"],
                    y=wall_action["y"],
                    orientation=wall_action["orientation"]
                )
                if self.is_fully_valid_wall(wall, game_board):
                    actions.append(wall_action)
                else:
                    logger.warning(f"Wall rejected at generation: ({wall.x}, {wall.y}) {wall.orientation}")



        return actions

    def _generate_strategic_walls(self, game_board):
        """Version optimisée avec filtrage précoce"""
        hot_spots = self._find_hot_spots(game_board)
        existing_positions = {(w.x, w.y) for w in game_board.walls}
        
        # Pré-calcul des zones intéressantes
        strategic_spots = [
            (x, y) for x, y in hot_spots 
            if (x, y) not in existing_positions
            and 0 <= x < game_board.size - 1
            and 0 <= y < game_board.size - 1
        ]
        
        # Génération avec validation immédiate
        return [
            {"x": x, "y": y, "orientation": o, "type": "wall"}
            for x, y in strategic_spots
            for o in ["horizontal", "vertical"]
            if self.is_fully_valid_wall(Wall(x=x, y=y, orientation=o), game_board)
        ]
        

    def _find_hot_spots(self, game_board):
        """Trouve les positions stratégiques pour les murs"""
        hot_spots = set()
        
        for player in game_board.players.values():
            if player.id == self.player_id:
                continue
                
            path = self._calculate_shortest_path(player, game_board)
            if path:
                for i in range(1, min(4, len(path))):
                    pos = path[i]
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            x, y = pos["x"] + dx, pos["y"] + dy
                            if 0 <= x < game_board.size - 1 and 0 <= y < game_board.size - 1:
                                hot_spots.add((x, y))
        
        return list(hot_spots)

    def _calculate_shortest_path(self, player, game_board):
        """Calcule le chemin le plus court pour un joueur"""
        from collections import deque
        
        start = player.position
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        visited = set()
        queue = deque([(start["x"], start["y"], [])])
        
        while queue:
            x, y, path = queue.popleft()
            
            if x == target_row:
                return path + [{"x": x, "y": y}]
            
            if (x, y) in visited:
                continue
                
            visited.add((x, y))
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < game_board.size and 0 <= ny < game_board.size:
                    if not game_board.is_blocked(x, y, nx, ny):
                        queue.append((nx, ny, path + [{"x": x, "y": y}]))
        
        return None

    def _minimax(self, game_board, depth, maximizing, alpha, beta):
        """Version optimisée avec élagage précoce"""
        cache_key = self._create_cache_key(game_board, depth, maximizing)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Évaluation terminale simplifiée
        if depth == 0:
            return self._fast_evaluate(game_board)
        
        # Génération des actions avec tri pour élagage optimal
        actions = sorted(
            self._generate_all_actions(game_board.players[self.player_id if maximizing else self.opponent_id], game_board),
            key=lambda a: self._action_heuristic(a, game_board),
            reverse=maximizing
        )
        
        best_value = -math.inf if maximizing else math.inf
        
        for action in actions:
            new_board = self._apply_action(game_board, action, self.player_id if maximizing else self.opponent_id)
            value = self._minimax(new_board, depth-1, not maximizing, alpha, beta)
            
            if maximizing:
                if value > best_value:
                    best_value = value
                if best_value >= beta:
                    break
                alpha = max(alpha, best_value)
            else:
                if value < best_value:
                    best_value = value
                if best_value <= alpha:
                    break
                beta = min(beta, best_value)
        
        self._cache[cache_key] = best_value
        return best_value
    def _apply_action(self, game_board, action, player_id):
        """Version optimisée avec copie légère"""
        # Copie shallow des éléments nécessaires seulement
        new_players = {
            pid: Player(
                id=p.id,
                position=p.position.copy(),  # Copie shallow de la position
                direction=p.direction,
                walls_left=p.walls_left
            )
            for pid, p in game_board.players.items()
        }
        
        new_walls = [Wall(w.x, w.y, w.orientation) for w in game_board.walls]
        
        if action["type"] == "player":
            new_players[player_id].position = action["position"]
        else:
            new_walls.append(Wall(
                x=action["x"],
                y=action["y"],
                orientation=action["orientation"]
            ))
        
        new_board = GameBoard(size=game_board.size)
        new_board.set_players(new_players)
        new_board.walls = new_walls
        
        return new_board

    def _create_cache_key(self, game_board, depth, maximizing):
        """Crée une clé de cache unique"""
        players_key = tuple(
            (pid, p.position["x"], p.position["y"], p.walls_left)
            for pid, p in sorted(game_board.players.items())
        )
        walls_key = tuple(
            (w.x, w.y, w.orientation)
            for w in sorted(game_board.walls, key=lambda x: (x.x, x.y, x.orientation))
        )
        return (players_key, walls_key, depth, maximizing)

    def _is_opening_move(self):
        """Détermine si c'est le début de la partie"""
        players = self.game_service.db.query(Player).all()
        total_walls_placed = sum(9 - p.walls_left for p in players)
        return total_walls_placed < 2

    def _make_opening_move(self, player, game_board):
        """Stratégie d'ouverture"""
        if player.id == 1:  # Premier joueur
            if game_board.is_valid_move(player, "up"):
                return {
                    "type": "player",
                    "direction": "up",
                    "position": game_board.calculate_new_position(player.position, "up")
                }
        else:  # Deuxième joueur
            center_x, center_y = game_board.size // 2 - 1, game_board.size // 2 - 1
            try:
                test_wall = Wall(x=center_x, y=center_y, orientation="horizontal")
                test_board = deepcopy(game_board)
                test_board.walls.append(test_wall)
                if all(test_board.has_path(p) for p in test_board.players.values()):
                    return {
                        "type": "wall",
                        "x": center_x,
                        "y": center_y,
                        "orientation": "horizontal"
                    }
            except:
                pass
            
            # Fallback: avancer
            if game_board.is_valid_move(player, "up"):
                return {
                    "type": "player",
                    "direction": "up",
                    "position": game_board.calculate_new_position(player.position, "up")
                }
        return None

    def _is_endgame(self, player, game_board):
        """Détecte la fin de partie"""
        path = self._calculate_shortest_path(player, game_board)
        return path and len(path) <= 3

    def _make_endgame_move(self, player, game_board):
        """Stratégie de fin de partie"""
        best_move = None
        min_distance = float('inf')
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                
                # Vérifie si c'est un mouvement gagnant
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
                
                # Sinon évalue la distance
                temp_player = deepcopy(player)
                temp_player.position = new_pos
                path = self._calculate_shortest_path(temp_player, game_board)
                
                if path and len(path) < min_distance:
                    min_distance = len(path)
                    best_move = {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        return best_move

    def _change_strategy(self, player, game_board):
        """Change de stratégie quand des répétitions sont détectées"""
        # Essaye d'abord de bouger le pion
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                move = {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
                self._last_moves.append(str(move))
                return move
        
        # Si aucun mouvement n'est possible, trouve un mur différent
        existing_walls = {(w.x, w.y, w.orientation) for w in game_board.walls}
        for x in range(game_board.size - 1):
            for y in range(game_board.size - 1):
                for orientation in ["horizontal", "vertical"]:
                    if (x, y, orientation) not in existing_walls:
                        try:
                            test_wall = Wall(x=x, y=y, orientation=orientation)
                            test_board = deepcopy(game_board)
                            test_board.walls.append(test_wall)
                            if all(test_board.has_path(p) for p in test_board.players.values()):
                                move = {
                                    "type": "wall",
                                    "x": x,
                                    "y": y,
                                    "orientation": orientation
                                }
                                self._last_moves.append(str(move))
                                return move
                        except:
                            continue
        return self._fallback_move(player, game_board)

    def _fallback_move(self, player, game_board):
        """Dernier recours quand tout échoue"""
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                return {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
        return {"type": "player", "direction": "up", "position": player.position}

    def _determine_search_depth(self, player):
        """Détermine la profondeur de recherche adaptative"""
        if player.walls_left < 3:  # Fin de partie
            return 4
        players = self.game_service.db.query(Player).all()
        if len(players) == 2 and sum(p.walls_left for p in players) < 10:
            return 3
        return 2

    def _is_winning_state(self, player, opponent, game_board):
        """Vérifie si un joueur a gagné"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        return player.position["x"] == target_row

    def _evaluate_state(self, player, opponent, game_board):
        """Évaluation complète de l'état du jeu"""
        # Calcul des chemins les plus courts
        my_path = self._calculate_shortest_path(player, game_board)
        opp_path = self._calculate_shortest_path(opponent, game_board)
        
        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")
        
        # Facteurs d'évaluation
        distance_diff = (opp_dist - my_dist) * 2.0
        walls_diff = (player.walls_left - opponent.walls_left) * 0.5
        center_bonus = self._calculate_center_bonus(player.position, game_board.size) * 0.3
        blocking = self._calculate_blocking_potential(opponent, game_board) * 1.5
        mobility = self._calculate_mobility(player, game_board) * 0.2
        
        return distance_diff + walls_diff + center_bonus + blocking + mobility

    def _calculate_center_bonus(self, position, board_size):
        """Bonus pour être près du centre"""
        center = board_size // 2
        dist_to_center = abs(position["x"] - center) + abs(position["y"] - center)
        return -dist_to_center * 0.1

    def _calculate_blocking_potential(self, opponent, game_board):
        """Évalue le potentiel de blocage"""
        score = 0
        path = self._calculate_shortest_path(opponent, game_board)
        
        if path and len(path) > 1:
            current_pos = opponent.position
            next_pos = path[1]
            if self._can_block_move(current_pos, next_pos, game_board):
                score += 2
        
        return score

    def _can_block_move(self, current_pos, next_pos, game_board):
        """Vérifie si un mur peut bloquer ce mouvement"""
        dx = next_pos["x"] - current_pos["x"]
        dy = next_pos["y"] - current_pos["y"]
        
        if dx > 0:  # Vers le bas
            wall_x, wall_y = current_pos["x"], min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dx < 0:  # Vers le haut
            wall_x, wall_y = current_pos["x"]-1, min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dy > 0:  # Vers la droite
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]
            orientation = "horizontal"
        else:  # Vers la gauche
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]-1
            orientation = "horizontal"
        
        try:
            test_wall = Wall(x=wall_x, y=wall_y, orientation=orientation)
            test_board = deepcopy(game_board)
            test_board.walls.append(test_wall)
            return all(test_board.has_path(p) for p in test_board.players.values())
        except:
            return False

    def _calculate_mobility(self, player, game_board):
        """Calcule la mobilité du joueur"""
        return sum(
            1 for direction in ["up", "down", "left", "right"] 
            if game_board.is_valid_move(player, direction)
        )

    def apply_move_to_db(self, move):
        if move["type"] == "wall":
            with self.game_service.db.begin() as transaction:
                # Vérification atomique
                exists = self.game_service.db.query(
                    exists().where(
                        and_(
                            Wall.x == move["x"],
                            Wall.y == move["y"]
                        )
                    )
                ).scalar()
                
                if exists:
                    logger.warning(f"Wall position {move['x']},{move['y']} already occupied")
                    transaction.rollback()
                    return False
                    
                wall = Wall(
                    x=move["x"],
                    y=move["y"],
                    orientation=move["orientation"].upper(),
                    player_id=self.player_id
                )
                self.game_service.db.add(wall)
                logger.info(f"Wall successfully placed at {wall.x},{wall.y}")
            return True
        return False
    def _generate_wall_candidates(self, game_board):
        """Génère des candidats murs avec vérification des croisements"""
        candidates = []
        hot_spots = self._find_hot_spots(game_board)
        existing_walls = {(w.x, w.y): w.orientation for w in game_board.walls}
        
        for x, y in hot_spots:
            # Ne pas proposer de mur là où il y a déjà un mur (quelque soit l'orientation)
            if (x, y) not in existing_walls:
                for orientation in ["horizontal", "vertical"]:
                    candidates.append({
                        "x": x,
                        "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
        
        return candidates
    
    def is_fully_valid_wall(self, wall, game_board):
        # Validation logique de base
        if not game_board._is_valid_wall(wall):
            return False
        
        # Validation des chemins (aucun joueur ne doit être bloqué)
        # On clone le plateau pour tester l'ajout du mur
        test_board = GameBoard(size=game_board.size)
        
        # Copie des joueurs
        new_players = {
            pid: Player(
                id=p.id,
                position=dict(p.position),
                direction=p.direction,
                walls_left=p.walls_left
            ) for pid, p in game_board.players.items()
        }
        test_board.set_players(new_players)
        
        # Copie des murs + ajout du nouveau
        test_board.walls = [Wall(x=w.x, y=w.y, orientation=w.orientation, player_id=w.player_id) for w in game_board.walls] + [wall]
        
        # Vérifie qu'il y a un chemin pour chaque joueur
        return all(test_board.has_path(p) for p in test_board.players.values())

import math
from copy import deepcopy

class AdvancedAI0espor(PathfindingMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self.used_wall_positions = set()

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()

        best_score, best_action = -math.inf, None
        actions = self._generate_all_actions(player, board, walls, players)

        # Debug print to check actions
        print(f"[DEBUG] Actions count: {len(actions)}")

        for action in actions:
            new_players, new_walls = deepcopy(players), deepcopy(walls)
            if action["type"] == "player":
                p = next(p for p in new_players if p.id == self.player_id)
                p.position = action["position"]
            else:
                new_walls.append(Wall(x=action["x"], y=action["y"], orientation=action["orientation"]))

            score = self._minimax(new_players, new_walls, board, depth=4,
                                   maximizing=False, alpha=-math.inf, beta=math.inf)
            if score > best_score:
                best_score, best_action = score, action

        if best_action and best_action.get("type") == "wall":
            self.used_wall_positions.add((best_action["x"], best_action["y"], best_action["orientation"]))

        print(f"[DEBUG] Chosen action: {best_action}")
        return best_action

    def _generate_all_actions(self, player, board, walls, players):
        bl = GameBoard(size=board.width)
        bl.set_players({p.id: p for p in players})
        bl.walls = walls

        moves = [{"type": "player", "position": bl.calculate_new_position(player.position, d)}
                 for d in ["up", "down", "left", "right"] if bl.is_valid_move(player, d)]

        if player.walls_left > 0:
            strategic_walls = self._generate_strategic_walls(board, walls, players, player)
            if strategic_walls:
                moves += strategic_walls
            else:
                fallback_walls = self._generate_any_valid_wall(board, walls, players)
                moves += fallback_walls

        return moves

    def _generate_strategic_walls(self, board, walls, players, player):
        opponent = next(p for p in players if p.id != self.player_id)
        base_path = self.calculate_shortest_path(opponent, board, walls)
        base_len = len(base_path) if base_path else float("inf")

        results = []
        for x in range(board.width - 1):
            for y in range(board.width - 1):
                for orient in ["horizontal", "vertical"]:
                    key = (x, y, orient)
                    if key in self.used_wall_positions:
                        continue
                    tb = GameBoard(size=board.width)
                    tb.set_players({p.id: deepcopy(p) for p in players})
                    tb.walls = deepcopy(walls)

                    new_wall = Wall(x=x, y=y, orientation=orient)
                    if tb.add_wall(new_wall):
                        new_path = self.calculate_shortest_path(opponent, tb, tb.walls)
                        new_len = len(new_path) if new_path else float("inf")
                        if new_len > base_len + 1:
                            results.append({"type": "wall", "x": x, "y": y, "orientation": orient})
        print(f"[DEBUG] Strategic walls found: {len(results)}")
        return results


    def _generate_any_valid_wall(self, board, walls, players):
        for x in range(board.width - 1):
            for y in range(board.width - 1):
                for orient in ["horizontal", "vertical"]:
                    key = (x, y, orient)
                    if key in self.used_wall_positions:
                        continue
                    tb = GameBoard(size=board.width)
                    tb.set_players({p.id: deepcopy(p) for p in players})
                    tb.walls = deepcopy(walls)

                    new_wall = Wall(x=x, y=y, orientation=orient)
                    if tb.add_wall(new_wall):
                        return [{"type": "wall", "x": x, "y": y, "orientation": orient}]
        return []

    def _minimax(self, players, walls, board, depth, maximizing, alpha, beta):
            me = next(p for p in players if p.id == self.player_id)
            opp = next(p for p in players if p.id != self.player_id)

            if depth == 0 or self._check_terminal(players, board):
                return self._evaluate(me, opp, walls, board)

            active = me if maximizing else opp
            moves = self._generate_all_actions(active, board, walls, players)

            best = -math.inf if maximizing else math.inf
            for m in moves:
                np_players, np_walls = deepcopy(players), deepcopy(walls)
                target = next(p for p in np_players if p.id == active.id)
                if m["type"] == "player":
                    target.position = m["position"]
                else:
                    np_walls.append(Wall(x=m["x"], y=m["y"], orientation=m["orientation"]))

                val = self._minimax(np_players, np_walls, board, depth - 1, not maximizing, alpha, beta)
                if maximizing:
                    best = max(best, val)
                    alpha = max(alpha, best)
                else:
                    best = min(best, val)
                    beta = min(beta, val)
                if beta <= alpha:
                    break
            return best

    def _evaluate(self, me, opp, walls, board):
        myp = self.calculate_shortest_path(me, board, walls)
        oppp = self.calculate_shortest_path(opp, board, walls)
        md = len(myp) if myp else float("inf")
        od = len(oppp) if oppp else float("inf")

        score = (od - md) * 1 + 10 * (me.walls_left - opp.walls_left)
        if od - md > 2 and me.walls_left > 0:
            score += 20
        return score

    def _check_terminal(self, players, board):
        for p in players:
            # Exemple condition victoire selon direction (à adapter)
            if p.direction == Direction.UP and p.position["x"] == 0:
                return True
            if p.direction == Direction.DOWN and p.position["x"] == board.width - 1:
                return True
        return False

'''
import math
from collections import deque, defaultdict
from copy import deepcopy
from functools import lru_cache
import logging
from sqlalchemy import exists, and_

logger = logging.getLogger(__name__)

class AdvancedAI(PathfindingMixin, WallValidationMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self._cache = {}
        self._last_moves = deque(maxlen=5)
        self._transposition_table = {}
        self._killer_moves = defaultdict(list)
        
    def choose_move(self):
        try:
            board, state, walls = self.game_service.get_board_and_state()
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(board, walls)
            
            # Gestion des ouvertures avec book moves
            if self._is_opening_move():
                move = self._get_book_move(player, game_board)
                if move and self._validate_move(move, player, game_board):
                    self._last_moves.append(str(move))
                    return move
            
            # Gestion de la fin de partie
            if self._is_endgame(player, game_board):
                move = self._make_endgame_move(player, game_board)
                if move and self._validate_move(move, player, game_board):
                    self._last_moves.append(str(move))
                    return move
            
            # Vérification des répétitions de coups
            if self._detect_repetition():
                move = self._change_strategy(player, game_board)
                if move:
                    return move
            
            # Génération des actions avec priorités
            actions = self._generate_prioritized_actions(player, game_board)
            
            if not actions:
                return self._fallback_move(player, game_board)
            
            # Sélection de la meilleure action avec alphabeta
            best_action = self._select_best_action_alphabeta(actions, player, game_board)
            
            if best_action and self._validate_move(best_action, player, game_board):
                self._last_moves.append(str(best_action))
                return best_action
            
            return self._fallback_move(player, game_board)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {str(e)}", exc_info=True)
            return self._fallback_move(player, game_board)

    def _create_game_board(self, board, walls):
        """Crée un objet GameBoard optimisé"""
        game_board = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        game_board.set_players({p.id: p for p in players})
        game_board.walls = walls
        return game_board

    def _get_book_move(self, player, game_board):
        """Mouvements prédéfinis pour l'ouverture"""
        book_moves = {
            # Premier joueur
            1: [
                {"type": "player", "direction": "up", "position": game_board.calculate_new_position(player.position, "up")},
                {"type": "wall", "x": game_board.size//2-1, "y": game_board.size//2-1, "orientation": "horizontal"}
            ],
            # Deuxième joueur
            2: [
                {"type": "wall", "x": game_board.size//2-1, "y": game_board.size//2-1, "orientation": "vertical"},
                {"type": "player", "direction": "up", "position": game_board.calculate_new_position(player.position, "up")}
            ]
        }
        
        total_moves = sum(9 - p.walls_left for p in game_board.players.values())
        player_moves = book_moves.get(self.player_id, [])
        
        if total_moves < len(player_moves):
            return player_moves[total_moves]
        return None

    def _validate_move(self, move, player, game_board):
        """Validation complète d'un mouvement"""
        if move["type"] == "wall":
            wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
            return (player.walls_left > 0 and 
                    self.is_fully_valid_wall(wall, game_board) and
                    not self._wall_exists(move["x"], move["y"]))
        else:
            return game_board.is_valid_move(player, move["direction"])

    def _wall_exists(self, x, y):
        """Vérifie si un mur existe déjà à cette position"""
        return self.game_service.db.query(
            exists().where(and_(Wall.x == x, Wall.y == y))
        ).scalar()

    def _generate_prioritized_actions(self, player, game_board):
        """Génère les actions avec une heuristique de priorité"""
        actions = []
        
        # Mouvements gagnants en premier
        winning_move = self._get_winning_move(player, game_board)
        if winning_move:
            return [winning_move]
        
        # Mouvements du joueur avec priorités
        for direction in self._get_move_priorities(player, game_board):
            new_pos = game_board.calculate_new_position(player.position, direction)
            if game_board.is_valid_move(player, direction):
                actions.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos
                })
        
        # Murs stratégiques seulement si nécessaire
        if player.walls_left > 0 and len(actions) < 3:
            walls = self._generate_high_impact_walls(game_board)
            actions.extend(walls)
        
        return actions

    def _get_move_priorities(self, player, game_board):
        """Retourne les directions prioritaires selon la position"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        current_row = player.position["x"]
        
        if current_row < target_row:
            return ["up", "right", "left", "down"]
        else:
            return ["down", "right", "left", "up"]

    def _generate_high_impact_walls(self, game_board):
        """Génère seulement les murs à fort impact"""
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)
        opponent_path = self._calculate_shortest_path(opponent, game_board)
        
        if not opponent_path or len(opponent_path) > 6:
            return []
            
        critical_positions = self._get_critical_positions(opponent_path)
        walls = []
        
        for x, y in critical_positions:
            for orientation in ["horizontal", "vertical"]:
                wall = {"x": x, "y": y, "orientation": orientation, "type": "wall"}
                if self._validate_wall_quick_check(wall, game_board):
                    walls.append(wall)
                    if len(walls) >= 3:  # Limite le nombre de murs testés
                        return walls
        return walls

    def _validate_wall_quick_check(self, wall, game_board):
        """Validation rapide d'un mur"""
        if (wall["x"], wall["y"]) in {(w.x, w.y) for w in game_board.walls}:
            return False
            
        test_wall = Wall(x=wall["x"], y=wall["y"], orientation=wall["orientation"])
        return self.is_fully_valid_wall(test_wall, game_board)

    def _get_critical_positions(self, path):
        """Retourne les positions critiques sur le chemin"""
        if len(path) < 2:
            return []
            
        critical = set()
        for i in range(1, min(4, len(path))):
            x, y = path[i]["x"], path[i]["y"]
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 9 and 0 <= ny < 9:
                    critical.add((nx, ny))
        return list(critical)

    def _select_best_action_alphabeta(self, actions, player, game_board):
        """Sélectionne la meilleure action avec alphabeta optimisé"""
        if not actions:
            return None
            
        # Trie les actions par évaluation heuristique
        scored_actions = []
        for action in actions:
            score = self._quick_evaluate(action, player, game_board)
            scored_actions.append((score, action))
        
        scored_actions.sort(reverse=True, key=lambda x: x[0])
        
        # Alphabeta sur les meilleures actions seulement
        best_action = None
        best_score = -math.inf
        depth = self._get_dynamic_depth(player, game_board)
        
        for _, action in scored_actions[:5]:  # Limite à 5 meilleures actions
            new_board = self._apply_action_fast(game_board, action, player.id)
            score = self._alphabeta(new_board, depth-1, -math.inf, math.inf, False)
            
            if score > best_score:
                best_score = score
                best_action = action
                
        return best_action or scored_actions[0][1]

    def _alphabeta(self, game_board, depth, alpha, beta, maximizing):
        """Algorithme alphabeta avec élagage et cache"""
        cache_key = self._create_cache_key(game_board, depth, maximizing)
        
        if cache_key in self._transposition_table:
            return self._transposition_table[cache_key]
            
        if depth == 0 or self._is_terminal_state(game_board):
            evaluation = self._evaluate_board(game_board)
            self._transposition_table[cache_key] = evaluation
            return evaluation
            
        current_player = game_board.players[self.player_id if maximizing else 
                                          next(pid for pid in game_board.players if pid != self.player_id)]
        
        actions = self._generate_prioritized_actions(current_player, game_board)
        
        if not actions:
            evaluation = self._evaluate_board(game_board)
            self._transposition_table[cache_key] = evaluation
            return evaluation
            
        if maximizing:
            value = -math.inf
            for action in actions:
                new_board = self._apply_action_fast(game_board, action, current_player.id)
                value = max(value, self._alphabeta(new_board, depth-1, alpha, beta, False))
                alpha = max(alpha, value)
                if alpha >= beta:
                    self._killer_moves[depth].append(action)  # Stocke les coups qui causent un élagage
                    break
            return value
        else:
            value = math.inf
            for action in actions:
                new_board = self._apply_action_fast(game_board, action, current_player.id)
                value = min(value, self._alphabeta(new_board, depth-1, alpha, beta, True))
                beta = min(beta, value)
                if alpha >= beta:
                    self._killer_moves[depth].append(action)
                    break
            return value

    def _apply_action_fast(self, game_board, action, player_id):
        """Applique une action rapidement sans deepcopy"""
        new_board = GameBoard(size=game_board.size)
        
        # Copie légère des joueurs
        new_players = {}
        for pid, p in game_board.players.items():
            new_p = Player(
                id=p.id,
                position=dict(p.position),
                direction=p.direction,
                walls_left=p.walls_left
            )
            if pid == player_id and action["type"] == "player":
                new_p.position = action["position"]
            new_players[pid] = new_p
        
        new_board.set_players(new_players)
        
        # Copie des murs + nouveau mur si applicable
        new_board.walls = list(game_board.walls)
        if action["type"] == "wall":
            new_board.walls.append(Wall(
                x=action["x"],
                y=action["y"],
                orientation=action["orientation"]
            ))
            
        return new_board

    def _get_dynamic_depth(self, player, game_board):
        """Détermine la profondeur de recherche dynamique"""
        remaining_walls = sum(p.walls_left for p in game_board.players.values())
        
        if remaining_walls > 12:  # Début de partie
            return 2
        elif remaining_walls > 6:  # Milieu de partie
            return 3
        else:  # Fin de partie
            return 4

    def _quick_evaluate(self, action, player, game_board):
        """Évaluation rapide d'une action"""
        if action["type"] == "player":
            new_pos = action["position"]
            target_row = 0 if player.direction == Direction.UP else game_board.size - 1
            distance = abs(new_pos["x"] - target_row)
            return -distance * 2  # Plus c'est proche, mieux c'est
            
        else:  # Mur
            wall = Wall(x=action["x"], y=action["y"], orientation=action["orientation"])
            opponent = next(p for p in game_board.players.values() if p.id != self.player_id)
            
            # Test rapide de l'impact sur l'opposant
            test_board = self._apply_action_fast(game_board, action, player.id)
            opponent_path = self._calculate_shortest_path(opponent, test_board)
            
            if not opponent_path:
                return 100  # Blocage complet
                
            return (len(opponent_path) - len(self._calculate_shortest_path(opponent, game_board))) * 3

    def _evaluate_board(self, game_board):
        """Évaluation complète du plateau avec score numérique"""
        player = game_board.players[self.player_id]
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)
        
        # Calcul des distances
        def get_path_length(path):
            return len(path) if path else 100  # Pénalité si pas de chemin
        
        player_dist = get_path_length(self._calculate_shortest_path(player, game_board))
        opponent_dist = get_path_length(self._calculate_shortest_path(opponent, game_board))
        
        # Composantes du score
        distance_score = (opponent_dist - player_dist) * 2.0  # Priorité à réduire sa distance
        walls_score = (player.walls_left - opponent.walls_left) * 0.8  # Avantage des murs restants
        mobility_score = (self._calculate_mobility(player, game_board) - 
                        self._calculate_mobility(opponent, game_board)) * 0.2
        
        # Score total pondéré
        total_score = distance_score + walls_score + mobility_score
        
        # Assurance que le score est numérique
        if not isinstance(total_score, (int, float)):
            logger.warning(f"Invalid score type: {type(total_score)}")
            return 0
        
        return total_score
    def _calculate_mobility(self, player, game_board):
        """Calcule la mobilité du joueur"""
        return sum(
            1 for direction in ["up", "down", "left", "right"] 
            if game_board.is_valid_move(player, direction)
        )

    def _is_terminal_state(self, game_board):
        """Vérifie si l'état est terminal (joueur a gagné)"""
        player = game_board.players[self.player_id]
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        return player.position["x"] == target_row

    def _get_winning_move(self, player, game_board):
        """Vérifie s'il existe un mouvement gagnant immédiat"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        return None

    def _detect_repetition(self):
        """Détecte les répétitions de coups"""
        if len(self._last_moves) < 3:
            return False
            
        last_move = self._last_moves[-1]
        return (self._last_moves.count(last_move) >= 2 or 
                (len(self._last_moves) >= 4 and 
                 self._last_moves[-1] == self._last_moves[-3] and 
                 self._last_moves[-2] == self._last_moves[-4]))

    def _change_strategy(self, player, game_board):
        """Change de stratégie en cas de répétition"""
        # Essaye les killer moves d'abord
        for depth in sorted(self._killer_moves.keys(), reverse=True):
            for move in self._killer_moves[depth]:
                if self._validate_move(move, player, game_board):
                    return move
        
        # Fallback aléatoire mais valide
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                move = {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
                if str(move) not in self._last_moves:
                    return move
        
        return self._fallback_move(player, game_board)

    def _fallback_move(self, player, game_board):
        """Dernier recours - mouvement sûr"""
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                return {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
        return {"type": "player", "direction": "up", "position": player.position}

    def _is_endgame(self, player, game_board):
        """Détecte la fin de partie"""
        path = self._calculate_shortest_path(player, game_board)
        return path and len(path) <= 3

    def _make_endgame_move(self, player, game_board):
        """Stratégie optimisée pour la fin de partie"""
        winning_move = self._get_winning_move(player, game_board)
        if winning_move:
            return winning_move
            
        # Trouve le chemin le plus court
        path = self._calculate_shortest_path(player, game_board)
        if not path or len(path) < 2:
            return None
            
        # Essaye de se déplacer vers la prochaine position du chemin optimal
        next_pos = path[1]
        current_pos = player.position
        
        if next_pos["x"] > current_pos["x"] and game_board.is_valid_move(player, "down"):
            return {"type": "player", "direction": "down", "position": next_pos}
        elif next_pos["x"] < current_pos["x"] and game_board.is_valid_move(player, "up"):
            return {"type": "player", "direction": "up", "position": next_pos}
        elif next_pos["y"] > current_pos["y"] and game_board.is_valid_move(player, "right"):
            return {"type": "player", "direction": "right", "position": next_pos}
        elif next_pos["y"] < current_pos["y"] and game_board.is_valid_move(player, "left"):
            return {"type": "player", "direction": "left", "position": next_pos}
            
        return None

    def _create_cache_key(self, game_board, depth, maximizing):
        """Crée une clé de cache efficace"""
        players_key = tuple(
            (pid, p.position["x"], p.position["y"], p.walls_left)
            for pid, p in sorted(game_board.players.items())
        )  # Parenthèse fermante ajoutée ici
        
        walls_key = frozenset(
            (w.x, w.y, w.orientation)
            for w in game_board.walls
        )
        return (players_key, walls_key, depth, maximizing)

    def is_fully_valid_wall(self, wall, game_board):
        """Validation complète d'un mur avec optimisation"""
        # Validation de base
        if not game_board._is_valid_wall(wall):
            return False
            
        # Vérification des croisements
        for existing_wall in game_board.walls:
            if wall.intersects(existing_wall):
                return False
                
        # Vérification des chemins
        test_board = GameBoard(size=game_board.size)
        test_board.set_players({pid: Player(
            id=p.id,
            position=dict(p.position),
            direction=p.direction,
            walls_left=p.walls_left
        ) for pid, p in game_board.players.items()})
        
        test_board.walls = list(game_board.walls) + [wall]
        
        return all(test_board.has_path(p) for p in test_board.players.values())

'''

'''class GameBoard:
    """Classe simplifiée pour la simulation"""
    def __init__(self, size=9):
        self.size = size
        self.players = {}
        self.walls = []
    
    def set_players(self, players):
        self.players = players
    
    def is_valid_move(self, player, direction):
        """Vérifie si un mouvement est valide"""
        new_pos = self.calculate_new_position(player.position, direction)
        if not (0 <= new_pos["x"] < self.size and 0 <= new_pos["y"] < self.size):
            return False
        
        current_pos = player.position
        if self.is_blocked(current_pos["x"], current_pos["y"], new_pos["x"], new_pos["y"]):
            return False
            
        return True
    
    def calculate_new_position(self, position, direction):
        """Calcule la nouvelle position"""
        moves = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1)
        }
        dx, dy = moves[direction]
        return {"x": position["x"] + dx, "y": position["y"] + dy}
    
    def is_blocked(self, x1, y1, x2, y2):
        """Vérifie si un mur bloque le mouvement"""
        for wall in self.walls:
            if wall.orientation == "horizontal":
                if y1 == y2 and (wall.y == y1 or wall.y == y1 - 1) and x2 == wall.x:
                    return True
            else:
                if x1 == x2 and (wall.x == x1 or wall.x == x1 - 1) and y2 == wall.y:
                    return True
        return False
    
    def has_path(self, player):
        """Vérifie si le joueur a un chemin vers sa ligne de but"""
        from collections import deque
        
        start = player.position
        target_row = 0 if player.direction == Direction.UP else self.size - 1
        visited = set()
        queue = deque([(start["x"], start["y"])])
        
        while queue:
            x, y = queue.popleft()
            
            if x == target_row:
                return True
                
            if (x, y) in visited:
                continue
                
            visited.add((x, y))
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    if not self.is_blocked(x, y, nx, ny):
                        queue.append((nx, ny))
        
        return False '''

import math
import random
from collections import deque, defaultdict
from copy import deepcopy
import logging
from sqlalchemy import exists, and_

logger = logging.getLogger(__name__)

class AdvancedAI33333(PathfindingMixin, WallValidationMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self._cache = {}
        self._last_moves = deque(maxlen=5)
        self._transposition_table = {}
        self._killer_moves = defaultdict(list)
        self._wall_aggressiveness = 0.9  # Très agressif (0-1)
        self._opening_book = self._init_opening_book()
        
    def choose_move(self):
        try:
            board, state, walls = self.game_service.get_board_and_state()
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(board, walls)
            
            # 1. Vérifier les mouvements gagnants immédiats
            winning_move = self._get_winning_move(player, game_board)
            if winning_move:
                return winning_move
                
            # 2. Utiliser les coups d'ouverture prédéfinis
            if self._is_opening_move():
                book_move = self._get_book_move(player, game_board)
                if book_move and self._validate_move(book_move, player, game_board):
                    self._last_moves.append(str(book_move))
                    return book_move
            
            # 3. Stratégie offensive: bloquer l'adversaire
            if player.walls_left > 0 and self._should_place_wall(player, game_board):
                blocking_wall = self._find_best_blocking_wall(player, game_board)
                if blocking_wall and self._validate_move(blocking_wall, player, game_board):
                    self._last_moves.append(str(blocking_wall))
                    return blocking_wall
            
            # 4. Avancer vers l'objectif avec chemin optimal
            best_move = self._get_best_progressive_move(player, game_board)
            if best_move and self._validate_move(best_move, player, game_board):
                self._last_moves.append(str(best_move))
                return best_move
            
            # 5. Fallback: mouvement valide quelconque
            return self._fallback_move(player, game_board)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {str(e)}", exc_info=True)
            return self._fallback_move(player, game_board)

    def _init_opening_book(self):
        """Coups d'ouverture prédéfinis pour chaque position"""
        return {
            1: [  # Premier joueur
                {"type": "player", "direction": "up", "position": {"x": 0, "y": 4}},
                {"type": "wall", "x": 4, "y": 4, "orientation": "horizontal"},
                {"type": "wall", "x": 5, "y": 3, "orientation": "vertical"}
            ],
            2: [  # Deuxième joueur
                {"type": "wall", "x": 4, "y": 4, "orientation": "vertical"},
                {"type": "player", "direction": "up", "position": {"x": 8, "y": 4}},
                {"type": "wall", "x": 3, "y": 5, "orientation": "horizontal"}
            ]
        }

    def _create_game_board(self, board, walls):
        """Crée un objet GameBoard optimisé"""
        game_board = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        game_board.set_players({p.id: p for p in players})
        game_board.walls = walls
        return game_board

    def _get_book_move(self, player, game_board):
        """Récupère le coup d'ouverture approprié"""
        total_moves = sum(9 - p.walls_left for p in game_board.players.values())
        player_moves = self._opening_book.get(self.player_id, [])
        return player_moves[total_moves] if total_moves < len(player_moves) else None

    def _find_best_blocking_wall(self, player, game_board):
        """Trouve le mur le plus gênant pour l'adversaire"""
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)
        opponent_path = self._calculate_shortest_path(opponent, game_board)
        
        if not opponent_path or len(opponent_path) > 8:
            return None
            
        # Classer les positions par criticité
        critical_positions = sorted(
            self._get_critical_positions(opponent_path),
            key=lambda p: self._position_criticality(p, opponent_path),
            reverse=True
        )
        
        # Essayer les 5 positions les plus critiques
        for x, y in critical_positions[:5]:
            for orientation in ["horizontal", "vertical"]:
                wall = {"x": x, "y": y, "orientation": orientation, "type": "wall"}
                if self._validate_wall_quick_check(wall, game_board):
                    test_board = self._apply_action_fast(game_board, wall, player.id)
                    new_path = self._calculate_shortest_path(opponent, test_board)
                    
                    # Si le mur bloque complètement ou rallonge significativement le chemin
                    if not new_path or len(new_path) > len(opponent_path) + 3:
                        return wall
        return None

    def _position_criticality(self, pos, path):
        """Évalue à quel point une position est critique sur le chemin"""
        x, y = pos
        criticality = 0
        
        # Plus c'est proche du joueur adverse, plus c'est critique
        for i, p in enumerate(path):
            dist = abs(p["x"] - x) + abs(p["y"] - y)
            criticality += 1 / (dist + 1) * (len(path) - i)
            
        return criticality

    def _should_place_wall(self, player, game_board):
        """Détermine si on doit placer un mur"""
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)
        
        # Calcul des distances
        my_path = self._calculate_shortest_path(player, game_board)
        opp_path = self._calculate_shortest_path(opponent, game_board)
        
        my_dist = len(my_path) if my_path else 100
        opp_dist = len(opp_path) if opp_path else 100
        
        # Plus l'adversaire est proche du but, plus on place de murs
        wall_chance = self._wall_aggressiveness * (1 - opp_dist/20)
        
        # Ajuster selon le nombre de murs restants et l'avance
        wall_chance *= min(1, player.walls_left / 5) * (1 + (my_dist - opp_dist)/10)
        
        return random.random() < wall_chance

    def _get_best_progressive_move(self, player, game_board):
        """Trouve le meilleur mouvement progressif vers l'objectif"""
        path = self._calculate_shortest_path(player, game_board)
        if not path or len(path) < 2:
            return None
            
        # Essayer le chemin direct
        next_pos = path[1]
        move = self._create_move_to_position(player, game_board, next_pos)
        if move:
            return move
            
        # Si bloqué, essayer des mouvements latéraux
        for direction in ["left", "right", "up", "down"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                new_path = self._calculate_shortest_path(
                    Player(id=player.id, position=new_pos, direction=player.direction), 
                    game_board
                )
                if new_path and len(new_path) <= len(path):
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        return None

    def _create_move_to_position(self, player, game_board, target_pos):
        """Crée un mouvement vers une position cible"""
        current_pos = player.position
        dx = target_pos["x"] - current_pos["x"]
        dy = target_pos["y"] - current_pos["y"]
        
        if dx > 0 and game_board.is_valid_move(player, "down"):
            return {"type": "player", "direction": "down", "position": target_pos}
        elif dx < 0 and game_board.is_valid_move(player, "up"):
            return {"type": "player", "direction": "up", "position": target_pos}
        elif dy > 0 and game_board.is_valid_move(player, "right"):
            return {"type": "player", "direction": "right", "position": target_pos}
        elif dy < 0 and game_board.is_valid_move(player, "left"):
            return {"type": "player", "direction": "left", "position": target_pos}
        return None

    def _get_critical_positions(self, path):
        """Trouve toutes les positions critiques près du chemin"""
        critical = set()
        for i, pos in enumerate(path):
            # Prendre 3 positions clés sur le chemin
            if i % max(1, len(path)//3) == 0 or i == len(path)-1:
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        x, y = pos["x"] + dx, pos["y"] + dy
                        if 0 <= x < 9 and 0 <= y < 9:
                            critical.add((x, y))
        return critical

    def _validate_wall_quick_check(self, wall, game_board):
        """Validation rapide d'un mur"""
        if (wall["x"], wall["y"]) in {(w.x, w.y) for w in game_board.walls}:
            return False
            
        test_wall = Wall(x=wall["x"], y=wall["y"], orientation=wall["orientation"])
        return self.is_fully_valid_wall(test_wall, game_board)

    def _apply_action_fast(self, game_board, action, player_id):
        """Applique une action rapidement sans deepcopy"""
        new_board = GameBoard(size=game_board.size)
        
        # Copie légère des joueurs
        new_players = {}
        for pid, p in game_board.players.items():
            new_p = Player(
                id=p.id,
                position=dict(p.position),
                direction=p.direction,
                walls_left=p.walls_left
            )
            if pid == player_id and action["type"] == "player":
                new_p.position = action["position"]
            new_players[pid] = new_p
        
        new_board.set_players(new_players)
        
        # Copie des murs + nouveau mur si applicable
        new_board.walls = list(game_board.walls)
        if action["type"] == "wall":
            new_board.walls.append(Wall(
                x=action["x"],
                y=action["y"],
                orientation=action["orientation"]
            ))
            
        return new_board

    def _get_winning_move(self, player, game_board):
        """Vérifie s'il existe un mouvement gagnant immédiat"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        return None

    def _is_opening_move(self):
        """Détermine si c'est le début de partie"""
        players = self.game_service.db.query(Player).all()
        return sum(9 - p.walls_left for p in players) < 4

    def _fallback_move(self, player, game_board):
        """Dernier recours - mouvement sûr"""
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                return {
                    "type": "player",
                    "direction": direction,
                    "position": new_pos
                }
        return {"type": "player", "direction": "up", "position": player.position}

    def _validate_move(self, move, player, game_board):
        """Validation complète d'un mouvement"""
        if move["type"] == "wall":
            wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
            return (player.walls_left > 0 and 
                    self.is_fully_valid_wall(wall, game_board) and
                    not self._wall_exists(move["x"], move["y"]))
        else:
            return game_board.is_valid_move(player, move["direction"])

    def _wall_exists(self, x, y):
        """Vérifie si un mur existe déjà à cette position"""
        return self.game_service.db.query(
            exists().where(and_(Wall.x == x, Wall.y == y))
        ).scalar()

    def is_fully_valid_wall(self, wall, game_board):
        """Validation complète d'un mur avec optimisation"""
        if not game_board._is_valid_wall(wall):
            return False
            
        for existing_wall in game_board.walls:
            if wall.intersects(existing_wall):
                return False
                
        test_board = GameBoard(size=game_board.size)
        test_board.set_players({pid: Player(
            id=p.id,
            position=dict(p.position),
            direction=p.direction,
            walls_left=p.walls_left
        ) for pid, p in game_board.players.items()})
        
        test_board.walls = list(game_board.walls) + [wall]
        return all(test_board.has_path(p) for p in test_board.players.values())

    
    





    
class AdvancedAI538(PathfindingMixin,WallValidationMixin ):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self._cache = {}
        self._last_moves = deque(maxlen=5)
        
    def choose_move(self):
        print("⚠️ CHOOSE_MOVE ACTIVE pour player", self.player_id)

        try:
            board, state, walls = self.game_service.get_board_and_state()
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(board, walls)
            
            # Gestion des ouvertures
            if self._is_opening_move():
                move = self._make_opening_move(player, game_board)
                if move:
                    if move["type"] == "wall":
                        wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
                        if not self.is_fully_valid_wall(wall, game_board):
                            move = None
                    if move:
                        self._last_moves.append(str(move))
                        return move
            
            # Gestion de la fin de partie
            if self._is_endgame(player, game_board):
                move = self._make_endgame_move(player, game_board)
                if move:
                    if move["type"] == "wall":
                        wall = Wall(x=move["x"], y=move["y"], orientation=move["orientation"])
                        if not self.is_fully_valid_wall(wall, game_board):
                            move = None
                    if move:
                        self._last_moves.append(str(move))
                        return move

            # Génération des actions possibles
            actions = self._generate_all_actions(player, game_board)
            
            if not actions:
                raise ValueError("No valid actions available")
            
            # Sélection de la meilleure action
            best_action = self._select_best_action(actions, player, game_board)
            
            if best_action:
                if best_action["type"] == "wall":
                    wall_pos = (best_action["x"], best_action["y"])
                    existing_positions = {(w.x, w.y) for w in game_board.walls}
                    if wall_pos in existing_positions:
                        return self._change_strategy(player, game_board)
                
                self._last_moves.append(str(best_action))
                return best_action
            
            return self._fallback_move(player, game_board)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {str(e)}")
            player = self.game_service.get_player(self.player_id)
            game_board = self._create_game_board(*self.game_service.get_board_and_state()[:2])
            return self._fallback_move(player, game_board)

    def _generate_all_actions(self, player, game_board):
        """Génère toutes les actions possibles avec priorités sur l'avancée vers la victoire"""
        actions = []
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Mouvements prioritaires (vers la ligne d'arrivée)
        preferred_directions = ["up"] if player.direction == Direction.UP else ["down"]
        secondary_directions = ["left", "right"]
        
        # D'abord vérifier les directions prioritaires
        for direction in preferred_directions + secondary_directions:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                actions.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos,
                    "priority": 1 if direction in preferred_directions else 0
                })

        # Murs (seulement si le joueur en a)
        if player.walls_left > 0:
            wall_candidates = self._generate_strategic_walls(game_board)
            for wall_action in wall_candidates:
                wall = Wall(x=wall_action["x"], y=wall_action["y"], orientation=wall_action["orientation"])
                if self.is_fully_valid_wall(wall, game_board):
                    actions.append(wall_action)

        return actions

    def _select_best_action(self, actions, player, game_board):
        """Sélectionne la meilleure action en priorisant l'avancée vers la victoire"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # D'abord vérifier les mouvements gagnants directs
        for action in actions:
            if action["type"] == "player" and action["position"]["x"] == target_row:
                return action
        
        # Ensuite prioriser les mouvements qui avancent
        advancing_actions = []
        for action in actions:
            if action["type"] == "player":
                current_dist = abs(player.position["x"] - target_row)
                new_dist = abs(action["position"]["x"] - target_row)
                if new_dist < current_dist:
                    advancing_actions.append(action)
        
        if advancing_actions:
            return advancing_actions[0]  # Prend le premier mouvement qui fait avancer
        
        # Fallback: retourne la première action valide
        return actions[0] if actions else self._fallback_move(player, game_board)

    def _make_opening_move(self, player, game_board):
        """Stratégie d'ouverture simplifiée"""
        # Toujours avancer vers le haut pour le joueur 1, vers le bas pour le joueur 2
        direction = "up" if player.direction == Direction.UP else "down"
        if game_board.is_valid_move(player, direction):
            return {
                "type": "player",
                "direction": direction,
                "position": game_board.calculate_new_position(player.position, direction)
            }
        return None

    def _make_endgame_move(self, player, game_board):
        """Stratégie de fin de partie optimisée"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Vérifie d'abord les mouvements gagnants directs
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        # Sinon choisit le mouvement qui rapproche le plus
        best_move = None
        min_distance = float('inf')
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                distance = abs(new_pos["x"] - target_row)
                if distance < min_distance:
                    min_distance = distance
                    best_move = {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        return best_move if best_move else self._fallback_move(player, game_board)
    def _create_game_board(self, board, walls):
        """Crée un objet GameBoard à partir des données du jeu"""
        game_board = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        game_board.set_players({p.id: p for p in players})
        game_board.walls = walls
        return game_board

    
    def _generate_strategic_walls(self, game_board):
        """Génère les murs stratégiques avec validation renforcée"""
        print("je suis APPPPLLLLLEEEEE")
        possible_walls = []
        hot_spots = self._find_hot_spots(game_board)
        existing_walls = {(w.x, w.y, w.orientation) for w in game_board.walls}
        existing_wall_positions = {(w.x, w.y) for w in game_board.walls}  # Positions occupées
        
        for (x, y) in hot_spots:
            # Skip si position déjà occupée (quelque soit l'orientation)
            if (x, y) in existing_wall_positions:
                continue
                
            for orientation in ["horizontal", "vertical"]:
                wall = Wall(x=x, y=y, orientation=orientation)
                
                # Validation complète du mur
                if not self.is_fully_valid_wall(wall, game_board):
                    continue

                    
                # Vérification des chemins
                test_board = deepcopy(game_board)
                test_board.walls.append(wall)
                
                if all(test_board.has_path(p) for p in test_board.players.values()):
                    possible_walls.append({
                        "x": x,
                        "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
        
        return possible_walls
    

    def _find_hot_spots(self, game_board):
        """Trouve les positions stratégiques pour les murs"""
        hot_spots = set()
        
        for player in game_board.players.values():
            if player.id == self.player_id:
                continue
                
            path = self._calculate_shortest_path(player, game_board)
            if path:
                for i in range(1, min(4, len(path))):
                    pos = path[i]
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            x, y = pos["x"] + dx, pos["y"] + dy
                            if 0 <= x < game_board.size - 1 and 0 <= y < game_board.size - 1:
                                hot_spots.add((x, y))
        
        return list(hot_spots)

    def _calculate_shortest_path(self, player, game_board):
        """Calcule le chemin le plus court pour un joueur"""
        from collections import deque
        
        start = player.position
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        visited = set()
        queue = deque([(start["x"], start["y"], [])])
        
        while queue:
            x, y, path = queue.popleft()
            
            if y == target_row:
                return path + [{"x": x, "y": y}]
            
            if (x, y) in visited:
                continue
                
            visited.add((x, y))
            
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < game_board.size and 0 <= ny < game_board.size:
                    if not game_board.is_blocked(x, y, nx, ny):
                        queue.append((nx, ny, path + [{"x": x, "y": y}]))
        
        return None

    def _minimax(self, game_board, depth, maximizing, alpha, beta):
        """Algorithme Minimax optimisé"""
        cache_key = self._create_cache_key(game_board, depth, maximizing)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        current_player = game_board.players[self.player_id]
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)

        if depth == 0 or self._is_winning_state(current_player, opponent, game_board):
            evaluation = self._evaluate_state(current_player, opponent, game_board)
            self._cache[cache_key] = evaluation
            return evaluation

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, game_board)

        if not actions:
            evaluation = self._evaluate_state(current_player, opponent, game_board)
            self._cache[cache_key] = evaluation
            return evaluation

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_game_board = self._apply_action(game_board, action, active_player.id)
                eval = self._minimax(new_game_board, depth-1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            self._cache[cache_key] = max_eval
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                new_game_board = self._apply_action(game_board, action, active_player.id)
                eval = self._minimax(new_game_board, depth-1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            self._cache[cache_key] = min_eval
            return min_eval

    def _apply_action(self, game_board, action, player_id):
        """Applique une action sur une copie du plateau"""
        new_game_board = deepcopy(game_board)
        new_players = deepcopy(new_game_board.players)
        
        if action["type"] == "player":
            player = new_players[player_id]
            player.position = action["position"]
        else:
            new_game_board.walls.append(Wall(
                x=action["x"],
                y=action["y"],
                orientation=action["orientation"]
            ))
        
        new_game_board.set_players(new_players)
        return new_game_board

    def _create_cache_key(self, game_board, depth, maximizing):
        """Crée une clé de cache unique"""
        players_key = tuple(
            (pid, p.position["x"], p.position["y"], p.walls_left)
            for pid, p in sorted(game_board.players.items())
        )
        walls_key = tuple(
            (w.x, w.y, w.orientation)
            for w in sorted(game_board.walls, key=lambda x: (x.x, x.y, x.orientation))
        )
        return (players_key, walls_key, depth, maximizing)

    def _is_opening_move(self):
        """Détermine si c'est le début de la partie"""
        players = self.game_service.db.query(Player).all()
        total_walls_placed = sum(9 - p.walls_left for p in players)
        return total_walls_placed < 2

    

    def _is_endgame(self, player, game_board):
        """Détecte la fin de partie"""
        path = self._calculate_shortest_path(player, game_board)
        return path and len(path) <= 3

    

    def _change_strategy(self, player, game_board):
        """Change de stratégie quand des répétitions sont détectées"""
        # Essaye d'abord de bouger le pion
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                move = {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
                self._last_moves.append(str(move))
                return move
        
        # Si aucun mouvement n'est possible, trouve un mur différent
        existing_walls = {(w.x, w.y, w.orientation) for w in game_board.walls}
        for x in range(game_board.size - 1):
            for y in range(game_board.size - 1):
                for orientation in ["horizontal", "vertical"]:
                    if (x, y, orientation) not in existing_walls:
                        try:
                            test_wall = Wall(x=x, y=y, orientation=orientation)
                            test_board = deepcopy(game_board)
                            test_board.walls.append(test_wall)
                            if all(test_board.has_path(p) for p in test_board.players.values()):
                                move = {
                                    "type": "wall",
                                    "x": x,
                                    "y": y,
                                    "orientation": orientation
                                }
                                self._last_moves.append(str(move))
                                return move
                        except:
                            continue
        return self._fallback_move(player, game_board)

    def _fallback_move(self, player, game_board):
        """Dernier recours quand tout échoue"""
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                return {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
        return {"type": "player", "direction": "up", "position": player.position}

    def _determine_search_depth(self, player):
        """Détermine la profondeur de recherche adaptative"""
        if player.walls_left < 3:  # Fin de partie
            return 4
        players = self.game_service.db.query(Player).all()
        if len(players) == 2 and sum(p.walls_left for p in players) < 10:
            return 3
        return 2

    def _is_winning_state(self, player, opponent, game_board):
        """Vérifie si un joueur a gagné"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        return player.position["x"] == target_row

    def _evaluate_state(self, player, opponent, game_board):
        """Évaluation complète de l'état du jeu"""
        # Calcul des chemins les plus courts
        my_path = self._calculate_shortest_path(player, game_board)
        opp_path = self._calculate_shortest_path(opponent, game_board)
        
        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")
        
        # Facteurs d'évaluation
        distance_diff = (opp_dist - my_dist) * 2.0
        walls_diff = (player.walls_left - opponent.walls_left) * 0.5
        center_bonus = self._calculate_center_bonus(player.position, game_board.size) * 0.3
        blocking = self._calculate_blocking_potential(opponent, game_board) * 1.5
        mobility = self._calculate_mobility(player, game_board) * 0.2
        
        return distance_diff + walls_diff + center_bonus + blocking + mobility

    def _calculate_center_bonus(self, position, board_size):
        """Bonus pour être près du centre"""
        center = board_size // 2
        dist_to_center = abs(position["x"] - center) + abs(position["y"] - center)
        return -dist_to_center * 0.1

    def _calculate_blocking_potential(self, opponent, game_board):
        """Évalue le potentiel de blocage"""
        score = 0
        path = self._calculate_shortest_path(opponent, game_board)
        
        if path and len(path) > 1:
            current_pos = opponent.position
            next_pos = path[1]
            if self._can_block_move(current_pos, next_pos, game_board):
                score += 2
        
        return score

    def _can_block_move(self, current_pos, next_pos, game_board):
        """Vérifie si un mur peut bloquer ce mouvement"""
        dx = next_pos["x"] - current_pos["x"]
        dy = next_pos["y"] - current_pos["y"]
        
        if dx > 0:  # Vers le bas
            wall_x, wall_y = current_pos["x"], min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dx < 0:  # Vers le haut
            wall_x, wall_y = current_pos["x"]-1, min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dy > 0:  # Vers la droite
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]
            orientation = "horizontal"
        else:  # Vers la gauche
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]-1
            orientation = "horizontal"
        
        try:
            test_wall = Wall(x=wall_x, y=wall_y, orientation=orientation)
            test_board = deepcopy(game_board)
            test_board.walls.append(test_wall)
            return all(test_board.has_path(p) for p in test_board.players.values())
        except:
            return False

    def _calculate_mobility(self, player, game_board):
        """Calcule la mobilité du joueur"""
        return sum(
            1 for direction in ["up", "down", "left", "right"] 
            if game_board.is_valid_move(player, direction)
        )

    def apply_move_to_db(self, move):
        if move["type"] == "wall":
            with self.game_service.db.begin() as transaction:
                # Vérification atomique
                exists = self.game_service.db.query(
                    exists().where(
                        and_(
                            Wall.x == move["x"],
                            Wall.y == move["y"]
                        )
                    )
                ).scalar()
                
                if exists:
                    logger.warning(f"Wall position {move['x']},{move['y']} already occupied")
                    transaction.rollback()
                    return False
                    
                wall = Wall(
                    x=move["x"],
                    y=move["y"],
                    orientation=move["orientation"].upper(),
                    player_id=self.player_id
                )
                self.game_service.db.add(wall)
                logger.info(f"Wall successfully placed at {wall.x},{wall.y}")
            return True
        return False
    def _generate_wall_candidates(self, game_board):
        """Génère des candidats murs avec vérification des croisements"""
        candidates = []
        hot_spots = self._find_hot_spots(game_board)
        existing_walls = {(w.x, w.y): w.orientation for w in game_board.walls}
        
        for x, y in hot_spots:
            # Ne pas proposer de mur là où il y a déjà un mur (quelque soit l'orientation)
            if (x, y) not in existing_walls:
                for orientation in ["horizontal", "vertical"]:
                    candidates.append({
                        "x": x,
                        "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
        
        return candidates
    
    def is_fully_valid_wall(self, wall, game_board):
        # Validation logique de base
        if not game_board._is_valid_wall(wall):
            return False
        
        # Validation des chemins (aucun joueur ne doit être bloqué)
        # On clone le plateau pour tester l'ajout du mur
        test_board = GameBoard(size=game_board.size)
        
        # Copie des joueurs
        new_players = {
            pid: Player(
                id=p.id,
                position=dict(p.position),
                direction=p.direction,
                walls_left=p.walls_left
            ) for pid, p in game_board.players.items()
        }
        test_board.set_players(new_players)
        
        # Copie des murs + ajout du nouveau
        test_board.walls = [Wall(x=w.x, y=w.y, orientation=w.orientation, player_id=w.player_id) for w in game_board.walls] + [wall]
        
        # Vérifie qu'il y a un chemin pour chaque joueur
        return all(test_board.has_path(p) for p in test_board.players.values())





class AdvancedAIenattaente(WallValidationMixin, PathfindingMixin):
    """AI sử dụng minimax với alpha-beta pruning"""
    
    def __init__(self, game_service, player_id):
        self.game = game_service
        self.player_id = player_id 
        self.opponent_id = 1 if player_id == 2 else 2
        self.wall_impact_weight = 0.7 
        self.path_priority_weight = 0.4  # Poids de la priorité de chemin

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
        """Fonction d'évaluation améliorée"""

        board, state, walls = self.game.get_board_and_state()
        player = players[self.player_id]
        opponent = players[self.opponent_id]


        # 1. Calcul des distances de base
        player_dist = self.calculate_shortest_path(player, board, walls)
        opponent_dist = self.calculate_shortest_path(opponent, board, walls)

        player_score = len(player_dist) if player_dist else 100
        opponent_score = len(opponent_dist) if opponent_dist else 100

        # 2. Bonus/Pénalité pour les murs restants
        wall_bonus = players[self.player_id].walls_left * 0.5
        wall_penalty = players[self.opponent_id].walls_left * 0.3

        # 3. Impact stratégique des murs existants (nouveau)
        blocking_score = self.calculate_wall_impact(players, walls)

        # 4. Priorité de progression (nouveau)
        progression_bonus = self.calculate_progression_bonus(player, player_dist)

        return (opponent_score - player_score) + wall_bonus - wall_penalty + blocking_score + progression_bonus

    def calculate_wall_impact(self, players, walls):
        """Calcule l'impact des murs placés sur le chemin adverse"""
        opponent = players[self.opponent_id]
        total_impact = 0

        for wall in walls:
            if wall.player_id == self.player_id:  # Seulement nos murs
                # Simule le plateau SANS ce mur
                temp_walls = [w for w in walls if w != wall]
                original_path = self.calculate_shortest_path(opponent, self.game_board, temp_walls)
                current_path = self.calculate_shortest_path(opponent, self.game_board, walls)
                
                if original_path and current_path:
                    impact = len(current_path) - len(original_path)
                    # Pondère par la proximité du mur avec l'adversaire
                    distance_to_opponent = abs(wall.x - opponent.position["x"]) + abs(wall.y - opponent.position["y"])
                    proximity_factor = max(0, 1 - distance_to_opponent/10)
                    total_impact += impact * self.wall_impact_weight * proximity_factor

        return total_impact

    def calculate_progression_bonus(self, player, player_dist):
        """Récompense la progression vers l'objectif"""
        if not player_dist:
            return 0
            
        # Bonus si le prochain mouvement rapproche du but
        direction = player.direction
        next_pos = player_dist[0] if player_dist else player.position
        
        if direction == Direction.UP:
            progression = player.position["x"] - next_pos[0]
        else:
            progression = next_pos[0] - player.position["x"]
            
        return progression * self.path_priority_weight

    def get_valid_moves(self, players, walls, player_id):
        """Priorise les mouvements stratégiques"""
        moves = self.get_valid_moves1(players, walls, player_id)
        
        # Trie les murs par potentiel de blocage
        opponent = players[3 - player_id]
        target_row = 0 if opponent.direction == Direction.UP else 8
        
        wall_moves = []
        player_moves = []
        
        for move in moves:
            if move["type"] == "wall":
                # Score de priorité basé sur la position
                y_distance = abs(move["y"] - target_row)
                x_center_distance = abs(move["x"] - 4)  # Centre du plateau
                priority = (10 - y_distance) + (4 - x_center_distance)
                wall_moves.append((priority, move))
            else:
                player_moves.append(move)
        
        # Trie les murs par priorité décroissante
        wall_moves.sort(reverse=True, key=lambda x: x[0])
        sorted_moves = [move for (_, move) in wall_moves] + player_moves
        
        return sorted_moves[:50]  # Limite à 50 meilleurs coups pour la performance

    def get_valid_moves1(self, players, walls, player_id):
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




class AdvancedAILast(PathfindingMixin, WallValidationMixin):
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self._cache = {}
        self._last_moves = deque(maxlen=5)
        
    def choose_move(self):
        try:
            board, state, walls = self.game_service.get_board_and_state()
            player = self.game_service.get_player(self.player_id)
            opponent = self._get_opponent(player, board)
            game_board = self._create_game_board(board, walls)
            
            # Gestion des ouvertures
            if self._is_opening_move():
                move = self._make_opening_move(player, game_board)
                if move and self._validate_move(move, game_board):
                    return move
            
            # Gestion de la fin de partie
            if self._is_endgame(player, game_board):
                move = self._make_endgame_move(player, opponent, game_board)
                if move and self._validate_move(move, game_board):
                    return move

            # Stratégie normale
            move = self._make_strategic_move(player, opponent, game_board)
            if move:
                return move
            
            return self._fallback_move(player, game_board)
                
        except Exception as e:
            logger.error(f"Error in choose_move: {str(e)}")
            return self._fallback_move(
                self.game_service.get_player(self.player_id),
                self._create_game_board(*self.game_service.get_board_and_state()[:2])
            )

    def _make_strategic_move(self, player, opponent, game_board):
        """Décide du meilleur mouvement stratégique"""
        # 1. Vérifier si on peut gagner immédiatement
        winning_move = self._get_winning_move(player, game_board)
        if winning_move:
            return winning_move
        
        # 2. Vérifier si l'adversaire peut gagner au prochain tour
        blocking_move = self._block_opponent_win(player, opponent, game_board)
        if blocking_move:
            return blocking_move
        
        # 3. Calculer les meilleures actions possibles
        actions = self._generate_strategic_actions(player, opponent, game_board)
        
        if not actions:
            return None
            
        # 4. Évaluer et choisir la meilleure action
        return self._select_best_strategic_action(actions, player, opponent, game_board)

    def _get_winning_move(self, player, game_board):
        """Vérifie si un mouvement gagnant est possible"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        return None

    def _block_opponent_win(self, player, opponent, game_board):
        """Essaie de bloquer un mouvement gagnant de l'adversaire"""
        # Vérifie si l'adversaire peut gagner au prochain tour
        opponent_win_move = self._get_winning_move(opponent, game_board)
        if not opponent_win_move:
            return None
            
        # Si l'adversaire peut gagner, essaye de bloquer avec un mur
        if player.walls_left > 0:
            blocking_wall = self._find_blocking_wall(opponent, opponent_win_move, game_board)
            if blocking_wall and self.is_fully_valid_wall(blocking_wall, game_board):
                return {
                    "type": "wall",
                    "x": blocking_wall.x,
                    "y": blocking_wall.y,
                    "orientation": blocking_wall.orientation
                }
        
        # Si on ne peut pas bloquer avec un mur, on avance nous-même
        return self._get_advancing_move(player, game_board)

    def _find_blocking_wall(self, opponent, opponent_move, game_board):
        """Trouve un mur pour bloquer le mouvement gagnant de l'adversaire"""
        current_pos = opponent.position
        next_pos = opponent_move["position"]
        
        dx = next_pos["x"] - current_pos["x"]
        dy = next_pos["y"] - current_pos["y"]
        
        if dx != 0:  # Mouvement vertical
            wall_x = min(current_pos["x"], next_pos["x"])
            wall_y = next_pos["y"] - 1 if next_pos["y"] > 0 else 0
            orientation = "horizontal"
        else:  # Mouvement horizontal
            wall_x = next_pos["x"] - 1 if next_pos["x"] > 0 else 0
            wall_y = min(current_pos["y"], next_pos["y"])
            orientation = "vertical"
        
        return Wall(x=wall_x, y=wall_y, orientation=orientation)

    def _get_advancing_move(self, player, game_board):
        """Trouve le meilleur mouvement pour avancer"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        best_move = None
        min_distance = float('inf')
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                distance = abs(new_pos["x"] - target_row)
                
                if distance < min_distance or (distance == min_distance and direction in ["up", "down"]):
                    min_distance = distance
                    best_move = {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        return best_move

    def _generate_strategic_actions(self, player, opponent, game_board):
        """Génère des actions stratégiques avec pondération"""
        actions = []
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Mouvements du joueur
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                distance = abs(new_pos["x"] - target_row)
                priority = 3 if direction in ["up", "down"] else 1  # Priorité aux mouvements verticaux
                
                actions.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos,
                    "priority": priority,
                    "distance": distance
                })

        # Murs stratégiques (si le joueur en a)
        if player.walls_left > 0:
            wall_actions = self._generate_effective_walls(player, opponent, game_board)
            actions.extend(wall_actions)
        
        return actions

    def _generate_effective_walls(self, player, opponent, game_board):
        """Génère des murs efficaces pour ralentir l'adversaire"""
        walls = []
        
        # 1. Murs qui bloquent le chemin le plus court de l'adversaire
        opp_path = self._calculate_shortest_path(opponent, game_board)
        if opp_path and len(opp_path) > 1:
            for i in range(1, min(3, len(opp_path))):
                pos = opp_path[i]
                prev_pos = opp_path[i-1]
                
                if pos["x"] != prev_pos["x"]:  # Mouvement vertical
                    wall_x = min(pos["x"], prev_pos["x"])
                    wall_y = pos["y"] - 1 if pos["y"] > 0 else 0
                    orientation = "horizontal"
                else:  # Mouvement horizontal
                    wall_x = pos["x"] - 1 if pos["x"] > 0 else 0
                    wall_y = min(pos["y"], prev_pos["y"])
                    orientation = "vertical"
                
                wall = Wall(x=wall_x, y=wall_y, orientation=orientation)
                if (wall_x, wall_y) not in {(w.x, w.y) for w in game_board.walls} and \
                   self.is_fully_valid_wall(wall, game_board):
                    walls.append({
                        "type": "wall",
                        "x": wall_x,
                        "y": wall_y,
                        "orientation": orientation,
                        "priority": 4  # Haute priorité pour les murs bloquants
                    })
        
        # 2. Murs qui créent des détours pour l'adversaire
        hot_spots = self._find_hot_spots(game_board)
        for (x, y) in hot_spots:
            if (x, y) not in {(w.x, w.y) for w in game_board.walls}:
                for orientation in ["horizontal", "vertical"]:
                    wall = Wall(x=x, y=y, orientation=orientation)
                    if self.is_fully_valid_wall(wall, game_board):
                        walls.append({
                            "type": "wall",
                            "x": x,
                            "y": y,
                            "orientation": orientation,
                            "priority": 2  # Priorité moyenne
                        })
        
        return walls

    def _select_best_strategic_action(self, actions, player, opponent, game_board):
        """Sélectionne l'action la plus stratégique"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Trier les actions par priorité et distance
        player_actions = [a for a in actions if a["type"] == "player"]
        wall_actions = [a for a in actions if a["type"] == "wall"]
        
        # Évaluer les actions de mouvement
        if player_actions:
            best_player_action = min(
                player_actions,
                key=lambda a: (a["distance"], -a["priority"])
            )
        else:
            best_player_action = None
            
        # Évaluer les actions de mur
        if wall_actions:
            best_wall_action = max(
                wall_actions,
                key=lambda a: a["priority"]
            )
            
            # Vérifier si le mur est vraiment utile
            test_board = deepcopy(game_board)
            test_wall = Wall(
                x=best_wall_action["x"],
                y=best_wall_action["y"],
                orientation=best_wall_action["orientation"]
            )
            test_board.walls.append(test_wall)
            b = float('inf')
            
            new_opp_dist = len(self._calculate_shortest_path(opponent, test_board) or float('inf'))
            current_opp_dist = len(self._calculate_shortest_path(opponent, game_board)) or b
            
            if new_opp_dist <= current_opp_dist:  # Le mur n'est pas efficace
                best_wall_action = None
        else:
            best_wall_action = None
        
        # Choisir entre mouvement et mur
        if best_wall_action and best_player_action:
            # Préférer le mur s'il est très prioritaire ou si on a une avance confortabl
            a = float('inf')
            player_dist = len(self._calculate_shortest_path(player, game_board)) or a
            opp_dist = len(self._calculate_shortest_path(opponent, game_board)) or a
            
            if best_wall_action["priority"] >= 4 or (player_dist + 2 < opp_dist):
                return best_wall_action
            else:
                return best_player_action
        elif best_wall_action:
            return best_wall_action
        elif best_player_action:
            return best_player_action
        
        return None

        return actions


    def _generate_all_actions(self, player, game_board):
        """Génère toutes les actions possibles avec priorités sur l'avancée vers la victoire"""
        actions = []
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Mouvements prioritaires (vers la ligne d'arrivée)
        preferred_directions = ["up"] if player.direction == Direction.UP else ["down"]
        secondary_directions = ["left", "right"]
        
        # D'abord vérifier les directions prioritaires
        for direction in preferred_directions + secondary_directions:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                actions.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos,
                    "priority": 1 if direction in preferred_directions else 0
                })

        # Murs (seulement si le joueur en a)
        if player.walls_left > 0:
            wall_candidates = self._generate_strategic_walls(game_board)
            for wall_action in wall_candidates:
                wall = Wall(x=wall_action["x"], y=wall_action["y"], orientation=wall_action["orientation"])
                if self.is_fully_valid_wall(wall, game_board):
                    actions.append(wall_action)

        return actions

    
    def _make_opening_move(self, player, game_board):
        """Stratégie d'ouverture simplifiée"""
        # Toujours avancer vers le haut pour le joueur 1, vers le bas pour le joueur 2
        direction = "up" if player.direction == Direction.UP else "down"
        if game_board.is_valid_move(player, direction):
            return {
                "type": "player",
                "direction": direction,
                "position": game_board.calculate_new_position(player.position, direction)
            }
        return None

    def _make_endgame_move(self, player, game_board):
        """Stratégie de fin de partie optimisée"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        
        # Vérifie d'abord les mouvements gagnants directs
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                if new_pos["x"] == target_row:
                    return {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        # Sinon choisit le mouvement qui rapproche le plus
        best_move = None
        min_distance = float('inf')
        
        for direction in ["up", "down", "left", "right"]:
            if game_board.is_valid_move(player, direction):
                new_pos = game_board.calculate_new_position(player.position, direction)
                distance = abs(new_pos["x"] - target_row)
                if distance < min_distance:
                    min_distance = distance
                    best_move = {
                        "type": "player",
                        "direction": direction,
                        "position": new_pos
                    }
        
        return best_move if best_move else self._fallback_move(player, game_board)
    def _create_game_board(self, board, walls):
        """Crée un objet GameBoard à partir des données du jeu"""
        game_board = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        game_board.set_players({p.id: p for p in players})
        game_board.walls = walls
        return game_board

    
    def _generate_strategic_walls(self, game_board):
        """Génère les murs stratégiques avec validation renforcée"""
        print("je suis APPPPLLLLLEEEEE")
        possible_walls = []
        hot_spots = self._find_hot_spots(game_board)
        existing_walls = {(w.x, w.y, w.orientation) for w in game_board.walls}
        existing_wall_positions = {(w.x, w.y) for w in game_board.walls}  # Positions occupées
        
        for (x, y) in hot_spots:
            # Skip si position déjà occupée (quelque soit l'orientation)
            if (x, y) in existing_wall_positions:
                continue
                
            for orientation in ["horizontal", "vertical"]:
                wall = Wall(x=x, y=y, orientation=orientation)
                
                # Validation complète du mur
                if not self.is_fully_valid_wall(wall, game_board):
                    continue

                    
                # Vérification des chemins
                test_board = deepcopy(game_board)
                test_board.walls.append(wall)
                
                if all(test_board.has_path(p) for p in test_board.players.values()):
                    possible_walls.append({
                        "x": x,
                        "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
        
        return possible_walls
    

    def _find_hot_spots(self, game_board):
        """Trouve les positions stratégiques pour les murs"""
        hot_spots = set()
        
        for player in game_board.players.values():
            if player.id == self.player_id:
                continue
                
            path = self._calculate_shortest_path(player, game_board)
            if path:
                for i in range(1, min(4, len(path))):
                    pos = path[i]
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            x, y = pos["x"] + dx, pos["y"] + dy
                            if 0 <= x < game_board.size - 1 and 0 <= y < game_board.size - 1:
                                hot_spots.add((x, y))
        
        return list(hot_spots)

    def _calculate_shortest_path(self, player, game_board):
        """Calcule le chemin le plus court pour un joueur"""
        from collections import deque
        
        start = player.position
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        visited = set()
        queue = deque([(start["x"], start["y"], [])])
        
        while queue:
            x, y, path = queue.popleft()
            
            if y == target_row:
                return path + [{"x": x, "y": y}]
            
            if (x, y) in visited:
                continue
                
            visited.add((x, y))
            
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < game_board.size and 0 <= ny < game_board.size:
                    if not game_board.is_blocked(x, y, nx, ny):
                        queue.append((nx, ny, path + [{"x": x, "y": y}]))
        
        return None

    def _minimax(self, game_board, depth, maximizing, alpha, beta):
        """Algorithme Minimax optimisé"""
        cache_key = self._create_cache_key(game_board, depth, maximizing)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        current_player = game_board.players[self.player_id]
        opponent = next(p for p in game_board.players.values() if p.id != self.player_id)

        if depth == 0 or self._is_winning_state(current_player, opponent, game_board):
            evaluation = self._evaluate_state(current_player, opponent, game_board)
            self._cache[cache_key] = evaluation
            return evaluation

        active_player = current_player if maximizing else opponent
        actions = self._generate_all_actions(active_player, game_board)

        if not actions:
            evaluation = self._evaluate_state(current_player, opponent, game_board)
            self._cache[cache_key] = evaluation
            return evaluation

        if maximizing:
            max_eval = float("-inf")
            for action in actions:
                new_game_board = self._apply_action(game_board, action, active_player.id)
                eval = self._minimax(new_game_board, depth-1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            self._cache[cache_key] = max_eval
            return max_eval
        else:
            min_eval = float("inf")
            for action in actions:
                new_game_board = self._apply_action(game_board, action, active_player.id)
                eval = self._minimax(new_game_board, depth-1, True, alpha, beta)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break
            self._cache[cache_key] = min_eval
            return min_eval

    def _apply_action(self, game_board, action, player_id):
        """Applique une action sur une copie du plateau"""
        new_game_board = deepcopy(game_board)
        new_players = deepcopy(new_game_board.players)
        
        if action["type"] == "player":
            player = new_players[player_id]
            player.position = action["position"]
        else:
            new_game_board.walls.append(Wall(
                x=action["x"],
                y=action["y"],
                orientation=action["orientation"]
            ))
        
        new_game_board.set_players(new_players)
        return new_game_board

    def _create_cache_key(self, game_board, depth, maximizing):
        """Crée une clé de cache unique"""
        players_key = tuple(
            (pid, p.position["x"], p.position["y"], p.walls_left)
            for pid, p in sorted(game_board.players.items())
        )
        walls_key = tuple(
            (w.x, w.y, w.orientation)
            for w in sorted(game_board.walls, key=lambda x: (x.x, x.y, x.orientation))
        )
        return (players_key, walls_key, depth, maximizing)

    def _is_opening_move(self):
        """Détermine si c'est le début de la partie"""
        players = self.game_service.db.query(Player).all()
        total_walls_placed = sum(9 - p.walls_left for p in players)
        return total_walls_placed < 2

    

    def _is_endgame(self, player, game_board):
        """Détecte la fin de partie"""
        path = self._calculate_shortest_path(player, game_board)
        return path and len(path) <= 3

    

    def _change_strategy(self, player, game_board):
        """Change de stratégie quand des répétitions sont détectées"""
        # Essaye d'abord de bouger le pion
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                move = {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
                self._last_moves.append(str(move))
                return move
        
        # Si aucun mouvement n'est possible, trouve un mur différent
        existing_walls = {(w.x, w.y, w.orientation) for w in game_board.walls}
        for x in range(game_board.size - 1):
            for y in range(game_board.size - 1):
                for orientation in ["horizontal", "vertical"]:
                    if (x, y, orientation) not in existing_walls:
                        try:
                            test_wall = Wall(x=x, y=y, orientation=orientation)
                            test_board = deepcopy(game_board)
                            test_board.walls.append(test_wall)
                            if all(test_board.has_path(p) for p in test_board.players.values()):
                                move = {
                                    "type": "wall",
                                    "x": x,
                                    "y": y,
                                    "orientation": orientation
                                }
                                self._last_moves.append(str(move))
                                return move
                        except:
                            continue
        return self._fallback_move(player, game_board)

    def _fallback_move(self, player, game_board):
        """Dernier recours quand tout échoue"""
        for direction in ["up", "right", "left", "down"]:
            if game_board.is_valid_move(player, direction):
                return {
                    "type": "player",
                    "direction": direction,
                    "position": game_board.calculate_new_position(player.position, direction)
                }
        return {"type": "player", "direction": "up", "position": player.position}

    def _determine_search_depth(self, player):
        """Détermine la profondeur de recherche adaptative"""
        if player.walls_left < 3:  # Fin de partie
            return 4
        players = self.game_service.db.query(Player).all()
        if len(players) == 2 and sum(p.walls_left for p in players) < 10:
            return 3
        return 2

    def _is_winning_state(self, player, opponent, game_board):
        """Vérifie si un joueur a gagné"""
        target_row = 0 if player.direction == Direction.UP else game_board.size - 1
        return player.position["x"] == target_row

    def _evaluate_state(self, player, opponent, game_board):
        """Évaluation complète de l'état du jeu"""
        # Calcul des chemins les plus courts
        my_path = self._calculate_shortest_path(player, game_board)
        opp_path = self._calculate_shortest_path(opponent, game_board)
        
        my_dist = len(my_path) if my_path else float("inf")
        opp_dist = len(opp_path) if opp_path else float("inf")
        
        # Facteurs d'évaluation
        distance_diff = (opp_dist - my_dist) * 2.0
        walls_diff = (player.walls_left - opponent.walls_left) * 0.5
        center_bonus = self._calculate_center_bonus(player.position, game_board.size) * 0.3
        blocking = self._calculate_blocking_potential(opponent, game_board) * 1.5
        mobility = self._calculate_mobility(player, game_board) * 0.2
        
        return distance_diff + walls_diff + center_bonus + blocking + mobility

    def _calculate_center_bonus(self, position, board_size):
        """Bonus pour être près du centre"""
        center = board_size // 2
        dist_to_center = abs(position["x"] - center) + abs(position["y"] - center)
        return -dist_to_center * 0.1

    def _calculate_blocking_potential(self, opponent, game_board):
        """Évalue le potentiel de blocage"""
        score = 0
        path = self._calculate_shortest_path(opponent, game_board)
        
        if path and len(path) > 1:
            current_pos = opponent.position
            next_pos = path[1]
            if self._can_block_move(current_pos, next_pos, game_board):
                score += 2
        
        return score

    def _can_block_move(self, current_pos, next_pos, game_board):
        """Vérifie si un mur peut bloquer ce mouvement"""
        dx = next_pos["x"] - current_pos["x"]
        dy = next_pos["y"] - current_pos["y"]
        
        if dx > 0:  # Vers le bas
            wall_x, wall_y = current_pos["x"], min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dx < 0:  # Vers le haut
            wall_x, wall_y = current_pos["x"]-1, min(current_pos["y"], game_board.size-2)
            orientation = "vertical"
        elif dy > 0:  # Vers la droite
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]
            orientation = "horizontal"
        else:  # Vers la gauche
            wall_x, wall_y = min(current_pos["x"], game_board.size-2), current_pos["y"]-1
            orientation = "horizontal"
        
        try:
            test_wall = Wall(x=wall_x, y=wall_y, orientation=orientation)
            test_board = deepcopy(game_board)
            test_board.walls.append(test_wall)
            return all(test_board.has_path(p) for p in test_board.players.values())
        except:
            return False

    def _calculate_mobility(self, player, game_board):
        """Calcule la mobilité du joueur"""
        return sum(
            1 for direction in ["up", "down", "left", "right"] 
            if game_board.is_valid_move(player, direction)
        )

    def apply_move_to_db(self, move):
        if move["type"] == "wall":
            with self.game_service.db.begin() as transaction:
                # Vérification atomique
                exists = self.game_service.db.query(
                    exists().where(
                        and_(
                            Wall.x == move["x"],
                            Wall.y == move["y"]
                        )
                    )
                ).scalar()
                
                if exists:
                    logger.warning(f"Wall position {move['x']},{move['y']} already occupied")
                    transaction.rollback()
                    return False
                    
                wall = Wall(
                    x=move["x"],
                    y=move["y"],
                    orientation=move["orientation"].upper(),
                    player_id=self.player_id
                )
                self.game_service.db.add(wall)
                logger.info(f"Wall successfully placed at {wall.x},{wall.y}")
            return True
        return False
    def _generate_wall_candidates(self, game_board):
        """Génère des candidats murs avec vérification des croisements"""
        candidates = []
        hot_spots = self._find_hot_spots(game_board)
        existing_walls = {(w.x, w.y): w.orientation for w in game_board.walls}
        
        for x, y in hot_spots:
            # Ne pas proposer de mur là où il y a déjà un mur (quelque soit l'orientation)
            if (x, y) not in existing_walls:
                for orientation in ["horizontal", "vertical"]:
                    candidates.append({
                        "x": x,
                        "y": y,
                        "orientation": orientation,
                        "type": "wall"
                    })
        
        return candidates
    
    def is_fully_valid_wall(self, wall, game_board):
        # Validation logique de base
        if not game_board._is_valid_wall(wall):
            return False
        
        # Validation des chemins (aucun joueur ne doit être bloqué)
        # On clone le plateau pour tester l'ajout du mur
        test_board = GameBoard(size=game_board.size)
        
        # Copie des joueurs
        new_players = {
            pid: Player(
                id=p.id,
                position=dict(p.position),
                direction=p.direction,
                walls_left=p.walls_left
            ) for pid, p in game_board.players.items()
        }
        test_board.set_players(new_players)
        
        # Copie des murs + ajout du nouveau
        test_board.walls = [Wall(x=w.x, y=w.y, orientation=w.orientation, player_id=w.player_id) for w in game_board.walls] + [wall]
        
        # Vérifie qu'il y a un chemin pour chaque joueur
        return all(test_board.has_path(p) for p in test_board.players.values())


    

    # ... (conservez les autres méthodes existantes sans modification) ...

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