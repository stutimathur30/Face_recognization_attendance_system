Smart Attendance Pro is an automated attendance system that uses facial recognition technology to mark student attendance. The system captures student faces during registration and then automatically recognizes them to mark attendance when they appear before the camera.

Features
Facial Recognition: Real-time face detection and recognition
Attendance Tracking: Automatic attendance marking with duplicate prevention
Database Integration: Stores student data and attendance records in MySQL
User-Friendly Interface: Clean GUI with camera feed and attendance display
Data Export: Export attendance records to CSV format
Multi-Date Support: View attendance for any date

Technologies Used
Python (3.7+)
OpenCV (for camera operations)
face_recognition (for facial recognition)
MySQL (database backend)
Tkinter (GUI interface)
Pillow (image processing)

Prerequisites
Before running the project, ensure you have:
Python 3.7 or higher installed
MySQL Server installed and running
Webcam connected to your system
Stable internet connection (for package installation)

Installation
Clone the repository:
git clone https://github.com/yourusername/smart-attendance-pro.git
cd smart-attendance-pro

Create and activate virtual environment (recommended):
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

Install required packages:
pip install -r requirements.txt

Set up MySQL database:
Create a database named attendance_system
Update the database credentials in the code (host, user, password)

Database schema
CREATE TABLE students (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50)
);

CREATE TABLE face_encodings (
    student_id VARCHAR(20) PRIMARY KEY,
    encoding BLOB NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    status VARCHAR(10) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    UNIQUE KEY unique_attendance (student_id, date)
);
