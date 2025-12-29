import os
from sqlalchemy import Column, Integer, String, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True)
    patient_name = Column(String, nullable=False)
    doctor_name = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    duration_minutes = Column(Integer, default=30)
    # Optional recurrence rule (RFC 5545 RRULE string, e.g. "FREQ=WEEKLY;COUNT=10")
    recurrence_rule = Column(String, nullable=True)
    # status: scheduled / cancelled /completed
    status = Column(String, default="scheduled")

engine = create_engine("sqlite:///clinic.db", echo=True)
SessionLocal = sessionmaker(bind=engine)


def _ensure_columns(engine):
    """Ensure new columns exist in SQLite table (simple ALTER TABLE for demo)."""
    # This helper is small and safe for typical dev workflows; for production use Alembic.
    try:
        # use sqlite3 directly to ensure the ALTER takes effect even if SQLAlchemy transaction state is odd
        import sqlite3
        db = os.path.join(os.path.dirname(__file__), '..', '..', 'clinic.db')
        db = os.path.normpath(db)
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("PRAGMA table_info('appointments')")
        cols = [r[1] for r in cur.fetchall()]
        if 'duration_minutes' not in cols:
            try:
                cur.execute("ALTER TABLE appointments ADD COLUMN duration_minutes INTEGER DEFAULT 30")
                con.commit()
            except Exception:
                pass
        # add recurrence_rule and status if missing
        if 'recurrence_rule' not in cols:
            try:
                cur.execute("ALTER TABLE appointments ADD COLUMN recurrence_rule TEXT")
                con.commit()
            except Exception:
                pass
        if 'status' not in cols:
            try:
                cur.execute("ALTER TABLE appointments ADD COLUMN status TEXT DEFAULT 'scheduled'")
                con.commit()
            except Exception:
                pass
        cur.close()
        con.close()
    except Exception:
        # Best-effort; ignore failures in dev environment
        pass


def has_overlapping_appointment(session, doctor_name, start_dt, duration_minutes=30, exclude_id=None):
    """Return True if there's a non-cancelled appointment for `doctor_name` that overlaps
    the interval [start_dt, start_dt + duration_minutes).
    """
    from datetime import timedelta
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    q = session.query(Appointment).filter(Appointment.doctor_name == doctor_name, Appointment.status != 'cancelled')
    if exclude_id:
        q = q.filter(Appointment.id != exclude_id)
    for appt in q.all():
        a_start = appt.date
        a_end = a_start + timedelta(minutes=getattr(appt, 'duration_minutes', 30))
        # overlap check: intervals intersect
        if start_dt < a_end and a_start < end_dt:
            return True
    return False


def init_db():
    Base.metadata.create_all(engine)
    _ensure_columns(engine)