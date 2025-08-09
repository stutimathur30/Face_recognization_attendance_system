import cv2
import face_recognition
import numpy as np
from datetime import datetime
from db_utils import db_connection
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_known_faces():
    """Load registered faces from MySQL database with error handling"""
    known_faces = []
    known_students = []
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            # Modified query without is_active check
            query = """
                SELECT s.student_id, s.name, f.encoding 
                FROM students s
                JOIN face_encodings f ON s.student_id = f.student_id
            """
            cursor.execute(query)
            
            for student_id, name, encoding_bytes in cursor:
                try:
                    encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
                    known_faces.append(encoding)
                    known_students.append((student_id, name))
                except Exception as e:
                    logging.error(f"Error loading encoding for {student_id}: {e}")
    
    except Exception as e:
        logging.error(f"Database error loading known faces: {e}")
    
    return known_faces, known_students

def mark_attendance(student_id, status='present', notes=None):
    """Mark attendance with error handling"""
    today = datetime.now().date()
    now = datetime.now().time()
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 1 FROM attendance 
                WHERE student_id = %s AND date = %s
                LIMIT 1
            """, (student_id, today))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO attendance 
                    (student_id, date, time, status, recorded_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    student_id, 
                    today, 
                    now, 
                    status, 
                    'face_recognition', 
                    notes
                ))
                conn.commit()
                return True
    except Exception as e:
        logging.error(f"Error marking attendance for {student_id}: {e}")
    
    return False

def take_attendance():
    """Main function with improved error handling"""
    logging.info("Loading known faces from database...")
    try:
        known_faces, known_students = load_known_faces()
        
        if not known_faces:
            logging.warning("No registered faces found in database!")
            return
        
        logging.info(f"Loaded {len(known_faces)} registered faces")
        logging.info("Starting camera for attendance... (Press ESC to quit)")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logging.error("Could not open video device")
            return
            
        # Rest of your camera processing code...
        # [Previous camera processing code remains the same]
        
    except Exception as e:
        logging.error(f"Error in attendance system: {e}")
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    take_attendance()