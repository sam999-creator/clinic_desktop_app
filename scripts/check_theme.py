from PySide6.QtWidgets import QApplication
from app.views.main_window import MainWindow
app = QApplication([])
w = MainWindow()
print('has_chk', hasattr(w, 'chk_dark_theme'))
if hasattr(w, 'chk_dark_theme'):
    print('checked', w.chk_dark_theme.isChecked())
    print('text', w.chk_dark_theme.text())
    page = w.pages.widget(4)
    found = any(c is w.chk_dark_theme for c in page.findChildren(type(w.chk_dark_theme)))
    print('in_page', found)
app.quit()
