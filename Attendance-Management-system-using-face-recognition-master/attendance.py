import tkinter as tk
from tkinter import *
import shutil
import os, cv2
import numpy as np
from PIL import Image, ImageTk
import pandas as pd 
import customtkinter as ctk
import os
import datetime
import time
import tkinter.font as font

# Project modules
import takeImage  # Import the TakeImage module
import trainImage
import automaticAttedance
import show_attendance
import pyttsx3

# Set appearance mode and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def text_to_speech(user_text):
    engine = pyttsx3.init()
    engine.say(user_text)
    engine.runAndWait()

class FaceRecognitionUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Class Vision - Face Recognition Attendance")
        self.geometry("1280x720")

        # Load and set background image
        try:
            self.bg_image = Image.open(r"C:\Users\Lenovo\Desktop\Attendance-Management-system-using-face-recognition-master\Attendance-Management-system-using-face-recognition-master\UI_Image\background.jpeg")
            self.bg_image = self.bg_image.resize((2000, 1000), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)

            self.bg_label = tk.Label(self, image=self.bg_photo)
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
        except:
            self.configure(bg="black")

        # Transparent overlay frame
        self.overlay = ctk.CTkFrame(self, corner_radius=20, fg_color=("#000000", "#1c1c1c"), width=1000, height=600)
        self.overlay.place(relx=0.5, rely=0.5, anchor="center")

        # Logo and title
        self.logo = Image.open(r"C:\Users\Lenovo\Desktop\Attendance-Management-system-using-face-recognition-master\Attendance-Management-system-using-face-recognition-master\UI_Image\0001.png")
        self.logo = self.logo.resize((50, 50))
        self.logo_img = ImageTk.PhotoImage(self.logo)

        self.title_frame = ctk.CTkFrame(self.overlay, corner_radius=10)
        self.title_frame.pack(pady=10, padx=20, fill="x")

        self.logo_label = ctk.CTkLabel(self.title_frame, image=self.logo_img, text="", width=50)
        self.logo_label.pack(side="left", padx=(10, 10))

        self.title_label = ctk.CTkLabel(
            self.title_frame, text="CLASS VISION", font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(side="left")

        self.intro_label = ctk.CTkLabel(
            self.overlay, text="Welcome to CLASS VISION", font=ctk.CTkFont(size=36, weight="bold")
        )
        self.intro_label.pack(pady=20)

        # Clock Display
        self.clock_label = ctk.CTkLabel(self.overlay, text="", font=ctk.CTkFont(size=18))
        self.clock_label.place(relx=0.95, rely=0.02, anchor="ne")
        self.update_clock()

        # Button Grid
        self.button_frame = ctk.CTkFrame(self.overlay)
        self.button_frame.pack(pady=30)

        self.register_btn = ctk.CTkButton(
            self.button_frame,
            text="Register Student",
            command=self.register_student,
            width=200,
            height=50,
            font=ctk.CTkFont(size=18)
        )
        self.register_btn.grid(row=0, column=0, padx=20, pady=10)

        self.attendance_btn = ctk.CTkButton(
            self.button_frame,
            text="Take Attendance",
            command=self.take_attendance,
            width=200,
            height=50,
            font=ctk.CTkFont(size=18)
        )
        self.attendance_btn.grid(row=0, column=1, padx=20, pady=10)

        self.view_btn = ctk.CTkButton(
            self.button_frame,
            text="View Attendance",
            command=self.view_attendance,
            width=200,
            height=50,
            font=ctk.CTkFont(size=18)
        )
        self.view_btn.grid(row=0, column=2, padx=20, pady=10)

        self.exit_btn = ctk.CTkButton(
            self.overlay,
            text="Exit",
            command=self.quit,
            width=200,
            height=50,
            font=ctk.CTkFont(size=18),
            fg_color="red",
            hover_color="#a30000"
        )
        self.exit_btn.pack(pady=40)

        # Voice Greeting on startup
        self.after(500, lambda: text_to_speech("Welcome to Class Vision"))

    def update_clock(self):
        current_time = time.strftime("%H:%M:%S")
        self.clock_label.configure(text=current_time)
        self.after(1000, self.update_clock)

    def register_student(self):
        self.take_image_ui()  # Calling the Take Image UI

    def take_image_ui(self):
        ImageUI = Tk()
        ImageUI.title("Take Student Image..")
        ImageUI.geometry("780x480")
        ImageUI.configure(background="#1c1c1c")  # Dark background for the image window
        ImageUI.resizable(0, 0)

        titl = tk.Label(ImageUI, bg="#1c1c1c", relief=RIDGE, bd=10, font=("Verdana", 30, "bold"))
        titl.pack(fill=X)

        # image and title
        titl = tk.Label(
            ImageUI, text="Register Your Face", bg="#1c1c1c", fg="green", font=("Verdana", 30, "bold"),
        )
        titl.place(x=270, y=12)

        # heading
        a = tk.Label(
            ImageUI,
            text="Enter the details",
            bg="#1c1c1c",  # Dark background for the details label
            fg="yellow",  # Bright yellow text color
            bd=10,
            font=("Verdana", 24, "bold"),
        )
        a.place(x=280, y=75)

        # ER no
        lbl1 = tk.Label(
            ImageUI,
            text="Enrollment No",
            width=10,
            height=2,
            bg="#1c1c1c",
            fg="yellow",
            bd=5,
            relief=RIDGE,
            font=("Verdana", 14),
        )
        lbl1.place(x=120, y=130)
        txt1 = tk.Entry(
            ImageUI,
            width=17,
            bd=5,
            bg="#333333",  # Dark input background
            fg="yellow",  # Bright text color for input
            relief=RIDGE,
            font=("Verdana", 18, "bold"),
        )
        txt1.place(x=250, y=130)

        # name
        lbl2 = tk.Label(
            ImageUI,
            text="Name",
            width=10,
            height=2,
            bg="#1c1c1c",
            fg="yellow",
            bd=5,
            relief=RIDGE,
            font=("Verdana", 14),
        )
        lbl2.place(x=120, y=200)
        txt2 = tk.Entry(
            ImageUI,
            width=17,
            bd=5,
            bg="#333333",  # Dark input background
            fg="yellow",  # Bright text color for input
            relief=RIDGE,
            font=("Verdana", 18, "bold"),
        )
        txt2.place(x=250, y=200)

        lbl3 = tk.Label(
            ImageUI,
            text="Notification",
            width=10,
            height=2,
            bg="#1c1c1c",
            fg="yellow",
            bd=5,
            relief=RIDGE,
            font=("Verdana", 14),
        )
        lbl3.place(x=120, y=270)

        message = tk.Label(
            ImageUI,
            text="",
            width=32,
            height=2,
            bd=5,
            bg="#333333",  # Dark background for messages
            fg="yellow",  # Bright text color for messages
            relief=RIDGE,
            font=("Verdana", 14, "bold"),
        )
        message.place(x=250, y=270)

        def take_image():
            enrollment = txt1.get()
            name = txt2.get()
            haarcascade_path = "haarcascade_frontalface_default.xml"  # Set the correct path
            trainimage_path = "TrainingImage"  # Set the correct directory for images
            takeImage.TakeImage(
                enrollment,
                name,
                haarcascade_path,
                trainimage_path,
                message,
                message,
                text_to_speech,
            )
            txt1.delete(0, "end")
            txt2.delete(0, "end")

        # take Image button
        takeImg = tk.Button(
            ImageUI,
            text="Take Image",
            command=take_image,
            bd=10,
            font=("Verdana", 18, "bold"),
            bg="#333333",  # Dark background for the button
            fg="yellow",  # Bright text color for the button
            height=2,
            width=12,
            relief=RIDGE,
        )
        takeImg.place(x=130, y=350)

    def take_attendance(self):
        text_to_speech("Launching Attendance Recognition")
        automaticAttedance.subjectChoose(text_to_speech)

    def view_attendance(self):
        text_to_speech("Opening Attendance Records")
        show_attendance.subjectchoose(text_to_speech)


if __name__ == "__main__":
    app = FaceRecognitionUI()
    app.mainloop()
