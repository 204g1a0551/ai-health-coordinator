import logging
from typing import Dict, Any, List, Optional
from app.config import postgres_settings

logger = logging.getLogger("postgres_service")

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    PSYCOPG2_AVAILABLE = False


class PostgresService:
    """
    PostgreSQL Storage Service for AI Health Checkup & Appointment Coordinator.
    Manages final appointment records, slots, and availability in PostgreSQL.
    Provides graceful fallback diagnostics if PostgreSQL is offline in local dev environments.
    """

    def __init__(self):
        self._connected = False
        self._last_error = None
        self._init_connection()

    def _get_connection(self):
        """Creates a new connection to PostgreSQL."""
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 is not installed.")

        if postgres_settings.url:
            return psycopg2.connect(postgres_settings.url, connect_timeout=2)

        return psycopg2.connect(
            host=postgres_settings.host,
            port=postgres_settings.port,
            dbname=postgres_settings.db,
            user=postgres_settings.user,
            password=postgres_settings.password,
            connect_timeout=2,
        )

    def _init_connection(self):
        """Tests connection and runs initial schema migrations if PostgreSQL is reachable."""
        if not PSYCOPG2_AVAILABLE:
            self._connected = False
            self._last_error = "psycopg2 library not available"
            return

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            self._create_schema(cursor)
            conn.commit()
            conn.close()
            self._connected = True
            self._last_error = None
            logger.info("Connected to PostgreSQL successfully at %s:%s", postgres_settings.host, postgres_settings.port)
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            logger.warning("PostgreSQL server offline or unreachable (%s). Using SQLite fallback.", str(e))

    def _create_schema(self, cursor):
        """Creates PostgreSQL tables with matching relational schema."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                department VARCHAR(100) NOT NULL,
                available_status VARCHAR(50) DEFAULT 'Available'
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointment_slots (
                id VARCHAR(50) PRIMARY KEY,
                doctor_id VARCHAR(50) NOT NULL,
                doctor_name VARCHAR(150) NOT NULL,
                department VARCHAR(100) NOT NULL,
                date VARCHAR(50) NOT NULL,
                time VARCHAR(50) NOT NULL,
                period VARCHAR(50) NOT NULL,
                is_available INTEGER DEFAULT 1,
                FOREIGN KEY(doctor_id) REFERENCES doctors(id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id VARCHAR(100) PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                doctor_id VARCHAR(50) NOT NULL,
                doctor_name VARCHAR(150) NOT NULL,
                department VARCHAR(100) NOT NULL,
                date VARCHAR(50) NOT NULL,
                display_date VARCHAR(50) NOT NULL,
                time VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                session_id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(150) DEFAULT 'Sarah Connor',
                age INTEGER DEFAULT 32,
                phone VARCHAR(50) DEFAULT '+1 (555) 019-2834',
                preferred_department VARCHAR(100) DEFAULT ''
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(50) PRIMARY KEY,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(150) UNIQUE NOT NULL,
                phone VARCHAR(50) NOT NULL,
                dob VARCHAR(50),
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_timeline_events (
                event_id VARCHAR(100) PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                event_type VARCHAR(40) NOT NULL,
                date VARCHAR(50),
                doctor VARCHAR(150),
                hospital VARCHAR(200),
                medicines TEXT NOT NULL DEFAULT '[]',
                bill_amount DOUBLE PRECISION,
                consultation_amount DOUBLE PRECISION,
                diagnostic_amount DOUBLE PRECISION,
                doc_id VARCHAR(100) NOT NULL,
                doc_type VARCHAR(60) NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_expenses (
                expense_id VARCHAR(100) PRIMARY KEY,
                session_id VARCHAR(100) NOT NULL,
                category VARCHAR(40) NOT NULL,
                amount DOUBLE PRECISION NOT NULL,
                date VARCHAR(50),
                provider VARCHAR(200),
                doc_id VARCHAR(100) NOT NULL
            );
        """)

    def is_connected(self) -> bool:
        """Returns whether live PostgreSQL connection is active."""
        if not self._connected:
            # Quick retry if requested
            self._init_connection()
        return self._connected

    def health_check(self) -> Dict[str, Any]:
        """Diagnostic health report for database status."""
        active = self.is_connected()
        return {
            "connected": active,
            "engine": "PostgreSQL" if active else "SQLite (Automatic Resilient Fallback)",
            "host": postgres_settings.host,
            "port": postgres_settings.port,
            "database": postgres_settings.db,
            "lastError": self._last_error if not active else None,
            "schemaVersion": "1.0.0",
        }

    def save_final_appointment(self, appointment_data: Dict[str, Any]) -> bool:
        """
        Stores confirmed appointment in PostgreSQL appointments table.
        """
        if not self.is_connected():
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO appointments
                (id, session_id, doctor_id, doctor_name, department, date, display_date, time, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    doctor_id = EXCLUDED.doctor_id,
                    doctor_name = EXCLUDED.doctor_name,
                    department = EXCLUDED.department,
                    date = EXCLUDED.date,
                    display_date = EXCLUDED.display_date,
                    time = EXCLUDED.time,
                    status = EXCLUDED.status;
            """, (
                appointment_data["id"],
                appointment_data["session_id"],
                appointment_data["doctor_id"],
                appointment_data["doctor_name"],
                appointment_data["department"],
                appointment_data["date"],
                appointment_data["display_date"],
                appointment_data["time"],
                appointment_data["status"],
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Failed to insert appointment into PostgreSQL: %s", str(e))
            return False

    def cancel_appointment(self, session_id: str) -> bool:
        """Updates appointment status to Cancelled in PostgreSQL."""
        if not self.is_connected():
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE appointments SET status = 'Cancelled' WHERE session_id = %s AND status = 'Booked'",
                (session_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Failed to cancel appointment in PostgreSQL: %s", str(e))
            return False

    def get_active_appointment(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Queries active appointment from PostgreSQL."""
        if not self.is_connected():
            return None

        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT * FROM appointments WHERE session_id = %s AND status = 'Booked' ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            )
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error("Failed to fetch appointment from PostgreSQL: %s", str(e))
            return None

    def create_user(self, user_data: Dict[str, Any]) -> bool:
        """Inserts a new user record into PostgreSQL."""
        if not self.is_connected():
            return False

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, full_name, email, phone, dob, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                user_data["id"],
                user_data["full_name"],
                user_data["email"].lower().strip(),
                user_data["phone"].strip(),
                user_data.get("dob"),
                user_data["password_hash"],
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error("Failed to insert user into PostgreSQL: %s", str(e))
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Queries a user by email from PostgreSQL."""
        if not self.is_connected():
            return None

        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(%s)", (email.strip(),))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error("Failed to query user by email from PostgreSQL: %s", str(e))
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Queries a user by id from PostgreSQL."""
        if not self.is_connected():
            return None

        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error("Failed to query user by id from PostgreSQL: %s", str(e))
            return None


postgres_service = PostgresService()
