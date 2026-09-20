import sqlite3
import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.db.postgres import postgres_service

logger = logging.getLogger(__name__)

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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            dob TEXT,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medical_documents (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT DEFAULT 'application/pdf',
            document_type TEXT NOT NULL,
            processing_status TEXT NOT NULL,
            extracted_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def revalidate_slot(doctor_id: str, time_query: str) -> Dict[str, Any]:
    """
    Revalidates the current availability of a specific slot immediately before booking.
    Returns whether it is currently available, the slot id, and alternative available slots.
    """
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    normalized_time = time_query.strip().upper()
    if normalized_time in ["6 PM", "6PM", "18:00"]:
        normalized_time = "6:00 PM"
    elif normalized_time in ["5:30 PM", "5:30PM", "17:30"]:
        normalized_time = "5:30 PM"
    elif normalized_time in ["6:30 PM", "6:30PM", "18:30"]:
        normalized_time = "6:30 PM"
    elif normalized_time in ["10 AM", "10AM"]:
        normalized_time = "10:00 AM"

    stripped_time = re.sub(r"^0", "", normalized_time)
    padded_time = f"0{stripped_time}" if len(stripped_time) < 8 else stripped_time

    cursor.execute(
        """SELECT id, time, is_available FROM appointment_slots
           WHERE doctor_id = ? AND (time = ? OR time = ? OR time = ?)""",
        (doctor_id, normalized_time, stripped_time, padded_time)
    )
    slot_row = cursor.fetchone()

    cursor.execute(
        """SELECT time FROM appointment_slots WHERE doctor_id = ? AND is_available = 1""",
        (doctor_id,)
    )
    alt_slots = [r["time"] for r in cursor.fetchall()]
    conn.close()

    if not slot_row:
        return {
            "is_available": False,
            "slot_id": None,
            "normalized_time": normalized_time,
            "alternatives": alt_slots,
            "reason": "Not found"
        }

    is_avail = bool(slot_row["is_available"] == 1)
    filtered_alts = [t for t in alt_slots if t != normalized_time]

    return {
        "is_available": is_avail,
        "slot_id": slot_row["id"],
        "normalized_time": normalized_time,
        "alternatives": filtered_alts,
        "reason": "Already booked" if not is_avail else None
    }


def book_appointment(
    session_id: str,
    doctor_query: str,
    time_query: str,
    date_query: Optional[str] = "tomorrow"
) -> Dict[str, Any]:
    """
    Validates doctor, date, and time slot. Revalidates availability and creates appointment.
    If unavailable, returns available alternatives.
    Stores confirmed appointment in PostgreSQL (with SQLite dual-storage).
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

    # 2 & 3. Revalidate Slot Availability
    reval = revalidate_slot(doctor["id"], normalized_time)
    if not reval["is_available"] or not reval["slot_id"]:
        conn.close()
        return {
            "success": False,
            "error": f"The slot at {normalized_time} is already booked or no longer available for {doctor['name']}.",
            "alternatives": reval["alternatives"],
            "doctor": doctor["name"]
        }

    slot_id = reval["slot_id"]

    # 4. Mark slot as booked
    cursor.execute(
        "UPDATE appointment_slots SET is_available = 0 WHERE id = ?",
        (slot_id,)
    )

    # 5. Create Appointment Record in SQLite
    appt_id = f"appt_{session_id}_{slot_id}"
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

    # 6. Store final appointment in PostgreSQL
    appt_record = {
        "id": appt_id,
        "session_id": session_id,
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "department": doctor["department"],
        "date": iso_date,
        "display_date": display_date,
        "time": normalized_time,
        "status": "Booked"
    }
    postgres_service.save_final_appointment(appt_record)

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
    """Cancels active appointment for the session and frees up the slot in PostgreSQL & SQLite."""
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

    # Mark appointment cancelled in SQLite
    cursor.execute(
        "UPDATE appointments SET status = 'Cancelled' WHERE id = ?",
        (row["id"],)
    )

    conn.commit()
    conn.close()

    # Cancel in PostgreSQL
    postgres_service.cancel_appointment(session_id)

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


def create_user_record(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a user record in both SQLite and PostgreSQL (dual-storage).
    Raises ValueError if email is already registered.
    """
    init_db()
    email_clean = user_data["email"].strip().lower()

    # Check existence
    existing = get_user_by_email(email_clean)
    if existing:
        raise ValueError("An account with this email address already exists.")

    user_id = user_data.get("id") or f"usr_{uuid.uuid4().hex[:12]}"
    record = {
        "id": user_id,
        "full_name": user_data["full_name"].strip(),
        "email": email_clean,
        "phone": user_data["phone"].strip(),
        "dob": user_data.get("dob"),
        "password_hash": user_data["password_hash"],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Store in SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, full_name, email, phone, dob, password_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["id"],
        record["full_name"],
        record["email"],
        record["phone"],
        record["dob"],
        record["password_hash"],
        record["created_at"],
        record["updated_at"]
    ))
    conn.commit()
    conn.close()

    # Dual-store in PostgreSQL if connected
    try:
        postgres_service.create_user(record)
    except Exception as e:
        logger.warning("Postgres user dual-storage notice: %s", str(e))

    return record


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves user by email, checking PostgreSQL first, with SQLite fallback."""
    init_db()
    email_clean = email.strip().lower()

    # Try PostgreSQL first
    try:
        pg_user = postgres_service.get_user_by_email(email_clean)
        if pg_user:
            return pg_user
    except Exception:
        pass

    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email_clean,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user by ID, checking PostgreSQL first, with SQLite fallback."""
    init_db()

    try:
        pg_user = postgres_service.get_user_by_id(user_id)
        if pg_user:
            return pg_user
    except Exception:
        pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


# ── Medical Document Repository Methods ────────────────────────────────────────

def create_medical_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Persists medical document metadata and extracted structured analysis."""
    import json
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    extracted_json = json.dumps(doc.get("extracted_data", {})) if isinstance(doc.get("extracted_data"), (dict, list)) else (doc.get("extracted_data") or "{}")

    cursor.execute("""
        INSERT INTO medical_documents (
            id, user_id, file_name, file_size, file_path, mime_type,
            document_type, processing_status, extracted_data, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (
        doc["id"],
        doc.get("user_id"),
        doc["file_name"],
        doc["file_size"],
        doc["file_path"],
        doc.get("mime_type", "application/pdf"),
        doc.get("document_type", "OTHER"),
        doc.get("processing_status", "COMPLETED"),
        extracted_json,
    ))
    conn.commit()
    conn.close()
    return get_medical_document(doc["id"])


def get_medical_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a medical document record by its ID."""
    import json
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medical_documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    record = dict(row)
    if record.get("extracted_data") and isinstance(record["extracted_data"], str):
        try:
            record["extracted_data"] = json.loads(record["extracted_data"])
        except Exception:
            pass
    return record


def list_medical_documents(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all medical documents, optionally filtered by user_id."""
    import json
    init_db()

    conn = get_db_connection()
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT * FROM medical_documents WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    else:
        cursor.execute("SELECT * FROM medical_documents ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        item = dict(r)
        if item.get("extracted_data") and isinstance(item["extracted_data"], str):
            try:
                item["extracted_data"] = json.loads(item["extracted_data"])
            except Exception:
                pass
        results.append(item)
    return results


def delete_medical_document(doc_id: str) -> bool:
    """Deletes a medical document record by ID."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medical_documents WHERE id = ?", (doc_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


