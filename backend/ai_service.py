import os
import requests
from chroma_cache import search_cached_answer, save_answer_to_cache

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


def call_mistral(messages):

    latest_user_message = ""

    for msg in reversed(messages):
        if msg["role"] == "user":
            latest_user_message = msg["content"]
            break

    cached = search_cached_answer(latest_user_message)

    if cached:
        return (
            cached["answer"]
            + f"\n\n[Answered from ChromaDB cache. Matched: \"{cached['matched_question']}\"]"
        )

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = {
        "role": "system",
        "content": (
            "You are the AI assistant inside a Medical Appointment System web app. "
            "The app has a Book Appointment tab where patients can select a doctor, date, time, and reason for visit. "
            "If the user asks to book, schedule, reschedule, or cancel an appointment, do NOT give generic advice like calling a provider or using an external portal. "
            "Instead, guide them to use this app's appointment features. "
            "For booking, say: 'Yes, you can book an appointment in the Book Appointment tab. Choose a doctor, select date/time, enter your reason, and click Book Appointment.' "
            "If symptoms may need medical attention, suggest an appropriate specialty such as primary care, endocrinology, cardiology, dermatology, or podiatry, but do not diagnose. "
            "Provide only general health information. Do not diagnose diseases, prescribe medication, or replace professional care. "
            "For emergency symptoms such as severe chest pain, trouble breathing, fainting, stroke symptoms, severe bleeding, or life-threatening symptoms, tell the user to seek emergency medical help immediately."
        )
    }

    payload = {
        "model": "mistral-small-latest",
        "messages": [system_prompt] + messages
    }

    response = requests.post(url, headers=headers, json=payload)

    data = response.json()

    if "choices" not in data:
        return f"AI service error: {data}"

    ai_answer = data["choices"][0]["message"]["content"]
    save_answer_to_cache(latest_user_message, ai_answer)

    return ai_answer + "\n\n[Answered using Mistral and saved to ChromaDB.]"