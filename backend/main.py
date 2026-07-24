from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from datetime import datetime
from database import Base, engine, SessionLocal
from auth import hash_password, verify_password, create_token
from ai_service import call_mistral
from agent_service import detect_intent, format_agent_response

from assistant_tools import (
    get_doctor_by_user_id,
    get_patient_by_user_id,
    get_doctor_appointments_today,
    get_doctor_next_appointment,
    get_patient_appointments,
    get_all_doctors,
    search_patients_by_condition,
    search_patients_by_city,
    search_patients_under_age,
    search_patients_generic,
    get_doctor_all_appointments,
    get_doctor_all_patients,
    get_doctor_upcoming_appointments,
)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Medical Appointment App API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {"message": "Medical Appointment API is running"}


@app.post("/auth/signup")
def signup(request: schemas.SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == request.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        role=request.role
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    if request.role == "patient":
        patient = models.Patient(
            user_id=user.id,
            phone=request.phone,
            address=request.address,
            previous_health_history=request.previous_health_history
        )
        db.add(patient)

    elif request.role == "doctor":
        doctor = models.Doctor(
            user_id=user.id,
            specialty=request.specialty,
            available_days=request.available_days,
            available_times=request.available_times
        )
        db.add(doctor)

    db.commit()

    return {
        "message": "User created successfully",
        "user_id": user.id,
        "role": user.role
    }


@app.post("/auth/login")
def login(request: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    })

    profile_id = None

    if user.role == "patient":
        patient = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
        if patient:
            profile_id = patient.id

    elif user.role == "doctor":
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doctor:
            profile_id = doctor.id

    return {
        "access_token": token,
        "user_id": user.id,
        "profile_id": profile_id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    }


@app.get("/doctors")
def get_doctors_api(db: Session = Depends(get_db)):
    doctors = db.query(models.Doctor).all()

    result = []

    for doctor in doctors:
        result.append({
            "doctor_id": doctor.id,
            "name": doctor.user.name,
            "email": doctor.user.email,
            "specialty": doctor.specialty,
            "available_days": doctor.available_days,
            "available_times": doctor.available_times
        })

    return result


@app.get("/doctors/{doctor_id}/availability")
def get_doctor_availability(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    return {
        "doctor_id": doctor.id,
        "doctor_name": doctor.user.name,
        "specialty": doctor.specialty,
        "available_days": doctor.available_days,
        "available_times": doctor.available_times
    }


@app.post("/appointments")
def create_appointment(request: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == request.doctor_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    appt_dt = request.appointment_datetime
    appt_day = appt_dt.strftime("%a")  # Mon, Tue, Wed
    appt_time = appt_dt.time()

    # Basic availability rule for formats like Mon-Fri and 9AM-5PM
    available_days = (doctor.available_days or "").lower()
    available_times = (doctor.available_times or "").upper().replace(" ", "")

    weekday_order = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    appt_day_lower = appt_day.lower()

    allowed_day = False

    if "-" in available_days:
        start_day, end_day = available_days.split("-")
        start_day = start_day.strip()[:3]
        end_day = end_day.strip()[:3]

        if start_day in weekday_order and end_day in weekday_order:
            start_idx = weekday_order.index(start_day)
            end_idx = weekday_order.index(end_day)
            appt_idx = weekday_order.index(appt_day_lower)

            allowed_day = start_idx <= appt_idx <= end_idx

    else:
        allowed_day = appt_day_lower in available_days

    if not allowed_day:
        raise HTTPException(
            status_code=400,
            detail=f"Doctor is not available on {appt_day}."
        )

    def parse_hour(time_str):
        if "AM" in time_str:
            hour = int(time_str.replace("AM", ""))
            return 0 if hour == 12 else hour

        if "PM" in time_str:
            hour = int(time_str.replace("PM", ""))
            return 12 if hour == 12 else hour + 12

        return int(time_str)

    try:
        start_str, end_str = available_times.split("-")
        start_hour = parse_hour(start_str)
        end_hour = parse_hour(end_str)

        if not (start_hour <= appt_dt.hour < end_hour):
            raise HTTPException(
                status_code=400,
                detail=f"Doctor is only available during {doctor.available_times}."
            )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Doctor availability time format is invalid."
        )

    existing = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == request.doctor_id,
        models.Appointment.appointment_datetime == request.appointment_datetime,
        models.Appointment.status == "booked"
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="This time slot is already booked for the selected doctor."
        )

    appointment = models.Appointment(
        patient_id=request.patient_id,
        doctor_id=request.doctor_id,
        appointment_datetime=request.appointment_datetime,
        reason_for_visit=request.reason_for_visit,
        status="booked"
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    notification = models.Notification(
        appointment_id=appointment.id,
        message="Appointment booked successfully.",
        sent_status="pending"
    )

    db.add(notification)
    db.commit()

    return {
        "message": "Appointment booked successfully",
        "appointment_id": appointment.id
    }

@app.get("/appointments")
def get_all_appointments(db: Session = Depends(get_db)):
    appointments = db.query(models.Appointment).all()

    result = []

    for appt in appointments:
        result.append({
            "appointment_id": appt.id,
            "patient_name": appt.patient.user.name,
            "doctor_name": appt.doctor.user.name,
            "specialty": appt.doctor.specialty,
            "appointment_datetime": appt.appointment_datetime,
            "status": appt.status,
            "reason_for_visit": appt.reason_for_visit,
            "notes": appt.notes
        })

    return result


@app.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return {
        "appointment_id": appt.id,
        "patient_name": appt.patient.user.name,
        "patient_email": appt.patient.user.email,
        "patient_phone": appt.patient.phone,
        "patient_address": appt.patient.address,
        "previous_health_history": appt.patient.previous_health_history,
        "doctor_name": appt.doctor.user.name,
        "specialty": appt.doctor.specialty,
        "appointment_datetime": appt.appointment_datetime,
        "status": appt.status,
        "reason_for_visit": appt.reason_for_visit,
        "notes": appt.notes
    }


@app.get("/patients/{patient_id}/appointments")
def get_patient_appointments_api(patient_id: int, db: Session = Depends(get_db)):
    appointments = db.query(models.Appointment).filter(
    models.Appointment.patient_id == patient_id,
    models.Appointment.appointment_datetime >= datetime.now(),
    models.Appointment.status == "booked"
).order_by(models.Appointment.appointment_datetime).all()

    result = []

    for appt in appointments:
        result.append({
            "appointment_id": appt.id,
            "doctor_name": appt.doctor.user.name,
            "specialty": appt.doctor.specialty,
            "appointment_datetime": appt.appointment_datetime,
            "status": appt.status,
            "reason_for_visit": appt.reason_for_visit
        })

    return result


@app.get("/doctors/{doctor_id}/appointments")
def get_doctor_appointments_api(doctor_id: int, db: Session = Depends(get_db)):
    appointments = db.query(models.Appointment).filter(
    models.Appointment.doctor_id == doctor_id,
    models.Appointment.appointment_datetime >= datetime.now(),
    models.Appointment.status == "booked"
).order_by(models.Appointment.appointment_datetime).all()

    result = []

    for appt in appointments:
        result.append({
            "appointment_id": appt.id,
            "patient_name": appt.patient.user.name,
            "patient_phone": appt.patient.phone,
            "appointment_datetime": appt.appointment_datetime,
            "status": appt.status,
            "reason_for_visit": appt.reason_for_visit,
            "previous_health_history": appt.patient.previous_health_history
        })

    return result


@app.put("/appointments/{appointment_id}")
def update_appointment(
    appointment_id: int,
    request: schemas.AppointmentUpdate,
    db: Session = Depends(get_db)
):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if request.appointment_datetime:
        appt.appointment_datetime = request.appointment_datetime

    if request.status:
        appt.status = request.status

    if request.notes:
        appt.notes = request.notes

    db.commit()

    return {"message": "Appointment updated successfully"}


@app.delete("/appointments/{appointment_id}")
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appt = db.query(models.Appointment).filter(models.Appointment.id == appointment_id).first()

    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appt.status = "cancelled"
    db.commit()

    return {"message": "Appointment cancelled successfully"}


@app.post("/ai/chat")
def ai_chat(request: schemas.ChatRequest, db: Session = Depends(get_db)):

    messages = request.messages
    user_id = request.user_id
    role = request.role

    latest_message = ""

    for msg in reversed(messages):
        if msg["role"] == "user":
            latest_message = msg["content"]
            break

    intent_data = detect_intent(latest_message, role)

    if not intent_data:
        intent_data = {
            "intent": "general_health_question",
            "condition": None,
            "city": None,
            "age_lt": None,
            "age_gt": None,
            "name": None,
            "doctor_name": None,
            "time_preference": None,
            "date_preference": None
        }

    intent = intent_data.get("intent")

    print("AGENT INTENT:", intent_data, flush=True)

    # ---------------- PATIENT RECORD SEARCH TOOLS ----------------

    if role in ["doctor", "admin"] and intent == "search_patients":

        patients = search_patients_generic(
            db=db,
            condition=intent_data.get("condition"),
            city=intent_data.get("city"),
            age_lt=intent_data.get("age_lt"),
            age_gt=intent_data.get("age_gt"),
            name=intent_data.get("name")
        )

        if not patients:
            tool_result = "No matching patients found."

        else:
            tool_result = "Matching patients:\n"

            for patient in patients:
                tool_result += (
                    f"- {patient['name']} | "
                    f"Age: {patient['age']} | "
                    f"DOB: {patient['date_of_birth']} | "
                    f"Phone: {patient['phone']} | "
                    f"Address: {patient['address']} | "
                    f"History: {patient['history']}\n"
                )

        answer = format_agent_response(latest_message, tool_result)

        return {"response": answer}
    
    if role in ["doctor", "admin"]:

        if intent == "patient_search_by_condition":
            condition = intent_data.get("condition")

            patients = search_patients_by_condition(db, condition)

            if not patients:
                tool_result = f"No patients found with condition/history containing: {condition}"
            else:
                tool_result = f"Patients with {condition}:\n"
                for patient in patients:
                    tool_result += (
                        f"- {patient.user.name} | "
                        f"Phone: {patient.phone} | "
                        f"Address: {patient.address} | "
                        f"History: {patient.previous_health_history}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "patient_search_by_city":
            city = intent_data.get("city")

            patients = search_patients_by_city(db, city)

            if not patients:
                tool_result = f"No patients found in: {city}"
            else:
                tool_result = f"Patients in {city}:\n"
                for patient in patients:
                    tool_result += (
                        f"- {patient.user.name} | "
                        f"Phone: {patient.phone} | "
                        f"Address: {patient.address} | "
                        f"History: {patient.previous_health_history}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "patient_search_by_age":
            age_limit = intent_data.get("age_limit")

            patients = search_patients_under_age(db, int(age_limit))

            if not patients:
                tool_result = f"No patients found under age {age_limit}."
            else:
                tool_result = f"Patients under age {age_limit}:\n"
                for patient in patients:
                    tool_result += (
                        f"- {patient.user.name} | "
                        f"DOB: {patient.date_of_birth} | "
                        f"Phone: {patient.phone} | "
                        f"Address: {patient.address}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}
        

    # ---------------- DOCTOR TOOLS ----------------
    if role == "doctor":
        doctor = get_doctor_by_user_id(db, user_id)

        if intent == "doctor_upcoming_appointments":
            appointments = get_doctor_upcoming_appointments(db, doctor.id)

            if not appointments:
                tool_result = "The doctor has no upcoming booked appointments."
            else:
                tool_result = "Upcoming appointments:\n"
                for appt in appointments:
                    tool_result += (
                        f"- {appt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} | "
                        f"Patient: {appt.patient.user.name} | "
                        f"Reason: {appt.reason_for_visit} | "
                        f"Status: {appt.status}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "doctor_all_patients":
            patients = get_doctor_all_patients(db, doctor.id)

            if not patients:
                tool_result = "No patients found for this doctor."
            else:
                tool_result = "Patients assigned to this doctor:\n"
                for patient in patients:
                    tool_result += (
                        f"- {patient.user.name} | "
                        f"Phone: {patient.phone} | "
                        f"Address: {patient.address} | "
                        f"DOB: {patient.date_of_birth} | "
                        f"History: {patient.previous_health_history}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}
        
        if not doctor:
            return {"response": "I could not find your doctor profile."}

        if intent == "doctor_schedule_today":
            appointments = get_doctor_appointments_today(db, doctor.id)

            if not appointments:
                tool_result = "The doctor has no booked appointments today."
            else:
                tool_result = "Today's appointments:\n"
                for appt in appointments:
                    tool_result += (
                        f"- {appt.appointment_datetime.strftime('%I:%M %p')} | "
                        f"Patient: {appt.patient.user.name} | "
                        f"Reason: {appt.reason_for_visit} | "
                        f"Status: {appt.status}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "doctor_next_patient":
            appt = get_doctor_next_appointment(db, doctor.id)

            if not appt:
                tool_result = "No upcoming booked appointment found."
            else:
                tool_result = (
                    f"Next appointment:\n"
                    f"Patient: {appt.patient.user.name}\n"
                    f"Time: {appt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}\n"
                    f"Reason: {appt.reason_for_visit}\n"
                    f"Status: {appt.status}"
                )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "doctor_next_patient_history":
            appt = get_doctor_next_appointment(db, doctor.id)

            if not appt:
                tool_result = "No upcoming patient found."
            else:
                tool_result = (
                    f"Next patient: {appt.patient.user.name}\n"
                    f"Appointment time: {appt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}\n"
                    f"Reason for visit: {appt.reason_for_visit}\n"
                    f"Previous health history: {appt.patient.previous_health_history}"
                )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

    # ---------------- PATIENT TOOLS ----------------
    if role == "patient":
        patient = get_patient_by_user_id(db, user_id)

        if not patient:
            return {"response": "I could not find your patient profile."}

        if intent == "patient_my_appointments":
            appointments = get_patient_appointments(db, patient.id)

            if not appointments:
                tool_result = "The patient has no appointments."
            else:
                tool_result = "Patient appointments:\n"
                for appt in appointments:
                    tool_result += (
                        f"- {appt.appointment_datetime.strftime('%B %d, %Y at %I:%M %p')} | "
                        f"Doctor: {appt.doctor.user.name} | "
                        f"Specialty: {appt.doctor.specialty} | "
                        f"Reason: {appt.reason_for_visit} | "
                        f"Status: {appt.status}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}
        
        if intent == "patient_cancel_appointment_help":
            return {
                "response": (
                    "Yes, you can cancel an appointment from the My Appointments tab. "
                    "Select the appointment from the cancel dropdown and click Cancel Selected Appointment."
                )
            }        

        if intent == "patient_available_doctors":
            doctors = get_all_doctors(db)

            if not doctors:
                tool_result = "No doctors found."
            else:
                tool_result = "Available doctors:\n"
                for doctor in doctors:
                    tool_result += (
                        f"- {doctor.user.name} | "
                        f"Specialty: {doctor.specialty} | "
                        f"Available days: {doctor.available_days} | "
                        f"Available times: {doctor.available_times}\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

        if intent == "patient_open_slots":
            doctors = get_all_doctors(db)

            if not doctors:
                tool_result = "No doctors found."
            else:
                tool_result = "Doctor schedule information:\n"
                for doctor in doctors:
                    tool_result += (
                        f"- {doctor.user.name} ({doctor.specialty}) is generally available "
                        f"{doctor.available_days}, {doctor.available_times}.\n"
                    )

            answer = format_agent_response(latest_message, tool_result)
            return {"response": answer}

    # ---------------- GENERAL HEALTH CHAT ----------------
    reply = call_mistral(messages)
    return {"response": reply}