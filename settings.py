import sys
import sqlite3
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QLabel,
                             QMessageBox, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt


class Settings(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактирование настроек")
        self.setGeometry(100, 100, 500, 300)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)

        # Группа для полей ввода
        group_box = QGroupBox("Параметры подключения")
        main_layout.addWidget(group_box)

        # Сетка для расположения полей
        grid_layout = QGridLayout()
        group_box.setLayout(grid_layout)

        # Создаем поля ввода
        self.ip_edit = QLineEdit()
        self.database_edit = QLineEdit()
        self.login_edit = QLineEdit()
        self.password_edit = QLineEdit()

        # Для пароля скрываем ввод
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        # Добавляем метки и поля в сетку
        grid_layout.addWidget(QLabel("IP адрес:"), 0, 0)
        grid_layout.addWidget(self.ip_edit, 0, 1)

        grid_layout.addWidget(QLabel("База данных:"), 1, 0)
        grid_layout.addWidget(self.database_edit, 1, 1)

        grid_layout.addWidget(QLabel("Логин:"), 2, 0)
        grid_layout.addWidget(self.login_edit, 2, 1)

        grid_layout.addWidget(QLabel("Пароль:"), 3, 0)
        grid_layout.addWidget(self.password_edit, 3, 1)

        # Кнопки
        button_layout = QHBoxLayout()

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_settings)


        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # Статус бар
        self.status_label = QLabel("Готов к работе")
        main_layout.addWidget(self.status_label)

        # Загружаем настройки при запуске
        self.load_settings()

    def get_db_connection(self):
        """Создает подключение к базе данных"""
        try:
            conn = sqlite3.connect('settings.db')
            return conn
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к БД: {e}")
            return None

    def load_settings(self):
        """Загружает настройки из таблицы nastr"""
        conn = self.get_db_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            # Проверяем существование таблицы

            # Получаем первую запись из таблицы
            cursor.execute("SELECT ip, db, login, password FROM nastr LIMIT 1")
            row = cursor.fetchone()

            if row:
                self.ip_edit.setText(row[0] or "")
                self.database_edit.setText(row[1] or "")
                self.login_edit.setText(row[2] or "")
                self.password_edit.setText(row[3] or "")
                self.status_label.setText("Настройки загружены")
            else:
                QMessageBox.information(self, "Информация",
                                        "В таблице нет записей. Создайте новую запись.")
                self.status_label.setText("Нет записей в таблице")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке: {e}")
        finally:
            conn.close()

    def save_settings(self):
        """Сохраняет изменения в таблицу nastr"""
        conn = self.get_db_connection()
        if not conn:
            return

        # Проверяем заполнение полей
        ip = self.ip_edit.text().strip()
        database = self.database_edit.text().strip()
        login = self.login_edit.text().strip()
        password = self.password_edit.text()

        if not all([ip, database, login]):
            QMessageBox.warning(self, "Предупреждение",
                                "Поля IP, База данных и Логин обязательны для заполнения")
            return

        try:
            cursor = conn.cursor()

            cursor.execute("UPDATE nastr SET ip=?, db=?, login=?, password=?", (ip, database, login, password))
            message = "Настройки обновлены"
            conn.commit()
            QMessageBox.information(self, "Успех", message)
            self.status_label.setText(message)
            #self.close()

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {e}")
        finally:
            conn.close()


def main():
    app = QApplication(sys.argv)
    window = settings()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()