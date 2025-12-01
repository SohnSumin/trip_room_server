from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.rooms import rooms_bp
from routes.schedules import schedules_bp
from routes.schedules_feedback import schedules_feedback_bp
from dotenv import load_dotenv

import os

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = Flask(__name__)

CORS(app)

app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSON_SORT_KEYS'] = False

app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(rooms_bp, url_prefix="/api")
app.register_blueprint(schedules_bp, url_prefix="/api")
app.register_blueprint(schedules_feedback_bp, url_prefix="/api")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)