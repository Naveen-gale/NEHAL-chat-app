from db import users_col, memory_col, emotion_col
from db import chats_col

def ensure_user(user_id):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({
            "user_id": user_id,
            "name": None
        })

def update_memory(user_id, text):
    ensure_user(user_id)
    text_l = text.lower()

    # Name
    if "my name is" in text_l:
        name = text.split("my name is")[-1].strip().title()
        users_col.update_one(
            {"user_id": user_id},
            {"$set": {"name": name}}
        )

    # Voice memory
    if "remember that" in text_l:
        fact = text.split("remember that")[-1].strip()
        memory_col.insert_one({
            "user_id": user_id,
            "fact": fact
        })

    # Emotional state
    for mood in ["sad", "happy", "lonely", "angry", "tired"]:
        if mood in text_l:
            emotion_col.insert_one({
                "user_id": user_id,
                "emotion": mood
            })

def get_memory_context(user_id):
    context = ""

    user = users_col.find_one({"user_id": user_id})
    if user and user.get("name"):
        context += f"The user's name is {user['name']}. "

    facts = memory_col.find({"user_id": user_id})
    facts_list = [f["fact"] for f in facts]
    if facts_list:
        context += "Things you remember about the user: "
        context += "; ".join(facts_list) + ". "

    last_emotion = emotion_col.find({"user_id": user_id}).sort("_id", -1).limit(1)
    for e in last_emotion:
        context += f"The user is currently feeling {e['emotion']}. "

    return context





def save_message(user_id, sender, text):
    chats_col.insert_one({
        "user_id": user_id,
        "sender": sender,
        "text": text
    })
def get_chat_history(user_id, limit=50):
    chats = chats_col.find(
        {"user_id": user_id}
    ).sort("_id", 1).limit(limit)

    history = []
    for c in chats:
        history.append({
            "sender": c["sender"],
            "text": c["text"]
        })

    return history


def update_relationship(user_id, text):
    ensure_user(user_id)
    text = text.lower()

    score = 1  # base increase per message

    if any(w in text for w in ["miss", "love", "care", "baby"]):
        score += 3

    if any(w in text for w in ["sad", "lonely", "tired"]):
        score += 2  # emotional bonding

    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"relationship_score": score}}
    )




def get_relationship_level(user_id):
    user = users_col.find_one({"user_id": user_id})
    score = user.get("relationship_score", 0)

    if score < 20:
        return "stranger"
    elif score < 50:
        return "friend"
    elif score < 80:
        return "close"
    else:
        return "girlfriend"
