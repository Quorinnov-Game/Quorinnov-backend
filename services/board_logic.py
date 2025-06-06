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

    '''
    def _is_valid_wall(self, wall: Wall) -> bool:
        print("JE SUIS UTILIS2EEEEEEEEE")
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

    '''
    '''V2
    def _is_valid_wall(self, wall: Wall) -> bool:
        x, y = wall.x, wall.y
        orientation = wall.orientation.upper()

        print(f"[VALIDATION] Vérification du mur à ({x},{y}) - {orientation}")

        # 1. Vérification des limites du plateau
        if not (0 <= x <= self.size - 2 and 0 <= y <= self.size - 2):
            print("[INVALID] Hors des limites du plateau.")
            return False

        # 2. Vérification des murs déjà présents
        for w in self.walls:
            if w.x == x and w.y == y and w.orientation == orientation:
                print("[INVALID] Mur déjà placé exactement au même endroit.")
                return False

            # 3. Collision avec un mur adjacent (ex. deux horizontaux côte à côte)
            if orientation == Orientation.HORIZONTAL and w.orientation == Orientation.HORIZONTAL:
                if w.x == x and abs(w.y - y) == 1:
                    print("[INVALID] Collision avec un autre mur horizontal adjacent.")
                    return False
            if orientation == Orientation.VERTICAL and w.orientation == Orientation.VERTICAL:
                if w.y == y and abs(w.x - x) == 1:
                    print("[INVALID] Collision avec un autre mur vertical adjacent.")
                    return False

            # 4. Croisement interdit
            if w.x == x and w.y == y and w.orientation != orientation:
                print("[INVALID] Croisement de mur interdit.")
                return False

        # 5. Vérification des chemins accessibles
        self.walls.append(wall)
        has_path_p1 = self.has_path(self.players[1])
        has_path_p2 = self.has_path(self.players[2])
        self.walls.pop()  # rollback

        if not (has_path_p1 and has_path_p2):
            print("[INVALID] Le mur bloque tous les chemins.")
            return False

        print("[VALID] Mur autorisé.")
        return True

    '''

    def _is_valid_wall(self, wall: Wall) -> bool:
        x, y = wall.x, wall.y
        orientation = wall.orientation.upper()

        print(f"[VALIDATION] Vérification du mur à ({x},{y}) - {orientation}")

        # 1. Vérification des limites du plateau
        if not (0 <= x <= self.size - 2 and 0 <= y <= self.size - 2):
            print("[INVALID] Hors des limites du plateau.")
            return False

        # 2. Vérification des murs déjà présents
        for w in self.walls:
            if w.x == x and w.y == y and w.orientation.upper() == orientation:
                print("[INVALID] Mur déjà placé exactement au même endroit.")
                return False

            # 3. Collision avec un mur adjacent (de même type côte à côte)
            if orientation == "HORIZONTAL" and w.orientation.upper() == "HORIZONTAL":
                if w.x == x and abs(w.y - y) == 1:
                    print("[INVALID] Collision avec un autre mur horizontal adjacent.")
                    return False
            if orientation == "VERTICAL" and w.orientation.upper() == "VERTICAL":
                if w.y == y and abs(w.x - x) == 1:
                    print("[INVALID] Collision avec un autre mur vertical adjacent.")
                    return False

            # 4. Croisement interdit
            if w.x == x and w.y == y and w.orientation.upper() != orientation:
                print("[INVALID] Croisement de mur interdit.")
                return False

        # 5. Barrière trop longue (3 cases alignées)
        if orientation == "HORIZONTAL":
            neighbors = [(x - 1, y), (x + 1, y)]
            count = sum(
                1 for nx, ny in neighbors
                if any(w.x == nx and w.y == ny and w.orientation.upper() == "HORIZONTAL" for w in self.walls)
            )
            if count == 2:
                print("[INVALID] Mur horizontal formerait une barrière de 3 cases.")
                return False

        if orientation == "VERTICAL":
            neighbors = [(x, y - 1), (x, y + 1)]
            count = sum(
                1 for nx, ny in neighbors
                if any(w.x == nx and w.y == ny and w.orientation.upper() == "VERTICAL" for w in self.walls)
            )
            if count == 2:
                print("[INVALID] Mur vertical formerait une barrière de 3 cases.")
                return False

        # 6. Vérification des chemins accessibles pour tous les joueurs
        self.walls.append(wall)
        has_path_p1 = self.has_path(self.players[1])
        has_path_p2 = self.has_path(self.players[2])
        self.walls.pop()  # rollback

        if not (has_path_p1 and has_path_p2):
            print("[INVALID] Le mur bloque tous les chemins.")
            return False

        print("[VALID] Mur autorisé.")
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
    def is_blocked(self, x1: int, y1: int, x2: int, y2: int) -> bool:
        """
        Kiểm tra xem có tường chặn giữa hai vị trí không
        x1, y1: vị trí hiện tại
        x2, y2: vị trí đích
        """
        for wall in self.walls:
            wx, wy = wall.x, wall.y
            ori = wall.orientation

            # Di chuyển theo chiều dọc (y không đổi)
            if y1 == y2:
                min_x = min(x1, x2)
                if ori == Orientation.HORIZONTAL:
                    # Tường ngang chặn đường đi
                    if (wx == min_x and 
                        (wy == y1 or wy + 1 == y1)):
                        return True

            # Di chuyển theo chiều ngang (x không đổi) 
            if x1 == x2:
                min_y = min(y1, y2)
                if ori == Orientation.VERTICAL:
                    # Tường dọc chặn đường đi
                    if (wy == min_y and 
                        (wx == x1 or wx + 1 == x1)):
                        return True
        return False

    def get_valid_moves(self, player: Player) -> list[dict]:
        """
        Lấy tất cả các nước đi hợp lệ cho người chơi
        """
        valid_moves = []
        x, y = player.position["x"], player.position["y"]

        # Kiểm tra 4 hướng
        directions = [
            (Direction.UP, -1, 0),
            (Direction.DOWN, 1, 0), 
            (Direction.LEFT, 0, -1),
            (Direction.RIGHT, 0, 1)
        ]

        for direction, dx, dy in directions:
            nx, ny = x + dx, y + dy

            # Kiểm tra giới hạn bàn cờ
            if not (0 <= nx < self.size and 0 <= ny < self.size):
                continue

            # Kiểm tra tường chặn
            if self.is_blocked(x, y, nx, ny):
                continue

            # Kiểm tra va chạm với người chơi khác
            other_player = None
            for pid, p in self.players.items():
                if (p.id != player.id and 
                    p.position["x"] == nx and 
                    p.position["y"] == ny):
                    other_player = p
                    break

            if other_player:
                # TH1: Có thể nhảy qua
                jump_x, jump_y = nx + dx, ny + dy
                if (0 <= jump_x < self.size and 
                    0 <= jump_y < self.size and
                    not self.is_blocked(nx, ny, jump_x, jump_y) and
                    not any(p.position["x"] == jump_x and 
                           p.position["y"] == jump_y 
                           for p in self.players.values())):
                    valid_moves.append({
                        "x": jump_x,
                        "y": jump_y
                    })

                else:
                    # TH2: Nhảy sang ngang
                    is_vertical = dx != 0
                    if is_vertical:
                        # Đang di chuyển lên/xuống -> thử sang trái/phải
                        side_moves = [(0, -1), (0, 1)]
                    else:
                        # Đang di chuyển trái/phải -> thử lên/xuống
                        side_moves = [(-1, 0), (1, 0)]

                    for side_dx, side_dy in side_moves:
                        side_x = nx + side_dx
                        side_y = ny + side_dy

                        if (0 <= side_x < self.size and 
                            0 <= side_y < self.size and
                            not self.is_blocked(nx, ny, side_x, side_y) and
                            not any(p.position["x"] == side_x and 
                                   p.position["y"] == side_y 
                                   for p in self.players.values())):
                            valid_moves.append({
                                "x": side_x,
                                "y": side_y
                            })

            else:
                # Không có người chơi -> di chuyển bình thường
                valid_moves.append({
                    "x": nx,
                    "y": ny
                })

        return valid_moves

    def is_valid_move(self, player: Player, direction: Direction) -> bool:
        """
        Kiểm tra nước đi có hợp lệ không
        """
        valid_moves = self.get_valid_moves(player)
        
        # Tính vị trí mới theo hướng di chuyển
        new_pos = self.calculate_new_position(player.position, direction)
        
        # Kiểm tra vị trí mới khác vị trí hiện tại
        if (new_pos["x"] == player.position["x"] and 
        new_pos["y"] == player.position["y"]):
            return False
        
        # Kiểm tra xem vị trí mới có trong danh sách nước đi hợp lệ không
        return any(move["x"] == new_pos["x"] and 
                  move["y"] == new_pos["y"] 
                  for move in valid_moves)

    def calculate_new_position(self, position: dict, direction: Direction) -> dict:
        """
        Tính toán vị trí mới dựa trên hướng di chuyển
        """
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