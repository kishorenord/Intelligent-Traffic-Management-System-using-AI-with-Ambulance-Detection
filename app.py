import os
import cv2
import traceback
import sqlite3
import hashlib
import logging
import time
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify, session, flash

from detector import TrafficDetector
from traffic_logic import TrafficLogic

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
DATABASE = 'users.db'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'your_super_secret_key_for_sessions'

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('traffic_app')

# --- Database Setup ---
def setup_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT * FROM users WHERE username = ?", ('traffic-admin',))
    if cursor.fetchone() is None:
        password = 'adminpassword'
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                       ('traffic-admin', hashed_password))
        logger.info("Admin user created.")

    conn.commit()
    conn.close()

# --- Globals ---
video_paths = {1: None, 2: None, 3: None, 4: None}
video_caps = {1: None, 2: None, 3: None, 4: None}

# --- Load Detector ---
try:
    detector = TrafficDetector(
        vehicle_model_path='yolov8n.pt',
        ambulance_model_path='ambulance_model.pt'
    )
    logger.info("Detector loaded successfully.")
except Exception:
    logger.exception("Error loading YOLO models")
    detector = None

traffic_manager = TrafficLogic()

# --- Helpers ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def draw_ui_elements(frame, lane_id, density, ambulance, status):
    cv2.rectangle(frame, (10, 10), (70, 170), (50, 50, 50), -1)
    cv2.rectangle(frame, (10, 10), (70, 170), (255, 255, 255), 1)

    red_color = (0, 0, 255) if status == 'red' else (40, 40, 40)
    orange_color = (0, 165, 255) if status == 'orange' else (40, 40, 40)
    green_color = (0, 255, 0) if status == 'green' else (40, 40, 40)

    cv2.circle(frame, (40, 40), 20, red_color, -1)
    cv2.circle(frame, (40, 90), 20, orange_color, -1)
    cv2.circle(frame, (40, 140), 20, green_color, -1)

    cv2.putText(frame, f"Lane: {lane_id}", (10, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.putText(frame, f"Density: {density}", (10, 230),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    if ambulance:
        cv2.putText(frame, "AMBULANCE PRIORITY!", (10, 260),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

    return frame


# --- Video Streaming ---
def generate_frames(lane_id):
    global video_caps

    video_path = video_paths.get(lane_id)
    if not video_path:
        return

    if video_caps[lane_id] is None:
        try:
            video_caps[lane_id] = cv2.VideoCapture(video_path)
            if not video_caps[lane_id].isOpened():
                logger.error(f"Cannot open video for lane {lane_id}")
                return
        except Exception:
            logger.exception("Video capture error")
            return

    cap = video_caps[lane_id]

    while True:
        try:
            ret, frame = cap.read()

            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            if detector:
                processed_frame, ambulance_detected, detailed_counts = detector.process_frame(frame)

                density = sum(detailed_counts.values())

                # 🔥 Debug log
                logger.info(f"[Lane {lane_id}] Density={density}, Ambulance={ambulance_detected}")

                # 🔥 PRIORITY BOOST
                if ambulance_detected:
                    logger.warning(f"🚑 Ambulance detected in Lane {lane_id}")
                    density += 50

            else:
                processed_frame = frame
                ambulance_detected = False
                detailed_counts = {}
                density = 0

            # Update traffic logic
            traffic_manager.update_lane_data(lane_id, density, ambulance_detected, detailed_counts)

            current_state = traffic_manager.get_system_state()
            lane_status = current_state[lane_id]['status']

            final_frame = draw_ui_elements(
                processed_frame, lane_id, density, ambulance_detected, lane_status
            )

            (flag, encodedImage) = cv2.imencode(".jpg", final_frame)
            if not flag:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   bytearray(encodedImage) + b'\r\n')

            # 🔥 FPS control
            time.sleep(0.03)

        except Exception:
            logger.exception(f"Error in lane {lane_id}")
            break

    logger.info(f"Stopped stream for lane {lane_id}")


# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?",
                       (username, hashed_password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials', 'danger')

    return render_template('login.html')


@app.route('/home')
def home():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('project_home.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))


@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    global video_paths, video_caps

    if request.method == 'POST':
        video_caps = {1: None, 2: None, 3: None, 4: None}

        for i in range(1, 5):
            file = request.files.get(f'video{i}')
            if not file or file.filename == '':
                continue

            if allowed_file(file.filename):
                filename = f'lane_{i}.{file.filename.rsplit(".", 1)[1].lower()}'
                path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(path)
                video_paths[i] = path

        return redirect(url_for('dashboard'))

    return render_template('upload.html')


@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if not all(video_paths.values()):
        return redirect(url_for('upload_page'))

    return render_template('dashboard.html')


@app.route('/analysis')
def analysis_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('analysis.html')


@app.route('/video_feed/<int:lane_id>')
def video_feed(lane_id):
    if 'logged_in' not in session:
        return "Unauthorized", 401

    if lane_id not in [1, 2, 3, 4]:
        return "Invalid lane", 404

    if not video_paths.get(lane_id):
        return "No video", 404

    return Response(generate_frames(lane_id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/status_api')
def status_api():
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(traffic_manager.get_system_state())


@app.route('/api/analysis_data')
def analysis_data():
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(traffic_manager.get_analysis_data())


# --- Run ---
if __name__ == '__main__':
    setup_database()

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    app.run(debug=True, host='0.0.0.0', threaded=True)