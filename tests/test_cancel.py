from datetime import date
from app.models.appointment import Appointment
from app.models.patient import SessionLocal, Patient
from app.views.main_window import MainWindow


def test_cancel_appointment_updates_status_and_dashboard(qapp):
    mw = MainWindow()

    # create patient and appointment for today
    mw.input_name.setText("cancel-patient")
    mw.input_age.setText("40")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText("cancel-patient")
    mw.input_appt_doctor.setText("Dr Cancel")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.add_appointment()

    # locate appointment
    session = SessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.doctor_name == 'Dr Cancel').first()
        assert appt is not None
        appt_id = appt.id
    finally:
        session.close()

    mw.update_dashboard()
    before_appts = int(mw.card_appointments.value_label.text())

    assert mw.cancel_appointment(appt_id)

    # status should be updated in DB
    session = SessionLocal()
    try:
        appt = session.get(Appointment, appt_id)
        assert appt.status == 'cancelled'
    finally:
        session.close()

    mw.update_dashboard()
    assert int(mw.card_appointments.value_label.text()) == before_appts - 1

    # cleanup
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Cancel').delete()
        session.query(Patient).filter(Patient.name == 'cancel-patient').delete()
        session.commit()
    finally:
        session.close()
