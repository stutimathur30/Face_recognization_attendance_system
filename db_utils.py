import mysql.connector
from mysql.connector import Error, pooling
import os
from dotenv import load_dotenv
import numpy as np
from contextlib import contextmanager

# Load environment variables
load_dotenv()

# Connection pool setup
connection_pool = None

def initialize_pool():
    global connection_pool
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="attendance_pool",
        pool_size=5,
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', 'stuti123'),
        database=os.getenv('DB_NAME', 'attendance_system')
    )

@contextmanager
def db_connection():
    conn = None
    try:
        conn = connection_pool.get_connection()
        yield conn
    except Error as e:
        print(f"Database error: {e}")
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

def initialize_database():
    with db_connection() as conn:
        cursor = conn.cursor()
        
        # Create students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id VARCHAR(20) PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                department VARCHAR(50),
                email VARCHAR(100),
                phone VARCHAR(20),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Create face_encodings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_encodings (
                student_id VARCHAR(20) PRIMARY KEY,
                encoding BLOB NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
        """)
        
        # Create attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                attendance_id INT AUTO_INCREMENT PRIMARY KEY,
                student_id VARCHAR(20) NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status ENUM('present', 'absent', 'late') NOT NULL,
                recorded_by VARCHAR(50),
                notes TEXT,
                FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
                UNIQUE KEY unique_attendance (student_id, date)
            )
        """)
        
        conn.commit()
        print("Database tables initialized successfully!")

# Initialize the connection pool when module is loaded
initialize_pool()

if __name__ == "__main__":
    initialize_database()