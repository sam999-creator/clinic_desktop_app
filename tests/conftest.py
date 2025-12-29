import os
# run Qt in offscreen to allow tests in CI/headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
# PySide6 may not be available on minimal CI images (missing system libs). Import safely and provide
# lightweight fallbacks so tests can skip GUI behavior instead of failing on import error.
try:
    from PySide6.QtWidgets import QApplication, QMessageBox
except Exception:
    QApplication = None
    class QMessageBox:
        Yes = 1
        @staticmethod
        def question(*args, **kwargs):
            return QMessageBox.Yes
        @staticmethod
        def warning(*args, **kwargs):
            return None
        @staticmethod
        def critical(*args, **kwargs):
            return None

# Prevent blocking modal dialogs during tests (auto-accept/ignore)
@pytest.fixture(autouse=True)
def _no_modal_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args, **kwargs: None)

@pytest.fixture(scope="module")
def qapp():
    if QApplication is None:
        pytest.skip("PySide6 not available in this environment")
    # Use existing QApplication if present (helps running tests programmatically in same process)
    app = QApplication.instance()
    created = False
    if app is None:
        app = QApplication([])
        created = True
    yield app
    if created:
        app.quit()
        del app
