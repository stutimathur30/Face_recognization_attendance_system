import tkinter as tk
from tkinter import *
import os, cv2
import shutil
import csv
import numpy as np
from PIL import ImageTk, Image
import pandas as pd
import datetime
import time
import tkinter.ttk as tkk
import tkinter.font as font
import mysql.connector

haarcasecade_path = r"C:\Users\Lenovo\Desktop\Attendance-Management-system-using-face-recognition-master\Attendance-Management-system-using-face-recognition-master\haarcascade_frontalface_default.xml"
trainimagelabel_path = r"C:\Users\Lenovo\Desktop\Attendance-Management-system-using-face-recognition-master\Attendance-Management-system-using-face-recognition-master\TrainingImageLabel\Trainner.yaml"
trainimage_path = "TrainingImage"
studentdetail_path = r"C:\Users\Lenovo\Desktop\Attendance-Management-system-using-face-recognition-master\Attendance-Management-system-using-face-recognition-master\StudentDetails\studentdetails.csv"
attendance_path = "Attendance"

def subjectChoose(text_to_speech):
    def FillAttendance():
        sub = tx.get()
        now = time.time()
        future = now + 20

        if sub == "":
            t = "Please enter the subject name!!!"
            text_to_speech(t)
            return

        try:
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(trainimagelabel_path)
            facecasCade = cv2.CascadeClassifier(haarcasecade_path)
            df = pd.read_csv(studentdetail_path)
            cam = cv2.VideoCapture(0)
            font = cv2.FONT_HERSHEY_SIMPLEX
            col_names = ["Enrollment", "Name"]
            attendance = pd.DataFrame(columns=col_names)

            face_found = False

            while True:
                _, im = cam.read()
                gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                faces = facecasCade.detectMultiScale(gray, 1.2, 5)
                for (x, y, w, h) in faces:
                    Id, conf = recognizer.predict(gray[y:y + h, x:x + w])
                    if conf < 70:
                        face_found = True
                        Subject = tx.get()
                        ts = time.time()
                        date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                        timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                        aa = df.loc[df["Enrollment"] == Id]["Name"].values
                        tt = str(Id) + "-" + str(aa[0])
                        attendance.loc[len(attendance)] = [Id, aa[0]]
                        cv2.rectangle(im, (x, y), (x + w, y + h), (0, 260, 0), 4)
                        cv2.putText(im, str(tt), (x + h, y), font, 1, (255, 255, 0), 4)
                    else:
                        Id = "Unknown"
                        tt = str(Id)
                        cv2.rectangle(im, (x, y), (x + w, y + h), (0, 25, 255), 7)
                        cv2.putText(im, str(tt), (x + h, y), font, 1, (0, 25, 255), 4)

                if time.time() > future:
                    break

                attendance = attendance.drop_duplicates(["Enrollment"], keep="first")
                cv2.imshow("Filling Attendance...", im)
                key = cv2.waitKey(30) & 0xFF
                if key == 27:
                    break

            cam.release()
            cv2.destroyAllWindows()

            if not face_found:
                raise ValueError("No recognizable face detected.")

            ts = time.time()
            date = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            timeStamp = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            Hour, Minute, Second = timeStamp.split(":")

            path = os.path.join(attendance_path, Subject)
            if not os.path.exists(path):
                os.makedirs(path)
            fileName = f"{path}/{Subject}_{date}_{Hour}-{Minute}-{Second}.csv"
            attendance = attendance.drop_duplicates(["Enrollment"], keep="first")
            attendance.to_csv(fileName, index=False)

            try:
                conn = mysql.connector.connect(
                    host='localhost',
                    user='root',
                    password='your_password',  # Replace with your actual MySQL password
                    database='attendance_system'
                )
                cursor = conn.cursor()

                table_name = f"subject_{Subject.lower()}"

                for index, row in attendance.iterrows():
                    insert_query = f"""
                    INSERT INTO {table_name} (enrollment_no, name, date, time, status)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cursor.execute(insert_query, (str(row["Enrollment"]), str(row["Name"]), date, timeStamp, "Present"))

                conn.commit()
                cursor.close()
                conn.close()

            except Exception as db_error:
                print("MySQL Error:", db_error)
                text_to_speech("Database Error")

            m = "Attendance Filled Successfully for " + Subject
            Notifica.configure(
                text=m,
                bg="black",
                fg="yellow",
                width=33,
                relief=RIDGE,
                bd=5,
                font=("times", 15, "bold"),
            )
            Notifica.place(x=20, y=250)
            text_to_speech(m)

            import csv
            root = Tk()
            root.title("Attendance of " + Subject)
            root.configure(background="black")
            with open(fileName, newline="") as file:
                reader = csv.reader(file)
                r = 0
                for col in reader:
                    c = 0
                    for row in col:
                        label = Label(
                            root,
                            width=10,
                            height=1,
                            fg="yellow",
                            font=("times", 15, " bold "),
                            bg="black",
                            text=row,
                            relief=RIDGE,
                        )
                        label.grid(row=r, column=c)
                        c += 1
                    r += 1
            root.mainloop()

        except Exception as e:
            print("Error:", e)
            text_to_speech("No Face found for attendance")
            cv2.destroyAllWindows()

    subject = Tk()
    subject.title("Subject...")
    subject.geometry("580x320")
    subject.resizable(0, 0)
    subject.configure(background="black")

    titl = tk.Label(subject, bg="black", relief=RIDGE, bd=10, font=("arial", 30))
    titl.pack(fill=X)

    titl = tk.Label(
        subject,
        text="Enter the Subject Name",
        bg="black",
        fg="green",
        font=("arial", 25),
    )
    titl.place(x=160, y=12)

    Notifica = tk.Label(
        subject,
        text="Attendance filled Successfully",
        bg="yellow",
        fg="black",
        width=33,
        height=2,
        font=("times", 15, "bold"),
    )

    def Attf():
        sub = tx.get()
        if sub == "":
            t = "Please enter the subject name!!!"
            text_to_speech(t)
        else:
            os.startfile(f"Attendance\\{sub}")

    attf = tk.Button(
        subject,
        text="Check Sheets",
        command=Attf,
        bd=7,
        font=("times new roman", 15),
        bg="black",
        fg="yellow",
        height=2,
        width=10,
        relief=RIDGE,
    )
    attf.place(x=360, y=170)

    sub = tk.Label(
        subject,
        text="Enter Subject",
        width=10,
        height=2,
        bg="black",
        fg="yellow",
        bd=5,
        relief=RIDGE,
        font=("times new roman", 15),
    )
    sub.place(x=50, y=100)

    tx = tk.Entry(
        subject,
        width=15,
        bd=5,
        bg="black",
        fg="yellow",
        relief=RIDGE,
        font=("times", 30, "bold"),
    )
    tx.place(x=190, y=100)

    fill_a = tk.Button(
        subject,
        text="Fill Attendance",
        command=FillAttendance,
        bd=7,
        font=("times new roman", 15),
        bg="black",
        fg="yellow",
        height=2,
        width=12,
        relief=RIDGE,
    )
    fill_a.place(x=195, y=170)

    subject.mainloop()