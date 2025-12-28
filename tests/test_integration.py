import os
from datetime import date

# run Qt in offscreen to allow tests in CI/headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox
from app.views.main_window import MainWindow
from app.models.patient import SessionLocal, Patient
from app.models.appointment import Appointment
from app.models.inventory import Inventory



import uuid

def test_smoke_flow_add_and_cleanup(qapp):
    mw = MainWindow()

    # use a unique name to avoid collisions with other test runs
    unique_name = f"pytest-smoke-patient-{uuid.uuid4().hex[:8]}"

    # read initial values
    before_patients = int(mw.card_patients.value_label.text())
    before_appts = int(mw.card_appointments.value_label.text())
    before_items = int(mw.card_inventory.value_label.text())

    # add patient via UI
    mw.input_name.setText(unique_name)
    mw.input_age.setText("42")
    mw.input_condition.setText("pytest")
    mw.add_patient()

    # add appointment via UI for today
    mw.input_appt_patient.setText(unique_name)
    mw.input_appt_doctor.setText("Dr PyTest")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.add_appointment()

    # add inventory via UI
    mw.input_item_name.setText("pytest-item")
    mw.input_quantity.setText("5")
    mw.input_category.setText("test")
    mw.add_inventory()

    # update dashboard and assert higher counts
    mw.update_dashboard()
    assert int(mw.card_patients.value_label.text()) == before_patients + 1
    assert int(mw.card_appointments.value_label.text()) >= before_appts + 1
    assert int(mw.card_inventory.value_label.text()) == before_items + 1

    # cleanup created test records
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr PyTest').delete()
        session.query(Inventory).filter(Inventory.item_name == 'pytest-item').delete()
        session.query(Patient).filter(Patient.name == unique_name).delete()
        session.commit()
    finally:
        session.close()

    # update dashboard again
    mw.update_dashboard()
    assert int(mw.card_patients.value_label.text()) == before_patients
    assert int(mw.card_inventory.value_label.text()) == before_items


def test_invalid_date_is_handled_gracefully(qapp):
    mw = MainWindow()

    # count current appointments for today
    mw.update_dashboard()
    before_appts = int(mw.card_appointments.value_label.text())

    # try to add appointment with invalid date
    mw.input_appt_patient.setText("pytest-invalid")
    mw.input_appt_doctor.setText("Dr Invalid")
    mw.input_appt_date.setText("not-a-date")

    # Should not raise and should not increase appointments
    mw.add_appointment()
    mw.update_dashboard()
    assert int(mw.card_appointments.value_label.text()) == before_appts

    # cleanup any leftovers (defensive)
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Invalid').delete()
        session.query(Patient).filter(Patient.name == 'pytest-invalid').delete()
        session.commit()
    finally:
        session.close()


def test_reschedule_appointment_updates_dashboard(qapp):
    from datetime import timedelta
    from PySide6.QtCore import QDate

    mw = MainWindow()

    # create patient and appointment for today
    mw.input_name.setText("resched-patient")
    mw.input_age.setText("30")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText("resched-patient")
    mw.input_appt_doctor.setText("Dr Resched")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.add_appointment()

    # find the appointment id
    session = SessionLocal()
    try:
        appt = session.query(Appointment).filter(Appointment.doctor_name == 'Dr Resched').first()
        assert appt is not None
        appt_id = appt.id
    finally:
        session.close()

    # ensure today's count increased
    mw.update_dashboard()
    before_appts = int(mw.card_appointments.value_label.text())

    # reschedule to tomorrow
    tomorrow = date.today() + timedelta(days=1)
    qd = QDate(tomorrow.year, tomorrow.month, tomorrow.day)
    qt = mw.input_appt_time.time()
    assert mw.reschedule_appointment(appt_id, qd, qt)

    # now today's appointments should decrease by 1
    mw.update_dashboard()
    assert int(mw.card_appointments.value_label.text()) == before_appts - 1

    # cleanup created records
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr Resched').delete()
        session.query(Patient).filter(Patient.name == 'resched-patient').delete()
        session.commit()
    finally:
        session.close()


def test_ui_reschedule_button_opens_dialog(monkeypatch, qapp):
    from datetime import timedelta
    from PySide6.QtCore import QDate, QTime
    from PySide6.QtWidgets import QDialog
    from app.views.main_window import RescheduleDialog
    mw = MainWindow()

    # create patient and appointment for today
    mw.input_name.setText("ui-resched-patient")
    mw.input_age.setText("28")
    mw.input_condition.setText("test")
    mw.add_patient()

    mw.input_appt_patient.setText("ui-resched-patient")
    mw.input_appt_doctor.setText("Dr UIResched")
    mw.input_appt_date.setText(date.today().isoformat())
    mw.add_appointment()

    # show non-calendar appointments listing
    mw.show_appointments()

    # find the row for our appointment and get the Reschedule button
    row = None
    for r in range(mw.table_appointments.rowCount()):
        item = mw.table_appointments.item(r, 1)
        if item and item.text() == 'Dr UIResched':
            row = r
            break
    assert row is not None
    btn = mw.table_appointments.cellWidget(row, 4)  # Reschedule column

    # monkeypatch dialog exec to set tomorrow date and accept
    def fake_exec(self):
        tomorrow = date.today() + timedelta(days=2)
        self.date_edit.setDate(QDate(tomorrow.year, tomorrow.month, tomorrow.day))
        # keep existing time
        return QDialog.Accepted

    monkeypatch.setattr(RescheduleDialog, 'exec', fake_exec)

    mw.update_dashboard()
    before_appts = int(mw.card_appointments.value_label.text())

    # click the button to open dialog (exec is monkeypatched so it won't block)
    btn.click()

    # appointment should be moved off today's list
    mw.update_dashboard()
    assert int(mw.card_appointments.value_label.text()) == before_appts - 1

    # cleanup
    session = SessionLocal()
    try:
        session.query(Appointment).filter(Appointment.doctor_name == 'Dr UIResched').delete()
        session.query(Patient).filter(Patient.name == 'ui-resched-patient').delete()
        session.commit()
    finally:
        session.close()
