import sys
import pymysql
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLineEdit, QPushButton, QMessageBox, QLabel, QDialog, QHBoxLayout
)
from PyQt6.QtGui import  QFont
from PyQt6.QtCore import Qt
from db import connect_db  # Import database connection
from main import MainWindow  # Importing the database view

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,QMenu
from PyQt6.QtGui import QFont

class HomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FormEase Admin")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Centered layout
        input_layout = QHBoxLayout()
        input_layout.addStretch()

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter Application ID")
        self.search_input.setFixedSize(300, 50)  # Width: 300px, Height: 50px
        self.search_input.setFont(QFont("Arial", 16))  # Bigger font size
        self.search_input.returnPressed.connect(self.fetch_application)  # Fetch on Enter key press
        input_layout.addWidget(self.search_input)
        input_layout.addStretch()

        layout.addLayout(input_layout)

        # Fetch Data Button
        fetch_button_layout = QHBoxLayout()
        fetch_button_layout.addStretch()
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.setFixedSize(200, 40)
        self.fetch_button.setStyleSheet(
            """
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #28a745;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            """
        )
        self.fetch_button.clicked.connect(self.fetch_application)
        fetch_button_layout.addWidget(self.fetch_button)
        fetch_button_layout.addStretch()

        layout.addLayout(fetch_button_layout)

        # Access Database Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.access_db_button = QPushButton("Access Database")
        self.access_db_button.setFixedSize(200, 40)
        self.access_db_button.setStyleSheet(
            """
            QPushButton {
                padding: 10px;
                font-size: 14px;
                background-color: #007BFF;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            """
        )
        self.access_db_button.clicked.connect(self.open_database_view)
        button_layout.addWidget(self.access_db_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def fetch_application(self):
        """Fetch application details based on entered Application ID."""
        app_id = self.search_input.text().strip()
        if not app_id:
            QMessageBox.warning(self, "Input Required", "Please enter an Application ID.")
            return

        connection = connect_db()
        if connection:
            try:
                cursor = connection.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM leave_applications WHERE application_id = %s", (app_id,))
                application_data = cursor.fetchone()
                connection.close()

                if application_data:
                    self.show_application_popup(application_data)
                else:
                    QMessageBox.warning(self, "Not Found", "No application found with this ID.")

            except pymysql.MySQLError as e:
                QMessageBox.critical(self, "Error", f"Database Error: {e}")



    def show_application_popup(self, data):
        dialog = QDialog(self)
        dialog.setWindowTitle("Application Details")
        dialog.setFixedSize(450, 600)
        dialog.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 8px;
            padding: 8px;
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # Approved label if approved is 1
        if data.get("approved") == 1:
            approved_label = QLabel("Approved")
            approved_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            approved_label.setStyleSheet("""
                color: white;
                background-color: green;
                padding: 4px;
                border-radius: 4px;
            """)
            approved_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(approved_label)

        # Store labels for easy reference
        self.detail_labels = {}

        for key, value in data.items():
            detail_layout = QHBoxLayout()
            detail_layout.setContentsMargins(0, 0, 0, 0)
            detail_layout.setSpacing(10)

            label_key = QLabel(f"{key}:")
            label_key.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label_key.setStyleSheet("color: #333; min-width: 120px;")

            label_value = QLabel(str(value))
            label_value.setFont(QFont("Arial", 10))
            label_value.setStyleSheet("color: #555;")
            label_value.setWordWrap(True)

            detail_layout.addWidget(label_key)
            detail_layout.addWidget(label_value)
            layout.addLayout(detail_layout)

            self.detail_labels[key] = label_value  # Store label reference

        # Buttons Layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        approve_button = QPushButton("Approve")
        not_approve_button = QPushButton("Not Approve")

        button_style = """
            padding: 6px;
            font-size: 12px;
            border-radius: 4px;
        """
        approve_button.setStyleSheet(button_style + "background-color: #28a745; color: white;")
        not_approve_button.setStyleSheet(button_style + "background-color: #dc3545; color: white;")

        approve_button.clicked.connect(lambda: self.update_approval_status(data["application_id"], 1, dialog))
        not_approve_button.clicked.connect(lambda: self.update_approval_status(data["application_id"], 0, dialog))

        button_layout.addWidget(approve_button)
        button_layout.addWidget(not_approve_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # ✅ Add right-click menu
        dialog.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        dialog.customContextMenuRequested.connect(lambda pos: self.contextMenuEvent(pos, dialog, data))

        dialog.move(self.mapToGlobal(self.rect().center()) - dialog.rect().center())
        dialog.exec()

    def contextMenuEvent(self, pos, dialog, data):
        """Right-click menu inside the application details popup."""
        menu = QMenu(dialog)

        menu.setStyleSheet("""
            QMenu {
                background-color: #333;  /* Dark background */
                color: white;  /* White text */
                border: 1px solid #555;  /* Visible border */
            }
            QMenu::item {
                padding: 6px 12px;
            }
            QMenu::item:selected {
                background-color: #555;  /* Slightly lighter selection */
            }
        """)

        edit_action = menu.addAction("✏ Edit Application")  
        action = menu.exec(dialog.mapToGlobal(pos))  

        if action == edit_action:
            self.show_edit_popup(data, dialog)



    def show_edit_popup(self, data, parent_dialog):
        """Opens a new popup to edit application details."""
        edit_dialog = QDialog(self)
        edit_dialog.setWindowTitle("Edit Application")
        edit_dialog.setFixedSize(450, 600)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        self.edit_fields = {}  # Store input fields

        for key, value in data.items():
            if key == "application_id":  # Keep application ID read-only
                continue

            field_layout = QHBoxLayout()
            field_layout.setSpacing(10)

            label_key = QLabel(f"{key}:")
            label_key.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            label_key.setStyleSheet("color: #333; min-width: 120px;")

            edit_field = QLineEdit(str(value))
            edit_field.setFont(QFont("Arial", 10))
            edit_field.setStyleSheet("color: #555; background-color: white; border: 1px solid #ccc; border-radius: 4px; padding: 4px;")

            field_layout.addWidget(label_key)
            field_layout.addWidget(edit_field)
            layout.addLayout(field_layout)

            self.edit_fields[key] = edit_field  # Store input field reference

        save_button = QPushButton("Save Changes")
        save_button.setStyleSheet("padding: 6px; font-size: 12px; border-radius: 4px; background-color: #17a2b8; color: white;")
        save_button.clicked.connect(lambda: self.save_edited_data(data["application_id"], edit_dialog, parent_dialog))

        layout.addWidget(save_button)
        edit_dialog.setLayout(layout)
        edit_dialog.move(self.mapToGlobal(self.rect().center()) - edit_dialog.rect().center())
        edit_dialog.exec()

    def save_edited_data(self, app_id, edit_dialog, parent_dialog):
        """Save edited data to the database."""
        updated_data = {key: field.text() for key, field in self.edit_fields.items()}

        connection = connect_db()
        if connection:
            try:
                cursor = connection.cursor()
                query = "UPDATE leave_applications SET " + ", ".join([f"{key} = %s" for key in updated_data.keys()]) + " WHERE application_id = %s"
                values = list(updated_data.values()) + [app_id]

                cursor.execute(query, values)
                connection.commit()
                connection.close()

                QMessageBox.information(self, "Success", "Application details updated!")
                edit_dialog.close()
                parent_dialog.close()  # Close the main popup to refresh it

            except pymysql.MySQLError as e:
                QMessageBox.critical(self, "Error", f"Update failed: {e}")


    def open_database_view(self):
        self.database_window = MainWindow(self)  # Pass the HomePage instance
        self.database_window.show()


    def update_approval_status(self, app_id, status, dialog):
        """Update the approval status in the database."""
        connection = connect_db()
        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute("UPDATE leave_applications SET approved = %s WHERE application_id = %s", (status, app_id))
                connection.commit()
                connection.close()
                QMessageBox.information(self, "Success", "Application status updated!")
                dialog.close()

            except pymysql.MySQLError as e:
                QMessageBox.critical(self, "Error", f"Update failed: {e}")
                
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HomePage()
    window.show()
    sys.exit(app.exec())