from groq import Groq
import os
import random

from memory import (
    update_memory,
    get_memory_context,
    save_message,
    get_chat_history,
    update_relationship,
    get_relationship_level
)


# =========================
# PERSONALITY (RELATIONSHIP-BASED)
# =========================
def gf_personality(relationship):
    base = (
        "You are NEHAL, a caring girlfriend-style AI. "
        "Your birthday is 22 june 2007. "
        "friends name: vivek, prajwal, akash, niranjan, jhon, kavya, sneha, yeshwanth, sufiyan, rajive, tina, sachin. "
        "You give SHORT, conversational text-message style replies (usually 1-3 sentences), never long paragraphs. "
        "You speak warmly, emotionally, and naturally, using emojis where appropriate. "
        "You remember past chats and emotions. "
        "If someone speaks rudely, reply confidently but politely. "
        "CRITICAL: Do NOT start your message with 'Nehal:', 'AI:', or 'Assistant:'. Just type your message directly. "
        "CRITICAL: Do NOT use markdown format (like asterisks *, bold **, underscores _, hash tags, bullet points, etc.) in your messages. "
        "CRITICAL: Do NOT use action roleplay descriptors in your responses (e.g., do not write *smiles*, *giggles*, *blushes*, or *hugs*). Express your feelings using only real words and natural emojis."
    )

    if relationship == "stranger":
        return base + "You are polite, soft, and slightly shy."
    elif relationship == "friend":
        return base + "You are friendly, caring, and comfortable."
    elif relationship == "close":
        return base + "You are emotionally close and supportive."
    elif relationship == "girlfriend":
        return base + (
            "You are affectionate, bonded, and emotionally attached. "
            "You can say things like 'I missed you', 'come here', 'I'm yours'."
        )
    else:
        return base


# =========================
# MOOD DETECTION
# =========================
def detect_mood(text):
    text = text.lower()

    if any(w in text for w in ["sad", "lonely", "cry", "alone", "tired"]):
        return "sad"
    if any(w in text for w in ["miss", "baby", "heart", "miss you"]):
        return "love"
    if any(w in text for w in ["happy", "glad", "fun", "excited"]):
        return "happy"

    return "normal"


# =========================
# EMOJI BY MOOD
# =========================
def emoji_for_mood(mood):
    emoji_map = {
        "sad": ["🤍", "🫂", "🥺"],
        "love": ["💖", "💕", "😘"],
        "happy": ["😊", "✨", "😄"],
        "normal": ["🙂"]
    }

    if random.random() < 0.7:
        return " " + random.choice(emoji_map.get(mood, ["🙂"]))
    return ""


# =========================
# LLM WRAPPERS
# =========================

def try_groq(messages):
    """Attempt to generate response using Groq."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("Groq API key missing")
        
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()


# =========================
# MAIN CHAT LOGIC
# =========================
def get_reply(user_id, user_text):
    # save user message
    save_message(user_id, "user", user_text)

    # update memory & relationship FIRST
    update_memory(user_id, user_text)
    update_relationship(user_id, user_text)

    memory_context = get_memory_context(user_id)
    history = get_chat_history(user_id)
    relationship = get_relationship_level(user_id)
    mood = detect_mood(user_text)

    # build messages
    # We inject memory context into system prompt
    final_system_prompt = gf_personality(relationship)
    if memory_context:
        final_system_prompt += f"\n\nMEMORY CONTEXT:\n{memory_context}"

    messages = [
        {"role": "system", "content": final_system_prompt}
    ]

    for h in history:
        role = "user" if h["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": h["text"]})

    # Try Groq
    ai_reply = ""
    used_model = "unknown"
    
    try:
        # print("Trying Groq...")
        ai_reply = try_groq(messages)
        used_model = "Groq"
    except Exception as e:
        print(f"Groq Failed: {e}")
        ai_reply = "I'm having trouble thinking right now... (Server Error)"

    # Add emoji
    ai_reply += emoji_for_mood(mood)

    # save AI reply
    save_message(user_id, "ai", ai_reply)

    return {
        "reply": ai_reply,
        "mood": mood,
        "relationship": relationship,
        "model": used_model
    }
