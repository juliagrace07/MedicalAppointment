from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session
import models

from datetime import datetime

def get_doctor_upcoming_appointments(db: Session, doctor_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == doctor_id)
        .filter(models.Appointment.appointment_datetime >= datetime.now())
        .filter(models.Appointment.status == "booked")
        .order_by(models.Appointment.appointment_datetime)
        .all()
    )


from datetime import date

def get_doctor_all_appointments(db: Session, doctor_id: int):
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == doctor_id)
        .order_by(models.Appointment.appointment_datetime)
        .all()
    )


def get_doctor_all_patients(db: Session, doctor_id: int):
    appointments = (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == doctor_id)
        .all()
    )

    patients = {}
    for appt in appointments:
        patients[appt.patient.id] = appt.patient

    return list(patients.values())

def search_patients_by_condition(db: Session, condition: str):
    return (
        db.query(models.Patient)
        .filter(models.Patient.previous_health_history.ilike(f"%{condition}%"))
        .all()
    )


def search_patients_by_city(db: Session, city: str):
    return (
        db.query(models.Patient)
        .filter(models.Patient.address.ilike(f"%{city}%"))
        .all()
    )


def search_patients_under_age(db: Session, age_limit: int):
    patients = db.query(models.Patient).all()
    result = []

    today = date.today()

    for patient in patients:
        if not patient.date_of_birth:
            continue

        try:
            year, month, day = map(int, patient.date_of_birth.split("-"))
            dob = date(year, month, day)
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

            if age < age_limit:
                result.append(patient)

        except:
            continue

    return result

def get_doctor_by_user_id(db: Session, user_id: int):
    return db.query(models.Doctor).filter(models.Doctor.user_id == user_id).first()


def get_patient_by_user_id(db: Session, user_id: int):
    return db.query(models.Patient).filter(models.Patient.user_id == user_id).first()


def get_doctor_appointments_today(db: Session, doctor_id: int):
    today = date.today()

    start = datetime.combine(today, time.min)
    end = datetime.combine(today, time.max)

    appointments = (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == doctor_id)
        .filter(models.Appointment.appointment_datetime >= start)
        .filter(models.Appointment.appointment_datetime <= end)
        .filter(models.Appointment.status == "booked")
        .order_by(models.Appointment.appointment_datetime)
        .all()
    )

    return appointments


def get_doctor_next_appointment(db: Session, doctor_id: int):
    now = datetime.now()

    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.doctor_id == doctor_id)
        .filter(models.Appointment.appointment_datetime >= now)
        .filter(models.Appointment.status == "booked")
        .order_by(models.Appointment.appointment_datetime)
        .first()
    )

    return appointment


def get_patient_appointments(db: Session, patient_id: int):
    appointments = (
        db.query(models.Appointment)
        .filter(models.Appointment.patient_id == patient_id)
        .order_by(models.Appointment.appointment_datetime)
        .all()
    )

    return appointments


def get_all_doctors(db: Session):
    return db.query(models.Doctor).all()


def get_doctor_by_name(db: Session, doctor_name: str):
    doctors = db.query(models.Doctor).all()

    doctor_name_lower = doctor_name.lower()

    for doctor in doctors:
        if doctor.user.name.lower() in doctor_name_lower or doctor_name_lower in doctor.user.name.lower():
            return doctor

    return None


def get_doctor_schedule_summary(db: Session, doctor_id: int):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()

    if not doctor:
        return "Doctor not found."

    return {
        "doctor_name": doctor.user.name,
        "specialty": doctor.specialty,
        "available_days": doctor.available_days,
        "available_times": doctor.available_times
    }
    
from datetime import date


def calculate_age(date_of_birth: str):
    if not date_of_birth:
        return None

    try:
        year, month, day = map(int, date_of_birth.split("-"))
        dob = date(year, month, day)
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except:
        return None


def search_patients_generic(
    db: Session,
    condition: str | None = None,
    city: str | None = None,
    age_lt: int | None = None,
    age_gt: int | None = None,
    name: str | None = None
):
    patients = db.query(models.Patient).all()
    results = []

    condition = condition.lower().strip() if condition else None
    city = city.lower().strip() if city else None
    name = name.lower().strip() if name else None

    for patient in patients:
        patient_name = patient.user.name.lower() if patient.user and patient.user.name else ""
        address = patient.address.lower() if patient.address else ""
        history = patient.previous_health_history.lower() if patient.previous_health_history else ""
        age = calculate_age(patient.date_of_birth)

        if condition and condition not in history:
            continue

        if city and city not in address:
            continue

        if name and name not in patient_name:
            continue

        if age_lt is not None and (age is None or age >= age_lt):
            continue

        if age_gt is not None and (age is None or age <= age_gt):
            continue

        results.append({
            "name": patient.user.name,
            "phone": patient.phone,
            "address": patient.address,
            "date_of_birth": patient.date_of_birth,
            "age": age,
            "history": patient.previous_health_history
        })

    return results