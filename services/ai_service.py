from copy import deepcopy
import random
from collections import deque
import math

from models.player import Player
from models.wall import Wall 
from models.enums import Direction
from .board_logic import GameBoard
import numpy as np

import heapq
import logging
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


from models.player import Player
from models.wall import Wall
from models.enums import Direction, Orientation




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
        # Récupère les coordonnées et l'orientation du mur
        x = wall.get("x") if isinstance(wall, dict) else wall.x
        y = wall.get("y") if isinstance(wall, dict) else wall.y
        orientation = wall.get("orientation") if isinstance(wall, dict) else wall.orientation

        # Vérifie si le mur est dans les limites du plateau
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

        # Un mur croise un autre si les deux ont une orientation différente et la même position        
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
        # Ajoute le mur a la liste temporaire des murs
        temp_walls = existing_walls + [Wall(
            x=new_wall.get("x") if isinstance(new_wall, dict) else new_wall.x,
            y=new_wall.get("y") if isinstance(new_wall, dict) else new_wall.y,
            orientation=new_wall.get("orientation") if isinstance(new_wall, dict) else new_wall.orientation
        )]

        # Fonction de recherche en largeur (BFS) pour détecter un chemin 
        #chat-gpt-promt: pouvez vous nous proposer des algorithmes de détection de chemin efficace pour un jeu de stratégie
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

                # Vérifie les 4 directions autour du joueur
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
    """"
    Mixin pour la recherche de chemin sur le plateau.

    Cette classe fournit une méthode `calculate_shortest_path` qui utilise un algorithme de 
    recherche en largeur (BFS) pour calculer le plus court chemin qu un joueur peut emprunter 
    depuis sa position actuelle jusqu à sa ligne d arrivée (selon sa direction).
    Elle prend en compte la taille du plateau et les murs présents qui peuvent bloquer le passage
    """
    
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


class RandomAInotused(WallValidationMixin, PathfindingMixin):
    """AI with random strategy"""
    #Si le joueur a des murs à poser (walls_left > 0),
    #Tente jusqu’à 5 fois de choisir un mur valide aléatoire parmi tous les murs possibles
    #Pour chaque tentative, elle vérifie que la pose est valide (via is_valid_wall),
    #Si un mur valide est trouvé, elle le retourne comme action.
    #sinon elle rends un mouvement aléatoire valide parmi les deplacement valide

    
    def __init__(self, game_service, player_id):
        # Initialise l'IA avec une référence au service de jeu et à l'ID du joueur contrôlé
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        # Récupère l'état du plateau, les joueurs, les murs
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        print(f"Player {player.id} choosing move...")
        print(f"Current position: {player.position}, Walls left: {player.walls_left}")
        if not player or not board:
            return None

        # Crée une logique de plateau à partir des donnees
        board_logic = GameBoard(size=board.width)
        players = self.game_service.db.query(Player).all()
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        # Tente de poser un mur avec une chance de 30%
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
        # Génère toutes les positions possibles pour les murs valides (horizontaux + verticaux)
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





import time
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from .board_logic import GameBoard

def make_hashable(obj):
    """Transforme récursivement un dict en tuple pour le rendre hashable."""
    if isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, list):
        return tuple(make_hashable(e) for e in obj)
    else:
        return obj

class BasicAI:
    """IA  basée sur Monte Carlo Tree Search """
    
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id
        self.opponent_id = 1 if player_id == 2 else 2
        self.exploration_weight = 1.414  # Paramètre d'exploration (sqrt(2))
        self.time_limit = 2.0  # Limite de temps en secondes
        self.simulation_depth = 20  # Profondeur maximale des simulations
        
    def choose_move(self):
        """Choisit le meilleur mouvement en utilisant MCTS"""
        board, state, walls = self.game_service.get_board_and_state()
        players = {
            p.id: p for p in self.game_service.db.query(Player).all()
        }
        
        root_state = {
            'players': players,
            'walls': walls,
            'board': board
        }
        
        root = Node(root_state, None, self.player_id)
        
        start_time = time.time()
        iterations = 0
        
        # Exploration de l'arbre dans la limite de temps
        while time.time() - start_time < self.time_limit:
            self.mcts_iteration(root)
            iterations += 1
        
        print(f"MCTS completed {iterations} iterations in {time.time() - start_time:.2f}s")
        
        # Choisir le mouvement avec le meilleur score
        best_move = max(root.children, key=lambda c: c.visits)
        return best_move.move
    
    def mcts_iteration(self, node):
        """Une itération complète de MCTS (sélection, expansion, simulation, backpropagation)"""
        # Sélection
        selected_node = self.select(node)
        
        # Expansion
        if not selected_node.is_terminal():
            selected_node = self.expand(selected_node)
        
        # Simulation
        result = self.simulate(selected_node)
        
        # Backpropagation
        self.backpropagate(selected_node, result)
    
    def select(self, node):
        """Sélectionne le meilleur noeud à explorer selon UCT"""
        while node.children:
            # Si le noeud n'est pas entièrement développé
            if not node.is_fully_expanded():
                return node
            
            # Sinon, choisir le meilleur enfant selon UCT
            node = max(node.children, key=lambda c: self.uct_value(c))
        
        return node
    
    def expand(self, node):
        """Étend l'arbre en ajoutant un nouveau noeud enfant"""
        # Générer tous les mouvements possibles
        possible_moves = self.get_valid_moves(node.state)
        
        # Trouver les mouvements non encore explorés
        explored_moves = {make_hashable(child.move) for child in node.children}
        unexplored_moves = [m for m in possible_moves if make_hashable(m) not in explored_moves]
        if not unexplored_moves:
            return node  # Ne devrait pas arriver si is_fully_expanded est correct
        
        # Choisir un mouvement aléatoire parmi les non explorés
        move = random.choice(unexplored_moves)
        
        # Appliquer le mouvement pour obtenir le nouvel état
        new_state = self.apply_move(node.state, move)
        
        # Créer le nouveau noeud
        new_node = Node(
            state=new_state,
            parent=node,
            player_id=self.opponent_id if node.player_id == self.player_id else self.player_id,
            move=move
        )
        
        node.children.append(new_node)
        return new_node
    
    def simulate(self, node):
        """Simule une partie aléatoire à partir de ce noeud"""
        state = deepcopy(node.state)
        current_player = node.player_id
        depth = 0
        
        while depth < self.simulation_depth:
            # Vérifier si c'est un état terminal
            winner = self.check_winner(state)
            if winner is not None:
                return 1 if winner == self.player_id else 0
            
            # Choisir un mouvement aléatoire
            possible_moves = self.get_valid_moves(state)
            if not possible_moves:
                return 0.5  # Match nul
            
            move = random.choice(possible_moves)
            state = self.apply_move(state, move)
            current_player = self.opponent_id if current_player == self.player_id else self.player_id
            depth += 1
        
        # Si on atteint la profondeur maximale, évaluer l'état
        return self.evaluate_state(state)
    
    def backpropagate(self, node, result):
        """Remonte le résultat de la simulation dans l'arbre"""
        while node is not None:
            node.visits += 1
            node.wins += result if node.player_id == self.player_id else (1 - result)
            node = node.parent
    
    def uct_value(self, node):
        """Calcule la valeur UCT d'un noeud"""
        if node.visits == 0:
            return float('inf')  # Priorité maximale pour les noeuds non visités
        
        exploitation = node.wins / node.visits
        exploration = self.exploration_weight * math.sqrt(math.log(node.parent.visits) / node.visits)
        return exploitation + exploration
    
    def get_valid_moves(self, state):
        """Retourne tous les mouvements valides pour l'état actuel"""
        moves = []
        player = state['players'][self.player_id]
        board_logic = GameBoard(size=state['board'].width)
        board_logic.set_players(state['players'])
        board_logic.walls = state['walls']
        
        # Mouvements de pion
        directions = ["up", "down", "left", "right"]
        for direction in directions:
            if board_logic.is_valid_move(player, direction):
                new_pos = board_logic.calculate_new_position(player.position, direction)
                moves.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos
                })
        
        # Placement de murs (si le joueur en a encore)
        if player.walls_left > 0:
            # Stratégie: ne considérer que les murs près du chemin de l'adversaire
            opponent = state['players'][self.opponent_id]
            opp_path = self.calculate_shortest_path(opponent, board_logic, state['walls'])
            
            if opp_path:
                # Générer des murs près du chemin de l'adversaire
                for i in range(1, min(4, len(opp_path))):
                    x, y = opp_path[i]
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < board_logic.width - 1 and 0 <= ny < board_logic.height - 1:
                                for orientation in ["horizontal", "vertical"]:
                                    wall = Wall(x=nx, y=ny, orientation=orientation)
                                    if board_logic._is_valid_wall(wall):
                                        moves.append({
                                            "type": "wall",
                                            "x": nx,
                                            "y": ny,
                                            "orientation": orientation
                                        })
        
        return moves
    
    def apply_move(self, state, move):
        """Applique un mouvement à l'état et retourne le nouvel état"""
        new_state = deepcopy(state)
        players = new_state['players']
        walls = new_state['walls']
        
        if move["type"] == "player":
            players[self.player_id].position = move["position"]
        else:
            wall = Wall(
                x=move["x"],
                y=move["y"],
                orientation=move["orientation"],
                player_id=self.player_id
            )
            walls.append(wall)
            players[self.player_id].walls_left -= 1
        
        return new_state
    
    def check_winner(self, state):
        """Vérifie s'il y a un gagnant dans l'état actuel"""
        board_logic = GameBoard(size=state['board'].width)
        board_logic.set_players(state['players'])
        board_logic.walls = state['walls']
        
        for pid, player in state['players'].items():
            if player.direction == Direction.UP and player.position["x"] == 0:
                return pid
            if player.direction == Direction.DOWN and player.position["x"] == board_logic.height - 1:
                return pid
        
        return None
    
    def evaluate_state(self, state):
        """Évalue l'état du jeu (0-1) pour le joueur courant"""
        player = state['players'][self.player_id]
        opponent = state['players'][self.opponent_id]
        board_logic = GameBoard(size=state['board'].width)
        board_logic.set_players(state['players'])
        board_logic.walls = state['walls']
        
        # Calcul des distances au but
        player_dist = len(self.calculate_shortest_path(player, board_logic, state['walls'])) or 100
        opp_dist = len(self.calculate_shortest_path(opponent, board_logic, state['walls'])) or 100
        
        # Avantage des murs
        wall_advantage = (player.walls_left - opponent.walls_left) * 0.1
        
        # Score basé sur la différence de distance
        score = 0.5 + (opp_dist - player_dist) * 0.05 + wall_advantage
        return max(0, min(1, score))  # Clamper entre 0 et 1
    
    def calculate_shortest_path(self, player, board_logic, walls):
        """Calcule le chemin le plus court pour un joueur"""
        start = player.position
        target_row = 0 if player.direction == Direction.UP else board_logic.height - 1
        
        visited = set()
        queue = [(start["x"], start["y"], [])]
        
        while queue:
            x, y, path = queue.pop(0)
            if x == target_row:
                return path + [(x, y)]
            
            if (x, y) in visited:
                continue
            visited.add((x, y))
            
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < board_logic.width and 0 <= ny < board_logic.height:
                    if not self.is_path_blocked(x, y, nx, ny, walls):
                        queue.append((nx, ny, path + [(x, y)]))
        
        return None
    
    def is_path_blocked(self, x1, y1, x2, y2, walls):
        """Vérifie si le chemin entre deux points est bloqué par un mur"""
        if y1 == y2:  # Mouvement horizontal
            wall_x = min(x1, x2)
            return any(wall.orientation == "horizontal" and
                      wall.x == wall_x and
                      (wall.y == y1 or wall.y == y1 - 1)
                      for wall in walls)
        elif x1 == x2:  # Mouvement vertical
            wall_y = min(y1, y2)
            return any(wall.orientation == "vertical" and
                      wall.y == wall_y and
                      (wall.x == x1 or wall.x == x1 - 1)
                      for wall in walls)
        return False
    
    def make_hashable(obj):
        """Transforme récursivement un dict en tuple pour le rendre hashable."""
        if isinstance(obj, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return tuple(make_hashable(e) for e in obj)
        else:
            return obj


class Node:
    """Noeud de l'arbre MCTS"""
    
    def __init__(self, state, parent, player_id, move=None):
        self.state = state  # État du jeu
        self.parent = parent  # Noeud parent
        self.player_id = player_id  # Joueur qui doit jouer
        self.move = move  # Mouvement qui a mené à ce noeud
        self.children = []  # Noeuds enfants
        self.visits = 0  # Nombre de visites
        self.wins = 0  # Nombre de victoires simulées
    
    def is_fully_expanded(self):
        """Vérifie si tous les mouvements possibles ont été explorés"""
        possible_moves = self.get_possible_moves()
        return len(self.children) >= len(possible_moves)
    
    def is_terminal(self):
        """Vérifie si c'est un noeud terminal (fin de partie)"""
        return self.check_winner() is not None
    
    def get_possible_moves(self):
        """Retourne tous les mouvements possibles pour ce noeud"""
        # Implémentation simplifiée - devrait utiliser la même méthode que MCTSAI
        moves = []
        board_logic = GameBoard(size=self.state['board'].width)
        board_logic.set_players(self.state['players'])
        board_logic.walls = self.state['walls']
        player = self.state['players'][self.player_id]
        
        # Mouvements de pion
        directions = ["up", "down", "left", "right"]
        for direction in directions:
            if board_logic.is_valid_move(player, direction):
                new_pos = board_logic.calculate_new_position(player.position, direction)
                moves.append({
                    "type": "player",
                    "direction": direction,
                    "position": new_pos
                })
        
        # Placement de murs
        if player.walls_left > 0:
            for x in range(board_logic.width - 1):
                for y in range(board_logic.height - 1):
                    for orientation in ["horizontal", "vertical"]:
                        wall = Wall(x=x, y=y, orientation=orientation)
                        if board_logic._is_valid_wall(wall):
                            moves.append({
                                "type": "wall",
                                "x": x,
                                "y": y,
                                "orientation": orientation
                            })
        
        return moves
    
    def check_winner(self):
        """Vérifie s'il y a un gagnant dans cet état"""
        board_logic = GameBoard(size=self.state['board'].width)
        board_logic.set_players(self.state['players'])
        board_logic.walls = self.state['walls']
        
        for pid, player in self.state['players'].items():
            if player.direction == Direction.UP and player.position["x"] == 0:
                return pid
            if player.direction == Direction.DOWN and player.position["x"] == board_logic.height - 1:
                return pid
        
        return None



    

class AdvancedAI(PathfindingMixin):

    #Minimax avec élagage alpha-bêta
    #Place  des murs agressifs en avance
    #Alterne attaque et défense selon le jeu
    #heuristique 
    def __init__(self, game_service, player_id):
        self.game_service = game_service
        self.player_id = player_id

    def choose_move(self):
        board, state, walls = self.game_service.get_board_and_state()
        player = self.game_service.get_player(self.player_id)
        players = self.game_service.db.query(Player).all()
        opponent = next(p for p in players if p.id != self.player_id)

        # Profondeur dynamique selon le nombre de murs restants
        if player.walls_left < 3 or opponent.walls_left < 3:
            depth = 3
        else:
            depth = 2

        actions = self._generate_all_actions(player, board, walls, opponent)
        actions = sorted(actions, key=lambda a: 0 if a["type"] == "player" else 1)
        if len(actions) > 20:
            actions = actions[:20]

        best_score = float("-inf")
        best_action = None

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
                new_players, new_walls, board, depth=depth,
                maximizing=False, alpha=float("-inf"), beta=float("inf")
            )

            if score > best_score:
                best_score = score
                best_action = action

            if action["type"] == "player" and self._evaluate_state(target_player, opponent, new_walls, board) > 1000:
                return action

        return best_action

    def _generate_all_actions(self, player, board, walls, opponent):
        # Génère tous les déplacements valides et les poses de murs possibles
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
        # Génère des murs pour gener l'adversaire en analysant son chemin
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

        for group in grouped_by_segment.values():
            if group:
                wall_candidates.append(group[0])

        return wall_candidates

    def _generate_aggressive_walls(self, opponent, board, walls):
        # Variante agressive : pose de murs rapides sur le chemin de l’adversaire
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

        return candidates

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
        # Fonction heuristique qui évalue l’état du jeu :
        # Plus le score est élevé, meilleur est l’état pour l’IA
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
        return score