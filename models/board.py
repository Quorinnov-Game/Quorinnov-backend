class Board:
    """
    board Quoridor (9x9).
    save list players, walls, ...
    """
    def __init__(self, size=9):
        self.size = size          # kích thước ví dụ 9x9
        self.players = []         # danh sách Player
        self.walls = []           # danh sách Wall

    def init_default_players(self):
        """
        Init 2 players on position default:
          - Player 1: on top (row=0)
          - Player 2: on bottom (row=size-1)
        """
        from models.player import Player

        # in center of board (col = size//2)
        p1 = Player(player_id=1, row=0, col=self.size // 2, walls_remaining=10)
        p2 = Player(player_id=2, row=self.size - 1, col=self.size // 2, walls_remaining=10)

        self.players = [p1, p2]

    def to_dict(self):
        """
         return in dict for  jsonify response.
        """
        return {
            "size": self.size,
            "players": [p.to_dict() for p in self.players],
            "walls": [w.to_dict() for w in self.walls]
        }
