import sys
import sqlite3
import psycopg2
from psycopg2 import sql
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QMessageBox, QHeaderView,
                             QDialog, QFormLayout, QLineEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CabinetDialog(QDialog):
    """Диалог для добавления/редактирования записи"""

    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self.record = record
        self.setWindowTitle("Добавление записи" if not record else "Редактирование записи")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Форма ввода
        form_layout = QFormLayout()

        self.number_edit = QLineEdit()
        self.number_edit.setPlaceholderText("Введите номер кабинета")
        form_layout.addRow("Номер:", self.number_edit)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название кабинета")
        form_layout.addRow("Название:", self.name_edit)

        self.otvetstv_edit = QLineEdit()
        self.otvetstv_edit.setPlaceholderText("Введите ответственного")
        form_layout.addRow("Ответственный:", self.otvetstv_edit)

        layout.addLayout(form_layout)

        # Если редактируем, заполняем поля
        if record:
            self.number_edit.setText(record[0])
            self.name_edit.setText(record[1])
            self.otvetstv_edit.setText(record[2])

        # Кнопки
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        """Возвращает введенные данные"""
        return (
            self.number_edit.text().strip(),
            self.name_edit.text().strip(),
            self.otvetstv_edit.text().strip()
        )


class CabinetViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection_params = None
        self.current_id = None  # Для хранения ID текущей записи
        self.init_ui()
        self.load_connection_settings()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Управление кабинетами")
        self.setGeometry(100, 100, 900, 600)

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
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(100)
        top_panel.addWidget(refresh_btn)

        layout.addLayout(top_panel)

        # Таблица для отображения данных
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # Добавляем колонку для ID
        self.table.setHorizontalHeaderLabels(["Номер", "Название", "Ответственный"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        # Настройка растяжения колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Номер
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Ответственный



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
        self.edit_btn.setEnabled(False)  # По умолчанию неактивна
        button_panel.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self.delete_record)
        self.delete_btn.setFixedWidth(120)
        self.delete_btn.setEnabled(False)  # По умолчанию неактивна
        button_panel.addWidget(self.delete_btn)

        layout.addLayout(button_panel)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

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
            self.current_id = (selected_rows[0].row())

    def load_connection_settings(self):
        """Загрузка настроек подключения из settings.db"""
        try:
            # Подключение к SQLite базе с настройками
            conn = sqlite3.connect('settings.db')
            cursor = conn.cursor()

            # Загружаем первую запись
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
            else:
                QMessageBox.warning(self, "Ошибка", "Нет настроек подключения в БД")

            conn.close()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при работе с settings.db: {e}")
            self.info_label.setText("Ошибка загрузки настроек")

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
            cursor.execute("SELECT number, name, otvetstv FROM invent.cabinet ORDER BY number")
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
        dialog = CabinetDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            number, name, otvetstv = dialog.get_data()

            if not number:
                QMessageBox.warning(self, "Предупреждение", "Номер кабинета обязателен для заполнения")
                return

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO invent.cabinet (number, name, otvetstv)
                    VALUES (%s, %s, %s)
                    """, (number, name, otvetstv))

                conn.commit()

                cursor.close()
                conn.close()

                self.load_data()  # Перезагружаем данные
                QMessageBox.information(self, "Успех", f"Запись успешно добавлена ")

            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении записи: {e}")

    def edit_record(self):
        """Редактирование текущей записи"""

        # Получаем текущие данные выделенной записи
        selected_row = self.table.selectedItems()
        if not selected_row:
            return

        row = selected_row[0].row()
        current_data = (
            self.table.item(row, 0).text(),  # number
            self.table.item(row, 1).text(),  # name
            self.table.item(row, 2).text()  # otvetstv
        )

        dialog = CabinetDialog(self, current_data)
        dialog.setWindowTitle("Редактирование записи")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            number, name, otvetstv = dialog.get_data()

            if not number:
                QMessageBox.warning(self, "Предупреждение", "Номер кабинета обязателен для заполнения")
                return

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("UPDATE invent.cabinet SET number = %s, name = %s, otvetstv = %s WHERE number = %s ", (number, name, otvetstv, number))

                conn.commit()

                cursor.close()
                conn.close()

                self.load_data()  # Перезагружаем данные
                QMessageBox.information(self, "Успех", "Запись успешно обновлена")

            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении записи: {e}")

    def delete_record(self):
        """Удаление текущей записи"""
        if not self.current_id:
            QMessageBox.warning(self, "Предупреждение", "Не выбрана запись для удаления")
            return
        selected_row = self.table.selectedItems()
        row = selected_row[0].row()
        # Запрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить запись с номером {self.current_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                cursor.execute("DELETE FROM invent.cabinet WHERE number = %s", ( self.table.item(row, 0).text(),))

                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Предупреждение", "Запись не найдена")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Успех", "Запись успешно удалена")

                cursor.close()
                conn.close()

                self.load_data()  # Перезагружаем данные

            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении записи: {e}")


def main():
    app = QApplication(sys.argv)

    # Установка стиля
    app.setStyle('Fusion')

    window = CabinetViewer()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()