from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
import random, string


auth_bp = Blueprint("auth", __name__)

mongo = None
bcrypt = None

def set_auth_dependencies(m, b):
    global mongo, bcrypt
    mongo = m
    bcrypt = b

def generate_meeting_key(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))



@auth_bp.route('/auth/signup', methods=["POST"])
def signup():
    data = request.json
    email = data["email"]
    password = data["password"]
    name= data["name"]

    if mongo.db.users.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400
    
    user_key= generate_meeting_key()
    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    mongo.db.users.insert_one({"email": email, "password": hashed_pw,'name':name,'userKey':user_key})
    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route('/auth/login', methods=["POST"])
def login():
    data = request.json
    email = data["email"]
    password = data["password"]

    user = mongo.db.users.find_one({"email": email})
    if user and bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Login successful", "email": user["email"], "userKey": user["userKey"],"name":user["name"]})
    return jsonify({"error": "Invalid credentials"}), 401
