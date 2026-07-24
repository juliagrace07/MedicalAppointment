from pydantic import BaseModel
from datetime import datetime


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str
    phone: str | None = None
    address: str | None = None
    previous_health_history: str | None = None
    specialty: str | None = None
    available_days: str | None = None
    available_times: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_datetime: datetime
    reason_for_visit: str


class AppointmentUpdate(BaseModel):
    appointment_datetime: datetime | None = None
    status: str | None = None
    notes: str | None = None


class ChatRequest(BaseModel):
    messages: list
    user_id: int | None = None
    role: str | None = None


class IntentRequest(BaseModel):
    message: str


class SummaryRequest(BaseModel):
    text: str
    
