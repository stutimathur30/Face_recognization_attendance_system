import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import face_recognition
import numpy as np
import mysql.connector
from datetime import datetime, timedelta
from PIL import Image, ImageTk
import os
from tkinter import font as tkfont
import logging
import threading
import queue
import time

class ModernAttendanceSystem:
    def __init__(self, root):
        self.root = root
        self.auto_attendance_active = False
        self.root.title("Smart Attendance Pro")
        self.root.geometry("1350x750")
        self.root.configure(bg="#f0f2f5")
        
        # Performance optimization variables
        self.processing_frame = False
        self.frame_queue = queue.Queue(maxsize=2)  # Limit queue size to prevent memory buildup
        self.attendance_queue = queue.Queue()
        self.skip_frames = 2  # Process every 3rd frame
        self.frame_counter = 0
        
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.attendance_today = set()
        
        # Custom fonts
        self.title_font = tkfont.Font(family="Helvetica", size=16, weight="bold")
        self.button_font = tkfont.Font(family="Arial", size=12)
        self.label_font = tkfont.Font(family="Arial", size=11)
        
        # Initialize database in background thread
        self.db = None
        self.db_ready = threading.Event()
        threading.Thread(target=self.initialize_db, daemon=True).start()
        
        # UI Elements
        self.setup_ui()
        
        # Camera setup
        self.cap = None
        self.camera_active = False
        self.current_frame = None
        
        # Face recognition data
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.face_data_ready = threading.Event()
        
        # Load known faces in background
        threading.Thread(target=self.load_known_faces, daemon=True).start()
        
        # Start frame processor thread
        self.frame_processor_thread = threading.Thread(target=self.process_frames, daemon=True)
        self.frame_processor_thread.start()
        
        # Start attendance processor thread
        self.attendance_processor_thread = threading.Thread(target=self.process_attendance_queue, daemon=True)
        self.attendance_processor_thread.start()

    def initialize_db(self):
        """Initialize database connection in background thread"""
        try:
            self.db = mysql.connector.connect(
                host="localhost",
                user="root",
                password="stuti123",
                database="attendance_system"
            )
            self.create_tables()
            self.db_ready.set()
            self.status("Database connected")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to connect to database:\n{str(e)}")
            self.db = None

    def create_tables(self):
        """Create required database tables"""
        if not self.db:
            return
            
        cursor = self.db.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id VARCHAR(20) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    department VARCHAR(50)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_encodings (
                    student_id VARCHAR(20) PRIMARY KEY,
                    encoding BLOB NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(student_id)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    status VARCHAR(10) NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(student_id),
                    UNIQUE KEY unique_attendance (student_id, date)
                )
            """)
            self.db.commit()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to create tables:\n{str(e)}")
        finally:
            cursor.close()

    def setup_ui(self):
        """Setup the user interface"""
        # Header Frame
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=80)
        header_frame.pack(fill=tk.X)
        
        title_label = tk.Label(header_frame, text="Smart Attendance Pro", 
                             font=self.title_font, bg="#2c3e50", fg="white")
        title_label.pack(side=tk.LEFT, padx=20, pady=20)
        
        date_label = tk.Label(header_frame, text=f"Date: {self.current_date}", 
                            font=self.label_font, bg="#2c3e50", fg="white")
        date_label.pack(side=tk.RIGHT, padx=20, pady=20)
        
        # Main Content Frame
        main_frame = tk.Frame(self.root, bg="#f0f2f5")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Left Panel - Registration
        left_panel = tk.Frame(main_frame, bg="white", bd=2, relief=tk.RIDGE)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        reg_title = tk.Label(left_panel, text="Student Registration", 
                           font=self.title_font, bg="white", fg="#2c3e50")
        reg_title.pack(pady=15)
        
        # Form Fields
        form_frame = tk.Frame(left_panel, bg="white")
        form_frame.pack(padx=15, pady=10, fill=tk.X)
        
        tk.Label(form_frame, text="Student ID:", font=self.label_font, bg="white").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.id_entry = ttk.Entry(form_frame, font=self.label_font)
        self.id_entry.grid(row=0, column=1, pady=8, padx=10, sticky=tk.EW)
        
        tk.Label(form_frame, text="Full Name:", font=self.label_font, bg="white").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.name_entry = ttk.Entry(form_frame, font=self.label_font)
        self.name_entry.grid(row=1, column=1, pady=8, padx=10, sticky=tk.EW)
        
        tk.Label(form_frame, text="Department:", font=self.label_font, bg="white").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.dept_entry = ttk.Entry(form_frame, font=self.label_font)
        self.dept_entry.grid(row=2, column=1, pady=8, padx=10, sticky=tk.EW)
        
        # Buttons
        btn_frame = tk.Frame(left_panel, bg="white")
        btn_frame.pack(pady=15, fill=tk.X, padx=15)
        
        self.capture_btn = tk.Button(btn_frame, text="Capture Face", command=self.capture_face,
                                   font=self.button_font, bg="#3498db", fg="white", bd=0, padx=15, pady=8)
        self.capture_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.register_btn = tk.Button(btn_frame, text="Register Student", command=self.register_student,
                                    font=self.button_font, bg="#2ecc71", fg="white", bd=0, padx=15, pady=8)
        self.register_btn.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Middle Panel - Camera
        middle_panel = tk.Frame(main_frame, bg="white", bd=2, relief=tk.RIDGE)
        middle_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        cam_title = tk.Label(middle_panel, text="Live Camera Feed", 
                           font=self.title_font, bg="white", fg="#2c3e50")
        cam_title.pack(pady=15)
        
        self.camera_frame = tk.Frame(middle_panel, bg="black", width=640, height=480)
        self.camera_frame.pack(pady=10)
        self.camera_frame.pack_propagate(False)
        
        self.camera_label = tk.Label(self.camera_frame)
        self.camera_label.pack(fill=tk.BOTH, expand=True)
        
        control_frame = tk.Frame(middle_panel, bg="white")
        control_frame.pack(pady=10)
        
        self.toggle_camera_btn = tk.Button(control_frame, text="Start Camera", command=self.toggle_camera,
                                         font=self.button_font, bg="#3498db", fg="white", bd=0, padx=15, pady=8)
        self.toggle_camera_btn.pack(side=tk.LEFT, padx=5)
        
        self.auto_start_btn = tk.Button(control_frame, text="Start Auto Attendance", 
                               command=self.start_automatic_attendance,
                               font=self.button_font, bg="#2ecc71", fg="white")
        self.auto_start_btn.pack(side=tk.LEFT, padx=5)

        self.auto_stop_btn = tk.Button(control_frame, text="Stop Auto Attendance", 
                              command=self.stop_automatic_attendance,
                              font=self.button_font, bg="#e74c3c", fg="white")
        self.auto_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Right Panel - Attendance
        right_panel = tk.Frame(main_frame, bg="white", bd=2, relief=tk.RIDGE)
        right_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)
        
        att_title = tk.Label(right_panel, text=f"Today's Attendance ({self.current_date})", 
                           font=self.title_font, bg="white", fg="#2c3e50")
        att_title.pack(pady=15)
        
        # Date selector
        date_frame = tk.Frame(right_panel, bg="white")
        date_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(date_frame, text="View Date:", font=self.label_font, bg="white").pack(side=tk.LEFT)
        self.date_entry = ttk.Entry(date_frame, font=self.label_font)
        self.date_entry.insert(0, self.current_date)
        self.date_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        view_btn = tk.Button(date_frame, text="View", command=self.load_attendance_for_date,
                            font=self.button_font, bg="#3498db", fg="white", bd=0, padx=10, pady=4)
        view_btn.pack(side=tk.LEFT)
        
        # Attendance Treeview
        tree_frame = tk.Frame(right_panel, bg="white")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.attendance_tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Time", "Status"), show="headings")
        self.attendance_tree.heading("ID", text="Student ID")
        self.attendance_tree.heading("Name", text="Name")
        self.attendance_tree.heading("Time", text="Time")
        self.attendance_tree.heading("Status", text="Status")
        self.attendance_tree.column("ID", width=100)
        self.attendance_tree.column("Name", width=150)
        self.attendance_tree.column("Time", width=80)
        self.attendance_tree.column("Status", width=80)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.attendance_tree.yview)
        self.attendance_tree.configure(yscrollcommand=scrollbar.set)
        
        self.attendance_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Export Button
        export_frame = tk.Frame(right_panel, bg="white")
        export_frame.pack(pady=10, fill=tk.X, padx=10)
        
        self.export_btn = tk.Button(export_frame, text="Export to CSV", command=self.export_attendance,
                                  font=self.button_font, bg="#27ae60", fg="white", bd=0, padx=15, pady=8)
        self.export_btn.pack(fill=tk.X)
        
        # Status Bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                 font=self.label_font, bg="#2c3e50", fg="white")
        self.status_bar.pack(fill=tk.X)
        
        # Initialize with today's attendance
        self.load_attendance_for_date()

    def toggle_camera(self):
        """Toggle camera on/off with proper error handling"""
        if not self.camera_active:
            try:
                self.cap = cv2.VideoCapture(0)
                if not self.cap.isOpened():
                    messagebox.showerror("Camera Error", "Could not open video device")
                    return
                    
                self.camera_active = True
                self.toggle_camera_btn.config(text="Stop Camera", bg="#e74c3c")
                self.status("Camera started")
                
                # Start camera thread
                self.camera_thread = threading.Thread(target=self.capture_frames, daemon=True)
                self.camera_thread.start()
            except Exception as e:
                messagebox.showerror("Camera Error", f"Failed to start camera:\n{str(e)}")
                if self.cap:
                    self.cap.release()
                self.camera_active = False
                self.toggle_camera_btn.config(text="Start Camera", bg="#3498db")
        else:
            self.camera_active = False
            if self.cap:
                self.cap.release()
            self.toggle_camera_btn.config(text="Start Camera", bg="#3498db")
            self.camera_label.config(image='')
            self.status("Camera stopped")

    def capture_frames(self):
        """Thread for capturing frames from camera"""
        while self.camera_active:
            ret, frame = self.cap.read()
            if ret:
                try:
                    # Skip frames if queue is full to prevent lag
                    if not self.frame_queue.full():
                        self.frame_queue.put(frame, timeout=0.1)
                    else:
                        # Get the latest frame if queue is full
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame, timeout=0.1)
                except queue.Full:
                    pass
                except queue.Empty:
                    pass
            else:
                break
            time.sleep(0.03)  # Reduce CPU usage

    def process_frames(self):
        """Thread for processing frames (face detection)"""
        while True:
            try:
                if not self.camera_active or not self.auto_attendance_active:
                    time.sleep(0.1)
                    continue
                    
                frame = self.frame_queue.get(timeout=0.1)
                self.frame_counter += 1
                
                # Skip frames to reduce processing load
                if self.frame_counter % (self.skip_frames + 1) != 0:
                    continue
                
                # Convert to RGB for processing
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create display frame
                display_frame = rgb_frame.copy()
                
                # Optimize face detection by resizing (faster processing)
                small_frame = cv2.resize(rgb_frame, (0, 0), fx=0.5, fy=0.5)
                
                # Find face locations using faster HOG model
                face_locations = face_recognition.face_locations(small_frame, model="hog")
                
                for (top, right, bottom, left) in face_locations:
                    # Scale back up face locations
                    top *= 2; right *= 2; bottom *= 2; left *= 2
                    
                    # Draw rectangle first (will be updated if recognized)
                    cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 2)
                    
                    # Only process encodings if we have known faces and auto attendance is on
                    if self.known_face_encodings and self.auto_attendance_active:
                        face_encoding = face_recognition.face_encodings(
                            rgb_frame, 
                            [(top, right, bottom, left)]
                        )[0]
                        
                        matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                        name = "Unknown"
                        color = (0, 0, 255)
                        status_text = "Not Registered"
                        
                        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index]:
                            name = self.known_face_names[best_match_index]
                            student_id = self.known_face_ids[best_match_index]
                            color = (0, 255, 0)
                            
                            if student_id not in self.attendance_today:
                                status_text = "Marking..."
                                self.attendance_queue.put((student_id, name))
                            else:
                                status_text = "Already Marked"
                    
                    # Update display
                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    cv2.rectangle(display_frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(display_frame, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)
                    cv2.putText(display_frame, status_text, (left + 6, top - 6), font, 0.8, color, 1)
                
                # Update display in main thread
                self.root.after(0, self.update_display, display_frame)
                
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Frame processing error: {e}")

    def update_display(self, frame):
        """Update the display in the main thread"""
        if not self.camera_active:
            return
            
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        self.camera_label.imgtk = imgtk
        self.camera_label.configure(image=imgtk)

    def process_attendance_queue(self):
        """Thread for processing attendance marking"""
        while True:
            try:
                student_id, name = self.attendance_queue.get(timeout=0.1)
                if self.mark_attendance(student_id):
                    self.attendance_today.add(student_id)
                    self.root.after(0, self.load_attendance_for_date)
                    self.root.after(0, self.show_thank_you_message, name)
            except queue.Empty:
                continue
            except Exception as e:
                logging.error(f"Attendance processing error: {e}")

    def show_thank_you_message(self, name):
        """Show thank you message and stop camera"""
        messagebox.showinfo("Attendance Marked", f"Thank you, {name}!\nAttendance marked successfully.")
        if self.camera_active:
            self.toggle_camera()  # This will stop the camera

    def mark_attendance(self, student_id):
        """Mark attendance in database"""
        if not self.db_ready.wait(timeout=5):
            return False
            
        cursor = self.db.cursor()
        try:
            today = datetime.now().date()
            current_time = datetime.now().time().strftime("%H:%M:%S")
            
            cursor.execute("SELECT * FROM attendance WHERE student_id = %s AND date = %s", 
                          (student_id, today))
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO attendance (student_id, date, time, status)
                    VALUES (%s, %s, %s, %s)
                    """, (student_id, today, current_time, 'Present'))
                self.db.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Attendance error: {e}")
            return False
        finally:
            cursor.close()

    def start_automatic_attendance(self):
        """Start automatic attendance marking"""
        if not self.camera_active:
            self.toggle_camera()
        
        self.auto_attendance_active = True
        self.status("Automatic attendance started - looking for faces...")

    def stop_automatic_attendance(self):
        """Stop automatic attendance marking"""
        self.auto_attendance_active = False
        self.status("Automatic attendance stopped")

    def capture_face(self):
        """Capture face for registration"""
        if not self.camera_active:
            messagebox.showwarning("Camera Off", "Please start the camera first")
            return
            
        if self.current_frame is not None:
            self.face_image = self.current_frame
            messagebox.showinfo("Success", "Face captured successfully!")
            self.status("Face captured - ready to register")
        else:
            messagebox.showerror("Error", "No frame available to capture")
            self.status("Failed to capture face")

    def register_student(self):
        """Register a new student"""
        student_id = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        department = self.dept_entry.get().strip() or "General"
        
        if not student_id or not name:
            messagebox.showerror("Error", "Student ID and Name are required!")
            self.status("Registration failed - missing fields")
            return
        
        if not hasattr(self, 'face_image'):
            messagebox.showerror("Error", "Please capture a face first!")
            self.status("Registration failed - no face captured")
            return
        
        try:
            # Convert to RGB and find encodings
            rgb_frame = cv2.cvtColor(self.face_image, cv2.COLOR_RGB2BGR)
            encodings = face_recognition.face_encodings(rgb_frame)
            
            if not encodings:
                messagebox.showerror("Error", "No face detected in captured image!")
                self.status("Registration failed - no face detected")
                return
            
            if not self.db_ready.wait(timeout=5):
                messagebox.showerror("Database Error", "Database connection not ready")
                return
                
            cursor = self.db.cursor()
            
            # Insert student data
            cursor.execute("""
                INSERT INTO students (student_id, name, department)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE name=VALUES(name), department=VALUES(department)
                """, (student_id, name, department))
            
            # Insert face encoding
            cursor.execute("""
                INSERT INTO face_encodings (student_id, encoding)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE encoding=VALUES(encoding)
                """, (student_id, encodings[0].tobytes()))
            
            self.db.commit()
            messagebox.showinfo("Success", f"Student {name} registered successfully!")
            self.status(f"Student {name} registered successfully")
            
            # Clear form and reload known faces
            self.id_entry.delete(0, tk.END)
            self.name_entry.delete(0, tk.END)
            self.dept_entry.delete(0, tk.END)
            del self.face_image
            
            # Reload known faces in background
            threading.Thread(target=self.load_known_faces, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Database Error", str(e))
            self.status(f"Registration failed - {str(e)}")
        finally:
            if 'cursor' in locals():
                cursor.close()

    def load_known_faces(self):
        """Load known faces from database in background"""
        if not self.db_ready.wait(timeout=5):
            return
            
        cursor = self.db.cursor()
        try:
            cursor.execute("""
                SELECT s.student_id, s.name, f.encoding 
                FROM students s
                JOIN face_encodings f ON s.student_id = f.student_id
                """)
            
            self.known_face_encodings = []
            self.known_face_ids = []
            self.known_face_names = []
            
            for (student_id, name, encoding_bytes) in cursor:
                self.known_face_encodings.append(np.frombuffer(encoding_bytes, dtype=np.float64))
                self.known_face_ids.append(student_id)
                self.known_face_names.append(name)
            
            self.status(f"Loaded {len(self.known_face_ids)} registered faces")
            self.face_data_ready.set()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load known faces:\n{str(e)}")
            self.status("Failed to load known faces")
        finally:
            cursor.close()

    def load_attendance_for_date(self):
        """Load attendance records for selected date"""
        if not self.db_ready.wait(timeout=5):
            self.status("Database not connected")
            return
        
        date_str = self.date_entry.get().strip() or self.current_date
    
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            self.status("Invalid date format (use YYYY-MM-DD)")
            return
        
        cursor = self.db.cursor()
        try:
            cursor.execute("""
                SELECT s.student_id, s.name, a.time, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.date = %s
                ORDER BY a.time DESC
                """, (selected_date,))
            
            self.attendance_tree.delete(*self.attendance_tree.get_children())
            
            for (student_id, name, time, status) in cursor:
                # Handle both time objects and timedelta objects
                if isinstance(time, timedelta):
                    # Convert timedelta to time string
                    total_seconds = time.total_seconds()
                    hours = int(total_seconds // 3600)
                    minutes = int((total_seconds % 3600) // 60)
                    seconds = int(total_seconds % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    # Regular time object
                    time_str = time.strftime("%H:%M:%S") if time else ""
                
                self.attendance_tree.insert("", tk.END, values=(student_id, name, time_str, status))
            
            self.status(f"Showing attendance for {selected_date}")
            
            if selected_date == datetime.now().date():
                cursor.execute("SELECT student_id FROM attendance WHERE date = %s", (selected_date,))
                self.attendance_today = set(row[0] for row in cursor)
            
        except Exception as e:
            self.status(f"Error loading attendance: {str(e)}")
            print(f"Database error: {e}")
        finally:
            cursor.close()

    def export_attendance(self):
        """Export attendance data to CSV"""
        if not self.db_ready.wait(timeout=5):
            return
            
        date_str = self.date_entry.get().strip() or self.current_date
        
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD format")
            return
            
        cursor = self.db.cursor()
        try:
            cursor.execute("""
                SELECT s.student_id, s.name, a.time, a.status
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.date = %s
                ORDER BY a.time
                """, (selected_date,))
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv")],
                initialfile=f"attendance_{selected_date}.csv"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write("Student ID,Name,Time,Status\n")
                    for (student_id, name, time, status) in cursor:
                        # Handle both time objects and timedelta objects
                        if isinstance(time, timedelta):
                            # Convert timedelta to time string
                            total_seconds = time.total_seconds()
                            hours = int(total_seconds // 3600)
                            minutes = int((total_seconds % 3600) // 60)
                            seconds = int(total_seconds % 60)
                            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            # Regular time object
                            time_str = time.strftime("%H:%M:%S") if time else ""
                        
                        f.write(f"{student_id},{name},{time_str},{status}\n")
                
                messagebox.showinfo("Success", f"Attendance data exported to:\n{filename}")
                self.status(f"Exported attendance to {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self.status("Export failed")
        finally:
            cursor.close()

    def status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'cap') and self.cap:
            self.cap.release()
        if hasattr(self, 'db') and self.db and self.db.is_connected():
            self.db.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernAttendanceSystem(root)
    root.mainloop()