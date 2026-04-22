import sqlite3

DB_NAME = "deployer.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            project_name TEXT NOT NULL,
            assigned_port INTEGER NOT NULL,
            route_path TEXT NOT NULL,
            container_name TEXT NOT NULL,
            status TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

def add_deployment(student_name, project_name, assigned_port, route_path, container_name, status):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO deployments (
            student_name, project_name, assigned_port, route_path, container_name, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_name, project_name, assigned_port, route_path, container_name, status))

    conn.commit()
    conn.close()

def get_all_deployments():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM deployments ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows