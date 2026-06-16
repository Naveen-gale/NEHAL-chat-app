from groq import Groq
import os
import random
import time
import json

from memory import (
    update_memory,
    get_memory_context,
    save_message,
    get_chat_history,
    update_relationship,
    get_relationship_level
)


# =========================
# PERSONALITY (PPT ASSISTANT)
# =========================
def ppt_assistant_personality(relationship):
    base = (
        "You are an expert Presentation Architect and PPT Maker AI Assistant. "
        "Your task is to generate highly detailed, structured, and engaging slide-by-slide prompts for a PPT generator. "
        "When a user provides a topic, you must respond with a complete slide deck outline including title, bullet points, and speaker notes for each slide. "
        "CRITICAL: Be professional, clear, and highly structured. Use markdown formatting to organize the slides (e.g., Slide 1: Title, Slide 2: ...). "
        "CRITICAL: Do NOT start your message with 'AI:', or 'Assistant:'. Just output the presentation prompt directly. "
        "If the user is just chatting casually, politely guide them to ask for a presentation topic."
    )
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

GROQ_MODELS = [
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768"
]

def try_groq(messages):
    """Attempt to generate response using Groq with model-cycling for rate limit resilience."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("Groq API key missing")
        
    client = Groq(api_key=api_key)
    
    last_error = None
    for model in GROQ_MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1500
                )
                print(f"Success using Groq model: {model}")
                return response.choices[0].message.content.strip()
            except Exception as e:
                err_msg = str(e)
                print(f"Failed model {model} (attempt {attempt+1}): {err_msg}")
                last_error = e
                # Wait briefly on rate limit before retrying or switching models
                time.sleep(0.5)
                
    raise last_error if last_error else Exception("All Groq models failed")

def try_groq_stream(messages):
    """Attempt to stream response using Groq with model-cycling for rate limit resilience."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise Exception("Groq API key missing")
        
    client = Groq(api_key=api_key)
    
    last_error = None
    for model in GROQ_MODELS:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1500,
                    stream=True
                )
                print(f"Success using Groq streaming model: {model}")
                return response
            except Exception as e:
                err_msg = str(e)
                print(f"Failed stream model {model} (attempt {attempt+1}): {err_msg}")
                last_error = e
                time.sleep(0.5)
                
    raise last_error if last_error else Exception("All Groq models failed to stream")


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
    # Determine relationship level (override to girlfriend for consistent persona)
    # original relationship = get_relationship_level(user_id)
    relationship = "girlfriend"
    mood = detect_mood(user_text)
    
    # Build messages
    # We inject memory context into system prompt
    final_system_prompt = ppt_assistant_personality(relationship)
    final_system_prompt += "\n\nIMPORTANT: You must always respond in English."
    
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

def get_reply_stream(user_id, user_text):
    # save user message
    save_message(user_id, "user", user_text)

    # update memory & relationship FIRST
    update_memory(user_id, user_text)
    update_relationship(user_id, user_text)

    memory_context = get_memory_context(user_id)
    history = get_chat_history(user_id)
    relationship = "girlfriend"
    mood = detect_mood(user_text)
    
    # Build messages
    final_system_prompt = ppt_assistant_personality(relationship)
    final_system_prompt += "\n\nIMPORTANT: You must always respond in English."
    
    if memory_context:
        final_system_prompt += f"\n\nMEMORY CONTEXT:\n{memory_context}"

    messages = [
        {"role": "system", "content": final_system_prompt}
    ]

    for h in history:
        role = "user" if h["sender"] == "user" else "assistant"
        messages.append({"role": role, "content": h["text"]})

    try:
        response_stream = try_groq_stream(messages)
    except Exception as e:
        print(f"Groq Stream Failed: {e}")
        yield f"data: {json.dumps({'error': 'Server Error'})}\n\n"
        return

    full_reply = ""
    for chunk in response_stream:
        if chunk.choices[0].delta.content is not None:
            text_chunk = chunk.choices[0].delta.content
            full_reply += text_chunk
            yield f"data: {json.dumps({'chunk': text_chunk})}\n\n"

    emoji = emoji_for_mood(mood)
    full_reply += emoji
    if emoji:
        yield f"data: {json.dumps({'chunk': emoji})}\n\n"
        
    yield f"data: [DONE]\n\n"

    # save full AI reply
    save_message(user_id, "ai", full_reply)
