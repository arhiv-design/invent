import sys
import sqlite3
import psycopg2
from psycopg2 import sql
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QMessageBox, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CabinetViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.connection_params = None
        self.init_ui()
        self.load_connection_settings()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setWindowTitle("Просмотр кабинетов")
        self.setGeometry(100, 100, 800, 600)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout(central_widget)

        # Верхняя панель с информацией и кнопками
        top_panel = QHBoxLayout()

        self.info_label = QLabel("Загрузка данных...")
        self.info_label.setFont(QFont("Arial", 10))
        top_panel.addWidget(self.info_label)

        top_panel.addStretch()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        top_panel.addWidget(refresh_btn)

        layout.addLayout(top_panel)

        # Таблица для отображения данных
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Номер", "Название", "Ответственный"])

        # Настройка растяжения колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.table)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    def load_connection_settings(self):
        """Загрузка настроек подключения из settings.db"""
        try:
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
                    self.table.setItem(i, j, item)

            self.info_label.setText(f"Загружено записей: {len(rows)}")
            self.statusBar().showMessage(f"Данные обновлены: {len(rows)} записей")

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при работе с PostgreSQL: {e}")
            self.info_label.setText("Ошибка загрузки данных")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Неизвестная ошибка: {e}")


def main():
    app = QApplication(sys.argv)

    # Установка стиля
    app.setStyle('Fusion')

    window = CabinetViewer()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()