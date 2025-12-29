import pytest
from datetime import date, timedelta
from PySide6.QtCore import QDate

from app.views.main_window import MainWindow
from app.models.appointment import Appointment
from app.models.patient import SessionLocal


def test_reschedule_to_past_is_rejected(qapp):
    mw = MainWindow()

    # create patient and appointment for tomorrow
    mw.input_name.setText("past-patient")
    mw.input_age.setText("40")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText("past-patient")
    mw.input_appt_doctor.setText("Dr Past")
    tomorrow = date.today() + timedelta(days=1)
    mw.input_appt_date.setText(tomorrow.isoformat())
    mw.add_appointment()

    # find appointment id
    session = SessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.doctor_name == 'Dr Past').first()
        assert appt is not None
        appt_id = appt.id
        old_date = appt.date
    finally:
        session.close()

    # attempt to reschedule to yesterday (past)
    yesterday = date.today() - timedelta(days=1)
    qd = QDate(yesterday.year, yesterday.month, yesterday.day)
    qt = mw.input_appt_time.time()
    assert not mw.reschedule_appointment(appt_id, qd, qt)

    # ensure date unchanged
    session = SessionLocal()
    try:
        appt2 = session.get(Appointment, appt_id)
        assert appt2.date == old_date
    finally:
        session.close()


def test_prevent_double_booking(qapp):
    mw = MainWindow()

    # create patient and appointment at a fixed datetime
    mw.input_name.setText("double-patient")
    mw.input_age.setText("35")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText("double-patient")
    mw.input_appt_doctor.setText("Dr Double")

    target = date.today() + timedelta(days=2)
    mw.input_appt_date.setText(target.isoformat())
    # set a fixed time (use current time)
    t = mw.input_appt_time.time()

    assert mw.add_appointment()  # first should succeed

    # try to add second appointment for same doctor/time
    mw.input_appt_patient.setText("double-patient")
    mw.input_appt_doctor.setText("Dr Double")
    mw.input_appt_date.setText(target.isoformat())

    # second add should be rejected due to conflict
    assert not mw.add_appointment()

    # cleanup
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Double').delete()
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Past').delete()
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Resched').delete()
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr UIResched').delete()
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Invalid').delete()
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr PyTest').delete()
        session.query(SessionLocal().bind.tables.get('appointments')).delete()
        session.commit()
    except Exception:
        pass
    finally:
        session.close()
