<<<<<<< HEAD
Traffic Light Dashboard

Quick setup

1. Install Python 3.10+ and ensure `python` is on your PATH.
2. Create a virtualenv and activate it:

   python -m venv venv; .\venv\Scripts\Activate.ps1

3. Install dependencies:

   pip install -r requirements.txt

4. Place the model files (`yolov8n.pt`, `best.pt`) in the project root (they are already present in this repo).

5. Run the app:

   python app.py

Notes
- If OpenCV (cv2) import fails on Windows, install the appropriate wheel for your Python version or use conda.
- This repo expects a browser-based login; default admin user is `traffic-admin` with password `adminpassword` (hashed in the DB).

Running tests (optional)

1. Install dev dependencies:

   pip install -r requirements-dev.txt

2. Run pytest from the project root:

   pytest -q

The repository includes a basic unit test for `TrafficLogic` under `tests/` as a smoke check.
=======
# Intelligent-Traffic-Management-System-using-AI-with-Ambulance-Detection
>>>>>>> 1106944a8383a419b7fbba430c32e025cdee9dc9
