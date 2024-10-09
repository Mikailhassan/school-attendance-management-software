Biometric Attendance System
This Biometric Attendance System is a time and attendance tracking system designed to help staff or teachers organize courses, manage students, and track attendance using the most unique physical identifier—fingerprints. It leverages computer vision (Python OpenCV), Flask, and the MERN stack to ensure accurate, efficient, and secure attendance management.

Note: The system has been developed and tested specifically with the DigitalPersona U.are.U 4500 fingerprint scanner and is currently supported on Windows OS only.

Hardware Supported
Below is an image of the DigitalPersona U.are.U 4500 fingerprint scanner:

You can download and install the required client for Windows here: HID DigitalPersona Client

Project Structure
The project is structured into three core sections for smooth functionality:

Frontend (React): Handles the user interface and client-side logic.
Backend (Flask): Manages business logic, API requests, and database communication.
Biometric Integration (Python OpenCV): Incorporates the biometric hardware for fingerprint scanning and verification.
Getting Started
To get the project up and running locally, follow the steps below:

Clone the repository:
bash
Copy code
# Using HTTPS
git clone https://github.com/Mikailhassan/school-attendnce-management-software.git

# Using SSH
git clone git@github.com:Mikailhassan/school-attendnce-management-software.git
Install dependencies and set up the project:
Frontend: Navigate to the frontend folder and run:
bash
Copy code
npm install
npm start
Backend: In the backend directory, create a virtual environment and install dependencies:
bash
Copy code
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate  # For Windows
pip install -r requirements.txt
Database Structure
The project uses a relational database system for managing attendance and student data. Below is the Entity Relationship Diagram (ERD) showcasing the database structure:



Screenshots
Here are some screenshots of the system in action:



Contributing
This project welcomes contributions to enhance its functionality and make it even better. Contributions are highly appreciated and help foster the open-source community.

If you have suggestions or improvements, you can fork the repository and submit a pull request. You can also open an issue tagged with "enhancement".

Contribution Steps:
Fork the repository.
Open a pull request.
License
This project is distributed under the MIT License. See the LICENSE file for more information.