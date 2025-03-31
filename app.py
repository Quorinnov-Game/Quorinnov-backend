from fastapi import FastAPI
from controllers import game_controller
import models.board, models.player, models.wall
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(game_controller.router)
