class Player:
    """
    save infor about the playerQuoridor.
    """
    def __init__(self, player_id, row, col, walls_remaining=10):
        self.player_id = player_id
        self.row = row      # line board
        self.col = col      # column
        self.walls_remaining = walls_remaining

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "row": self.row,
            "col": self.col,
            "walls_remaining": self.walls_remaining
        }
