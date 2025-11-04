from flask import Blueprint, request, jsonify, make_response
from bson import ObjectId
from datetime import datetime, timezone
from db import db, users

rooms_bp = Blueprint("rooms", __name__)

def json_utf8(data, status=200):
    """UTF-8 인코딩이 보장된 jsonify 헬퍼 함수"""
    response = make_response(jsonify(data), status)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


# ✅ 방 생성
@rooms_bp.route("/rooms", methods=["POST"])
def create_room():
    data = request.get_json()
    required = ["title", "country", "startDate", "endDate", "ownerId"]
    if not all(k in data and data[k] for k in required):
        return jsonify({"error": "Missing fields"}), 400

    try:
        owner_oid = ObjectId(data["ownerId"])
    except:
        return jsonify({"error": "Invalid ownerId"}), 400

    room = {
        "title": data["title"],
        "country": data["country"],
        "startDate": data["startDate"],
        "endDate": data["endDate"],
        "ownerId": owner_oid,
        "members": [owner_oid],
        "pendingInvites": [],
        "createdAt": datetime.now(timezone.utc)
    }
    
    result = db.rooms.insert_one(room)
    room["_id"] = str(result.inserted_id)
    room["ownerId"] = str(room["ownerId"])
    room["members"] = [str(m) for m in room["members"]]
    room["pendingInvites"] = [str(p) for p in room["pendingInvites"]]
    return jsonify(room), 201

# ✅ 방 삭제
@rooms_bp.route("/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id):
    result = db.rooms.delete_one({"_id": ObjectId(room_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"status": "deleted"}), 200

# ✅ 방 정보 업데이트
@rooms_bp.route("/rooms/<room_id>", methods=["PUT"])
def update_room(room_id):
    data = request.get_json()
    update_data = {}

    for field in ["title", "country", "startDate", "endDate"]:
        if field in data and data[field]:
            update_data[field] = data[field]

    if not update_data:
        return jsonify({"error": "Nothing to update"}), 400

    result = db.rooms.update_one({"_id": ObjectId(room_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return jsonify({"error": "Room not found"}), 404

    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    room["_id"] = str(room["_id"])
    room["ownerId"] = str(room["ownerId"])
    room["members"] = [str(m) for m in room["members"]]
    room["pendingInvites"] = [str(p) for p in room.get("pendingInvites", [])]
    return jsonify(room), 200

# ✅ 내가 속한 방 보기
@rooms_bp.route("/rooms/user/<user_id>", methods=["GET"])
def get_user_rooms(user_id):
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify([]), 200

    rooms = list(db.rooms.find({"members": user_oid}))
    for r in rooms:
        r["_id"] = str(r["_id"])
        r["ownerId"] = str(r["ownerId"])
        r["members"] = [str(m) for m in r["members"]]
        r["pendingInvites"] = [str(p) for p in r.get("pendingInvites", [])]
    return jsonify(rooms), 200

# ✅ 초대된 방 보기
@rooms_bp.route("/rooms/invited/<user_id>", methods=["GET"])
def get_invited_rooms(user_id):
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify([]), 200

    rooms = list(db.rooms.find({"pendingInvites": user_oid}))
    for r in rooms:
        r["_id"] = str(r["_id"])
        r["ownerId"] = str(r["ownerId"])
        r["members"] = [str(m) for m in r["members"]]
        r["pendingInvites"] = [str(p) for p in r.get("pendingInvites", [])]
    return jsonify(rooms), 200

# ✅ 방 초대
@rooms_bp.route("/rooms/<room_id>/invite", methods=["POST"])
def invite_member(room_id):
    data = request.get_json()
    user_id = data.get("userId")  # 클라에서 보낸 가입 ID

    if not user_id:
        return jsonify({"error": "userId is required"}), 400

    # 1. 가입 ID 기준으로 사용자 조회
    user_doc = users.find_one({"id": user_id})
    if not user_doc:
        return jsonify({"error": "User not found"}), 404

    user_oid = user_doc["_id"]  # ObjectId를 가져옴

    # 2. 방 존재 여부 확인
    try:
        room_oid = ObjectId(room_id)
    except:
        return jsonify({"error": "Invalid roomId"}), 400

    room = db.rooms.find_one({"_id": room_oid})
    if not room:
        return jsonify({"error": "Room not found"}), 404

    # 3. 이미 멤버인지 확인
    if user_oid in room["members"]:
        return jsonify({"error": "Already a member"}), 400

    # 4. 이미 초대되었는지 확인
    if user_oid in room.get("pendingInvites", []):
        return jsonify({"error": "Already invited"}), 400

    # 5. 초대 전송 (DB에는 ObjectId로 저장)
    db.rooms.update_one(
        {"_id": room_oid},
        {"$push": {"pendingInvites": user_oid}}
    )
    return jsonify({"status": "invite sent"}), 200


# ✅ 방 상세 정보 보기
@rooms_bp.route("/rooms/<room_id>", methods=["GET"])
def get_room_detail(room_id):
    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return jsonify({"error": "Room not found"}), 404

    room["_id"] = str(room["_id"])
    room["ownerId"] = str(room["ownerId"])
    room["members"] = [str(m) for m in room["members"]]
    room["pendingInvites"] = [str(p) for p in room.get("pendingInvites", [])]
    return jsonify(room), 200

# ✅ 초대 수락
@rooms_bp.route("/rooms/<room_id>/accept", methods=["POST"])
def accept_invite(room_id):
    data = request.get_json()
    user_id = data.get("userId")

    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid userId"}), 400

    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room or user_oid not in room.get("pendingInvites", []):
        return jsonify({"error": "No pending invite"}), 404

    db.rooms.update_one(
        {"_id": ObjectId(room_id)},
        {
            "$pull": {"pendingInvites": user_oid},
            "$push": {"members": user_oid}
        }
    )
    return jsonify({"status": "joined"}), 200

# ✅ 초대 거절
@rooms_bp.route("/rooms/<room_id>/decline", methods=["POST"])
def decline_invite(room_id):
    data = request.get_json()
    user_id = data.get("userId")
    
    try:
        user_oid = ObjectId(user_id)
    except:
        return jsonify({"error": "Invalid userId"}), 400

    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room or user_oid not in room.get("pendingInvites", []):
        return jsonify({"error": "No pending invite"}), 404
    
    db.rooms.update_one(
        {"_id": ObjectId(room_id)},
        {"$pull": {"pendingInvites": user_oid}}
    )
    return jsonify({"status": "invite declined"}), 200

# ✅ 방장 변경
@rooms_bp.route("/rooms/<room_id>/change_owner", methods=["POST"])
def change_owner(room_id):
    data = request.get_json()
    new_owner_id = data.get("newOwnerId")
    user = users.find_one({"id": new_owner_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    new_owner_oid = user["_id"]

    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return jsonify({"error": "Room not found"}), 404
    if new_owner_oid not in room["members"]:
        return jsonify({"error": "New owner must be a member"}), 400
    
    db.rooms.update_one(
        {"_id": ObjectId(room_id)},
        {"$set": {"ownerId": new_owner_oid}}
    )
    return jsonify({"status": "owner changed"}), 200

# ✅ 멤버 제거
@rooms_bp.route("/rooms/<room_id>/remove_member", methods=["POST"])
def remove_member(room_id):
    data = request.get_json()
    user_id = data.get("userId")
    user = users.find_one({"id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_oid = user["_id"]

    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return jsonify({"error": "Room not found"}), 404
    if user_oid == room["ownerId"]:
        return jsonify({"error": "Cannot remove the owner"}), 400
    if user_oid not in room["members"]:
        return jsonify({"error": "User not in members"}), 404
    
    db.rooms.update_one(
        {"_id": ObjectId(room_id)},
        {"$pull": {"members": user_oid}}
    )
    return jsonify({"status": "member removed"}), 200

# ✅ 방 멤버 조회
@rooms_bp.route("/rooms/<room_id>/members", methods=["GET"])
def get_room_members(room_id):
    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return jsonify({"error": "Room not found"}), 404

    members_info = []
    for member_oid in room.get("members", []):
        user = users.find_one({"_id": member_oid})
        if user:
            members_info.append({
                "id": user["id"],
                "nickname": user.get("nickname", "")
            })

    return jsonify(members_info), 200