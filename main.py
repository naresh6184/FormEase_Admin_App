import sys
import pymysql
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QLineEdit, QMenu,
    QComboBox, QCheckBox, QFileDialog, QMessageBox, QDateEdit, QPushButton
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction
from db import connect_db
from openpyxl.styles import Alignment
import subprocess


class DataFetcher(QThread):
    data_loaded = pyqtSignal(list, list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, query, params):
        super().__init__()
        self.query = query
        self.params = params
    
    def run(self):
        connection = connect_db()
        if connection:
            try:
                cursor = connection.cursor(pymysql.cursors.DictCursor)
                cursor.execute(self.query, self.params)
                data = cursor.fetchall()
                headers = list(data[0].keys()) if data else []
                self.data_loaded.emit(data, headers)
                connection.close()
            except pymysql.MySQLError as e:
                self.error_occurred.emit(str(e))


class MainWindow(QWidget):
    
    def __init__(self, homepage_instance):
        super().__init__()
        self.homepage = homepage_instance  # Store the homepage instance
        self.setWindowTitle("FormEase Admin App")
        self.setWindowIcon(QIcon("admin_icon.ico"))
        self.setGeometry(100, 100, 1200, 800)
        self.current_thread = None
        self.last_edited_item = None

        self.init_ui()
        self.load_data()

        # Setup search debounce timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_data)

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Back Button
        back_button_layout = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setIcon(QIcon("back_icon.ico"))  # Optional: Add a back icon
        self.back_button.clicked.connect(self.go_to_homepage)
        back_button_layout.addWidget(self.back_button)
        back_button_layout.addStretch()  # Pushes the button to the left
    
        layout.addLayout(back_button_layout)  # Add the back button layout at the top
    
        filter_layout = QHBoxLayout()
        
        # UG & PG Filter
        self.ug_check = QCheckBox("UG")
        self.pg_check = QCheckBox("PG")
        self.ug_check.stateChanged.connect(self.load_data)
        self.pg_check.stateChanged.connect(self.load_data)
        
        # Add UG & PG filters to the layout
        filter_layout.addWidget(self.ug_check)
        filter_layout.addWidget(self.pg_check)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Application ID, Name, or Roll No")
        self.search_input.textChanged.connect(self.handle_search_changed)

        self.start_date = QDateEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date_check = QCheckBox("Leave Start Date:")
        self.start_date_check.stateChanged.connect(self.load_data)
        self.start_date.dateChanged.connect(self.load_data)

        self.end_date = QDateEdit()
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date_check = QCheckBox("Leave End Date:")
        self.end_date_check.stateChanged.connect(self.load_data)
        self.end_date.dateChanged.connect(self.load_data)
        
        self.dept_combo = QComboBox()
        self.load_departments()
        self.dept_combo.currentIndexChanged.connect(self.load_data)
        
        self.approved_check = QCheckBox("Approved Only")
        self.approved_check.stateChanged.connect(self.load_data)
        
        filter_layout.addWidget(QLabel("Filters:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.start_date_check)
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(self.end_date_check)
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(QLabel("Department:"))
        filter_layout.addWidget(self.dept_combo)
        filter_layout.addWidget(self.approved_check)
        
        layout.addLayout(filter_layout)
        
        self.table = QTableWidget()
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)
        
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export to Excel")
        self.export_btn.clicked.connect(self.export_data)
        export_layout.addWidget(self.export_btn)
        layout.addLayout(export_layout)
        
        self.setLayout(layout)

    def show_context_menu(self, position):
        item = self.table.itemAt(position)
        if item:
            menu = QMenu(self)
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.enable_cell_editing(item))
            menu.addAction(edit_action)
            menu.exec(self.table.viewport().mapToGlobal(position))


    def handle_search_changed(self):
        self.search_timer.stop()
        self.search_timer.start(300)

    def load_departments(self):
        connection = connect_db()
        if connection:
            try:
                cursor = connection.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT DISTINCT department FROM leave_applications")
                self.dept_combo.addItem("All Departments")
                for dept in cursor.fetchall():
                    self.dept_combo.addItem(dept['department'])
                connection.close()
            except pymysql.MySQLError as e:
                QMessageBox.critical(self, "Error", f"Department load failed: {e}")

    def build_query(self):
        query = "SELECT * FROM leave_applications WHERE 1=1"
        params = []

        search_text = self.search_input.text().strip()
        if search_text:
            query += " AND (application_id LIKE %s OR name LIKE %s OR roll_no LIKE %s)"
            params.extend([f"%{search_text}%", f"%{search_text}%", f"%{search_text}%"])

        # Get selected dates
        start_date_selected = self.start_date.date().toString("yyyy-MM-dd")
        end_date_selected = self.end_date.date().toString("yyyy-MM-dd")

        if self.start_date_check.isChecked() and self.end_date_check.isChecked():
            # Apply filter based on the selected interval
            query += " AND ((leave_start_date BETWEEN %s AND %s) AND (leave_end_date BETWEEN %s AND %s))"
            params.extend([start_date_selected, end_date_selected, start_date_selected, end_date_selected])

        elif self.start_date_check.isChecked():
            # Apply filter only for leave start date falling in interval
            query += " AND leave_start_date BETWEEN %s AND %s"
            params.extend([start_date_selected, end_date_selected])

        elif self.end_date_check.isChecked():
            # Apply filter only for leave end date falling in interval
            query += " AND leave_end_date BETWEEN %s AND %s"
            params.extend([start_date_selected, end_date_selected])

        if self.dept_combo.currentText() != "All Departments":
            query += " AND department = %s"
            params.append(self.dept_combo.currentText())

        if self.approved_check.isChecked():
            query += " AND approved = 1"

        if self.ug_check.isChecked() and not self.pg_check.isChecked():
            query += " AND institute_email = 'N/A'"
        elif self.pg_check.isChecked() and not self.ug_check.isChecked():
            query += " AND institute_email != 'N/A'"

        return query, params

    def load_data(self):
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()
        
        query, params = self.build_query()
        self.current_thread = DataFetcher(query, params)
        self.current_thread.data_loaded.connect(self.populate_table)
        self.current_thread.error_occurred.connect(lambda e: QMessageBox.critical(self, "Error", f"Data load failed: {e}"))
        self.current_thread.start()

    def populate_table(self, data, headers):
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        
        try:
            current_headers = [self.table.horizontalHeaderItem(i).text() 
                             for i in range(self.table.columnCount())] if self.table.columnCount() > 0 else []
            
            if headers != current_headers:
                self.table.clear()
                self.table.setColumnCount(len(headers))
                self.table.setHorizontalHeaderLabels(headers)
            
            self.table.setRowCount(len(data))
            
            for row_idx in range(len(data)):
                if row_idx >= self.table.rowCount():
                    self.table.insertRow(row_idx)
                
                for col_idx in range(len(headers)):
                    value = str(data[row_idx].get(headers[col_idx], ''))
                    
                    if self.table.item(row_idx, col_idx):
                        item = self.table.item(row_idx, col_idx)
                        if item.text() != value:
                            item.setText(value)
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    else:
                        item = QTableWidgetItem(value)
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.table.setItem(row_idx, col_idx, item)
            
            while self.table.rowCount() > len(data):
                self.table.removeRow(self.table.rowCount()-1)
                
        finally:
            self.table.setSortingEnabled(True)
            self.table.blockSignals(False)


    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Excel Files (*.xlsx)")
        if path:
            try:
                data = []
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                
                for row in range(self.table.rowCount()):
                    data.append([
                        self.table.item(row, col).text() 
                        for col in range(self.table.columnCount())
                    ])
                
                df = pd.DataFrame(data, columns=headers)
                writer = pd.ExcelWriter(path, engine='openpyxl')
                df.to_excel(writer, index=False)
                
                worksheet = writer.sheets['Sheet1']
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
                    for cell in column:
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                
                writer.close()
                QMessageBox.information(self, "Success", "Data exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def go_to_homepage(self):
        self.hide()  # Hide the admin window instead of closing
        self.homepage.show()  # Show the homepage smoothly

        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())