from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.views.main_window import MainWindow

app = QApplication([])
w = MainWindow()

results = []

# Theme checks
initial_theme = w.get_saved_theme()
results.append(f"initial_theme={initial_theme}")
try:
    w.apply_theme('light')
    results.append("apply_theme_light=ok")
except Exception as e:
    results.append(f"apply_theme_light=error:{e}")

if hasattr(w, 'toggle_theme'):
    results.append(f"toggle_exists=True, checked={w.toggle_theme.isChecked()}")
else:
    results.append("toggle_exists=False")

w.on_theme_toggled(True)
results.append(f"theme_after_toggle_true={w.get_saved_theme()}")
w.on_theme_toggled(False)
results.append(f"theme_after_toggle_false={w.get_saved_theme()}")

# Language / RTL checks
w.on_language_changed('ar')
results.append(f"layoutDirection_is_RTL={w.layoutDirection()==Qt.RightToLeft}")
font_notice_vis = hasattr(w, 'lbl_font_notice') and w.lbl_font_notice.isVisible()
results.append(f"font_notice_visible={font_notice_vis}")

# Sidebar checks
sidebar_ok = hasattr(w, 'sidebar_buttons') and len(w.sidebar_buttons) >= 5
results.append(f"sidebar_ok={sidebar_ok}")
if sidebar_ok:
    w.pages.setCurrentIndex(2)
    # call internal handler
    try:
        w._on_page_changed(2)
        results.append(f"page_changed_ok, button2_checked={w.sidebar_buttons[2].isChecked()}")
    except Exception as e:
        results.append(f"page_changed_error={e}")
    # check icon tint (sample center pixel)
    try:
        btn = w.sidebar_buttons[0]
        pm = btn.icon().pixmap(btn.iconSize())
        img = pm.toImage()
        found = None
        for x in range(img.width()):
            for y in range(img.height()):
                c = img.pixelColor(x, y)
                if c.alpha() != 0:
                    found = c
                    break
            if found:
                break
        if found:
            results.append(f"icon_sample_color={found.name()}")
        else:
            results.append("icon_sample_color=transparent")
    except Exception as e:
        results.append(f"icon_color_error={e}")

# Calendar & scheduling checks
try:
    calendar_exists = hasattr(w, 'calendar_widget')
    results.append(f"calendar_exists={calendar_exists}")
    if calendar_exists:
        # set inputs and add an appointment for today
        w.input_appt_patient.setText('Test Patient')
        w.input_appt_doctor.setText('Dr. Test')
        # ensure date fields are set
        w.input_appt_date.setDate(w.calendar_widget.selectedDate())
        w.input_appt_time.setTime(w.input_appt_time.time())
        w.input_appt_duration.setValue(45)
        w.add_appointment()
        # reload and verify one matching appointment exists for today
        w.load_appointments_for_date(w.calendar_widget.selectedDate())
        # check table count > 0
        count = w.table_appointments.rowCount()
        results.append(f"appt_added_table_rows={count}")
except Exception as e:
    results.append(f"calendar_error={e}")

# Charts
try:
    pc = w.create_patient_chart()
    ac = w.create_appointments_chart()
    results.append(f"patient_chart_type={type(pc).__name__}")
    results.append(f"appointments_chart_type={type(ac).__name__}")
except Exception as e:
    results.append(f"charts_error={e}")

# Translation checks (Arabic mapping / .po fallback)
try:
    w.on_language_changed('ar')
    results.append(f"sidebar_first_label={w.sidebar_buttons[0].text()}")
    # expect Arabic label for Dashboard
    results.append(f"sidebar_first_is_ar={w.sidebar_buttons[0].text() == 'لوحة التحكم'}")
except Exception as e:
    results.append(f"translation_error={e}")

# Mono icons presence & recolor
try:
    mono_exists = True
    for fname in ['dashboard_mono.svg','patients_mono.svg','appointments_mono.svg','inventory_mono.svg','settings_mono.svg']:
        import os
        if not os.path.exists(os.path.join('app','resources','icons',fname)):
            mono_exists = False
    results.append(f"mono_icons_exist={mono_exists}")
    if mono_exists:
        w.apply_theme('dark')
        btn = w.sidebar_buttons[0]
        pix = btn.icon().pixmap(btn.iconSize())
        results.append(f"first_icon_pixmap_null={pix.isNull()}")
except Exception as e:
    results.append(f"icons_error={e}")

# Summary
print('\n'.join(results))

app.quit()
