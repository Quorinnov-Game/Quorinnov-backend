from models.board import Board
from models.wall import Wall
from models.player import Player

class GameService:
    def __init__(self):
        # We keep only one game board in memory for demonstration.
        # In a real application, you might manage multiple boards or games at once.
        self.board = None

    def init_game(self):
        """
        Creates a new 9x9 board and initializes two players at their default positions.
        Returns the initial state (as a dictionary).
        """
        self.board = Board(size=9)
        self.board.init_default_players()
        return self.board.to_dict()

    def move_player(self, player_id, direction):
        """
        Moves the specified player (player_id) in the given direction
        ('up', 'down', 'left', or 'right').

        This method checks if the game board is initialized, finds the correct player,
        and applies the movement if it's within board boundaries.
        Currently, it does not fully account for walls (no wall-blocking logic yet).
        """
        if not self.board:
            return {"error": "Game not initialized."}

        # Locate the player with the given player_id
        current_player = None
        for p in self.board.players:
            if p.player_id == player_id:
                current_player = p
                break

        if not current_player:
            return {"error": f"Player {player_id} not found."}

        # Determine movement offsets
        delta_row, delta_col = 0, 0
        if direction == 'up':
            delta_row = -1
        elif direction == 'down':
            delta_row = 1
        elif direction == 'left':
            delta_col = -1
        elif direction == 'right':
            delta_col = 1

        new_row = current_player.row + delta_row
        new_col = current_player.col + delta_col

        # Check if the new position is within board limits
        if 0 <= new_row < self.board.size and 0 <= new_col < self.board.size:
            # TODO: Add logic to check if a wall is blocking movement.
            # For now, assume no wall is blocking.
            current_player.row = new_row
            current_player.col = new_col

        return self.board.to_dict()

    def place_wall(self, player_id, row, col, orientation):
        """
        Places a wall at the specified board location (row, col) with the given orientation
        ('H' for horizontal or 'V' for vertical).

        Checks if the game is initialized, locates the correct player, and ensures
        they have walls remaining. Currently, this does not fully validate whether
        placing the wall blocks all possible paths.
        """
        if not self.board:
            return {"error": "Game not initialized."}

        # Locate the player
        current_player = None
        for p in self.board.players:
            if p.player_id == player_id:
                current_player = p
                break

        if not current_player:
            return {"error": f"Player {player_id} not found."}

        # Check if the player still has walls left
        if current_player.walls_remaining <= 0:
            return {"error": "No walls remaining for this player."}

        # TODO: Check row, col, orientation for validity (and ensure it doesn't block all paths).
        # For now, we place the wall without full validation.
        new_wall = Wall(row=row, col=col, orientation=orientation)
        self.board.walls.append(new_wall)

        # Decrement the player's wall count
        current_player.walls_remaining -= 1

        return self.board.to_dict()

    def get_current_state(self):
        """
        Returns the current state of the board as a dictionary, which includes
        board size, player positions, and any walls placed.
        """
        if not self.board:
            return {"error": "Game not initialized."}
        return self.board.to_dict()
