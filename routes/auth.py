from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from db import users

auth_bp = Blueprint("auth", __name__)

def json_utf8(data, status=200):
    """UTF-8 인코딩이 보장된 jsonify 헬퍼 함수"""
    response = make_response(jsonify(data), status)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


# 회원가입
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    id = data.get("id", "").strip()
    password = data.get("password", "").strip()
    nickname = data.get("nickname", "").strip()

    if not id or not password or not nickname:
        return jsonify({"error": "All fields required"}), 400

    if users.find_one({"id": id}):
        return jsonify({"error": "id exists"}), 409

    hashed_pw = generate_password_hash(password)
    user = {
        "id": id,
        "password": hashed_pw,
        "nickname": nickname,
    }
    result = users.insert_one(user)

    return jsonify({
        "status": "ok",
        "userId": str(result.inserted_id),
        "id": id,
        "nickname": nickname
    }), 201


# 로그인
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    id = data.get("id", "").strip()
    password = data.get("password", "").strip()

    user = users.find_one({"id": id})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401


    return jsonify({
        "status": "ok",
        "userId": str(user["_id"]),  
        "id": user["id"],
        "nickname": user["nickname"]
    }), 200


# 탈퇴
@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True)
    id = data.get("id")
    password = data.get("password")

    user = users.find_one({"id": id})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    users.delete_one({"id": id})
    return jsonify({"status": "deleted"}), 200
