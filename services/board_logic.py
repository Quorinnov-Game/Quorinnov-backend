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