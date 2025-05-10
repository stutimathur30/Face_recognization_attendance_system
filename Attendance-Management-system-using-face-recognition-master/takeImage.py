import cv2
import numpy as np
import os
import pymysql
import time
from PIL import Image
import datetime

import time

def TakeImage(enrollment, name, haarcascade_path, model_save_path, message_label, error_function, text_to_speech):
    if enrollment == "" or name == "":
        error_function()
        text_to_speech("Please fill all the required fields.")
        return

    try:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="stuti123",
            database="attendance_system"
        )
        cursor = conn.cursor()
    except pymysql.Error as err:
        message_label.configure(text="Database connection failed.")
        text_to_speech("Database connection failed.")
        print(f"MySQL Error: {err}")
        return

    if not os.path.exists("TrainingImage"):
        os.makedirs("TrainingImage")

    print("Opening camera...")
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
      print("Error: Camera failed to open.")
      message_label.configure(text="Camera not accessible.")
      text_to_speech("Camera not accessible.")
      return

    haarcascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(haarcascade_path)
    if detector.empty():
     print("Error: Haar cascade file not loaded properly.")
     return

    captured = False
    start_time = time.time()
    timeout = 10  # seconds

    while True:
        ret, img = cam.read()
        if not ret:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.3, 5)

        cv2.imshow("Capturing Image", img)

        if len(faces) > 0:
            x, y, w, h = faces[0]  # Take the first face only
            face_img = gray[y:y + h, x:x + w]
            filename = f"TrainingImage/{name}_{enrollment}.jpg"
            cv2.imwrite(filename, face_img)

            try:
                cursor.execute(
                    "INSERT INTO attendance (enrollment_no, name, image) VALUES (%s, %s, %s)",
                    (enrollment, name, filename)
                )
                conn.commit()
            except Exception as e:
                print(f"Insert error: {e}")
                message_label.configure(text="Failed to insert record.")
                text_to_speech("Failed to insert record.")
                cam.release()
                cv2.destroyAllWindows()
                return

            captured = True
            break

        if time.time() - start_time > timeout:
            break  # Timeout after 10 seconds if no face is detected

        if cv2.waitKey(1) & 0xFF == ord('q'):
         break

    cam.release()
    cv2.destroyAllWindows()
    cursor.close()
    conn.close()

    if captured:
        message_label.configure(text="Image captured and data saved.")
        text_to_speech("Image captured and data saved successfully.")
    else:
        message_label.configure(text="No face detected.")
        text_to_speech("No face detected. Please try again.")





def TrainImages(model_save_path, message_label, text_to_speech):
    try:
        # Connect to MySQL
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="stuti123",
            database="attendance_system"
        )
        cursor = conn.cursor()
        subject = "FaceCapture"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        filename = f"TrainingImage/{name}_{enrollment}.jpg"
        cursor.execute(
    """
    INSERT INTO attendance (name, enrollment_no, subject, date_time, image)
    VALUES (%s, %s, %s, %s, %s)
    """,
    (name, enrollment, subject, now, filename)
)
        records = cursor.fetchall()
        conn.commit()

        if len(records) == 0:
            message_label.configure(text="No data found in the database.")
            text_to_speech("No data found in the database.")
            return

        faces = []
        ids = []
        label_map = {}
        current_id = 0

        for record in records:
            enrollment, name, image_path = record
            if not os.path.exists(image_path):
                continue

            # Assign a unique numeric ID to each enrollment
            if enrollment not in label_map:
                label_map[enrollment] = current_id
                current_id += 1

            img = Image.open(image_path).convert('L')  # grayscale
            img_np = np.array(img, 'uint8')
            faces.append(img_np)
            ids.append(label_map[enrollment])

        if not faces:
            message_label.configure(text="No valid images found.")
            text_to_speech("No valid images found.")
            return

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids))
        recognizer.save(model_save_path)

        message_label.configure(text="Training Completed Successfully")
        text_to_speech("Training Completed Successfully")

    except Exception as e:
        message_label.configure(text=f"Training Failed: {e}")
        text_to_speech("Training Failed")

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
