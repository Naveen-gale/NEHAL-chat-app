from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from db import users_col, chats_col
import uuid
import os
from dotenv import load_dotenv
from brain import get_reply

load_dotenv() # Load environment variables from .env file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# 🔐 MUST BE CONSTANT (never change)
app.secret_key = "un-chat-super-secret-key"

# Make session persistent
app.config["SESSION_PERMANENT"] = True

@app.route("/")
def home():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        session["is_registered"] = False
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon():
    return "", 204

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    msg = data.get("message", "").strip()

    user_id = session.get("user_id")
    is_registered = session.get("is_registered", False)

    # Enforce 2-message limit for unregistered guests
    if not is_registered:
        msg_count = chats_col.count_documents({"user_id": user_id, "sender": "user"})
        if msg_count >= 2:
            return jsonify({"requires_login": True})

    reply_data = get_reply(user_id, msg)
    return jsonify(reply_data)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            return render_template("signup.html", error="Username and password are required")
            
        existing_user = users_col.find_one({"username": username})
        if existing_user:
            return render_template("signup.html", error="Username already exists")
            
        hashed_pw = generate_password_hash(password)
        
        # If user has an existing guest session, tie this new account to that session's data
        user_id = session.get("user_id", str(uuid.uuid4()))
        
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": username,
                "password": hashed_pw,
                "is_registered": True
            }},
            upsert=True
        )
        
        session["user_id"] = user_id
        session["is_registered"] = True
        return redirect(url_for("home"))
        
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = users_col.find_one({"username": username, "is_registered": True})
        
        if user and check_password_hash(user.get("password", ""), password):
            session["user_id"] = user["user_id"]
            session["is_registered"] = True
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid username or password")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

from memory import get_chat_history

@app.route("/history", methods=["GET"])
def history():
    user_id = session.get("user_id")
    chats = get_chat_history(user_id)
    return jsonify(chats)

@app.route("/auth_status")
def auth_status():
    return jsonify({
        "is_registered": session.get("is_registered", False),
        "username": users_col.find_one({"user_id": session.get("user_id", "")}).get("username", "") if session.get("is_registered") else None
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
