from flask import Flask, render_template, request, jsonify, session, send_from_directory, redirect, url_for, Response, stream_with_context
from werkzeug.security import generate_password_hash, check_password_hash
from db import users_col, chats_col
import uuid
import os
import time
import threading
from dotenv import load_dotenv
from brain import get_reply, get_reply_stream
import edge_tts
import asyncio

def generate_edge_tts_sync(text, output_file):
    async def _generate():
        # en-US-AriaNeural is a very smooth, natural, and expressive female voice
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        await communicate.save(output_file)
    asyncio.run(_generate())

# --- NEW IMPORTS FOR SPEAKER RECOGNITION ---
try:
    import torchaudio
    from speechbrain.inference.speaker import SpeakerRecognition
    print("Loading Speaker Recognition model (this might take a few seconds)...")
    speaker_model = SpeakerRecognition.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb", 
        savedir="pretrained_models/spkrec-ecapa-voxceleb"
    )
except Exception as e:
    print(f"Warning: Failed to load Speaker Recognition model: {e}")
    speaker_model = None
# ---------------------------------------------

load_dotenv() # Load environment variables from .env file

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

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

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    data = request.get_json()
    msg = data.get("message", "").strip()

    user_id = session.get("user_id")
    is_registered = session.get("is_registered", False)

    if not is_registered:
        msg_count = chats_col.count_documents({"user_id": user_id, "sender": "user"})
        if msg_count >= 2:
            import json
            def err_gen():
                yield f"data: {json.dumps({'requires_login': True})}\n\n"
            return Response(stream_with_context(err_gen()), mimetype='text/event-stream')

    return Response(stream_with_context(get_reply_stream(user_id, msg)), mimetype='text/event-stream')

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        voice_sample = request.files.get("voice_sample")
        
        if not username or not password:
            return render_template("signup.html", error="Username and password are required")
        if not voice_sample or voice_sample.filename == "":
            return render_template("signup.html", error="Voice enrollment is required. Please record your voice.")
            
        existing_user = users_col.find_one({"username": username})
        if existing_user:
            return render_template("signup.html", error="Username already exists")
            
        hashed_pw = generate_password_hash(password)
        
        # If user has an existing guest session, tie this new account to that session's data
        user_id = session.get("user_id", str(uuid.uuid4()))
        
        # Save voice sample reference
        ref_path = os.path.join(AUDIO_DIR, f"ref_{user_id}.webm")
        voice_sample.save(ref_path)
        
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "username": username,
                "password": hashed_pw,
                "is_registered": True,
                "voice_ref": ref_path
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
    is_registered = session.get("is_registered", False)
    username = None
    if is_registered:
        user_doc = users_col.find_one({"user_id": session.get("user_id", "")})
        if user_doc:
            username = user_doc.get("username", "")
        else:
            session["is_registered"] = False
            is_registered = False
    return jsonify({
        "is_registered": is_registered,
        "username": username
    })

@app.route("/live")
def live_chat():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        session["is_registered"] = False
    return render_template("live.html")

# edge_tts function removed for instant response

@app.route("/chat_voice", methods=["POST"])
def chat_voice():
    try:
        # Clean up old audio files
        try:
            now = time.time()
            for f in os.listdir(AUDIO_DIR):
                fpath = os.path.join(AUDIO_DIR, f)
                if os.path.isfile(fpath) and f.endswith(".mp3") and (now - os.path.getmtime(fpath) > 300):
                    os.remove(fpath)
        except Exception as e:
            print(f"Cleanup error: {e}")

        user_id = session.get("user_id")
        is_registered = session.get("is_registered", False)
        
        transcribed_text = None
        detected_lang_code = "en-US"
        
        if "audio" in request.files:
            audio_file = request.files["audio"]
            if audio_file.filename != "":
                # Save audio file temporarily
                temp_filename = f"temp_{uuid.uuid4().hex}.webm"
                temp_filepath = os.path.join(AUDIO_DIR, temp_filename)
                audio_file.save(temp_filepath)
                
                # --- VOICE BIOMETRICS CHECK ---
                if is_registered and speaker_model is not None:
                    user_doc = users_col.find_one({"user_id": user_id})
                    if user_doc and "voice_ref" in user_doc:
                        ref_path = user_doc["voice_ref"]
                        if os.path.exists(ref_path):
                            try:
                                score, prediction = speaker_model.verify_files(ref_path, temp_filepath)
                                if score.item() < 0.4:  # Enforce stricter threshold (0.4 instead of default 0.25)
                                    print(f"Speaker rejected! Score: {score.item()}")
                                    # Silently ignore the noise/other person
                                    if os.path.exists(temp_filepath):
                                        os.remove(temp_filepath)
                                    return jsonify({"retry": True, "error": "Not your voice"}), 200
                                else:
                                    print(f"Speaker verified. Score: {score.item()}")
                            except Exception as e:
                                print(f"Voice verification error: {e}")
                                if os.path.exists(temp_filepath):
                                    os.remove(temp_filepath)
                                return jsonify({"retry": True, "error": "Verification failed"}), 200
                # ------------------------------
                
                # Transcribe via Groq Whisper API with retry loop
                try:
                    from groq import Groq
                    api_key = os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise Exception("Groq API key missing")
                    client = Groq(api_key=api_key)
                    
                    # Retry loop
                    for attempt in range(3):
                        try:
                            with open(temp_filepath, "rb") as file:
                                transcription = client.audio.transcriptions.create(
                                    file=(temp_filepath, file.read()),
                                    model="whisper-large-v3-turbo",
                                    response_format="verbose_json",
                                    language="en"
                                )
                            transcribed_text = transcription.text.strip()
                            detected_lang_code = "en-US"
                            print(f"Whisper transcribed in English: {transcribed_text}")
                            break
                        except Exception as e:
                            print(f"Whisper attempt {attempt+1} failed: {e}")
                            if attempt == 2:
                                raise e
                            time.sleep(1)
                except Exception as e:
                    print(f"Whisper transcription failed: {e}")
                    raise e
                finally:
                    # Always remove temporary audio file
                    if os.path.exists(temp_filepath):
                        try:
                            os.remove(temp_filepath)
                        except Exception as e:
                            print(f"Temp file remove error: {e}")
        else:
            # Fallback text
            transcribed_text = request.form.get("text", "").strip()
            detected_lang_code = "en-US"
            print(f"Fallback text: {transcribed_text}")

        if not transcribed_text:
            return jsonify({"retry": True, "error": "No speech detected"}), 200

        # Enforce 2-message limit for unregistered guests
        if not is_registered:
            msg_count = chats_col.count_documents({"user_id": user_id, "sender": "user"})
            if msg_count >= 2:
                warning_text = "I'd love to keep chatting! Please sign up to continue."
                    
                return jsonify({
                    "user_text": transcribed_text,
                    "reply": warning_text,
                    "audio_url": None,
                    "requires_login": True
                })

        # Get AI reply
        reply_data = get_reply(user_id, transcribed_text)
        reply_text = reply_data.get("reply", "")
        
        # Decide what to speak (if text is very long, just speak a short summary)
        if len(reply_text) > 200:
            spoken_text = "Here is the detailed presentation prompt you requested. Please check the chat."
        else:
            spoken_text = reply_text

        # Generate smooth female voice using edge_tts
        audio_filename = f"reply_{uuid.uuid4().hex}.mp3"
        audio_filepath = os.path.join(AUDIO_DIR, audio_filename)
        generate_edge_tts_sync(spoken_text, audio_filepath)
        audio_url = f"/static/audio/{audio_filename}"

        return jsonify({
            "user_text": transcribed_text,
            "reply": reply_text,
            "audio_url": audio_url,
            "mood": reply_data.get("mood", "normal"),
            "relationship": reply_data.get("relationship", "stranger"),
            "requires_login": False
        })
    except Exception as outer_e:
        import traceback
        error_tb = traceback.format_exc()
        print(f"CRITICAL: /chat_voice failed: {outer_e}\n{error_tb}")
        try:
            with open("backend_error.log", "w") as log_f:
                log_f.write(f"{outer_e}\n{error_tb}")
        except Exception as log_err:
            print(f"Failed to write log file: {log_err}")
        return jsonify({"error": str(outer_e), "traceback": error_tb}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
