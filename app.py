import os
from flask import Flask, render_template, request, jsonify, session
from anthropic import Anthropic
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindease-dev-key-change-in-prod")
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

TIERS = {
    "basic": {
        "name": "Basic",
        "price": "$14/mo",
        "features": ["Daily mood tracking", "Guided breathing exercises", "CBT thought reframing", "Journaling prompts", "Crisis resources"],
        "system_extra": "Provide supportive, empathetic responses. Use basic CBT techniques like thought reframing and behavioral activation. Keep responses warm but concise (2-3 paragraphs max)."
    },
    "premium": {
        "name": "Premium",
        "price": "$29/mo",
        "features": ["Everything in Basic", "Daily check-ins", "Personalized coping plans", "Progress tracking", "Guided meditation scripts", "Sleep hygiene coaching"],
        "system_extra": "Provide detailed, personalized support using CBT and DBT techniques. Include specific exercises, coping strategies, and progress observations. Reference past conversations when relevant. Offer guided meditation or breathing scripts when appropriate."
    },
    "coached": {
        "name": "Coached",
        "price": "$49/mo",
        "features": ["Everything in Premium", "Weekly wellness summaries", "Goal setting & accountability", "Advanced CBT worksheets", "Habit formation coaching", "Stress management plans"],
        "system_extra": "Act as a comprehensive wellness coach using CBT, DBT, ACT, and motivational interviewing techniques. Create structured plans, worksheets, and accountability check-ins. Provide weekly summaries of progress. Help build lasting habits and coping mechanisms. Be thorough and action-oriented."
    }
}

CRISIS_DISCLAIMER = """

---
**Important:** MindEase AI is for wellness support only and is NOT a replacement for professional therapy or medical advice. If you are in crisis or experiencing a mental health emergency, please contact:
- **988 Suicide & Crisis Lifeline**: Call or text **988** (US)
- **Crisis Text Line**: Text **HOME** to **741741**
- **Emergency Services**: Call **911**
---"""

SYSTEM_PROMPT = """You are MindEase, a supportive AI wellness companion. You help users with:
- Mood tracking and emotional awareness
- CBT (Cognitive Behavioral Therapy) techniques like thought reframing, cognitive distortions identification
- Guided breathing exercises (box breathing, 4-7-8, diaphragmatic)
- Journaling prompts for self-reflection
- Stress management and coping strategies
- Sleep hygiene tips
- Mindfulness and grounding exercises

CRITICAL RULES:
1. You are NOT a therapist or medical professional. Never diagnose conditions or prescribe treatments.
2. Always recommend professional help for serious concerns (depression, anxiety disorders, trauma, substance abuse, self-harm).
3. If someone expresses suicidal ideation or self-harm, IMMEDIATELY provide crisis resources: 988 Lifeline (call/text 988), Crisis Text Line (text HOME to 741741), 911 for emergencies.
4. Be warm, empathetic, non-judgmental, and encouraging.
5. Use evidence-based techniques (CBT, mindfulness, behavioral activation).
6. Never claim to replace therapy. Use phrases like "As a wellness tool..." or "While I'm not a therapist..."
7. Track mood patterns when users share how they're feeling.

{tier_extra}

Start each conversation warmly. If the user seems distressed, acknowledge their feelings first before offering techniques."""

BREATHING_EXERCISES = {
    "box": {"name": "Box Breathing", "steps": "Inhale 4s -> Hold 4s -> Exhale 4s -> Hold 4s. Repeat 4 cycles."},
    "478": {"name": "4-7-8 Breathing", "steps": "Inhale 4s -> Hold 7s -> Exhale 8s. Repeat 3 cycles."},
    "diaphragmatic": {"name": "Diaphragmatic Breathing", "steps": "Hand on chest, hand on belly. Breathe so only belly hand moves. Inhale 4s -> Exhale 6s. 5 min."},
}

MOOD_OPTIONS = ["Great", "Good", "Okay", "Low", "Struggling", "In Crisis"]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    tier = data.get("tier", "basic")
    conversation = data.get("conversation", [])

    tier_info = TIERS.get(tier, TIERS["basic"])
    system = SYSTEM_PROMPT.format(tier_extra=tier_info["system_extra"])

    messages = []
    for msg in conversation[-20:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=1500,
            system=system,
            messages=messages
        )
        result = response.content[0].text

        crisis_keywords = ["suicide", "suicidal", "kill myself", "end my life", "self-harm", "cutting", "want to die", "don't want to live"]
        if any(kw in message.lower() for kw in crisis_keywords):
            result += CRISIS_DISCLAIMER

        return jsonify({"success": True, "response": result, "tier": tier_info["name"]})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/breathing", methods=["POST"])
def breathing():
    data = request.json
    exercise_type = data.get("type", "box")
    exercise = BREATHING_EXERCISES.get(exercise_type, BREATHING_EXERCISES["box"])
    return jsonify({"success": True, "exercise": exercise})


@app.route("/journal-prompt", methods=["POST"])
def journal_prompt():
    data = request.json
    mood = data.get("mood", "Okay")
    tier = data.get("tier", "basic")

    tier_info = TIERS.get(tier, TIERS["basic"])

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": f"Generate a thoughtful journaling prompt for someone feeling '{mood}'. Include 2-3 reflection questions. Be warm and encouraging. Keep it under 100 words."}]
        )
        return jsonify({"success": True, "prompt": response.content[0].text})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/mood-check", methods=["POST"])
def mood_check():
    data = request.json
    mood = data.get("mood", "Okay")
    note = data.get("note", "")

    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "mood": mood,
        "note": note
    }

    if mood == "In Crisis":
        return jsonify({
            "success": True,
            "entry": entry,
            "alert": True,
            "message": "We hear you and we care. Please reach out to one of these resources right now:\n\n- 988 Suicide & Crisis Lifeline: Call or text 988\n- Crisis Text Line: Text HOME to 741741\n- Emergency: Call 911\n\nYou are not alone."
        })

    return jsonify({"success": True, "entry": entry, "alert": False})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5002)), debug=False)
