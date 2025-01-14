from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QDialog, QComboBox,
    QLineEdit, QLabel, QDialogButtonBox, QMessageBox
)
from PyQt6.QtGui import QIntValidator
from PyQt6.QtCore import Qt
from database import Database
from ui_products import AddProductDialog
from export_to_excel import ExportToExcelDialog



class MainApp(QMainWindow):
    def __init__(self, db, user_id, role):
        super().__init__()

        self.db = db
        self.user_id = user_id
        self.role = role

        self.setWindowTitle("Система управления заказами")
        self.setGeometry(100, 100, 800, 600)

        container = QWidget()
        self.setCentralWidget(container)

        self.layout = QVBoxLayout()

        # Установка стиля
        self.setStyleSheet("""
            QWidget { background-color: #D7EAD7; }
            QPushButton { background-color: #B2EBF2; color: black; }
            QTableWidget { background-color: #D7EAD7; }
            QLabel { color: black; }
            QLineEdit { background-color: #F1F4F1; }
        """)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)  # Увеличиваем количество колонок на 1
        self.orders_table.setHorizontalHeaderLabels(["Имя заказчика", "Номер заказа", "Товар", "Количество", "Цена", "Статус", "Время создания"])  # Добавляем заголовок для времени создания
        self.layout.addWidget(self.orders_table)

        self.update_orders_list()

        # Кнопки управления
        self.add_order_button = QPushButton("Добавить заказ")
        self.add_order_button.clicked.connect(self.on_add_order_button_click)

        self.edit_order_button = QPushButton("Редактировать заказ")
        self.edit_order_button.clicked.connect(self.edit_order)

        self.delete_order_button = QPushButton("Удалить заказ")
        self.delete_order_button.clicked.connect(self.delete_order)

        self.manage_products_button = QPushButton("Управление товарами")
        self.manage_products_button.clicked.connect(self.manage_products)

        # Добавляем кнопки только если пользователь - администратор
        if self.role == 'admin':
            self.layout.addWidget(self.add_order_button)
            self.layout.addWidget(self.edit_order_button)
            self.layout.addWidget(self.delete_order_button)
            self.layout.addWidget(self.manage_products_button)

        # Кнопка обновления таблицы
        self.refresh_button = QPushButton("Обновить таблицу")
        self.refresh_button.clicked.connect(self.update_orders_list)
        self.layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignRight)  # Выравнивание по правому краю

        self.export_button = QPushButton("Экспорт в Excel")
        self.export_button.clicked.connect(self.open_export_dialog)
        self.layout.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)

        container.setLayout(self.layout)

    def open_export_dialog(self):
        dialog = ExportToExcelDialog(self.db)
        dialog.exec()

    def on_add_order_button_click(self):
        try:
            dialog = AddOrderDialog(self.db, self.user_id, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                order_items = dialog.get_selected_order_items()
                if not order_items:
                    QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один товар для добавления в заказ.")
                    return

                # Добавляем заказ
                self.add_order(self.user_id, order_items)
                self.db.conn.commit()  # Подтверждаем изменения в БД

                self.update_orders_list()  # Обновляем таблицу заказов
                QMessageBox.information(self, "Успех", "Заказ успешно добавлен.")
        except Exception as e:
            print(f"Ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении заказа: {e}")

    def load_orders(self):
        """ Загружает заказы из базы данных и обновляет таблицу. """
        try:
            orders = self.db.fetch_all(""" 
                SELECT o.id, u.username AS customer_name, 
                       p.name AS product_name,
                       oi.quantity,
                       (oi.quantity * p.price) AS total_price,
                       o.status,
                       o.created_at  -- Добавляем время создания заказа
                FROM orders o
                JOIN order_items oi ON o.id = oi.order_id
                JOIN products p ON oi.product_id = p.id
                JOIN users u ON o.user_id = u.id
            """)

            self.orders_table.setRowCount(len(orders))  # Устанавливаем количество строк в таблице

            for row, (order_id, customer_name, product_name, quantity, total_price, status, created_at) in enumerate(
                    orders):
                self.orders_table.setItem(row, 0, QTableWidgetItem(customer_name))  # Имя заказчика
                self.orders_table.setItem(row, 1, QTableWidgetItem(str(order_id)))  # ID заказа
                self.orders_table.setItem(row, 2, QTableWidgetItem(product_name))  # Название товара
                self.orders_table.setItem(row, 3, QTableWidgetItem(str(quantity)))  # Количество товара
                self.orders_table.setItem(row, 4, QTableWidgetItem(f"{total_price:.2f}"))  # Общая сумма за товар
                self.orders_table.setItem(row, 5, QTableWidgetItem(status))  # Статус заказа
                self.orders_table.setItem(row, 6, QTableWidgetItem(created_at))  # Время создания заказа

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки заказов: {e}")

    def update_orders_list(self):
        # Очищаем таблицу перед обновлением
        self.orders_table.setRowCount(0)

        # Формируем запрос в зависимости от роли пользователя
        if self.role == 'admin':
            query = """ 
                SELECT 
                    orders.id,
                    orders.order_number, 
                    users.username, 
                    GROUP_CONCAT(products.name || '|' || order_items.quantity || '|' || order_items.price, '\n') AS product_list, 
                    SUM(order_items.quantity) AS total_quantity,
                    SUM(order_items.price) AS total_price,
                    orders.status,
                    orders.created_at  -- Добавляем время создания заказа
                FROM orders
                JOIN users ON orders.user_id = users.id
                JOIN order_items ON order_items.order_id = orders.id
                JOIN products ON order_items.product_id = products.id
                GROUP BY orders.id
            """
            orders = self.db.fetch_all(query)
        else:
            query = """ 
                SELECT 
                    orders.id,
                    orders.order_number, 
                    users.username, 
                    GROUP_CONCAT(products.name || '|' || order_items.quantity || '|' || order_items.price, '\n') AS product_list, 
                    SUM(order_items.quantity) AS total_quantity,
                    SUM(order_items.price) AS total_price,
                    orders.status,
                    orders.created_at  -- Добавляем время создания заказа
                FROM orders
                JOIN users ON orders.user_id = users.id
                JOIN order_items ON order_items.order_id = orders.id
                JOIN products ON order_items.product_id = products.id
                WHERE users.id = ?
                GROUP BY orders.id
            """
            orders = self.db.fetch_all(query, (self.user_id,))

        # Перебор заказов и добавление данных в таблицу
        for order in orders:
            order_id, order_number, username, product_list, total_quantity, total_price, status, created_at = order

            # Добавляем строку с данными о заказе
            main_row = self.orders_table.rowCount()
            self.orders_table.insertRow(main_row)

            # Заполняем данные о заказе
            self.orders_table.setItem(main_row, 0, QTableWidgetItem(username))  # Имя заказчика
            self.orders_table.setItem(main_row, 1, QTableWidgetItem(order_number))  # Номер заказа
            self.orders_table.setItem(main_row, 2, QTableWidgetItem(""))  # Пусто
            self.orders_table.setItem(main_row, 3, QTableWidgetItem(str(total_quantity)))  # Общее количество
            self.orders_table.setItem(main_row, 4, QTableWidgetItem(f"{total_price:.2f}₽"))  # Общая цена
            self.orders_table.setItem(main_row, 5, QTableWidgetItem(status))  # Статус заказа
            self.orders_table.setItem(main_row, 6, QTableWidgetItem(created_at))  # Время создания заказа

            # Добавление строк для продуктов в заказе
            if product_list:
                products = product_list.split('\n')
                for product_details in products:
                    product_name, quantity, price = product_details.split('|')
                    quantity = int(quantity)
                    price = float(price)

                    details_row = self.orders_table.rowCount()
                    self.orders_table.insertRow(details_row)

                    # Заполняем только данные о товаре
                    self.orders_table.setItem(details_row, 0, QTableWidgetItem(""))  # Пусто
                    self.orders_table.setItem(details_row, 1, QTableWidgetItem(""))  # Пусто
                    self.orders_table.setItem(details_row, 2, QTableWidgetItem(product_name))  # Название товара
                    self.orders_table.setItem(details_row, 3, QTableWidgetItem(str(quantity)))  # Количество товара
                    self.orders_table.setItem(details_row, 4, QTableWidgetItem(f"{price:.2f}₽"))  # Цена товара
                    self.orders_table.setItem(details_row, 5, QTableWidgetItem(""))  # Пусто

                # Устанавливаем время создания только для первой строки
                self.orders_table.setItem(main_row, 6, QTableWidgetItem(created_at))  # Время создания заказа
                # Оставляем пустыми строки с товарами
                for i in range(1, len(products) + 1):
                    self.orders_table.setItem(main_row + i, 6, QTableWidgetItem(""))  # Пусто для строк с товарами

    def update_order_status(self, order_id, new_status):
        """Обновляет статус заказа в базе данных."""
        query = "UPDATE orders SET status = ? WHERE id = ?"
        try:
            # Получаем текущие товары в заказе
            current_order_items = self.db.fetch_all("SELECT product_id, quantity FROM order_items WHERE order_id = ?",
                                                    (order_id,))

            # Обновляем статус заказа
            self.db.query(query, (new_status, order_id))

            if new_status == "завершено":
                # Если статус изменен на "завершено", обновляем количество товара на складе
                for product_id, quantity in current_order_items:
                    self.db.query("UPDATE products SET quantity = quantity - ? WHERE id = ?",
                                  (quantity, product_id))  # Вычитаем количество

            self.db.conn.commit()  # Подтверждаем изменения в БД
            print(f"Статус заказа {order_id} обновлён на {new_status}")
        except Exception as e:
            self.db.conn.rollback()
            print(f"Ошибка обновления статуса заказа: {e}")

    def toggle(self, row: int, product_count: int):
        """
        Сворачивает или разворачивает строки с товарами.
        :param row: Номер строки с заказом.
        :param product_count: Количество строк с товарами для данного заказа.
        """
        # Проверяем, развернуты ли строки
        is_expanded = self.orders_table.rowSpan(row, 0) > 1

        # Меняем текст кнопки
        button = self.orders_table.cellWidget(row, 4)
        if button:  # Проверяем, что кнопка существует
            button.setText("Развернуть" if is_expanded else "Свернуть")

        # Показываем или скрываем строки с товарами
        for i in range(1, product_count + 1):
            details_row = row + i
            self.orders_table.setRowHidden(details_row, is_expanded)

        # Обновляем объединение строк
        if is_expanded:
            self.orders_table.setSpan(row, 0, 1, 1)  # Сбрасываем объединение строк
        else:
            self.orders_table.setSpan(row, 0, product_count + 1, 1)  # Объединяем строки с товарами

    def create_toggle_callback(self, row, product_count):
        def toggle(self, row, product_count):
            # Состояние строки (развернута или свернута)
            is_expanded = self.orders_table.rowSpan(row, 0) > 1
            for i in range(product_count):
                self.orders_table.setRowHidden(row + i + 1, not is_expanded)

            button = self.orders_table.cellWidget(row, 4)
            button.setText("Свернуть" if not is_expanded else "Развернуть")
            self.orders_table.setRowSpan(row, 0, 1 if is_expanded else product_count + 1)

        return toggle

    def toggle_products(self, order_row, products):
        # Узнаём, нужно ли скрыть или показать строки
        is_expanded = self.orders_table.isRowHidden(order_row + 1)

        for product_index in range(len(products)):
            details_row = order_row + 1 + product_index
            self.orders_table.setRowHidden(details_row, is_expanded)

        # Обновляем текст кнопки
        button = self.orders_table.cellWidget(order_row, 3)
        if is_expanded:
            button.setText("Свернуть")
        else:
            button.setText("Развернуть")

    def add_order(self, user_id, order_items):
        try:
            print(f"Добавление заказа для пользователя {user_id}, товары: {order_items}")

            # Проверка наличия товара на складе
            for product_id, quantity in order_items:
                stock_quantity = self.db.fetch_one("SELECT quantity FROM products WHERE id = ?", (product_id,))
                if stock_quantity is None or stock_quantity[0] < quantity:
                    QMessageBox.warning(self, "Недостаточно товара", f"Недостаточно товара на складе для продукта ID {product_id}.")
                    return  # Прерываем выполнение, если товара недостаточно

            # Генерация номера заказа
            order_number_query = "SELECT COUNT(*) FROM orders"
            order_count = self.db.fetch_one(order_number_query)[0]
            order_number = f"ORD-{order_count + 1}"

            # Начинаем транзакцию для добавления заказа
            self.db.query("INSERT INTO orders (user_id, order_number, status) VALUES (?, ?, ?)",
                          (user_id, order_number, "Ожидание"))

            # Получаем ID только что добавленного заказа
            order_id = self.db.fetch_one("SELECT id FROM orders WHERE order_number = ?", (order_number,))[0]

            total_quantity = 0
            total_price = 0.0

            # Добавление товаров в заказ
            for product_id, quantity in order_items:
                # Получаем цену товара
                price = self.db.fetch_one("SELECT price FROM products WHERE id = ?", (product_id,))

                if price is None:
                    print(f"Товар с ID {product_id} не найден.")
                    continue

                price = price[0]  # Извлекаем цену

                # Добавляем товар в таблицу order_items
                self.db.query("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                              (order_id, product_id, quantity, price * quantity))

                total_quantity += quantity
                total_price += price * quantity

                # Обновляем количество товара на складе
                self.db.query("UPDATE products SET quantity = quantity - ? WHERE id = ?", (quantity, product_id))

            # Фиксируем изменения в базе данных
            self.db.conn.commit()
            print(f"Заказ {order_number} успешно добавлен для пользователя {user_id}")

            # Обновляем таблицу заказов
            self.update_orders_list()  # Обновляем таблицу после добавления заказа

        except Exception as e:
            # Откат транзакции в случае ошибки
            self.db.conn.rollback()
            print(f"Ошибка добавления заказа: {e}")
            raise e

    def edit_order(self):
        # Открываем диалог выбора заказа
        select_order_dialog = SelectOrderDialog(self.db, self)
        if select_order_dialog.exec() == QDialog.DialogCode.Accepted:
            order_id = select_order_dialog.get_selected_order_id()  # Получаем ID выбранного заказа
            if order_id:
                # Получаем текущие товары в заказе
                current_order_items = self.db.fetch_all(
                    "SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
                # Открываем диалог редактирования
                dialog = EditOrderDialog(self.db, order_id)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # Получаем новые товары в заказе
                    new_order_items = dialog.get_order_items()  # Получаем новые товары

                    # Обновляем количество товара на складе
                    for product_id, quantity in current_order_items:
                        self.db.query("UPDATE products SET quantity = quantity + ? WHERE id = ?",
                                      (quantity, product_id))  # Возвращаем старое количество

                    for product_id, quantity in new_order_items:
                        self.db.query("UPDATE products SET quantity = quantity - ? WHERE id = ?",
                                      (quantity, product_id))  # Вычитаем новое количество

                    self.update_orders_list()  # Обновляем список заказов после редактирования

    def delete_order(self):
        dialog = DeleteOrderDialog(self.db)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_orders_list()
            QMessageBox.information(self, "Заказ удалён", "Заказ успешно удалён!")

    def manage_products(self):
        dialog = ManageProductsDialog(self.db)
        dialog.exec()


class ManageProductsDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Управление товарами")
        self.setGeometry(250, 250, 600, 400)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(4)
        self.products_table.setHorizontalHeaderLabels(["ID", "Название товара", "Цена (руб.)", "Остаток товара на складе"])  # Изменено название столбца
        self.layout.addWidget(self.products_table)

        self.add_product_button = QPushButton("Добавить товар")
        self.add_product_button.clicked.connect(self.add_product)
        self.layout.addWidget(self.add_product_button)

        self.edit_product_button = QPushButton("Редактировать выбранный товар")
        self.edit_product_button.clicked.connect(self.edit_selected_product)
        self.layout.addWidget(self.edit_product_button)

        self.delete_product_button = QPushButton("Удалить выбранный товар")
        self.delete_product_button.clicked.connect(self.delete_selected_product)
        self.layout.addWidget(self.delete_product_button)

        self.load_products()
        self.setLayout(self.layout)

    def load_products(self):
        products = self.db.fetch_all("SELECT id, name, price, quantity FROM products")
        self.products_table.setRowCount(len(products))

        for row, product in enumerate(products):
            for col, data in enumerate(product):
                self.products_table.setItem(row, col, QTableWidgetItem(str(data)))

    def refresh_products(self):
        """Обновляет список товаров в таблице."""
        self.load_products()  # Перезагружаем товары из базы данных

    def edit_selected_product(self):
        current_row = self.products_table.currentRow()
        if current_row != -1:
            product_id = int(self.products_table.item(current_row, 0).text())
            dialog = EditProductDialog(self.db, product_id)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_products()  # Обновляем таблицу после редактирования
        else:
            QMessageBox.warning(self, "Нет выбора", "Пожалуйста, выберите товар для редактирования.")

    def add_product(self):
        dialog = AddProductDialog(self.db)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_products()  # Обновляем таблицу после добавления

    def delete_selected_product(self):
        current_row = self.products_table.currentRow()
        if current_row != -1:
            product_id = self.products_table.item(current_row, 0).text()
            reply = QMessageBox.question(
                self,
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить продукт с ID {product_id}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.db.query("DELETE FROM products WHERE id = ?", (product_id,))
                self.refresh_products()  # Обновляем таблицу после удаления
        else:
            QMessageBox.warning(self, "Нет выбранного элемента", "Пожалуйста, выберите продукт для удаления.")


class AddOrderDialog(QDialog):
    def __init__(self, db, user_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_id = user_id

        self.setWindowTitle("Добавить заказ")
        self.setGeometry(300, 300, 600, 400)

        self.layout = QVBoxLayout(self)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        # Выбор пользователя
        self.user_combobox = QComboBox()
        try:
            users = self.db.fetch_all("SELECT id, username FROM users WHERE role = 'user'")
            if not users:
                QMessageBox.warning(self, "Предупреждение", "Нет доступных пользователей для выбора.")
            for user_id, username in users:
                self.user_combobox.addItem(username, user_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки пользователей: {e}")
            return
        self.layout.addWidget(QLabel("Выберите пользователя:"))
        self.layout.addWidget(self.user_combobox)

        # Таблица товаров
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(2)
        self.products_table.setHorizontalHeaderLabels(["ID Товара", "Количество"])
        self.layout.addWidget(QLabel("Добавьте товары:"))
        self.layout.addWidget(self.products_table)

        # Кнопки подтверждения
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.load_products()

    def load_products(self):
        """
        Загружаем товары из базы данных и заполняем таблицу.
        """
        try:
            products = self.db.fetch_all("SELECT id, name, quantity FROM products")
            if not products:
                QMessageBox.warning(self, "Предупреждение", "Нет доступных товаров для добавления.")
                return
            self.products_table.setRowCount(len(products))
            for row, (product_id, name, quantity) in enumerate(products):
                self.products_table.setItem(row, 0, QTableWidgetItem(f"{product_id}: {name}"))
                self.products_table.setItem(row, 1, QTableWidgetItem("0"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки товаров: {e}")

    def get_selected_order_items(self):
        """
        Собирает данные о выбранных товарах и их количестве из таблицы.
        :return: Список кортежей (id_товара, количество)
        """
        order_items = []
        for row in range(self.products_table.rowCount()):
            product_id_item = self.products_table.item(row, 0)
            quantity_item = self.products_table.item(row, 1)

            if not product_id_item or not quantity_item:
                continue

            try:
                product_id = int(product_id_item.text().split(":")[0])
                quantity = int(quantity_item.text())
                if quantity > 0:
                    order_items.append((product_id, quantity))
            except ValueError:
                continue

        return order_items

    def accept(self):
        """
        Обработка данных перед закрытием диалога.
        """
        order_items = self.get_selected_order_items()

        if not order_items:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один товар для заказа.")
            return

        try:
            selected_user_id = self.user_combobox.currentData()  # Получаем ID выбранного пользователя
            main_app = self.parent()
            main_app.add_order(selected_user_id, order_items)

            # Обновляем таблицу заказов
            main_app.load_orders()  # Добавьте этот вызов

            self.close()  # Закрываем диалог
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при добавлении заказа: {e}")

class EditProductDialog(QDialog):
    def __init__(self, db, product_id):
        super().__init__()
        self.db = db
        self.product_id = product_id
        self.setWindowTitle("Редактировать продукт")
        self.setGeometry(250, 250, 400, 300)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        product = self.db.fetch_one("SELECT name, price, quantity FROM products WHERE id = ?", (self.product_id,))

        self.product_name_input = QLineEdit(product[0])
        self.product_price_input = QLineEdit(str(product[1]))
        self.product_quantity_input = QLineEdit(str(product[2]))
        self.product_quantity_input.setValidator(QIntValidator())

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.layout.addWidget(QLabel("Имя продукта:"))
        self.layout.addWidget(self.product_name_input)
        self.layout.addWidget(QLabel("Цена(рубли):"))
        self.layout.addWidget(self.product_price_input)
        self.layout.addWidget(QLabel("Колличество:"))
        self.layout.addWidget(self.product_quantity_input)

        self.layout.addWidget(self.buttons)
        self.setLayout(self.layout)

    def accept(self):
        name = self.product_name_input.text()
        price = self.product_price_input.text()
        quantity = self.product_quantity_input.text()

        if name and price and quantity.isdigit():
            self.db.query("UPDATE products SET name = ?, price = ?, quantity = ? WHERE id = ?",
                          (name, float(price), int(quantity), self.product_id))
            super().accept()
        else:
            QMessageBox.warning(self, "Вывод ошибки", "Пожалуйста заполните все правильно.")

class SelectOrderDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Выберите заказ")
        self.setGeometry(300, 300, 400, 300)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        # Список доступных заказов
        self.order_combobox = QComboBox()
        self.load_orders()
        self.layout.addWidget(QLabel("Выберите заказ:"))
        self.layout.addWidget(self.order_combobox)

        # Кнопки подтверждения
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def load_orders(self):
        orders = self.db.fetch_all("SELECT id, order_number FROM orders")
        for order in orders:
            self.order_combobox.addItem(order[1], order[0])  # order[1] - номер заказа, order[0] - ID заказа

    def get_selected_order_id(self):
        return self.order_combobox.currentData()  # Возвращает ID выбранного заказа


class RemoveProductDialog(QDialog):
    def __init__(self, order_items):
        super().__init__()
        self.setWindowTitle("Удалить товар")
        self.setGeometry(300, 300, 400, 300)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        # Список добавленных товаров
        self.products_list = QTableWidget()
        self.products_list.setColumnCount(2)
        self.products_list.setHorizontalHeaderLabels(["Название товара", "Количество"])
        self.layout.addWidget(self.products_list)

        self.load_products(order_items)

        # Кнопки подтверждения
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def load_products(self, order_items):
        self.order_items = order_items
        self.products_list.setRowCount(len(order_items))
        for row, (product_id, name, quantity) in enumerate(order_items):
            self.products_list.setItem(row, 0, QTableWidgetItem(name))
            self.products_list.setItem(row, 1, QTableWidgetItem(str(quantity)))

    def accept(self):
        current_row = self.products_list.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите товар для удаления.")
            return

        self.selected_product_id = self.order_items[current_row][0]
        super().accept()



class EditOrderDialog(QDialog):
    def __init__(self, db, order_id):
        super().__init__()
        self.db = db
        self.order_id = order_id
        self.setWindowTitle("Редактировать заказ")
        self.setGeometry(300, 300, 500, 400)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        # Выбор пользователя
        self.user_combobox = QComboBox()
        users = self.db.fetch_all("SELECT id, username FROM users WHERE role = 'user'")
        for user in users:
            self.user_combobox.addItem(user[1], user[0])

        order = self.db.fetch_one("SELECT user_id FROM orders WHERE id = ?", (self.order_id,))
        if order:
            self.user_combobox.setCurrentIndex(
                next(i for i in range(self.user_combobox.count()) if self.user_combobox.itemData(i) == order[0])
            )
        self.layout.addWidget(QLabel("Выберите пользователя:"))
        self.layout.addWidget(self.user_combobox)

        # Редактирование статуса заказа
        self.status_combobox = QComboBox()
        self.status_combobox.addItems(["В процессе", "завершено", "отменено"])  # Пример статусов
        current_status = self.db.fetch_one("SELECT status FROM orders WHERE id = ?", (self.order_id,))
        if current_status:
            self.status_combobox.setCurrentText(current_status[0])
        self.layout.addWidget(QLabel("Статус заказа:"))
        self.layout.addWidget(self.status_combobox)

        # Редактирование товаров заказа
        self.items = []
        self.items_layout = QVBoxLayout()  # Новый layout для товаров
        order_items = self.db.fetch_all("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (self.order_id,))
        for product_id, quantity in order_items:
            self.add_product_item(product_id, quantity)

        self.layout.addLayout(self.items_layout)

        # Кнопка для добавления нового товара
        self.add_product_button = QPushButton("Добавить товар")
        self.add_product_button.clicked.connect(self.add_product)
        self.layout.addWidget(self.add_product_button)

        # Кнопка для удаления выбранного товара
        self.remove_product_button = QPushButton("Удалить выбранный товар")
        self.remove_product_button.clicked.connect(self.remove_product)
        self.layout.addWidget(self.remove_product_button)

        # Кнопки подтверждения
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def add_product_item(self, product_id=None, quantity=1):
        """Добавляет элемент товара в список товаров заказа."""
        item_layout = QVBoxLayout()
        product_combobox = QComboBox()
        products = self.db.fetch_all("SELECT id, name FROM products")
        for product in products:
            product_combobox.addItem(product[1], product[0])

        # Если product_id не None, устанавливаем текущий индекс
        if product_id is not None:
            product_combobox.setCurrentIndex(
                next(i for i in range(product_combobox.count()) if product_combobox.itemData(i) == product_id)
            )

        quantity_input = QLineEdit(str(quantity))
        quantity_input.setValidator(QIntValidator())

        item_layout.addWidget(QLabel("Товар:"))
        item_layout.addWidget(product_combobox)
        item_layout.addWidget(QLabel("Количество:"))
        item_layout.addWidget(quantity_input)

        self.items_layout.addLayout(item_layout)
        self.items.append((product_combobox, quantity_input))

    def add_product(self):
        """Добавляет новый товар в заказ."""
        self.add_product_item(quantity=1)  # Добавляем новый товар с количеством 1

    def remove_product(self):
        """Удаляет выбранный товар из заказа."""
        if self.items:
            # Удаляем последний добавленный товар
            product_combobox, quantity_input = self.items.pop()
            for i in range(self.items_layout.count()):
                layout = self.items_layout.itemAt(i).layout()
                if layout and layout.itemAt(0).widget() == product_combobox:
                    # Удаляем layout с товарами
                    for j in range(layout.count()):
                        widget = layout.itemAt(j).widget()
                        if widget:
                            widget.deleteLater()
                    self.items_layout.removeItem(self.items_layout.itemAt(i))
                    break

    def get_order_items(self):
        """Возвращает список товаров и их количеств из диалога редактирования заказа."""
        order_items = []
        for product_combobox, quantity_input in self.items:
            product_id = product_combobox.currentData()
            quantity = quantity_input.text()
            if product_id and quantity.isdigit() and int(quantity) > 0:
                order_items.append((product_id, int(quantity)))  # Добавляем кортеж (product_id, quantity)
        return order_items

    def accept(self):
        user_id = self.user_combobox.currentData()
        if not user_id:
            QMessageBox.warning(self, "Ошибка", "Выберите пользователя.")
            return

        # Обновление заказа
        self.db.query("UPDATE orders SET user_id = ?, status = ? WHERE id = ?", (user_id, self.status_combobox.currentText(), self.order_id))
        self.db.query("DELETE FROM order_items WHERE order_id = ?", (self.order_id,))

        for product_combobox, quantity_input in self.items:
            product_id = product_combobox.currentData()
            quantity = quantity_input.text()
            if product_id and quantity.isdigit() and int(quantity) > 0:
                product = self.db.fetch_one("SELECT price FROM products WHERE id = ?", (product_id,))
                price = product[0] * int(quantity)
                self.db.query("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?, ?, ?, ?)",
                              (self.order_id, product_id, int(quantity), price))

        QMessageBox.information(self, "Успех", "Заказ успешно отредактирован.")
        super().accept()


class DeleteOrderDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Удалить заказ")
        self.setGeometry(300, 300, 400, 200)

        self.setStyleSheet("""
                    QWidget { background-color: #D7EAD7; }
                    QPushButton { background-color: #B2EBF2; color: black; }
                    QLabel { color: black; }
                    QLineEdit { background-color: #F1F4F1; }
                """)

        self.layout = QVBoxLayout()

        # Список заказов
        self.order_combobox = QComboBox()
        orders = self.db.fetch_all("SELECT id, order_number FROM orders")
        for order in orders:
            self.order_combobox.addItem(order[1], order[0])
        self.layout.addWidget(QLabel("Выберите заказ:"))
        self.layout.addWidget(self.order_combobox)

        # Кнопки подтверждения
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

        self.setLayout(self.layout)

    def accept(self):
        order_id = self.order_combobox.currentData()
        if not order_id:
            QMessageBox.warning(self, "Ошибка", "Выберите заказ для удаления.")
            return

        self.db.query("DELETE FROM order_items WHERE order_id = ?", (order_id,))
        self.db.query("DELETE FROM orders WHERE id = ?", (order_id,))
        QMessageBox.information(self, "Успех", "Заказ успешно удалён.")
        super().accept()




if __name__ == '__main__':
    app = QApplication([])
    window = MainApp()
    window.show()
    app.exec()