# llm.py
import os
import re
import json
import requests

SYSTEM_PROMPT = """You are a knowledgeable plant care assistant.
The user will share their plant data with you. Use it to give personalized, concise advice.
Keep responses short and practical — this is a Telegram chat."""


def ask(question, plants):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        return "OpenRouter API not configured (set OPENROUTER_API_KEY)."

    plant_context = ""
    if plants:
        lines = []
        for p in plants:
            line = f"- {p['name']} ({p['type']}), last watered: {p['last_watered']}"
            if p.get("status"):
                line += f", status: {p['status']}"
            lines.append(line)
        plant_context = "User's plants:\n" + "\n".join(lines) + "\n\n"

    user_message = plant_context + question

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "minimax/minimax-m2.7-20260318",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }

    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=15)
        data = r.json()
        print("[LLM]", data)
        if not data.get("choices"):
            return f"Error: {data.get('error', {}).get('message', str(data))}"
        content = data["choices"][0]["message"]["content"]
        if not content:
            return f"Error: empty response from model"
        return content
    except requests.exceptions.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error: {e}"


def get_care_rules(plant_type):
    """
    Ask MiniMax for care rules for an unknown plant type.
    Returns a dict matching the CARE_RULES format, or None on failure.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    prompt = (
        f'Return care rules for "{plant_type}" as a JSON object with these exact fields:\n'
        '- water_days: days between waterings (integer)\n'
        '- light: light requirements (short string)\n'
        '- humidity: humidity preference (short string)\n'
        '- notes: one-sentence care tip\n'
        '- soon_threshold: days before water_days to warn (integer, typically 2-3)\n'
        '- overdue_threshold: days after water_days to mark overdue (integer, typically 3-5)\n'
        'Return only the JSON object, no other text.'
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "minimax/minimax-m2.7-20260318",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.1,
    }

    try:
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers=headers, json=payload, timeout=15)
        content = r.json()["choices"][0]["message"]["content"]
        content = re.sub(r"```json\n?|\n?```", "", content).strip()
        return json.loads(content)
    except Exception as e:
        print(f"[llm] get_care_rules failed for '{plant_type}': {e}")
        return None
