import sys
import sqlite3
import psycopg2
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QMessageBox, QHeaderView,
                             QDateEdit, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QComboBox)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont


class ComputerDialog(QDialog):
    """Диалог для добавления/редактирования компьютера"""

    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle("Добавление компьютера" if not record else "Редактирование компьютера")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Форма ввода
        form_layout = QFormLayout()

        # Название компьютера
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название компьютера")
        form_layout.addRow("Название:*", self.name_edit)

        # Инвентарный номер
        self.inventory_edit = QLineEdit()
        self.inventory_edit.setPlaceholderText("Введите инвентарный номер")
        form_layout.addRow("Инв. номер:", self.inventory_edit)

        # Производитель
        self.manufacturer_edit = QLineEdit()
        self.manufacturer_edit.setPlaceholderText("Введите производителя")
        form_layout.addRow("Производитель:", self.manufacturer_edit)

        # Модель
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Введите модель")
        form_layout.addRow("Модель:", self.model_edit)

        # Дата покупки
        self.purchase_date_edit = QDateEdit()
        self.purchase_date_edit.setCalendarPopup(True)
        self.purchase_date_edit.setDate(QDate.currentDate())
        self.purchase_date_edit.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата покупки:", self.purchase_date_edit)

        layout.addLayout(form_layout)

        # Если редактируем, заполняем поля
        if record:
            self.name_edit.setText(record[1])  # name
            self.inventory_edit.setText(record[2] if record[2] else "")  # inventory_number
            self.manufacturer_edit.setText(record[3] if record[3] else "")  # manufacturer
            self.model_edit.setText(record[4] if record[4] else "")  # model

            # Дата покупки
            if record[5]:  # purchase_date
                date_parts = record[5].split('-')
                if len(date_parts) == 3:
                    date = QDate(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
                    self.purchase_date_edit.setDate(date)

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        """Проверка данных перед принятием"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Название компьютера обязательно для заполнения")
            return
        self.accept()

    def get_data(self):
        """Возвращает введенные данные"""
        purchase_date = self.purchase_date_edit.date().toString("yyyy-MM-dd")

        return (
            self.name_edit.text().strip(),
            self.inventory_edit.text().strip() or None,
            self.manufacturer_edit.text().strip() or None,
            self.model_edit.text().strip() or None,
            purchase_date
        )


class ComputersViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection_params = None
        self.current_id = None
        self.init_ui()
        self.load_connection_settings()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Управление компьютерами")
        self.setGeometry(100, 100, 1000, 600)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout(central_widget)

        # Верхняя панель с информацией
        top_panel = QHBoxLayout()

        self.info_label = QLabel("Загрузка данных...")
        self.info_label.setFont(QFont("Arial", 10))
        top_panel.addWidget(self.info_label)

        top_panel.addStretch()

        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(100)
        top_panel.addWidget(refresh_btn)

        layout.addLayout(top_panel)

        # Таблица для отображения данных
        self.table = QTableWidget()
        self.table.setColumnCount(7)  # id + 6 полей
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Инв. номер", "Производитель",
            "Модель", "Дата покупки", "Возраст (лет)"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        # Настройка растяжения колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Инв. номер
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Производитель
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Модель
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Дата покупки
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Возраст

        # Скрываем колонку с ID
        self.table.setColumnHidden(0, True)

        layout.addWidget(self.table)

        # Панель кнопок управления
        button_panel = QHBoxLayout()
        button_panel.addStretch()

        # Кнопки
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.clicked.connect(self.add_record)
        self.add_btn.setFixedWidth(120)
        button_panel.addWidget(self.add_btn)

        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.clicked.connect(self.edit_record)
        self.edit_btn.setFixedWidth(120)
        self.edit_btn.setEnabled(False)
        button_panel.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self.delete_record)
        self.delete_btn.setFixedWidth(120)
        self.delete_btn.setEnabled(False)
        button_panel.addWidget(self.delete_btn)

        layout.addLayout(button_panel)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    def calculate_age(self, purchase_date):
        """Расчет возраста компьютера в годах"""
        if not purchase_date:
            return ""

        try:
            if isinstance(purchase_date, str):
                purchase_date = datetime.strptime(purchase_date, '%Y-%m-%d').date()

            today = datetime.now().date()
            age = today.year - purchase_date.year

            # Проверяем, был ли уже день рождения в этом году
            if today.month < purchase_date.month or (
                    today.month == purchase_date.month and today.day < purchase_date.day):
                age -= 1

            return str(age)
        except:
            return ""

    def on_selection_changed(self):
        """Обработчик изменения выделения в таблице"""
        selected_rows = self.table.selectedItems()
        has_selection = len(selected_rows) > 0

        # Активируем кнопки если есть выделение
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)

        if has_selection:
            # Получаем ID из первой колонки выделенной строки
            row = selected_rows[0].row()
            id_item = self.table.item(row, 0)
            if id_item:
                self.current_id = int(id_item.text())
                self.statusBar().showMessage(f"Выбран компьютер ID: {self.current_id}")

    def load_connection_settings(self):
        """Загрузка настроек подключения из settings.db"""

        # Подключение к SQLite базе с настройками
        conn = sqlite3.connect('settings.db')
        cursor = conn.cursor()

        cursor.execute("SELECT ip, db, login, password FROM nastr LIMIT 1")
        row = cursor.fetchone()

        if row:
                self.connection_params = {
                    'host': row[0],
                    'database': row[1],
                    'user': row[2],
                    'password': row[3]
                }
        self.info_label.setText(f"Подключение к: {row[0]}/{row[1]}")
        self.load_data()
        conn.close()



    def load_data(self):
        """Загрузка данных из PostgreSQL"""
        if not self.connection_params:
            QMessageBox.warning(self, "Ошибка", "Нет параметров подключения")
            return

        try:
            # Подключение к PostgreSQL
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()
            # Получаем данные
            cursor.execute("""
                SELECT id, name, inventory_number, manufacturer, model, purchase_date 
                FROM invent.computers 
                ORDER BY id
            """)
            rows = cursor.fetchall()

            # Заполняем таблицу
            self.table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value else "")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                    # Для колонки с ID устанавливаем флаг, чтобы нельзя было редактировать
                    if j == 0:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                    self.table.setItem(i, j, item)

                # Добавляем колонку с возрастом компьютера
                age = self.calculate_age(row[5])
                age_item = QTableWidgetItem(age)
                age_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, 6, age_item)

            self.info_label.setText(f"Загружено записей: {len(rows)}")
            self.statusBar().showMessage(f"Данные обновлены: {len(rows)} записей")

            # Сбрасываем выделение
            self.table.clearSelection()
            self.current_id = None
            self.edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при работе с PostgreSQL: {e}")
            self.info_label.setText("Ошибка загрузки данных")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Неизвестная ошибка: {e}")

    def add_record(self):
        """Добавление новой записи"""
        dialog = ComputerDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, inventory, manufacturer, model, purchase_date = dialog.get_data()

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO invent.computers 
                    (name, inventory_number, manufacturer, model, purchase_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, inventory, manufacturer, model, purchase_date))

                new_id = cursor.fetchone()[0]
                conn.commit()

                cursor.close()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Успех", f"Компьютер успешно добавлен (ID: {new_id})")

            except psycopg2.IntegrityError as e:
                if "unique constraint" in str(e).lower():
                    QMessageBox.critical(self, "Ошибка", "Компьютер с таким инвентарным номером уже существует")
                else:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении записи: {e}")
            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении записи: {e}")

    def edit_record(self):
        """Редактирование текущей записи"""
        if not self.current_id:
            QMessageBox.warning(self, "Предупреждение", "Не выбран компьютер для редактирования")
            return

        # Получаем текущие данные выделенной записи
        selected_row = self.table.selectedItems()
        if not selected_row:
            return

        row = selected_row[0].row()
        current_data = (
            self.current_id,
            self.table.item(row, 1).text(),  # name
            self.table.item(row, 2).text() if self.table.item(row, 2).text() != "" else None,  # inventory_number
            self.table.item(row, 3).text() if self.table.item(row, 3).text() != "" else None,  # manufacturer
            self.table.item(row, 4).text() if self.table.item(row, 4).text() != "" else None,  # model
            self.table.item(row, 5).text() if self.table.item(row, 5).text() != "" else None  # purchase_date
        )

        dialog = ComputerDialog(self, current_data)
        dialog.setWindowTitle("Редактирование компьютера")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, inventory, manufacturer, model, purchase_date = dialog.get_data()

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("""
                    UPDATE invent.computers
                    SET name = %s, inventory_number = %s, manufacturer = %s, 
                        model = %s, purchase_date = %s
                    WHERE id = %s
                """, (name, inventory, manufacturer, model, purchase_date, self.current_id))

                conn.commit()

                cursor.close()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Успех", "Компьютер успешно обновлен")

            except psycopg2.IntegrityError as e:
                if "unique constraint" in str(e).lower():
                    QMessageBox.critical(self, "Ошибка", "Компьютер с таким инвентарным номером уже существует")
                else:
                    QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении записи: {e}")
            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении записи: {e}")

    def delete_record(self):
        """Удаление текущей записи"""
        if not self.current_id:
            QMessageBox.warning(self, "Предупреждение", "Не выбран компьютер для удаления")
            return

        # Получаем название компьютера для подтверждения
        selected_row = self.table.selectedItems()
        computer_name = selected_row[1].text() if selected_row else f"ID {self.current_id}"

        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить компьютер '{computer_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("DELETE FROM invent.computers WHERE id = %s", (self.current_id,))

                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Предупреждение", "Компьютер не найден")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Успех", "Компьютер успешно удален")

                cursor.close()
                conn.close()

                self.load_data()

            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении компьютера: {e}")


def main():
    app = QApplication(sys.argv)

    # Установка стиля
    app.setStyle('Fusion')

    window = ComputersViewer()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()