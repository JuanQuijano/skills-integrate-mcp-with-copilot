"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import json
import secrets
from copy import deepcopy
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

users_file = current_dir / "users.json"
sessions = {}
notifications = []
notification_id = 0


class LoginRequest(BaseModel):
    email: str
    password: str


def load_users():
    with users_file.open(encoding="utf-8") as file:
        return {user["email"]: user for user in json.load(file)}


def get_current_user(authorization: Annotated[str | None, Header()] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.removeprefix("Bearer ")
    user = sessions.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_role(role):
    def dependency(user=Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


def require_roles(*roles):
    def dependency(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


@app.post("/auth/login")
def login(credentials: LoginRequest):
    user = load_users().get(credentials.email)
    password_hash = hashlib.sha256(credentials.password.encode()).hexdigest()
    if not user or not secrets.compare_digest(user["password_hash"], password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = {"email": user["email"], "role": user["role"]}
    return {"token": token, "email": user["email"], "role": user["role"]}

DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


def build_activity_response(activity_name: str, activity: dict):
    participant_count = len(activity["participants"])
    seats_remaining = max(activity["max_participants"] - participant_count, 0)
    occupancy_rate = round((participant_count / activity["max_participants"]) * 100, 1)
    return {
        "name": activity_name,
        "description": activity["description"],
        "schedule": activity["schedule"],
        "max_participants": activity["max_participants"],
        "participants": list(activity["participants"]),
        "participants_count": participant_count,
        "seats_remaining": seats_remaining,
        "occupancy_rate": occupancy_rate,
    }


def build_activity_history():
    timestamp = current_timestamp()
    return {
        name: [{"timestamp": timestamp, "participant_count": len(details["participants"])}]
        for name, details in activities.items()
    }


def record_activity_history(activity_name: str):
    activity_history[activity_name].append(
        {
            "timestamp": current_timestamp(),
            "participant_count": len(activities[activity_name]["participants"]),
        }
    )


def add_notification(audience: str, message: str, activity_name: str, student_email: str | None = None):
    global notification_id
    notification_id += 1
    notifications.insert(
        0,
        {
            "id": notification_id,
            "audience": audience,
            "message": message,
            "activity_name": activity_name,
            "student_email": student_email,
            "timestamp": current_timestamp(),
        },
    )


activities = deepcopy(DEFAULT_ACTIVITIES)
activity_history = build_activity_history()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return {
        activity_name: build_activity_response(activity_name, activity)
        for activity_name, activity in activities.items()
    }


@app.get("/notifications")
def get_notifications(user=Depends(get_current_user)):
    if user["role"] in {"staff", "coordinator"}:
        relevant_notifications = [
            notification for notification in notifications if notification["audience"] == "coordinator"
        ]
    else:
        relevant_notifications = [
            notification
            for notification in notifications
            if notification["audience"] == "student" and notification["student_email"] == user["email"]
        ]
    return {"notifications": relevant_notifications[:10]}


@app.get("/coordinator/dashboard")
def get_coordinator_dashboard(user=Depends(require_roles("staff", "coordinator"))):
    del user
    activity_summaries = [
        {
            **build_activity_response(activity_name, activity),
            "history": list(activity_history[activity_name]),
        }
        for activity_name, activity in activities.items()
    ]
    popular_activities = sorted(
        activity_summaries,
        key=lambda activity: (-activity["participants_count"], activity["name"]),
    )
    total_participants = sum(activity["participants_count"] for activity in activity_summaries)
    total_seats_remaining = sum(activity["seats_remaining"] for activity in activity_summaries)
    return {
        "generated_at": current_timestamp(),
        "overview": {
            "total_activities": len(activity_summaries),
            "total_participants": total_participants,
            "total_seats_remaining": total_seats_remaining,
            "full_activities": sum(activity["seats_remaining"] == 0 for activity in activity_summaries),
        },
        "popular_activities": [
            {
                "name": activity["name"],
                "participants_count": activity["participants_count"],
                "seats_remaining": activity["seats_remaining"],
                "occupancy_rate": activity["occupancy_rate"],
            }
            for activity in popular_activities[:5]
        ],
        "activities": popular_activities,
    }


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str,
                        user=Depends(require_role("student"))):
    """Sign up a student for an activity"""
    if email != user["email"]:
        raise HTTPException(status_code=403, detail="Students can only manage their own registration")

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    if len(activity["participants"]) >= activity["max_participants"]:
        raise HTTPException(status_code=400, detail="Activity is full")

    # Add student
    activity["participants"].append(email)
    record_activity_history(activity_name)
    add_notification("student", f"You're confirmed for {activity_name}.", activity_name, email)
    add_notification("coordinator", f"{email} signed up for {activity_name}.", activity_name, email)
    if len(activity["participants"]) == activity["max_participants"]:
        add_notification("coordinator", f"{activity_name} is now full.", activity_name)

    return {
        "message": f"Signed up {email} for {activity_name}",
        "seats_remaining": max(activity["max_participants"] - len(activity["participants"]), 0),
    }


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str,
                             user=Depends(require_role("staff"))):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    record_activity_history(activity_name)
    add_notification("student", f"Your registration for {activity_name} was canceled.", activity_name, email)
    add_notification("coordinator", f"{email} was removed from {activity_name}.", activity_name, email)
    return {
        "message": f"Unregistered {email} from {activity_name}",
        "seats_remaining": max(activity["max_participants"] - len(activity["participants"]), 0),
    }
