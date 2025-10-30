from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.rooms import room_bp

app = Flask(__name__)
CORS(app)

# Blueprint 등록
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(room_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
