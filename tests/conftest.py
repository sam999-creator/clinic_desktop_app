import os
import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

# run Qt in offscreen to allow tests in CI/headless
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Prevent blocking modal dialogs during tests (auto-accept/ignore)
@pytest.fixture(autouse=True)
def _no_modal_dialogs(monkeypatch):
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args, **kwargs: None)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Ensure test database and tables exist before tests run; remove after tests."""
    # Use a fresh DB for tests
    from pathlib import Path
    db_path = Path('clinic.db')
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass
    # initialize all model tables
    from app.models import patient, appointment, inventory
    patient.init_db()
    appointment.init_db()
    inventory.init_db()
    yield
    # cleanup DB file after tests
    if db_path.exists():
        try:
            db_path.unlink()
        except Exception:
            pass


@pytest.fixture(scope="module")
def qapp():
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
