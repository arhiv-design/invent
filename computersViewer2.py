import sys
import sqlite3
import psycopg2
import platform
import subprocess
import os
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QMessageBox, QHeaderView,
                             QDateEdit, QDialog, QFormLayout, QLineEdit,
                             QDialogButtonBox, QComboBox, QSplitter, QGroupBox,
                             QAbstractItemView, QProgressDialog, QCheckBox)
from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor


class SystemSpecsLoaderThread(QThread):
    """Поток для загрузки системных характеристик"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self):
        super().__init__()

    def get_windows_product_key(self):
        """Получение ключа продукта Windows"""
        try:
            if platform.system() == "Windows":
                # Попытка получить ключ из реестра
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                try:
                    product_key = winreg.QueryValueEx(key, "DigitalProductId")[0]
                    # Здесь нужна дополнительная обработка для декодирования ключа
                    # Для простоты вернем заглушку
                    return "XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
                except:
                    pass
                finally:
                    winreg.CloseKey(key)
        except:
            pass
        return "Не удалось получить ключ"

    def get_processor_info(self):
        """Получение информации о процессоре"""
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                for processor in c.Win32_Processor():
                    return f"{processor.Name} ({processor.NumberOfCores} ядер, {processor.MaxClockSpeed} МГц)"
            elif platform.system() == "Linux":
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
        except:
            pass

        # Запасной вариант
        return f"{platform.processor()}"

    def get_ram_info(self):
        """Получение информации об оперативной памяти"""
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                total_ram = 0
                for memory in c.Win32_PhysicalMemory():
                    total_ram += int(memory.Capacity)
                return f"{total_ram // (1024 ** 3)} GB"
            elif platform.system() == "Linux":
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if 'MemTotal' in line:
                            mem_kb = int(line.split()[1])
                            return f"{mem_kb // (1024 ** 2)} GB"
        except:
            pass

        # Запасной вариант с использованием psutil
        try:
            import psutil
            return f"{psutil.virtual_memory().total // (1024 ** 3)} GB"
        except:
            pass

        return "Не удалось определить"

    def get_disk_info(self):
        """Получение информации о жестких дисках"""
        disks = []
        try:
            if platform.system() == "Windows":
                import wmi
                c = wmi.WMI()
                for disk in c.Win32_DiskDrive():
                    size_gb = int(disk.Size) // (1024 ** 3) if disk.Size else 0
                    disks.append(f"{disk.Model} ({size_gb} GB)")
            elif platform.system() == "Linux":
                import psutil
                for partition in psutil.disk_partitions():
                    if partition.fstype:
                        usage = psutil.disk_usage(partition.mountpoint)
                        size_gb = usage.total // (1024 ** 3)
                        disks.append(f"{partition.device} ({size_gb} GB)")
        except:
            pass

        return ", ".join(disks) if disks else "Не удалось определить"

    def get_os_info(self):
        """Получение информации об операционной системе"""
        os_info = platform.system()
        os_version = platform.version()
        os_release = platform.release()

        if os_info == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                     r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                try:
                    product_name = winreg.QueryValueEx(key, "ProductName")[0]
                    return f"{product_name} (Версия {os_release})"
                except:
                    pass
                finally:
                    winreg.CloseKey(key)
            except:
                pass

        return f"{os_info} {os_release}"

    def run(self):
        try:
            specs = {}

            # Процессор
            self.progress.emit(10)
            specs['Процессор'] = self.get_processor_info()

            # Оперативная память
            self.progress.emit(30)
            specs['Оперативная память'] = self.get_ram_info()

            # Жесткий диск
            self.progress.emit(50)
            specs['Жесткий диск'] = self.get_disk_info()

            # Операционная система
            self.progress.emit(70)
            specs['Операционная система'] = self.get_os_info()

            # Ключ Windows (только для Windows)
            self.progress.emit(90)
            if platform.system() == "Windows":
                specs['Ключ Windows'] = self.get_windows_product_key()

            self.progress.emit(100)
            self.finished.emit(specs)

        except Exception as e:
            self.error.emit(str(e))


class ComputerSpecsLoaderThread(QThread):
    """Поток для загрузки характеристик компьютера из БД"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, connection_params, computer_id):
        super().__init__()
        self.connection_params = connection_params
        self.computer_id = computer_id

    def run(self):
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()

            # Получаем характеристики текущего компьютера
            cursor.execute("""
                SELECT spec_name, value FROM invent.computer_specs
                WHERE computer_id = %s
                ORDER BY spec_name
            """, (self.computer_id,))

            specs = cursor.fetchall()
            cursor.close()
            conn.close()

            self.finished.emit(specs)

        except Exception as e:
            self.error.emit(str(e))


class SpecificationsDialog(QDialog):
    """Диалог для добавления/редактирования характеристики"""

    def __init__(self, parent=None, spec=None):
        super().__init__(parent)
        self.spec = spec
        self.setWindowTitle("Добавление характеристики" if not spec else "Редактирование характеристики")
        self.setModal(True)
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Форма ввода
        form_layout = QFormLayout()

        # Название характеристики
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: Процессор, ОЗУ, Видеокарта...")
        form_layout.addRow("Название:*", self.name_edit)

        # Значение характеристики
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Например: Intel i7, 16GB, GTX 1060...")
        form_layout.addRow("Значение:*", self.value_edit)

        layout.addLayout(form_layout)

        # Если редактируем, заполняем поля
        if spec:
            self.name_edit.setText(spec[0])
            self.value_edit.setText(spec[1])

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
            QMessageBox.warning(self, "Предупреждение", "Название характеристики обязательно для заполнения")
            return
        if not self.value_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Значение характеристики обязательно для заполнения")
            return
        self.accept()

    def get_data(self):
        """Возвращает введенные данные"""
        return (
            self.name_edit.text().strip(),
            self.value_edit.text().strip()
        )


class ComputerDialog(QDialog):
    """Диалог для добавления/редактирования компьютера с характеристиками"""

    def __init__(self, parent=None, record=None, specs=None, connection_params=None):
        super().__init__(parent)
        self.record = record
        self.specs = specs or []
        self.connection_params = connection_params
        self.current_spec_id = None
        self.computer_id = record[0] if record else None

        self.setWindowTitle("Добавление компьютера" if not record else "Редактирование компьютера")
        self.setModal(True)
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)

        # Основной layout
        layout = QVBoxLayout(self)

        # Создаем разделитель для двух частей
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Верхняя часть - основная информация о компьютере
        computer_widget = QWidget()
        computer_layout = QVBoxLayout(computer_widget)
        computer_layout.setContentsMargins(0, 0, 0, 0)

        # Группа с основной информацией
        info_group = QGroupBox("Основная информация")
        info_layout = QFormLayout(info_group)

        # Название компьютера
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название компьютера")
        info_layout.addRow("Название:*", self.name_edit)

        # Инвентарный номер
        self.inventory_edit = QLineEdit()
        self.inventory_edit.setPlaceholderText("Введите инвентарный номер")
        info_layout.addRow("Инв. номер:", self.inventory_edit)

        # Производитель
        self.manufacturer_edit = QLineEdit()
        self.manufacturer_edit.setPlaceholderText("Введите производителя")
        info_layout.addRow("Производитель:", self.manufacturer_edit)

        # Модель
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Введите модель")
        info_layout.addRow("Модель:", self.model_edit)

        # Дата покупки
        self.purchase_date_edit = QDateEdit()
        self.purchase_date_edit.setCalendarPopup(True)
        self.purchase_date_edit.setDate(QDate.currentDate())
        self.purchase_date_edit.setDisplayFormat("dd.MM.yyyy")
        info_layout.addRow("Дата покупки:", self.purchase_date_edit)

        computer_layout.addWidget(info_group)

        # Нижняя часть - характеристики компьютера
        specs_widget = QWidget()
        specs_layout = QVBoxLayout(specs_widget)
        specs_layout.setContentsMargins(0, 0, 0, 0)

        # Группа с характеристиками
        specs_group = QGroupBox("Характеристики компьютера")
        specs_group_layout = QVBoxLayout(specs_group)

        # Таблица характеристик
        self.specs_table = QTableWidget()
        self.specs_table.setColumnCount(2)
        self.specs_table.setHorizontalHeaderLabels(["Характеристика", "Значение"])
        self.specs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.specs_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.specs_table.itemSelectionChanged.connect(self.on_spec_selection_changed)

        # Настройка растяжения колонок
        header = self.specs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        specs_group_layout.addWidget(self.specs_table)

        # Кнопки управления характеристиками
        specs_buttons_layout = QHBoxLayout()

        self.add_spec_btn = QPushButton("➕ Добавить")
        self.add_spec_btn.clicked.connect(self.add_specification)
        specs_buttons_layout.addWidget(self.add_spec_btn)

        self.edit_spec_btn = QPushButton("✏️ Редактировать")
        self.edit_spec_btn.clicked.connect(self.edit_specification)
        self.edit_spec_btn.setEnabled(False)
        specs_buttons_layout.addWidget(self.edit_spec_btn)

        self.delete_spec_btn = QPushButton("🗑️ Удалить")
        self.delete_spec_btn.clicked.connect(self.delete_specification)
        self.delete_spec_btn.setEnabled(False)
        specs_buttons_layout.addWidget(self.delete_spec_btn)

        specs_buttons_layout.addStretch()

        # Кнопка получения характеристик из БД (только для режима редактирования)
        if record:
            self.load_db_specs_btn = QPushButton("🔄 Загрузить из БД")
            self.load_db_specs_btn.clicked.connect(self.load_specs_from_db)
            self.load_db_specs_btn.setStyleSheet("background-color: #4CAF50; color: white;")
            specs_buttons_layout.addWidget(self.load_db_specs_btn)

        # Кнопка получения системных характеристик
        self.load_system_specs_btn = QPushButton("💻 Загрузить системные характеристики")
        self.load_system_specs_btn.clicked.connect(self.load_system_specs)
        self.load_system_specs_btn.setStyleSheet("background-color: #2196F3; color: white;")
        specs_buttons_layout.addWidget(self.load_system_specs_btn)

        specs_group_layout.addLayout(specs_buttons_layout)

        specs_layout.addWidget(specs_group)

        # Добавляем виджеты в разделитель
        splitter.addWidget(computer_widget)
        splitter.addWidget(specs_widget)

        # Устанавливаем начальные размеры разделителя
        splitter.setSizes([300, 300])

        layout.addWidget(splitter)

        # Если редактируем, заполняем поля основной информации
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

        # Загружаем характеристики
        self.load_specifications()

        # Кнопки диалога
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_spec_selection_changed(self):
        """Обработчик изменения выделения в таблице характеристик"""
        selected_rows = self.specs_table.selectedItems()
        has_selection = len(selected_rows) > 0

        self.edit_spec_btn.setEnabled(has_selection)
        self.delete_spec_btn.setEnabled(has_selection)

    def load_specifications(self):
        """Загрузка характеристик в таблицу"""
        self.specs_table.setRowCount(len(self.specs))

        for i, spec in enumerate(self.specs):
            # Название характеристики
            name_item = QTableWidgetItem(spec[0])
            name_item.setData(Qt.ItemDataRole.UserRole, spec[2] if len(spec) > 2 else None)  # Сохраняем ID
            self.specs_table.setItem(i, 0, name_item)

            # Значение
            value_item = QTableWidgetItem(spec[1])
            self.specs_table.setItem(i, 1, value_item)

    def load_specs_from_db(self):
        """Загрузка характеристик текущего компьютера из БД"""
        if not self.computer_id:
            QMessageBox.warning(self, "Предупреждение", "ID компьютера не определен")
            return

        # Показываем диалог загрузки
        progress = QProgressDialog("Загрузка характеристик из БД...", "Отмена", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        # Создаем и запускаем поток для загрузки
        self.loader_thread = ComputerSpecsLoaderThread(self.connection_params, self.computer_id)
        self.loader_thread.finished.connect(lambda specs: self.on_db_specs_loaded(specs, progress))
        self.loader_thread.error.connect(lambda error: self.on_specs_load_error(error, progress))
        self.loader_thread.start()

    def load_system_specs(self):
        """Загрузка системных характеристик текущего компьютера"""
        # Показываем диалог загрузки с прогрессом
        progress = QProgressDialog("Загрузка системных характеристик...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        # Создаем и запускаем поток для загрузки системных характеристик
        self.system_loader = SystemSpecsLoaderThread()
        self.system_loader.progress.connect(progress.setValue)
        self.system_loader.finished.connect(lambda specs: self.on_system_specs_loaded(specs, progress))
        self.system_loader.error.connect(lambda error: self.on_specs_load_error(error, progress))
        self.system_loader.start()

    def on_db_specs_loaded(self, specs, progress):
        """Обработчик успешной загрузки характеристик из БД"""
        progress.close()

        if specs:
            added_count = 0
            for spec in specs:
                # Проверяем, есть ли уже такая характеристика
                if not self.spec_exists(spec[0]):
                    self.specs.append([spec[0], spec[1], None])
                    added_count += 1

            # Обновляем таблицу
            self.load_specifications()

            QMessageBox.information(
                self,
                "Успех",
                f"Загружено {len(specs)} характеристик из БД\n"
                f"Добавлено {added_count} новых"
            )
        else:
            QMessageBox.information(self, "Информация", "У компьютера нет характеристик в БД")

    def on_system_specs_loaded(self, specs, progress):
        """Обработчик успешной загрузки системных характеристик"""
        progress.close()

        if specs:
            added_count = 0
            for spec_name, spec_value in specs.items():
                # Проверяем, есть ли уже такая характеристика
                if not self.spec_exists(spec_name):
                    self.specs.append([spec_name, spec_value, None])
                    added_count += 16
                else:
                    # Обновляем существующую
                    for i, spec in enumerate(self.specs):
                        if spec[0] == spec_name:
                            self.specs[i][1] = spec_value
                            break

            # Обновляем таблицу
            self.load_specifications()

            QMessageBox.information(
                self,
                "Успех",
                f"Загружены системные характеристики:\n"
                f"• Процессор: {specs.get('Процессор', 'Не определен')}\n"
                f"• Оперативная память: {specs.get('Оперативная память', 'Не определена')}\n"
                f"• Жесткий диск: {specs.get('Жесткий диск', 'Не определен')}\n"
                f"• ОС: {specs.get('Операционная система', 'Не определена')}\n"
                + (f"• Ключ Windows: {specs.get('Ключ Windows', '')}\n" if 'Ключ Windows' in specs else "")
            )
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить системные характеристики")

    def spec_exists(self, spec_name):
        """Проверка, существует ли характеристика в текущем списке"""
        for spec in self.specs:
            if spec[0].lower() == spec_name.lower():
                return True
        return False

    def on_specs_load_error(self, error, progress):
        """Обработчик ошибки загрузки"""
        progress.close()
        QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке характеристик: {error}")

    def add_specification(self):
        """Добавление новой характеристики"""
        dialog = SpecificationsDialog(self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, value = dialog.get_data()
            self.specs.append([name, value, None])  # None - это ID (для новых записей)
            self.load_specifications()

    def edit_specification(self):
        """Редактирование выбранной характеристики"""
        current_row = self.specs_table.currentRow()
        if current_row < 0:
            return

        spec_name = self.specs_table.item(current_row, 0).text()
        spec_value = self.specs_table.item(current_row, 1).text()
        spec_id = self.specs_table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        dialog = SpecificationsDialog(self, (spec_name, spec_value))

        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, value = dialog.get_data()
            self.specs[current_row] = [name, value, spec_id]
            self.load_specifications()

    def delete_specification(self):
        """Удаление выбранной характеристики"""
        current_row = self.specs_table.currentRow()
        if current_row < 0:
            return

        spec_name = self.specs_table.item(current_row, 0).text()

        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Удалить характеристику '{spec_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            del self.specs[current_row]
            self.load_specifications()

    def validate_and_accept(self):
        """Проверка данных перед принятием"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Название компьютера обязательно для заполнения")
            return
        self.accept()

    def get_data(self):
        """Возвращает введенные данные"""
        purchase_date = self.purchase_date_edit.date().toString("yyyy-MM-dd")

        computer_data = (
            self.name_edit.text().strip(),
            self.inventory_edit.text().strip() or None,
            self.manufacturer_edit.text().strip() or None,
            self.model_edit.text().strip() or None,
            purchase_date
        )

        return computer_data, self.specs


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
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Название", "Инв. номер", "Производитель",
            "Модель", "Дата покупки", "Кол-во характеристик"
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
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Кол-во характеристик

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
        try:
            conn = sqlite3.connect('settings.db')
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nastr (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    database TEXT NOT NULL,
                    login TEXT NOT NULL,
                    password TEXT NOT NULL
                )
            ''')

            cursor.execute("SELECT COUNT(*) FROM nastr")
            count = cursor.fetchone()[0]

            if count == 0:
                cursor.execute('''
                    INSERT INTO nastr (ip, database, login, password)
                    VALUES (?, ?, ?, ?)
                ''', ('localhost', 'ont', 'postgres', 'postgres'))
                conn.commit()
                self.statusBar().showMessage("Добавлены настройки по умолчанию")

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
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()

            # Проверяем существование схемы invent и таблиц
            cursor.execute("CREATE SCHEMA IF NOT EXISTS invent")

            # Создаем таблицу computers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invent.computers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    inventory_number VARCHAR(100) UNIQUE,
                    manufacturer VARCHAR(100),
                    model VARCHAR(255),
                    purchase_date DATE
                )
            """)

            # Создаем таблицу computer_specs для характеристик
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS invent.computer_specs (
                    id SERIAL PRIMARY KEY,
                    computer_id INTEGER NOT NULL REFERENCES invent.computers(id) ON DELETE CASCADE,
                    spec_name VARCHAR(100) NOT NULL,
                    value TEXT NOT NULL,
                    UNIQUE(computer_id, spec_name)
                )
            """)

            # Проверяем, есть ли данные в computers
            cursor.execute("SELECT COUNT(*) FROM invent.computers")
            count = cursor.fetchone()[0]

            if count == 0:
                # Добавляем тестовые данные
                test_data = [
                    ('Workstation-01', 'INV-001', 'Dell', 'OptiPlex 7080', '2022-01-15'),
                    ('Workstation-02', 'INV-002', 'HP', 'EliteDesk 800', '2022-03-20'),
                    ('Server-01', 'INV-003', 'Supermicro', 'X11DPi-N', '2021-11-10')
                ]

                for data in test_data:
                    cursor.execute("""
                        INSERT INTO invent.computers 
                        (name, inventory_number, manufacturer, model, purchase_date) 
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id
                    """, data)
                    computer_id = cursor.fetchone()[0]

                    # Добавляем характеристики для каждого компьютера
                    if computer_id == 1:  # Workstation-01
                        specs = [
                            ('Процессор', 'Intel Core i7-10700'),
                            ('Оперативная память', '16GB DDR4'),
                            ('Видеокарта', 'NVIDIA Quadro P620'),
                            ('Жесткий диск', '512GB SSD'),
                            ('Операционная система', 'Windows 10 Pro'),
                            ('Ключ Windows', 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')
                        ]
                    elif computer_id == 2:  # Workstation-02
                        specs = [
                            ('Процессор', 'AMD Ryzen 5 5600X'),
                            ('Оперативная память', '32GB DDR4'),
                            ('Жесткий диск', '1TB NVMe SSD'),
                            ('Операционная система', 'Windows 11 Pro'),
                            ('Ключ Windows', 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')
                        ]
                    else:  # Server-01
                        specs = [
                            ('Процессор', 'Intel Xeon Silver 4210'),
                            ('Оперативная память', '64GB DDR4 ECC'),
                            ('Жесткий диск', '2x 1TB SSD RAID1'),
                            ('Операционная система', 'Windows Server 2019'),
                            ('Ключ Windows', 'XXXXX-XXXXX-XXXXX-XXXXX-XXXXX')
                        ]

                    for spec in specs:
                        cursor.execute("""
                            INSERT INTO invent.computer_specs (computer_id, spec_name, value)
                            VALUES (%s, %s, %s)
                        """, (computer_id, spec[0], spec[1]))

                conn.commit()
                self.statusBar().showMessage("Созданы тестовые данные с характеристиками")

            # Получаем данные с количеством характеристик
            cursor.execute("""
                SELECT 
                    c.id, 
                    c.name, 
                    c.inventory_number, 
                    c.manufacturer, 
                    c.model, 
                    c.purchase_date,
                    COUNT(cs.id) as specs_count
                FROM invent.computers c
                LEFT JOIN invent.computer_specs cs ON c.id = cs.computer_id
                GROUP BY c.id, c.name, c.inventory_number, c.manufacturer, c.model, c.purchase_date
                ORDER BY c.id
            """)
            rows = cursor.fetchall()

            # Заполняем таблицу
            self.table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if j < 6:  # Основные поля
                        item = QTableWidgetItem(str(value) if value else "")
                        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                        if j == 0:  # ID
                            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                        self.table.setItem(i, j, item)
                    else:  # Количество характеристик
                        count_item = QTableWidgetItem(str(value))
                        count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        count_item.setFlags(count_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.table.setItem(i, j, count_item)

            self.info_label.setText(f"Загружено записей: {len(rows)}")
            self.statusBar().showMessage(f"Данные обновлены: {len(rows)} записей")

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

    def get_computer_specs(self, computer_id):
        """Получение характеристик компьютера"""
        try:
            conn = psycopg2.connect(**self.connection_params)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT spec_name, value, id FROM invent.computer_specs
                WHERE computer_id = %s
                ORDER BY id
            """, (computer_id,))

            specs = cursor.fetchall()
            cursor.close()
            conn.close()

            return [[s[0], s[1], s[2]] for s in specs]

        except psycopg2.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке характеристик: {e}")
            return []

    def add_record(self):
        """Добавление новой записи"""
        dialog = ComputerDialog(self, connection_params=self.connection_params)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            computer_data, specs = dialog.get_data()
            name, inventory, manufacturer, model, purchase_date = computer_data

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                # Добавляем компьютер
                cursor.execute("""
                    INSERT INTO invent.computers 
                    (name, inventory_number, manufacturer, model, purchase_date)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (name, inventory, manufacturer, model, purchase_date))

                computer_id = cursor.fetchone()[0]

                # Добавляем характеристики
                for spec in specs:
                    if spec[0] and spec[1]:  # Проверяем, что поля не пустые
                        cursor.execute("""
                            INSERT INTO invent.computer_specs (computer_id, spec_name, value)
                            VALUES (%s, %s, %s)
                        """, (computer_id, spec[0], spec[1]))

                conn.commit()
                cursor.close()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Успех", f"Компьютер успешно добавлен (ID: {computer_id})")

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

        # Получаем текущие характеристики
        current_specs = self.get_computer_specs(self.current_id)

        dialog = ComputerDialog(self, current_data, current_specs, self.connection_params)
        dialog.setWindowTitle("Редактирование компьютера")

        if dialog.exec() == QDialog.DialogCode.Accepted:
            computer_data, specs = dialog.get_data()
            name, inventory, manufacturer, model, purchase_date = computer_data

            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                # Обновляем компьютер
                cursor.execute("""
                    UPDATE invent.computers
                    SET name = %s, inventory_number = %s, manufacturer = %s, 
                        model = %s, purchase_date = %s
                    WHERE id = %s
                """, (name, inventory, manufacturer, model, purchase_date, self.current_id))

                # Обновляем характеристики
                for spec in specs:
                    spec_name, spec_value, spec_id = spec

                    if spec_id:  # Существующая характеристика
                        cursor.execute("""
                            UPDATE invent.computer_specs
                            SET spec_name = %s, value = %s
                            WHERE id = %s AND computer_id = %s
                        """, (spec_name, spec_value, spec_id, self.current_id))
                    else:  # Новая характеристика
                        if spec_name and spec_value:
                            cursor.execute("""
                                INSERT INTO invent.computer_specs (computer_id, spec_name, value)
                                VALUES (%s, %s, %s)
                            """, (self.current_id, spec_name, spec_value))

                # Удаляем характеристики, которых больше нет в списке
                existing_ids = [spec[2] for spec in specs if spec[2] is not None]
                if existing_ids:
                    cursor.execute("""
                        DELETE FROM invent.computer_specs
                        WHERE computer_id = %s AND id NOT IN %s
                    """, (self.current_id, tuple(existing_ids)))
                else:
                    cursor.execute("""
                        DELETE FROM invent.computer_specs
                        WHERE computer_id = %s
                    """, (self.current_id,))

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
            f"Вы уверены, что хотите удалить компьютер '{computer_name}'?\n\n"
            "Все связанные характеристики также будут удалены!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = psycopg2.connect(**self.connection_params)
                cursor = conn.cursor()

                # Характеристики удалятся автоматически благодаря ON DELETE CASCADE
                cursor.execute("DELETE FROM invent.computers WHERE id = %s", (self.current_id,))

                if cursor.rowcount == 0:
                    QMessageBox.warning(self, "Предупреждение", "Компьютер не найден")
                else:
                    conn.commit()
                    QMessageBox.information(self, "Успех", "Компьютер и все его характеристики успешно удалены")

                cursor.close()
                conn.close()

                self.load_data()

            except psycopg2.Error as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при удалении компьютера: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = ComputersViewer()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()