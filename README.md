#  Medical Appointment Assistant

An AI-powered medical appointment management application that combines appointment scheduling with an intelligent healthcare assistant. The application provides a modern interface for managing patient appointments while leveraging Retrieval-Augmented Generation (RAG) to answer medical-related questions using a semantic knowledge base.

---

##  Overview

The Medical Appointment Assistant is a full-stack healthcare application designed to simplify appointment management while providing users with AI-assisted medical information. The backend is built using FastAPI, the frontend uses Streamlit, and PostgreSQL is used for persistent data storage. ChromaDB is integrated to cache AI responses and improve response times for repeated queries.

This project demonstrates modern software engineering practices including RESTful API development, authentication, containerization with Docker, database integration, and AI-powered semantic search.

---

##  Features

### Appointment Management

* Create new appointments
* View scheduled appointments
* Store appointment information in PostgreSQL
* RESTful API architecture

### AI Medical Assistant

* AI-powered healthcare question answering
* Semantic similarity search using ChromaDB
* Response caching to improve performance
* Retrieval-Augmented Generation (RAG) workflow

### Authentication

* User authentication
* Secure API endpoints
* Authorization support

### User Interface

* Interactive Streamlit web application
* Easy-to-use appointment management interface
* AI chatbot integration

### Containerized Deployment

* Docker support for frontend and backend
* Easy local deployment
* Consistent development environment

---

##  Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn
* SQLAlchemy
* PostgreSQL

### Frontend

* Streamlit

### AI & Data

* ChromaDB
* Vector similarity search

### DevOps

* Docker
* Docker Compose

---

##  Project Structure

```text
MedicalAppointment/
│
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── ai_service.py
│   ├── agent_service.py
│   ├── chroma_cache.py
│   ├── assistant_tools.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
│
└── README.md
```

---

##  Installation

### Clone the repository

```bash
git clone https://github.com/juliagrace07/MedicalAppointment.git
cd MedicalAppointment
```

---

### Backend Setup

```bash
cd backend

python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --reload
```

---

### Frontend Setup

Open a new terminal:

```bash
cd frontend

pip install -r requirements.txt

streamlit run app.py
```

---

##  Docker

Run the application using Docker:

```bash
docker compose up --build
```

---

##  AI Workflow

1. User submits a healthcare-related question.
2. The backend checks ChromaDB for a semantically similar cached response.
3. If a suitable cached answer exists, it is returned immediately.
4. Otherwise, the AI generates a new response.
5. The new response is stored in ChromaDB for future reuse.

This reduces response time while minimizing repeated AI processing.

---

##  API

Example endpoints include:

```
POST /appointments
GET /appointments
POST /login
POST /chat
```

---

##  Future Improvements

* Doctor availability management
* Email and SMS appointment reminders
* Patient medical history
* Prescription management
* Role-based access control
* Calendar integration
* Voice-enabled AI assistant
* Cloud deployment (Azure or AWS)
* Analytics dashboard for appointment trends

---

##  Learning Outcomes

This project strengthened my understanding of:

* REST API development
* FastAPI backend architecture
* Authentication and authorization
* Database modeling
* PostgreSQL integration
* Docker containerization
* Retrieval-Augmented Generation (RAG)
* Vector databases
* AI response caching
* Full-stack application development

---

##  Author

**Julia Grace Muddada**

* GitHub: https://github.com/juliagrace07
* LinkedIn: https://www.linkedin.com/in/julia-grace-muddada-6708271b3
