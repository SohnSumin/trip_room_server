from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.rooms import rooms_bp
from routes.schedules import schedules_bp
from routes.schedules_feedback import schedules_feedback_bp
from dotenv import load_dotenv

import os

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 API 키를 가져옵니다.
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Flask 애플리케이션을 생성합니다.
app = Flask(__name__)
# 모든 출처에서의 API 요청을 허용하도록 CORS를 설정합니다.
CORS(app)

# JSON 응답이 한글을 정상적으로 표시하도록 설정합니다.
app.config['JSON_AS_ASCII'] = False
# JSON 응답을 보기 좋게 출력하도록 설정합니다.
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
# JSON 응답의 키를 정렬하지 않도록 설정합니다.
app.config['JSON_SORT_KEYS'] = False

# 각 기능별로 분리된 라우트(블루프린트)를 등록합니다.
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(rooms_bp, url_prefix="/api")
app.register_blueprint(schedules_bp, url_prefix="/api")
app.register_blueprint(schedules_feedback_bp, url_prefix="/api")

# 이 스크립트가 직접 실행될 경우에만 app.run()을 호출합니다.
# 프로덕션 환경(예: Gunicorn)에서는 이 부분이 실행되지 않습니다.
if __name__ == "__main__":
    # 환경 변수 PORT가 있으면 해당 값을, 없으면 5000을 포트로 사용합니다.
    port = int(os.environ.get("PORT", 5000))
    # 개발 서버를 0.0.0.0 호스트에서 실행하여 외부 접근을 허용합니다.
    app.run(host="0.0.0.0", port=port, debug=False)