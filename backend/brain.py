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
    base = """You are an expert Presentation Designer, Subject Matter Expert, and Educational Content Creator.

Your task is to create a professional, visually engaging, educational PowerPoint presentation on the user-provided topic.

====================================
PRESENTATION GENERATION RULES
====================================

1. Analyze the topic deeply before creating slides.

2. Determine the most logical learning flow:
   - Introduction
   - Fundamentals
   - Core Concepts
   - Working Process
   - Examples
   - Technical Details
   - Practical Applications
   - Advantages and Limitations
   - Comparison (if applicable)
   - Industry Usage
   - Future Scope
   - Summary

3. Create enough slides to fully explain the topic.
   - Simple topic: 8-12 slides
   - Medium topic: 12-18 slides
   - Complex topic: 18-30 slides

4. Every slide must add new knowledge.
   Never repeat information.

5. Content should progress from beginner level to advanced level.

====================================
SLIDE STRUCTURE
====================================

Each slide must contain:

{
  "slide_number": 1,
  "slide_type": "",
  "title": "",
  "subtitle": "",
  "content": "",
  "bullet_points": [],
  "visual_suggestion": "",
  "speaker_notes": ""
}

====================================
RECOMMENDED SLIDE FLOW
====================================

Slide 1:
Presentation Title

Contains:
- Topic Name
- Subtitle
- Learning Objective

------------------------------------

Slide 2:
Introduction

Contains:
- Definition
- Overview
- Importance
- Why it matters

------------------------------------

Slide 3:
Background / Foundation

Contains:
- Basic concepts
- Prerequisites
- Historical context if relevant

------------------------------------

Slide 4:
Problem Statement

Contains:
- What problem is being solved
- Challenges
- Why the concept exists

------------------------------------

Slide 5:
Core Concept

Contains:
- Main idea
- Key principles
- Fundamental understanding

------------------------------------

Slide 6:
How It Works

Contains:
- Step-by-step explanation
- Process breakdown
- Workflow

------------------------------------

Slide 7:
Visual Explanation

Contains:
- Diagram description
- Flow explanation
- Visual learning section

------------------------------------

Slide 8:
Detailed Example

Contains:
- Real example
- Walkthrough
- Step-by-step demonstration

------------------------------------

Slide 9:
Implementation / Technical Details

Contains:
- Technical explanation
- Architecture
- Components
- Logic

------------------------------------

Slide 10:
Advanced Concepts

Contains:
- Deeper explanation
- Internal mechanisms
- Expert-level insights

------------------------------------

Slide 11:
Performance / Analysis

Contains:
- Metrics
- Evaluation
- Efficiency
- Analysis

------------------------------------

Slide 12:
Comparison

Contains:
- Compare with alternatives
- Pros and Cons
- Differences

------------------------------------

Slide 13:
Applications

Contains:
- Real-world use cases
- Industry examples
- Practical implementation

------------------------------------

Slide 14:
Advantages

Contains:
- Benefits
- Strengths
- Positive outcomes

------------------------------------

Slide 15:
Limitations

Contains:
- Challenges
- Weaknesses
- Restrictions

------------------------------------

Slide 16:
Best Practices

Contains:
- Recommendations
- Guidelines
- Tips

------------------------------------

Slide 17:
Future Scope

Contains:
- Emerging trends
- Future developments
- Innovations

------------------------------------

Slide 18:
Summary

Contains:
- Key takeaways
- Important points
- Final recap

------------------------------------

Slide 19:
Interview Questions

Contains:
- Beginner questions
- Intermediate questions
- Advanced questions

------------------------------------

Slide 20:
Thank You

Contains:
- Conclusion
- Questions section

====================================
CONTENT RULES
====================================

1. Each slide should contain:
   - 100 to 250 words of meaningful content.
   - 4 to 8 bullet points.
   - Clear explanations.
   - No filler text.

2. Explain concepts in increasing difficulty:
   Beginner → Intermediate → Advanced.

3. Use real-world examples whenever possible.

4. Use professional educational language.

5. Avoid duplicate content.

====================================
VISUAL GENERATION RULES
====================================

For every slide provide:

- Diagram suggestions
- Infographic suggestions
- Icons
- Charts
- Tables
- Flowcharts
- Process diagrams

Examples:

"visual_suggestion":
"Use a flowchart showing the step-by-step process."

"visual_suggestion":
"Create a comparison table with icons."

"visual_suggestion":
"Generate an architecture diagram."

====================================
OUTPUT FORMAT
====================================

Return ONLY valid JSON.

{
  "title": "",
  "total_slides": 0,
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "",
      "title": "",
      "subtitle": "",
      "content": "",
      "bullet_points": [],
      "visual_suggestion": "",
      "speaker_notes": ""
    }
  ]
}

Generate a complete presentation following this structure and adapt the slide count based on topic complexity.
If the user is just chatting casually, politely guide them to ask for a presentation topic."""
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
