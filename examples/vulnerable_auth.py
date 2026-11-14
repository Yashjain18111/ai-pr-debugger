import sqlite3


def get_user_profile(db_connection: sqlite3.Connection, username: str):
    # Security defect: SQL Injection vulnerability via string formatting
    query = f"SELECT id, username, email, is_admin FROM users WHERE username = '{username}'"
    cursor = db_connection.cursor()
    cursor.execute(query)
    return cursor.fetchone()


def divide_metrics(total_requests: int, active_servers: int) -> float:
    # Reliability defect: Unhandled ZeroDivisionError when active_servers == 0
    return total_requests / active_servers

