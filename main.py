import sys
import traceback
from PyQt6.QtWidgets import QApplication, QDialog
from ui_main import MainApp
from database import Database
from registration_ui import RegistrationDialog, LoginDialog

def exception_hook(exc_type, exc_value, exc_traceback):
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    sys.exit(1)

sys.excepthook = exception_hook
def main():
    app = QApplication(sys.argv)
    db = Database()

    while True:
        # Всегда показываем окно регистрации первым
        registration_dialog = RegistrationDialog(db)
        if registration_dialog.exec() == QDialog.DialogCode.Accepted:
            # Успешная регистрация
            continue  # Вернуться в цикл для входа

        # Если пользователь выбрал "Уже есть аккаунт", переключаемся на окно входа
        login_dialog = LoginDialog(db)
        if login_dialog.exec() != QDialog.DialogCode.Accepted:
            return  # Закрыть приложение, если вход не выполнен

        # Получить идентификатор пользователя и роль
        user_id, role = login_dialog.user_id, login_dialog.role
        break

    # Открыть основное приложение после успешного входа
    main_window = MainApp(db, user_id, role)
    main_window.show()
    sys.exit(app.exec())




if __name__ == "__main__":
    main()
