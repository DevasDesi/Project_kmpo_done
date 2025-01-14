import pandas as pd
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
from database import Database
import os

class ExportToExcelDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Экспорт в Excel")
        self.setGeometry(300, 300, 400, 200)
        self.setStyleSheet("""
            QWidget { background-color: #D7EAD7; }
            QPushButton { background-color: #B2EBF2; color: black; }
            QLabel { color: black; }
            QLineEdit { background-color: #F1F4F1; }
        """)

        self.layout = QVBoxLayout()

        self.filename_input = QLineEdit()
        self.layout.addWidget(QLabel("Введите название файла (без .xlsx):"))
        self.layout.addWidget(self.filename_input)

        self.export_button = QPushButton("Экспортировать")
        self.export_button.clicked.connect(self.export_to_excel)
        self.layout.addWidget(self.export_button)

        self.setLayout(self.layout)

    def export_to_excel(self):
        filename = self.filename_input.text().strip()
        if not filename:
            QMessageBox.warning(self, "Ошибка", "Введите название файла.")
            return

        filepath = f"{filename}.xlsx"

        # Проверка на существование файла
        if os.path.exists(filepath):
            reply = QMessageBox.question(self, "Файл существует",
                                         f"Файл {filepath} уже существует. Перезаписать его?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return  # Если пользователь не хочет перезаписывать, выходим из функции

        # Получаем данные о завершенных заказах
        completed_orders = self.db.fetch_all(
            "SELECT SUM(price) FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE status = 'завершено')")
        total_income = float(completed_orders[0][0]) if completed_orders and completed_orders[0][0] is not None else 0.0

        sold_products = self.db.fetch_all(
            "SELECT product_id, SUM(quantity) FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE status = 'завершено') GROUP BY product_id")
        sold_products_dict = {product[0]: product[1] for product in sold_products}

        # Получаем данные о товарах на складе
        products_in_stock = self.db.fetch_all("SELECT id, name, quantity FROM products")
        stock_data = {product[0]: (product[1], product[2]) for product in products_in_stock}

        # Создаем DataFrame для записи в Excel
        data = {
            "Общий доход": [f"{total_income:.2f} ₽"],  # Добавляем символ рубля
            "Продано товаров": [sum(sold_products_dict.values())],
        }

        # Создаем DataFrame для товаров на складе
        stock_list = []
        for product_id, (name, quantity) in stock_data.items():
            sold_quantity = sold_products_dict.get(product_id, 0)
            stock_list.append({
                "Товар": name,
                "Остаток товара на складе": quantity,
                "Продано": sold_quantity,
            })

        stock_df = pd.DataFrame(stock_list)

        # Получаем данные о заказах по месяцам
        monthly_data = self.db.fetch_all(
            """
            SELECT strftime('%Y-%m', orders.created_at) AS month, 
                   SUM(order_items.price) AS total_income, 
                   SUM(order_items.quantity) AS total_sold
            FROM orders
            JOIN order_items ON orders.id = order_items.order_id
            WHERE orders.status = 'завершено'
            GROUP BY month
            ORDER BY month
            """
        )

        # Создаем DataFrame для месячных данных
        monthly_list = []
        for month, total_income, total_sold in monthly_data:
            monthly_list.append({
                "Месяц": month,
                "Общий доход": f"{total_income:.2f} ₽",
                "Продано товаров": total_sold,
            })

        monthly_df = pd.DataFrame(monthly_list)

        # Записываем данные в Excel
        try:
            with pd.ExcelWriter(filepath) as writer:
                pd.DataFrame(data).to_excel(writer, sheet_name='Общая информация', index=False)
                stock_df.to_excel(writer, sheet_name='Товары на складе', index=False)
                monthly_df.to_excel(writer, sheet_name='Данные по месяцам', index=False)

                # Устанавливаем ширину столбцов автоматически
                for sheet_name in ['Общая информация', 'Товары на складе', 'Данные по месяцам']:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column = [cell for cell in column]
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)  # Добавляем немного пространства
                        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width

            QMessageBox.information(self, "Успех", f"Данные успешно экспортированы в {filepath}.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать данные: {str(e)}")
