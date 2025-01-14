from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox
from database import Database
import bcrypt

class RegistrationDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Регистрация пользователя")
        self.setGeometry(300, 300, 400, 200)

        self.layout = QVBoxLayout()

        # Установка стиля
        self.setStyleSheet("""
            QWidget { background-color: #D7EAD7; }
            QPushButton { background-color: #B2EBF2; color: black; }
            QLabel { color: black; }
            QLineEdit { background-color: #F1F4F1; }  /* Добавлено для изменения цвета полей ввода */
        """)

        # Поле для имени пользователя
        self.username_label = QLabel("Имя пользователя:")
        self.username_input = QLineEdit()
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        # Поле для пароля
        self.password_label = QLabel("Пароль:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        # Поле для выбора роли
        self.role_label = QLabel("Роль:")
        self.role_combobox = QComboBox()
        self.role_combobox.addItems(["admin", "user"])
        self.layout.addWidget(self.role_label)
        self.layout.addWidget(self.role_combobox)

        # Кнопка регистрации
        self.register_button = QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.register_user)
        self.layout.addWidget(self.register_button)

        # Кнопка перехода на вход
        self.login_button = QPushButton("Уже есть аккаунт?")
        self.login_button.clicked.connect(self.switch_to_login_dialog)
        self.layout.addWidget(self.login_button)

        self.setLayout(self.layout)

    def register_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role = self.role_combobox.currentText()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены.")
            return

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        try:
            self.db.query("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
            QMessageBox.information(self, "Успех", "Пользователь успешно зарегистрирован.")
            self.accept()  # Закрыть окно регистрации
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при регистрации: {e}")

    def switch_to_login_dialog(self):
        self.reject()  # Закрываем окно регистрации, чтобы открыть окно входа


class LoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setWindowTitle("Вход в систему")
        self.setGeometry(300, 300, 400, 150)

        self.layout = QVBoxLayout()

        # Установка стиля
        self.setStyleSheet("""
            QWidget { background-color: #D7EAD7; }
            QPushButton { background-color: #B2EBF2; color: black; }
            QLabel { color: black; }
            QLineEdit { background-color: #F1F4F1; }  /* Добавлено для изменения цвета полей ввода */
        """)

        # Поле для имени пользователя
        self.username_label = QLabel("Имя пользователя:")
        self.username_input = QLineEdit()
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_input)

        # Поле для пароля
        self.password_label = QLabel("Пароль:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_input)

        # Кнопка входа
        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.login_user)
        self.layout.addWidget(self.login_button)

        self.setLayout(self.layout)

    def login_user(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self , "Ошибка ", "Все поля должны быть заполнены.")
            return

        user = self.db.fetch_one("SELECT id, password, role FROM users WHERE username = ?", (username,))
        if user:
            user_id, hashed_password, role = user
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                QMessageBox.information(self, "Успех", "Вход выполнен успешно.")
                self.accept()
                self.user_id = user_id
                self.role = role
            else:
                QMessageBox.critical(self, "Ошибка", "Неверный пароль.")
        else:
            QMessageBox.critical(self, "Ошибка", "Пользователь не найден.")