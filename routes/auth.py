# routes/auth.py
from flask import Blueprint, request, Response
from werkzeug.security import generate_password_hash, check_password_hash
from db import users

auth_bp = Blueprint("auth", __name__)

# 회원가입
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    nickname = data.get("nickname", "").strip()

    if not email or not password or not nickname:
        return Response('{"error":"All fields required"}', status=400, mimetype="application/json")

    if users.find_one({"email": email}):
        return Response('{"error":"Email exists"}', status=409, mimetype="application/json")

    hashed_pw = generate_password_hash(password)
    user = {
        "email": email,
        "password": hashed_pw,
        "nickname": nickname,
    }
    users.insert_one(user)
    return Response('{"status":"ok","email":"%s","nickname":"%s"}' % (email, nickname),
                    status=201, mimetype="application/json")


# 로그인
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    user = users.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return Response('{"error":"Invalid credentials"}', status=401, mimetype="application/json")

    return Response('{"status":"ok","email":"%s","nickname":"%s"}' % (user["email"], user["nickname"]),
                    status=200, mimetype="application/json")


# 탈퇴
@auth_bp.route("/delete", methods=["POST"])
def delete_account():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")

    user = users.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return Response('{"error":"Invalid credentials"}', status=401, mimetype="application/json")

    users.delete_one({"email": email})
    return Response('{"status":"deleted"}', status=200, mimetype="application/json")

