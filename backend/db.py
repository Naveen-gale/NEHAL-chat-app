from pymongo import MongoClient
import os
from dotenv import load_dotenv


load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["un_chat"]

users_col = db["users"]
memory_col = db["memory"]
emotion_col = db["emotions"]
chats_col = db["chats"]  # ✅ NEW

print("[OK] MongoDB connected to:", db.name)




def ensure_user(user_id):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({
            "user_id": user_id,
            "relationship_score": 0
        })
