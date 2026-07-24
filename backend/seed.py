from datetime import datetime
from database import SessionLocal, Base, engine
import models
from auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("Connected to database", flush=True)

try:
    doctor_user = db.query(models.User).filter(
        models.User.email == "doctor@test.com"
    ).first()

    if not doctor_user:
        doctor_user = models.User(
            name="Dr. Emily Smith",
            email="doctor@test.com",
            password_hash=hash_password("test123"),
            role="doctor"
        )
        db.add(doctor_user)
        db.commit()
        db.refresh(doctor_user)

    doctor = db.query(models.Doctor).filter(
        models.Doctor.user_id == doctor_user.id
    ).first()

    if not doctor:
        doctor = models.Doctor(
            user_id=doctor_user.id,
            specialty="Cardiology",
            available_days="Mon-Fri",
            available_times="9AM-5PM"
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)

    patient_user = db.query(models.User).filter(
        models.User.email == "patient@test.com"
    ).first()

    if not patient_user:
        patient_user = models.User(
            name="Sarah Johnson",
            email="patient@test.com",
            password_hash=hash_password("test123"),
            role="patient"
        )
        db.add(patient_user)
        db.commit()
        db.refresh(patient_user)

    patient = db.query(models.Patient).filter(
        models.Patient.user_id == patient_user.id
    ).first()

    if not patient:
        patient = models.Patient(
            user_id=patient_user.id,
            phone="555-1234",
            address="123 Main Street, Dayton, OH",
            previous_health_history="Hypertension, diabetes, previous knee surgery."
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)

    existing_appointment = db.query(models.Appointment).filter(
        models.Appointment.patient_id == patient.id,
        models.Appointment.doctor_id == doctor.id
    ).first()

    if not existing_appointment:
        appointment = models.Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_datetime=datetime(2026, 5, 6, 10, 30),
            status="booked",
            reason_for_visit="Follow-up visit",
            notes="Patient reports mild discomfort."
        )
        db.add(appointment)
        db.commit()

    print("Seed complete", flush=True)

except Exception as e:
    db.rollback()
    print("ERROR:", e, flush=True)

finally:
    db.close()