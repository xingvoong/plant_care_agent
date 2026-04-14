# llm.py
import os
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
