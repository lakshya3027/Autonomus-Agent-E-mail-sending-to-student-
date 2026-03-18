from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import joblib

from database import engine, SessionLocal
from model import Base, Student

# ----------------------------
# Load ENV variables
# ----------------------------
load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

print("Loaded EMAIL:", EMAIL_ADDRESS)

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Create tables
# ----------------------------
Base.metadata.create_all(bind=engine)

# ----------------------------
# Load AI model
# ----------------------------
try:
    model = joblib.load("attendance_model.pkl")
    print("AI model loaded successfully")
except:
    model = None
    print("AI model not loaded")

# ----------------------------
# Database session
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Request models
# ----------------------------
class StudentData(BaseModel):
    roll_number: str
    name: str
    email: str
    attendance: int


class WarningRequest(BaseModel):
    students: List[StudentData]

# ----------------------------
# Root
# ----------------------------
@app.get("/")
def home():
    return {"message": "MentorLink Backend Running"}

# ----------------------------
# Save students
# ----------------------------
@app.post("/save-students")
def save_students(students: List[StudentData], db: Session = Depends(get_db)):

    for s in students:

        existing = db.query(Student).filter(
            Student.roll_number == s.roll_number
        ).first()

        if not existing:
            student = Student(
                roll_number=s.roll_number,
                name=s.name,
                email=s.email,
                attendance=s.attendance
            )

            db.add(student)

    db.commit()

    return {"message": "Students saved successfully"}

# ----------------------------
# Get students
# ----------------------------
@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).all()

# ----------------------------
# Send warnings
# ----------------------------
@app.post("/send-warnings")
def send_warnings(data: WarningRequest):

    sent_count = 0
    failed = []

    try:

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        for student in data.students:

            try:

                message = f"""
Dear {student.name},

Your attendance is {student.attendance}%.
It is below the required 75%.

Please improve your attendance.

Regards,
MentorLink
"""

                msg = MIMEText(message)

                msg["Subject"] = "Attendance Warning"
                msg["From"] = EMAIL_ADDRESS
                msg["To"] = student.email

                server.send_message(msg)

                sent_count += 1

            except Exception as e:
                print("Failed for:", student.email)
                print(e)
                failed.append(student.email)

        server.quit()

    except Exception as e:
        print("SMTP ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Warnings sent to {sent_count} students",
        "failed": failed
    }

# ----------------------------
# AI Prediction
# ----------------------------
@app.get("/predict-risk")
def predict_risk(db: Session = Depends(get_db)):

    if model is None:
        raise HTTPException(status_code=500, detail="AI model not loaded")

    students = db.query(Student).all()

    results = []

    for s in students:

        prediction = model.predict([[s.attendance]])[0]

        risk = "At Risk" if prediction == 1 else "Safe"

        results.append({
            "roll_number": s.roll_number,
            "name": s.name,
            "email": s.email,
            "attendance": s.attendance,
            "risk": risk
        })

    return results