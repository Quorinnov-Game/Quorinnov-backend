from sqlalchemy import Column, Integer, String
from database import Base
from .wall import Wall
from .player import Player
from .enums import Orientation, Direction

class Board:
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

        # Kiểm tra giới hạn
        if orientation == Orientation.HORIZONTAL:
            if not (0 <= x < self.size - 1 and 0 < y < self.size):
                return False
        elif orientation == Orientation.VERTICAL:
            if not (0 < x < self.size and 0 <= y < self.size - 1):
                return False

        # Kiểm tra trùng vị trí
        for w in self.walls:
            if w.x == x and w.y == y and w.orientation == orientation:
                return False

        # Kiểm tra giao nhau (như frontend đã làm)
        for w in self.walls:
            if (
                    orientation == Orientation.HORIZONTAL and w.orientation == Orientation.VERTICAL and
                    x == w.x - 1 and y == w.y + 1
            ):
                return False
            elif (
                    orientation == Orientation.VERTICAL and w.orientation == Orientation.HORIZONTAL and
                    x == w.x + 1 and y == w.y - 1
            ):
                return False

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

           for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
               nx, ny = x + dx, y + dy
               if not (0 <= nx < self.size and 0 <= ny < self.size):
                   continue
               if (nx, ny) in visited:
                   continue
               if self.is_blocked(x, y, nx, ny):  # kiểm tra có bị chắn bởi tường không
                   continue
               queue.append((nx, ny))
        return False  # không tới được hàng đích
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