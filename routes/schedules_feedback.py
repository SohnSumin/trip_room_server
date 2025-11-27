from flask import Blueprint, request, jsonify
from db import db
from bson import ObjectId
import requests, os, traceback, json, re

schedules_feedback_bp = Blueprint("schedules_feedback", __name__)

GEMINI_MODEL = "gemini-2.5-flash"
@schedules_feedback_bp.route("/rooms/<room_id>/schedule/feedback/auto", methods=["POST"])
def auto_feedback(room_id):
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        schedule_doc = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule_doc:
            return jsonify({"error": "No schedule found for this room"}), 404

        original_schedule = schedule_doc.get("schedule", {})

        # --- 프롬프트 최적화를 위한 데이터 가공 ---
        simplified_schedule_str = ""
        for day, items in sorted(original_schedule.items()):
            simplified_schedule_str += f"Day {day}:\n"
            if not items:
                simplified_schedule_str += "  - (No schedule)\n"
                continue
            for item in items:
                place_info = item.get("placeInfo", {})
                lat = place_info.get("lat", "N/A")
                lng = place_info.get("lng", "N/A")
                simplified_schedule_str += f"  - {item['startHour']}:{item['startMinute']:02d} ~ {item['endHour']}:{item['endMinute']:02d}: {item['place']} (lat: {lat}, lng: {lng})\n"
        # -----------------------------------------

        prompt = f"""
You are a world-class travel planner AI. Your task is to optimize the user's travel schedule for realism and efficiency.

**Analysis Data:**
I will provide the original schedule in a simplified text format, including place names, times, and coordinates (lat, lng).
I will also provide the full schedule in JSON format. You MUST use the full JSON to reconstruct the `improved_schedule`.

**Strict Guidelines:**
1.  **Analyze Route:** Use the coordinates to check if travel times between locations are realistic. Identify inefficient routes or impossible schedules.
2.  **Optimize:** Suggest changes ONLY for clear issues (e.g., unrealistic travel time, inefficient order). DO NOT add new places.
3.  **No Changes Needed:** If the schedule is good, `feedback_message` must be a positive message (e.g., "현재 일정은 이동 경로와 시간 분배가 효율적으로 잘 구성되어 있습니다. 즐거운 여행 되세요!"), and `changes` must be an empty list.
4.  **Language:** Your entire response MUST be in Korean.

**Output Format (Strictly JSON only, no other text):**
{{
  "feedback_message": "A summary of the analysis and improvements in Korean.",
  "changes": ["A list of specific changes made, in Korean."],
  "improved_schedule": {{ }}  // The complete, optimized schedule in the original JSON format. If no changes, return the original schedule.
}}

**Simplified Schedule for Analysis:**
{simplified_schedule_str}

**Full Original Schedule JSON for Reconstructing Output:**
{json.dumps(original_schedule, ensure_ascii=False, indent=2)}
"""

        headers = {"Content-Type": "application/json"}
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

        gemini_api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        response = requests.post(gemini_api_url, headers=headers, json=body)
        result = response.json()

        ai_text = (
            result.get("candidates", [{}])[0]
                  .get("content", {})
                  .get("parts", [{}])[0]
                  .get("text", "")
        )


        # 1. 코드 블록(```json ... ```) 제거
        ai_text_clean = re.sub(r"^```json|```$", "", ai_text.strip(), flags=re.MULTILINE).strip()

        # 2. JSON 파싱 시도
        try:
            feedback_data = json.loads(ai_text_clean)
        except Exception:
            feedback_data = {
                "feedback_message": ai_text.strip(),
                "changes": [],
                "improved_schedule": None,
            }

        improved_schedule = feedback_data.get("improved_schedule")

        # 3. 내부 로직에서는 int key로 사용
        if isinstance(improved_schedule, dict):
            improved_schedule = {int(k): v for k, v in improved_schedule.items() if k.isdigit()}

        # 4. DB 저장용으로 string key 변환
        mongo_schedule = {str(k): v for k, v in improved_schedule.items()} if improved_schedule else None

        # 5. DB 업데이트 (MongoDB는 string key만 허용)
        if mongo_schedule:
            db.schedules.update_one(
                {"room_id": ObjectId(room_id)},
                {"$set": {"schedule": mongo_schedule}}
            )

        return jsonify({
            "message": "AI feedback applied and schedule updated successfully",
            "feedback_message": feedback_data.get("feedback_message"),
            "changes": feedback_data.get("changes"),
            "debug_prompt": prompt,
            "debug_raw_gemini_response": result,
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
