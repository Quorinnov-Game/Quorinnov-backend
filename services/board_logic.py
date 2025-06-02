from sqlalchemy import Column, Integer, String
from database import Base
from models.wall import Wall
from models.player import Player
from models.enums import Orientation, Direction

class GameBoard:
    def __init__(self, size=9):
        self.size = size
        self.grid = [["" for _ in range(size)] for _ in range(size)]
        self.walls: list[Wall] = []
        self.players: dict[int, Player] = {}

    def set_players(self, players: dict[int, Player]):
        """set player and update position of player on grid"""
        self.players = players
        self._update_grid()

    def _update_grid(self):
        """update position of player on grid"""
        self.grid = [["" for _ in range(self.size)] for _ in range(self.size)]
        for pid, player in self.players.items():
            x, y = player.position["x"], player.position["y"]
            self.grid[x][y] = f"P{pid}"

    def get_grid(self):
        """return grid for frontend (phục vụ frontend)"""
        self._update_grid()
        return self.grid

    def add_wall(self, wall: Wall) -> bool:
        """check the valid if valid add wall"""
        if not self._is_valid_wall(wall):
            return False
        self.walls.append(wall)
        return True

    def _is_valid_wall(self, wall: Wall) -> bool:
        x, y = wall.x, wall.y
        orientation = wall.orientation

        # Kiểm tra giới hạn bàn cờ tường có thể được đặt (0 -> 7)
        if (0 <= x <= self.size - 2 and 0 <= y <= self.size - 2):
            return True

        # Kiểm tra trùng vị trí
        for w in self.walls:
            if w.orientation == orientation:
                if orientation == Orientation.HORIZONTAL:
                    return abs(w.y - y) <= 1 and w.x == x
                elif orientation == Orientation.VERTICAL:
                    return abs(w.x - x) <= 1 and w.y == y

        # Kiểm tra giao nhau (như frontend đã làm)
        for w in self.walls:
            return w.x == x and w.y == y and w.orientation != orientation

        # (Optional) kiểm tra chắn đường
        self.walls.append(wall)
        has_path_p1 = self.has_path(self.players[1])
        has_path_p2 = self.has_path(self.players[2])
        self.walls.pop()  # Gỡ lại wall tạm

        if not (has_path_p1 and has_path_p2):
            return False

        return True


    def has_path(self, player: Player) -> bool:
        from collections import deque
        visited = set()
        queue = deque()
        queue.append((player.position["x"], player.position["y"]))
        target_row = 0 if player.direction == Direction.UP else self.size - 1

        while queue:
            x, y = queue.popleft()
            if x == target_row:
                return True
            visited.add((x, y))

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < self.size and 0 <= ny < self.size):
                    continue
                if (nx, ny) in visited:
                    continue

                # ⚠ Quan trọng: Gọi đúng chiều truyền vào để phù hợp với `is_blocked`
                if self.is_blocked(min(x, nx), min(y, ny), max(x, nx), max(y, ny)):
                    continue

                queue.append((nx, ny))

        return False
    def is_blocked(self, x1, y1, x2, y2):
        for wall in self.walls:
            wx, wy = wall.x, wall.y
            ori = wall.orientation

            if ori == Orientation.HORIZONTAL:
                # chắn giữa (x,y) và (x,y+1)
                if x1 == x2 == wx and {y1, y2} == {wy, wy + 1}:
                    return True
            elif ori == Orientation.VERTICAL:
                # chắn giữa (x,y) và (x+1,y)
                if y1 == y2 == wy and {x1, x2} == {wx, wx + 1}:
                    return True
        return False

    def get_walls(self):
        return [w.to_dict() for w in self.walls]

    def is_valid_move(self, player: Player, direction: Direction) -> bool:
        x, y = player.position["x"], player.position["y"]
        dx, dy = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[direction]

        nx, ny = x + dx, y + dy
        if not (0 <= nx < self.size and 0 <= ny < self.size):
            return False
        if self.is_blocked(x, y, nx, ny):
            return False
        # Kiểm tra nếu ô tiếp theo có người chơi khác
        for pid, other in self.players.items():
            if other.id != player.id and other.position["x"] == nx and other.position["y"] == ny:
                # Người chơi khác đang ở phía trước

                # Tọa độ sau người chơi kia
                jump_x, jump_y = nx + dx, ny + dy
                if (0 <= jump_x < self.size and 0 <= jump_y < self.size and
                    not self.is_blocked(nx, ny, jump_x, jump_y)):
                    # Có thể nhảy qua
                    return True
                else:
                    # Không thể nhảy qua, kiểm tra sang trái/phải
                    if direction in [Direction.UP, Direction.DOWN]:
                        # thử sang trái và phải
                        for side_dy in [-1, 1]:
                            side_y = ny + side_dy
                            if (0 <= side_y < self.size and
                                not self.is_blocked(nx, ny, nx, side_y)):
                                return True
                    else:
                        # thử lên hoặc xuống
                        for side_dx in [-1, 1]:
                            side_x = nx + side_dx
                            if (0 <= side_x < self.size and
                                not self.is_blocked(nx, ny, side_x, ny)):
                                return True
                    return False

        # Không có ai phía trước → bình thường
        return True

    def calculate_new_position(self, position: dict, direction: Direction) -> dict:
        dx, dy = {
            Direction.UP: (-1, 0),
            Direction.DOWN: (1, 0),
            Direction.LEFT: (0, -1),
            Direction.RIGHT: (0, 1),
        }[direction]

        return {
            "x": position["x"] + dx,
            "y": position["y"] + dy
        }

    print("nothing")




def is_valid_move_state(self, state, player, direction):
    """
    Vérifie si le déplacement est valide dans l'état 'state' simulé.
    """
    # Exemple simplifié:
    x, y = player['position']
    new_pos = self.calculate_new_position((x, y), direction)

    # Vérifier que new_pos est dans la grille
    if not self.is_valid_position(*new_pos):
        return False

    # Vérifier qu'il n'y a pas de mur entre pos et new_pos en fonction des murs dans 'state'
    if self.is_wall_blocking(state, (x, y), new_pos):
        return False

    # Vérifier que new_pos n'est pas occupé par l'autre joueur
    for pid, p in state['players'].items():
        if p['position'] == new_pos and pid != player['id']:
            return False

    return True
def is_valid_wall_state(self, state, player_id, x, y, orientation):
    """
    Vérifie si poser un mur est valide dans l'état simulé.
    """
    # Valide position, non chevauchement avec murs déjà posés dans 'state'
    # et que ça ne bloque pas complètement un joueur (doit appeler un pathfinder)
    
    # Exemple:
    if not self.is_within_bounds_for_wall(x, y, orientation):
        return False

    for wall in state['walls']:
        if self.walls_overlap(wall, {'x': x, 'y': y, 'orientation': orientation}):
            return False

    # Ajouter le mur temporairement dans une copie de state, vérifier si chaque joueur a encore un chemin vers la ligne d'arrivée
    temp_state = deepcopy(state)
    temp_state['walls'].append({"x": x, "y": y, "orientation": orientation})

    for pid, player in temp_state['players'].items():
        target_rows = [0] if player['direction'] == Direction.UP else [self.size - 1]
        path = self.a_star(player['position'], target_rows, temp_state)
        if path is None:
            return False

    return True



import heapq

def a_star(start_pos, target_rows, state, board_size):
    """
    start_pos: tuple (x,y)
    target_rows: list d'indices de lignes d'arrivée (par ex [0] ou [8])
    state: dict contenant players, walls, etc. (état simulé)
    board_size: taille de la grille (ex 9)
    """

    def heuristic(pos):
        # Distance Manhattan au plus proche row cible
        x, y = pos
        return min(abs(y - target_row) for target_row in target_rows)

    def neighbors(pos):
        x, y = pos
        possible_moves = [
            (x, y-1),  # UP
            (x, y+1),  # DOWN
            (x-1, y),  # LEFT
            (x+1, y)   # RIGHT
        ]

        valid_neighbors = []
        for nx, ny in possible_moves:
            # Vérifier limites
            if nx < 0 or nx >= board_size or ny < 0 or ny >= board_size:
                continue

            # Vérifier si un mur bloque le passage entre pos et (nx, ny)
            if is_wall_blocking(state, pos, (nx, ny)):
                continue

            # Vérifier qu'il n'y a pas un autre joueur à cette position
            occupied = False
            for pid, player in state['players'].items():
                if player['position'] == (nx, ny):
                    occupied = True
                    break
            if occupied:
                continue

            valid_neighbors.append((nx, ny))
        return valid_neighbors

    open_set = []
    heapq.heappush(open_set, (heuristic(start_pos), 0, start_pos))
    came_from = {}
    g_score = {start_pos: 0}

    while open_set:
        _, current_g, current = heapq.heappop(open_set)

        # Vérifier si on est arrivé sur une des lignes d'arrivée
        if current[1] in target_rows:
            # Reconstituer le chemin
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start_pos)
            path.reverse()
            return path

        for neighbor in neighbors(current):
            tentative_g_score = current_g + 1
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score = tentative_g_score + heuristic(neighbor)
                heapq.heappush(open_set, (f_score, tentative_g_score, neighbor))

    # Pas de chemin trouvé
    return None

def is_wall_blocking(state, pos1, pos2):
    """
    Vérifie si un mur dans state bloque la connexion entre pos1 et pos2 (adjacents).
    """
    x1, y1 = pos1
    x2, y2 = pos2

    # Exemple simplifié pour murs horizontaux et verticaux:
    # Si on veut avancer vers le haut (y-1), vérifier un mur horizontal au-dessus de pos1
    for wall in state['walls']:
        wx, wy, orientation = wall['x'], wall['y'], wall['orientation']
        if orientation == 'H':
            # Mur horizontal bloque passage vertical entre (x, y) et (x, y-1) ou (x, y) et (x, y+1)
            if (x1 == wx and x2 == wx) and ((y1 == wy and y2 == wy - 1) or (y2 == wy and y1 == wy - 1)):
                return True
        elif orientation == 'V':
            # Mur vertical bloque passage horizontal entre (x, y) et (x-1, y) ou (x, y) et (x+1, y)
            if (y1 == wy and y2 == wy) and ((x1 == wx and x2 == wx - 1) or (x2 == wx and x1 == wx - 1)):
                return True

    return False






    