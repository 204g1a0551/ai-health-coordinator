import sqlite3
import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.db.postgres import postgres_service
from app.security.crypto import crypto_service
from app.security.consent_manager import consent_manager

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
            role TEXT DEFAULT 'PATIENT',
            abha_id TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ensure role, abha_id, is_active exist on older sqlite DBs
    for col_def in [
        "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'PATIENT'",
        "ALTER TABLE users ADD COLUMN abha_id TEXT",
        "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1"
    ]:
        try:
            cursor.execute(col_def)
        except Exception:
            pass

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

    # Security Audit Logs (ABDM/DPDP/HIPAA immutable event log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            actor_id TEXT NOT NULL,
            resource_id TEXT,
            details TEXT,
            ip_address TEXT,
            severity TEXT DEFAULT 'LOW',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ABDM / DPDP electronic Consent Artefacts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consent_records (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            requester_id TEXT NOT NULL,
            requester_name TEXT,
            purpose TEXT NOT NULL,
            state TEXT NOT NULL,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP
        )
    """)

    # Seed or sync doctors and slots
    seed_data(cursor)

    conn.commit()
    conn.close()


def seed_data(cursor: sqlite3.Cursor):
    """Seed comprehensive verified doctors and time slots across all 13 medical categories."""
    doctors = [
        # General Medicine
        ("doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Available"),
        ("doc-priya", "Dr. Priya Sharma", "General Medicine", "Available"),
        ("doc-rajesh", "Dr. Rajesh Nair", "General Medicine", "Available"),
        # Cardiology
        ("doc-anand", "Dr. Anand Shenoy", "Cardiology", "Available"),
        ("doc-deepak", "Dr. Deepak Krishnamurthy", "Cardiology", "Available"),
        # Gastroenterology
        ("doc-rajat", "Dr. Rajat Goel", "Gastroenterology", "Available"),
        ("doc-shalini", "Dr. Shalini Verma", "Gastroenterology", "Available"),
        # Neurology
        ("doc-suresh", "Dr. Suresh Rao", "Neurology", "Available"),
        ("doc-pradeep", "Dr. Pradeep Kumar", "Neurology", "Available"),
        # Pulmonology
        ("doc-harish", "Dr. Harish Mallapura", "Pulmonology", "Available"),
        ("doc-aravind", "Dr. Aravind S", "Pulmonology", "Available"),
        # Gynecology
        ("doc-nandini", "Dr. Nandini Devi", "Gynecology", "Available"),
        ("doc-shweta", "Dr. Shweta Bhardwaj", "Gynecology", "Available"),
        # Psychiatry
        ("doc-ashok", "Dr. Ashok Patel", "Psychiatry", "Available"),
        ("doc-ananya", "Dr. Ananya Sen", "Psychiatry", "Available"),
        # Orthopedics
        ("doc-vikram", "Dr. Vikram Seth", "Orthopedics", "Available"),
        ("doc-manoj", "Dr. Manoj Chawla", "Orthopedics", "Available"),
        # Dermatology
        ("doc-sneha", "Dr. Sneha Rao", "Dermatology", "Available"),
        ("doc-pooja", "Dr. Pooja Hegde", "Dermatology", "Available"),
        # ENT
        ("doc-arjun", "Dr. Arjun Reddy", "ENT", "Available"),
        ("doc-vijay", "Dr. Vijay Krishna", "ENT", "Available"),
        # Ophthalmology
        ("doc-kavita", "Dr. Kavita Menon", "Ophthalmology", "Available"),
        ("doc-aditya", "Dr. Aditya Murthy", "Ophthalmology", "Available"),
        # Dental
        ("doc-alok", "Dr. Alok Verma", "Dental", "Available"),
        ("doc-ritu", "Dr. Ritu Mittal", "Dental", "Available"),
        # Pediatrics
        ("doc-meera", "Dr. Meera Iyer", "Pediatrics", "Available"),
        ("doc-karthik", "Dr. Karthik Somanna", "Pediatrics", "Available"),
        # Hematology (Platelets, Anemia, Blood Disorders)
        ("doc-sandeep", "Dr. Sandeep Batra", "Hematology", "Available"),
        ("doc-radhika", "Dr. Radhika Joshi", "Hematology", "Available"),
        # Endocrinology (Diabetes, Thyroid, Metabolism)
        ("doc-mahesh", "Dr. Mahesh Reddy", "Endocrinology", "Available"),
        ("doc-sunita", "Dr. Sunita Rao", "Endocrinology", "Available"),
        # Nephrology (Kidneys, Creatinine, Urinary)
        ("doc-mohan", "Dr. Mohan Kumar", "Nephrology", "Available"),
        ("doc-vidya", "Dr. Vidya Shankar", "Nephrology", "Available"),
    ]

    cursor.executemany(
        "INSERT OR REPLACE INTO doctors (id, name, department, available_status) VALUES (?, ?, ?, ?)",
        doctors
    )

    slots = [
        # Dr. Ravi Kumar (General Medicine)
        ("slot-r-1", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-r-2", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-r-3", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-r-4", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "5:30 PM", "evening", 1),
        ("slot-r-6", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),
        ("slot-r-5", "doc-ravi", "Dr. Ravi Kumar", "General Medicine", "Tomorrow, Oct 24", "6:30 PM", "evening", 1),

        # Dr. Priya Sharma (General Medicine)
        ("slot-p-1", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-p-2", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-p-3", "doc-priya", "Dr. Priya Sharma", "General Medicine", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),

        # Dr. Rajesh Nair (General Medicine)
        ("slot-rn-1", "doc-rajesh", "Dr. Rajesh Nair", "General Medicine", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-rn-2", "doc-rajesh", "Dr. Rajesh Nair", "General Medicine", "Tomorrow, Oct 24", "4:30 PM", "evening", 1),
        ("slot-rn-3", "doc-rajesh", "Dr. Rajesh Nair", "General Medicine", "Tomorrow, Oct 24", "6:30 PM", "evening", 1),

        # Dr. Anand Shenoy (Cardiology)
        ("slot-an-1", "doc-anand", "Dr. Anand Shenoy", "Cardiology", "Tomorrow, Oct 24", "09:00 AM", "morning", 1),
        ("slot-an-2", "doc-anand", "Dr. Anand Shenoy", "Cardiology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-an-3", "doc-anand", "Dr. Anand Shenoy", "Cardiology", "Tomorrow, Oct 24", "05:00 PM", "evening", 1),

        # Dr. Deepak Krishnamurthy (Cardiology)
        ("slot-dp-1", "doc-deepak", "Dr. Deepak Krishnamurthy", "Cardiology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-dp-2", "doc-deepak", "Dr. Deepak Krishnamurthy", "Cardiology", "Tomorrow, Oct 24", "04:00 PM", "afternoon", 1),
        ("slot-dp-3", "doc-deepak", "Dr. Deepak Krishnamurthy", "Cardiology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Rajat Goel (Gastroenterology)
        ("slot-rj-1", "doc-rajat", "Dr. Rajat Goel", "Gastroenterology", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-rj-2", "doc-rajat", "Dr. Rajat Goel", "Gastroenterology", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-rj-3", "doc-rajat", "Dr. Rajat Goel", "Gastroenterology", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Shalini Verma (Gastroenterology)
        ("slot-sh-1", "doc-shalini", "Dr. Shalini Verma", "Gastroenterology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-sh-2", "doc-shalini", "Dr. Shalini Verma", "Gastroenterology", "Tomorrow, Oct 24", "04:00 PM", "afternoon", 1),
        ("slot-sh-3", "doc-shalini", "Dr. Shalini Verma", "Gastroenterology", "Tomorrow, Oct 24", "06:30 PM", "evening", 1),

        # Dr. Suresh Rao (Neurology)
        ("slot-sr-1", "doc-suresh", "Dr. Suresh Rao", "Neurology", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-sr-2", "doc-suresh", "Dr. Suresh Rao", "Neurology", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-sr-3", "doc-suresh", "Dr. Suresh Rao", "Neurology", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Pradeep Kumar (Neurology)
        ("slot-pk-1", "doc-pradeep", "Dr. Pradeep Kumar", "Neurology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-pk-2", "doc-pradeep", "Dr. Pradeep Kumar", "Neurology", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-pk-3", "doc-pradeep", "Dr. Pradeep Kumar", "Neurology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Harish Mallapura (Pulmonology)
        ("slot-hr-1", "doc-harish", "Dr. Harish Mallapura", "Pulmonology", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-hr-2", "doc-harish", "Dr. Harish Mallapura", "Pulmonology", "Tomorrow, Oct 24", "02:00 PM", "afternoon", 1),
        ("slot-hr-3", "doc-harish", "Dr. Harish Mallapura", "Pulmonology", "Tomorrow, Oct 24", "04:30 PM", "evening", 1),

        # Dr. Aravind S (Pulmonology)
        ("slot-av-1", "doc-aravind", "Dr. Aravind S", "Pulmonology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-av-2", "doc-aravind", "Dr. Aravind S", "Pulmonology", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-av-3", "doc-aravind", "Dr. Aravind S", "Pulmonology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Nandini Devi (Gynecology)
        ("slot-nd-1", "doc-nandini", "Dr. Nandini Devi", "Gynecology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-nd-2", "doc-nandini", "Dr. Nandini Devi", "Gynecology", "Tomorrow, Oct 24", "01:30 PM", "afternoon", 1),
        ("slot-nd-3", "doc-nandini", "Dr. Nandini Devi", "Gynecology", "Tomorrow, Oct 24", "05:00 PM", "evening", 1),

        # Dr. Shweta Bhardwaj (Gynecology)
        ("slot-sw-1", "doc-shweta", "Dr. Shweta Bhardwaj", "Gynecology", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-sw-2", "doc-shweta", "Dr. Shweta Bhardwaj", "Gynecology", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-sw-3", "doc-shweta", "Dr. Shweta Bhardwaj", "Gynecology", "Tomorrow, Oct 24", "06:30 PM", "evening", 1),

        # Dr. Ashok Patel (Psychiatry)
        ("slot-as-1", "doc-ashok", "Dr. Ashok Patel", "Psychiatry", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-as-2", "doc-ashok", "Dr. Ashok Patel", "Psychiatry", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-as-3", "doc-ashok", "Dr. Ashok Patel", "Psychiatry", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Ananya Sen (Psychiatry)
        ("slot-ay-1", "doc-ananya", "Dr. Ananya Sen", "Psychiatry", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-ay-2", "doc-ananya", "Dr. Ananya Sen", "Psychiatry", "Tomorrow, Oct 24", "04:00 PM", "afternoon", 1),
        ("slot-ay-3", "doc-ananya", "Dr. Ananya Sen", "Psychiatry", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Arjun Reddy (ENT)
        ("slot-a-1", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-a-2", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "04:30 PM", "afternoon", 1),
        ("slot-a-3", "doc-arjun", "Dr. Arjun Reddy", "ENT", "Tomorrow, Oct 24", "6:00 PM", "evening", 1),

        # Dr. Vijay Krishna (ENT)
        ("slot-vj-1", "doc-vijay", "Dr. Vijay Krishna", "ENT", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-vj-2", "doc-vijay", "Dr. Vijay Krishna", "ENT", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-vj-3", "doc-vijay", "Dr. Vijay Krishna", "ENT", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Sneha Rao (Dermatology)
        ("slot-s-1", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-s-2", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-s-3", "doc-sneha", "Dr. Sneha Rao", "Dermatology", "Tomorrow, Oct 24", "5:00 PM", "evening", 1),

        # Dr. Pooja Hegde (Dermatology)
        ("slot-pj-1", "doc-pooja", "Dr. Pooja Hegde", "Dermatology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-pj-2", "doc-pooja", "Dr. Pooja Hegde", "Dermatology", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-pj-3", "doc-pooja", "Dr. Pooja Hegde", "Dermatology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Meera Iyer (Pediatrics)
        ("slot-m-1", "doc-meera", "Dr. Meera Iyer", "Pediatrics", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-m-2", "doc-meera", "Dr. Meera Iyer", "Pediatrics", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-m-3", "doc-meera", "Dr. Meera Iyer", "Pediatrics", "Tomorrow, Oct 24", "05:00 PM", "evening", 1),

        # Dr. Karthik Somanna (Pediatrics)
        ("slot-kt-1", "doc-karthik", "Dr. Karthik Somanna", "Pediatrics", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-kt-2", "doc-karthik", "Dr. Karthik Somanna", "Pediatrics", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-kt-3", "doc-karthik", "Dr. Karthik Somanna", "Pediatrics", "Tomorrow, Oct 24", "06:30 PM", "evening", 1),

        # Dr. Vikram Seth (Orthopedics)
        ("slot-v-1", "doc-vikram", "Dr. Vikram Seth", "Orthopedics", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-v-2", "doc-vikram", "Dr. Vikram Seth", "Orthopedics", "Tomorrow, Oct 24", "04:00 PM", "afternoon", 1),
        ("slot-v-3", "doc-vikram", "Dr. Vikram Seth", "Orthopedics", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Manoj Chawla (Orthopedics)
        ("slot-mc-1", "doc-manoj", "Dr. Manoj Chawla", "Orthopedics", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-mc-2", "doc-manoj", "Dr. Manoj Chawla", "Orthopedics", "Tomorrow, Oct 24", "02:00 PM", "afternoon", 1),
        ("slot-mc-3", "doc-manoj", "Dr. Manoj Chawla", "Orthopedics", "Tomorrow, Oct 24", "05:00 PM", "evening", 1),

        # Dr. Alok Verma (Dental)
        ("slot-d-1", "doc-alok", "Dr. Alok Verma", "Dental", "Tomorrow, Oct 24", "09:00 AM", "morning", 1),
        ("slot-d-2", "doc-alok", "Dr. Alok Verma", "Dental", "Tomorrow, Oct 24", "02:00 PM", "afternoon", 1),
        ("slot-d-3", "doc-alok", "Dr. Alok Verma", "Dental", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Ritu Mittal (Dental)
        ("slot-rt-1", "doc-ritu", "Dr. Ritu Mittal", "Dental", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-rt-2", "doc-ritu", "Dr. Ritu Mittal", "Dental", "Tomorrow, Oct 24", "04:30 PM", "afternoon", 1),
        ("slot-rt-3", "doc-ritu", "Dr. Ritu Mittal", "Dental", "Tomorrow, Oct 24", "07:00 PM", "evening", 1),

        # Dr. Kavita Menon (Ophthalmology)
        ("slot-k-1", "doc-kavita", "Dr. Kavita Menon", "Ophthalmology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-k-2", "doc-kavita", "Dr. Kavita Menon", "Ophthalmology", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-k-3", "doc-kavita", "Dr. Kavita Menon", "Ophthalmology", "Tomorrow, Oct 24", "5:30 PM", "evening", 1),

        # Dr. Aditya Murthy (Ophthalmology)
        ("slot-ad-1", "doc-aditya", "Dr. Aditya Murthy", "Ophthalmology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-ad-2", "doc-aditya", "Dr. Aditya Murthy", "Ophthalmology", "Tomorrow, Oct 24", "02:00 PM", "afternoon", 1),
        ("slot-ad-3", "doc-aditya", "Dr. Aditya Murthy", "Ophthalmology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Sandeep Batra (Hematology)
        ("slot-sb-1", "doc-sandeep", "Dr. Sandeep Batra", "Hematology", "Tomorrow, Oct 24", "10:00 AM", "morning", 1),
        ("slot-sb-2", "doc-sandeep", "Dr. Sandeep Batra", "Hematology", "Tomorrow, Oct 24", "02:30 PM", "afternoon", 1),
        ("slot-sb-3", "doc-sandeep", "Dr. Sandeep Batra", "Hematology", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Radhika Joshi (Hematology)
        ("slot-rd-1", "doc-radhika", "Dr. Radhika Joshi", "Hematology", "Tomorrow, Oct 24", "11:30 AM", "morning", 1),
        ("slot-rd-2", "doc-radhika", "Dr. Radhika Joshi", "Hematology", "Tomorrow, Oct 24", "03:30 PM", "afternoon", 1),
        ("slot-rd-3", "doc-radhika", "Dr. Radhika Joshi", "Hematology", "Tomorrow, Oct 24", "06:30 PM", "evening", 1),

        # Dr. Mahesh Reddy (Endocrinology)
        ("slot-mh-1", "doc-mahesh", "Dr. Mahesh Reddy", "Endocrinology", "Tomorrow, Oct 24", "09:30 AM", "morning", 1),
        ("slot-mh-2", "doc-mahesh", "Dr. Mahesh Reddy", "Endocrinology", "Tomorrow, Oct 24", "03:00 PM", "afternoon", 1),
        ("slot-mh-3", "doc-mahesh", "Dr. Mahesh Reddy", "Endocrinology", "Tomorrow, Oct 24", "05:00 PM", "evening", 1),

        # Dr. Sunita Rao (Endocrinology)
        ("slot-sn-1", "doc-sunita", "Dr. Sunita Rao", "Endocrinology", "Tomorrow, Oct 24", "11:00 AM", "morning", 1),
        ("slot-sn-2", "doc-sunita", "Dr. Sunita Rao", "Endocrinology", "Tomorrow, Oct 24", "02:00 PM", "afternoon", 1),
        ("slot-sn-3", "doc-sunita", "Dr. Sunita Rao", "Endocrinology", "Tomorrow, Oct 24", "06:00 PM", "evening", 1),

        # Dr. Mohan Kumar (Nephrology)
        ("slot-mn-1", "doc-mohan", "Dr. Mohan Kumar", "Nephrology", "Tomorrow, Oct 24", "10:30 AM", "morning", 1),
        ("slot-mn-2", "doc-mohan", "Dr. Mohan Kumar", "Nephrology", "Tomorrow, Oct 24", "01:30 PM", "afternoon", 1),
        ("slot-mn-3", "doc-mohan", "Dr. Mohan Kumar", "Nephrology", "Tomorrow, Oct 24", "05:30 PM", "evening", 1),

        # Dr. Vidya Shankar (Nephrology)
        ("slot-vs-1", "doc-vidya", "Dr. Vidya Shankar", "Nephrology", "Tomorrow, Oct 24", "09:00 AM", "morning", 1),
        ("slot-vs-2", "doc-vidya", "Dr. Vidya Shankar", "Nephrology", "Tomorrow, Oct 24", "04:00 PM", "afternoon", 1),
        ("slot-vs-3", "doc-vidya", "Dr. Vidya Shankar", "Nephrology", "Tomorrow, Oct 24", "06:30 PM", "evening", 1),
    ]

    cursor.executemany(
        """INSERT OR IGNORE INTO appointment_slots
           (id, doctor_id, doctor_name, department, date, time, period, is_available)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        slots
    )

    # Seed sample medical documents & insurance policies if table is empty
    cursor.execute("SELECT COUNT(*) FROM medical_documents")
    count_docs = cursor.fetchone()[0]
    if count_docs == 0:
        storage_base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
        sample_docs = [
            (
                "doc-fc6d33ca06fc",
                "user_default",
                "corporate_reimbursement_policy.pdf",
                1799,
                os.path.join(storage_base, "doc-fc6d33ca06fc_corporate_reimbursement_policy.pdf"),
                "application/pdf",
                "INSURANCE_POLICY",
                "COMPLETED",
                '{"policy_category":"COMPANY_HEALTH_INSURANCE","coverage_amount":"₹5,00,000","claim_limit":"₹15,000 OPD","summary":"Comprehensive corporate group mediclaim policy covering inpatient hospitalization and outpatient pharmacy expenses."}'
            ),
            (
                "doc-b5529e2268f0",
                "user_default",
                "company_reimbursement_policy.pdf",
                1875,
                os.path.join(storage_base, "doc-b5529e2268f0_company_reimbursement_policy.pdf"),
                "application/pdf",
                "REIMBURSEMENT_POLICY",
                "COMPLETED",
                '{"policy_category":"EMPLOYEE_REIMBURSEMENT","coverage_amount":"₹50,000","claim_limit":"₹5,000 per month","summary":"Employee medical expense reimbursement guidelines with 30-day submission deadline."}'
            ),
            (
                "doc-24cda217a762",
                "user_default",
                "pharmacy_medicine_bill.pdf",
                1601,
                os.path.join(storage_base, "doc-24cda217a762_pharmacy_medicine_bill.pdf"),
                "application/pdf",
                "MEDICINE_BILL",
                "COMPLETED",
                '{"patient_name":"Sarah Connor","doctor_hospital":{"doctor_name":"Dr. Ravi Kumar","hospital_name":"Apollo Pharmacy Indiranagar"},"medicines":[{"name":"Augmentin 625 Duo","dosage":"625mg","frequency":"1-0-1","duration":"5 days"},{"name":"Dolo 650","dosage":"650mg","frequency":"1-0-1","duration":"3 days"}],"total_amount":"₹742.50","dates":{"document_date":"2026-09-18"}}'
            ),
            (
                "doc-f133b396fca5",
                "user_default",
                "dr_ravi_prescription.pdf",
                1737,
                os.path.join(storage_base, "doc-f133b396fca5_dr_ravi_prescription.pdf"),
                "application/pdf",
                "PRESCRIPTION",
                "COMPLETED",
                '{"patient_name":"Sarah Connor","doctor_hospital":{"doctor_name":"Dr. Ravi Kumar","hospital_name":"Manipal Hospital"},"medicines":[{"name":"Amoxicillin","dosage":"500mg"},{"name":"Paracetamol","dosage":"650mg"}],"dates":{"consultation_date":"2026-09-17"}}'
            ),
            (
                "doc-ad301582d5c5",
                "user_default",
                "cbc_lab_report.pdf",
                1653,
                os.path.join(storage_base, "doc-ad301582d5c5_cbc_lab_report.pdf"),
                "application/pdf",
                "MEDICAL_REPORT",
                "COMPLETED",
                '{"patient_name":"Sarah Connor","diagnosis_findings":["Platelet count: 180,000 /uL (Normal)","Hemoglobin: 13.8 g/dL"],"dates":{"document_date":"2026-09-15"}}'
            ),
        ]
        cursor.executemany(
            """INSERT OR IGNORE INTO medical_documents
               (id, user_id, file_name, file_size, file_path, mime_type, document_type, processing_status, extracted_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sample_docs
        )

    # Seed default verified users if users table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    count_users = cursor.fetchone()[0]
    if count_users == 0:
        cursor.execute(
            """INSERT INTO users (id, full_name, email, phone, dob, password_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                "usr_sarah_connor",
                "Dr. Sarah Connor",
                "sarah.connor@healthcare.org",
                "+91 98765 43210",
                "1985-05-12",
                "$2b$12$WhROVzvxpCh23itwh1uzv.M45Hv/qD6kXV4kH73Bnc3gFQy7jlmHK" # SecurePassword123!
            )
        )


def query_doctors_and_slots(
    department: str,
    period_preference: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search available doctors and appointment slots for a given department and time preference."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    dept_clean = department.strip()
    if dept_clean.upper() == "ENT":
        cursor.execute(
            "SELECT id, name, department, available_status FROM doctors WHERE UPPER(department) = 'ENT'"
        )
    else:
        cursor.execute(
            "SELECT id, name, department, available_status FROM doctors WHERE LOWER(department) LIKE LOWER(?)",
            (f"%{dept_clean}%",)
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
    Applies AES-256 field-level encryption at rest for sensitive PII/PHI.
    Raises ValueError if email is already registered.
    """
    init_db()
    email_clean = user_data["email"].strip().lower()

    # Check existence
    existing = get_user_by_email(email_clean)
    if existing:
        raise ValueError("An account with this email address already exists.")

    user_id = user_data.get("id") or f"usr_{uuid.uuid4().hex[:12]}"
    raw_phone = user_data["phone"].strip()
    raw_abha = user_data.get("abha_id")
    role = user_data.get("role", "PATIENT").upper()

    # Field-level AES-256 encryption at rest
    encrypted_phone = crypto_service.encrypt(raw_phone)
    encrypted_abha = crypto_service.encrypt(raw_abha) if raw_abha else None

    record = {
        "id": user_id,
        "full_name": user_data["full_name"].strip(),
        "email": email_clean,
        "phone": encrypted_phone,
        "dob": user_data.get("dob"),
        "password_hash": user_data["password_hash"],
        "role": role,
        "abha_id": encrypted_abha,
        "is_active": 1,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # Store in SQLite
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (id, full_name, email, phone, dob, password_hash, role, abha_id, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        record["id"],
        record["full_name"],
        record["email"],
        record["phone"],
        record["dob"],
        record["password_hash"],
        record["role"],
        record["abha_id"],
        record["is_active"],
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

    # Return clean decrypted representation to caller
    return {
        **record,
        "phone": raw_phone,
        "abha_id": raw_abha,
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves user by email, checking PostgreSQL first, with SQLite fallback, decrypting sensitive fields."""
    init_db()
    email_clean = email.strip().lower()

    # Try PostgreSQL first
    try:
        pg_user = postgres_service.get_user_by_email(email_clean)
        if pg_user:
            pg_user["phone"] = crypto_service.decrypt(pg_user.get("phone"))
            if pg_user.get("abha_id"):
                pg_user["abha_id"] = crypto_service.decrypt(pg_user.get("abha_id"))
            if "role" not in pg_user:
                pg_user["role"] = "PATIENT"
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
        user_dict = dict(row)
        user_dict["phone"] = crypto_service.decrypt(user_dict.get("phone"))
        if user_dict.get("abha_id"):
            user_dict["abha_id"] = crypto_service.decrypt(user_dict.get("abha_id"))
        if "role" not in user_dict or not user_dict["role"]:
            user_dict["role"] = "PATIENT"
        return user_dict
    return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user by ID, checking PostgreSQL first, with SQLite fallback, decrypting sensitive fields."""
    init_db()

    try:
        pg_user = postgres_service.get_user_by_id(user_id)
        if pg_user:
            pg_user["phone"] = crypto_service.decrypt(pg_user.get("phone"))
            if pg_user.get("abha_id"):
                pg_user["abha_id"] = crypto_service.decrypt(pg_user.get("abha_id"))
            if "role" not in pg_user:
                pg_user["role"] = "PATIENT"
            return pg_user
    except Exception:
        pass

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        user_dict = dict(row)
        user_dict["phone"] = crypto_service.decrypt(user_dict.get("phone"))
        if user_dict.get("abha_id"):
            user_dict["abha_id"] = crypto_service.decrypt(user_dict.get("abha_id"))
        if "role" not in user_dict or not user_dict["role"]:
            user_dict["role"] = "PATIENT"
        return user_dict
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


def get_medical_document(
    doc_id: str,
    requester_id: Optional[str] = None,
    requester_role: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetches a medical document record by ID.
    Enforces user-level document isolation and ABDM consent verification.
    """
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

    # Document isolation & consent check
    owner_id = record.get("user_id")
    if requester_id and owner_id and requester_id != owner_id:
        if (requester_role or "").upper() not in ["ADMIN", "AUDITOR"]:
            # Secondary access requires active consent
            if not consent_manager.is_consent_active(patient_id=owner_id, requester_id=requester_id):
                return None

    if record.get("extracted_data") and isinstance(record["extracted_data"], str):
        try:
            record["extracted_data"] = json.loads(record["extracted_data"])
        except Exception:
            pass
    return record


def list_medical_documents(
    user_id: Optional[str] = None,
    requester_id: Optional[str] = None,
    requester_role: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves medical documents, optionally filtered by user_id,
    with ABDM consent gating if requested by another party.
    """
    import json
    init_db()

    # Enforce consent gating if requester is looking at another patient's documents
    if user_id and requester_id and user_id != requester_id:
        if (requester_role or "").upper() not in ["ADMIN", "AUDITOR"]:
            if not consent_manager.is_consent_active(patient_id=user_id, requester_id=requester_id):
                return []

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


def delete_medical_document(doc_id: str, requester_id: Optional[str] = None, requester_role: Optional[str] = None) -> bool:
    """
    Deletes a medical document record by ID.
    Enforces that only the document owner or an ADMIN can delete.
    """
    init_db()
    existing = get_medical_document(doc_id)
    if not existing:
        return False

    owner_id = existing.get("user_id")
    if requester_id and owner_id and requester_id != owner_id:
        if (requester_role or "").upper() != "ADMIN":
            return False

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medical_documents WHERE id = ?", (doc_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


