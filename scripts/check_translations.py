from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.views.main_window import MainWindow

app = QApplication([])
w = MainWindow()

w.on_language_changed('ar')
print('sidebar_first:', w.sidebar_buttons[0].text())
print('window_title:', w.windowTitle())

w.on_language_changed('en')
print('sidebar_first_en:', w.sidebar_buttons[0].text())

app.quit()
