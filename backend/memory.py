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

    # Trigger background fact extraction for self-learning memory
    background_extract_facts(user_id, text)

def background_extract_facts(user_id, user_text):
    import threading
    import os
    
    def _run():
        try:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                return
            from groq import Groq
            client = Groq(api_key=api_key)
            
            prompt = (
                "You are a silent helper for a girlfriend AI. Analyze the user's message and extract any new key facts, preferences, interests, details, hobbies, or name/relationship details about the user.\n"
                "Return the extracted fact in the 3rd person singular format (e.g. 'The user is learning Python', 'The user loves playing basketball', 'The user's favorite color is blue').\n"
                "CRITICAL: If the message does not contain any new personal facts, preferences, or details about the user, return absolutely nothing (completely empty string).\n"
                "Do not explain, do not add preamble. Output either the fact or empty string."
            )
            
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"User says: '{user_text}'"}
                ],
                max_tokens=60
            )
            
            fact = response.choices[0].message.content.strip()
            # Clean up the output in case it wrapped in quotes
            if fact.startswith('"') and fact.endswith('"'):
                fact = fact[1:-1].strip()
            
            if fact and len(fact) > 5 and not fact.lower().startswith("no fact") and "nothing" not in fact.lower():
                from db import memory_col
                # Check if this fact already exists to prevent duplicate spam
                existing = memory_col.find_one({"user_id": user_id, "fact": fact})
                if not existing:
                    memory_col.insert_one({
                        "user_id": user_id,
                        "fact": fact
                    })
                    print(f"[Self-Learning] Learned fact for {user_id}: {fact}")
        except Exception as e:
            print(f"[Self-Learning] Error extracting facts: {e}")
            
    # Run in background so we do not block response time
    t = threading.Thread(target=_run)
    t.start()

def get_memory_context(user_id):
    context = ""

    user = users_col.find_one({"user_id": user_id})
    if user:
        if user.get("name"):
            context += f"The user's name is {user['name']}. "
        elif user.get("username"):
            context += f"The user's name is {user['username']}. "

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
def get_chat_history(user_id, limit=30):
    # Fetch the latest messages (newest first) and reverse them for chronological order
    chats = list(chats_col.find(
        {"user_id": user_id}
    ).sort("_id", -1).limit(limit))
    chats.reverse()

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
