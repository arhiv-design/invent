import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu,
                             QVBoxLayout, QWidget, QLabel)
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import Qt

from cabinetViewer import CabinetViewer
from settings import Settings
from computersViewer import ComputersViewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Настройка главного окна
        self.room = None
        self.sett = None
        self.computers = None

        self.setWindowTitle("Главное окно приложения")
        self.setGeometry(100, 100, 800, 600)  # x, y, width, height

        # Установка иконки для окна
        # Замените 'icon.png' на путь к вашему файлу иконки
        self.setWindowIcon(QIcon('icon/computer.png'))  # Поддерживает .ico, .png, .jpg и др.

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Добавляем информационную метку в центр окна
        layout = QVBoxLayout(central_widget)
        label = QLabel("Добро пожаловать в приложение!\n инвентаризация ОНТ")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; color: #333;")
        layout.addWidget(label)

        # Создание строки меню
        menubar = self.menuBar()

        # 1. Меню "Компьютеры"
        computers_menu = QAction("Компьютеры",self)
        computers_menu.triggered.connect(self.show_computers_list)
        menubar.addAction(computers_menu)

        # 2. Меню "Кабинеты"
        rooms_action = QAction("Кабинеты", self)
        rooms_action.triggered.connect(self.rooms_list)
        menubar.addAction(rooms_action)

        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.show_nasty)
        menubar.addAction(settings_action)

        # 4. Меню "Об авторе"
        about_menu = menubar.addMenu("Об авторе")
        about_menu.triggered.connect(self.show_about_info)

        # Добавляем дополнительно меню "Справка" (опционально)
        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("Справка", self.show_help)
        help_menu.addAction("О программе", self.show_about)

        # Статус бар
        self.statusBar().showMessage("Готов к работе")

    # Слоты для обработки действий меню
    def show_computers_list(self):
       self.computers = ComputersViewer()
       self.computers.show()
    def rooms_list(self):
        self.room = CabinetViewer()
        self.room.show()



    def show_about_info(self):
        self.statusBar().showMessage("Информация об авторе")
        print("Выбрано: Об авторе -> Информация")

    def show_nasty(self):
        self.sett = Settings()
        self.sett.show()
        print("Выбрано: Справка -> О программе")

    def show_help(self):
        self.statusBar().showMessage("Справка")
        print("Выбрано: Справка -> Справка")

    def show_about(self):
        self.statusBar().showMessage("О программе")
        print("Выбрано: Справка -> О программе")


def main():
    # Создание приложения
    app = QApplication(sys.argv)

    # Создание и отображение главного окна
    window = MainWindow()
    window.show()

    # Запуск основного цикла приложения
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
