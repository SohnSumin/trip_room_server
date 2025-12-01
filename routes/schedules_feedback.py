from flask import Blueprint, request, jsonify
from db import db
from bson import ObjectId
import requests, os, threading, traceback, json, re

schedules_feedback_bp = Blueprint("schedules_feedback", __name__)

GEMINI_MODEL = "gemini-2.5-flash"

def process_feedback(room_id: str):
    """백그라운드에서 AI 호출 및 DB 업데이트 처리"""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        schedule_doc = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule_doc:
            print(f"No schedule found for room {room_id}")
            return

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
3.  **No Changes Needed:** If the schedule is good, `feedback_message` must be a positive message, and `changes` must be an empty list.
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
        response = requests.post(gemini_api_url, headers=headers, json=body, timeout=60)
        result = response.json()

        ai_text = (
            result.get("candidates", [{}])[0]
                  .get("content", {})
                  .get("parts", [{}])[0]
                  .get("text", "")
        )

        ai_text_clean = re.sub(r"^```json|```$", "", ai_text.strip(), flags=re.MULTILINE).strip()

        try:
            feedback_data = json.loads(ai_text_clean)
        except Exception:
            feedback_data = {
                "feedback_message": ai_text.strip(),
                "changes": [],
                "improved_schedule": original_schedule,
            }

        improved_schedule = feedback_data.get("improved_schedule", original_schedule)
        mongo_schedule = {str(k): v for k, v in improved_schedule.items() if str(k).isdigit()}

        # DB 업데이트: schedule + feedback_applied + feedback_message + changes
        db.schedules.update_one(
            {"room_id": ObjectId(room_id)},
            {"$set": {
                "schedule": mongo_schedule,
                "feedback_applied": True,
                "feedback_message": feedback_data.get("feedback_message", "AI 피드백 완료"),
                "changes": feedback_data.get("changes", [])
            }}
        )

        print(f"AI feedback applied for room {room_id}")

    except Exception as e:
        traceback.print_exc()


@schedules_feedback_bp.route("/rooms/<room_id>/schedule/feedback/auto", methods=["POST"])
def auto_feedback(room_id):
    try:
        threading.Thread(target=process_feedback, args=(room_id,)).start()
        return jsonify({
            "message": "AI feedback task started, processing in background"
        }), 202
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@schedules_feedback_bp.route("/rooms/<room_id>/schedule/feedback/latest", methods=["GET"])
def get_latest_feedback(room_id):
    try:
        schedule_doc = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule_doc:
            return jsonify({"error": "No schedule found for this room"}), 404

        feedback_applied = schedule_doc.get("feedback_applied", False)
        schedule = schedule_doc.get("schedule", {})

        if feedback_applied:
            feedback_message = schedule_doc.get("feedback_message", "AI 피드백 완료")
            changes = schedule_doc.get("changes", [])
            return jsonify({
                "feedback_message": feedback_message,
                "changes": changes,
                "improved_schedule": schedule
            }), 200
        else:
            return jsonify({"message": "AI feedback is still processing"}), 202

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
