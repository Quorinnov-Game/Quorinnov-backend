from flask import Flask
from controllers.game_controller import router as game_routes
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.register_blueprint(game_routes, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True)