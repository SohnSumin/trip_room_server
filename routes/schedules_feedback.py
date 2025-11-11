from flask import Blueprint, request, jsonify
from db import db
from bson import ObjectId
import requests, os, traceback, json, re

schedules_feedback_bp = Blueprint("schedules_feedback", __name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

@schedules_feedback_bp.route("/rooms/<room_id>/schedule/feedback/auto", methods=["POST"])
def auto_feedback(room_id):
    try:
        schedule_doc = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule_doc:
            return jsonify({"error": "No schedule found for this room"}), 404

        schedule_json = json.dumps(schedule_doc.get("schedule", {}), ensure_ascii=False, indent=2)

        prompt = f"""
You are an expert travel planner AI assistant.
Your job is to carefully review and slightly optimize the user's multi-day travel schedule.

Guidelines:
1. Review the user's provided schedule JSON.
2. Identify only clear issues such as overlapping times, excessive travel distance, or unbalanced days.
3. DO NOT add entirely new activities or places that were not in the original schedule.
4. If there are no meaningful improvements, simply state that there are no significant issues.
5. Answer in Korean (한국어로 작성).

Return your output in **strict JSON** format:
{{
  "feedback_message": "요약 및 개선 설명 (개선사항이 없으면 '현재 일정은 전반적으로 잘 구성되어 있으며 별다른 개선사항이 없습니다.' 라고 작성)",
  "changes": ["2일차: 이동 시간 조정", "3일차: 점심 시간 수정", "..."],
  "improved_schedule": {{ }}  // 개선된 일정 (없으면 기존 일정 그대로 반환)
}}

Schedule JSON:
{schedule_json}
"""

        headers = {"Content-Type": "application/json"}
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

        response = requests.post(GEMINI_API_URL, headers=headers, json=body)
        result = response.json()

        ai_text = (
            result.get("candidates", [{}])[0]
                  .get("content", {})
                  .get("parts", [{}])[0]
                  .get("text", "")
        )

        # 🧹 1️⃣ 코드 블록(```json ... ```) 제거
        ai_text_clean = re.sub(r"^```json|```$", "", ai_text.strip(), flags=re.MULTILINE).strip()

        # 🧠 2️⃣ JSON 파싱 시도
        try:
            feedback_data = json.loads(ai_text_clean)
        except Exception:
            feedback_data = {
                "feedback_message": ai_text.strip(),
                "changes": [],
                "improved_schedule": None
            }

        improved_schedule = feedback_data.get("improved_schedule")

        # 🔢 3️⃣ 내부 로직에서는 int key로 사용
        if isinstance(improved_schedule, dict):
            improved_schedule = {int(k): v for k, v in improved_schedule.items() if k.isdigit()}

        # 💾 4️⃣ DB 저장용으로 string key 변환
        mongo_schedule = {str(k): v for k, v in improved_schedule.items()} if improved_schedule else None

        # ✅ 5️⃣ DB 업데이트 (MongoDB는 string key만 허용)
        if mongo_schedule:
            db.schedules.update_one(
                {"room_id": ObjectId(room_id)},
                {"$set": {"schedule": mongo_schedule}}
            )

        return jsonify({
            "message": "AI feedback applied and schedule updated successfully",
            "feedback_message": feedback_data.get("feedback_message"),
            "changes": feedback_data.get("changes"),
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
