import sqlite3
import os
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "health_system.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes sqlite database tables for doctors and appointment slots."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            available_status TEXT DEFAULT 'Available'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointment_slots (
            id TEXT PRIMARY KEY,
            doctor_id TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            department TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            period TEXT NOT NULL, -- 'morning', 'afternoon', 'evening'
            is_available INTEGER DEFAULT 1,
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        )
    """)

    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM doctors")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_data(cursor)

    conn.commit()
    conn.close()


def seed_data(cursor: sqlite3.Cursor):
    """Seed sample doctors and time slots matching the requirements."""
    doctors = [
        ("doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Available"),
        ("doc-priya", "Dr. Priya Sharma", "General Medicine", "Available"),
        ("doc-arjun", "Dr. Arjun Reddy", "ENT", "Available"),
        ("doc-sneha", "Dr. Sneha Rao", "Dermatology", "Available"),
        ("doc-meera", "Dr. Meera Iyer", "Pediatrics", "Available"),
        ("doc-vikram", "Dr. Vikram Seth", "Orthopedics", "Available"),
        ("doc-alok", "Dr. Alok Verma", "Dental", "Available"),
        ("doc-kavita", "Dr. Kavita Menon", "Ophthalmology", "Available"),
    ]

    cursor.executemany(
        "INSERT INTO doctors (id, name, department, available_status) VALUES (?, ?, ?, ?)",
        doctors
    )

    # Sample Slots for Tomorrow (Oct 24)
    # Dr. Ravi Kumar: Morning, Afternoon, Evening (5:30 PM, 6:30 PM)
    # Dr. Priya Sharma: Morning, Evening (6:00 PM)
    slots = [
        # Dr. Ravi Kumar
        ("slot-r-1", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-r-2", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-r-3", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-r-4", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "5:30 PM", "evening", 1),
        ("slot-r-5", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "6:30 PM", "evening", 1),

        # Dr. Priya Sharma
        ("slot-p-1", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-p-2", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-p-3", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),

        # Dr. Arjun Reddy (ENT)
        ("slot-a-1", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-a-2", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "04:30 PM", "afternoon", 1),
        ("slot-a-3", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),

        # Dr. Sneha Rao (Dermatology)
        ("slot-s-1", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-s-2", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-s-3", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "5:00 PM", "evening", 1),
    ]

    cursor.executemany(
        """INSERT INTO appointment_slots
           (id, doctor_id, doctor_name, department, date, time, period, is_available)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        slots
    )


def query_doctors_and_slots(
    department: str,
    period_preference: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search available doctors and appointment slots for a given department and time preference.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find doctors in department
    cursor.execute(
        "SELECT id, name, department, available_status FROM doctors WHERE LOWER(department) = LOWER(?)",
        (department.strip(),)
    )
    doctor_rows = cursor.fetchall()

    if not doctor_rows:
        # Fallback partial match
        cursor.execute(
            "SELECT id, name, department, available_status FROM doctors WHERE LOWER(department) LIKE LOWER(?)",
            (f"%{department.strip()}%",)
        )
        doctor_rows = cursor.fetchall()

    result = []
    for doc in doctor_rows:
        doc_id = doc["id"]
        doc_name = doc["name"]

        # Filter slots by period if specified (morning, afternoon, evening)
        if period_preference:
            cursor.execute(
                """SELECT id, date, time, is_available FROM appointment_slots
                   WHERE doctor_id = ? AND LOWER(period) = LOWER(?) AND is_available = 1
                   ORDER BY id""",
                (doc_id, period_preference.strip())
            )
        else:
            cursor.execute(
                """SELECT id, date, time, is_available FROM appointment_slots
                   WHERE doctor_id = ? AND is_available = 1
                   ORDER BY id""",
                (doc_id,)
            )

        slots_rows = cursor.fetchall()
        slots_list = [s["time"] for s in slots_rows]
        slots_details = [
            {
                "id": s["id"],
                "doctor": doc_name,
                "date": s["date"],
                "time": s["time"],
                "isAvailable": bool(s["is_available"])
            }
            for s in slots_rows
        ]

        if slots_list:
            result.append({
                "id": doc_id,
                "name": doc_name,
                "department": doc["department"],
                "availableStatus": doc["available_status"],
                "slots": slots_list,
                "slotsDetails": slots_details,
            })

    conn.close()
    return result


# Initialize on import
init_db()
