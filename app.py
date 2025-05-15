from flask import Flask
from flask_cors import CORS
from controllers.game_controller import router as game_routes
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"])
app.register_blueprint(game_routes, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=True)