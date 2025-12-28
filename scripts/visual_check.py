import os
import sys
import time
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from app.views.main_window import MainWindow

# Reduce noisy SQLAlchemy engine logs for visual check
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'artifacts', 'screenshots')
os.makedirs(out_dir, exist_ok=True)

app = QApplication(sys.argv)
win = None

# small helper to process events and sleep
def wait(ms=300):
    t0 = time.time()
    end = t0 + ms/1000.0
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)

try:
    win = MainWindow()
    win.show()

    # initial
    wait(400)
    win.repaint()
    app.processEvents()
    img = win.grab()
    img.save(os.path.join(out_dir, 'initial.png'))
    print('Saved initial.png')

    # Light theme
    win.apply_theme('light')
    wait(400)
    win.repaint()
    app.processEvents()
    img = win.grab()
    img.save(os.path.join(out_dir, 'light.png'))
    print('Saved light.png')

    # Dark theme
    win.apply_theme('dark')
    wait(400)
    win.repaint()
    app.processEvents()
    img = win.grab()
    img.save(os.path.join(out_dir, 'dark.png'))
    print('Saved dark.png')

    # Arabic
    win.on_language_changed('ar')
    wait(400)
    win.repaint()
    app.processEvents()
    img = win.grab()
    img.save(os.path.join(out_dir, 'arabic.png'))
    print('Saved arabic.png')

    # Capture charts individually if present
    try:
        if hasattr(win, 'patient_chart_view') and win.patient_chart_view:
            cimg = win.patient_chart_view.grab()
            cimg.save(os.path.join(out_dir, 'patients_chart.png'))
            print('Saved patients_chart.png')
        if hasattr(win, 'appointments_chart_view') and win.appointments_chart_view:
            cimg = win.appointments_chart_view.grab()
            cimg.save(os.path.join(out_dir, 'appointments_chart.png'))
            print('Saved appointments_chart.png')
    except Exception as e:
        print('chart capture error', e)

except KeyboardInterrupt:
    print('Visual check interrupted by user')
except Exception as e:
    print('Visual check failed:', e)
finally:
    if win is not None:
        try:
            win.close()
        except Exception:
            pass
    try:
        app.quit()
    except Exception:
        pass
    print('Done')
