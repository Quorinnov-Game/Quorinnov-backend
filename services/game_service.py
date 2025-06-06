
from sqlalchemy.orm import Session
from models.board import Board
from models.player import Player
from models.wall import Wall
from models.enums import Direction
from models.state import State
from .board_logic import GameBoard
from models.turns import Turn
import copy
from services.ai_service import RandomAI, BasicAI, AdvancedAI


class GameService:
    def __init__(self, db: Session):
        self.db = db

    def create_game(self, player1: dict, player2: dict):
        # Crée une nouvelle partie :
        # - Supprime toutes les anciennes données (joueurs, murs, plateau, tours)
        # - Crée un nouvel état du jeu et un nouveau plateau
        # - Ajoute les deux joueurs avec leurs positions et murs restants

        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.query(Turn).delete()
        self.db.commit()

        # Create empty state
        state_obj = State(playerA=[], playerB=[])
        self.db.add(state_obj)
        self.db.flush() # Flush để lấy ID của state trước khi commit

        # Create new game (board)
        board_obj = Board(state_id=state_obj.id, width=9, height=9)
        self.db.add(board_obj)
        self.db.flush()

        # Create players with fixed ID
        player1_obj = Player(
            id=1,
            # board_id=board_obj.id,
            color=player1["color"],
            position=player1["position"],
            direction="up",
            walls_left=player1["walls_left"]
        )
        player2_obj = Player(
            id=2,
            # board_id=board_obj.id,
            color=player2["color"],
            position=player2["position"],
            direction="down",
            walls_left=player2["walls_left"]
        )
        self.db.add_all([player1_obj, player2_obj])
        self.db.commit()

        # Refresh the board object
        self.db.refresh(board_obj)

        return board_obj

    def get_player(self, player_id: int) -> Player:
        return self.db.query(Player).filter(Player.id == player_id).first()

    def get_board_and_state(self):
        board = self.db.query(Board).first()
        if not board:
            return None, None, None
        state = self.db.query(State).filter(State.id == board.state_id).first()
        walls = self.db.query(Wall).all()
        return board, state, walls

    def move_player_logic_backup(self, player_id: int, direction: str) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board, state, walls = self.get_board_and_state()
        if not board or not state:
            return False

        players = self.db.query(Player).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        if not board_logic.is_valid_move(player, direction):
            return False

        # Update player position
        player.position = board_logic.calculate_new_position(player.position, direction)

        # Log the move to state
        self.log_action_to_state(player_id, {"type": "player", "direction": direction})
        self.db.commit()
        return True
    def move_player(self, player_id: int, x: int, y: int) -> bool:
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        state = self.db.query(State).filter(State.id == board.state_id).first()
        if not state:
            return False

        # no init position player
        # only write log in state
        self.log_action_to_state(player_id, {
            "type": "player",
            "position": {"x": x, "y": y}
        })

        player.position = {"x": x, "y": y}
        self.db.add(player)
        self.db.commit()
        
        # Log to Turn table
        self.update_turn()
        return True


    def place_wall(self, player_id: int, x: int, y: int, orientation: str, is_valid: bool) -> bool:
        print(f"[place_wall] Request from player {player_id} to place at ({x}, {y}) - {orientation}, confirmed: {is_valid}")

        player = self.get_player(player_id)
        if not player:
            print("[place_wall] Failed: player not found")
            return False
        if player.walls_left <= 0:
            print("[place_wall] Failed: no walls left")
            return False

        board_data = self.db.query(Board).first()
        if not board_data:
            print("[place_wall] Failed: no board")
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()
        state = self.db.query(State).filter(State.id == board_data.state_id).first()

        board_logic = GameBoard(size=board_data.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        new_wall = Wall(x=x, y=y, orientation=orientation, player_id=player_id, is_valid=is_valid)

        if not board_logic._is_valid_wall(new_wall):
            print("[place_wall] Failed: wall not valid by logic")
            return False

        if is_valid:
            print("[place_wall] Confirmed wall placed")
            self.db.add(new_wall)
            player.walls_left -= 1

            self.log_action_to_state(player_id, {
                "type": "wall",
                "x": x,
                "y": y,
                "orientation": orientation
            })

            self.update_turn()


            self.db.commit()
        else:
            print("[place_wall] Wall not confirmed, skipping DB write and log")

        return True

    def is_valid_wall(self, player_id: int, x: int, y: int, orientation: str) -> bool:
        # Vérifie si le mur est autorisé à cette position selon les règles (ne bloque pas complètement l’adversaire, etc.)
        player = self.get_player(player_id)
        if not player:
            return False

        board, _, walls = self.get_board_and_state()
        if not board:
            return False

        players = self.db.query(Player).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        test_wall = Wall(x=x, y=y, orientation=orientation, player_id=player_id)
        return board_logic._is_valid_wall(test_wall)

    def reset_game(self):
        # Réinitialise totalement la partie en supprimant tous les éléments : joueurs, murs, plateau et historique
        self.db.query(Wall).delete()
        self.db.query(Player).delete()
        self.db.query(Board).delete()
        self.db.query(Turn).delete()
        self.db.commit()


    def check_winner(self) -> str:
        # Vérifie si un des joueurs a gagné (atteint la ligne d’arrivée selon sa direction)
        # Retourne le nom du joueur gagnant ou une chaîne vide sinon
        players = self.db.query(Player).all()
        board = self.db.query(Board).first()
        if not board:
            return ""

        walls = self.db.query(Wall).all()
        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        for player in players:
            if board_logic.has_path(player):
                if player.direction == Direction.UP and player.position["x"] == 0:
                    return player.name
                elif player.direction == Direction.DOWN and player.position["x"] == board.height - 1:
                    return player.name
        return ""



    def log_action_to_state(self, player_id: int, action: dict):
        # Enregistre une action (déplacement ou pose de mur) dans la liste des actions du joueur (dans l’état)
        player = self.get_player(player_id)
        if not player:
            return

        board = self.db.query(Board).first()
        if not board:
            return

        state = self.db.query(State).filter(State.id == board.state_id).first()
        if not state:
            return

        if player_id == 1:
            new_log = copy.deepcopy(state.playerA)
            new_log.append(action)
            state.playerA = new_log
        elif player_id == 2:
            new_log = copy.deepcopy(state.playerB)
            new_log.append(action)
            state.playerB = new_log

        self.db.commit()

    def perform_action(self, player_id: int, action: dict) -> bool:
        # Exécute une action (soit déplacement, soit mur) en fonction de son type
        # Valide l’action, met à jour le joueur, et l’enregistre dans l’état
        player = self.get_player(player_id)
        if not player:
            return False

        board = self.db.query(Board).first()
        if not board:
            return False

        players = self.db.query(Player).all()
        walls = self.db.query(Wall).all()

        board_logic = GameBoard(size=board.width)
        board_logic.set_players({p.id: p for p in players})
        board_logic.walls = walls

        if action["type"] == "player":
            direction = action["direction"]
            if board_logic.is_valid_move(player, direction):
                new_pos = board_logic.calculate_new_position(player.position, direction)
                player.position = new_pos
                self.log_action_to_state(player_id, {"player": new_pos})
                self.db.commit()
                return True

        elif action["type"] == "wall":
            x, y, orientation = action["x"], action["y"], action["orientation"]

            if player.walls_left <= 0:
                return False

            new_wall = Wall(x=x, y=y, orientation=orientation, player_id=player_id)
            if board_logic.add_wall(new_wall):
                self.db.add(new_wall)
                player.walls_left -= 1
                self.log_action_to_state(player_id, {
                    "wall": {
                        "x": x,
                        "y": y,
                        "orientation": orientation
                    }
                })
                self.db.commit()
                return True

        return False
    def update_turn(self):
        # Sauvegarde l’état actuel des positions des deux joueurs et de tous les murs dans la table des tours (Turn)
        turn_count = self.db.query(Turn).count()
        player1 = self.get_player(1)
        player2 = self.get_player(2)
        walls = self.db.query(Wall).all()

        wall_list = [wall.to_dict() for wall in walls]

        current_turn = Turn(
            id=turn_count + 1,
            position={
                "player1": player1.position,
                "player2": player2.position
            },
            walls=wall_list
        )

        self.db.add(current_turn)
        self.db.commit()



    def ia_play(self, game_id: int, difficulty: int):
        print(f"[ia_play] Starting with difficulty: {difficulty}")
        
        try:
            # Conversion de la difficulté numérique en format texte
            difficulty_map = {
                1: "random",
                2: "basic", 
                3: "advanced",
                4: "advanced"
            }
            
            if difficulty not in difficulty_map:
                raise ValueError(f"Difficulty {difficulty} not supported")
                
            ai_difficulty = difficulty_map[difficulty]
            
            # Toujours le joueur 2 pour l'IA
            player = self.get_player(2)
            if not player:
                raise ValueError("IA player (ID 2) not found")
            
            # Initialisation de l'IA appropriée
            if ai_difficulty == "random":
                ai = RandomAI(self, player.id)
            elif ai_difficulty == "basic":
                ai = BasicAI(self, player.id)
            else:
                ai = AdvancedAI(self, player.id)
            
            # Choix du mouvement
            move = ai.choose_move()
            if not move:
                raise ValueError("AI couldn't choose a valid move")
                
            print(f"[ia_play] AI chose move: {move}")
            
            # Exécution du mouvement
            if move["type"] == "player":
                success = self.move_player(
                    player.id, 
                    move["position"]["x"], 
                    move["position"]["y"]
                )
            else:
                success = self.place_wall(
                    player.id,
                    move["x"],
                    move["y"],
                    move["orientation"],
                    True
                )
                
            if not success:
                raise ValueError("Move execution failed")
            
            # Construction de la réponse
            response = {
                "success": True,
                "action": move["type"],
                "difficulty": difficulty,
                "x": move["position"]["x"] if move["type"] == "player" else move["x"],
                "y": move["position"]["y"] if move["type"] == "player" else move["y"],
                "new_position": move.get("position")
            }
            
            if move["type"] == "wall":
                response["orientation"] = move["orientation"]
                
            print(f"[ia_play] Response: {response}")
            return response
            
        except Exception as e:
            print(f"[ia_play] Error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "action": None
            }
            
    def get_all_players(self):
        """Lấy tất cả players từ database"""
        try:
            return self.db.query(Player).all()
        except Exception as e:
            print(f"Error querying players: {str(e)}")
            return []
    