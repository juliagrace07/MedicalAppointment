import os
import json
import requests

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


def base_intent(intent):
    return {
        "intent": intent,
        "condition": None,
        "city": None,
        "age_lt": None,
        "age_gt": None,
        "name": None,
        "doctor_name": None,
        "time_preference": None,
        "date_preference": None
    }


def extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass

    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return base_intent("general_health_question")


def detect_intent(user_message: str, role: str):
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """
You are an AI tool-routing agent for a medical appointment system.

Convert the user's natural language into exactly ONE backend tool intent.
Return ONLY valid JSON. No explanation.

Available intents:
- doctor_schedule_today
- doctor_all_appointments
- doctor_upcoming_appointments
- doctor_all_patients
- doctor_next_patient
- doctor_next_patient_history
- patient_my_appointments
- patient_available_doctors
- patient_open_slots
- patient_cancel_appointment_help
- search_patients
- general_health_question

Rules:
If role is doctor and the user asks about patients, patient list, assigned patients, patient details, or people under their care, use doctor_all_patients.
If role is doctor and the user asks about appointments generally, use doctor_all_appointments.
If role is doctor and the user asks about upcoming/future/next appointments, use doctor_upcoming_appointments.
If role is doctor and the user asks about today/day/schedule, use doctor_schedule_today.
If role is doctor and the user asks about next patient medical history, use doctor_next_patient_history.

If role is patient and the user asks about their appointments, use patient_my_appointments.
If role is patient and the user asks for doctors/providers/available doctors, use patient_available_doctors.
If role is patient and the user asks to cancel an appointment, use patient_cancel_appointment_help.

Use search_patients for doctor/admin questions that filter/search patients by condition, disease, city, address, age, or name.

Examples:
Doctor: "show me my patients"
{"intent":"doctor_all_patients","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show list of patients"
{"intent":"doctor_all_patients","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show me my appointments"
{"intent":"doctor_all_appointments","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show my upcoming appointments"
{"intent":"doctor_upcoming_appointments","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show patients with diabetes"
{"intent":"search_patients","condition":"diabetes","city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show patients above age 45"
{"intent":"search_patients","condition":null,"city":null,"age_lt":null,"age_gt":45,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Doctor: "show patients in Dayton"
{"intent":"search_patients","condition":null,"city":"Dayton","age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Patient: "show me my appointments"
{"intent":"patient_my_appointments","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}

Patient: "show me the list of doctors"
{"intent":"patient_available_doctors","condition":null,"city":null,"age_lt":null,"age_gt":null,"name":null,"doctor_name":null,"time_preference":null,"date_preference":null}
"""

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Role: {role}\nQuestion: {user_message}"}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()

        print("RAW INTENT RESPONSE:", data, flush=True)

        if "choices" not in data:
            return base_intent("general_health_question")

        content = data["choices"][0]["message"]["content"]
        print("INTENT CONTENT:", content, flush=True)

        intent_data = extract_json(content)

        if not intent_data or "intent" not in intent_data:
            return base_intent("general_health_question")

        return intent_data

    except Exception as e:
        print("INTENT ERROR:", str(e), flush=True)
        return base_intent("general_health_question")


def format_agent_response(user_message: str, tool_result: str):
    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """
You are the assistant inside a medical appointment app.
Use the provided database result to answer clearly.
Do not invent appointments, patient records, or medical history.
Do not diagnose or prescribe.
"""

    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"User asked: {user_message}\n\nDatabase result:\n{tool_result}"
            }
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()

        if "choices" not in data:
            return tool_result

        return data["choices"][0]["message"]["content"]

    except Exception:
        return tool_result