from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.rooms import rooms_bp
from routes.schedules import schedules_bp

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
