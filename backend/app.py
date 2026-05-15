from flask import Flask, render_template, request, jsonify, session, send_from_directory
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
        print("NEW USER:", session["user_id"])
    else:
        print("EXISTING USER:", session["user_id"])

    return render_template("index.html")

@app.route('/favicon.ico')
def favicon():
    return "", 204

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    msg = data.get("message", "").strip()

    user_id = session.get("user_id")

    reply_data = get_reply(user_id, msg)
    return jsonify(reply_data)



from memory import get_chat_history

@app.route("/history", methods=["GET"])
def history():
    user_id = session.get("user_id")
    chats = get_chat_history(user_id)
    return jsonify(chats)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
