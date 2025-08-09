import cv2
import face_recognition
import numpy as np
import mysql.connector
from datetime import datetime
import sys

def create_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="stuti123",
            database="attendance_system"
        )
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

def mark_attendance(student_id):
    conn = create_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            today = datetime.now().date()
            cursor.execute("""
                INSERT INTO attendance (student_id, date, time, status)
                SELECT %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM attendance 
                    WHERE student_id = %s AND date = %s
                )
                """, 
                (student_id, today, datetime.now().time(), 'Present', 
                 student_id, today))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"Attendance marked for {student_id}")
        except Exception as e:
            print(f"Error marking attendance: {str(e)}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

def load_known_faces():
    conn = create_db_connection()
    if not conn:
        return None, None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.student_id, f.encoding 
            FROM students s
            JOIN face_encodings f ON s.student_id = f.student_id
            """)
        
        known_encodings = []
        known_ids = []
        
        for (student_id, encoding_bytes) in cursor:
            known_encodings.append(np.frombuffer(encoding_bytes, dtype=np.float64))
            known_ids.append(student_id)
        
        return known_encodings, known_ids
    except Exception as e:
        print(f"Error loading known faces: {str(e)}")
        return None, None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def main():
    # Load known faces
    known_encodings, known_ids = load_known_faces()
    if not known_encodings:
        print("No known faces found in database!")
        return
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open video capture")
        return
    
    # Camera warm-up
    for _ in range(5):
        cap.read()
    
    process_this_frame = True
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error reading frame")
                break
            
            # Process every other frame
            if process_this_frame:
                # Resize and convert to RGB
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                rgb_frame = small_frame[:, :, ::-1]
                
                # Find face locations (HOG model)
                face_locations = face_recognition.face_locations(rgb_frame)
                
                # Get face encodings (simplified call)
                face_encodings = face_recognition.face_encodings(
                    rgb_frame, 
                    face_locations
                )
                
                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Compare faces
                    matches = face_recognition.compare_faces(
                        known_encodings, 
                        face_encoding,
                        tolerance=0.6
                    )
                    
                    name = "Unknown"
                    
                    if True in matches:
                        best_match = np.argmin(
                            face_recognition.face_distance(
                                known_encodings, 
                                face_encoding
                            )
                        )
                        student_id = known_ids[best_match]
                        name = f"ID: {student_id}"
                        mark_attendance(student_id)
                    
                    # Scale back up coordinates
                    top *= 4; right *= 4; bottom *= 4; left *= 4
                    
                    # Draw rectangle and label
                    cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                    cv2.putText(
                        frame, name, 
                        (left + 6, bottom - 6), 
                        cv2.FONT_HERSHEY_SIMPLEX, 
                        0.8, (255, 255, 255), 1
                    )
            
            process_this_frame = not process_this_frame
            
            # Display UI
            cv2.putText(
                frame, "ESC to quit", 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.7, (0, 0, 255), 2
            )
            cv2.imshow('Attendance System', frame)
            
            if cv2.waitKey(1) == 27:  # ESC key
                break
                
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Fix Windows console encoding
    if sys.stdout.encoding != 'UTF-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("Starting attendance system...")
    main()