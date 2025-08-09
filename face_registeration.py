import cv2
import face_recognition
import numpy as np
from db_utils import db_connection  # Using your MySQL connection
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def register_face(student_id, name, department="General"):
    """Register a new face with enhanced features"""
    cap = None
    try:
        # Initialize camera with optimal settings
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        logging.info("Starting face registration...")
        print("\nInstructions:")
        print("1. Face the camera directly")
        print("2. Ensure good lighting")
        print("3. Keep a neutral expression")
        print("4. Press SPACE to capture")
        print("5. Press ESC to cancel\n")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to capture frame")
                break
            
            # Display instructions on the frame
            cv2.putText(frame, "Press SPACE to capture", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, "Press ESC to cancel", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Show face detection in real-time
            rgb_small_frame = frame[:, :, ::-1]  # Convert to RGB
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            # Draw rectangle around detected faces
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            
            cv2.imshow('Register Face', frame)
            
            key = cv2.waitKey(1)
            if key == 32:  # SPACE key to capture
                if len(face_locations) != 1:
                    print("Error: Please ensure exactly one face is visible")
                    continue
                
                # Get high-quality face encoding
                face_encodings = face_recognition.face_encodings(
                    rgb_small_frame, 
                    face_locations,
                    model="large"  # More accurate but slower
                )
                
                if not face_encodings:
                    print("Error: Could not extract face features")
                    continue
                
                # Save to database
                if save_to_database(student_id, name, department, face_encodings[0]):
                    print(f"\n Successfully registered {name} (ID: {student_id})")
                    logging.info(f"Registered face for {name} ({student_id})")
                    break
            
            elif key == 27:  # ESC to quit
                print("\nRegistration cancelled")
                break
    
    except Exception as e:
        logging.error(f"Error during face registration: {e}")
        print(f"\n Error: {e}")
    finally:
        if cap and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()

def save_to_database(student_id, name, department, face_encoding):
    """Save student data to MySQL database with transaction"""
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            
            # Start transaction
            conn.start_transaction()
            
            # Insert/update student
            cursor.execute("""
                INSERT INTO students 
                (student_id, name, department, registration_date)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                name=VALUES(name), 
                department=VALUES(department)
            """, (
                student_id, 
                name, 
                department, 
                datetime.now()
            ))
            
            # Insert/update face encoding
            cursor.execute("""
                INSERT INTO face_encodings 
                (student_id, encoding, last_updated)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                encoding=VALUES(encoding),
                last_updated=VALUES(last_updated)
            """, (
                student_id, 
                face_encoding.tobytes(), 
                datetime.now()
            ))
            
            conn.commit()
            return True
            
    except Exception as e:
        logging.error(f"Database error: {e}")
        if conn.is_connected():
            conn.rollback()
        return False

if __name__ == "__main__":
    print("\n=== Face Registration System ===")
    try:
        student_id = input("Enter Student ID: ").strip()
        name = input("Enter Full Name: ").strip()
        department = input("Enter Department (optional, default: General): ").strip() or "General"
        
        if not student_id or not name:
            raise ValueError("Student ID and Name are required")
            
        register_face(student_id, name, department)
    except Exception as e:
        print(f"\n Error: {e}")
        logging.error(f"Registration failed: {e}")