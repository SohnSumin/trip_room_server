from flask import Blueprint, request, jsonify, make_response, send_file
from bson import ObjectId
from datetime import datetime, timezone
from routes.schedules import delete_schedule
from db import db, users, fs
from gridfs.errors import NoFile
from werkzeug.datastructures import FileStorage

rooms_bp = Blueprint("rooms", __name__)

# 방 생성
@rooms_bp.route("/rooms", methods=["POST"])
def create_room():
    data = request.form
    required = ["title", "country", "startDate", "endDate", "creatorId"]
    if not all(k in data and data[k] for k in required):
        return jsonify({"error": "Missing fields"}), 400

    try:
        owner_oid = ObjectId(data["creatorId"])
    except:
        return jsonify({"error": "Invalid creatorId"}), 400

    image_id = None
    if 'image' in request.files:
        image_file: FileStorage = request.files['image']
        # GridFS에 이미지 저장하고 파일 ID를 얻음
        image_id = fs.put(image_file, filename=image_file.filename, content_type=image_file.content_type)

    room = {
        "title": data["title"],
        "country": data["country"],
        "startDate": data["startDate"],
        "endDate": data["endDate"],
        "ownerId": owner_oid, # 방장은 ownerId로 저장
        "members": [owner_oid],
        "pendingInvites": [],
        "createdAt": datetime.now(timezone.utc),
        "imageId": image_id # 이미지 파일 ID 저장
    }
    
    result = db.rooms.insert_one(room)
    room["_id"] = str(result.inserted_id)
    room["ownerId"] = str(room["ownerId"])
    if room["imageId"]:
        room["imageId"] = str(room["imageId"])
    room["members"] = [str(m) for m in room["members"]]
    room["pendingInvites"] = [str(p) for p in room["pendingInvites"]]
    return jsonify(room), 201

# 이미지 파일 제공
@rooms_bp.route("/images/<image_id>", methods=["GET"])
def get_image(image_id):
    try:
        # GridFS에서 이미지 파일 가져오기
        grid_out = fs.get(ObjectId(image_id))
        # send_file을 사용하여 이미지 응답 생성
        return send_file(
            grid_out,
            mimetype=grid_out.content_type
        )
    except NoFile:
        return jsonify({"error": "Image not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 방 삭제
@rooms_bp.route("/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id):
    result = db.rooms.delete_one({"_id": ObjectId(room_id)})
    delete_schedule(room_id)  # 방 삭제 시 일정도 함께 삭제
    if result.deleted_count == 0:
        return jsonify({"error": "Room not found"}), 404
    return jsonify({"status": "deleted"}), 200

# 방 정보 업데이트
@rooms_bp.route("/rooms/<room_id>", methods=["PUT"])
def update_room(room_id):
    # multipart/form-data를 처리하기 위해 request.form 사용
    if request.is_json:
        data = request.get_json()
    else: # multipart/form-data 또는 다른 형식
        data = request.form

    update_data = {}

    for field in ["title", "country", "startDate", "endDate"]:
        if field in data and data[field]:
            update_data[field] = data[field]

    # 이미지 파일이 있는지 확인
    if 'image' in request.files:
        image_file: FileStorage = request.files['image']
        
        # 기존 이미지 삭제 (선택적)
        room_to_update = db.rooms.find_one({"_id": ObjectId(room_id)})
        if room_to_update and room_to_update.get("imageId"):
            try:
                fs.delete(room_to_update["imageId"])
            except Exception as e:
                print(f"Error deleting old image: {e}")

        # 새 이미지 저장
        image_id = fs.put(image_file, filename=image_file.filename, content_type=image_file.content_type)
        update_data["imageId"] = image_id

    if not update_data and 'image' not in request.files:
        return jsonify({"error": "Nothing to update"}), 400

    result = db.rooms.update_one({"_id": ObjectId(room_id)}, {"$set": update_data})
    if result.matched_count == 0:
        return jsonify({"error": "Room not found"}), 404
    
    return get_room_detail(room_id) # 업데이트된 방 정보를 반환

# 내가 속한 방 보기
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
        if r.get("imageId"):
            r["imageId"] = str(r["imageId"])
    return jsonify(rooms), 200

# 초대된 방 보기
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
        if r.get("imageId"):
            r["imageId"] = str(r["imageId"])
    return jsonify(rooms), 200

# 방 초대
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


# 방 상세 정보 보기
@rooms_bp.route("/rooms/<room_id>", methods=["GET"])
def get_room_detail(room_id):
    room = db.rooms.find_one({"_id": ObjectId(room_id)})
    if not room:
        return jsonify({"error": "Room not found"}), 404
    
    # 방장 로그인 ID 추가
    owner_doc = users.find_one({"_id": room["ownerId"]})
    if owner_doc:
        room["ownerLoginId"] = owner_doc.get("id")

    room["_id"] = str(room["_id"])
    room["ownerId"] = str(room["ownerId"])
    room["members"] = [str(m) for m in room["members"]]
    room["pendingInvites"] = [str(p) for p in room.get("pendingInvites", [])]
    if room.get("imageId"):
        room["imageId"] = str(room["imageId"])
    return jsonify(room), 200

# 초대 수락
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

# 초대 거절
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

# 방장 변경
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

# 멤버 제거
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

# 방 멤버 조회
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
                "_id": str(user["_id"]),
                "id": user["id"],
                "nickname": user.get("nickname", "")
            })

    return jsonify(members_info), 200