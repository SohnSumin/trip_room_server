from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.rooms import rooms_bp
from routes.schedules import schedules_bp
from dotenv import load_dotenv

import os
import os

load_dotenv()  # .env 파일이 있을 경우 자동 로드

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


app = Flask(__name__)
CORS(app)

app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSON_SORT_KEYS'] = False

# Blueprint 등록
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(rooms_bp, url_prefix="/api")
app.register_blueprint(schedules_bp, url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
