import sys
import logging
from PySide6.QtWidgets import QApplication
from app.views.main_window import MainWindow
from app.models.patient import init_db

# Reduce noisy SQLAlchemy engine logs (show warnings/errors only)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def main():
    # إنشاء قاعدة البيانات والجداول
    init_db()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())
