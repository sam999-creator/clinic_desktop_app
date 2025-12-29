import uuid
from datetime import date

import pytest
from PySide6.QtCore import QTime
from app.views.main_window import MainWindow
from app.models.appointment import Appointment
from app.models.patient import SessionLocal, Patient


def _cleanup(doctor_name, patient_name):
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == doctor_name).delete()
        session.query(Patient).filter(Patient.name == patient_name).delete()
        session.commit()
    finally:
        session.close()


def test_doctor_double_booking_prevented(qapp):
    mw = MainWindow()
    name = f"test-overlap-{uuid.uuid4().hex[:8]}"

    # create patient
    mw.input_name.setText(name)
    mw.input_age.setText("40")
    mw.input_condition.setText("test")
    mw.add_patient()

    # add first appointment at 10:00 for 60 minutes
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Overlap")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(10, 0))
    mw.input_appt_duration.setValue(60)
    assert mw.add_appointment()

    # attempt overlapping appointment (10:30 for 30 minutes) -> should be rejected
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Overlap")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(10, 30))
    mw.input_appt_duration.setValue(30)
    assert not mw.add_appointment()

    _cleanup("Dr Overlap", name)


def test_overlapping_allowed_for_different_doctors(qapp):
    mw = MainWindow()
    name = f"test-overlap-{uuid.uuid4().hex[:8]}"

    mw.input_name.setText(name)
    mw.input_age.setText("36")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr A")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(11, 0))
    mw.input_appt_duration.setValue(60)
    assert mw.add_appointment()

    # overlapping for a different doctor should be allowed
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr B")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(11, 30))
    mw.input_appt_duration.setValue(30)
    assert mw.add_appointment()

    _cleanup("Dr A", name)
    _cleanup("Dr B", name)


def test_cancelled_appointments_are_ignored(qapp):
    mw = MainWindow()
    name = f"test-overlap-{uuid.uuid4().hex[:8]}"

    mw.input_name.setText(name)
    mw.input_age.setText("37")
    mw.input_condition.setText("test")
    mw.add_patient()

    # create and then cancel an appointment
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Cancel")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(13, 0))
    mw.input_appt_duration.setValue(60)
    assert mw.add_appointment()

    session = SessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.doctor_name == 'Dr Cancel').first()
        assert appt is not None
        mw.cancel_appointment(appt.id)
    finally:
        session.close()

    # now adding an appointment that overlaps the cancelled one should succeed
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Cancel")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(13, 30))
    mw.input_appt_duration.setValue(30)
    assert mw.add_appointment()

    _cleanup("Dr Cancel", name)


def test_reschedule_conflict_is_rejected(qapp):
    from datetime import timedelta
    from PySide6.QtCore import QDate

    mw = MainWindow()
    name = f"test-overlap-{uuid.uuid4().hex[:8]}"

    mw.input_name.setText(name)
    mw.input_age.setText("35")
    mw.input_condition.setText("test")
    mw.add_patient()

    # appointment A at 9:00 for 60 min
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Res")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(9, 0))
    mw.input_appt_duration.setValue(60)
    assert mw.add_appointment()

    # appointment B at 11:00 for 30 min
    mw.input_appt_patient.setText(name)
    mw.input_appt_doctor.setText("Dr Res")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.input_appt_time.setTime(QTime(11, 0))
    mw.input_appt_duration.setValue(30)
    assert mw.add_appointment()

    # find B's id
    session = SessionLocal()
    try:
        appt_b = session.query(Appointment).filter(Appointment.doctor_name == 'Dr Res').order_by(Appointment.id.desc()).first()
        appt_b_id = appt_b.id
    finally:
        session.close()

    # try to reschedule B to 9:30 -> overlaps A
    tomorrow = date.today()
    qd = QDate(tomorrow.year, tomorrow.month, tomorrow.day)
    from PySide6.QtCore import QTime as QT
    qt = QT(9, 30)
    assert not mw.reschedule_appointment(appt_b_id, qd, qt)

    # cleanup
    _cleanup("Dr Res", name)
