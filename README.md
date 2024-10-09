Biometric Attendance System
This biometric attendance system is a time and attendance tracking system that allows staff or teachers to organize courses, manage students, and mark students' attendance using their unique physical characteristics—their fingerprints. It's built using computer vision (Python OpenCV), Flask, and the MERN stack.

NB: This system has been built and tested with The DigitalPersona U.are.U 4500 scanner only. It currently supports Windows OS.

Below is an image of the DigitalPersona U.are.U 4500 scanner:


Download and install the required client for Windows here: HID DigitalPersona Client

Project Structure
The project is divided into three sections:

Frontend (React): User interface and client-side logic.
Backend (Flask): Manages the API, database communication, and business logic.
Biometric Integration (Python OpenCV): Handles fingerprint scanning and verification using the biometric hardware.
Getting Started
Follow the steps below to set up the project locally:

Clone the repository:
bash
Copy code
# Using HTTPS
git clone https://github.com/Mikailhassan/school-attendnce-management-software.git

# Using SSH
git clone git@github.com:Mikailhassan/school-attendnce-management-software.git
Install Dependencies and Set Up:
Frontend: Navigate to the frontend directory and run:
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
Project DB ERD
Below is the Entity Relationship Diagram (ERD) for the system's database:


Screenshots
Here are some screenshots of the system in action:

![Screenshot of system 1](./screenshots/bas_screenshot_1.JPG)

![Screenshot of system 2](./screenshots/bas_screenshot_2.JPG)

![Screenshot of system 3](./screenshots/bas_screenshot_3.JPG)

![Screenshot of system 4](./screenshots/bas_screenshot_4.JPG)

![Screenshot of system 5](./screenshots/bas_screenshot_5.jpg)

![Screenshot of system 6](./screenshots/bas_screenshot_6.JPG)

![Screenshot of system 7](./screenshots/bas_screenshot_7.JPG)



Contributing
Contributions are what make the open-source community such a great place to learn, inspire, and create. Any contributions you make are greatly appreciated.

If you have a suggestion for improvement, feel free to fork the repo and create a pull request. You can also open an issue with the tag "enhancement".
Don't forget to star the project! Thanks again!

Contribution Steps:
Fork the project.
Create your feature branch (git checkout -b feature/AmazingFeature).
Commit your changes (git commit -m 'Add some AmazingFeature').
Push to the branch (git push origin feature/AmazingFeature).
Open a Pull Request.
License
This project is licensed under the MIT License. See the LICENSE file for more information.

