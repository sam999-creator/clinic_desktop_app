from PySide6.QtWidgets import QApplication
from app.views.main_window import MainWindow
app = QApplication([])
w = MainWindow()
print('sidebar_buttons:', [b.text() for b in w.sidebar_buttons])
print('toggle_exists:', hasattr(w, 'toggle_theme'), 'checked:', getattr(w, 'toggle_theme', None) and w.toggle_theme.isChecked())
print('lang_saved:', w.get_saved_language())
app.quit()
