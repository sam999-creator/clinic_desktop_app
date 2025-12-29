from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QTableWidget,
    QTableWidgetItem, QFrame, QLineEdit, QFormLayout, QMessageBox, QCheckBox,
    QButtonGroup, QComboBox
)
import os
from PySide6.QtCore import Qt, QSettings, QSize, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPainter, QBrush, QColor, QFontDatabase, QFont, QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QDateEdit, QTimeEdit
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtCharts import (
    QChart, QChartView, QPieSeries,
    QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
)
from datetime import date, datetime
import gettext

from app.models.patient import SessionLocal, Patient
from app.models.appointment import Appointment, has_overlapping_appointment
from app.models.inventory import Inventory
from app.views.edit_dialogs import PatientEditDialog

_ = gettext.gettext

class ToggleSwitch(QWidget):
    """A small animated toggle switch widget."""
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self._position = 1.0 if checked else 0.0
        self._checked = checked
        self._anim = QPropertyAnimation(self, b"position")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # background
        rect = self.rect()
        radius = rect.height() / 2
        bg_color = QColor('#10b981') if self._checked else QColor(200,200,200,80)
        p.setBrush(QBrush(bg_color))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, radius, radius)
        # handle
        handle_radius = radius - 3
        x = 3 + self._position * (rect.width() - 2 * (handle_radius + 3))
        y = rect.center().y()
        p.setBrush(QBrush(QColor('#ffffff')))
        p.drawEllipse(int(x), int(y - handle_radius), int(handle_radius*2), int(handle_radius*2))
        p.end()

    def getPosition(self):
        return self._position

    def setPosition(self, v):
        self._position = v
        self.update()

    position = Property(float, getPosition, setPosition)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        start = self._position
        end = 1.0 if checked else 0.0
        self._anim.stop()
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()
        self.toggled.emit(self._checked)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Clinic Management System"))
        self.setMinimumSize(1200, 800)

        # ensure database schema is up-to-date for new appointment fields
        try:
            from app.models.appointment import init_db as _init_appt_db
            _init_appt_db()
        except Exception:
            pass

        # ===== Sidebar =====
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        btn_dashboard = QPushButton(_("Dashboard"))
        btn_patients = QPushButton(_("Patients"))
        btn_appointments = QPushButton(_("Appointments"))
        btn_inventory = QPushButton(_("Inventory"))
        btn_settings = QPushButton(_("Settings"))

        # set icons for the sidebar buttons
        btn_dashboard.setIcon(QIcon("app/resources/icons/dashboard.svg"))
        btn_patients.setIcon(QIcon("app/resources/icons/patients.svg"))
        btn_appointments.setIcon(QIcon("app/resources/icons/appointments.svg"))
        btn_inventory.setIcon(QIcon("app/resources/icons/inventory.svg"))
        btn_settings.setIcon(QIcon("app/resources/icons/settings.svg"))
        for b in (btn_dashboard, btn_patients, btn_appointments, btn_inventory, btn_settings):
            b.setIconSize(QSize(18, 18))
            b.setCheckable(True)

        # Put buttons in a group so only one is active at a time
        self.sidebar_buttons = [btn_dashboard, btn_patients, btn_appointments, btn_inventory, btn_settings]
        # save icon filenames aligned with the buttons for recoloring
        self.sidebar_icon_files = ["dashboard.svg", "patients.svg", "appointments.svg", "inventory.svg", "settings.svg"]
        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        for idx, b in enumerate(self.sidebar_buttons):
            self._btn_group.addButton(b, idx)
        # Set shortcuts and tooltips
        btn_dashboard.setShortcut("Alt+D")
        btn_dashboard.setToolTip(_("Dashboard (Alt+D)"))
        btn_patients.setShortcut("Alt+P")
        btn_patients.setToolTip(_("Patients (Alt+P)"))
        btn_appointments.setShortcut("Alt+A")
        btn_appointments.setToolTip(_("Appointments (Alt+A)"))
        btn_inventory.setShortcut("Alt+I")
        btn_inventory.setToolTip(_("Inventory (Alt+I)"))
        btn_settings.setShortcut("Alt+S")
        btn_settings.setToolTip(_("Settings (Alt+S)"))

        # recolor icons to match initial theme (deferred to apply_style to avoid calling
        # methods that may be defined later during import)


        for btn in (btn_dashboard, btn_patients, btn_appointments, btn_inventory, btn_settings):
            btn.setObjectName("SidebarButton")
            sidebar_layout.addWidget(btn)

        # ===== Pages =====
        self.pages = QStackedWidget()

        # Dashboard page
        dashboard = QWidget()
        dash_layout = QVBoxLayout(dashboard)

        cards_row = QHBoxLayout()
        self.card_patients = self.create_card(_("Total Patients"), "0")
        self.card_appointments = self.create_card(_("Appointments Today"), "0")
        self.card_inventory = self.create_card(_("Inventory Items"), "0")

        cards_row.addWidget(self.card_patients)
        cards_row.addWidget(self.card_appointments)
        cards_row.addWidget(self.card_inventory)
        dash_layout.addLayout(cards_row)

        # Charts row (Patients by condition, Appointments per doctor)
        self.chart_row = QHBoxLayout()
        self.patient_chart_view = self.create_patient_chart()
        self.appointments_chart_view = self.create_appointments_chart()
        self.chart_row.addWidget(self.patient_chart_view)
        self.chart_row.addWidget(self.appointments_chart_view)
        dash_layout.addLayout(self.chart_row)

        dash_layout.addWidget(QLabel(_("Welcome to the Clinic Dashboard!")))
        self.pages.addWidget(dashboard)

        # تحديث الإحصائيات عند بدء التشغيل
        self.update_dashboard()

        # Patients page
        patients_page = QWidget()
        patients_layout = QVBoxLayout(patients_page)

        self.table_patients = QTableWidget()
        self.table_patients.setColumnCount(5)
        self.table_patients.setHorizontalHeaderLabels([_("Name"), _("Age"), _("Condition"), _("Edit"), _("Delete")])
        patients_layout.addWidget(self.table_patients)

        form_patients = QFormLayout()
        self.input_name = QLineEdit()
        self.input_age = QLineEdit()
        self.input_condition = QLineEdit()
        btn_add_patient = QPushButton(_("Add Patient"))
        btn_add_patient.clicked.connect(self.add_patient)

        form_patients.addRow(_("Name:"), self.input_name)
        form_patients.addRow(_("Age:"), self.input_age)
        form_patients.addRow(_("Condition:"), self.input_condition)
        form_patients.addRow(btn_add_patient)
        patients_layout.addLayout(form_patients)

        self.pages.addWidget(patients_page)

        # Appointments page
        from PySide6.QtWidgets import QCalendarWidget, QDateEdit, QTimeEdit, QSpinBox
        from PySide6.QtCore import QDate, QTime

        appointments_page = QWidget()
        appt_root_layout = QHBoxLayout(appointments_page)

        # Left: calendar
        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.selectionChanged.connect(lambda: self.load_appointments_for_date(self.calendar_widget.selectedDate()))
        appt_root_layout.addWidget(self.calendar_widget, 1)

        # Right: appointments list + form
        right_col = QVBoxLayout()

        self.table_appointments = QTableWidget()
        # add Reschedule + Cancel columns in addition to Edit/Delete
        self.table_appointments.setColumnCount(7)
        self.table_appointments.setHorizontalHeaderLabels([_("Patient"), _("Doctor"), _("Date"), _("Edit"), _("Reschedule"), _("Cancel"), _("Delete")])
        right_col.addWidget(self.table_appointments)

        form_appt = QFormLayout()
        self.input_appt_patient = QLineEdit()
        self.input_appt_doctor = QLineEdit()
        self.input_appt_date = QDateEdit()
        self.input_appt_date.setCalendarPopup(True)
        self.input_appt_date.setDate(QDate.currentDate())
        # Compatibility helpers: tests expect setText()/text() like QLineEdit
        # We track validity separately so setting an invalid string doesn't raise
        # but add_appointment can detect invalid inputs and refuse to create appointments.
        self._appt_date_input_valid = True
        def _set_date_text(s):
            try:
                # try parse as ISO YYYY-MM-DD
                from datetime import date as _pdate
                dpy = _pdate.fromisoformat(s)
                qd = QDate(dpy.year, dpy.month, dpy.day)
            except Exception:
                # fallback to QDate parsing
                qd = QDate.fromString(s, 'yyyy-MM-dd')
            if qd.isValid():
                self.input_appt_date.setDate(qd)
                self._appt_date_input_valid = True
            else:
                # mark invalid but do not raise here (tests expect setText to not throw)
                self._appt_date_input_valid = False

        def _date_text():
            return self.input_appt_date.date().toString('yyyy-MM-dd')

        self.input_appt_date.setText = _set_date_text
        self.input_appt_date.text = _date_text
        self.input_appt_time = QTimeEdit()
        self.input_appt_time.setTime(QTime.currentTime())
        self.input_appt_duration = QSpinBox()
        self.input_appt_duration.setRange(5, 240)
        self.input_appt_duration.setValue(30)

        btn_add_appt = QPushButton(_("Add Appointment"))
        btn_add_appt.clicked.connect(self.add_appointment)

        form_appt.addRow(_("Patient:"), self.input_appt_patient)
        form_appt.addRow(_("Doctor:"), self.input_appt_doctor)
        form_appt.addRow(_("Date:"), self.input_appt_date)
        form_appt.addRow(_("Time:"), self.input_appt_time)
        form_appt.addRow(_("Duration (min):"), self.input_appt_duration)
        form_appt.addRow(btn_add_appt)

        right_col.addLayout(form_appt)
        appt_root_layout.addLayout(right_col, 2)

        self.pages.addWidget(appointments_page)

        # load today's appointments
        self.load_appointments_for_date(self.calendar_widget.selectedDate())

        # Inventory page
        inventory_page = QWidget()
        inventory_layout = QVBoxLayout(inventory_page)

        self.table_inventory = QTableWidget()
        self.table_inventory.setColumnCount(5)
        self.table_inventory.setHorizontalHeaderLabels([_("Item"), _("Quantity"), _("Category"), _("Edit"), _("Delete")])
        inventory_layout.addWidget(self.table_inventory)

        form_inv = QFormLayout()
        self.input_item_name = QLineEdit()
        self.input_quantity = QLineEdit()
        self.input_category = QLineEdit()
        btn_add_item = QPushButton(_("Add Item"))
        btn_add_item.clicked.connect(self.add_inventory)

        form_inv.addRow(_("Item:"), self.input_item_name)
        form_inv.addRow(_("Quantity:"), self.input_quantity)
        form_inv.addRow(_("Category:"), self.input_category)
        form_inv.addRow(btn_add_item)
        inventory_layout.addLayout(form_inv)

        self.pages.addWidget(inventory_page)

        # Settings page
        settings_page = QWidget()
        settings_layout = QVBoxLayout(settings_page)
        lbl_settings = QLabel(_("Settings"))
        lbl_settings.setObjectName("SettingsTitle")

        # Theme toggle (animated)
        h_theme = QHBoxLayout()
        lbl_theme = QLabel(_("Dark Theme"))
        self.toggle_theme = ToggleSwitch(self.get_saved_theme() == 'dark')
        self.toggle_theme.toggled.connect(self.on_theme_toggled)
        h_theme.addWidget(lbl_theme)
        h_theme.addWidget(self.toggle_theme)
        h_theme.addStretch()
        settings_layout.addWidget(lbl_settings)
        settings_layout.addLayout(h_theme)

        # Language selector (placeholder for RTL support)
        h_lang = QHBoxLayout()
        lbl_lang = QLabel(_("Language"))
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("English", "en")
        self.combo_lang.addItem("العربية", "ar")
        self.combo_lang.setCurrentIndex(0 if self.get_saved_language() == 'en' else 1)
        self.combo_lang.currentIndexChanged.connect(lambda idx: self.on_language_changed(self.combo_lang.itemData(idx)))
        h_lang.addWidget(lbl_lang)
        h_lang.addWidget(self.combo_lang)
        h_lang.addStretch()
        settings_layout.addLayout(h_lang)

        # Font notice (shown if Arabic selected and no Arabic font is available)
        self.lbl_font_notice = QLabel("")
        self.lbl_font_notice.setWordWrap(True)
        self.lbl_font_notice.setStyleSheet("color: #f59e0b;")
        settings_layout.addWidget(self.lbl_font_notice)
        self.lbl_font_notice.setVisible(False)

        settings_layout.addStretch(1)
        self.pages.addWidget(settings_page)

        # ===== Connect buttons =====
        btn_dashboard.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_patients.clicked.connect(lambda: self.show_patients())
        btn_appointments.clicked.connect(lambda: self.show_appointments())
        btn_inventory.clicked.connect(lambda: self.show_inventory())
        btn_settings.clicked.connect(lambda: self.pages.setCurrentIndex(4))

        # ===== Layout =====
        container = QWidget()
        root = QHBoxLayout(container)
        sidebar.setFixedWidth(240)
        root.addWidget(sidebar)
        root.addWidget(self.pages)
        self.setCentralWidget(container)
        self.apply_style()

    # ===== Patients =====
    def show_patients(self):
        session = SessionLocal()
        patients = session.query(Patient).all()
        self.table_patients.setRowCount(len(patients))
        for row, patient in enumerate(patients):
            self.table_patients.setItem(row, 0, QTableWidgetItem(patient.name))
            self.table_patients.setItem(row, 1, QTableWidgetItem(str(patient.age)))
            self.table_patients.setItem(row, 2, QTableWidgetItem(patient.condition))

            btn_edit = QPushButton(_("Edit"))
            btn_edit.clicked.connect(lambda _, pid=patient.id: self.edit_patient(pid))
            self.table_patients.setCellWidget(row, 3, btn_edit)

            btn_delete = QPushButton(_("Delete"))
            btn_delete.clicked.connect(lambda _, pid=patient.id: self.delete_patient(pid))
            self.table_patients.setCellWidget(row, 4, btn_delete)
        session.close()
        self.pages.setCurrentIndex(1)
        self.update_dashboard()

    def add_patient(self):
        session = SessionLocal()
        try:
            # validate age
            try:
                age_val = int(self.input_age.text())
            except ValueError:
                QMessageBox.warning(self, _("Invalid Age"), _("Please enter a valid integer age"))
                return

            new_patient = Patient(
                name=self.input_name.text(),
                age=age_val,
                condition=self.input_condition.text()
            )
            session.add(new_patient)
            if not self._safe_commit(session):
                return
        finally:
            session.close()
        self.show_patients()

    def edit_patient(self, patient_id):
        session = SessionLocal()
        try:
            patient = session.get(Patient, patient_id)
            if patient:
                dialog = PatientEditDialog(patient, self)
                if dialog.exec():  # إذا ضغط المستخدم Save
                    data = dialog.get_data()
                    patient.name = data["name"]
                    patient.age = data["age"]
                    patient.condition = data["condition"]
                    if not self._safe_commit(session):
                        return
        finally:
            session.close()
        self.show_patients()

    def delete_patient(self, patient_id):
        session = SessionLocal()
        try:
            patient = session.get(Patient, patient_id)
            if patient:
                confirm = QMessageBox.question(self, _("Confirm Delete"),
                                               _("Are you sure you want to delete this patient?"),
                                               QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    session.delete(patient)
                    if not self._safe_commit(session):
                        return
        finally:
            session.close()
        self.show_patients()
    
     # ===== Appointments =====
    def show_appointments(self):
        # Keep backward compatibility: jump to the appointments page
        self.pages.setCurrentIndex(2)
        # load for currently selected calendar date
        if hasattr(self, 'calendar_widget'):
            self.load_appointments_for_date(self.calendar_widget.selectedDate())
        else:
            session = SessionLocal()
            appointments = session.query(Appointment).all()
            self.table_appointments.setRowCount(len(appointments))
            for row, appt in enumerate(appointments):
                self.table_appointments.setItem(row, 0, QTableWidgetItem(appt.patient_name))
                self.table_appointments.setItem(row, 1, QTableWidgetItem(appt.doctor_name))
                self.table_appointments.setItem(row, 2, QTableWidgetItem(str(appt.date)))

                btn_edit = QPushButton(_("Edit"))
                btn_edit.clicked.connect(lambda _, aid=appt.id: self.edit_appointment(aid))
                self.table_appointments.setCellWidget(row, 3, btn_edit)

                btn_resched = QPushButton(_("Reschedule"))
                btn_resched.clicked.connect(lambda _, aid=appt.id: self.open_reschedule_dialog(aid))
                self.table_appointments.setCellWidget(row, 4, btn_resched)

                btn_cancel = QPushButton(_("Cancel"))
                btn_cancel.clicked.connect(lambda _, aid=appt.id: self.cancel_appointment(aid))
                self.table_appointments.setCellWidget(row, 5, btn_cancel)

                btn_delete = QPushButton(_("Delete"))
                btn_delete.clicked.connect(lambda _, aid=appt.id: self.delete_appointment(aid))
                self.table_appointments.setCellWidget(row, 6, btn_delete)
            session.close()
        self.update_dashboard()

    def load_appointments_for_date(self, qdate):
        """Load appointments that fall on the given QDate into the appointments table."""
        # convert QDate to datetime range
        from datetime import datetime, time as dtime
        d = qdate.toPython() if hasattr(qdate, 'toPython') else date.fromisoformat(qdate.toString('yyyy-MM-dd'))
        start = datetime.combine(d, dtime.min)
        end = datetime.combine(d, dtime.max)

        session = SessionLocal()
        try:
            # Do not include cancelled appointments
            appts = session.query(Appointment).filter(Appointment.date >= start, Appointment.date <= end, Appointment.status != 'cancelled').all()
            self.table_appointments.setRowCount(len(appts))
            for row, appt in enumerate(appts):
                self.table_appointments.setItem(row, 0, QTableWidgetItem(appt.patient_name))
                self.table_appointments.setItem(row, 1, QTableWidgetItem(appt.doctor_name))
                # show date + time + duration
                dt = appt.date.strftime('%Y-%m-%d %H:%M') if appt.date else ''
                dur = f" ({getattr(appt, 'duration_minutes', 30)} min)"
                self.table_appointments.setItem(row, 2, QTableWidgetItem(dt + dur))

                btn_edit = QPushButton(_("Edit"))
                btn_edit.clicked.connect(lambda _, aid=appt.id: self.edit_appointment(aid))
                self.table_appointments.setCellWidget(row, 3, btn_edit)

                btn_resched = QPushButton(_("Reschedule"))
                btn_resched.clicked.connect(lambda _, aid=appt.id: self.open_reschedule_dialog(aid))
                self.table_appointments.setCellWidget(row, 4, btn_resched)

                btn_cancel = QPushButton(_("Cancel"))
                btn_cancel.clicked.connect(lambda _, aid=appt.id: self.cancel_appointment(aid))
                self.table_appointments.setCellWidget(row, 5, btn_cancel)

                btn_delete = QPushButton(_("Delete"))
                btn_delete.clicked.connect(lambda _, aid=appt.id: self.delete_appointment(aid))
                self.table_appointments.setCellWidget(row, 6, btn_delete)
        finally:
            session.close()

    def add_appointment(self):
        # Create appointment using the new form with date + time + duration
        # If the last textual date input was invalid, refuse to create the appointment.
        if hasattr(self, '_appt_date_input_valid') and not self._appt_date_input_valid:
            QMessageBox.warning(self, _("Invalid Date"), _("Please enter date as YYYY-MM-DD"))
            return False
        try:
            qdate = self.input_appt_date.date()
            qtime = self.input_appt_time.time()
            appt_dt = date.fromisoformat(qdate.toString('yyyy-MM-dd'))
            appt_datetime = datetime.combine(appt_dt, qtime.toPython()) if hasattr(qtime, 'toPython') else datetime(appt_dt.year, appt_dt.month, appt_dt.day, qtime.hour(), qtime.minute())
        except Exception as e:
            # print exception so tests can show reason for failure
            print("add_appointment: failed to parse date/time:", repr(e))
            QMessageBox.warning(self, _("Invalid Date"), _("Please enter date as YYYY-MM-DD"))
            return False

        session = SessionLocal()
        try:
            duration = int(self.input_appt_duration.value()) if hasattr(self, 'input_appt_duration') else 30
            # Prevent exact and time-range overlap for same doctor
            if has_overlapping_appointment(session, self.input_appt_doctor.text(), appt_datetime, duration):
                QMessageBox.warning(self, _("Time slot unavailable"), _("This doctor already has an overlapping appointment"))
                return False
            new_appt = Appointment(
                patient_name=self.input_appt_patient.text(),
                doctor_name=self.input_appt_doctor.text(),
                date=appt_datetime,
                duration_minutes=duration
            )
            session.add(new_appt)
            if not self._safe_commit(session):
                return False
        finally:
            session.close()
        # refresh the calendar view for selected date
        self.load_appointments_for_date(self.calendar_widget.selectedDate())
        # update dashboard counts
        self.update_dashboard()
        return True

    def edit_appointment(self, appt_id):
        session = SessionLocal()
        try:
            appt = session.get(Appointment, appt_id)
            if appt:
                appt.patient_name = self.input_appt_patient.text() or appt.patient_name
                appt.doctor_name = self.input_appt_doctor.text() or appt.doctor_name
                if self.input_appt_date.text():
                    try:
                        appt.date = date.fromisoformat(self.input_appt_date.text())
                    except ValueError:
                        QMessageBox.warning(self, _("Invalid Date"), _("Please enter date as YYYY-MM-DD"))
                        return
                if not self._safe_commit(session):
                    return
        finally:
            session.close()
        self.show_appointments()

    def delete_appointment(self, appt_id):
        session = SessionLocal()
        try:
            appt = session.get(Appointment, appt_id)
            if appt:
                confirm = QMessageBox.question(self, _("Confirm Delete"),
                                               _("Are you sure you want to delete this appointment?"),
                                               QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    session.delete(appt)
                    if not self._safe_commit(session):
                        return
        finally:
            session.close()
        self.show_appointments()

    def cancel_appointment(self, appt_id):
        """Mark appointment as cancelled (status='cancelled'). Returns True on success."""
        session = SessionLocal()
        try:
            appt = session.get(Appointment, appt_id)
            if not appt:
                return False
            appt.status = 'cancelled'
            if not self._safe_commit(session):
                return False
        finally:
            session.close()
        # refresh UI
        try:
            self.load_appointments_for_date(self.calendar_widget.selectedDate())
        except Exception:
            pass
        self.update_dashboard()
        return True

    def reschedule_appointment(self, appt_id, new_qdate, new_qtime):
        """Reschedule an existing appointment to a new QDate/QTime.

        Returns True on success, False otherwise.
        """
        from datetime import datetime
        session = SessionLocal()
        try:
            appt = session.get(Appointment, appt_id)
            if not appt:
                return False
            # convert QDate to date
            d = new_qdate.toPython() if hasattr(new_qdate, 'toPython') else date.fromisoformat(new_qdate.toString('yyyy-MM-dd'))
            # convert QTime to time
            if hasattr(new_qtime, 'toPython'):
                t = new_qtime.toPython()
            else:
                # QTime-like fallback
                try:
                    t = datetime(1,1,1,new_qtime.hour(), new_qtime.minute()).time()
                except Exception:
                    t = None
            if t is None:
                return False
            new_dt = datetime.combine(d, t)
            duration = getattr(appt, 'duration_minutes', 30)
            if has_overlapping_appointment(session, appt.doctor_name, new_dt, duration, exclude_id=appt_id):
                QMessageBox.warning(self, _("Time slot unavailable"), _("This doctor already has an overlapping appointment"))
                return False
            appt.date = new_dt
            if not self._safe_commit(session):
                return False
        finally:
            session.close()
        # refresh views
        try:
            self.load_appointments_for_date(self.calendar_widget.selectedDate())
        except Exception:
            pass
        self.update_dashboard()
        return True

    # ===== Inventory =====
    def show_inventory(self):
        session = SessionLocal()
        items = session.query(Inventory).all()
        self.table_inventory.setRowCount(len(items))
        for row, item in enumerate(items):
            self.table_inventory.setItem(row, 0, QTableWidgetItem(item.item_name))
            self.table_inventory.setItem(row, 1, QTableWidgetItem(str(item.quantity)))
            self.table_inventory.setItem(row, 2, QTableWidgetItem(item.category))

            btn_edit = QPushButton(_("Edit"))
            btn_edit.clicked.connect(lambda _, iid=item.id: self.edit_inventory(iid))
            self.table_inventory.setCellWidget(row, 3, btn_edit)

            btn_delete = QPushButton(_("Delete"))
            btn_delete.clicked.connect(lambda _, iid=item.id: self.delete_inventory(iid))
            self.table_inventory.setCellWidget(row, 4, btn_delete)
        session.close()
        self.pages.setCurrentIndex(3)
        self.update_dashboard()

    def add_inventory(self):
        session = SessionLocal()
        try:
            # validate quantity
            try:
                qty = int(self.input_quantity.text())
            except ValueError:
                QMessageBox.warning(self, _("Invalid Quantity"), _("Please enter a valid integer quantity"))
                return

            new_item = Inventory(
                item_name=self.input_item_name.text(),
                quantity=qty,
                category=self.input_category.text()
            )
            session.add(new_item)
            if not self._safe_commit(session):
                return
        finally:
            session.close()
        self.show_inventory()

    def edit_inventory(self, item_id):
        session = SessionLocal()
        try:
            item = session.get(Inventory, item_id)
            if item:
                item.item_name = self.input_item_name.text() or item.item_name
                item.quantity = int(self.input_quantity.text()) if self.input_quantity.text() else item.quantity
                item.category = self.input_category.text() or item.category
                if not self._safe_commit(session):
                    return
        finally:
            session.close()
        self.show_inventory()

    def delete_inventory(self, item_id):
        session = SessionLocal()
        try:
            item = session.get(Inventory, item_id)
            if item:
                confirm = QMessageBox.question(self, _("Confirm Delete"),
                                               _("Are you sure you want to delete this item?"),
                                               QMessageBox.Yes | QMessageBox.No)
                if confirm == QMessageBox.Yes:
                    session.delete(item)
                    if not self._safe_commit(session):
                        return
        finally:
            session.close()
        self.show_inventory()

    # ===== Dashboard helpers =====
    def create_card(self, title, value, color="#10b981"):
        """Create a card-like QPushButton with a small indicator and large value label."""
        btn = QPushButton()
        btn.setObjectName("Card")
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(btn)
        header = QHBoxLayout()

        indicator = QLabel()
        indicator.setFixedSize(12, 12)
        indicator.setStyleSheet(f"background-color: {color}; border-radius: 6px;")
        lbl_title = QLabel(title)
        lbl_title.setObjectName("CardTitle")
        header.addWidget(indicator)
        header.addSpacing(8)
        header.addWidget(lbl_title)
        header.addStretch()

        lbl_value = QLabel(value)
        lbl_value.setObjectName("CardValue")

        layout.addLayout(header)
        layout.addWidget(lbl_value)

        btn.value_label = lbl_value   # نخزن المرجع للـ Label
        btn.title_label = lbl_title   # نخزن المرجع للـ Title حتى نغيّر النص لاحقًا
        return btn

    def create_patient_chart(self):
        session = SessionLocal()
        patients = session.query(Patient).all()
        session.close()

        # حساب عدد المرضى لكل حالة
        conditions = {}
        for p in patients:
            key = p.condition or "Unknown"
            conditions[key] = conditions.get(key, 0) + 1

        if not conditions:
            lbl = QLabel(_("No patient data"))
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        palette = ["#06b6d4", "#60a5fa", "#f59e0b", "#ef4444", "#10b981", "#a78bfa", "#f472b6", "#f97316"]

        series = QPieSeries()
        for i, (condition, count) in enumerate(conditions.items()):
            slice = series.append(condition, count)
            slice.setLabel(f"{condition} ({count})")
            slice.setLabelVisible(True)
            color = QColor(palette[i % len(palette)])
            slice.setBrush(QBrush(color))

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(_("Patients by Condition"))
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        return chart_view

    def create_appointments_chart(self):
        session = SessionLocal()
        try:
            appts = session.query(Appointment).all()
        except Exception:
            # fallback if DB schema is missing newer columns: use a raw select for basic columns
            try:
                res = session.execute("SELECT id, patient_name, doctor_name, date FROM appointments")
                appts = []
                for row in res:
                    class _A: pass
                    a = _A()
                    a.id = row[0]
                    a.patient_name = row[1]
                    a.doctor_name = row[2]
                    a.date = row[3]
                    appts.append(a)
            except Exception:
                appts = []
        finally:
            session.close()

        counts = {}
        for a in appts:
            doctor = a.doctor_name or _("Unknown")
            counts[doctor] = counts.get(doctor, 0) + 1

        if not counts:
            lbl = QLabel(_("No appointments"))
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        palette = ["#06b6d4", "#60a5fa", "#f59e0b", "#ef4444", "#10b981", "#a78bfa", "#f472b6", "#f97316"]

        series = QBarSeries()
        categories = []
        max_val = 0
        for i, (doctor, count) in enumerate(counts.items()):
            set_i = QBarSet(doctor)
            set_i.append(count)
            color = QColor(palette[i % len(palette)])
            set_i.setBrush(QBrush(color))
            series.append(set_i)
            categories.append(doctor)
            if count > max_val:
                max_val = count

        series.setLabelsVisible(True)
        series.setLabelsFormat("%d")

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(_("Appointments per Doctor"))
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QBarCategoryAxis()
        axisX.append(categories)
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)

        axisY = QValueAxis()
        axisY.setRange(0, max(1, int(max_val * 1.2)))
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        return chart_view

    def refresh_charts(self):
        # إزالة المخططات الحالية وإعادة إنشائها لكي تنعكس التغييرات
        if not hasattr(self, 'chart_row'):
            return
        layout = self.chart_row
        for i in reversed(range(layout.count())):
            item = layout.takeAt(i)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # إعادة إنشاء المخططات
        self.patient_chart_view = self.create_patient_chart()
        self.appointments_chart_view = self.create_appointments_chart()
        layout.addWidget(self.patient_chart_view)
        layout.addWidget(self.appointments_chart_view)

    def update_dashboard(self):
        session = SessionLocal()

        # عدد المرضى
        total_patients = session.query(Patient).count()
        self.card_patients.value_label.setText(str(total_patients))

        # عدد المواعيد اليوم
        today = date.today()
        # appointments whose date falls on today's date (ignore time) and are not cancelled
        from datetime import datetime, time as dtime
        start = datetime.combine(today, dtime.min)
        end = datetime.combine(today, dtime.max)
        appointments_today = session.query(Appointment).filter(
            Appointment.date >= start,
            Appointment.date <= end,
            Appointment.status != 'cancelled'
        ).count()
        self.card_appointments.value_label.setText(str(appointments_today))

        # عدد عناصر المخزون
        total_items = session.query(Inventory).count()
        self.card_inventory.value_label.setText(str(total_items))

        session.close()

        # تحديث الرسوم البيانية عندما تتغير البيانات
        self.refresh_charts()

    def _safe_commit(self, session):
        """Try to commit, rollback and show a message on failure."""
        try:
            session.commit()
            return True
        except Exception as e:
            try:
                session.rollback()
            except Exception:
                pass
            QMessageBox.critical(self, _("Database Error"), str(e))
            return False

    # ===== Reschedule dialog / UI =====
    def open_reschedule_dialog(self, appt_id):
        """Open a reschedule dialog for the given appointment id and apply changes if accepted."""
        session = SessionLocal()
        try:
            appt = session.get(Appointment, appt_id)
            if not appt:
                return False
            current_dt = appt.date
        finally:
            session.close()

        dialog = RescheduleDialog(self, current_dt)
        res = dialog.exec()
        if res == QDialog.Accepted:
            qd = dialog.date_edit.date()
            qt = dialog.time_edit.time()
            return self.reschedule_appointment(appt_id, qd, qt)
        return False

    # ===== Style =====
    def get_saved_theme(self):
        settings = QSettings("clinic_app", "clinic_desktop_app")
        return settings.value("theme", "dark")

    def save_theme(self, theme):
        settings = QSettings("clinic_app", "clinic_desktop_app")
        settings.setValue("theme", theme)

    def get_saved_language(self):
        settings = QSettings("clinic_app", "clinic_desktop_app")
        return settings.value("language", "en")

    def save_language(self, lang):
        settings = QSettings("clinic_app", "clinic_desktop_app")
        settings.setValue("language", lang)

    def set_language(self, lang):
        # placeholder: set layout direction for RTL languages
        if lang == 'ar':
            self.setLayoutDirection(Qt.RightToLeft)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
        self.save_language(lang)

    def on_language_changed(self, lang):
        self.load_translation(lang)
        self.set_language(lang)
        self.refresh_ui_texts()

    def fonts_dir(self):
        # folder where custom fonts can be placed
        base = os.path.dirname(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(base, 'resources', 'fonts'))

    def load_font_for_language(self, lang):
        # for Arabic, look for NotoSansArabic-Regular.ttf in resources/fonts
        if lang != 'ar':
            return False
        fpath = os.path.join(self.fonts_dir(), 'NotoSansArabic-Regular.ttf')
        if os.path.exists(fpath):
            id = QFontDatabase.addApplicationFont(fpath)
            if id != -1:
                families = QFontDatabase.applicationFontFamilies(id)
                if families:
                    QApplication.setFont(QFont(families[0]))
                    return True
        return False

    def set_language(self, lang):
        # set layout direction for RTL languages and attempt to load Arabic font if requested
        if lang == 'ar':
            self.setLayoutDirection(Qt.RightToLeft)
            ok = self.load_font_for_language('ar')
            if hasattr(self, 'lbl_font_notice'):
                if ok:
                    self.lbl_font_notice.setVisible(False)
                else:
                    self.lbl_font_notice.setText(_("To improve Arabic typography, place 'NotoSansArabic-Regular.ttf' into app/resources/fonts/"))
                    self.lbl_font_notice.setVisible(True)
        else:
            self.setLayoutDirection(Qt.LeftToRight)
            if hasattr(self, 'lbl_font_notice'):
                self.lbl_font_notice.setVisible(False)
        self.save_language(lang)

    def apply_theme(self, theme_name):
        """Apply theme by loading the corresponding QSS file."""
        qss_path = f"app/resources/styles_{theme_name}.qss"
        try:
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            # fallback to default dark style if missing
            try:
                with open("app/resources/styles_dark.qss", "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except FileNotFoundError:
                pass
        # recolor sidebar icons to match theme
        icon_color = '#dbeafe' if theme_name == 'dark' else '#0b1220'
        try:
            self.recolor_sidebar_icons(icon_color)
        except Exception:
            pass
        # keep the toggle in sync if it exists
        if hasattr(self, 'toggle_theme'):
            # avoid re-triggering signal
            try:
                self.toggle_theme.toggled.disconnect(self.on_theme_toggled)
            except Exception:
                pass
            self.toggle_theme.setChecked(True if theme_name == 'dark' else False)
            self.toggle_theme.toggled.connect(self.on_theme_toggled)

    def recolor_sidebar_icons(self, color):
        """Tint sidebar SVG icons to the given color and set them back to buttons.

        Prefer a mono SVG variant (e.g. `dashboard_mono.svg`) if available; otherwise use original.
        """
        try:
            for btn, fname in zip(self.sidebar_buttons, self.sidebar_icon_files):
                base, ext = os.path.splitext(fname)
                mono_name = f"{base}_mono{ext}"
                # prefer mono variant when present
                candidate = None
                mono_path = os.path.join('app', 'resources', 'icons', mono_name)
                orig_path = os.path.join('app', 'resources', 'icons', fname)
                if os.path.exists(mono_path):
                    candidate = mono_path
                elif os.path.exists(orig_path):
                    candidate = orig_path
                else:
                    continue

                icon = QIcon(candidate)
                size = btn.iconSize()
                pix = icon.pixmap(size)
                if pix.isNull():
                    continue
                tinted = QPixmap(pix.size())
                tinted.fill(Qt.transparent)
                painter = QPainter(tinted)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.drawPixmap(0, 0, pix)
                painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
                painter.fillRect(tinted.rect(), QColor(color))
                painter.end()
                btn.setIcon(QIcon(tinted))
        except Exception:
            pass

    def on_theme_toggled(self, state):
        # state may be int (Qt.Checked) or bool from ToggleSwitch
        if isinstance(state, bool):
            checked = state
        else:
            checked = True if state == Qt.Checked else False
        theme = 'dark' if checked else 'light'
        self.apply_theme(theme)
        self.save_theme(theme)

    def apply_style(self):
        # This method initializes the theme from saved settings and language
        theme = self.get_saved_theme()
        self.apply_theme(theme)
        # apply language (layout direction)
        self.load_translation(self.get_saved_language())
        self.set_language(self.get_saved_language())
        # refresh UI texts to reflect translation
        self.refresh_ui_texts()

    def _on_page_changed(self, idx):
        try:
            btn = self.sidebar_buttons[idx]
            btn.setChecked(True)
        except Exception:
            pass

    def load_translation(self, lang):
        """Load gettext translation for given language and set global _ function.

        Falls back to a minimal built-in Arabic mapping when .mo files are not present (for demo).
        """
        global _
        localedir = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations'))
        try:
            t = gettext.translation('messages', localedir=localedir, languages=[lang])
            t.install()
            _ = t.gettext
        except Exception:
            # fallback: if Arabic requested, use small in-memory mapping so UI updates for demo/testing
            if lang == 'ar':
                mapping = {
                    "Clinic Management System": "نظام إدارة العيادة",
                    "Dashboard": "لوحة التحكم",
                    "Patients": "المرضى",
                    "Appointments": "المواعيد",
                    "Inventory": "المخزون",
                    "Settings": "الإعدادات",
                    "Dashboard (Alt+D)": "لوحة التحكم (Alt+D)",
                    "Patients (Alt+P)": "المرضى (Alt+P)",
                    "Appointments (Alt+A)": "المواعيد (Alt+A)",
                    "Inventory (Alt+I)": "المخزون (Alt+I)",
                    "Settings (Alt+S)": "الإعدادات (Alt+S)",
                    "Total Patients": "إجمالي المرضى",
                    "Appointments Today": "مواعيد اليوم",
                    "Inventory Items": "عناصر المخزون",
                    "Name": "الاسم",
                    "Age": "العمر",
                    "Condition": "الحالة",
                    "Edit": "تعديل",
                    "Delete": "حذف",
                    "Patient": "المريض",
                    "Doctor": "الطبيب",
                    "Date": "التاريخ",
                    "Item": "العنصر",
                    "Quantity": "الكمية",
                    "Category": "الفئة",
                    "Dark Theme": "الوضع الداكن",
                    "Language": "اللغة",
                    "No patient data": "لا توجد بيانات للمرضى",
                    "No appointments": "لا توجد مواعيد",
                    "Patients by Condition": "المرضى حسب الحالة",
                    "Appointments per Doctor": "المواعيد لكل طبيب",
                    "Welcome to the Clinic Dashboard!": "مرحباً بك في لوحة تحكم العيادة!",
                    "Add Patient": "إضافة مريض",
                    "Add Appointment": "إضافة موعد",
                    "Add Item": "إضافة عنصر",
                    "Invalid Age": "عمر غير صالح",
                    "Please enter a valid integer age": "الرجاء إدخال عمر صحيح",
                    "Invalid Date": "تاريخ غير صالح",
                    "Please enter date as YYYY-MM-DD": "الرجاء إدخال التاريخ بالشكل YYYY-MM-DD",
                    "Confirm Delete": "تأكيد الحذف",
                    "Are you sure you want to delete this patient?": "هل أنت متأكد أنك تريد حذف هذا المريض؟",
                    "Are you sure you want to delete this appointment?": "هل أنت متأكد أنك تريد حذف هذا الموعد؟",
                    "Are you sure you want to delete this item?": "هل أنت متأكد أنك تريد حذف هذا العنصر؟",
                    "To improve Arabic typography, place 'NotoSansArabic-Regular.ttf' into app/resources/fonts/": "لتحسين مظهر العربية، ضع 'NotoSansArabic-Regular.ttf' في app/resources/fonts/"
                }
                def gettext_ar(s):
                    return mapping.get(s, s)
                _ = gettext_ar
            else:
                _ = gettext.gettext

    def refresh_ui_texts(self):
        """Refresh visible UI texts to use the current gettext translations."""
        # Window title
        self.setWindowTitle(_("Clinic Management System"))
        # Sidebar
        labels = [_("Dashboard"), _("Patients"), _("Appointments"), _("Inventory"), _("Settings")]
        tooltips = [_("Dashboard (Alt+D)"), _("Patients (Alt+P)"), _("Appointments (Alt+A)"), _("Inventory (Alt+I)"), _("Settings (Alt+S)")]
        for b, txt, tip in zip(self.sidebar_buttons, labels, tooltips):
            b.setText(txt)
            b.setToolTip(tip)
        # Cards
        self.card_patients.title_label.setText(_("Total Patients"))
        self.card_appointments.title_label.setText(_("Appointments Today"))
        self.card_inventory.title_label.setText(_("Inventory Items"))
        # Tables headers
        self.table_patients.setHorizontalHeaderLabels([_("Name"), _("Age"), _("Condition"), _("Edit"), _("Delete")])
        self.table_appointments.setHorizontalHeaderLabels([_("Patient"), _("Doctor"), _("Date"), _("Edit"), _("Delete")])
        self.table_inventory.setHorizontalHeaderLabels([_("Item"), _("Quantity"), _("Category"), _("Edit"), _("Delete")])
        # Settings labels
        try:
            # Toggle label
            # find label sibling of toggle (we created lbl_theme variable but didn't store it; find in settings page)
            settings_page = self.pages.widget(4)
            for lbl in settings_page.findChildren(QLabel):
                if lbl.objectName() == "SettingsTitle":
                    lbl.setText(_("Settings"))
            # update combo box entries (keep Language text as given names)
            # update other helpers
        except Exception:
            pass


class RescheduleDialog(QDialog):
    def __init__(self, parent=None, current_dt=None):
        super().__init__(parent)
        self.setWindowTitle(_("Reschedule Appointment"))
        self.setModal(True)
        layout = QVBoxLayout(self)
        from PySide6.QtCore import QDate, QTime
        self.date_edit = QDateEdit()
        self.time_edit = QTimeEdit()
        if current_dt:
            # current_dt is a datetime
            self.date_edit.setDate(QDate(current_dt.year, current_dt.month, current_dt.day))
            self.time_edit.setTime(QTime(current_dt.hour, current_dt.minute))
        else:
            self.date_edit.setDate(QDate.currentDate())
            self.time_edit.setTime(QTime.currentTime())

        layout.addWidget(self.date_edit)
        layout.addWidget(self.time_edit)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)




