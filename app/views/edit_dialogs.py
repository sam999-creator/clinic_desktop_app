from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox

class PatientEditDialog(QDialog):
    def __init__(self, patient, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Patient")
        self.patient = patient

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.input_name = QLineEdit(patient.name)
        self.input_age = QLineEdit(str(patient.age))
        self.input_condition = QLineEdit(patient.condition)

        form.addRow("Name:", self.input_name)
        form.addRow("Age:", self.input_age)
        form.addRow("Condition:", self.input_condition)
        layout.addLayout(form)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def get_data(self):
        # validate age before returning
        try:
            age_val = int(self.input_age.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Age", "Please enter a valid integer age")
            raise
        return {
            "name": self.input_name.text(),
            "age": age_val,
            "condition": self.input_condition.text()
        }