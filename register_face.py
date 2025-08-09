import cv2
import face_recognition
import numpy as np
import mysql.connector
from datetime import datetime
import sys
import logging
import time
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('attendance.log'),
        logging.StreamHandler()
    ]
)

@contextmanager
def db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="stuti123",
            database="attendance_system",
            pool_name="attendance_pool",
            pool_size=3
        )
        yield conn
    except Exception as e:
        logging.error(f"Database connection error: {str(e)}")
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

def mark_attendance(student_id):
    """Mark attendance with improved error handling and duplicate prevention"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            now = datetime.now().time()
            
            # Check if attendance already marked today
            cursor.execute("""
                SELECT 1 FROM attendance 
                WHERE student_id = %s AND date = %s
                LIMIT 1
            """, (student_id, today))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO attendance 
                    (student_id, date, time, status, recorded_by)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student_id, today, now, 'Present', 'face_recognition'))
                conn.commit()
                logging.info(f"Attendance marked for {student_id}")
                return True
            return False
    except Exception as e:
        logging.error(f"Error marking attendance for {student_id}: {str(e)}")
        return False

def load_known_faces():
    """Load known faces with performance optimizations"""
    known_encodings = []
    known_ids = []
    
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.student_id, s.name, f.encoding 
                FROM students s
                JOIN face_encodings f ON s.student_id = f.student_id
                WHERE s.is_active = TRUE
            """)
            
            for student_id, name, encoding_bytes in cursor:
                try:
                    encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
                    known_encodings.append(encoding)
                    known_ids.append((student_id, name))
                except Exception as e:
                    logging.error(f"Error decoding face for {student_id}: {str(e)}")
        
        logging.info(f"Loaded {len(known_encodings)} known faces")
        return known_encodings, known_ids
    except Exception as e:
        logging.error(f"Error loading known faces: {str(e)}")
        return None, None

def main():
    """Main attendance system with enhanced features"""
    # Fix Windows console encoding
    if sys.stdout.encoding != 'UTF-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    logging.info("Starting attendance system...")
    
    # Load known faces
    known_encodings, known_ids = load_known_faces()
    if not known_encodings:
        logging.error("No known faces found in database!")
        return
    
    # Initialize camera with optimized settings
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        logging.error("Could not open video capture")
        return
    
    try:
        # Camera configuration
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Variables for performance tracking
        frame_count = 0
        process_this_frame = True
        last_attendance = {}  # Track last attendance time per student
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.error("Error reading frame")
                break
            
            frame_count += 1
            
            # Only process every other frame for better performance
            if process_this_frame:
                # Resize and convert to RGB
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_frame = small_frame[:, :, ::-1]
                
                # Find face locations (HOG model is faster than CNN)
                face_locations = face_recognition.face_locations(
                    rgb_frame,
                    model="hog"  # Faster than "cnn"
                )
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(
                    rgb_frame, 
                    face_locations
                )
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Compare faces with known encodings
                    matches = face_recognition.compare_faces(
                        known_encodings, 
                        face_encoding,
                        tolerance=0.5  # Lower is more strict
                    )
                    
                    name = "Unknown"
                    student_id = None
                    
                    if True in matches:
                        # Use the known face with the smallest distance
                        face_distances = face_recognition.face_distance(
                            known_encodings, 
                            face_encoding
                        )
                        best_match = np.argmin(face_distances)
                        
                        if matches[best_match]:
                            student_id, name = known_ids[best_match]
                            
                            # Prevent duplicate attendance within 5 minutes
                            current_time = time.time()
                            last_marked = last_attendance.get(student_id, 0)
                            
                            if current_time - last_marked > 300:  # 5 minutes
                                if mark_attendance(student_id):
                                    last_attendance[student_id] = current_time
                    
                    # Scale back up coordinates
                    top *= 4; right *= 4; bottom *= 4; left *= 4
                    
                    # Draw rectangle and label
                    color = (0, 255, 0) if student_id else (0, 0, 255)
                    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                    cv2.putText(
                        frame, name, 
                        (left + 6, bottom - 6), 
                        cv2.FONT_HERSHEY_DUPLEX, 
                        0.8, (255, 255, 255), 1
                    )
            
            process_this_frame = not process_this_frame
            
            # Display UI
            cv2.putText(
                frame, "ESC to quit | FPS: {:.1f}".format(cap.get(cv2.CAP_PROP_FPS)), 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (0, 0, 255), 2
            )
            cv2.imshow('Attendance System', frame)
            
            if cv2.waitKey(1) == 27:  # ESC key
                logging.info("Attendance system stopped by user")
                break
                
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()