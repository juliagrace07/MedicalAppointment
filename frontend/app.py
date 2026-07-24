import streamlit as st
import requests
from datetime import datetime
import pandas as pd

API_URL = "http://backend:8000"

st.set_page_config(page_title="Medical App", layout="wide")

st.title("🏥 Medical Appointment System")

menu = st.sidebar.selectbox("Menu", ["Login", "Signup"])

# ------------------ SIGNUP ------------------
if menu == "Signup":
    st.subheader("Create Account")

    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["patient", "doctor"])

    if role == "patient":
        phone = st.text_input("Phone")
        address = st.text_input("Address")
        history = st.text_area("Previous Health History")

    if role == "doctor":
        specialty = st.text_input("Specialty")
        available_days = st.text_input("Available Days (e.g., Mon-Fri)")
        available_times = st.text_input("Available Times (e.g., 9AM-5PM)")

    if st.button("Signup"):
        payload = {
            "name": name,
            "email": email,
            "password": password,
            "role": role
        }

        if role == "patient":
            payload.update({
                "phone": phone,
                "address": address,
                "previous_health_history": history
            })

        if role == "doctor":
            payload.update({
                "specialty": specialty,
                "available_days": available_days,
                "available_times": available_times
            })

        response = requests.post(f"{API_URL}/auth/signup", json=payload)

        if response.status_code == 200:
            st.success("Signup successful!")
        else:
            try:
                st.error(response.json())
            except:
                st.error(response.text)

# ------------------ LOGIN ------------------
if menu == "Login":
    st.subheader("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password}
        )

        if response.status_code == 200:
            data = response.json()
            st.session_state["user"] = data
            st.success(f"Welcome {data['name']} ({data['role']})")
        else:
            st.error("Invalid credentials")

# ------------------ AFTER LOGIN ------------------
if "user" in st.session_state:

    user = st.session_state["user"]

    st.sidebar.success(f"Logged in as {user['name']}")

    if st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.rerun()

    # ------------------ PATIENT ------------------
    if user["role"] == "patient":

        st.header("Patient Dashboard")

        tab1, tab2, tab3 = st.tabs([
            "Book Appointment",
            "My Appointments",
            "AI Assistant"
        ])

        # -------- BOOK APPOINTMENT --------
        with tab1:
            st.subheader("📅 Book Appointment")

            try:
                doctors = requests.get(f"{API_URL}/doctors").json()
            except:
                doctors = []

            if not doctors:
                st.warning("No doctors available.")
            else:
                doctor_names = [
                    f"{d['name']} ({d['specialty']})" for d in doctors
                ]

                selected = st.selectbox("Choose Doctor", doctor_names)

                doctor = doctors[doctor_names.index(selected)]

                st.info(
                    f"Available: {doctor['available_days']} | {doctor['available_times']}"
                )

                appointment_date = st.date_input("Select Date")
                appointment_time = st.time_input("Select Time")

                reason = st.text_area("Reason for visit")

                if st.button("Book Appointment"):
                    appointment_datetime = datetime.combine(
                        appointment_date,
                        appointment_time
                    )

                    payload = {
                        "patient_id": user["profile_id"],
                        "doctor_id": doctor["doctor_id"],
                        "appointment_datetime": appointment_datetime.isoformat(),
                        "reason_for_visit": reason
                    }

                    res = requests.post(
                        f"{API_URL}/appointments",
                        json=payload
                    )

                    if res.status_code == 200:
                        st.success("Appointment booked successfully!")
                    else:
                        try:
                              st.error(res.json()["detail"])
                        except:
                              st.error(res.text)

        # -------- MY APPOINTMENTS --------
        with tab2:
            st.subheader("My Appointments")

            res = requests.get(
                f"{API_URL}/patients/{user['profile_id']}/appointments"
            )

            if res.status_code == 200:
                appointments = res.json()

                if appointments:
                    df = pd.DataFrame(appointments)
                    st.dataframe(df, use_container_width=True)

                    st.subheader("Cancel Appointment")

                    appointment_options = {
                        f"{appt['appointment_datetime']} with {appt['doctor_name']}": appt["appointment_id"]
                        for appt in appointments
                    }

                    selected_appt = st.selectbox(
                        "Select appointment to cancel",
                        list(appointment_options.keys())
                    )

                    if st.button("Cancel Selected Appointment"):
                        appt_id = appointment_options[selected_appt]

                        cancel_res = requests.delete(
                            f"{API_URL}/appointments/{appt_id}"
                        )

                        if cancel_res.status_code == 200:
                            st.success("Appointment cancelled successfully.")
                            st.rerun()
                        else:
                            st.error("Could not cancel appointment.")
                else:
                    st.info("No upcoming appointments found.")
            else:
                st.error("Could not load appointments.")
                
        # -------- AI ASSISTANT --------
        # -------- AI ASSISTANT --------
        with tab3:

            st.subheader("🤖 AI Medical Assistant")

            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []

            # Display messages
            for message in st.session_state.chat_history:

                if message["role"] == "user":
                    st.chat_message("user").write(message["content"])

                elif message["role"] == "assistant":
                    st.chat_message("assistant").write(message["content"])

            user_input = st.chat_input("Ask a medical question")

            if user_input:

                # Add user message
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input
                })

                # Send full conversation to backend
                res = requests.post(
                    f"{API_URL}/ai/chat",
                    json={
                          "messages": st.session_state.chat_history,
                          "user_id": user["user_id"],
                          "role": user["role"]
                    }
                )

                if res.status_code == 200:

                    ai_reply = res.json()["response"]

                    # Add AI response
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": ai_reply
                    })

                    st.rerun()

                else:
                    st.error("AI failed")
    # ------------------ DOCTOR ------------------
        # ------------------ DOCTOR ------------------
    elif user["role"] == "doctor":

        st.header("Doctor Dashboard")

        doc_tab1, doc_tab2 = st.tabs(["My Schedule", "AI Assistant"])

        with doc_tab1:
           st.subheader("My Schedule")

           res = requests.get(
               f"{API_URL}/doctors/{user['profile_id']}/appointments"
            )

           if res.status_code == 200:
                appointments = res.json()
   
                if appointments:
                  df = pd.DataFrame(appointments)
                  st.dataframe(df, use_container_width=True)
                else:
                   st.info("No upcoming appointments.")
           else:
                st.error("Error loading data")

        with doc_tab2:
            st.subheader("🤖 Doctor AI Assistant")

            if "doctor_chat_history" not in st.session_state:
                st.session_state.doctor_chat_history = []

            for message in st.session_state.doctor_chat_history:
                if message["role"] == "user":
                    st.chat_message("user").write(message["content"])
                elif message["role"] == "assistant":
                    st.chat_message("assistant").write(message["content"])

            doctor_input = st.chat_input("Ask about your schedule or patients")

            if doctor_input:
                st.session_state.doctor_chat_history.append({
                    "role": "user",
                    "content": doctor_input
                })

                res = requests.post(
                    f"{API_URL}/ai/chat",
                    json={
                        "messages": st.session_state.doctor_chat_history,
                        "user_id": user["user_id"],
                        "role": user["role"]
                    }
                )

                if res.status_code == 200:
                    reply = res.json()["response"]

                    st.session_state.doctor_chat_history.append({
                        "role": "assistant",
                        "content": reply
                    })

                    st.rerun()
                else:
                    st.error("AI failed")