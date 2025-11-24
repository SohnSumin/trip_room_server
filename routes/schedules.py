from flask import Blueprint, request, jsonify, make_response
from bson import ObjectId
from util.google_utils import get_place_info
from db import db  # MongoDB 연 결
import traceback

schedules_bp = Blueprint("schedules", __name__)

def json_utf8(data, status=200):
    """UTF-8 인코딩이 보장된 jsonify 헬퍼 함수"""
    response = make_response(jsonify(data), status)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


# -----------------------
# ✅ 일정 조회 (GET)
# -----------------------
@schedules_bp.route("/rooms/<room_id>/schedule", methods=["GET"])
def get_schedule(room_id):
    try:
        schedule = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule:
            return jsonify({"error": "No schedule found for this room"}), 404

        schedule["_id"] = str(schedule["_id"])
        schedule["room_id"] = str(schedule["room_id"])
        return jsonify(schedule), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# -----------------------
# ✅ 입력값 검증 함수
# -----------------------
def validate_schedule_item(item):
    required_fields = ["title", "place", "startHour", "startMinute", "endHour", "endMinute", "color"]
    for f in required_fields:
        if f not in item:
            return f"Missing field: {f}"

    if not (0 <= item["startHour"] <= 23 and 0 <= item["endHour"] <= 23):
        return "Hour must be between 0 and 23"
    if not (0 <= item["startMinute"] <= 59 and 0 <= item["endMinute"] <= 59):
        return "Minute must be between 0 and 59"

    start_total = item["startHour"] * 60 + item["startMinute"]
    end_total = item["endHour"] * 60 + item["endMinute"]
    if end_total <= start_total:
        return "End time must be after start time"

    return None

# -----------------------
# ✅ 특정 날짜 일정 추가 (POST)
# -----------------------
# ✅ 일정 추가 시 장소 정보 Google Maps에서 가져오기
@schedules_bp.route("/rooms/<room_id>/schedule/day/<day>", methods=["POST"])
def add_schedule_item(room_id, day):
    try:
        data = request.get_json()
        item = data.get("item")

        if not item:
            return jsonify({"error": "Missing 'item'"}), 400

        # 입력값 검증
        error = validate_schedule_item(item)
        if error:
            return jsonify({"error": error}), 400

        # Google Maps에서 장소 정보 가져오기
        place_name = item.get("place")
        place_info = get_place_info(place_name)
        if not place_info:
            return jsonify({"error": f"'{place_name}' 장소를 찾을 수 없습니다."}), 404

        # placeInfo에서 name을 꺼내 최상위 place로, 내부에서는 제거
        item["place"] = place_info.get("name", place_name)
        filtered_place_info = {
            k: v for k, v in place_info.items()
            if k != "name"
        }
        item["placeInfo"] = filtered_place_info

        # DB에 저장
        db.schedules.update_one(
            {"room_id": ObjectId(room_id)},
            {"$push": {f"schedule.{day}": item}},
            upsert=True
        )

        return jsonify({
            "message": f"✅ '{item['place']}' 일정이 Day {day}에 추가되었습니다.",
            "place": item["place"],
            "placeInfo": filtered_place_info
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# -----------------------
# ✅ 특정 날짜 일정 삭제 (DELETE)
# -----------------------
@schedules_bp.route("/rooms/<room_id>/schedule/day/<day>/<int:index>", methods=["DELETE"])
def delete_schedule_item(room_id, day, index):
    try:
        schedule = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule:
            return jsonify({"error": "Schedule not found"}), 404

        day_list = schedule.get("schedule", {}).get(day, [])
        if index < 0 or index >= len(day_list):
            return jsonify({"error": "Invalid index"}), 400

        # 해당 인덱스의 일정 제거
        day_list.pop(index)
        db.schedules.update_one(
            {"room_id": ObjectId(room_id)},
            {"$set": {f"schedule.{day}": day_list}}
        )
        return jsonify({"message": f"Item {index} deleted from day {day}"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------
# ✅ 일정 삭제 (전체) (DELETE)
# -----------------------
@schedules_bp.route("/rooms/<room_id>/schedule", methods=["DELETE"])
def delete_schedule(room_id):
    try:
        result = db.schedules.delete_one({"room_id": ObjectId(room_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "No schedule found to delete"}), 404
        return jsonify({"message": "Schedule deleted successfully"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -----------------------
# ✅ 일정 수정
# -----------------------
@schedules_bp.route("/rooms/<room_id>/schedule/day/<day>/<int:index>", methods=["PUT"])
def update_schedule_item(room_id, day, index):
    try:
        data = request.get_json()
        new_item = data.get("item")
        if not new_item:
            return jsonify({"error": "Missing 'item' data"}), 400

        # 검증
        error = validate_schedule_item(new_item)
        if error:
            return jsonify({"error": error}), 400

        schedule = db.schedules.find_one({"room_id": ObjectId(room_id)})
        if not schedule:
            return jsonify({"error": "Schedule not found"}), 404

        schedule_data = schedule.get("schedule", {})
        day_list = schedule_data.get(day, [])

        if index < 0 or index >= len(day_list):
            return jsonify({"error": "Invalid index"}), 400

        old_item = day_list[index]
        old_place = old_item.get("place")
        new_place = new_item.get("place")

        # ✅ 장소가 바뀐 경우
        if new_place and new_place != old_place:
            from util.google_utils import get_place_info
            place_info = get_place_info(new_place)
            if not place_info:
                return jsonify({"error": f"'{new_place}' 장소를 찾을 수 없습니다."}), 404

            new_item["place_info"] = place_info
            new_item["place"] = place_info["name"]
        else:
            new_item["place_info"] = old_item.get("place_info", {})

        # ✅ 수정 반영
        day_list[index] = new_item
        db.schedules.update_one(
            {"room_id": ObjectId(room_id)},
            {"$set": {f"schedule.{day}": day_list}}
        )

        return jsonify({
            "message": f"✅ Item {index} on day {day} updated successfully",
            "place_info": new_item.get("place_info")
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
