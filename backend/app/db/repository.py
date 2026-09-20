import sqlite3
import os
import re
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(__file__), "health_system.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes sqlite database tables for doctors, appointment slots, and bookings."""
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            department TEXT NOT NULL,
            date TEXT NOT NULL,
            display_date TEXT NOT NULL,
            time TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            session_id TEXT PRIMARY KEY,
            name TEXT DEFAULT 'Sarah Connor',
            age INTEGER DEFAULT 32,
            phone TEXT DEFAULT '+1 (555) 019-2834',
            preferred_department TEXT DEFAULT ''
        )
    """)

    # Seed data if empty
    cursor.execute("SELECT COUNT(*) FROM doctors")
    count = cursor.fetchone()[0]
    if count == 0:
        seed_data(cursor)
    else:
        # Check if 6:00 PM slot exists for Dr. Ravi, if not add it
        cursor.execute("SELECT COUNT(*) FROM appointment_slots WHERE doctor_id='doc-ravi' AND time='6:00 PM'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO appointment_slots
                (id, doctor_id, doctor_name, department, date, time, period, is_available)
                VALUES ('slot-r-6', 'doc-ravi', 'Dr. Ravi Kumar', 'General Medicine', 'Tomorrow, Oct 24', '6:00 PM', 'evening', 1)
            """)

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

    slots = [
        # Dr. Ravi Kumar
        ("slot-r-1", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-r-2", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-r-3", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-r-4", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "5:30 PM", "evening", 1),
        ("slot-r-6", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),
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
    """Search available doctors and appointment slots for a given department and time preference."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, department, available_status FROM doctors WHERE LOWER(department) LIKE LOWER(?)",
        (f"%{department.strip()}%",)
    )
    doctor_rows = cursor.fetchall()

    result = []
    for doc in doctor_rows:
        doc_id = doc["id"]
        doc_name = doc["name"]

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


def find_doctor_by_name(doctor_query: str) -> Optional[Dict[str, Any]]:
    """Match doctor by query like 'Ravi', 'Dr. Ravi', or 'Dr. Ravi Kumar'."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cleaned = re.sub(r"^(dr\.?|doctor)\s*", "", doctor_query.strip(), flags=re.IGNORECASE).strip()
    cursor.execute(
        "SELECT id, name, department, available_status FROM doctors WHERE LOWER(name) LIKE LOWER(?)",
        (f"%{cleaned}%",)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)

    # Fallback to provider service
    try:
        from app.services.provider_service import provider_service
        provider_docs = provider_service.search_doctors(query=cleaned)
        if provider_docs:
            p_doc = provider_docs[0]
            # Ensure inserted into local sqlite table if missing
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO doctors (id, name, department, available_status) VALUES (?, ?, ?, ?)",
                (p_doc["id"], p_doc["name"], p_doc["department"], p_doc.get("availableStatus", "Available"))
            )
            # Also insert slots
            p_slots = provider_service.get_available_slots(p_doc["id"])
            for s in p_slots:
                cursor.execute(
                    """INSERT OR IGNORE INTO appointment_slots
                       (id, doctor_id, doctor_name, department, date, time, period, is_available)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (s["id"], p_doc["id"], p_doc["name"], p_doc["department"], s.get("date", "Tomorrow, Oct 24"), s["time"], s.get("period", "evening"), 1 if s.get("isAvailable", True) else 0)
                )
            conn.commit()
            conn.close()
            return {
                "id": p_doc["id"],
                "name": p_doc["name"],
                "department": p_doc["department"],
                "available_status": p_doc.get("availableStatus", "Available"),
            }
    except Exception:
        pass

    return None


def book_appointment(
    session_id: str,
    doctor_query: str,
    time_query: str,
    date_query: Optional[str] = "tomorrow"
) -> Dict[str, Any]:
    """
    Validates doctor, date, and time slot. Checks availability and creates appointment.
    If unavailable, returns available alternatives.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Validate Doctor
    doctor = find_doctor_by_name(doctor_query)
    if not doctor:
        conn.close()
        return {
            "success": False,
            "error": f"Doctor '{doctor_query}' not found. Please choose from our available doctors."
        }

    # Normalize time query (e.g. '6 PM', '6:00 PM', '18:00')
    normalized_time = time_query.strip().upper()
    if normalized_time in ["6 PM", "6PM", "18:00"]:
        normalized_time = "6:00 PM"
    elif normalized_time in ["5:30 PM", "5:30PM", "17:30"]:
        normalized_time = "5:30 PM"
    elif normalized_time in ["6:30 PM", "6:30PM", "18:30"]:
        normalized_time = "6:30 PM"
    elif normalized_time in ["10 AM", "10AM"]:
        normalized_time = "10:00 AM"

    # Normalize date
    iso_date = "2026-09-21"
    display_date = "21 Sep 2026"
    if "today" in (date_query or "").lower():
        iso_date = "2026-09-20"
        display_date = "20 Sep 2026"

    # 2 & 3. Check Slot Availability
    stripped_time = re.sub(r"^0", "", normalized_time)
    padded_time = f"0{stripped_time}" if len(stripped_time) < 8 else stripped_time

    cursor.execute(
        """SELECT id, time, is_available FROM appointment_slots
           WHERE doctor_id = ? AND (time = ? OR time = ? OR time = ?)""",
        (doctor["id"], normalized_time, stripped_time, padded_time)
    )
    slot_row = cursor.fetchone()

    if not slot_row:
        # Check all available alternative slots for this doctor
        cursor.execute(
            """SELECT time FROM appointment_slots WHERE doctor_id = ? AND is_available = 1""",
            (doctor["id"],)
        )
        alt_slots = [r["time"] for r in cursor.fetchall()]
        conn.close()
        return {
            "success": False,
            "error": f"The requested slot ({normalized_time}) is not available for {doctor['name']}.",
            "alternatives": alt_slots,
            "doctor": doctor["name"]
        }

    if slot_row["is_available"] == 0:
        cursor.execute(
            """SELECT time FROM appointment_slots WHERE doctor_id = ? AND is_available = 1""",
            (doctor["id"],)
        )
        alt_slots = [r["time"] for r in cursor.fetchall()]
        conn.close()
        return {
            "success": False,
            "error": f"The slot at {normalized_time} is already booked.",
            "alternatives": alt_slots,
            "doctor": doctor["name"]
        }

    # 4. Mark slot as booked
    cursor.execute(
        "UPDATE appointment_slots SET is_available = 0 WHERE id = ?",
        (slot_row["id"],)
    )

    # 5. Create Appointment Record
    appt_id = f"appt_{session_id}_{slot_row['id']}"
    cursor.execute(
        """INSERT OR REPLACE INTO appointments
           (id, session_id, doctor_id, doctor_name, department, date, display_date, time, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            appt_id,
            session_id,
            doctor["id"],
            doctor["name"],
            doctor["department"],
            iso_date,
            display_date,
            normalized_time,
            "Booked"
        )
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "appointment": {
            "doctor": doctor["name"],
            "department": doctor["department"],
            "date": iso_date,
            "displayDate": display_date,
            "time": "18:00" if normalized_time == "6:00 PM" else normalized_time,
            "displayTime": normalized_time,
            "status": "Booked"
        }
    }


def cancel_appointment(session_id: str) -> Dict[str, Any]:
    """Cancels active appointment for the session and frees up the slot."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, doctor_id, time FROM appointments WHERE session_id = ? AND status = 'Booked'",
        (session_id,)
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return {
            "success": False,
            "error": "No active booked appointment found to cancel."
        }

    # Free up slot
    cursor.execute(
        "UPDATE appointment_slots SET is_available = 1 WHERE doctor_id = ? AND time = ?",
        (row["doctor_id"], row["time"])
    )

    # Mark appointment cancelled
    cursor.execute(
        "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
        (row["id"],)
    )

    conn.commit()
    conn.close()

    return {
        "success": True,
        "status": "Cancelled"
    }


def get_active_appointment(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve active appointment for a session."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT doctor_name, department, date, display_date, time, status
           FROM appointments WHERE session_id = ? AND status = 'Booked'
           ORDER BY id DESC LIMIT 1""",
        (session_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "doctor": row["doctor_name"],
            "department": row["department"],
            "date": row["date"],
            "displayDate": row["display_date"],
            "time": row["time"],
            "status": row["status"]
        }
    return None


def get_patient_info(session_id: str) -> Dict[str, Any]:
    """Retrieve basic demographic patient info for demo session."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, age, phone, preferred_department FROM patients WHERE session_id = ?",
        (session_id,)
    )
    row = cursor.fetchone()
    if not row:
        default_patient = ("Sarah Connor", 32, "+1 (555) 019-2834", "")
        cursor.execute(
            """INSERT OR REPLACE INTO patients
               (session_id, name, age, phone, preferred_department)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, *default_patient)
        )
        conn.commit()
        conn.close()
        return {
            "name": default_patient[0],
            "age": default_patient[1],
            "phone": default_patient[2],
            "preferred_department": default_patient[3],
        }

    conn.close()
    return dict(row)


def update_patient_info(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update patient basic info for session."""
    current = get_patient_info(session_id)
    new_name = updates.get("name", current.get("name"))
    new_age = updates.get("age", current.get("age"))
    new_phone = updates.get("phone", current.get("phone"))
    new_dept = updates.get("preferred_department", current.get("preferred_department"))

    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO patients (session_id, name, age, phone, preferred_department)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, new_name, new_age, new_phone, new_dept))
    conn.commit()
    conn.close()

    return {
        "name": new_name,
        "age": new_age,
        "phone": new_phone,
        "preferred_department": new_dept
    }
