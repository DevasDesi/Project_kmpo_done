import bcrypt
from database import Database

def register_user(db, username, password, role):
    if role not in ('admin', 'user'):
        raise ValueError("Invalid role. Must be 'admin' or 'user'.")

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        db.query("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hashed_password, role))
        print(f"User {username} registered successfully as {role}.")
    except Exception as e:
        print(f"Error registering user: {e}")

def login_user(db, username, password):
    user = db.fetch_one("SELECT id, password, role FROM users WHERE username = ?", (username,))
    if user:
        user_id, hashed_password, role = user
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            print(f"Login successful. Welcome, {username}!")
            return user_id, role
        else:
            print("Invalid password.")
    else:
        print("User not found.")
    return None, None

if __name__ == "__main__":
    db = Database()

    while True:
        action = input("Choose action (register/login/exit): ").strip().lower()
        if action == "register":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            role = input("Role (admin/user): ").strip().lower()
            register_user(db, username, password, role)
        elif action == "login":
            username = input("Username: ").strip()
            password = input("Password: ").strip()
            user_id, role = login_user(db, username, password)
            if user_id:
                print(f"Logged in as {role} (User ID: {user_id}).")
        elif action == "exit":
            break
        else:
            print("Invalid action.")
